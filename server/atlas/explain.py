from dataclasses import dataclass, field
import functools
from typing import List, Dict, Optional, Tuple
import numpy as np
import logging

from server.adapters.domain_profile import PRIMARY_DOMAIN, get_profile
from server.atlas.adaptive_context import AdaptiveContext, NeighborContext

logger = logging.getLogger(__name__)

@dataclass
class ExplanationReport:
    confidence_score: float
    confidence_level: str
    primary_justification: str
    citations: List[str]
    note: str = ""
    sensor_attributions: List[Dict[str, float]] = field(default_factory=list)
    top_contributors: List[str] = field(default_factory=list)
    attribution_unavailable_reason: Optional[str] = None
    
    def to_dict(self):
        return {
            "confidence_score": self.confidence_score,
            "confidence_level": self.confidence_level,
            "primary_justification": self.primary_justification,
            "citations": self.citations,
            "note": self.note,
            "sensor_attributions": self.sensor_attributions,
            "top_contributors": self.top_contributors,
            "attribution_unavailable_reason": self.attribution_unavailable_reason
        }

class ExplanationEngine:
    """
    Constructs a structured explanation string from a template to ground predictions
    in historical AMKB data. This relies on template-based string construction, not
    generative NLG/LLMs.
    
    CONFIDENCE FORMULA:
    Confidence is mathematically bounded using a combination of similarity and true_rul variance:
      confidence = avg_similarity * (1.0 / (1.0 + variance))
    where:
      similarity = 1.0 / (1.0 + cosine_distance)
      variance = np.var(true_ruls)
    This prevents division-by-zero crashes (via the +1.0 epsilon) and gracefully penalizes 
    high-variance historical trajectories.
    
    UNGROUNDED BASELINE (grounding_enabled=False):
    When grounding is disabled, AMKB citation construction is bypassed entirely.
    Confidence defaults to a constant 0.50, representing maximal uncertainty in the
    absence of empirical historical grounding — the natural uninformative prior when
    no historical evidence is consulted.
    
    FUTURE DECISION (Month 6): When live domains begin returning experiences where
    `true_rul` is `None` (because failure hasn't occurred yet), this engine will
    filter out those neighbors prior to computation (silently reducing k). If all
    retrieved neighbors are filtered, it will degrade gracefully to the zero-neighbor
    fallback. It will not hard-crash the API.
    """
    def __init__(self, grounding_enabled: bool = True):
        self.grounding_enabled = grounding_enabled

    def _attribute(self, context: AdaptiveContext, window: Optional[np.ndarray], ace):
        """Occlusion attribution plus the sentence that names the strongest sensor."""
        if window is None or ace is None:
            return [], [], "", None
        attributions, reason = self.calculate_feature_attribution(window, ace, context.predicted_rul, context.domain)
        if not attributions:
            return [], [], "", reason
        top = attributions[0]
        if get_profile(context.domain).rul_scale is None:
            # The output of these domains is a 0-1 estimate, not cycles: state the size, not a direction.
            text = (f" {top['sensor_name']} is the strongest driver of this estimate: masking it moves the "
                    f"model output by {top['magnitude']:.3f}.")
        elif top["signed_delta"] > 0:
            text = f" {top['sensor_name']} readings are actively driving this prediction toward a shorter RUL estimate."
        elif top["signed_delta"] < 0:
            text = f" {top['sensor_name']} readings are supporting a healthier (longer) RUL estimate."
        else:
            text = f" {top['sensor_name']} is the most influential factor in this prediction."
        return attributions, [a["sensor_name"] for a in attributions[:3]], text, reason

    def explain(self, context: AdaptiveContext, window: Optional[np.ndarray] = None, ace=None) -> ExplanationReport:
        attributions, top_contributors, attribution_text, attribution_unavailable_reason = self._attribute(context, window, ace)
        noun = "engine" if context.domain == PRIMARY_DOMAIN else "machine"

        # Check if grounding is explicitly disabled
        if not self.grounding_enabled:
            return ExplanationReport(
                confidence_score=0.50,
                confidence_level="Moderate",
                primary_justification="Ungrounded prediction: historical AMKB episodic memory retrieval disabled." + attribution_text,
                citations=[],
                note="Ungrounded baseline mode: confidence fixed at 0.50 maximal uncertainty prior.",
                sensor_attributions=attributions,
                top_contributors=top_contributors,
                attribution_unavailable_reason=attribution_unavailable_reason,
            )

        neighbors = context.neighbors
        
        # Guard against zero neighbors
        if not neighbors:
            return ExplanationReport(
                confidence_score=0.0,
                confidence_level="Low",
                primary_justification=f"No historical similar {noun}s found to ground this prediction." + attribution_text,
                citations=[],
                sensor_attributions=attributions,
                top_contributors=top_contributors,
                attribution_unavailable_reason=attribution_unavailable_reason
            )

        # 2. Explicit carry-over: citations MUST use true_rul, never predicted_rul
        # We assert this here to prevent circular justification.
        true_ruls = []
        similarities = []
        for n in neighbors:
            if getattr(n, "rul", None) is None:
                if get_profile(context.domain).run_to_failure:
                    raise ValueError("Neighbors must contain true RUL for citations, not predicted RUL")
                # Month 6 Update: Filter out live-domain neighbors (e.g. laptop)
                # that have no known failure time, ensuring we only cite 
                # historical fully-failed experiences.
                continue
            true_ruls.append(n.rul)
            # n.distance from pgvector is cosine distance [0, 2], where 0 is identical.
            # We map this to a similarity score [0, 1] where 1 is identical.
            sim = 1.0 / (1.0 + n.distance)
            similarities.append(sim)
            
        if not true_ruls:
            # If ALL neighbors were filtered out, fallback safely
            logger.warning("No neighbors with true_rul found. Cannot generate confident citations.")
            return ExplanationReport(
                confidence_score=0.5,
                confidence_level="Low",
                primary_justification="Insufficient historical failure data for confident citation." + attribution_text,
                citations=[],
                sensor_attributions=attributions,
                top_contributors=top_contributors,
                attribution_unavailable_reason=attribution_unavailable_reason
            )
            
        true_ruls_arr = np.array(true_ruls)
        similarities_arr = np.array(similarities)
        
        # Calculate variance
        variance = np.var(true_ruls_arr)
        
        # Average similarity (cosine distance mapping)
        avg_similarity = float(np.mean(similarities_arr))
        
        # 1. Confidence formula with epsilon=1 to prevent division by zero
        # Multiplicative combination: confidence = avg_similarity * (1 / (1 + variance))
        confidence_score = avg_similarity * (1.0 / (1.0 + variance))
        
        # Determine human readable level
        if confidence_score > 0.5:
            level = "High"
        elif confidence_score > 0.1:
            level = "Moderate"
        else:
            level = "Low"
            
        note = ""
        if len(neighbors) < 10:
            note = "Confidence scores derived from small neighbor counts should be interpreted as indicative, not precise."
            
        # 3. Construct structured explanation string from a template
        avg_true_rul = float(np.mean(true_ruls_arr))
        primary_justification = (
            f"Prediction is grounded in {len(neighbors)} historically similar {noun} trajectories "
            f"with an average true RUL of {avg_true_rul:.1f} cycles. "
            f"The matching units exhibited a variance of {variance:.1f} cycles."
        ) + attribution_text
        
        # Construct citations
        citations = []
        for n in neighbors:
            if getattr(n, "rul", None) is None:
                continue
            # Map cosine distance back to similarity for human readability, or just show distance
            sim = 1.0 / (1.0 + n.distance)
            citations.append(f"Unit {n.machine_id} at cycle {n.cycle} (True RUL: {n.rul:.1f}, similarity: {sim:.4f})")
            
        return ExplanationReport(
            confidence_score=float(confidence_score),
            confidence_level=level,
            primary_justification=primary_justification,
            citations=citations,
            note=note,
            sensor_attributions=attributions,
            top_contributors=top_contributors,
            attribution_unavailable_reason=attribution_unavailable_reason
        )

    def calculate_feature_attribution(self, window: np.ndarray, ace, baseline_rul: float,
                                      domain: str = PRIMARY_DOMAIN) -> Tuple[List[Dict[str, float]], Optional[str]]:
        """
        Occlusion sensitivity per sensor, for any domain with a known feature layout.

        GRANULARITY: one sensor at a time, the whole column across the window (feature_dim
        extra forward passes, not seq_len * feature_dim).

        BASELINE VALUE: C-MAPSS columns are masked with 0.0, as they always were, so the
        published deletion-test numbers stay reproducible. Every other domain is masked with
        the population-average value of that sensor, taken from the profiles its model was
        trained on (see `feature_layout`), because 0.0 on a [0, 1] scale is an extreme reading.

        Returns (attributions sorted by magnitude, None) or ([], reason).
        """
        window = np.asarray(window)
        if window.ndim != 2:
            return [], f"Feature attribution needs a 2D window, got shape {window.shape}."
        layout = feature_layout(domain, window.shape[1])
        if layout is None:
            return [], (f"No sensor layout is registered for domain '{domain}' with {window.shape[1]} features, "
                        "so per-sensor attribution is not available.")
        names, baseline = layout

        resolve = getattr(ace, "get_world_model", None)
        model = resolve(domain, window.shape[1]) if callable(resolve) else getattr(ace, "world_model", None)
        if model is None:
            return [], f"No trained World Model for domain '{domain}' with {window.shape[1]} features."
        seq_len = int(getattr(getattr(model, "config", None), "seq_len", 30) or 30)
        if window.shape[0] != seq_len:
            return [], f"Feature attribution needs a window of {seq_len} steps, got {window.shape[0]}."

        from server.atlas.world_model import prepare_window

        attributions = []
        for idx, sensor_name in enumerate(names):
            occluded = np.copy(window)
            occluded[:, idx] = baseline[idx]
            occ_rul = float(model.predict(prepare_window(occluded, seq_len=seq_len, feature_dim=window.shape[1])).rul_pred)
            # A positive delta means the real readings were pulling the estimate down.
            signed_delta = occ_rul - baseline_rul
            attributions.append({
                "sensor_index": idx,
                "sensor_name": sensor_name,
                "magnitude": float(abs(signed_delta)),
                "signed_delta": float(signed_delta),
            })

        # Largest first; ties by sensor index so the order is stable.
        attributions.sort(key=lambda x: (-x["magnitude"], x["sensor_index"]))
        return attributions, None


@functools.lru_cache(maxsize=16)
def feature_layout(domain: str, feature_dim: int) -> Optional[Tuple[Tuple[str, ...], Tuple[float, ...]]]:
    """(sensor names, occlusion baseline) in the model's column order, or None when the layout is unknown.

    A sensor name reads "<channel> (<what it measures>)"; the channel key comes first so the
    3D Asset View can bind it to a part.
    """
    if domain == PRIMARY_DOMAIN:
        from server.adapters.cmapss_adapter import INFORMATIVE_SENSORS, SENSOR_DESCRIPTIONS

        if feature_dim != len(INFORMATIVE_SENSORS):
            return None
        return (tuple(f"{c} ({SENSOR_DESCRIPTIONS.get(c, c)})" for c in INFORMATIVE_SENSORS),
                (0.0,) * feature_dim)  # the benchmark's original occlusion value

    profile = get_profile(domain)
    if not profile.features or len(profile.features) != feature_dim:
        return None
    from server.adapters.asset_profiles import get_asset_profile

    asset = get_asset_profile(domain)
    labels = {k: b.label for k, b in asset.channels.items()} if asset else {}
    names = tuple(f"{f} ({labels[f]})" if f in labels else f for f in profile.features)
    return names, tuple(float(v) for v in population_mean(domain))


def population_mean(domain: str) -> np.ndarray:
    """Per-feature mean of the profiles the domain model was trained on, in live column order."""
    profile = get_profile(domain)
    if profile.simulated_run_to_failure:
        from server.adapters import pump_degradation

        mean, order = pump_degradation.population_mean(), pump_degradation.FEATURES
    else:
        from server.atlas.pretrain_domain import DOMAIN_FEATURE_MAP, DomainDatasetGenerator

        X, _, _ = DomainDatasetGenerator.get_dataset(domain)
        mean, order = X.reshape(-1, X.shape[-1]).mean(axis=0), DOMAIN_FEATURE_MAP[domain]
    by_name = dict(zip(order, mean))
    return np.asarray([by_name[f] for f in profile.features], dtype=np.float32)

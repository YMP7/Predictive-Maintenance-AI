from dataclasses import dataclass, field
from typing import List, Dict, Optional
import numpy as np
import logging

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

    def explain(self, context: AdaptiveContext, window: Optional[np.ndarray] = None, ace=None) -> ExplanationReport:
        # Check if grounding is explicitly disabled
        if not self.grounding_enabled:
            attributions = []
            top_contributors = []
            attribution_text = ""
            attribution_unavailable_reason = None

            if window is not None and ace is not None:
                attributions, attribution_unavailable_reason = self.calculate_feature_attribution(window, ace, context.predicted_rul)
                top_k = attributions[:3]
                top_contributors = [attr["sensor_name"] for attr in top_k]
                if attributions:
                    top_sensor = attributions[0]
                    if top_sensor["signed_delta"] > 0:
                        attribution_text = f" {top_sensor['sensor_name']} readings are actively driving this prediction toward a shorter RUL estimate."
                    elif top_sensor["signed_delta"] < 0:
                        attribution_text = f" {top_sensor['sensor_name']} readings are supporting a healthier (longer) RUL estimate."
                    else:
                        attribution_text = f" {top_sensor['sensor_name']} is the most influential factor in this prediction."

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
            attributions = []
            attribution_unavailable_reason = None
            if window is not None and ace is not None:
                attributions, attribution_unavailable_reason = self.calculate_feature_attribution(window, ace, context.predicted_rul)
            return ExplanationReport(
                confidence_score=0.0,
                confidence_level="Low",
                primary_justification="No historical similar engines found to ground this prediction.",
                citations=[],
                sensor_attributions=attributions,
                attribution_unavailable_reason=attribution_unavailable_reason
            )

        # 2. Explicit carry-over: citations MUST use true_rul, never predicted_rul
        # We assert this here to prevent circular justification.
        true_ruls = []
        similarities = []
        for n in neighbors:
            if getattr(n, "rul", None) is None:
                if context.domain == "cmapss":
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
                primary_justification="Insufficient historical failure data for confident citation.",
                citations=[]
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
            
        # Feature Attribution
        attributions = []
        top_contributors = []
        attribution_text = ""
        
        attribution_unavailable_reason = None
        
        if window is not None and ace is not None:
            attributions, attribution_unavailable_reason = self.calculate_feature_attribution(window, ace, context.predicted_rul)
            
            # Get top K contributors (e.g., top 3)
            top_k = attributions[:3]
            top_contributors = [attr["sensor_name"] for attr in top_k]
            
            if attributions:
                top_sensor = attributions[0]
                if top_sensor["signed_delta"] > 0:
                    attribution_text = f" {top_sensor['sensor_name']} readings are actively driving this prediction toward a shorter RUL estimate."
                elif top_sensor["signed_delta"] < 0:
                    attribution_text = f" {top_sensor['sensor_name']} readings are supporting a healthier (longer) RUL estimate."
                else:
                    attribution_text = f" {top_sensor['sensor_name']} is the most influential factor in this prediction."
            
        # 3. Construct structured explanation string from a template
        avg_true_rul = float(np.mean(true_ruls_arr))
        primary_justification = (
            f"Prediction is grounded in {len(neighbors)} historically similar engine trajectories "
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

    def calculate_feature_attribution(self, window: np.ndarray, ace, baseline_rul: float) -> List[Dict[str, float]]:
        """
        Calculates Occlusion Sensitivity for the 14 sensors.
        
        GRANULARITY: Occlusion is performed at the coarse, per-sensor level
        (zeroing the entire sensor column across all 30 timesteps at once). This
        matches the project's established per-sensor analysis granularity and is
        far cheaper than cell-by-cell (14 extra forward passes vs 420).
        
        BASELINE VALUE: We use `0.0` to occlude the features. Since the operational
        data is already z-score normalized on the population (via Month 2's fit_normalizer),
        `0.0` intrinsically represents the population-average value. Using the window
        mean would improperly erase within-window degradation trends.
        """
        if window.shape != (30, 14):
            return [], "Feature attribution not yet implemented for domains with feature_dim != 14 (got shape {}).".format(window.shape)
            
        attributions = []
        from server.atlas.world_model import prepare_window
        
        from server.adapters.cmapss_adapter import INFORMATIVE_SENSORS, SENSOR_DESCRIPTIONS
        
        for sensor_idx in range(14):
            # Map the 0-13 index to the actual C-MAPSS sensor string (e.g., 's3')
            # and then to its physical description.
            sensor_code = INFORMATIVE_SENSORS[sensor_idx]
            physical_desc = SENSOR_DESCRIPTIONS.get(sensor_code, sensor_code)
            sensor_name = f"{sensor_code} ({physical_desc})"
            
            # 1. Copy window
            occluded_window = np.copy(window)
            
            # 2. Coarse occlusion: zero out entire column using population mean baseline (0.0)
            occluded_window[:, sensor_idx] = 0.0
            
            # 3. Predict RUL
            occ_tensor = prepare_window(occluded_window, seq_len=30, feature_dim=14)
            occ_out = ace.world_model.predict(occ_tensor)
            occ_rul = occ_out.rul_pred
            
            # 4. Calculate signed delta and magnitude
            # If removing sensor increases RUL, the sensor's real values were dragging RUL DOWN (degradation signal)
            signed_delta = occ_rul - baseline_rul
            magnitude = abs(signed_delta)
            
            attributions.append({
                "sensor_index": sensor_idx,
                "sensor_name": sensor_name,
                "magnitude": float(magnitude),
                "signed_delta": float(signed_delta)
            })
            
        # 5. Sort by magnitude descending
        # To ensure stable sort for ties, sort by sensor_index ascending secondarily
        attributions.sort(key=lambda x: (-x["magnitude"], x["sensor_index"]))
        return attributions, None

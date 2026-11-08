"""Trained fault-type classifier that refines the rule-based FaultDetector label.

The rules in ``FaultDetector`` stay the safety floor: they decide whether a
machine is faulty and how severe it is. This model only names *which* fault,
with a probability per class, and only when it is confident.

Train with ``python -m server.fault_classifier``. The model is a standardised
multinomial logistic regression stored as plain JSON (no pickle), so loading it
cannot execute code and does not depend on the installed sklearn version.
The current training data is the sensor simulator and the file records that in
``training_source``; swap ``build_dataset`` for labelled field data before
claiming field accuracy.
"""
import json
import logging
import math
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

CLASSES: Tuple[str, ...] = (
    "Normal",
    "Bearing Wear",
    "Misalignment",
    "Rotor Imbalance",
    "Overheating",
    "Electrical Fault",
)
SIM_MODE_TO_CLASS: Dict[str, str] = {
    "normal": "Normal",
    "bearing_wear": "Bearing Wear",
    "misalignment": "Misalignment",
    "rotor_imbalance": "Rotor Imbalance",
    "overheating": "Overheating",
    "electrical_fault": "Electrical Fault",
}
# Normalised by each machine's warning thresholds so one model serves machines
# with different ratings; axis shares separate imbalance (x≈y) from misalignment (x≫y).
FEATURES: Tuple[str, ...] = (
    "vib_rms_over_warn",
    "temp_over_warn",
    "current_over_warn",
    "vib_x_share",
    "vib_y_share",
    "vib_z_share",
)
MIN_CONFIDENCE = 0.6

MODEL_PATH = Path(__file__).resolve().parent / "models" / "fault_classifier.json"


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def extract_features(reading: Dict, thresholds: Dict) -> Optional[List[float]]:
    """Return the feature vector, or None when the reading or thresholds can't support one."""
    vib = reading.get("vibration")
    if not isinstance(vib, dict):
        return None
    values = [vib.get("rms"), vib.get("x"), vib.get("y"), vib.get("z"),
              reading.get("temperature"), reading.get("current")]
    warns = [thresholds[k]["warning"] for k in ("vibration", "temperature", "current")]
    if not all(_finite(v) for v in values) or not all(_finite(w) and w > 0 for w in warns):
        return None
    rms, x, y, z, temp, curr = (float(v) for v in values)
    axis_norm = math.sqrt(x * x + y * y + z * z) or 1e-6
    return [
        rms / warns[0],
        temp / warns[1],
        curr / warns[2],
        abs(x) / axis_norm,
        abs(y) / axis_norm,
        abs(z) / axis_norm,
    ]


def arbitrate(rule_fault: str, rules_flagged: bool,
              probabilities: Optional[Dict[str, float]]) -> Tuple[str, str]:
    """Combine the rule verdict and model probabilities into (fault_type, source).

    The model may name a fault only once the rules have flagged an issue, and
    can never clear one; that keeps status and alerting rule-driven. It also
    names faults the rule label misses (e.g. high temperature at normal current).
    """
    if probabilities is None or not rules_flagged:
        return rule_fault, "rules"
    top = max(probabilities, key=probabilities.get)
    if top != "Normal" and probabilities[top] >= MIN_CONFIDENCE:
        return top, "model"
    return rule_fault, "rules"


class FaultClassifier:
    def __init__(self, params: Dict):
        self.classes: List[str] = params["classes"]
        self.mean = np.asarray(params["scaler_mean"], dtype=float)
        self.scale = np.asarray(params["scaler_scale"], dtype=float)
        self.coef = np.asarray(params["coef"], dtype=float)
        self.intercept = np.asarray(params["intercept"], dtype=float)
        self.metadata = params.get("metadata", {})

    @classmethod
    def load(cls, path: Path = MODEL_PATH) -> Optional["FaultClassifier"]:
        """Load the trained model; None (rules-only mode) when absent or unreadable."""
        if not path.exists():
            logger.warning("Fault classifier not found at %s; using rules only", path)
            return None
        try:
            return cls(json.loads(path.read_text()))
        except Exception as exc:
            logger.warning("Fault classifier failed to load (%s); using rules only", exc)
            return None

    def predict_proba(self, reading: Dict, thresholds: Dict) -> Optional[Dict[str, float]]:
        feats = extract_features(reading, thresholds)
        if feats is None:
            return None
        logits = ((np.asarray(feats) - self.mean) / self.scale) @ self.coef.T + self.intercept
        exp = np.exp(logits - logits.max())
        probs = exp / exp.sum()
        out = {label: 0.0 for label in CLASSES}
        out.update({label: round(float(p), 4) for label, p in zip(self.classes, probs)})
        return out


def build_dataset(samples_per_class: int, seed: int) -> Tuple[np.ndarray, np.ndarray]:
    """Labelled readings from the simulator, with random fault severity and progression."""
    from server.ai_agent import FaultDetector
    from server.sensor_simulator import SensorSimulator

    rng = random.Random(seed)
    thresholds = FaultDetector().thresholds_for("__train__")
    X: List[List[float]] = []
    y: List[str] = []
    saved_state = random.getstate()
    random.seed(seed)  # the simulator draws its noise from the global RNG
    try:
        for mode, label in SIM_MODE_TO_CLASS.items():
            for _ in range(samples_per_class):
                sim = SensorSimulator("__train__", mode, severity=rng.uniform(0.3, 1.6))
                sim.degradation_step = rng.randint(10, 200)
                X.append(extract_features(sim.get_sensor_reading(), thresholds))
                y.append(label)
    finally:
        random.setstate(saved_state)
    return np.asarray(X), np.asarray(y)


def train(samples_per_class: int = 1500, seed: int = 42) -> Tuple[Dict, object]:
    """Return (JSON-serialisable params, fitted sklearn pipeline)."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, confusion_matrix
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    X, y = build_dataset(samples_per_class, seed)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, stratify=y, random_state=seed)
    # Logistic regression: same holdout accuracy as gradient boosting here at a
    # fraction of the latency, and its coefficients are directly explainable.
    pipe = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=10)).fit(X_tr, y_tr)
    scaler, lr = pipe.named_steps["standardscaler"], pipe.named_steps["logisticregression"]
    pred = pipe.predict(X_te)
    labels = list(CLASSES)
    params = {
        "classes": [str(c) for c in lr.classes_],
        "features": list(FEATURES),
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "coef": lr.coef_.tolist(),
        "intercept": lr.intercept_.tolist(),
        "metadata": {
            "model": "StandardScaler + multinomial LogisticRegression(C=10)",
            "min_confidence": MIN_CONFIDENCE,
            "training_source": "sensor_simulator (synthetic)",
            "samples_per_class": samples_per_class,
            "seed": seed,
            "holdout_accuracy": round(float(accuracy_score(y_te, pred)), 4),
            "holdout_confusion_matrix": {
                "labels": labels,
                "rows_true_cols_pred": confusion_matrix(y_te, pred, labels=labels).tolist(),
            },
            "trained_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    }
    return params, pipe


if __name__ == "__main__":
    params, _ = train()
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    MODEL_PATH.write_text(json.dumps(params, indent=2) + "\n")
    print(f"holdout accuracy {params['metadata']['holdout_accuracy']} -> {MODEL_PATH}")

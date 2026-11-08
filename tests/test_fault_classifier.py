"""Hybrid fault diagnosis: rules decide fault/severity, the model names the fault."""
import random
from pathlib import Path

import pytest

from server.ai_agent import AIAgent
from server.fault_classifier import CLASSES, FaultClassifier, arbitrate, extract_features
from server.sensor_simulator import SensorSimulator


def _probs(**overrides):
    p = {label: 0.0 for label in CLASSES}
    p.update({k.replace("_", " "): v for k, v in overrides.items()})
    return p


@pytest.mark.parametrize("rule, flagged, probs, expected", [
    ("Normal", False, _probs(Rotor_Imbalance=0.99), ("Normal", "rules")),
    ("Normal", True, _probs(Overheating=0.97), ("Overheating", "model")),
    ("Misalignment", True, _probs(Rotor_Imbalance=0.9), ("Rotor Imbalance", "model")),
    ("Bearing Wear", True, _probs(Normal=0.95), ("Bearing Wear", "rules")),
    ("Overheating", True, _probs(Electrical_Fault=0.5, Overheating=0.4), ("Overheating", "rules")),
    ("Overheating", True, None, ("Overheating", "rules")),
])
def test_arbitration_never_clears_or_raises_a_fault(rule, flagged, probs, expected):
    assert arbitrate(rule, flagged, probs) == expected


def test_reading_without_axes_has_no_features():
    reading = {"vibration": {"rms": 1.0}, "temperature": 50.0, "current": 2.0}
    assert extract_features(reading, {"vibration": {"warning": 1.5},
                                      "temperature": {"warning": 60}, "current": {"warning": 3.5}}) is None


def test_json_model_matches_sklearn_probabilities():
    import numpy as np
    from server.fault_classifier import build_dataset, train

    params, pipe = train(samples_per_class=60, seed=7)
    clf = FaultClassifier(params)
    X, _ = build_dataset(5, seed=8)
    thresholds = {"vibration": {"warning": 1.0}, "temperature": {"warning": 1.0}, "current": {"warning": 1.0}}
    for row in X:
        x_share, y_share, z_share = row[3:]
        # Rebuild a reading whose features equal ``row`` under unit thresholds.
        reading = {"vibration": {"rms": row[0], "x": x_share, "y": y_share, "z": z_share},
                   "temperature": row[1], "current": row[2]}
        ours = clf.predict_proba(reading, thresholds)
        theirs = dict(zip(pipe.classes_, pipe.predict_proba(np.asarray([row]))[0]))
        for label, p in theirs.items():
            assert ours[label] == pytest.approx(p, abs=1e-3)


def test_model_error_keeps_rule_alerts():
    class Broken:
        def predict_proba(self, *_):
            raise RuntimeError("boom")

    agent = AIAgent()
    agent.fault_classifier = Broken()
    random.seed(4)
    result = agent.process_reading(SensorSimulator("M001", "misalignment").get_sensor_reading())
    assert result["fault_type"] == "Misalignment"
    assert result["fault_probabilities"] is None
    assert any(a["type"] == "Fault Detection" for a in result["alerts"])


def test_zero_threshold_yields_no_features():
    reading = {"vibration": {"rms": 1.0, "x": 1.0, "y": 0.0, "z": 0.0}, "temperature": 50.0, "current": 2.0}
    assert extract_features(reading, {"vibration": {"warning": 0},
                                      "temperature": {"warning": 60}, "current": {"warning": 3.5}}) is None


def test_missing_model_falls_back_to_rules(tmp_path: Path):
    assert FaultClassifier.load(tmp_path / "absent.joblib") is None
    agent = AIAgent()
    agent.fault_classifier = None
    random.seed(0)
    result = agent.process_reading(SensorSimulator("M001", "rotor_imbalance").get_sensor_reading())
    assert result["fault_probabilities"] is None
    assert result["diagnosis_source"] == "rules"
    assert result["fault_type"] == result["rule_fault_type"]


@pytest.fixture(scope="module")
def agent():
    a = AIAgent()
    if a.fault_classifier is None:
        pytest.skip("trained model missing; run python -m server.fault_classifier")
    return a


def test_model_separates_imbalance_the_rules_call_misalignment(agent):
    random.seed(1)
    result = agent.process_reading(SensorSimulator("M001", "rotor_imbalance").get_sensor_reading())
    assert result["rule_fault_type"] == "Misalignment"
    assert result["fault_type"] == "Rotor Imbalance"
    assert result["diagnosis_source"] == "model"
    assert "rotor" in result["recommendation"].lower()
    assert [a["fault_type"] for a in result["alerts"] if a["type"] == "Fault Detection"] == ["Rotor Imbalance"]
    assert sum(result["fault_probabilities"].values()) == pytest.approx(1.0, abs=1e-3)


@pytest.mark.parametrize("mode, label", [
    ("misalignment", "Misalignment"),
    ("overheating", "Overheating"),
    ("electrical_fault", "Electrical Fault"),
])
def test_model_agrees_on_existing_faults(agent, mode, label):
    random.seed(2)
    result = agent.process_reading(SensorSimulator("M001", mode).get_sensor_reading())
    assert result["fault_type"] == label


def test_normal_machine_stays_normal(agent):
    random.seed(3)
    result = agent.process_reading(SensorSimulator("M001", "normal").get_sensor_reading())
    assert result["status"] == "Normal"
    assert result["fault_type"] == "Normal"

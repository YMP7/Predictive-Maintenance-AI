import pytest
from server.atlas.adaptive_context import AdaptiveContext, NeighborContext
from server.atlas.explain import ExplanationEngine, ExplanationReport

@pytest.fixture
def engine():
    return ExplanationEngine()

def test_explain_normal(engine):
    context = AdaptiveContext(
        domain="cmapss",
        machine_id="test_unit",
        query_cycle=50,
        predicted_rul=120.0,
        neighbors=[
            NeighborContext(machine_id="u1", cycle=10, rul=125.0, distance=0.8),
            NeighborContext(machine_id="u2", cycle=15, rul=115.0, distance=0.9),
            NeighborContext(machine_id="u3", cycle=20, rul=120.0, distance=0.85)
        ],
        average_neighbor_rul=120.0,
        machine_dna=None
    )
    
    report = engine.explain(context)
    assert isinstance(report, ExplanationReport)
    assert len(report.citations) == 3
    assert "average true RUL of 120.0" in report.primary_justification
    assert "variance of 16.7" in report.primary_justification
    assert report.confidence_score > 0
    assert report.confidence_level in ["High", "Moderate", "Low"]

def test_explain_zero_variance(engine):
    """Test the all-neighbors-identical-RUL edge case where variance = 0."""
    context = AdaptiveContext(
        domain="cmapss",
        machine_id="test_unit",
        query_cycle=50,
        predicted_rul=120.0,
        neighbors=[
            NeighborContext(machine_id="u1", cycle=10, rul=120.0, distance=0.9),
            NeighborContext(machine_id="u2", cycle=15, rul=120.0, distance=0.9)
        ],
        average_neighbor_rul=120.0,
        machine_dna=None
    )
    
    report = engine.explain(context)
    # Variance is 0. 1 / (1 + 0) = 1.0. 
    # Distance is 0.9. Similarity is 1 / 1.9 ≈ 0.5263. Confidence should be ~0.5263.
    assert "variance of 0.0" in report.primary_justification
    assert abs(report.confidence_score - (1.0 / 1.9)) < 1e-3
    assert report.confidence_level == "High"

def test_explain_zero_neighbors(engine):
    """Test edge case with no neighbors."""
    context = AdaptiveContext(
        domain="cmapss",
        machine_id="test_unit",
        query_cycle=50,
        predicted_rul=120.0,
        neighbors=[],
        average_neighbor_rul=0.0,
        machine_dna=None
    )
    
    report = engine.explain(context)
    assert report.confidence_score == 0.0
    assert report.confidence_level == "Low"
    assert "No historical similar engines found" in report.primary_justification
    assert len(report.citations) == 0

def test_explain_missing_true_rul_raises(engine):
    """Ensure ExplanationEngine strictly enforces true_rul and rejects missing RULs."""
    context = AdaptiveContext(
        domain="cmapss",
        machine_id="test_unit",
        query_cycle=50,
        predicted_rul=120.0,
        neighbors=[
            NeighborContext(machine_id="u1", cycle=10, rul=None, distance=0.9)
        ],
        average_neighbor_rul=0.0,
        machine_dna=None
    )
    
    with pytest.raises(ValueError, match="must contain true RUL for citations, not predicted RUL"):
        engine.explain(context)

# ---------------------------------------------------------
# Feature Attribution Tests
# ---------------------------------------------------------

import numpy as np
from server.atlas.world_model import PredictionOutput

class MockWorldModel:
    def predict(self, window_tensor):
        # Determine RUL based on the occlusion of specific features
        # The window tensor is either PyTorch tensor (1, 30, 14) or numpy array
        if hasattr(window_tensor, 'numpy'):
            w = window_tensor.numpy()
        else:
            w = window_tensor
            
        # Baseline RUL is 50.0
        rul = 50.0
        
        # We look at the sum of the first row to determine if a sensor is occluded
        # (Since the test window will be all ones, an occluded sensor column will be all zeros)
        if w.ndim == 3:
            v3 = w[0, 0, 3]
            v7 = w[0, 0, 7]
            v8 = w[0, 0, 8]
        else:
            v3 = w[0, 3]
            v7 = w[0, 7]
            v8 = w[0, 8]
        
        # Sensor 3 is highly sensitive. If it's occluded (0.0), RUL jumps to 80 (delta = +30)
        if abs(v3) < 1e-5:
            rul += 30.0
            
        # Sensors 7 and 8 have tied sensitivity. If occluded, RUL drops to 40 (delta = -10)
        if abs(v7) < 1e-5:
            rul -= 10.0
        if abs(v8) < 1e-5:
            rul -= 10.0
            
        return PredictionOutput(rul_pred=rul, state_vector=np.zeros(32))

class MockACE:
    def __init__(self):
        self.world_model = MockWorldModel()

def test_explain_feature_attribution_synthetic(engine):
    """Test occlusion sensitivity ranks features correctly and stores signed deltas."""
    ace = MockACE()
    
    # Create a dummy window of ones (1.0). 
    # Occlusion will set columns to 0.0.
    window = np.ones((30, 14), dtype=np.float32)
    
    context = AdaptiveContext(
        domain="cmapss",
        machine_id="test_unit",
        query_cycle=50,
        predicted_rul=50.0,  # Baseline RUL
        neighbors=[NeighborContext(machine_id="u1", cycle=10, rul=50.0, distance=0.5)],
        average_neighbor_rul=50.0,
        machine_dna=None
    )
    
    report = engine.explain(context, window=window, ace=ace)
    
    # Sensor 3 removes -> RUL=80. Signed delta = 80 - 50 = +30. Magnitude = 30.
    # Sensor 7 removes -> RUL=40. Signed delta = 40 - 50 = -10. Magnitude = 10.
    # Sensor 8 removes -> RUL=40. Signed delta = 40 - 50 = -10. Magnitude = 10.
    
    attrs = report.sensor_attributions
    assert len(attrs) == 14
    
    # Top contributor should be Sensor 3
    assert attrs[0]["sensor_index"] == 3
    assert attrs[0]["magnitude"] == 30.0
    assert attrs[0]["signed_delta"] == 30.0
    
    # Verify the UI summary list has top K
    assert "s7 (P50 (Total pressure at LPT outlet))" in report.top_contributors
    
    # Verify the justification string incorporates the active degradation signal
    assert "s7 (P50 (Total pressure at LPT outlet)) readings are actively driving this prediction toward a shorter RUL estimate" in report.primary_justification
    
def test_explain_feature_attribution_tie_breaker(engine):
    """Test that tied magnitudes sort deterministically by sensor index."""
    ace = MockACE()
    window = np.ones((30, 14), dtype=np.float32)
    context = AdaptiveContext(
        domain="cmapss",
        machine_id="test_unit",
        query_cycle=50,
        predicted_rul=50.0,
        neighbors=[NeighborContext(machine_id="u1", cycle=10, rul=50.0, distance=0.5)],
        average_neighbor_rul=50.0,
        machine_dna=None
    )
    
    report = engine.explain(context, window=window, ace=ace)
    attrs = report.sensor_attributions
    
    # Ranks 0 is Sensor 3 (magnitude 30).
    # Ranks 1 and 2 should be Sensor 7 and Sensor 8 (magnitude 10).
    # Because 7 < 8, Sensor 7 should appear before Sensor 8 in the sorted list.
    assert attrs[1]["sensor_index"] == 7
    assert attrs[1]["magnitude"] == 10.0
    
    assert attrs[2]["sensor_index"] == 8
    assert attrs[2]["magnitude"] == 10.0

def test_explain_near_failure_high_confidence(engine):
    """Phase 1 verification: A near-zero distance MUST produce high confidence."""
    context = AdaptiveContext(
        domain="cmapss",
        machine_id="test_unit",
        query_cycle=50,
        predicted_rul=10.0,
        neighbors=[
            NeighborContext(machine_id="u1", cycle=100, rul=10.0, distance=0.0001),
            NeighborContext(machine_id="u2", cycle=105, rul=10.0, distance=0.0002)
        ],
        average_neighbor_rul=10.0,
        machine_dna=None
    )
    
    report = engine.explain(context)
    
    # Variance is 0. 1 / (1+0) = 1.0.
    # Average distance = 0.00015. Similarity ≈ 1 / 1.00015 ≈ 0.99985
    # So confidence score should be very close to 1.0 (highly confident)
    assert report.confidence_score > 0.99
    assert report.confidence_level == "High"
    print(f"\n[Test] Near-failure distance=0.0001 -> Confidence: {report.confidence_score:.4f}")

def test_explain_feature_attribution_naming_convention(engine):
    """Test that sensor_name matches the canonical C-MAPSS naming convention (s[n])."""
    window = np.zeros((30, 14), dtype=np.float32)
    mock_ace = MockACE()
    
    context = AdaptiveContext(
        domain="cmapss",
        machine_id="test_unit",
        query_cycle=50,
        predicted_rul=50.0,
        neighbors=[NeighborContext(machine_id="u1", cycle=10, rul=50.0, distance=0.5)],
        average_neighbor_rul=50.0,
        machine_dna=None
    )
    
    report = engine.explain(context, window=window, ace=mock_ace)
    
    # Check that all sensor_names start with s[number]
    import re
    pattern = re.compile(r"^s\d+ \(")
    
    for attr in report.sensor_attributions:
        assert pattern.match(attr["sensor_name"]), f"sensor_name '{attr['sensor_name']}' does not match canonical convention"
        
    # Spot check specific elements
    # index 0 -> s2
    assert report.sensor_attributions[0]["sensor_name"].startswith("s2 (")
    # index 1 -> s3
    assert report.sensor_attributions[1]["sensor_name"].startswith("s3 (")
    # index 13 -> s21
    assert report.sensor_attributions[13]["sensor_name"].startswith("s21 (")

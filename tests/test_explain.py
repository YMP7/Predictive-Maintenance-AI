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
    # Similarity is 0.9. Confidence should be ~0.9.
    assert "variance of 0.0" in report.primary_justification
    assert abs(report.confidence_score - 0.9) < 1e-5
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

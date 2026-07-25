import pytest
import numpy as np

from server.atlas.simulation import SimulationEngine, MaintenanceAction
from server.atlas.decision import DecisionGraph
from server.atlas.explain import ExplanationReport

def test_simulation_engine_basic_outputs():
    """Verify that all 4 actions produce valid SimulationResults."""
    engine = SimulationEngine(num_samples=1000)
    
    # Very safe RUL, low variance
    predicted_rul = 100.0
    variance = 1.0
    
    results = engine.simulate_actions(predicted_rul, variance)
    
    assert len(results) == 4
    action_names = [r.action for r in results]
    assert MaintenanceAction.CONTINUE_OPERATION in action_names
    assert MaintenanceAction.SCHEDULE_MAINTENANCE_SOON in action_names
    assert MaintenanceAction.SCHEDULE_MAINTENANCE_NOW in action_names
    assert MaintenanceAction.REPLACE_IMMEDIATELY in action_names
    
    # For a safe RUL of 100.0 with std=1.0, failures should be exactly 0
    continue_op = next(r for r in results if r.action == MaintenanceAction.CONTINUE_OPERATION)
    assert continue_op.p_failure_before_action == 0.0
    assert continue_op.expected_cost == 0.0

def test_simulation_engine_high_risk():
    """CONTINUE_OPERATION cost correctly spikes when predicted_rul is very low."""
    engine = SimulationEngine(num_samples=1000)
    
    # Dangerous RUL (e.g. 0.0) -> high failure probability
    predicted_rul = 0.0
    variance = 0.1
    
    results = engine.simulate_actions(predicted_rul, variance)
    continue_op = next(r for r in results if r.action == MaintenanceAction.CONTINUE_OPERATION)
    
    # RUL is clipped to [0, cap], so all samples will be >= 0.
    # However, any sample <= 0 is a failure. Since loc=0.0 and it's clipped to 0, 
    # approx 50% of the normal distribution is <= 0 (which gets clipped to exactly 0).
    # Wait, actually anything <= 0 is a failure. Since we clip to 0, all the negative 
    # samples become exactly 0. Thus they all fail.
    # So p_failure should be approx 0.5. Let's just assert it's > 0.4.
    assert continue_op.p_failure_before_action > 0.4
    assert continue_op.expected_cost > 400.0  # Since penalty is 1000

def test_simulation_engine_determinism():
    """Ranking is stable/deterministic given a fixed random seed."""
    np.random.seed(42)
    engine = SimulationEngine(num_samples=1000)
    res1 = engine.simulate_actions(10.0, 5.0)
    
    np.random.seed(42)
    engine2 = SimulationEngine(num_samples=1000)
    res2 = engine2.simulate_actions(10.0, 5.0)
    
    for r1, r2 in zip(res1, res2):
        assert r1.expected_cost == r2.expected_cost
        assert r1.p_failure_before_action == r2.p_failure_before_action

def test_decision_graph_confidence_reuse():
    """confidence field is verified to come from ExplanationEngine, not an independent calculation."""
    sim_engine = SimulationEngine(num_samples=10)
    results = sim_engine.simulate_actions(50.0, 10.0)
    
    # Mock explanation
    explanation = ExplanationReport(
        confidence_score=0.9999,
        confidence_level="High",
        primary_justification="Test",
        citations=[],
        note="",
        sensor_attributions=[],
        top_contributors=[]
    )
    
    graph = DecisionGraph()
    decision = graph.decide(results, explanation, predicted_rul=50.0, neighbor_variance=10.0)
    
    assert decision.confidence == explanation.confidence_score
    assert decision.confidence == 0.9999

def test_decision_graph_tie_breaker():
    """Tie-break case: two actions with identical expected cost — confirm stable ordering."""
    from server.atlas.simulation import SimulationResult
    
    # B and A have identical expected_cost (100.0)
    # But A has lower p_failure (0.01 vs 0.05), so A should be favored (ranked higher/first).
    results = [
        SimulationResult("B_ACTION", 100.0, 5.0, 0.05),
        SimulationResult("A_ACTION", 100.0, 5.0, 0.01),
        SimulationResult("C_ACTION", 200.0, 5.0, 0.0)
    ]
    
    explanation = ExplanationReport(
        confidence_score=0.5,
        confidence_level="Medium",
        primary_justification="Test",
        citations=[],
        note="",
        sensor_attributions=[],
        top_contributors=[]
    )
    
    graph = DecisionGraph()
    decision = graph.decide(results, explanation, predicted_rul=50.0, neighbor_variance=10.0)
    
    # A_ACTION should beat B_ACTION because of lower p_failure_before_action
    assert decision.recommended_action == "A_ACTION"
    assert decision.ranked_actions[0].action == "A_ACTION"
    assert decision.ranked_actions[1].action == "B_ACTION"

def test_decision_graph_urgency_drives_ranking():
    """Near-failure input -> top-ranked action must not be SCHEDULE_MAINTENANCE_SOON."""
    sim_engine = SimulationEngine(num_samples=1000)
    # Near failure: RUL=2, Variance=16
    results = sim_engine.simulate_actions(2.0, 16.0)
    
    explanation = ExplanationReport(
        confidence_score=0.9, confidence_level="High", primary_justification="", citations=[], note="", sensor_attributions=[], top_contributors=[]
    )
    
    graph = DecisionGraph()
    decision = graph.decide(results, explanation, predicted_rul=2.0, neighbor_variance=16.0)
    
    # SCHEDULE_MAINTENANCE_SOON has a lead time of 10. With RUL=2, most samples fail before lead time, making it very expensive.
    # Therefore, it should definitely NOT be the top recommended action.
    assert decision.recommended_action != MaintenanceAction.SCHEDULE_MAINTENANCE_SOON
    # It should recommend REPLACE_IMMEDIATELY or SCHEDULE_MAINTENANCE_NOW (lead time 0 or 3)
    assert decision.recommended_action in [MaintenanceAction.REPLACE_IMMEDIATELY, MaintenanceAction.SCHEDULE_MAINTENANCE_NOW]



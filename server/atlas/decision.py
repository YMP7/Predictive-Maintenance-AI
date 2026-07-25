"""
Month 5 Week 3: Decision Graph

This module evaluates SimulationEngine results to rank maintenance actions by expected cost,
while computing higher-level metrics (Risk, Impact, Urgency) and strictly reusing the 
Explainability Engine's confidence score to prevent metric drift.
"""

from dataclasses import dataclass
from typing import List
import numpy as np

from server.atlas.simulation import SimulationResult
from server.atlas.explain import ExplanationReport

@dataclass
class DecisionRecommendation:
    recommended_action: str
    ranked_actions: List[SimulationResult]   # all 4, sorted by expected_cost ascending
    confidence: float                        # PULLED FROM ExplanationEngine — not recomputed
    risk: float                              # derived from p_failure_before_action + cost_std
    impact: float                            # magnitude of cost difference between top and worst action
    urgency: float                           # inverse function of predicted_rul + neighbor_rul_variance
    explanation: ExplanationReport           # embeds Month 4's full citation/attribution output directly

class DecisionGraph:
    def __init__(self):
        pass
        
    def decide(
        self, 
        simulation_results: List[SimulationResult], 
        explanation: ExplanationReport,
        predicted_rul: float,
        neighbor_variance: float
    ) -> DecisionRecommendation:
        """
        Ranks simulated actions and derives higher-level decision metrics.
        Strictly reuses the ExplanationReport's confidence score.
        """
        
        # 1. Rank actions by expected cost (ascending)
        # Tie-break deterministic sort: 
        #   - expected_cost (primary)
        #   - p_failure_before_action (secondary, favor safer actions in a tie)
        #   - cost_std (tertiary, favor lower uncertainty)
        #   - action name (quaternary, deterministic fallback)
        ranked = sorted(
            simulation_results, 
            key=lambda x: (x.expected_cost, x.p_failure_before_action, x.cost_std, x.action)
        )
        
        best_action = ranked[0]
        worst_action = ranked[-1]
        
        # 2. Re-use Confidence
        confidence = explanation.confidence_score
        
        # 3. Compute Risk (derived from recommended action's p_failure and std)
        # We normalize cost_std by 1000.0 just to keep risk roughly in [0, 1] range for UI
        risk = best_action.p_failure_before_action + (best_action.cost_std / 1000.0)
        
        # 4. Compute Impact (cost difference between doing the best thing vs the worst thing)
        impact = worst_action.expected_cost - best_action.expected_cost
        
        # 5. Compute Urgency (inverse function of predicted_rul + neighbor_variance)
        # Smaller RUL / smaller variance = higher urgency to act.
        # Adding 1.0 to prevent division by zero.
        urgency = 100.0 / (predicted_rul + neighbor_variance + 1.0)
        
        return DecisionRecommendation(
            recommended_action=best_action.action,
            ranked_actions=ranked,
            confidence=float(confidence),
            risk=float(risk),
            impact=float(impact),
            urgency=float(urgency),
            explanation=explanation
        )

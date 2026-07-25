"""
Month 5 Week 2: Simulation Engine

This module implements Uncertainty Propagation (Monte Carlo sampling) for decision making.
It translates RUL predictive uncertainty (derived from AMKB neighbor-variance) into a
distribution of possible future states to evaluate discrete maintenance actions.

NOTE ON COST PARAMETERS:
Cost parameters below are illustrative and not fitted to real financial data — no such data 
exists for this dataset. They are chosen to produce sensible relative orderings between actions 
(e.g., unplanned failure is costlier than early maintenance) for demonstration and evaluation 
purposes. Real deployment would require site-specific cost calibration.

NOTE ON UNCERTAINTY:
Uncertainty is approximated as Gaussian around the point estimate, scaled by empirical 
neighbor variance; this is a simplification and a candidate for refinement via true 
predictive-distribution modeling in future work.

OUT OF SCOPE ACTIONS (Future Work):
Partial repairs, component-specific interventions, alternate operating-mode recommendations.
"""

from dataclasses import dataclass
from typing import List
import numpy as np

# 1. Action Space (frozen, 4 actions)
class MaintenanceAction:
    CONTINUE_OPERATION = "CONTINUE_OPERATION"
    SCHEDULE_MAINTENANCE_SOON = "SCHEDULE_MAINTENANCE_SOON"
    SCHEDULE_MAINTENANCE_NOW = "SCHEDULE_MAINTENANCE_NOW"
    REPLACE_IMMEDIATELY = "REPLACE_IMMEDIATELY"
    
    @classmethod
    def all_actions(cls) -> List[str]:
        return [
            cls.CONTINUE_OPERATION,
            cls.SCHEDULE_MAINTENANCE_SOON,
            cls.SCHEDULE_MAINTENANCE_NOW,
            cls.REPLACE_IMMEDIATELY
        ]

# 2. Illustrative cost parameters
COST_PARAMS = {
    "unplanned_failure_penalty": 1000.0,   # cost if RUL hits 0 before any action taken
    "maintenance_base_cost": 50.0,          # fixed cost of any scheduled maintenance event
    "downtime_cost_per_cycle": 5.0,         # cost of production downtime during maintenance
    "urgency_multiplier": {                 # how much action lead-time affects total cost
        "CONTINUE_OPERATION": 0.0,
        "SCHEDULE_MAINTENANCE_SOON": 1.0,
        "SCHEDULE_MAINTENANCE_NOW": 1.5,    # more disruptive to reschedule urgently
        "REPLACE_IMMEDIATELY": 2.0,
    },
}

ACTION_LEAD_TIME = {
    # Assumed cycles until the action's effect is realized (illustrative assumption)
    # For CONTINUE_OPERATION, this represents the "risk exposure horizon" (e.g. 30 cycles until next possible review).
    MaintenanceAction.CONTINUE_OPERATION: 30,       
    MaintenanceAction.SCHEDULE_MAINTENANCE_SOON: 10,
    MaintenanceAction.SCHEDULE_MAINTENANCE_NOW: 3,
    MaintenanceAction.REPLACE_IMMEDIATELY: 0,       # effectively removes ongoing risk immediately
}

def compute_action_cost(sampled_rul: float, action: str) -> float:
    """
    For each Monte Carlo sample of RUL, compute the cost of a given action.
    Failure risk applies to every action with nonzero lead time, not just CONTINUE_OPERATION.
    If the unit fails before the action can be executed, it incurs the unplanned failure penalty.
    """
    lead_time = ACTION_LEAD_TIME[action]
    failed_before_action = sampled_rul <= lead_time
    
    if failed_before_action:
        return COST_PARAMS["unplanned_failure_penalty"]
        
    if action == MaintenanceAction.CONTINUE_OPERATION:
        return 0.0
    
    base = COST_PARAMS["maintenance_base_cost"]
    downtime = COST_PARAMS["downtime_cost_per_cycle"] * COST_PARAMS["urgency_multiplier"][action]
    return base + downtime

@dataclass
class SimulationResult:
    action: str
    expected_cost: float
    cost_std: float          # spread across the 1000 samples — a second, independent uncertainty signal
    p_failure_before_action: float  # fraction of samples where RUL <= 0 before the action's assumed lead time

class SimulationEngine:
    def __init__(self, num_samples: int = 1000):
        self.num_samples = num_samples
        self.rul_cap = 125.0
        
    def simulate_actions(self, predicted_rul: float, neighbor_variance: float) -> List[SimulationResult]:
        """
        Runs Monte Carlo sampling over the RUL prediction's uncertainty.
        Returns expected costs and risk profiles for all discrete actions.
        """
        # If variance is 0, std is 0. Avoid completely degenerate distributions by giving it a tiny jitter.
        std_dev = np.sqrt(neighbor_variance)
        if std_dev < 1e-3:
            std_dev = 1e-3
            
        # Draw N=1000 samples
        sampled_ruls = np.random.normal(loc=predicted_rul, scale=std_dev, size=self.num_samples)
        
        # Clip strictly to [0, rul_cap] matching our model bounds
        sampled_ruls = np.clip(sampled_ruls, 0.0, self.rul_cap)
        
        results = []
        for action in MaintenanceAction.all_actions():
            action_costs = []
            failures = 0
            
            for rul_val in sampled_ruls:
                cost = compute_action_cost(rul_val, action)
                action_costs.append(cost)
                
                # Any sample hitting <= lead_time means failure
                lead_time = ACTION_LEAD_TIME[action]
                if rul_val <= lead_time:
                    failures += 1
            
            action_costs_arr = np.array(action_costs)
            results.append(SimulationResult(
                action=action,
                expected_cost=float(np.mean(action_costs_arr)),
                cost_std=float(np.std(action_costs_arr)),
                p_failure_before_action=float(failures / self.num_samples)
            ))
            
        return results

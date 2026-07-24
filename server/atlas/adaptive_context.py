import json
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import numpy as np

from .amkb import AMKB
from .machine_dna import MachineDNAEngine
from .world_model import WorldModel, prepare_window

@dataclass
class NeighborContext:
    machine_id: str
    cycle: int
    rul: float
    distance: float

@dataclass
class AdaptiveContext:
    domain: str
    machine_id: str
    query_cycle: int
    predicted_rul: float
    neighbors: List[NeighborContext]
    average_neighbor_rul: float
    machine_dna: Optional[List[float]]

class AdaptiveContextEngine:
    def __init__(self, amkb: AMKB, dna_engine: MachineDNAEngine, world_model: WorldModel):
        self.amkb = amkb
        self.dna_engine = dna_engine
        self.world_model = world_model

    def build_context(
        self,
        domain: str,
        machine_id: str,
        current_cycle: int,
        current_window: np.ndarray,
        k: int = 10
    ) -> AdaptiveContext:
        """
        Builds the adaptive context for a given operational window.
        - Validates window is exactly shape (30, 14)
        - Runs the World Model to get `state_vector` and `predicted_rul`.
        - Queries AMKB for similar historical states, applying self-match exclusion.
        - Fetches Machine DNA.
        """
        # 1. Validate shape
        if current_window.shape != (30, 14):
            raise ValueError(f"Expected window shape (30, 14), got {current_window.shape}")

        # 2. Run World Model
        tensor_window = prepare_window(current_window, seq_len=30, feature_dim=14)
        out = self.world_model.predict(tensor_window)
        pred_rul = out.rul_pred
        sv = out.state_vector

        # 3. Query AMKB
        # Request k+1 to allow filtering out self-matches
        results = self.amkb.retrieve_similar(sv, k=k+1, domain=domain)

        # 4. Filter self-matches
        neighbors = []
        for r in results:
            if r.machine_id == machine_id and r.cycle == current_cycle:
                continue
            
            if r.true_rul is not None:
                dist = r.similarity if r.similarity is not None else 0.0
                neighbors.append(NeighborContext(
                    machine_id=r.machine_id,
                    cycle=r.cycle,
                    rul=r.true_rul,
                    distance=dist
                ))
            
            if len(neighbors) == k:
                break

        # 5. Fetch Machine DNA
        try:
            dna = self.dna_engine.get_dna(domain, machine_id)
        except Exception as e:
            import traceback
            traceback.print_exc()
            dna = None

        # 6. Aggregate stats
        if neighbors:
            avg_rul = sum(n.rul for n in neighbors) / len(neighbors)
        else:
            avg_rul = 0.0

        return AdaptiveContext(
            domain=domain,
            machine_id=machine_id,
            query_cycle=current_cycle,
            predicted_rul=float(pred_rul),
            neighbors=neighbors,
            average_neighbor_rul=float(avg_rul),
            machine_dna=dna.tolist() if dna is not None else None
        )

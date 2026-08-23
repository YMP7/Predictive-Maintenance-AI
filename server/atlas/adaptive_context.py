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
    def __init__(
        self,
        amkb: AMKB,
        dna_engine: MachineDNAEngine,
        world_model: Optional[WorldModel] = None,
        domain_models: Optional[Dict[str, WorldModel]] = None,
    ):
        self.amkb = amkb
        self.dna_engine = dna_engine
        self.world_model = world_model
        self.domain_models: Dict[str, WorldModel] = dict(domain_models) if domain_models else {}

    def get_world_model(self, domain: str, feature_dim: int) -> Optional[WorldModel]:
        """Resolves the appropriate WorldModel for a specific domain and feature dimensionality."""
        # 1. Explicit domain models registry
        if domain in self.domain_models:
            m = self.domain_models[domain]
            if m is not None and getattr(m, "config", None) is not None and m.config.feature_dim == feature_dim:
                return m

        # 2. Check default world_model
        if (
            self.world_model is not None
            and getattr(self.world_model, "config", None) is not None
            and self.world_model.config.feature_dim == feature_dim
        ):
            return self.world_model

        # 3. Dynamic disk lookup from data/models/
        try:
            from pathlib import Path
            models_dir = Path(__file__).parent.parent.parent / "data" / "models"
            candidate = models_dir / f"{domain}_world_model.pt"
            if candidate.exists():
                loaded = WorldModel.load(str(candidate))
                if getattr(loaded, "config", None) is not None and loaded.config.feature_dim == feature_dim:
                    self.domain_models[domain] = loaded
                    return loaded
        except Exception:
            pass

        return None

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
        - Validates 2D shape (seq_len, feature_dim).
        - Runs the domain-specific World Model to get `state_vector` and `predicted_rul`.
        - Queries AMKB for similar historical states, applying self-match exclusion.
        - Fetches Machine DNA.
        """
        # 1. Validate 2D temporal window
        if len(current_window.shape) != 2 or current_window.shape[0] < 1:
            raise ValueError(f"Expected 2D window array (seq_len, feature_dim), got {current_window.shape}")

        seq_len, feature_dim = current_window.shape

        # 2. Run World Model if available for domain and feature_dim, otherwise fallback
        model = self.get_world_model(domain, feature_dim)
        if model is not None:
            tensor_window = prepare_window(current_window, seq_len=seq_len, feature_dim=feature_dim)
            out = model.predict(tensor_window)
            pred_rul = float(out.rul_pred)
            sv = out.state_vector
        else:
            # Fallback for domains without a matching trained WorldModel
            pred_rul = 30.0
            sv = np.zeros(32, dtype=np.float32)

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

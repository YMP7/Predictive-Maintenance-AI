import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import numpy as np
from pathlib import Path

from server.atlas.amkb import AMKB
from server.atlas.machine_dna import MachineDNAEngine
from server.atlas.world_model import WorldModel
from server.atlas.adaptive_context import AdaptiveContextEngine, AdaptiveContext
from server.atlas.explain import ExplanationEngine
from server.atlas.simulation import SimulationEngine
from server.atlas.decision import DecisionGraph
from server.atlas.learning_engine import LearningEngine, LearningResult
import dataclasses

app = FastAPI(title="ATLAS Adaptive Context API")

MODELS_DIR = Path(__file__).parent.parent / "data" / "models"

# Initialize shared components
_amkb: Optional[AMKB] = None
_dna_engine: Optional[MachineDNAEngine] = None
_world_model: Optional[WorldModel] = None
_ace: Optional[AdaptiveContextEngine] = None
_explain_engine: Optional[ExplanationEngine] = None
_simulation_engine: Optional[SimulationEngine] = None
_decision_graph: Optional[DecisionGraph] = None
_learning_engine: Optional[LearningEngine] = None

@app.on_event("startup")
def startup_event():
    global _amkb, _dna_engine, _world_model, _ace, _explain_engine
    global _simulation_engine, _decision_graph, _learning_engine
    
    # 1. Connect AMKB (Vector DB)
    _amkb = AMKB()
    
    # 2. Init Machine DNA
    _dna_engine = MachineDNAEngine()
    
    # 3. Load World Models for all available domains
    domain_models = {}
    for domain, filename in [
        ("cmapss", "best_model.pt"),
        ("laptop", "laptop_world_model.pt"),
        ("mobile", "mobile_world_model.pt"),
        ("server", "server_world_model.pt"),
    ]:
        p = MODELS_DIR / filename
        if not p.exists() and domain == "cmapss":
            p = MODELS_DIR / "cmapss_world_model.pt"
        if p.exists():
            try:
                domain_models[domain] = WorldModel.load(p)
            except Exception as e:
                print(f"Warning: could not load {domain} model from {p}: {e}")

    _world_model = domain_models.get("cmapss")
    if _world_model is None:
        raise RuntimeError(f"Primary C-MAPSS WorldModel not found in {MODELS_DIR}")
        
    _ace = AdaptiveContextEngine(_amkb, _dna_engine, _world_model, domain_models=domain_models)
    _explain_engine = ExplanationEngine()
    _simulation_engine = SimulationEngine()
    _decision_graph = DecisionGraph()
    _learning_engine = LearningEngine()

@app.on_event("shutdown")
def shutdown_event():
    global _amkb
    if _amkb is not None:
        try:
            _amkb._get_pool().close()
        except Exception:
            pass

def _validate_window(window: List[List[float]]) -> np.ndarray:
    if not window or len(window) == 0:
        raise HTTPException(status_code=400, detail="Window cannot be empty.")
    expected_cols = len(window[0])
    if expected_cols == 0:
        raise HTTPException(status_code=400, detail="Window rows cannot be empty.")
    for idx, row in enumerate(window):
        if len(row) != expected_cols:
            raise HTTPException(
                status_code=400,
                detail=f"Inconsistent window dimensions at step {idx}: expected {expected_cols}, got {len(row)}."
            )
    return np.array(window, dtype=np.float32)

class ContextQueryRequest(BaseModel):
    domain: str
    machine_id: str
    cycle: int
    window: List[List[float]] = Field(
        ...,
        description="A 2D array (seq_len x feature_dim) of float values representing the operational window."
    )
    k: int = Field(10, description="Number of neighbors to retrieve")

@app.post("/api/context", response_model=AdaptiveContext)
def get_context(req: ContextQueryRequest):
    if _ace is None:
        raise HTTPException(status_code=503, detail="ACE not initialized")
    
    np_window = _validate_window(req.window)
    
    try:
        context = _ace.build_context(
            domain=req.domain,
            machine_id=req.machine_id,
            current_cycle=req.cycle,
            current_window=np_window,
            k=req.k
        )
        return context
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/explain")
def post_explain(req: ContextQueryRequest):
    if _ace is None or _explain_engine is None:
        raise HTTPException(status_code=503, detail="Atlas engines not initialized")
        
    try:
        np_window = _validate_window(req.window)
        context = _ace.build_context(
            domain=req.domain,
            machine_id=req.machine_id,
            current_cycle=req.cycle,
            current_window=np_window,
            k=req.k
        )
        report = _explain_engine.explain(context, window=np_window, ace=_ace)
        return report.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/decide")
def post_decide(req: ContextQueryRequest):
    if _ace is None or _explain_engine is None or _simulation_engine is None or _decision_graph is None:
        raise HTTPException(status_code=503, detail="Atlas engines not initialized")
        
    try:
        np_window = _validate_window(req.window)
        
        # 1. Get Context (including predicted RUL and neighbors)
        context = _ace.build_context(
            domain=req.domain,
            machine_id=req.machine_id,
            current_cycle=req.cycle,
            current_window=np_window,
            k=req.k
        )
        
        # 2. Compute Explainability
        explanation = _explain_engine.explain(context, window=np_window, ace=_ace)
        
        # 3. Calculate Variance for Uncertainty
        if not context.neighbors:
            variance = 0.0
        else:
            variance = float(np.var([n.rul for n in context.neighbors]))
            
        # 4. Simulate Action Outcomes
        sim_results = _simulation_engine.simulate_actions(
            predicted_rul=context.predicted_rul,
            neighbor_variance=variance
        )
        
        # 5. Build Decision Graph Recommendation
        decision = _decision_graph.decide(
            simulation_results=sim_results,
            explanation=explanation,
            predicted_rul=context.predicted_rul,
            neighbor_variance=variance
        )
        
        return dataclasses.asdict(decision)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


class RetrainRequest(BaseModel):
    domain: str = "cmapss"
    trigger_reason: str = "manual"
    epochs: int = 5
    batch_size: int = 128
    lr: float = 1e-3


@app.post("/api/learn/retrain")
def retrain_model(req: RetrainRequest):
    """Triggers a controlled batch retraining run with Candidate-vs-Active validation gating."""
    if _learning_engine is None:
        raise HTTPException(status_code=503, detail="Learning Engine not initialized")

    try:
        result = _learning_engine.retrain_domain(
            domain=req.domain,
            trigger_reason=req.trigger_reason,
            epochs=req.epochs,
            batch_size=req.batch_size,
            lr=req.lr,
        )
        return result.to_dict()
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/learn/history")
def get_learning_history(domain: str = "cmapss", limit: int = 20):
    """Fetches learning event audit logs from the database."""
    if _learning_engine is None:
        raise HTTPException(status_code=503, detail="Learning Engine not initialized")

    try:
        history = _learning_engine.get_learning_history(domain=domain, limit=limit)
        return {"domain": domain, "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dna/{domain}/{machine_id}")
def get_dna(domain: str, machine_id: str):
    if _dna_engine is None:
        raise HTTPException(status_code=503, detail="DNA Engine not initialized")
        
    try:
        dna = _dna_engine.get_dna(domain, machine_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
        
    if dna is None:
        raise HTTPException(status_code=404, detail="Machine DNA not found")
        
    return {"domain": domain, "machine_id": machine_id, "dna": dna.tolist()}

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

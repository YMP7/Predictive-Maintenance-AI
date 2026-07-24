import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import numpy as np

from server.atlas.amkb import AMKB
from server.atlas.machine_dna import MachineDNAEngine
from server.atlas.world_model import WorldModel
from server.atlas.adaptive_context import AdaptiveContextEngine, AdaptiveContext

app = FastAPI(title="ATLAS Adaptive Context API")

# Initialize shared components
_amkb: Optional[AMKB] = None
_dna_engine: Optional[MachineDNAEngine] = None
_world_model: Optional[WorldModel] = None
_ace: Optional[AdaptiveContextEngine] = None

@app.on_event("startup")
def startup_event():
    global _amkb, _dna_engine, _world_model, _ace
    _amkb = AMKB()
    _dna_engine = MachineDNAEngine(pool=_amkb._get_pool())
    
    # Load world model
    model_path = os.path.join(os.path.dirname(__file__), "..", "data", "models", "cmapss_world_model.pt")
    if not os.path.exists(model_path):
        raise RuntimeError(f"WorldModel not found at {model_path}")
    
    _world_model = WorldModel.load(model_path)
    _ace = AdaptiveContextEngine(_amkb, _dna_engine, _world_model)

class ContextQueryRequest(BaseModel):
    domain: str
    machine_id: str
    cycle: int
    window: List[List[float]] = Field(
        ...,
        description="A 30x14 array of float values representing the current operational window."
    )
    k: int = Field(10, description="Number of neighbors to retrieve")

@app.post("/api/context", response_model=AdaptiveContext)
def get_context(req: ContextQueryRequest):
    if _ace is None:
        raise HTTPException(status_code=503, detail="ACE not initialized")
    
    # Validate exactly 30x14
    if len(req.window) != 30:
        raise HTTPException(status_code=400, detail="Window must have exactly 30 time steps.")
    for row in req.window:
        if len(row) != 14:
            raise HTTPException(status_code=400, detail="Each time step must have exactly 14 sensors.")
            
    np_window = np.array(req.window, dtype=np.float32)
    
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
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

@app.get("/api/dna/{domain}/{machine_id}")
def get_dna(domain: str, machine_id: str):
    if _dna_engine is None:
        raise HTTPException(status_code=503, detail="DNA Engine not initialized")
        
    dna = _dna_engine.get_dna(domain, machine_id)
    if dna is None:
        raise HTTPException(status_code=404, detail="Machine DNA not found")
        
    return {"domain": domain, "machine_id": machine_id, "dna": dna.tolist()}

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

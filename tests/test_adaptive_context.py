import os
import pytest
import numpy as np
from dotenv import load_dotenv

load_dotenv()

from server.atlas.amkb import AMKB
from server.atlas.machine_dna import MachineDNAEngine
from server.atlas.world_model import WorldModel
from server.atlas.adaptive_context import AdaptiveContextEngine


def _is_db_available() -> bool:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        return False
    try:
        import psycopg
        with psycopg.connect(db_url, connect_timeout=1):
            pass
        return True
    except Exception:
        return False


DB_AVAILABLE = _is_db_available()
pytestmark = pytest.mark.skipif(not DB_AVAILABLE, reason="DATABASE_URL not set or database unreachable")

@pytest.fixture
def amkb():
    return AMKB()

@pytest.fixture
def dna_engine(amkb):
    return MachineDNAEngine(pool=amkb._get_pool())

@pytest.fixture
def world_model():
    model_path = __import__("pathlib").Path("data/models/cmapss_world_model.pt")
    if not model_path.exists():
        pytest.skip("Trained WorldModel not found")
    return WorldModel.load(model_path)

@pytest.fixture
def ace(amkb, dna_engine, world_model):
    return AdaptiveContextEngine(amkb, dna_engine, world_model)

def test_build_context_healthy(ace, amkb):
    # Ensure DB is populated
    count = amkb.count(domain="cmapss")
    if count < 1000:
        pytest.skip("AMKB not populated")
        
    # Get a real healthy window from the DB (we need the raw sensors)
    pool = amkb._get_pool()
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT machine_id, cycle, metadata->'sensors', rul_cycles FROM amkb_experiences "
            "WHERE domain = 'cmapss' AND rul_cycles >= 100 LIMIT 1"
        ).fetchone()
        
    if not row:
        pytest.skip("No healthy window found")
        
    machine_id, cycle, sensors_json, true_rul = row
    
    # In AMKB, the metadata["sensors"] is just the 14-dim reading of that *one* cycle,
    # wait... no, the population script didn't store the 30x14 window in metadata, 
    # it only stored the *last* 14-dim reading in metadata["sensors"].
    # So we need to reconstruct the 30x14 window from CMAPSSAdapter for the test.
    from server.adapters.cmapss_adapter import CMAPSSAdapter
    adapter = CMAPSSAdapter(subset="FD001", split="train")
    adapter.connect()
    readings = adapter.get_unit_history(machine_id)
    adapter.disconnect()
    
    if len(readings) < cycle:
        pytest.skip("Cycle out of bounds")
        
    buf = [r.feature_vector for r in readings[cycle-30:cycle]]
    if len(buf) != 30:
        pytest.skip("Not enough history for full window")
        
    window = np.array(buf, dtype=np.float32)
    
    context = ace.build_context("cmapss", machine_id, cycle, window)
    
    assert context.domain == "cmapss"
    assert context.machine_id == machine_id
    assert context.query_cycle == cycle
    
    # Should exclude self-match
    for n in context.neighbors:
        assert not (n.machine_id == machine_id and n.cycle == cycle), "Self-match was not excluded"
        
    # Healthy window should have high average neighbor RUL
    assert context.average_neighbor_rul > 70.0
    
    print(f"\n--- HEALTHY CONTEXT ---")
    print(f"Query: {machine_id} at cycle {cycle}")
    print(f"Neighbors retrieved:")
    for n in context.neighbors:
        print(f"  -> {n.machine_id} at cycle {n.cycle} (RUL: {n.rul}) [Dist: {n.distance:.5f}]")
    print(f"Average Neighbor RUL: {context.average_neighbor_rul:.2f}")
    
    # Should fetch Machine DNA
    assert context.machine_dna is not None
    assert len(context.machine_dna) == 16

def test_build_context_near_failure(ace, amkb):
    count = amkb.count(domain="cmapss")
    if count < 1000:
        pytest.skip("AMKB not populated")
        
    pool = amkb._get_pool()
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT machine_id, cycle FROM amkb_experiences "
            "WHERE domain = 'cmapss' AND rul_cycles <= 5 LIMIT 1"
        ).fetchone()
        
    if not row:
        pytest.skip("No near-failure window found")
        
    machine_id, cycle = row
    
    from server.adapters.cmapss_adapter import CMAPSSAdapter
    adapter = CMAPSSAdapter(subset="FD001", split="train")
    adapter.connect()
    readings = adapter.get_unit_history(machine_id)
    adapter.disconnect()
    
    buf = [r.feature_vector for r in readings[cycle-30:cycle]]
    window = np.array(buf, dtype=np.float32)
    
    context = ace.build_context("cmapss", machine_id, cycle, window)
    
    for n in context.neighbors:
        assert not (n.machine_id == machine_id and n.cycle == cycle), "Self-match was not excluded"
        
    # Near failure window should have low average neighbor RUL
    assert context.average_neighbor_rul < 20.0
    print(f"\n--- NEAR FAILURE CONTEXT ---")
    print(f"Query: {machine_id} at cycle {cycle}")
    print(f"Neighbors retrieved:")
    for n in context.neighbors:
        print(f"  -> {n.machine_id} at cycle {n.cycle} (RUL: {n.rul}) [Dist: {n.distance:.5f}]")
    print(f"Average Neighbor RUL: {context.average_neighbor_rul:.2f}")

def test_build_context_shape_validation(ace):
    bad_window = np.zeros(14, dtype=np.float32)  # 1D array instead of 2D
    with pytest.raises(ValueError, match="Expected 2D window array"):
        ace.build_context("cmapss", "unit_1", 10, bad_window)

def test_api_health():
    from fastapi.testclient import TestClient
    from server.api import app
    
    with TestClient(app) as client:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

def test_api_get_dna():
    from fastapi.testclient import TestClient
    from server.api import app
    
    # We use 'unit_1' which should exist in cmapss domain
    with TestClient(app) as client:
        resp = client.get("/api/dna/cmapss/unit_1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["domain"] == "cmapss"
        assert data["machine_id"] == "unit_1"
        assert len(data["dna"]) == 16

def test_api_post_context():
    from fastapi.testclient import TestClient
    from server.api import app
    
    # Send a valid 30x14 zero window (just to test routing and response shape)
    payload = {
        "domain": "cmapss",
        "machine_id": "unit_1",
        "cycle": 50,
        "window": [[0.0] * 14] * 30,
        "k": 5
    }
    
    with TestClient(app) as client:
        resp = client.post("/api/context", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["domain"] == "cmapss"
        assert data["machine_id"] == "unit_1"
        assert "predicted_rul" in data
        assert isinstance(data["neighbors"], list)
        
        # We asked for 5
        assert len(data["neighbors"]) <= 5

def test_api_post_context_bad_shape():
    from fastapi.testclient import TestClient
    from server.api import app
    
    # Send an empty window
    payload = {
        "domain": "cmapss",
        "machine_id": "unit_1",
        "cycle": 50,
        "window": [],
        "k": 5
    }
    
    with TestClient(app) as client:
        resp = client.post("/api/context", json=payload)
        assert resp.status_code == 400
        assert "Window cannot be empty" in resp.json()["detail"]

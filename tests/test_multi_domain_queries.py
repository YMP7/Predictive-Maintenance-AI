import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from server.atlas.adaptive_context import AdaptiveContextEngine, AdaptiveContext, NeighborContext
from server.atlas.explain import ExplanationEngine
from server.atlas.decision import DecisionGraph
from server.atlas.simulation import SimulationEngine
from server.atlas.world_model import WorldModelConfig, WorldModel
import server.api as api


@pytest.fixture
def mock_engines():
    # Setup mock AMKB & WorldModel for CMAPSS
    mock_amkb = MagicMock()
    mock_amkb.retrieve_similar.return_value = [
        MagicMock(machine_id="unit_10", cycle=50, true_rul=75.0, similarity=0.05),
        MagicMock(machine_id="unit_20", cycle=80, true_rul=45.0, similarity=0.12),
    ]
    
    mock_dna_engine = MagicMock()
    mock_dna_engine.get_dna.return_value = np.zeros(32, dtype=np.float32)
    
    mock_world_model = MagicMock()
    mock_world_model.config = WorldModelConfig(feature_dim=14, seq_len=30, state_dim=32)
    mock_world_model.predict.return_value = MagicMock(
        rul_pred=82.5,
        state_vector=np.ones(32, dtype=np.float32)
    )
    
    ace = AdaptiveContextEngine(mock_amkb, mock_dna_engine, mock_world_model)
    explain = ExplanationEngine()
    sim = SimulationEngine()
    decision = DecisionGraph()
    
    return {
        "amkb": mock_amkb,
        "dna": mock_dna_engine,
        "world_model": mock_world_model,
        "ace": ace,
        "explain": explain,
        "sim": sim,
        "decision": decision,
    }


def test_adaptive_context_multi_domain_shapes(mock_engines):
    ace = mock_engines["ace"]
    
    # 1. C-MAPSS (30, 14)
    cmapss_win = np.random.rand(30, 14).astype(np.float32)
    ctx_cmapss = ace.build_context(
        domain="cmapss",
        machine_id="unit_1",
        current_cycle=50,
        current_window=cmapss_win
    )
    assert ctx_cmapss.domain == "cmapss"
    assert ctx_cmapss.predicted_rul == 82.5
    assert len(ctx_cmapss.neighbors) == 2
    
    # 2. Laptop (30, 5) -> Uses domain-specific trained model if available
    laptop_win = np.random.rand(30, 5).astype(np.float32)
    ctx_laptop = ace.build_context(
        domain="laptop",
        machine_id="laptop_local",
        current_cycle=10,
        current_window=laptop_win
    )
    assert ctx_laptop.domain == "laptop"
    # When laptop_world_model.pt exists, it outputs normalized stress [0, 1]
    assert 0.0 <= ctx_laptop.predicted_rul <= 1.0 or ctx_laptop.predicted_rul == 30.0
    assert len(ctx_laptop.neighbors) == 2

    # 3. Unsupported domain (30, 8) -> Triggers fallback path safely
    unsupported_win = np.random.rand(30, 8).astype(np.float32)
    ctx_unsupported = ace.build_context(
        domain="unsupported_domain",
        machine_id="device_99",
        current_cycle=1,
        current_window=unsupported_win
    )
    assert ctx_unsupported.domain == "unsupported_domain"
    assert ctx_unsupported.predicted_rul == 30.0


def test_explain_multidomain_attribution_reason(mock_engines):
    ace = mock_engines["ace"]
    explain = mock_engines["explain"]
    
    # Laptop (30, 5) window
    laptop_win = np.random.rand(30, 5).astype(np.float32)
    ctx = ace.build_context(
        domain="laptop",
        machine_id="laptop_local",
        current_cycle=10,
        current_window=laptop_win
    )
    
    report = explain.explain(ctx, window=laptop_win, ace=ace)
    
    # Attributions should be empty with an explicit machine-readable reason
    assert report.sensor_attributions == []
    assert report.attribution_unavailable_reason is not None
    assert "feature_dim != 14" in report.attribution_unavailable_reason


def test_api_endpoints_with_multi_domain_windows(mock_engines):
    # Wire mock engines into api module globals
    api._amkb = mock_engines["amkb"]
    api._dna_engine = mock_engines["dna"]
    api._world_model = mock_engines["world_model"]
    api._ace = mock_engines["ace"]
    api._explain_engine = mock_engines["explain"]
    api._simulation_engine = mock_engines["sim"]
    api._decision_graph = mock_engines["decision"]
    
    client = TestClient(api.app)
    
    # 1. Post Laptop (30, 5) window to /api/context
    laptop_payload = {
        "domain": "laptop",
        "machine_id": "laptop_local",
        "cycle": 15,
        "window": np.random.rand(30, 5).tolist(),
        "k": 5
    }
    resp = client.post("/api/context", json=laptop_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain"] == "laptop"
    assert data["machine_id"] == "laptop_local"
    
    # 2. Post Laptop (30, 5) window to /api/explain
    resp_exp = client.post("/api/explain", json=laptop_payload)
    assert resp_exp.status_code == 200
    exp_data = resp_exp.json()
    assert exp_data["sensor_attributions"] == []
    assert exp_data["attribution_unavailable_reason"] is not None
    
    # 3. Post Laptop (30, 5) window to /api/decide
    resp_dec = client.post("/api/decide", json=laptop_payload)
    assert resp_dec.status_code == 200
    dec_data = resp_dec.json()
    assert "recommended_action" in dec_data
    assert "ranked_actions" in dec_data
    
    # 4. Post C-MAPSS (30, 14) window to /api/context
    cmapss_payload = {
        "domain": "cmapss",
        "machine_id": "unit_1",
        "cycle": 50,
        "window": np.random.rand(30, 14).tolist(),
        "k": 5
    }
    resp_cmapss = client.post("/api/context", json=cmapss_payload)
    assert resp_cmapss.status_code == 200

    # 5. Post Server (30, 5) window to /api/decide
    server_payload = {
        "domain": "server",
        "machine_id": "server_prod_1",
        "cycle": 100,
        "window": np.random.rand(30, 5).tolist(),
        "k": 5
    }
    resp_server = client.post("/api/decide", json=server_payload)
    assert resp_server.status_code == 200
    server_dec_data = resp_server.json()
    assert "recommended_action" in server_dec_data
    assert "ranked_actions" in server_dec_data

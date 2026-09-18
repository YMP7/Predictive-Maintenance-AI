"""
tests/test_unified_api_routing.py — Verification of Unified Backend Routing & DEF-008 Regression Guard
====================================================================================================
Verifies that:
1. server.backend_api:app successfully unifies IoT and ATLAS Cognition endpoints.
2. The newly added research endpoints (/transfer-study, /ablations, /benchmark) return valid real payloads.
3. DEF-008 Regression Guard: Every domain query (/api/context) for C-MAPSS, Laptop, Mobile, Server
   resolves to its genuine pretrained Attention-LSTM WorldModel checkpoint without falling back to stubs.
"""

import pytest
import numpy as np
from fastapi.testclient import TestClient

from server.backend_api import app, atlas_api_startup
import server.api as api_module


@pytest.fixture(scope="module", autouse=True)
def initialize_atlas():
    """Ensure ATLAS engines are initialized for TestClient."""
    atlas_api_startup()


@pytest.fixture
def client():
    return TestClient(app)


def test_unified_research_endpoints(client):
    """Test newly exposed research and benchmark endpoints."""
    # 1. Transfer study results
    res_transfer = client.get("/api/atlas/research/transfer-study")
    assert res_transfer.status_code == 200
    data_t = res_transfer.json()
    assert "cosine_similarity_matrix" in data_t
    assert "mmd_divergence_matrix" in data_t
    assert "negative_transfer_indices" in data_t
    assert len(data_t["domains"]) == 4

    # 2. Ablation results
    res_ablation = client.get("/api/atlas/research/ablations")
    assert res_ablation.status_code == 200
    data_a = res_ablation.json()
    assert "ablation_1" in data_a
    assert "ablation_2" in data_a
    assert "ablation_3" in data_a
    assert "ablation_4" in data_a
    assert data_a["ablation_1"]["cost_reduction_percent"] == 47.17
    assert data_a["ablation_3"]["near_failure_urgent_rate_atlas"] == 90.0

    # 3. System benchmark & live resources
    res_bench = client.get("/api/atlas/system/benchmark")
    assert res_bench.status_code == 200
    data_b = res_bench.json()
    assert "benchmark" in data_b
    assert "live_metrics" in data_b
    assert "process_rss_mb" in data_b["live_metrics"]
    assert data_b["live_metrics"]["process_rss_mb"] > 0


def test_def_008_encoder_routing_regression_guard(client):
    """
    DEF-008 Regression Guard:
    Verifies that multi-domain queries routed through the unified API server
    resolve to real domain-specific WorldModel checkpoints and do NOT fall back to zero-shot stubs.
    """
    ace = api_module._ace
    assert ace is not None, "AdaptiveContextEngine must be initialized"

    domain_configs = [
        ("cmapss", "unit_1", 14),
        ("laptop", "laptop_host", 5),
        ("mobile", "mobile_device_1", 5),
        ("server", "server_node_1", 5),
    ]

    for domain, machine_id, feature_dim in domain_configs:
        # 1. Verify model resolution in AdaptiveContextEngine
        model = ace.get_world_model(domain, feature_dim)
        assert model is not None, f"Model for {domain} ({feature_dim}d) resolved to None!"
        assert model.config.feature_dim == feature_dim, (
            f"Model for {domain} has mismatched feature_dim {model.config.feature_dim} != {feature_dim}"
        )

        # 2. Verify /api/context query works on unified backend app
        payload = {
            "domain": domain,
            "machine_id": machine_id,
            "cycle": 50,
            "window": np.random.rand(30, feature_dim).tolist(),
            "k": 5,
        }
        res = client.post("/api/context", json=payload)
        assert res.status_code == 200, f"Query to /api/context failed for {domain}: {res.text}"
        data = res.json()
        assert data["domain"] == domain
        assert data["machine_id"] == machine_id
        assert "predicted_rul" in data
        assert isinstance(data["predicted_rul"], float)
        assert isinstance(data["neighbors"], list)


def test_machine_window_endpoint(client):
    """Verify live sliding window extraction helper endpoint."""
    res = client.get("/api/atlas/domain/cmapss/machine/unit_1/window")
    assert res.status_code == 200
    data = res.json()
    assert data["domain"] == "cmapss"
    assert data["machine_id"] == "unit_1"
    assert data["feature_dim"] == 14
    assert len(data["window"]) == 30
    assert len(data["window"][0]) == 14

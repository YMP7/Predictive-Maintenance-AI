import pytest
from unittest.mock import patch, MagicMock
from server.adapters.laptop_adapter import LaptopAdapter
from server.adapters.base_adapter import AdapterStatus
from server.atlas.explain import ExplanationEngine, NeighborContext
import numpy as np


def test_laptop_adapter_reading():
    adapter = LaptopAdapter()
    adapter.connect()
    
    reading = adapter.get_reading("laptop_local")
    
    assert reading.domain == "laptop"
    assert reading.machine_id == "laptop_local"
    assert reading.rul_label is None
    assert reading.adapter_status == AdapterStatus.LIVE.value
    
    # Check that canonical 5 features are strictly present
    features = reading.features
    expected_canonical_keys = {"cpu_usage", "memory_usage", "disk_usage", "battery_percent", "is_charging"}
    assert expected_canonical_keys.issubset(set(features.keys()))
    
    # Check that all 16 channels (15 genuine + 1 estimated) are returned
    assert len(features) == 16
    
    # Check that canonical model vector preserves exact 5 dimensions for WorldModel
    assert len(reading.feature_vector) == 5
    
    # Check that features are strictly bounded in [0, 1]
    for k, v in features.items():
        assert 0.0 <= v <= 1.0, f"{k} is out of bounds: {v}"
        
    # Check health_index (Instantaneous Stress Score) invariant
    assert 0.0 <= reading.health_index <= 1.0
    expected_stress = round((0.7 * features["cpu_usage"]) + (0.3 * features["memory_usage"]), 4)
    assert abs(reading.health_index - expected_stress) < 1e-4
    
    # Check honest heuristic metadata on derived thermal estimate
    assert reading.raw_features.get("is_estimated") is True
    assert reading.raw_features.get("thermal_is_estimated") is True
    assert reading.raw_features.get("estimation_method") == "thermodynamic_heuristic"
    assert "estimated_thermal_c" in reading.raw_features


def test_explain_filter_mixed_neighbors():
    engine = ExplanationEngine()
    
    # Create a mixed set of neighbors
    n1 = NeighborContext(machine_id="unit_1", cycle=100, rul=50.0, distance=0.1) # Has true_rul
    n2 = NeighborContext(machine_id="laptop_local", cycle=3600, rul=None, distance=0.05) # No true_rul
    n3 = NeighborContext(machine_id="unit_2", cycle=120, rul=25.0, distance=0.2) # Has true_rul
    
    # We mock AdaptiveContext
    from server.atlas.adaptive_context import AdaptiveContext
    context = AdaptiveContext(
        domain="laptop",
        machine_id="laptop_local", 
        query_cycle=100,
        predicted_rul=10.0, 
        neighbors=[n1, n2, n3],
        average_neighbor_rul=37.5,
        machine_dna=None
    )
    
    report = engine.explain(context)
    
    # The citation should only include the two valid neighbors
    citations = report.citations
    assert len(citations) == 2
    assert "unit_1" in citations[0] or "unit_2" in citations[0]
    assert "unit_1" in citations[1] or "unit_2" in citations[1]
    
    # Ensure laptop_local was filtered out
    for citation in citations:
        assert "laptop_local" not in citation

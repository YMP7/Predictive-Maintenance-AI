import os
import datetime
import pytest
import numpy as np

from server.atlas.amkb import Experience
from server.atlas.machine_dna import MachineDNAEngine, DNA_DIM

@pytest.fixture
def empty_experiences():
    return []

@pytest.fixture
def short_experiences():
    return [
        Experience(id="1", domain="cmapss", machine_id="u1", cycle=1, event_type="normal", 
                   state_vector=np.ones(32, dtype=np.float32), health_index=1.0,
                   true_rul=100.0, predicted_rul=100.0,
                   metadata={"sensors": {"s2": 10.0, "s3": 20.0, "s4": 30.0, "s9": 40.0, "s14": 50.0, "s7": 60.0, "s11": 70.0, "s15": 80.0}},
                   recorded_at=datetime.datetime.now())
    ]

@pytest.fixture
def long_experiences():
    exps = []
    # Total cycles = 20, cycle runs from 1 to 20
    # true_rul runs from 19 down to 0
    for i in range(20):
        # linear decline
        sv = np.ones(32, dtype=np.float32) * (1.0 - i * 0.05)
        hi = 1.0 - i * 0.05
        # some varying sensors
        s2 = 10.0 + i * 0.5
        s3 = 20.0 + i * 1.0
        exps.append(
            Experience(id=str(i), domain="cmapss", machine_id="u2", cycle=i+1, event_type="normal",
                       state_vector=sv, health_index=hi,
                       true_rul=float(19 - i), predicted_rul=None,
                       metadata={"sensors": {"s2": s2, "s3": s3, "s4": 30.0, "s9": 40.0, "s14": 50.0, "s7": 60.0, "s11": 70.0, "s15": 80.0}},
                       recorded_at=datetime.datetime.now())
        )
    return exps

def test_compute_dna_raw_empty(empty_experiences):
    engine = MachineDNAEngine()
    dna = engine.compute_dna_raw(empty_experiences)
    assert dna.shape == (DNA_DIM,)
    assert np.all(dna == 0.0)

def test_compute_dna_raw_short(short_experiences):
    # Length < 2 should return 0 for slopes
    engine = MachineDNAEngine()
    dna = engine.compute_dna_raw(short_experiences)
    assert dna.shape == (DNA_DIM,)
    assert np.all(dna == 0.0)

def test_compute_dna_raw_long(long_experiences):
    engine = MachineDNAEngine()
    dna = engine.compute_dna_raw(long_experiences)
    assert dna.shape == (DNA_DIM,)
    
    # life_fraction_health:
    # tot = 20. lf_h = 1 - (cycle / 20).
    # i=0: cycle=1, lf_h=0.95
    # i=1: cycle=2, lf_h=0.9
    # i=19: cycle=20, lf_h=0.0
    # declines by 0.05 per step.
    assert np.isclose(dna[1], -0.05, atol=1e-5)
    
    # s2 increases by 0.5 per step
    assert np.isclose(dna[3], 0.5, atol=1e-5)
    
    # s3 increases by 1.0 per step
    assert np.isclose(dna[4], 1.0, atol=1e-5)
    
    # s4 is flat
    assert np.isclose(dna[5], 0.0, atol=1e-5)

# Integration tests using a live DB
import psycopg
from psycopg_pool import ConnectionPool

def _skip_if_no_db():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        pytest.skip("DATABASE_URL not set")
    try:
        with psycopg.connect(db_url, connect_timeout=1):
            pass
    except Exception:
        pytest.skip("DATABASE_URL not set or DB unreachable")

@pytest.fixture
def db_pool():
    _skip_if_no_db()
    db_url = os.environ.get("DATABASE_URL")
    pool = ConnectionPool(db_url, min_size=1, max_size=2, open=True)
    yield pool
    with pool.connection() as conn:
        conn.execute("DELETE FROM machine_dna WHERE domain = 'test_dna';")
        conn.commit()
    pool.close()

def test_machine_dna_db_integration(db_pool):
    # Engine without a scaler json available will just use identity normalization (raw)
    engine = MachineDNAEngine(pool=db_pool, scaler_path="nonexistent_scaler.json")
    
    # Store DNA 1
    vec1 = np.zeros(DNA_DIM, dtype=np.float32)
    vec1[1] = -0.5
    engine.store_dna("test_dna", "u1", vec1, components={"test": True}, n_cycles_used=10)
    
    # Store DNA 2 (very similar)
    vec2 = np.zeros(DNA_DIM, dtype=np.float32)
    vec2[1] = -0.45
    engine.store_dna("test_dna", "u2", vec2, components={"test": True}, n_cycles_used=20)
    
    # Store DNA 3 (very different)
    vec3 = np.zeros(DNA_DIM, dtype=np.float32)
    vec3[1] = 0.8
    engine.store_dna("test_dna", "u3", vec3, components={"test": True}, n_cycles_used=30)
    
    # Retrieve similar to vec1
    results = engine.retrieve_similar(vec1, k=3, domain="test_dna")
    assert len(results) == 3
    assert results[0].machine_id == "u1"
    assert results[1].machine_id == "u2"
    assert results[2].machine_id == "u3"
    assert results[0].similarity < results[2].similarity

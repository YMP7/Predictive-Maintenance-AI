"""
tests/test_amkb.py — AMKB test suite
======================================
Unit tests (no DB required) + integration tests (require Docker timescaledb).

Unit tests run always. Integration tests are skipped automatically if
DATABASE_URL is not set or the DB is unreachable.

Run all:
    pytest tests/test_amkb.py -v

Run only unit tests:
    pytest tests/test_amkb.py -v -k "not integration"

Run integration + real-data sanity check (Docker DB must be up):
    pytest tests/test_amkb.py -v -k "integration"
"""

from __future__ import annotations

import os
import pytest
import numpy as np
from datetime import datetime
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Detect DB availability for integration test skipping
# ---------------------------------------------------------------------------

def _db_available() -> bool:
    """True if DATABASE_URL is set and the DB is reachable."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        return False
    try:
        from psycopg_pool import ConnectionPool
        pool = ConnectionPool(url, min_size=1, max_size=1, open=True)
        with pool.connection() as conn:
            conn.execute("SELECT 1")
        pool.close()
        return True
    except Exception:
        return False

DB_AVAILABLE = _db_available()
skip_no_db = pytest.mark.skipif(not DB_AVAILABLE, reason="DATABASE_URL not set or DB unreachable")


# ---------------------------------------------------------------------------
# Import under test
# ---------------------------------------------------------------------------

from server.atlas.amkb import AMKB, Experience, EMBEDDING_DIM


# ---------------------------------------------------------------------------
# Unit tests — no DB needed
# ---------------------------------------------------------------------------

class TestValidation:
    """Vector validation and type safety — no DB needed."""

    def test_wrong_dim_raises(self):
        amkb = AMKB()
        bad_vec = np.random.randn(16).astype(np.float32)
        with pytest.raises(ValueError, match="shape"):
            amkb._validate_vector(bad_vec)

    def test_correct_dim_passes(self):
        amkb = AMKB()
        v = np.random.randn(EMBEDDING_DIM).astype(np.float32)
        out = amkb._validate_vector(v)
        assert out.shape == (EMBEDDING_DIM,)
        assert out.dtype == np.float32

    def test_float64_coerced_to_float32(self):
        amkb = AMKB()
        v = np.random.randn(EMBEDDING_DIM)   # float64
        out = amkb._validate_vector(v)
        assert out.dtype == np.float32

    def test_2d_wrong_shape_raises(self):
        amkb = AMKB()
        bad = np.random.randn(EMBEDDING_DIM, 1).astype(np.float32)
        with pytest.raises(ValueError):
            amkb._validate_vector(bad)


class TestRetrieveNoDb:
    """retrieve_similar edge cases that don't hit the DB."""

    def test_k_zero_returns_empty(self):
        amkb = AMKB()
        sv = np.random.randn(EMBEDDING_DIM).astype(np.float32)
        # Should return early before any DB call
        result = amkb.retrieve_similar(sv, k=0)
        assert result == []

    def test_k_negative_returns_empty(self):
        amkb = AMKB()
        sv = np.random.randn(EMBEDDING_DIM).astype(np.float32)
        result = amkb.retrieve_similar(sv, k=-5)
        assert result == []


class TestPgVecConversion:
    """Round-trip vector <-> pgvector string conversion."""

    def test_round_trip(self):
        v = np.random.randn(EMBEDDING_DIM).astype(np.float32)
        pg_str = AMKB._to_pg_vec(v)
        v2 = AMKB._from_pg_vec(pg_str)
        np.testing.assert_allclose(v, v2, rtol=1e-5)

    def test_format_starts_with_bracket(self):
        v = np.ones(EMBEDDING_DIM, dtype=np.float32)
        pg_str = AMKB._to_pg_vec(v)
        assert pg_str.startswith("[") and pg_str.endswith("]")


class TestTrueRulSeparation:
    """
    Verify true_rul and predicted_rul are stored separately.
    This is the critical separation for Explainability (Month 5) correctness.
    """

    def test_experience_has_both_rul_fields(self):
        exp = Experience(
            id="1",
            domain="cmapss",
            machine_id="unit_001",
            cycle=150,
            event_type="normal",
            state_vector=np.zeros(EMBEDDING_DIM, dtype=np.float32),
            true_rul=47.0,
            predicted_rul=51.3,
            health_index=0.7,
            metadata={},
            recorded_at=datetime.now(),
        )
        assert exp.true_rul == 47.0
        assert exp.predicted_rul == 51.3
        assert exp.true_rul != exp.predicted_rul   # must be independent fields

    def test_true_rul_can_be_none_for_live_domains(self):
        exp = Experience(
            id="2",
            domain="laptop",
            machine_id="my_laptop",
            cycle=0,
            event_type="normal",
            state_vector=np.zeros(EMBEDDING_DIM, dtype=np.float32),
            true_rul=None,       # no ground truth for live domains
            predicted_rul=82.5,
            health_index=0.95,
            metadata={},
            recorded_at=datetime.now(),
        )
        assert exp.true_rul is None
        assert exp.predicted_rul == 82.5

    def test_predicted_rul_can_be_none(self):
        """Historical experiences stored before model inference have no predicted_rul."""
        exp = Experience(
            id="3",
            domain="cmapss",
            machine_id="unit_002",
            cycle=200,
            event_type="fault",
            state_vector=np.zeros(EMBEDDING_DIM, dtype=np.float32),
            true_rul=5.0,
            predicted_rul=None,
            health_index=0.1,
            metadata={},
            recorded_at=datetime.now(),
        )
        assert exp.predicted_rul is None
        assert exp.true_rul == 5.0


# ---------------------------------------------------------------------------
# Integration tests — require Docker DB
# ---------------------------------------------------------------------------

@skip_no_db
class TestIntegration:
    """Round-trip integration tests against the real pgvector DB."""

    @pytest.fixture
    def amkb(self):
        """AMKB with standalone pool; cleans up test rows after each test."""
        inst = AMKB()
        yield inst
        # Cleanup: delete all rows we inserted during this test
        pool = inst._get_pool()
        with pool.connection() as conn:
            conn.execute(
                "DELETE FROM amkb_experiences WHERE metadata->>'_test' = 'true'"
            )
            conn.commit()

    def _test_vec(self, seed: int = 0) -> np.ndarray:
        rng = np.random.default_rng(seed)
        return rng.standard_normal(EMBEDDING_DIM).astype(np.float32)

    def _store(self, amkb, machine_id, seed, true_rul, cycle=100):
        sv = self._test_vec(seed)
        return amkb.store_experience(
            domain="cmapss",
            machine_id=machine_id,
            state_vector=sv,
            cycle=cycle,
            true_rul=true_rul,
            predicted_rul=true_rul + 5.0,
            metadata={"_test": "true"},
        ), sv

    def test_store_returns_id(self, amkb):
        exp_id, _ = self._store(amkb, "unit_test_001", seed=1, true_rul=80.0)
        assert exp_id is not None
        assert len(str(exp_id)) > 0

    def test_get_experience_round_trip(self, amkb):
        exp_id, sv = self._store(amkb, "unit_test_002", seed=2, true_rul=60.0)
        fetched = amkb.get_experience(exp_id)
        assert fetched is not None
        assert fetched.machine_id == "unit_test_002"
        assert fetched.true_rul == pytest.approx(60.0, abs=0.01)
        assert fetched.predicted_rul == pytest.approx(65.0, abs=0.01)
        np.testing.assert_allclose(fetched.state_vector, sv, rtol=1e-4)

    def test_self_match_is_nearest(self, amkb):
        """Store 3 experiences; retrieve top-1 for sv_b; confirm it matches sv_b."""
        exp_a, sv_a = self._store(amkb, "unit_test_003", seed=10, true_rul=90.0)
        exp_b, sv_b = self._store(amkb, "unit_test_003", seed=20, true_rul=50.0)
        exp_c, sv_c = self._store(amkb, "unit_test_003", seed=30, true_rul=10.0)

        results = amkb.retrieve_similar(sv_b, k=3, domain="cmapss")
        assert len(results) >= 1
        # Top result should be b itself (self-match ~0.0 cosine distance)
        top = results[0]
        assert top.similarity == pytest.approx(0.0, abs=0.01)
        assert top.machine_id == "unit_test_003"

    def test_unit_history_descending_order(self, amkb):
        """get_unit_history should return most recent first."""
        for cycle in [10, 50, 100]:
            self._store(amkb, "unit_test_004", seed=cycle, true_rul=125 - cycle, cycle=cycle)

        history = amkb.get_unit_history("cmapss", "unit_test_004", limit=10)
        cycles = [h.cycle for h in history if h.machine_id == "unit_test_004"]
        assert cycles == sorted(cycles, reverse=True)

    def test_count_increases_after_store(self, amkb):
        before = amkb.count(domain="cmapss")
        self._store(amkb, "unit_test_005", seed=99, true_rul=40.0)
        after = amkb.count(domain="cmapss")
        assert after == before + 1

    def test_true_rul_stored_separately_from_predicted_rul(self, amkb):
        """Critical: true_rul and predicted_rul must be independently retrievable."""
        exp_id, _ = self._store(amkb, "unit_test_006", seed=7, true_rul=30.0)
        fetched = amkb.get_experience(exp_id)
        assert fetched.true_rul == pytest.approx(30.0, abs=0.01)
        assert fetched.predicted_rul == pytest.approx(35.0, abs=0.01)
        # They must NOT be the same value (proving they are stored independently)
        assert fetched.true_rul != fetched.predicted_rul


@skip_no_db
class TestNearFailureRetrieval:
    """
    Semantic retrieval sanity check using real WorldModel embeddings.

    Verifies that querying the fully populated AMKB with a near-failure state vector 
    retrieves other near-failure experiences, and querying with a healthy vector 
    retrieves healthy neighbors.
    """

    @pytest.fixture
    def amkb(self):
        return AMKB()

    def test_semantic_retrieval_sanity(self, amkb):
        """
        Query with a near-failure unit's state vector, and a healthy one.
        Assert that neighbors reflect the corresponding RUL bands.
        """
        # Ensure the DB has been populated
        count = amkb.count(domain="cmapss")
        if count < 1000:
            pytest.skip("AMKB not fully populated. Run scripts/populate_amkb.py first.")

        # 1. Fetch a near-failure query vector (e.g. rul_cycles <= 5)
        pool = amkb._get_pool()
        with pool.connection() as conn:
            row_fail = conn.execute(
                "SELECT id, embedding FROM amkb_experiences WHERE domain = 'cmapss' AND rul_cycles <= 5 LIMIT 1"
            ).fetchone()
            
            row_health = conn.execute(
                "SELECT id, embedding FROM amkb_experiences WHERE domain = 'cmapss' AND rul_cycles >= 100 LIMIT 1"
            ).fetchone()
            
        if not row_fail or not row_health:
            pytest.skip("Could not find suitable healthy/failure experiences for testing.")
            
        fail_id, fail_emb_str = row_fail
        health_id, health_emb_str = row_health

        sv_fail = np.array([float(x) for x in str(fail_emb_str).strip("[]").split(",")], dtype=np.float32)
        sv_health = np.array([float(x) for x in str(health_emb_str).strip("[]").split(",")], dtype=np.float32)

        # 2. Test Near-Failure Retrieval
        # We assert on mean neighbor RUL, which tolerates some noisy outliers among the k=10 neighbors.
        # Request k=11 to allow filtering out the exact self-match (the query experience itself).
        results_fail = amkb.retrieve_similar(sv_fail, k=11, domain="cmapss")
        neighbors_fail = [r for r in results_fail if str(r.id) != str(fail_id)][:10]
        assert len(neighbors_fail) > 0
        ruls_fail = [r.true_rul for r in neighbors_fail if r.true_rul is not None]
        
        avg_fail = sum(ruls_fail) / len(ruls_fail)
        assert avg_fail < 30.0, f"Near-failure query returned too many healthy neighbors. Avg RUL: {avg_fail}"

        # 3. Test Healthy Retrieval
        results_health = amkb.retrieve_similar(sv_health, k=11, domain="cmapss")
        neighbors_health = [r for r in results_health if str(r.id) != str(health_id)][:10]
        assert len(neighbors_health) > 0
        ruls_health = [r.true_rul for r in neighbors_health if r.true_rul is not None]
        
        avg_health = sum(ruls_health) / len(ruls_health)
        assert avg_health > 70.0, f"Healthy query returned too many near-failure neighbors. Avg RUL: {avg_health}"

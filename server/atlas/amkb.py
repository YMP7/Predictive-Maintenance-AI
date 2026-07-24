"""
AMKB — Adaptive Machine Knowledge Base
=======================================
Month 2 deliverable: the persistent experience store that gives ATLAS
its machine memory.

When the WorldModel encodes a machine window into a 32-dim state vector,
the AMKB is what stores that experience, indexes it for retrieval, and
makes Month 5 Explainability possible:

    "This recommendation is grounded in similarity to unit #47's trajectory,
     which had true RUL=23 cycles at a similar operational state."

Architecture
------------
- Backed by pgvector amkb_experiences table (created by migrate_atlas.py).
- Similarity search uses cosine distance (<=> operator): angular similarity
  between state vectors, independent of magnitude.
  L2 retrieval is a planned Month 9-10 ablation.
- Embedding dimension is canonically 32 (WorldModel state_dim=32).
  Do NOT change without updating machine_dna.py and WorldModel.

true_rul vs. predicted_rul (critical separation)
-------------------------------------------------
  true_rul:      Optional[float]  -- ground-truth label (C-MAPSS preprocessed).
                                     None for live domains where no label exists yet.
  predicted_rul: Optional[float]  -- model estimate at storage time.

The Explainability Engine MUST cite true_rul (where available), not predicted_rul.
Citing predicted_rul as "evidence" is circular: the model citing its own guesses.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import numpy as np

logger = logging.getLogger("ATLAS.AMKB")

EMBEDDING_DIM = 32  # Must match WorldModel.config.state_dim = 32
                    # and pgvector column: embedding vector(32)

EventType = Literal["normal", "fault", "rul_warning", "resolved"]


@dataclass
class Experience:
    """
    A single stored experience in the AMKB.

    true_rul vs. predicted_rul
    --------------------------
    true_rul:      Ground-truth label from C-MAPSS preprocessed data.
                   None for live domains (no label until failure observed).
                   USE THIS for Explainability citations.

    predicted_rul: WorldModel estimate at storage time.
                   DO NOT use as evidence in Explainability — circular reasoning.

    similarity:    Cosine distance to query vector; populated only on retrieval.
                   Lower = more similar. Self-match = ~0.0.
    """
    id: str
    domain: str
    machine_id: str
    cycle: int
    event_type: str
    state_vector: np.ndarray         # shape (32,)
    true_rul: Optional[float]        # ground-truth label
    predicted_rul: Optional[float]   # model estimate — not for citations
    health_index: float
    metadata: Dict[str, Any]
    recorded_at: datetime
    similarity: Optional[float] = None


class AMKB:
    """
    Adaptive Machine Knowledge Base — vector-indexed experience store.

    Parameters
    ----------
    pool : optional psycopg_pool.ConnectionPool
        Shared pool from integrated_server.py. If None, a standalone
        pool is created from DATABASE_URL env var (useful for tests/scripts).
    embedding_dim : int
        Must match WorldModel state_dim = 32.
    """

    def __init__(self, pool=None, embedding_dim: int = EMBEDDING_DIM) -> None:
        self._embedding_dim = embedding_dim
        self._pool = pool

    def _get_pool(self):
        if self._pool is not None:
            return self._pool
        try:
            from psycopg_pool import ConnectionPool
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError as e:
            raise RuntimeError(
                "psycopg_pool is required. Install: pip install 'psycopg[binary]' psycopg_pool"
            ) from e
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            raise RuntimeError(
                "DATABASE_URL not set. Pass pool= argument or set DATABASE_URL."
            )
        logger.info("Creating standalone AMKB connection pool...")
        self._pool = ConnectionPool(db_url, min_size=1, max_size=3, open=True)
        return self._pool

    def _validate_vector(self, v: np.ndarray, name: str = "state_vector") -> np.ndarray:
        v = np.asarray(v, dtype=np.float32)
        if v.shape != (self._embedding_dim,):
            raise ValueError(
                f"{name} must have shape ({self._embedding_dim},), got {v.shape}. "
                f"Check WorldModel.config.state_dim == {self._embedding_dim}."
            )
        return v

    @staticmethod
    def _to_pg_vec(v: np.ndarray) -> str:
        return "[" + ",".join(f"{x:.8f}" for x in v) + "]"

    @staticmethod
    def _from_pg_vec(raw) -> np.ndarray:
        s = str(raw).strip("[]")
        return np.array([float(x) for x in s.split(",")], dtype=np.float32)

    @staticmethod
    def _row_to_exp(row: tuple) -> Experience:
        """
        Parse a DB row into an Experience.
        Column order: id, domain, machine_id, cycle, event_type,
                      embedding, true_rul, predicted_rul, health_index,
                      metadata, created_at [, cosine_distance]
        """
        (id_, domain, machine_id, cycle, event_type,
         emb_raw, true_rul, pred_rul_raw, health_index,
         meta_raw, created_at, *rest) = row

        sv = AMKB._from_pg_vec(emb_raw) if emb_raw is not None else np.zeros(EMBEDDING_DIM, dtype=np.float32)
        meta = dict(meta_raw) if meta_raw else {}

        # predicted_rul stored inside metadata to avoid schema change
        predicted_rul: Optional[float] = None
        if pred_rul_raw is not None:
            try:
                predicted_rul = float(pred_rul_raw)
            except (ValueError, TypeError):
                predicted_rul = None

        similarity = float(rest[0]) if rest and rest[0] is not None else None

        return Experience(
            id=str(id_),
            domain=domain,
            machine_id=machine_id,
            cycle=int(cycle),
            event_type=event_type,
            state_vector=sv,
            true_rul=float(true_rul) if true_rul is not None else None,
            predicted_rul=predicted_rul,
            health_index=float(health_index),
            metadata=meta,
            recorded_at=created_at,
            similarity=similarity,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store_experience(
        self,
        domain: str,
        machine_id: str,
        state_vector: np.ndarray,
        *,
        cycle: int = 0,
        event_type: EventType = "normal",
        true_rul: Optional[float] = None,
        predicted_rul: Optional[float] = None,
        health_index: float = 1.0,
        outcome: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store one experience in the AMKB.

        For C-MAPSS training data: always pass true_rul from preprocessed labels.
        For live domains (Month 6+): pass predicted_rul; leave true_rul=None
        until failure is confirmed and you can retrospectively update it.

        Returns the inserted row ID as a string.
        """
        sv = self._validate_vector(state_vector)
        meta = dict(metadata or {})
        # predicted_rul stored in metadata to keep it clearly separate from
        # the rul_cycles column (which holds ground-truth only)
        meta["_predicted_rul"] = predicted_rul

        pool = self._get_pool()
        with pool.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO amkb_experiences
                    (domain, machine_id, cycle, event_type, outcome,
                     health_index, rul_cycles, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector, %s)
                RETURNING id
                """,
                (
                    domain, machine_id, cycle, event_type, outcome,
                    health_index, true_rul,
                    self._to_pg_vec(sv),
                    json.dumps(meta),
                ),
            ).fetchone()
            conn.commit()

        exp_id = str(row[0])
        logger.debug(
            f"Stored {domain}/{machine_id} cycle={cycle} true_rul={true_rul} "
            f"predicted_rul={predicted_rul} id={exp_id}"
        )
        return exp_id

    def retrieve_similar(
        self,
        state_vector: np.ndarray,
        *,
        k: int = 5,
        domain: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> List[Experience]:
        """
        Retrieve the k most similar experiences by cosine distance.

        Lower cosine distance = more similar. Self-match returns ~0.0.

        Parameters
        ----------
        state_vector : np.ndarray, shape (32,)
        k : int   Number of results.
        domain : Optional[str]   Restrict to this domain.
        event_type : Optional[str]   Restrict to this event type.

        Returns
        -------
        List[Experience] ordered by ascending cosine distance (closest first).
        """
        if k <= 0:
            return []
        sv = self._validate_vector(state_vector)
        pg_vec = self._to_pg_vec(sv)

        where_parts: List[str] = []
        where_params: List[Any] = []
        if domain is not None:
            where_parts.append("domain = %s")
            where_params.append(domain)
        if event_type is not None:
            where_parts.append("event_type = %s")
            where_params.append(event_type)

        where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

        sql = f"""
            SELECT
                id, domain, machine_id, cycle, event_type,
                embedding,
                rul_cycles                           AS true_rul,
                (metadata->>'_predicted_rul')::float AS predicted_rul,
                health_index, metadata, created_at,
                (embedding <=> %s::vector)           AS cosine_distance
            FROM amkb_experiences
            {where_clause}
            ORDER BY cosine_distance ASC
            LIMIT %s
        """
        # Query vector first, limit last; where_params go between
        params = [pg_vec] + where_params + [k]

        pool = self._get_pool()
        with pool.connection() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [self._row_to_exp(r) for r in rows]

    def get_unit_history(
        self,
        domain: str,
        machine_id: str,
        *,
        limit: int = 100,
    ) -> List[Experience]:
        """
        Retrieve stored experiences for a specific unit, most recent first.
        """
        sql = """
            SELECT
                id, domain, machine_id, cycle, event_type,
                embedding,
                rul_cycles                           AS true_rul,
                (metadata->>'_predicted_rul')::float AS predicted_rul,
                health_index, metadata, created_at
            FROM amkb_experiences
            WHERE domain = %s AND machine_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        pool = self._get_pool()
        with pool.connection() as conn:
            rows = conn.execute(sql, (domain, machine_id, limit)).fetchall()
        return [self._row_to_exp(r) for r in rows]

    def get_experience(self, experience_id: str) -> Optional[Experience]:
        """Fetch a single experience by primary key. Returns None if not found."""
        sql = """
            SELECT
                id, domain, machine_id, cycle, event_type,
                embedding,
                rul_cycles                           AS true_rul,
                (metadata->>'_predicted_rul')::float AS predicted_rul,
                health_index, metadata, created_at
            FROM amkb_experiences
            WHERE id = %s
        """
        pool = self._get_pool()
        with pool.connection() as conn:
            row = conn.execute(sql, (experience_id,)).fetchone()
        return self._row_to_exp(row) if row else None

    def count(self, domain: Optional[str] = None) -> int:
        """Return total stored experiences, optionally filtered by domain."""
        if domain:
            sql, params = "SELECT COUNT(*) FROM amkb_experiences WHERE domain = %s", (domain,)
        else:
            sql, params = "SELECT COUNT(*) FROM amkb_experiences", ()
        pool = self._get_pool()
        with pool.connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return int(row[0])

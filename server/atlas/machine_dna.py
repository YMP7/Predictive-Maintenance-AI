import json
import logging
import os
import datetime
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import numpy as np

from server.atlas.amkb import Experience

logger = logging.getLogger("ATLAS.MachineDNA")

DNA_DIM = 16

@dataclass
class MachineDNA:
    id: str
    domain: str
    machine_id: str
    dna_embedding: np.ndarray  # 16-dim float32 array
    components: Dict[str, Any]
    n_cycles_used: int
    computed_at: datetime.datetime
    similarity: Optional[float] = None

class MachineDNAEngine:
    """
    Computes and manages Machine DNA fingerprints.
    Machine DNA captures the long-term degradation character of a unit.
    
    Z-Score Normalization:
    Cosine similarity requires dimensions to be on the same scale. The engine
    attempts to load 'machine_dna_scaler.json' (created during Week 3 population).
    If present, store_dna and retrieve_similar automatically normalize their 
    input vectors.
    """

    def __init__(self, pool=None, scaler_path: str = "data/models/machine_dna_scaler.json"):
        self._pool = pool
        self._scaler_mean = None
        self._scaler_std = None
        
        # Load scaler if it exists
        if os.path.exists(scaler_path):
            try:
                with open(scaler_path, "r") as f:
                    scaler = json.load(f)
                    self._scaler_mean = np.array(scaler["mean"], dtype=np.float32)
                    self._scaler_std = np.array(scaler["std"], dtype=np.float32)
                    # avoid div by zero
                    self._scaler_std[self._scaler_std == 0] = 1.0
                logger.info(f"Loaded Machine DNA scaler from {scaler_path}")
            except Exception as e:
                logger.warning(f"Failed to load scaler from {scaler_path}: {e}")

    def _normalize(self, v: np.ndarray) -> np.ndarray:
        if self._scaler_mean is not None and self._scaler_std is not None:
            return (v - self._scaler_mean) / self._scaler_std
        return v

    def _get_pool(self):
        if self._pool is not None:
            return self._pool
        try:
            from psycopg_pool import ConnectionPool
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError as e:
            raise RuntimeError("psycopg_pool is required.") from e
        
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            raise RuntimeError("DATABASE_URL not set.")
        
        self._pool = ConnectionPool(db_url, min_size=1, max_size=3, open=True)
        return self._pool

    @staticmethod
    def _slope(y: np.ndarray) -> float:
        if len(y) < 2:
            return 0.0
        return float(np.polyfit(np.arange(len(y)), y, 1)[0])
    
    @staticmethod
    def _validate_vector(v: np.ndarray) -> np.ndarray:
        v = np.asarray(v, dtype=np.float32)
        if v.shape != (DNA_DIM,):
            raise ValueError(f"Machine DNA must have shape ({DNA_DIM},), got {v.shape}.")
        return v
    
    @staticmethod
    def _to_pg_vec(v: np.ndarray) -> str:
        return "[" + ",".join(f"{x:.8f}" for x in v) + "]"
    
    @staticmethod
    def _from_pg_vec(raw) -> np.ndarray:
        s = str(raw).strip("[]")
        return np.array([float(x) for x in s.split(",")], dtype=np.float32)

    def compute_dna_raw(self, experiences: List[Experience]) -> np.ndarray:
        """
        Computes the RAW (unnormalized) 16-dim DNA vector for a unit.
        Experiences must be sorted chronologically.
        """
        if not experiences:
            return np.zeros(DNA_DIM, dtype=np.float32)
        
        # We need total life to compute life_fraction without the 125 clip.
        # true_rul is the remaining life at that cycle.
        # cycle + true_rul = total_cycles.
        life_fraction_health = []
        for e in experiences:
            # Prefer raw physical RUL to avoid clip flattening the health fraction
            raw_rul = e.metadata.get("raw_rul", e.true_rul)
            if raw_rul is not None:
                tot = e.cycle + raw_rul
                lf = 1.0 - (e.cycle / tot) if tot > 0 else 0.0
            else:
                lf = 0.0 # Fallback if unknown
            life_fraction_health.append(lf)
            
        life_fraction_health = np.array(life_fraction_health, dtype=np.float32)
        health_idx = np.array([e.health_index for e in experiences])
        sv_norms = np.array([np.linalg.norm(e.state_vector) for e in experiences])
        
        def get_sensor(s_name: str) -> np.ndarray:
            return np.array([e.metadata.get("sensors", {}).get(s_name, 0.0) for e in experiences])
        
        s2, s3, s4 = get_sensor("s2"), get_sensor("s3"), get_sensor("s4")
        s9, s14 = get_sensor("s9"), get_sensor("s14")
        s7, s11, s15 = get_sensor("s7"), get_sensor("s11"), get_sensor("s15")
        
        idx_20 = max(1, int(len(experiences) * 0.8))
        
        dna = np.zeros(DNA_DIM, dtype=np.float32)
        
        # 1. Health Pattern (3 dims) - uses life_fraction_health (unclipped)
        dna[0] = self._slope(sv_norms)
        dna[1] = self._slope(life_fraction_health)
        dna[2] = float(np.var(life_fraction_health)) if len(life_fraction_health) > 1 else 0.0
        
        # 2. Thermal Profile (3 dims)
        dna[3] = self._slope(s2)
        dna[4] = self._slope(s3)
        dna[5] = self._slope(s4)
        
        # 3. Power Signature (2 dims)
        dna[6] = self._slope(s9)
        dna[7] = self._slope(s14)
        
        # 4. Failure Signature (last 20%) (8 dims) - uses clipped health_index
        dna[8] = self._slope(health_idx[idx_20:])
        dna[9] = self._slope(sv_norms[idx_20:])
        dna[10] = self._slope(s2[idx_20:])
        dna[11] = self._slope(s3[idx_20:])
        dna[12] = self._slope(s4[idx_20:])
        dna[13] = self._slope(s7[idx_20:])
        dna[14] = self._slope(s11[idx_20:])
        dna[15] = self._slope(s15[idx_20:])
        
        return dna

    def store_dna(
        self,
        domain: str,
        machine_id: str,
        dna_vector: np.ndarray,
        components: Optional[Dict[str, Any]] = None,
        n_cycles_used: int = 0
    ) -> str:
        """
        Normalizes and stores the dna_vector into the machine_dna table.
        Uses UPSERT.
        """
        raw_vec = self._validate_vector(dna_vector)
        norm_vec = self._normalize(raw_vec)
        comp = components or {}
        
        pool = self._get_pool()
        with pool.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO machine_dna 
                    (domain, machine_id, dna_embedding, components, n_cycles_used)
                VALUES (%s, %s, %s::vector, %s, %s)
                ON CONFLICT (domain, machine_id) DO UPDATE SET
                    computed_at = NOW(),
                    dna_embedding = EXCLUDED.dna_embedding,
                    components = EXCLUDED.components,
                    n_cycles_used = EXCLUDED.n_cycles_used
                RETURNING id
                """,
                (domain, machine_id, self._to_pg_vec(norm_vec), json.dumps(comp), n_cycles_used)
            ).fetchone()
            conn.commit()
            
        return str(row[0])
    
    def get_dna(self, domain: str, machine_id: str) -> Optional[np.ndarray]:
        """
        Retrieves the Machine DNA vector for a specific unit.
        """
        pool = self._get_pool()
        with pool.connection() as conn:
            row = conn.execute(
                "SELECT dna_embedding FROM machine_dna WHERE domain = %s AND machine_id = %s",
                (domain, machine_id)
            ).fetchone()
            if row:
                return self._from_pg_vec(row[0])
            return None
    
    def retrieve_similar(
        self,
        dna_vector: np.ndarray,
        k: int = 5,
        domain: Optional[str] = None
    ) -> List[MachineDNA]:
        """
        Normalizes the dna_vector and retrieves the top-k most similar Machine DNAs.
        """
        raw_vec = self._validate_vector(dna_vector)
        norm_vec = self._normalize(raw_vec)
        
        query = """
            SELECT id, domain, machine_id, dna_embedding, components, 
                   n_cycles_used, computed_at,
                   dna_embedding <=> %s::vector AS distance
            FROM machine_dna
        """
        params: List[Any] = [self._to_pg_vec(norm_vec)]
        
        if domain:
            query += " WHERE domain = %s"
            params.append(domain)
            
        query += " ORDER BY distance ASC LIMIT %s"
        params.append(k)
        
        pool = self._get_pool()
        results = []
        with pool.connection() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            for row in rows:
                results.append(MachineDNA(
                    id=str(row[0]),
                    domain=row[1],
                    machine_id=row[2],
                    dna_embedding=self._from_pg_vec(row[3]),
                    components=row[4] if isinstance(row[4], dict) else json.loads(row[4]),
                    n_cycles_used=row[5],
                    computed_at=row[6],
                    similarity=float(row[7])
                ))
        return results

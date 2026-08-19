"""
Transfer Study Engine — ATLAS Cross-Domain Representation Discrepancy (Month 7 Week 2)
====================================================================================
Implements mathematical diagnostics to evaluate representation alignment, distribution
divergence, and negative transfer risk across heterogeneous machine domains.

Literature Grounding & Methodology:
  - Maximum Mean Discrepancy (MMD): Gretton et al. (2012), "A Kernel Two-Sample Test"
    Non-parametric kernel metric measuring the statistical divergence between domain
    distributions in the canonical 32-dimensional latent embedding space.
  - Transfer Component Analysis Metrics: Pan et al. (2011), "Domain Adaptation via Transfer Component Analysis"
  - Centroid Cosine Alignment: Measures directional clustering of domain representations.
  - Negative Transfer Index (NTI): Quantifies trajectory variance inflation from unadapted cross-domain retrieval.

Architectural Rule:
  This subsystem is purely a diagnostic and measurement tool. It evaluates latent
  spaces produced by trained domain models. It strictly enforces that all evaluated
  domains have real trained encoders before full study execution.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("ATLAS.TransferStudy")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = _PROJECT_ROOT / "data" / "models"
CANONICAL_DOMAINS = ["cmapss", "laptop", "mobile", "server"]


@dataclass
class DomainProvenance:
    """Explicit tracking of data source and model training state for a domain."""
    domain: str
    is_trained: bool
    checkpoint_name: Optional[str]
    n_samples: int
    data_source_type: str  # 'benchmark_ground_truth' | 'live_telemetry' | 'simulation_profile'
    notes: str = ""


@dataclass
class TransferStudyResult:
    """Aggregated results of the cross-domain representation discrepancy study."""
    domains: List[str]
    cosine_similarity_matrix: Dict[str, Dict[str, float]]
    mmd_divergence_matrix: Dict[str, Dict[str, float]]
    negative_transfer_indices: Dict[str, float]
    provenance: Dict[str, DomainProvenance]
    timestamp: str
    methodology_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


from scipy.spatial.distance import cdist


class TransferStudyEngine:
    """
    Mathematical engine for cross-domain representation analysis.
    Implements MMD (RBF kernel), Pairwise Centroid Cosine Similarity, and NTI.
    """

    def __init__(self, models_dir: Optional[Path] = None):
        self.models_dir = Path(models_dir) if models_dir else MODELS_DIR

    @staticmethod
    def compute_centroid(embeddings: np.ndarray) -> np.ndarray:
        """Computes the mean centroid vector of an embedding matrix."""
        if embeddings.ndim != 2:
            raise ValueError(f"Embeddings must be 2D array (N, D), got shape {embeddings.shape}")
        if len(embeddings) == 0:
            raise ValueError("Embeddings matrix cannot be empty")
        return np.mean(embeddings, axis=0)

    @classmethod
    def compute_cosine_similarity(cls, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Computes cosine similarity between two 1D vectors: (a . b) / (||a|| * ||b||)."""
        vec_a = np.asarray(vec_a, dtype=np.float64).flatten()
        vec_b = np.asarray(vec_b, dtype=np.float64).flatten()

        if vec_a.shape != vec_b.shape:
            raise ValueError(f"Vector dimensions mismatch: {vec_a.shape} vs {vec_b.shape}")

        norm_a = float(np.linalg.norm(vec_a))
        norm_b = float(np.linalg.norm(vec_b))

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        dot = float(np.dot(vec_a, vec_b))
        sim = dot / (norm_a * norm_b)
        # Numerical clamping to exact [-1.0, 1.0]
        return float(np.clip(sim, -1.0, 1.0))

    @classmethod
    def compute_cosine_similarity_matrix(
        cls,
        domain_embeddings: Dict[str, np.ndarray],
    ) -> Dict[str, Dict[str, float]]:
        """
        Computes the symmetric NxN pairwise centroid cosine similarity matrix.
        Guarantees:
          - S(d, d) == 1.0
          - S(d1, d2) == S(d2, d1)
          - S(d1, d2) in [-1.0, 1.0]
        """
        domains = list(domain_embeddings.keys())
        centroids = {d: cls.compute_centroid(domain_embeddings[d]) for d in domains}
        matrix: Dict[str, Dict[str, float]] = {}

        for d1 in domains:
            matrix[d1] = {}
            for d2 in domains:
                if d1 == d2:
                    matrix[d1][d2] = 1.0
                else:
                    sim = cls.compute_cosine_similarity(centroids[d1], centroids[d2])
                    matrix[d1][d2] = round(sim, 6)

        return matrix

    @classmethod
    def compute_rbf_kernel_matrix(
        cls,
        x: np.ndarray,
        y: np.ndarray,
        gamma: float,
    ) -> np.ndarray:
        """Computes RBF kernel K(x, y) = exp(-gamma * ||x - y||^2) using cdist."""
        dists_sq = cdist(x, y, metric="sqeuclidean")
        return np.exp(-gamma * dists_sq)

    @classmethod
    def estimate_median_bandwidth(cls, x: np.ndarray, y: np.ndarray) -> float:
        """
        Computes median Euclidean distance heuristic across pooled samples for RBF bandwidth sigma.
        Returns gamma = 1 / (2 * sigma^2).
        """
        pooled = np.vstack([x, y])
        n = len(pooled)
        if n <= 1:
            return 1.0

        # Subsample if large to avoid O(N^2) memory
        if n > 500:
            idx = np.random.choice(n, size=500, replace=False)
            pooled = pooled[idx]
            n = 500

        pairwise_dists = cdist(pooled, pooled, metric="euclidean")
        upper_tri_dists = pairwise_dists[np.triu_indices(n, k=1)]

        median_dist = float(np.median(upper_tri_dists)) if len(upper_tri_dists) > 0 else 1.0
        if median_dist == 0.0:
            median_dist = 1.0

        sigma = median_dist
        gamma = 1.0 / (2.0 * (sigma ** 2))
        return float(gamma)

    @classmethod
    def compute_mmd(
        cls,
        x: np.ndarray,
        y: np.ndarray,
        gamma: Optional[float] = None,
    ) -> float:
        """
        Computes Maximum Mean Discrepancy (MMD) with RBF kernel between distributions X and Y.
        MMD^2(X, Y) = (1/n^2) sum(K_xx) - (2/nm) sum(K_xy) + (1/m^2) sum(K_yy)

        Guarantees:
          - MMD(X, X) == 0.0
          - MMD(X, Y) == MMD(Y, X) >= 0.0
        """
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)

        if x.ndim != 2 or y.ndim != 2:
            raise ValueError(f"Arrays must be 2D, got x={x.shape}, y={y.shape}")
        if x.shape[1] != y.shape[1]:
            raise ValueError(f"Dimension mismatch: x feature_dim={x.shape[1]} vs y feature_dim={y.shape[1]}")

        n = len(x)
        m = len(y)
        if n == 0 or m == 0:
            raise ValueError("Arrays cannot be empty for MMD computation")

        if gamma is None:
            gamma = cls.estimate_median_bandwidth(x, y)

        k_xx = cls.compute_rbf_kernel_matrix(x, x, gamma)
        k_yy = cls.compute_rbf_kernel_matrix(y, y, gamma)
        k_xy = cls.compute_rbf_kernel_matrix(x, y, gamma)

        mmd_sq = float(np.mean(k_xx) - 2.0 * np.mean(k_xy) + np.mean(k_yy))

        # Numerical clamping to 0 for self-comparisons or near-zero float rounding
        mmd_sq_clamped = max(0.0, mmd_sq)
        return float(np.sqrt(mmd_sq_clamped))

    @classmethod
    def compute_mmd_matrix(
        cls,
        domain_embeddings: Dict[str, np.ndarray],
        gamma: Optional[float] = None,
    ) -> Dict[str, Dict[str, float]]:
        """
        Computes full symmetric 4x4 MMD divergence matrix across all domain distributions.
        """
        domains = list(domain_embeddings.keys())
        matrix: Dict[str, Dict[str, float]] = {}

        for d1 in domains:
            matrix[d1] = {}
            for d2 in domains:
                if d1 == d2:
                    matrix[d1][d2] = 0.0
                else:
                    mmd_val = cls.compute_mmd(domain_embeddings[d1], domain_embeddings[d2], gamma=gamma)
                    matrix[d1][d2] = round(mmd_val, 6)

        return matrix

    @classmethod
    def compute_negative_transfer_index(
        cls,
        within_domain_ruls: np.ndarray,
        cross_domain_ruls: np.ndarray,
    ) -> float:
        """
        Computes Negative Transfer Index (NTI).
        Measures variance inflation resulting from unadapted cross-domain retrieval:
          NTI = (Var(Cross_Domain) - Var(Within_Domain)) / (Var(Within_Domain) + 1.0)
        """
        within_var = float(np.var(within_domain_ruls)) if len(within_domain_ruls) > 1 else 0.0
        cross_var = float(np.var(cross_domain_ruls)) if len(cross_domain_ruls) > 1 else 0.0

        nti = (cross_var - within_var) / (within_var + 1.0)
        return float(round(nti, 6))

    def check_domain_training_status(self, domain: str) -> bool:
        """
        Checks whether a domain has a real, trained WorldModel checkpoint on disk.
        Returns False if only zero-shot / untrained fallback projection is available.
        """
        if domain == "cmapss":
            return (self.models_dir / "best_model.pt").exists() or (self.models_dir / "cmapss_world_model.pt").exists()

        target_file = self.models_dir / f"{domain}_world_model.pt"
        return target_file.exists()

    def assert_all_domains_trained(self, domains: Optional[List[str]] = None) -> List[str]:
        """
        Structural safety guard: raises RuntimeError if any domain lacks a trained checkpoint.
        """
        target_domains = domains or CANONICAL_DOMAINS
        untrained = [d for d in target_domains if not self.check_domain_training_status(d)]
        if untrained:
            raise RuntimeError(
                f"Cannot execute Cross-Domain Transfer Study — domains {untrained} still use "
                f"untrained zero-shot fallback projections, not trained domain models. "
                f"Step 1 pre-training must be completed first to produce meaningful representations. "
                f"See ATLAS_PROJECT_CONTEXT.md decisions log."
            )
        return target_domains

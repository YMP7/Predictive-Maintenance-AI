"""
scripts/attribution_faithfulness.py: deletion test for the occlusion attribution (the "Explainable" evidence).

For each domain with a trained World Model, the Explainability Engine ranks the sensors of a window by
occlusion attribution. We then mask the top-k ranked sensors, and separately k random sensors, using the
engine's own occlusion baseline, and measure how far the model output moves. A faithful attribution moves
the output more when its top-ranked sensors are removed than when random ones are.

Windows per domain:
  cmapss                  the 100 NASA C-MAPSS FD001 test units, terminal 30-cycle window
  modbus                  the 50 held-out SIMULATED pump units of server/atlas/train_pump_rul.py
  laptop, mobile, server  100 held-out windows of each domain's SIMULATED workload profile

Uses only public methods of the pipeline (WorldModel.predict, ExplanationEngine.calculate_feature_attribution);
nothing about the models changes. Seeded, so the result is reproducible.

Usage:
    python scripts/attribution_faithfulness.py            -> data/attribution_faithfulness.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Callable, Dict, List, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

K_VALUES = [1, 2, 3, 5]
SEED = 42
RANDOM_DRAWS = 20


def _masked(window: np.ndarray, cols: Sequence[int], baseline: Sequence[float] | None = None) -> np.ndarray:
    w = np.array(window, copy=True)
    for c in cols:
        w[:, c] = 0.0 if baseline is None else baseline[c]  # the engine's occlusion baseline
    return w


def deletion_curve(predict: Callable[[np.ndarray], float], window: np.ndarray, ranking: Sequence[int],
                   k_values: Sequence[int], rng: np.random.Generator,
                   random_draws: int = RANDOM_DRAWS, baseline: Sequence[float] | None = None) -> Dict[int, Dict[str, float]]:
    """|change in RUL| when the top-k ranked columns are masked, against the mean over k random columns."""
    base = predict(window)
    n = window.shape[1]
    out: Dict[int, Dict[str, float]] = {}
    for k in k_values:
        top = abs(predict(_masked(window, ranking[:k], baseline)) - base)
        rand = float(np.mean([abs(predict(_masked(window, rng.choice(n, size=k, replace=False), baseline)) - base)
                              for _ in range(random_draws)]))
        out[k] = {"top": round(float(top), 6), "random": round(rand, 6)}
    return out


def summarise(per_unit: List[Dict[int, Dict[str, float]]], k_values: Sequence[int]) -> Dict[str, Dict[str, float]]:
    out = {}
    for k in k_values:
        top = [u[k]["top"] for u in per_unit]
        rnd = [u[k]["random"] for u in per_unit]
        out[f"k{k}"] = {"mean_abs_delta_top": round(float(np.mean(top)), 4),
                        "mean_abs_delta_random": round(float(np.mean(rnd)), 4),
                        "top_beats_random_pct": round(100.0 * float(np.mean([t > r for t, r in zip(top, rnd)])), 1),
                        "n_units": len(per_unit)}
    return out


def domain_windows(domain: str) -> tuple[str, List[np.ndarray]]:
    """(description, windows in the model's column order) for one domain."""
    from server.adapters.domain_profile import PRIMARY_DOMAIN, get_profile

    profile = get_profile(domain)
    if domain == PRIMARY_DOMAIN:
        from server.adapters.cmapss_adapter import INFORMATIVE_SENSORS, CMAPSSAdapter
        from server.atlas.world_model import prepare_window

        dim = len(INFORMATIVE_SENSORS)
        test = CMAPSSAdapter(data_dir=ROOT / "data" / "cmapss", subset="FD001", split="test")
        test.connect()
        out = []
        for unit in sorted(test.machine_ids):
            readings = test.get_unit_history(unit)
            if readings:
                out.append(np.asarray(prepare_window([r.feature_vector for r in readings[-30:]], seq_len=30, feature_dim=dim),
                                      dtype=np.float32).reshape(30, dim))
        test.disconnect()
        return "NASA C-MAPSS FD001 test set, terminal 30-cycle window per unit", out
    if profile.simulated_run_to_failure:
        from server.atlas.train_pump_rul import datasets

        return "SIMULATED pump run-to-failure, last 30-cycle window of each held-out unit", list(datasets()["X_test"])
    from server.atlas.pretrain_domain import DOMAIN_FEATURE_MAP, DomainDatasetGenerator

    X, _, _ = DomainDatasetGenerator.get_dataset(domain)
    cols = [DOMAIN_FEATURE_MAP[domain].index(f) for f in profile.features]
    held_out = X[1000:][:, :, cols]  # the validation part the model never trained on
    return "SIMULATED workload profile, 100 held-out windows", list(held_out[np.linspace(0, len(held_out) - 1, 100).astype(int)])


def run_domain(domain: str) -> Dict | None:
    from server.adapters.domain_profile import get_profile
    from server.atlas.explain import ExplanationEngine, feature_layout
    from server.atlas.world_model import MODELS_DIR, WorldModel, prepare_window

    path = next((Path(MODELS_DIR) / f for f in get_profile(domain).checkpoints if (Path(MODELS_DIR) / f).exists()), None)
    if path is None:
        return None
    model = WorldModel.load(path)
    model.eval()
    dataset, windows = domain_windows(domain)
    dim = windows[0].shape[1]
    names, baseline = feature_layout(domain, dim)

    def predict(w: np.ndarray) -> float:
        return float(np.asarray(model.predict(prepare_window(w, seq_len=30, feature_dim=dim)).rul_pred).reshape(-1)[0])

    engine = ExplanationEngine()
    ace = SimpleNamespace(get_world_model=lambda d, n: model)
    rng = np.random.default_rng(SEED)
    k_values = [k for k in K_VALUES if k < dim]
    per_unit, first = [], {}
    for window in windows:
        attributions, _ = engine.calculate_feature_attribution(window, ace, predict(window), domain)
        ranking = [a["sensor_index"] for a in attributions]
        first[names[ranking[0]]] = first.get(names[ranking[0]], 0) + 1
        per_unit.append(deletion_curve(predict, window, ranking, k_values, rng, baseline=baseline))
    return {
        "dataset": dataset,
        "model": path.name,
        "provenance": "NASA benchmark" if get_profile(domain).run_to_failure else "SIMULATED",
        "n_features": dim,
        "output": "RUL in cycles" if get_profile(domain).rul_scale else "0-1 estimate",
        "k_values": k_values,
        "summary": summarise(per_unit, k_values),
        "top_ranked_sensor_counts": dict(sorted(first.items(), key=lambda kv: -kv[1])),
    }


def main() -> int:
    from server.adapters.domain_profile import DOMAIN_PROFILES, PRIMARY_DOMAIN

    domains = {d: r for d in DOMAIN_PROFILES if (r := run_domain(d)) is not None}
    primary = domains[PRIMARY_DOMAIN]
    result = {
        # top-level fields describe the benchmark domain, as before
        "dataset": primary["dataset"],
        "model": primary["model"],
        "method": "Deletion test: mask the top-k sensors ranked by occlusion attribution vs k random sensors "
                  f"(mean of {RANDOM_DRAWS} draws); occlusion = the column set to its population mean, as in the "
                  "Explainability Engine. k = 1 is true by construction; the evidence is k >= 2.",
        "seed": SEED,
        "k_values": primary["k_values"],
        "summary": primary["summary"],
        "domains": domains,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    out = ROOT / "data" / "attribution_faithfulness.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({d: r["summary"] for d, r in domains.items()}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

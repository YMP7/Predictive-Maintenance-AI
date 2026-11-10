"""
scripts/attribution_faithfulness.py: deletion test for the occlusion attribution (the "Explainable" evidence).

For each of the 100 NASA C-MAPSS FD001 test units (terminal 30-cycle window), the Explainability Engine ranks the
14 sensors by occlusion attribution. We then mask the top-k ranked sensors, and separately k random sensors, using
the engine's own occlusion (zeroing the whole column), and measure how far the predicted RUL moves. A faithful
attribution moves the prediction more when its top-ranked sensors are removed than when random ones are.

Uses only public methods of the frozen pipeline (WorldModel.predict, ExplanationEngine.calculate_feature_attribution);
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


def _masked(window: np.ndarray, cols: Sequence[int]) -> np.ndarray:
    w = np.array(window, copy=True)
    w[:, list(cols)] = 0.0  # the engine's occlusion baseline
    return w


def deletion_curve(predict: Callable[[np.ndarray], float], window: np.ndarray, ranking: Sequence[int],
                   k_values: Sequence[int], rng: np.random.Generator,
                   random_draws: int = RANDOM_DRAWS) -> Dict[int, Dict[str, float]]:
    """|change in RUL| when the top-k ranked columns are masked, against the mean over k random columns."""
    base = predict(window)
    n = window.shape[1]
    out: Dict[int, Dict[str, float]] = {}
    for k in k_values:
        top = abs(predict(_masked(window, ranking[:k])) - base)
        rand = float(np.mean([abs(predict(_masked(window, rng.choice(n, size=k, replace=False))) - base)
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


def main() -> int:
    from server.adapters.cmapss_adapter import INFORMATIVE_SENSORS, CMAPSSAdapter

    from server.atlas.explain import ExplanationEngine
    from server.atlas.world_model import MODELS_DIR, WorldModel, prepare_window

    model = WorldModel.load(Path(MODELS_DIR) / "best_model.pt")
    model.eval()
    dim = len(INFORMATIVE_SENSORS)

    def predict(w: np.ndarray) -> float:
        return float(np.asarray(model.predict(prepare_window(w, seq_len=30, feature_dim=dim)).rul_pred).reshape(-1)[0])

    test = CMAPSSAdapter(data_dir=ROOT / "data" / "cmapss", subset="FD001", split="test")
    test.connect()
    engine = ExplanationEngine()
    ace = SimpleNamespace(world_model=model)
    rng = np.random.default_rng(SEED)
    per_unit = []
    for unit in sorted(test.machine_ids):
        readings = test.get_unit_history(unit)
        if not readings:
            continue
        window = np.asarray(prepare_window([r.feature_vector for r in readings[-30:]], seq_len=30, feature_dim=dim),
                            dtype=np.float32).reshape(30, dim)
        attributions, _ = engine.calculate_feature_attribution(window, ace, predict(window))
        ranking = [a["sensor_index"] for a in attributions]
        per_unit.append(deletion_curve(predict, window, ranking, K_VALUES, rng))
    test.disconnect()

    result = {
        "dataset": "NASA C-MAPSS FD001 test set, terminal 30-cycle window per unit",
        "model": "best_model.pt",
        "method": "Deletion test: mask the top-k sensors ranked by occlusion attribution vs k random sensors "
                  f"(mean of {RANDOM_DRAWS} draws); occlusion = zeroed column, as in the Explainability Engine",
        "seed": SEED,
        "k_values": K_VALUES,
        "summary": summarise(per_unit, K_VALUES),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    out = ROOT / "data" / "attribution_faithfulness.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

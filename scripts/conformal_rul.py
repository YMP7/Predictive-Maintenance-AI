"""
scripts/conformal_rul.py: split-conformal RUL interval for the shipped C-MAPSS World Model.

Calibration: the 20 FD001 training engines that server/atlas/train_rul.py held out as validation
(seed 42, 80/20 split by engine). The model never trained on them; they only chose the early-stopping
epoch. Every window of those engines, residual against the capped training target.

Check: the 100 FD001 test engines, terminal 30-cycle window, true RUL (the benchmark protocol).

Writes:
    data/models/cmapss_conformal.json   q for the engine, tied to the checkpoint's SHA-256
    data/conformal_coverage.json        empirical coverage and width on the test set

Usage:
    python scripts/conformal_rul.py
"""

from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ALPHAS = [0.1, 0.2]
ENGINE_ALPHA = 0.1
SEED = 42  # train_rul.py default; reproduces its validation engines


def wilson(k: int, n: int, z: float = 1.96) -> list:
    """95% Wilson interval for a coverage of k hits in n, in percent."""
    p = k / n
    centre, half = (p + z * z / (2 * n)), z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round(100.0 * (centre - half) / (1 + z * z / n), 1), round(100.0 * (centre + half) / (1 + z * z / n), 1)]


def main() -> None:
    import torch

    from server.adapters.cmapss_adapter import INFORMATIVE_SENSORS, CMAPSSAdapter
    from server.atlas.rul_engine import conformal_path, conformal_quantile, file_sha256
    from server.atlas.train_rul import build_windows
    from server.atlas.world_model import MODELS_DIR, WorldModel, prepare_window

    model_path = Path(MODELS_DIR) / "cmapss_world_model.pt"
    model = WorldModel.load(model_path)
    model.eval()
    seq_len, dim = model.config.seq_len, len(INFORMATIVE_SENSORS)

    train = CMAPSSAdapter(subset="FD001", split="train")
    train.connect()
    ids = sorted(train.machine_ids)
    random.Random(SEED).shuffle(ids)
    cal_ids = ids[int(len(ids) * 0.8):]
    X_cal, y_cal = build_windows(train, seq_len, target_ids=cal_ids)
    train.disconnect()

    with torch.no_grad():
        p_cal = model(torch.tensor(X_cal)).rul_pred.numpy().reshape(-1)
    r_cal = y_cal - p_cal

    test = CMAPSSAdapter(subset="FD001", split="test")
    test.connect()
    y_test, p_test = [], []
    with torch.no_grad():
        for unit in sorted(test.machine_ids):
            readings = test.get_unit_history(unit)
            if not readings:
                continue
            w = prepare_window([r.feature_vector for r in readings[-seq_len:]], seq_len, dim)
            p_test.append(float(model(torch.tensor(w, dtype=torch.float32).unsqueeze(0)).rul_pred.item()))
            y_test.append(float(readings[-1].rul_label or 0.0))
    test.disconnect()
    y_test, p_test = np.array(y_test), np.array(p_test)

    results = {}
    for a in ALPHAS:
        q = conformal_quantile(r_cal, a)
        lo, hi = np.maximum(0.0, p_test - q), p_test + q
        covered = (y_test >= lo) & (y_test <= hi)
        results[f"{int(round((1 - a) * 100))}"] = {
            "alpha": a,
            "q_cycles": round(q, 3),
            "test_coverage_pct": round(100.0 * float(covered.mean()), 1),
            "test_coverage_95ci_pct": wilson(int(covered.sum()), len(covered)),
            "mean_width_cycles": round(float(np.mean(hi - lo)), 2),
            # the costly miss: the engine fails before the interval's lower bound
            "test_true_below_lower_pct": round(100.0 * float((y_test < lo).mean()), 1),
            "test_true_above_upper_pct": round(100.0 * float((y_test > hi).mean()), 1),
        }

    sha = file_sha256(model_path)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    q_engine = results[f"{int(round((1 - ENGINE_ALPHA) * 100))}"]["q_cycles"]
    conformal_path("cmapss").write_text(json.dumps({
        "domain": "cmapss", "alpha": ENGINE_ALPHA, "q_cycles": q_engine,
        "n_calibration": int(len(r_cal)), "calibration_engines": len(cal_ids),
        "model_sha256": sha, "created": now,
    }, indent=2) + "\n")

    summary = {
        "method": "split conformal, symmetric absolute residual",
        "model": "data/models/cmapss_world_model.pt", "model_sha256": sha,
        "calibration": f"FD001 train engines held out as validation by train_rul.py (seed {SEED}): "
                       f"{len(cal_ids)} engines, {len(r_cal)} windows, target capped at 125",
        "test": f"FD001 test set, {len(y_test)} engines, terminal {seq_len}-cycle window, true RUL",
        "test_rmse": round(float(np.sqrt(np.mean((y_test - p_test) ** 2))), 4),
        "levels": results,
        "caveat": "Calibration windows span whole engine lives and are capped at 125; test windows are "
                  "truncated trajectories with uncapped RUL, so exchangeability is approximate. "
                  "The empirical test coverage is the number to trust. q is never tuned on the test set. "
                  "Binning q by predicted RUL (0-40, 40-80, 80+) was tried and gave 83% at 90%, so the "
                  "single global q is kept.",
        "created": now,
    }
    out = ROOT / "data" / "conformal_coverage.json"
    out.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

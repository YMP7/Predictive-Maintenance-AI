"""
scripts/run_retrain_history.py: a recorded series of gated retraining runs (the "Adaptive" evidence).

Runs the Learning Engine several times per domain, with different seeds and learning rates, and
records what the 3% promotion gate did with each candidate. Every run works on a scratch copy of
the domain's checkpoint, so the shipped models in data/models/ (and every number measured on them)
stay exactly as they are. Runs within a domain are sequential on the same scratch copy: a promoted
candidate becomes the model the next run starts from, as it would in production.

Data per domain (stated in every row):
  cmapss                  NASA C-MAPSS FD001 training windows, 90/10 train/validation
  modbus                  SIMULATED pump run-to-failure (server/adapters/pump_degradation.py)
  laptop, mobile, server  SIMULATED workload profiles, stress-score target

The gate scores on the validation part only. For C-MAPSS the FD001 test RMSE is also recorded for
each run, for reporting; it never decides a promotion.

Usage:
    python scripts/run_retrain_history.py            -> data/retrain_history.json
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

EPOCHS = 3
# (learning rate, seed): from an aggressive step that the gate should stop to a careful fine-tune.
PLAN = [(1e-3, 0), (1e-3, 1), (3e-4, 0), (3e-4, 1), (1e-4, 0), (1e-4, 1), (3e-5, 0), (3e-5, 1)]
DOMAIN_PLAN = [(1e-3, 0), (1e-4, 0), (1e-4, 1), (3e-5, 0)]
SOURCE_LABEL = {"benchmark": "NASA C-MAPSS FD001", "simulated_failure": "SIMULATED run-to-failure",
                "simulated_profile": "SIMULATED workload profile"}


def run_domain(domain: str, plan, scratch: Path) -> list:
    from server.adapters.domain_profile import PRIMARY_DOMAIN, get_profile
    from server.atlas.learning_engine import LearningEngine
    from server.atlas.world_model import MODELS_DIR, WorldModel

    source = next((MODELS_DIR / f for f in get_profile(domain).checkpoints if (MODELS_DIR / f).exists()), None)
    if source is None:
        return []
    path = scratch / f"{domain}.pt"
    shutil.copy2(source, path)
    engine = LearningEngine(model_path=path, log_events=False)
    rows = []
    for i, (lr, seed) in enumerate(plan, 1):
        r = engine.retrain_domain(domain=domain, trigger_reason="scheduled", epochs=EPOCHS, lr=lr, seed=seed)
        row = {"domain": domain, "run": i, "data": SOURCE_LABEL[engine.data_source(domain)], "lr": lr, "seed": seed,
               "epochs": r.epochs_run, "n_samples": r.n_samples, "val_rmse_before": round(r.rmse_before, 4),
               "val_rmse_after": round(r.rmse_after, 4), "promoted": bool(r.success), "notes": r.notes}
        if domain == PRIMARY_DOMAIN:
            # report only: the test split never reaches the gate
            row["test_rmse_active_after_run"] = round(engine.evaluate_cmapss_benchmark(WorldModel.load(path)), 4)
        rows.append(row)
        print(f"{domain:7s} run {i} lr {lr:g} seed {seed}: {r.rmse_before:.4f} -> {r.rmse_after:.4f} "
              f"{'PROMOTED' if r.success else 'REJECTED'}")
    return rows


def main() -> int:
    from server.adapters.domain_profile import DOMAIN_PROFILES, PRIMARY_DOMAIN

    runs = []
    with tempfile.TemporaryDirectory() as tmp:
        for domain in DOMAIN_PROFILES:
            runs += run_domain(domain, PLAN if domain == PRIMARY_DOMAIN else DOMAIN_PLAN, Path(tmp))
    by_domain = {}
    for r in runs:
        d = by_domain.setdefault(r["domain"], {"runs": 0, "promoted": 0, "rejected": 0, "data": r["data"]})
        d["runs"] += 1
        d["promoted" if r["promoted"] else "rejected"] += 1
    for domain, d in by_domain.items():
        mine = [r for r in runs if r["domain"] == domain]
        d["val_rmse_start"] = mine[0]["val_rmse_before"]
        d["val_rmse_best_promoted"] = min([r["val_rmse_after"] for r in mine if r["promoted"]], default=None)
    result = {
        "method": f"Sequential gated retraining on scratch copies of the shipped checkpoints, {EPOCHS} epochs per run. "
                  "A candidate is promoted only if its validation RMSE is within 3% of the best ever promoted. "
                  "Shipped checkpoints are not modified.",
        "gate_tolerance": 0.03,
        "total_runs": len(runs),
        "promoted": sum(r["promoted"] for r in runs),
        "rejected": sum(not r["promoted"] for r in runs),
        "by_domain": by_domain,
        "runs": runs,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    (ROOT / "data" / "retrain_history.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("total_runs", "promoted", "rejected", "by_domain")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

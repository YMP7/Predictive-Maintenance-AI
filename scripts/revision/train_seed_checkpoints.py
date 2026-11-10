"""Retrain FD001 for seeds 42-46 and keep each checkpoint (R4: r_s across seeds)."""
import shutil, json
from _env import ROOT
from server.atlas.train_rul import train

M = ROOT / "data" / "models"
out = {}
for s in [42, 43, 44, 45, 46]:
    m = train(subset="FD001", epochs=50, batch_size=256, lr=1e-3, seq_len=30,
              hidden_size=64, num_layers=2, dropout=0.2, quick=False, seed=s)
    shutil.copy(M / "best_model.pt", M / f"best_model_seed{s}.pt")
    out[s] = m["benchmark"]
    print("SEED", s, m["benchmark"], flush=True)
shutil.copy(M / "best_model_original.pt", M / "best_model.pt")  # restore paper checkpoint
shutil.copy(M / "cmapss_metrics_original.json", M / "cmapss_metrics.json")
(ROOT / "data" / "revision_seed_benchmarks.json").write_text(json.dumps(out, indent=2))

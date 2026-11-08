"""Revision figures for the IEEE paper: Fig. 4 (decision value) and Fig. 5 (3x3 compute retrieval).

Reads data/revision_r1_r3_r4.json (decision_grounding_reanalysis.py) and data/ablation_results.json.
Writes docs/paper/ieee/figure5.png and figure6.png (file names as referenced by paper.md).
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from _env import ROOT

OUT = ROOT / "docs" / "paper" / "ieee"
plt.rcParams.update({"font.family": "serif", "font.size": 8, "axes.spines.top": False, "axes.spines.right": False})

rev = json.loads((ROOT / "data" / "revision_r1_r3_r4.json").read_text())["paper"]
POL = [("fixed_rule", "Fixed\n<30"), ("cascade", "Cascade\n30/60"), ("tuned_threshold", "Tuned\nrule"), ("atlas", "ATLAS")]

# ---- Fig. 4: (a) total cost per policy, (b) ATLAS vs tuned rule across the sensitivity grid
fig, (a, b) = plt.subplots(1, 2, figsize=(7.0, 2.4), gridspec_kw={"width_ratios": [1.1, 1]})
x, w = np.arange(len(POL)), 0.38
for off, key, lab, col in ((-w / 2, "paper_cost_model", "Eq. (6)", "#555555"),
                           (w / 2, "with_discarded_life", "+ discarded life", "#aaaaaa")):
    vals = [rev["decision"][key]["breakdown"][p]["total"] for p, _ in POL]
    a.bar(x + off, vals, w, color=col, label=lab)
a.set_xticks(x, [l for _, l in POL]); a.set_ylabel("Total simulated cost ($)")
a.set_title("(a) Cost on 100 test units", fontsize=8); a.legend(frameon=False, fontsize=7)

sw = [s for s in rev["sensitivity"] if s["c_life"] == 0.0]
cf, tc = sorted({s["c_f"] for s in sw}), sorted({s["tau_continue"] for s in sw})
grid = np.array([[next(s["atlas_vs_tuned_threshold_pct"] for s in sw if s["c_f"] == f and s["tau_continue"] == t)
                  for f in cf] for t in tc])
lim = np.abs(grid).max()
im = b.imshow(grid, cmap="RdBu", vmin=-lim, vmax=lim, aspect="auto")
for i in range(len(tc)):
    for j in range(len(cf)):
        b.text(j, i, f"{grid[i, j]:+.0f}", ha="center", va="center", fontsize=7)
b.set_xticks(range(len(cf)), [str(f) for f in cf]); b.set_yticks(range(len(tc)), [str(t) for t in tc])
b.set_xlabel("Failure cost $C_f$"); b.set_ylabel(r"$\tau$(continue)")
b.set_title("(b) ATLAS saving vs. tuned rule (%)", fontsize=8)
fig.colorbar(im, ax=b, fraction=0.05)
fig.tight_layout(); fig.savefig(OUT / "figure5.png", dpi=300); plt.close(fig)

# ---- Fig. 5: 3x3 compute-domain retrieval inflation (query domain x encoder+memory domain)
inf = json.loads((ROOT / "data" / "ablation_results.json").read_text())["ablation_4"]["cross_compute_inflation_matrix"]
D = ["laptop", "mobile", "server"]
m = np.array([[inf[q][e] for e in D] for q in D])
fig, ax = plt.subplots(figsize=(3.3, 2.5))
ax.imshow(np.log10(m), cmap="Greys", vmin=0, vmax=np.log10(m.max()) * 1.3)
for i in range(3):
    for j in range(3):
        ax.text(j, i, f"{m[i, j]:.2f}×", ha="center", va="center", fontsize=8,
                color="white" if np.log10(m[i, j]) > 0.6 else "black")
ax.set_xticks(range(3), [d.capitalize() for d in D]); ax.set_yticks(range(3), [d.capitalize() for d in D])
ax.set_xlabel("Encoder, memory and labels from"); ax.set_ylabel("Query windows from")
fig.tight_layout(); fig.savefig(OUT / "figure6.png", dpi=300); plt.close(fig)
print("wrote figure5.png, figure6.png")

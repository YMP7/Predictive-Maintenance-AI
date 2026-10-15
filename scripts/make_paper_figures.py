"""Generate the figures for the ATLAS research paper from the committed result JSONs.

Usage: python scripts/make_paper_figures.py   -> writes docs/figures/paper/*.png
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "docs" / "figures" / "paper"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False, "savefig.dpi": 300, "savefig.bbox": "tight"})
BLUE, ORANGE, GREY, GREEN, RED = "#2f6db5", "#e07b28", "#8a8a8a", "#3a9a5b", "#c23b3b"
DOMAINS = ["cmapss", "laptop", "mobile", "server"]
LABEL = {"cmapss": "C-MAPSS", "laptop": "Laptop", "mobile": "Mobile", "server": "Server"}


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def save(fig, name):
    fig.savefig(OUT / name)
    plt.close(fig)
    print("wrote", OUT / name)


def fig_architecture():
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 64)
    ax.axis("off")

    def box(x, y, w, h, text, fc="#eef3fa", ec=BLUE, fs=6.3):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2",
                                    fc=fc, ec=ec, lw=1.1))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, linespacing=1.25)

    def arrow(x1, y1, x2, y2, text=None, dy=1.2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color="#444", lw=0.9, shrinkA=0, shrinkB=0))
        if text:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + dy, text, ha="center", fontsize=6.5, color="#444")

    ax.text(9, 61.5, "Machines", ha="center", fontsize=8, fontweight="bold", color="#333")
    srcs = [("C-MAPSS FD001\n(turbofan)", 51), ("Laptop\n(psutil)", 41),
            ("Mobile\n(Android / Termux)", 31), ("Server\n(SSH / simulation)", 21),
            ("Modbus TCP\n(industrial PLC)", 11)]
    for text, y in srcs:
        box(1, y, 16, 7.5, text, fc="#f4f4f4", ec=GREY)
        arrow(17.8, y + 3.75, 22.2, 33.75)
    box(23, 9, 12, 49.5, "Adapter\nlayer\n\nNormalized\nReading\n\nhealth index\n[0, 1]\n+ canonical\nfeatures")

    arrow(35.8, 46, 40.2, 46, "30 x D", dy=2)
    box(41, 41, 17, 10, "World model\n2-layer LSTM\n+ attention")
    arrow(58.8, 46, 63.2, 46, "z, RUL", dy=2)
    box(64, 41, 16, 10, "AMKB memory\npgvector cosine\nlabeled only")
    box(64, 26, 16, 10, "Machine DNA\n16-d fingerprint\n(z-scored)")
    arrow(72, 40.2, 72, 36.8)
    arrow(80.8, 46, 84.2, 46)
    box(85, 41, 14, 10, "Explainability\nconfidence C\nocclusion\nattribution")
    arrow(92, 40.2, 92, 36.8)
    box(85, 23, 14, 13, "Monte Carlo\nsimulation\nM = 1000\nGaussian\nclip [0, 125]")
    arrow(92, 22.2, 92, 18.8)
    box(78, 4, 21, 14, "Decision graph\n4 actions, lead times\n30 / 10 / 3 / 0 cycles\nrank: E[cost], P(fail),\nstd, name",
        fc="#fdf1e6", ec=ORANGE)

    box(41, 23, 17, 10, "Learning engine\nretrain -> gate\n(RMSE within 3%)\natomic promote", fc="#f1f8f3", ec=GREEN)
    arrow(49.5, 33.8, 49.5, 40.2)
    box(41, 4, 33, 13, "LLM agent safety gate\nlive alert (< 24 h) + exact fault match\n+ allowed action per fault\n"
        "-> Pending Approval -> human sign-off", fc="#fbeeee", ec=RED)
    arrow(77.2, 11, 74.8, 11)
    save(fig, "fig1_architecture.png")


def fig_multiseed():
    # Section 5.1 table values (five seeds, 42-46); literature row from Zheng et al. [2].
    rows = [("Linear\nhead", 15.34, 0.60, 426.07, 83.55, GREY),
            ("Attention\n(ATLAS)", 15.22, 0.31, 375.00, 21.93, BLUE),
            ("Literature\n[2]", 16.14, 0, 338, 0, "#c9c9c9")]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6))
    for ax, idx, ylabel, title in [(axes[0], 1, "RMSE (cycles)", "(a) RMSE, lower is better"),
                                   (axes[1], 3, "PHM score", "(b) PHM score, lower is better")]:
        vals = [r[idx] for r in rows]
        errs = [r[idx + 1] for r in rows]
        ax.bar(range(3), vals, color=[r[5] for r in rows], width=0.6)
        ax.errorbar(range(2), vals[:2], yerr=errs[:2], fmt="none", ecolor="black", capsize=4, lw=1)
        top = max(v + e for v, e in zip(vals, errs))
        for i, (v, e) in enumerate(zip(vals, errs)):
            ax.text(i, v + e + top * 0.02, f"{v:.2f}" + (f" ± {e:.2f}" if e else ""), ha="center", fontsize=7)
        ax.set_xticks(range(3), [r[0] for r in rows])
        ax.set_ylabel(ylabel)
        ax.set_ylim(0, top * 1.15)
        ax.set_title(title, fontsize=9)
    fig.tight_layout()
    save(fig, "fig3_multiseed_rmse_phm.png")


def fig_ablation_cost(ab):
    a1 = ab["ablation_1"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 2.9), gridspec_kw={"width_ratios": [1, 1.6]})
    vals = [a1["total_cost_pipeline_a"], a1["total_cost_pipeline_b"]]
    bars = ax1.bar(["Fixed threshold\n(RUL < 30)", "ATLAS\n(full pipeline)"], vals, color=[GREY, BLUE], width=0.55)
    for b, v in zip(bars, vals):
        ax1.text(b.get_x() + b.get_width() / 2, v + 60, f"${v:,.0f}", ha="center", fontsize=8)
    ax1.set_ylabel("Total simulated cost (100 units)")
    ax1.set_ylim(0, max(vals) * 1.18)
    ax1.set_title(f"(a) Fleet cost: -{a1['cost_reduction_percent']:.2f}%", fontsize=9)

    actions = ["CONTINUE_OPERATION", "SCHEDULE_MAINTENANCE_SOON", "SCHEDULE_MAINTENANCE_NOW", "REPLACE_IMMEDIATELY"]
    x = range(len(actions))
    w = 0.38
    ca = [a1["action_counts_a"][k] for k in actions]
    cb = [a1["action_counts_b"][k] for k in actions]
    ax2.bar([i - w / 2 for i in x], ca, w, color=GREY, label="Fixed threshold")
    ax2.bar([i + w / 2 for i in x], cb, w, color=BLUE, label="ATLAS")
    for i in x:
        ax2.text(i - w / 2, ca[i] + 1, ca[i], ha="center", fontsize=7)
        ax2.text(i + w / 2, cb[i] + 1, cb[i], ha="center", fontsize=7)
    ax2.set_xticks(list(x), ["Continue", "Maintain\nsoon", "Maintain\nnow", "Replace"])
    ax2.set_ylabel("Units")
    ax2.set_ylim(0, 88)
    ax2.legend(frameon=False, fontsize=7)
    ax2.set_title("(b) Recommended actions", fontsize=9)
    fig.tight_layout()
    save(fig, "fig5_ablation_cost_actions.png")


def heat(ax, m, names, title, cmap, vmin, vmax, suffix=""):
    im = ax.imshow(m, cmap=cmap, vmin=vmin, vmax=vmax)
    n = len(m)
    ax.set_xticks(range(n), names, rotation=30 if n == 4 else 0, ha="right" if n == 4 else "center")
    ax.set_yticks(range(n), names)
    for i in range(n):
        for j in range(n):
            v = m[i][j]
            dark = abs(v - (vmin + vmax) / 2) / (vmax - vmin) > 0.3 if vmin < 0 else (v - vmin) / (vmax - vmin) > 0.6
            ax.text(j, i, f"{v:.2f}{suffix}", ha="center", va="center", fontsize=7.5,
                    color="white" if dark else "black")
    ax.set_title(title, fontsize=9)
    for s in ax.spines.values():
        s.set_visible(False)
    return im


def fig_cross_domain(ts):
    names = [LABEL[d] for d in DOMAINS]
    mmd = [[ts["mmd_divergence_matrix"][a][b] for b in DOMAINS] for a in DOMAINS]
    cos = [[ts["cosine_similarity_matrix"][a][b] for b in DOMAINS] for a in DOMAINS]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.2))
    fig.colorbar(heat(ax1, mmd, names, "(a) MMD between latent distributions", "Blues", 0, 1.3),
                 ax=ax1, fraction=0.046, pad=0.04)
    fig.colorbar(heat(ax2, cos, names, "(b) Centroid cosine similarity", "RdBu_r", -1, 1),
                 ax=ax2, fraction=0.046, pad=0.04)
    fig.tight_layout()
    save(fig, "fig6_cross_domain_mmd_cosine.png")


def fig_retrieval(ab):
    a4 = ab["ablation_4"]
    t = a4["within_vs_cmapss_transfer"]
    comp = ["laptop", "mobile", "server"]
    names = [LABEL[d] for d in comp]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.0), gridspec_kw={"width_ratios": [1.3, 1]})
    w = 0.38
    x = range(len(comp))
    within = [t[d]["within_rmse"] for d in comp]
    cross = [t[d]["cross_cmapss_rmse"] for d in comp]
    ax1.bar([i - w / 2 for i in x], within, w, color=BLUE, label="Own-domain memory")
    ax1.bar([i + w / 2 for i in x], cross, w, color=ORANGE, label="C-MAPSS memory")
    for i, d in enumerate(comp):
        ax1.text(i + w / 2, cross[i] + 0.008, f"{t[d]['error_inflation_ratio']:.2f}x", ha="center", fontsize=7.5)
    ax1.set_xticks(list(x), names)
    ax1.set_ylabel("Retrieval RMSE (normalized [0, 1])")
    ax1.set_ylim(0, 0.33)
    ax1.legend(frameon=False, fontsize=7, loc="upper left")
    ax1.set_title("(a) Own vs C-MAPSS memory", fontsize=9)

    inf = [[a4["cross_compute_inflation_matrix"][q][m] for m in comp] for q in comp]
    im = heat(ax2, inf, names, "(b) Error inflation, compute domains", "Oranges", 0, 12, suffix="x")
    ax2.set_xlabel("Encoder / memory domain")
    ax2.set_ylabel("Query domain")
    fig.colorbar(im, ax=ax2, fraction=0.046, pad=0.04)
    fig.tight_layout()
    save(fig, "fig7_retrieval_transfer.png")


def fig_performance(bm, rp):
    stages = [("World model", bm["stage_2_world_model_ms"]["cmapss"]["mean_ms"]),
              ("AMKB retrieval (k=10)", bm["stage_3_amkb_retrieval_ms"]["k_10"]["mean_ms"]),
              ("Machine DNA", bm["stage_4_machine_dna_ms"]["mean_ms"]),
              ("Occlusion attribution", bm["stage_5_explainability_ms"]["mean_ms"]),
              ("Monte Carlo (M=1000)", bm["stage_6_simulation_ms"]["mean_ms"]),
              ("Decision graph", bm["stage_7_decision_graph_ms"]["mean_ms"])]
    e2e = bm["stage_8_end_to_end_ms"]["cmapss"]["mean_ms"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.0), gridspec_kw={"width_ratios": [1.1, 1]})
    names = [s[0] for s in stages][::-1]
    vals = [s[1] for s in stages][::-1]
    ax1.barh(names, vals, color=[ORANGE if "Occlusion" in n else BLUE for n in names])
    for i, v in enumerate(vals):
        ax1.text(v + 0.15, i, f"{v:.2f}" if v >= 0.01 else f"{v:.3f}", va="center", fontsize=7)
    ax1.set_xlabel("Mean latency per stage (ms)")
    ax1.set_xlim(0, max(vals) * 1.25)
    ax1.set_title(f"(a) C-MAPSS stages (end to end {e2e:.1f} ms)", fontsize=9)

    for ep, label, c in [("api_context", "/api/context", BLUE), ("api_decide", "/api/decide", ORANGE),
                         ("api_dna", "/api/dna", GREEN)]:
        tiers = list(rp["concurrent_load_profiles"][ep]["tiers"].values())
        ax2.plot([t["concurrency"] for t in tiers], [t["throughput_rps"] for t in tiers],
                 "o-", color=c, ms=3.5, lw=1.3, label=label)
    ax2.set_xscale("log", base=2)
    ax2.set_xticks([1, 2, 4, 8, 16, 32, 64], ["1", "2", "4", "8", "16", "32", "64"])
    ax2.set_xlabel("Concurrent clients")
    ax2.set_ylabel("Throughput (req/s)")
    ax2.legend(frameon=False, fontsize=7)
    ax2.set_title("(b) Throughput under load (0% errors)", fontsize=9)
    fig.tight_layout()
    save(fig, "fig8_system_performance.png")


if __name__ == "__main__":
    ab = load("ablation_results.json")
    fig_architecture()
    fig_multiseed()
    fig_ablation_cost(ab)
    fig_cross_domain(load("transfer_study_results.json"))
    fig_retrieval(ab)
    fig_performance(load("system_benchmark_results.json"), load("system_resource_profile.json"))

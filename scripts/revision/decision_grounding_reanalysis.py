"""Round-1 revision re-analysis (reviewer items R1, R3, R4) for the ATLAS IEEE paper.

R1  decision value: per-policy cost breakdown, stronger baselines (3-tier cascade and a
    threshold rule tuned on each checkpoint's held-out validation units), discarded-life cost, sensitivity sweep,
    paired bootstrap CI on the saving.
R3  leakage audit: the test-time memory holds training units only; the health index and the
    safety override are not on the evaluated path (asserted/recorded here).
R4  confidence: raw vs. normalized sigma^2, Spearman r_s with bootstrap CI, simple proxies,
    Monte Carlo interval coverage, all per checkpoint (paper checkpoint + seeds 42-46).

Reuses the exact loading/retrieval protocol of scripts/run_ablations.py (k=10 cosine
neighbors from the training memory, last window per test unit) and the decision rule of
server/atlas/{simulation,decision}.py, with the cost constants made parameters.

Usage:  python scripts/revision/decision_grounding_reanalysis.py
Output: data/revision_r1_r3_r4.json
"""
from __future__ import annotations

import itertools
import json
import random

import numpy as np
import torch
from scipy.spatial.distance import cdist
from scipy.stats import norm, spearmanr

from _env import ROOT
from server.adapters.cmapss_adapter import CMAPSSAdapter, INFORMATIVE_SENSORS
from server.atlas.simulation import ACTION_LEAD_TIME, COST_PARAMS, MaintenanceAction as A
from server.atlas.world_model import WorldModel, prepare_window

ACTIONS = A.all_actions()  # continue, soon, now, replace
SEQ, K, CAP, M_SAMPLES = 30, 10, 125.0, 1000
MODELS = ROOT / "data" / "models"
# checkpoint -> training seed. The paper checkpoint is seed 46: retraining with seed 46 reproduces
# its test predictions exactly (RMSE 15.4242, PHM 394.7), so its held-out split is seed 46's.
CHECKPOINTS = {"paper": (MODELS / "best_model_original.pt", 46),
               **{f"seed{s}": (MODELS / f"best_model_seed{s}.pt", s) for s in range(42, 47)}}


# ---------------------------------------------------------------- data + retrieval
def load_data():
    tr, te = CMAPSSAdapter(subset="FD001", split="train"), CMAPSSAdapter(subset="FD001", split="test")
    tr.connect(); te.connect()
    Xte, yte = [], []
    for mid in sorted(te.machine_ids):
        r = te.get_unit_history(mid)
        Xte.append(prepare_window([x.feature_vector for x in r[-SEQ:]], SEQ, len(INFORMATIVE_SENSORS)))
        yte.append(float(r[-1].rul_label or 0.0))
    Xtr, ytr, utr = [], [], []
    for mid in sorted(tr.machine_ids):
        r = tr.get_unit_history(mid)
        for i in range(len(r)):
            Xtr.append(prepare_window([x.feature_vector for x in r[max(0, i - SEQ + 1): i + 1]], SEQ, len(INFORMATIVE_SENSORS)))
            ytr.append(float(r[i].rul_label or 0.0))
            utr.append(f"train/{mid}")
    test_units = {f"test/{m}" for m in te.machine_ids}
    # R3: memory and queries come from disjoint engine populations (train_FD001 vs test_FD001).
    assert not test_units & set(utr)
    return (np.stack(Xte), np.array(yte, np.float32), np.stack(Xtr), np.array(ytr, np.float32),
            np.array(utr), sorted(tr.machine_ids))


def validation_mask(utr, train_ids, seed):
    """Windows of the 20% of training units train_rul.train() held out for this seed."""
    ids = list(train_ids)
    random.Random(seed).shuffle(ids)
    val = {f"train/{m}" for m in ids[int(len(ids) * 0.8):]}
    return np.array([u in val for u in utr])


def encode(ckpt, Xte, Xtr):
    m = WorldModel.load(str(ckpt)); m.eval()
    with torch.no_grad():
        o_te, o_tr = m(torch.tensor(Xte, dtype=torch.float32)), m(torch.tensor(Xtr, dtype=torch.float32))
    return (o_te.state_vector.numpy(), torch.clamp(o_te.rul_pred, min=0).flatten().numpy(),
            o_tr.state_vector.numpy(), torch.clamp(o_tr.rul_pred, min=0).flatten().numpy())


def neighbors(z_q, z_mem, y_mem):
    """k=10 cosine neighbors from the training memory (queries are never in it, see load_data)."""
    d = cdist(z_q, z_mem, metric="cosine")
    idx = np.argsort(d, axis=1)[:, :K]
    return np.take_along_axis(d, idx, axis=1), y_mem[idx]


# ---------------------------------------------------------------- cost model
def params(c_f=1000.0, tau_continue=30, c_life=0.0):
    tau = dict(ACTION_LEAD_TIME); tau[A.CONTINUE_OPERATION] = tau_continue
    return {"c_f": c_f, "c_b": COST_PARAMS["maintenance_base_cost"], "c_d": COST_PARAMS["downtime_cost_per_cycle"],
            "u": COST_PARAMS["urgency_multiplier"], "tau": tau, "c_life": c_life}


def cost(y, a, p):
    """Eq. (6), plus optional discarded-life charge c_life * (y - tau(a)) for executed maintenance.
    Vectorized over y. Default params reproduce server/atlas/simulation.compute_action_cost."""
    y = np.asarray(y, dtype=float)
    fail = y <= p["tau"][a]
    if a == A.CONTINUE_OPERATION:
        return np.where(fail, p["c_f"], 0.0)
    planned = p["c_b"] + p["c_d"] * p["u"][a] + p["c_life"] * np.maximum(y - p["tau"][a], 0.0)
    return np.where(fail, p["c_f"], planned)


def atlas_policy(preds, var, p, seed=42):
    """Monte Carlo decision graph: same RNG stream and tie-break as SimulationEngine + DecisionGraph."""
    rng, out = np.random.default_rng(seed), []
    for yh, v in zip(preds, var):
        s = np.clip(rng.normal(yh, max(np.sqrt(v), 1e-3), M_SAMPLES), 0.0, CAP)
        keys = []
        for a in ACTIONS:
            c = cost(s, a, p)
            keys.append((float(c.mean()), float(np.mean(s <= p["tau"][a])), float(c.std()), a))
        out.append(min(keys)[3])
    return out


def threshold_policy(preds, t_replace, t_now=None, t_soon=None):
    out = []
    for yh in preds:
        if yh < t_replace: out.append(A.REPLACE_IMMEDIATELY)
        elif t_now is not None and yh < t_now: out.append(A.SCHEDULE_MAINTENANCE_NOW)
        elif t_soon is not None and yh < t_soon: out.append(A.SCHEDULE_MAINTENANCE_SOON)
        else: out.append(A.CONTINUE_OPERATION)
    return out


def total(actions, y, p):
    return float(sum(float(cost(yy, a, p)) for yy, a in zip(y, actions)))


def tune_thresholds(pred_tr, y_tr, p):
    """Grid-search a monotone 3-threshold rule (replace < now < soon) on held-out validation windows."""
    by_a = {a: cost(y_tr, a, p) for a in ACTIONS}
    best = None
    for t_r, t_n, t_s in itertools.combinations_with_replacement(range(0, 105, 5), 3):
        act = np.where(pred_tr < t_r, 3, np.where(pred_tr < t_n, 2, np.where(pred_tr < t_s, 1, 0)))
        c = sum(by_a[ACTIONS[i]][act == i].sum() for i in range(4)) / len(y_tr)
        if best is None or c < best[0]:
            best = (c, t_r, t_n, t_s)
    return best[1:]


def breakdown(actions, y, p):
    rows = {}
    acts = np.array(actions)
    for a in ACTIONS:
        ya = y[acts == a]
        fail = ya <= p["tau"][a]
        disc = 0.0 if a == A.CONTINUE_OPERATION else float(np.maximum(ya[~fail] - p["tau"][a], 0).sum())
        rows[a] = {"n": int(len(ya)), "lead_time_failures": int(fail.sum()),
                   "true_rul_of_failures": [float(v) for v in ya[fail]],
                   "discarded_cycles": disc, "cost": float(cost(ya, a, p).sum())}
    rows["total"] = total(actions, y, p)
    return rows


def policies(pred_te, var, pred_val, y_val, p):
    tuned = tune_thresholds(pred_val, y_val, p)
    return {"fixed_rule": threshold_policy(pred_te, 30),
            "cascade": threshold_policy(pred_te, 30, None, 60),
            "tuned_threshold": threshold_policy(pred_te, *tuned),
            "atlas": atlas_policy(pred_te, var, p)}, [int(t) for t in tuned]


def paired_bootstrap(a_actions, b_actions, y, p, n=2000, seed=0):
    ca = np.array([float(cost(yy, a, p)) for yy, a in zip(y, a_actions)])
    cb = np.array([float(cost(yy, a, p)) for yy, a in zip(y, b_actions)])
    idx = np.random.default_rng(seed).integers(0, len(y), (n, len(y)))
    pct = 100 * (ca[idx].sum(1) - cb[idx].sum(1)) / ca[idx].sum(1)
    return [float(np.percentile(pct, 2.5)), float(np.percentile(pct, 97.5))]


# ---------------------------------------------------------------- confidence (R4)
def confidence(nd, ny, normalize):
    sim = np.mean(1.0 / (1.0 + nd), axis=1)  # explain.py: mean of per-neighbor 1/(1+d)
    var = np.var(ny, axis=1)
    return sim / (1.0 + (var / CAP ** 2 if normalize else var))


def boot_spearman(x, err, n=2000, seed=0):
    bs = [spearmanr(x[i], err[i]).correlation
          for i in np.random.default_rng(seed).integers(0, len(x), (n, len(x)))]
    return {"rho": float(spearmanr(x, err).correlation),
            "ci95": [float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5))]}


def coverage(pred, var, y):
    """Share of true RUL (on the clipped [0,125] scale the samples use) inside the central Gaussian interval."""
    sd, yc, out = np.maximum(np.sqrt(var), 1e-3), np.minimum(y, CAP), {}
    for lvl in (0.5, 0.8, 0.9, 0.95):
        z = norm.ppf(0.5 + lvl / 2)
        lo, hi = np.clip(pred - z * sd, 0, CAP), np.clip(pred + z * sd, 0, CAP)
        out[str(lvl)] = float(np.mean((yc >= lo) & (yc <= hi)))
    return out


def grounding_block(pred, nd, ny, y):
    err, var = np.abs(pred - y), np.var(ny, axis=1)
    c_raw, c_norm = confidence(nd, ny, False), confidence(nd, ny, True)
    return {"confidence_raw": boot_spearman(c_raw, err), "confidence_raw_mean": float(c_raw.mean()),
            "confidence_normalized": boot_spearman(c_norm, err), "confidence_normalized_mean": float(c_norm.mean()),
            "neg_neighbor_std_only": boot_spearman(-np.sqrt(var), err),
            "neighbor_similarity_only": boot_spearman(np.mean(1.0 / (1.0 + nd), axis=1), err),
            "neg_predicted_rul_proxy": boot_spearman(-pred, err),
            "mc_interval_coverage": coverage(pred, var, y),
            "frac_zero_variance_neighbors": float(np.mean(var == 0))}


# ---------------------------------------------------------------- main
def main():
    Xte, yte, Xtr, ytr, utr, train_ids = load_data()
    res = {"n_test_units": len(yte), "n_memory_windows": len(ytr), "k": K,
           "leakage_audit": {"memory_population": "train_FD001 windows only (100 engines)",
                             "query_population": "test_FD001 last windows (100 different engines)",
                             "query_unit_in_memory": False,
                             "health_index_on_evaluated_path": False,
                             "safety_override_implemented": False}}
    for name, (ckpt, seed) in CHECKPOINTS.items():
        if not ckpt.exists():
            res[name] = {"missing_checkpoint": ckpt.name}
            continue
        zte, pte, ztr, ptr = encode(ckpt, Xte, Xtr)
        nd, ny = neighbors(zte, ztr, ytr)
        var = np.var(ny, axis=1)
        val = validation_mask(utr, train_ids, seed)
        pval, yval = ptr[val], ytr[val]
        block = {"rmse_last_window": float(np.sqrt(np.mean((pte - yte) ** 2))),  # train_rul benchmark protocol
                 "n_tuning_windows": int(val.sum()),
                 "grounding": grounding_block(pte, nd, ny, yte)}

        dec = {}
        for label, p in {"paper_cost_model": params(), "with_discarded_life": params(c_life=50 / 125)}.items():
            pols, tuned = policies(pte, var, pval, yval, p)
            bd = {k: breakdown(v, yte, p) for k, v in pols.items()}
            dec[label] = {"tuned_thresholds_replace_now_soon": tuned, "breakdown": bd,
                          **{f"atlas_vs_{k}_pct": 100 * (bd[k]["total"] - bd["atlas"]["total"]) / bd[k]["total"]
                             for k in ("fixed_rule", "cascade", "tuned_threshold")},
                          # the tuned rule is the a-priori strongest baseline (chosen without test outcomes)
                          "atlas_vs_tuned_threshold_ci95": paired_bootstrap(pols["tuned_threshold"], pols["atlas"], yte, p)}
        block["decision"] = dec

        if name == "paper":  # cost sensitivity on the paper checkpoint
            sweep = []
            for c_f, tau_c, c_life in itertools.product((250, 500, 1000, 2000, 4000), (15, 20, 30), (0.0, 0.4)):
                p = params(c_f, tau_c, c_life)
                pols, _ = policies(pte, var, pval, yval, p)
                tot = {k: total(v, yte, p) for k, v in pols.items()}
                sweep.append({"c_f": c_f, "tau_continue": tau_c, "c_life": c_life, **tot,
                              **{f"atlas_vs_{k}_pct": 100 * (tot[k] - tot["atlas"]) / tot[k]
                                 for k in ("fixed_rule", "cascade", "tuned_threshold")}})
            block["sensitivity"] = sweep
        res[name] = block
        print(name, "done", flush=True)

    out = ROOT / "data" / "revision_r1_r3_r4.json"
    out.write_text(json.dumps(res, indent=2))
    print("wrote", out)


if __name__ == "__main__":
    main()

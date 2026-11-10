# ATLAS IEEE paper: response to simulated peer review, Round 1

Review: `ATLAS_review_round1.md` (2026-11-08, Major Revision). Revised sources: `paper.md`, `ATLAS_IEEE_Conference_Paper.docx` (rebuilt by `build_ieee.py`).
Re-analysis: `scripts/revision/decision_grounding_reanalysis.py` → `data/revision_r1_r3_r4.json`; seed checkpoints from `scripts/revision/train_seed_checkpoints.py`; figures from `scripts/revision/make_revision_figures.py`.

Author triage (2026-11-08): R1–R4 re-analyse; R6 drop the reproducibility claim; S1–S4, S6–S9 as text items; S5 not addressed.

The re-analysis reproduces the published numbers exactly before changing anything: fixed rule $3,440, ATLAS $1,817.50, r_s = −0.509, checkpoint RMSE 15.42. Retraining with seed 46 reproduces the ablation checkpoint's predictions exactly, which identifies its training seed (and so its held-out split, used to tune the threshold baseline).

## Must fix

| Ref | Status | What changed |
|---|---|---|
| R1 decision value | addressed; headline reversed | Table II is now a per-policy breakdown (actions, lead-time failures, discarded cycles, cost with and without a discarded-life charge). The reviewers' reconstruction holds: the fixed rule's $3,440 = 24 × $60 + 2 × $1,000, with failures on units of true RUL 28 and 29. Added a cascade and a three-threshold rule tuned on each checkpoint's 20 held-out validation engines. ATLAS costs **7.2% more** than the tuned rule on the ablation checkpoint (paired bootstrap 95% CI: 5.8% less to 24.3% more) and 3.8% *less* when discarded life is charged. Sweep over C_f × τ(continue) × C_ℓ (30 settings): ATLAS beats the tuned rule in 12, the fixed rule in 18, the cascade in 22. Five retrained checkpoints: ATLAS saves 25–73% vs the fixed rule on every seed but costs 7–216% more than the tuned rule on every seed; seeds 44 and 45 give ATLAS its own lead-time failures. The abstract now leads with the tuned-rule comparison and the paper no longer claims a cost advantage. New Fig. 4. |
| R2 cross-domain | addressed by reframing | Methods now specify data (synthetic, seeded, 1,250 × 30 × 5 per domain, 1,000 memory / 250 query), encoders, labels (stress composites, with formulas), k = 5 Euclidean retrieval. MMD, centroid cosine and the C-MAPSS-vs-compute EIR (old Table III, Fig. 5, the 10.82 distance) are **removed**: they compared vectors from independently trained encoders, which share no coordinates, and the C-MAPSS EIR row was a hard-coded constant in `ablation_engine.py`. Only the 3×3 compute matrix remains (query and memory share one encoder per cell; reproduced exactly). It is framed as confirming that memory must be partitioned by domain, not as a discovery. Contribution 4 is demoted to a bounded diagnostic. |
| R3 leakage | addressed; no leakage, two text errors corrected | The test-time memory holds only the 20,631 windows of the 100 training engines; queries are the 100 test engines (a different population), so unit-level exclusion is already guaranteed (asserted in the script). The C-MAPSS health index **is** label-derived (1 − min(RUL,125)/125), but it is not on the evaluated path. The "safety override (ŷ ≤ 10 or HI ≤ 0.20)" the paper described **does not exist in the code**; the text now says so. Eq. (9) also had the wrong sign on p_f: the code prefers the *lower* failure probability on cost ties. Corrected. |
| R4 confidence | addressed | Eq. (5) now matches the code (mean per-neighbor similarity). Kept the raw σ² and justified it as a ranking score: normalising by 125² gives the same r_s. r_s = −0.509 [−0.66, −0.33]; across five retrained checkpoints −0.45 ± 0.04. The score's ranking is identical to that of neighbor label spread alone, and −ŷ with no memory gives −0.45 [−0.61, −0.26]. MC interval coverage at nominal 50/80/90/95% is 63/85/87/91% (not calibrated). "Calibrated" is replaced by "dispersion-based" throughout; the new Table III holds these numbers. |
| R5 consistency | addressed (earlier pass + this one) | qquad, k = 5 vs 10, Table IV DNA row, 7.1–8.3× were fixed earlier. This pass names the ablation checkpoint in Figs. 2–3 and states k and memory contents explicitly. The 7.1–8.3× figure is gone with R2. |
| R6 availability | addressed (claim dropped) | "open, reproducible" removed; added a Code and Data Availability section: code, checkpoints and regeneration scripts available from the authors on request. (The earlier IP-filing caveat was dropped on 2026-11-08: no IP filing will be made.) |

## Should fix / consider

| Ref | Status | What changed |
|---|---|---|
| S1 literature | addressed | Added after web verification: Nguyen & Medjaher 2019 [10], de Pater et al. 2022 [11], Gal & Ghahramani 2016 (MC dropout) [14]. The deep-ensembles reference was **not** added (could not be verified this round). References renumbered in order of first citation. |
| S2 narrow claims | addressed | Title drops "Across Heterogeneous Machine Systems"; "runs unchanged" → shared architecture with per-domain encoder and memory; compute domains labelled synthetic in the abstract. |
| S3 defect catalogue | addressed | Removed from the numbered contributions; new Table V (defect, detected by, guard) built from `docs/qa/DEFECT_REPORTS.md`; register described as practice, not a controlled study. |
| S4 promotion drift | addressed in text | Section III-G acknowledges the drift and plans comparison against a fixed reference or the best checkpoint. Code unchanged. |
| S5 lead times | not addressed | Stated as an assumption in Limitations; no planning source cited. |
| S6 digital twin | addressed | Dropped from the Index Terms. |
| S7 uncited claims | addressed | Lewis et al. 2020 (RAG) [16]; Marseguerra & Zio 2000 [17]. |
| S8 compute data | addressed | Section IV Data paragraph (see R2). Corrects the earlier statement that laptop and mobile data came from the adapters: every reported compute-domain number is synthetic. |
| S9 author email | **open: needs the author** | K. R. Muppu's email still duplicates the first author's in `front_matter.docx`; the correct address is not in the repository. |

## Not changed, by design

- Table I and Table IV numbers (untouched by the review).
- The near-failure safety-parity paragraph (ablation 3), which reviewers cited as a strength.

## Length (6-page limit)

Cut from 8 to 6 pages in Word (US Letter, two columns) on 2026-11-08:
- The body now starts under the abstract instead of on a new page (`build_ieee.py` section break).
- The training-loss figure, the system-performance figure and the 3×3 heatmap were removed. The heatmap's nine values are now in the text, and Table IV keeps the latency numbers.
- Prose was trimmed throughout, and the abstract is cut to about 200 words. No result, number or caveat was dropped.

Figures are now Fig. 1 (architecture), Fig. 2 (predicted vs. true RUL), Fig. 3 (decision value).

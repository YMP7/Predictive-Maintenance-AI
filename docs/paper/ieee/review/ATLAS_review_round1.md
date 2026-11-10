# Simulated Peer Review — Round 1

- **Manuscript**: ATLAS: An Adaptive Machine Cognition Platform for Explainable Predictive Maintenance Across Heterogeneous Machine Systems
- **File reviewed**: `docs/paper/ieee/ATLAS_IEEE_Conference_Paper.docx` (saved 2026-10-13; newer than `paper.md`)
- **Review date**: 2026-11-08
- **Mode**: `full` (5 seats + editorial synthesis)
- **Target venue**: none confirmed — `criteria_binding_unavailable`. No venue-alignment claim is made; the panel judges against general IEEE PHM / industrial-informatics conference expectations.
- **Calibration status**: `NOT_CALIBRATED`

---

# Editorial Decision

## Review Panel Provenance

All five seats were written by one model (Claude Opus 5.5) in **one session context**, one after another, after one shared reading of the manuscript.

| Provenance axis | Status |
|---|---|
| Role-separated | true (distinct cards and rubrics) |
| Within-panel invocation-context separation | false (single context) |
| Blind to peer outputs | false (each later seat could see earlier seats) |
| Model-family distinct | false |
| Provider distinct | false |
| Human-reviewer distinct | false (no human reviewer) |

- **Binary independence claim**: not computed. Persona separation is not independence.
- **Correlated-error disclosure**: all seats share one model family and one context, so their errors are correlated. Agreement between seats is weak corroboration, not five independent votes. The typed `review-panel-provenance/1.0` artifact, the sprint-contract Phase 1/2 split and the conformance/synthesis checker scripts were **not** run for this review.

## Decision

### Major Revision

The paper is honest, well scoped and unusually candid about its limits. But two of its five headline contributions (decision value and the cross-domain study) rest on evidence whose construction is not described well enough for a reader to check it, and in places the construction may favour the result. These are repairable with analysis and text, mostly without new data.

## Blocking Issues (immutable source order)

| Ref | Blocking issue | Source | Evidence anchor | Resolves via |
|---|---|---|---|---|
| B1 | The 47% cost saving is measured against a binary threshold rule under a cost model that never charges discarded life, so most of the gap may come from two lead-time "failures" in the baseline | R1, R3, DA | `equation: Eq. (6) — C_f charged when y ≤ τ(continue)=30; no term for discarded life` | R1 |
| B2 | Cross-domain diagnostics compare latent states from separately trained encoders and targets with different meanings, and the comparison procedure (encoder, kernel, labels, data volumes) is not specified | R1, R2, R3, DA | `text: §IV "Compute-domain encoders are pretrained by self-supervised next-step prediction on simulation profiles calibrated to real telemetry."` | R2 |
| B3 | Possible evaluation leakage: neighbor exclusion is per record, not per unit, and it is unclear whether the C-MAPSS health index used by the safety override needs ground-truth life at test time | R1, DA | `text: §III-C "excluding the query's own record"` | R3 |

## Reviewer Summary

| Reviewer | Identity | Recommendation | Confidence |
|---|---|---|---|
| Journal-Fit Reviewer | Associate editor, IEEE PHM / industrial-informatics conference track | Major Revision | 4 |
| Reviewer 1 | ML evaluation methodologist, prognostics benchmarking and UQ | Major Revision | 4 |
| Reviewer 2 | RUL prediction and maintenance decision-making researcher | Major Revision | 4 |
| Reviewer 3 | Reliability engineer / industrial-IoT practitioner | Major Revision | 3 |
| Devil's Advocate | Fixed adversarial seat | N/A — findings only | N/A |

## Consensus Analysis

**[CONSENSUS-4]**
1. **The decision-value claim is under-supported.** The baseline is weak and the cost model is one-sided (EIC W2, R1 W1, R2 W3, R3 W1).
2. **The cross-domain study is under-specified, and its "domain-specific" conclusion is close to built in** (EIC W3, R1 W3, R2 W4, R3 W2).
3. **The candour is a real strength.** The no-SOTA statement, the multi-seed reporting, the reporting of a favourable earlier seed, and the "approximate safety parity, not a safety advantage" wording are all cited as strengths (EIC S2, R1 S1, R2 S1, R3 S1).

**[CONSENSUS-3]** (R1, R2, DA; EIC and R3 silent)
1. **"Calibrated confidence" is not calibrated.** Eq. (5) is a monotone neighbor-dispersion score with no reliability analysis, and its unit dependence on σ² (cycles²) is unaddressed (R1 W2, R2 W2, DA M2).

### Points of Disagreement

**Disagreement 1: Is the defect catalogue (§V-E) a research contribution?**
- **EIC view**: As written it is anecdotal: there is no collection protocol, taxonomy or comparison. It should be cut to a paragraph, or turned into a structured, method-backed contribution (EIC W4).
- **R3 view**: It is the most practically useful part of the paper for practitioners, and the "plausible result computed by the wrong method" signature is a valuable lesson (R3 S3).
- **Type**: Perspective difference.
- **Resolution**: Keep it, but present it as a structured lesson (a table with defect, detection method and guard) rather than a numbered contribution claim. Otherwise drop it from the contribution list.
- **Rationale**: Both views are evidence-based. Moving it out of the contribution list costs little and removes the EIC's objection without losing R3's practical value.

**Disagreement 2: Severity of the missing artifact / code-availability statement.**
- **R1**: Major, because "reproducible" is claimed (R1 W5).
- **EIC**: Minor, because many conference papers ship without code.
- **Resolution**: Major. The manuscript makes the reproducibility claim itself, so it carries the evidence burden.

## Decision Rationale

All four scoring reviewers independently recommend Major Revision, and no reviewer finds a fatal flaw. The prediction engine is modest but reported correctly (multi-seed, honest comparison with [2]). The latency and verification material is solid. The paper's distinctive claims, though, are decision value (47% cost reduction) and the four-domain representation study. For both, the reviewers converge on the same gap: a reader cannot rebuild how the number was produced, and what can be reconstructed suggests the setup favours the reported outcome.

For decision value, the reviewers show from Eq. (6) and the text that the baseline's $3,440 is consistent with 24 replacements at $60 plus exactly two $1,000 lead-time violations. If so, the headline saving depends on two units. The cost model also never charges the 281 discarded cycles that the paper itself flags. The paper's own threshold-cascade comparison (−10.46%) is the fairer figure.

For the cross-domain study, comparing latent spaces from separately trained encoders, and targets whose meanings the paper calls different, makes "domain-specific" close to tautological. The latent distance of 10.82 also cannot be a cosine distance (Eq. 4 bounds cosine distance to [0,2]).

Minor Revision is too lenient, because B1–B3 need re-analysis and possibly re-framed headline numbers. Reject is too strict: the system, honesty and engineering are publishable, and every blocking issue can be fixed with existing data plus clearer reporting.

The Devil's Advocate raised no CRITICAL issue, so nothing is held back for DA-CRITICAL adjudication.

## Required Revisions (Must Fix)

| Ref | Revision item | Severity | Evidence anchor | Source | Obligation | Cost scope |
|---|---|---|---|---|---|---|
| R1 | Rebuild the decision-value evaluation: cost breakdown, stronger baselines, discarded-life cost, sensitivity | major | `equation: Eq. (6)` / `table: Table II row 1` | EIC, R1, R2, R3, DA | must_fix | re-analysis, §V-B, Table II, abstract |
| R2 | Specify and justify the cross-domain comparison, or reframe it | major | `text: §IV encoder sentence` / `text: §V-C "0.28 within vs. 10.82 across"` | EIC, R1, R2, R3, DA | must_fix | re-analysis or section rewrite, §V-C, Figs 5–6 |
| R3 | Rule out leakage: unit-level neighbor exclusion; state how the C-MAPSS health index is computed at test time | major | `text: §III-C "excluding the query's own record"` | R1, DA | must_fix | re-analysis (if needed), §III-A/C |
| R4 | Report the confidence-error correlation with a CI and across seeds; drop "calibrated" or add a reliability analysis; fix the σ² units in Eq. (5) | major | `equation: Eq. (5) — σ² in cycles² dominates C` | R1, R2, DA | must_fix | re-analysis, §III-E, §V-B, abstract |
| R5 | Fix internal inconsistencies (k=5 vs k=10; stage sum 13.81 vs 14.8 ms; Fig. 3 run identity; "7–8×" vs 8.30×) and equation rendering (`qquad`) | minor | `table: Table IV row "pgvector retrieval (k=10, …)"` | R1, EIC | must_fix | sentence-level |
| R6 | Add a code/data availability statement, or drop "reproducible" | major | `text: §II "one open, reproducible architecture"` | R1 | must_fix | sentence/section |

### Required Item Details

**R1: Decision-value evaluation**
- **Problem**: The baseline is binary (continue/replace). Failure cost is charged at the lead-time violation, not at actual failure. Discarded life costs nothing. A reconstruction from Eq. (6) suggests the baseline total is 24×$60 + 2×$1,000.
- **Source**: R1 W1, R3 W1, DA M1, EIC W2, R2 W3.
- **Requirement**:
  - Publish a per-policy cost breakdown (counts × unit cost).
  - Add at least one baseline that also has a "schedule" option (e.g. a two-threshold rule tuned on the training split).
  - Add a discarded-life cost term, or report discarded cycles per policy.
  - Run a sensitivity sweep over C_f/C_b and τ.
  - Lead the abstract with whichever comparison survives.
- **Acceptance criteria**: A reader can recompute every Table II cost from a breakdown table, and the headline saving is stated against the strongest baseline, with a sensitivity range.

**R2: Cross-domain study**
- **Problem**: Each compute domain uses its own encoder. MMD and centroid cosine appear to compare latent coordinates that are not aligned. The targets differ in meaning (wear vs. stress). Kernel, bandwidth, sample sizes, label definitions and data volumes are not given. "10.82 across" exceeds the cosine range.
- **Source**: R1 W3, R2 W4, R3 W2, DA M3, EIC W3.
- **Requirement**:
  - State which encoder produces each latent set.
  - Give the MMD kernel and bandwidth, the n per domain, and what the "normalized" retrieval label is for compute domains.
  - Say which distance gives 0.28 / 10.82.
  - Either compute the diagnostics in a common space (one shared encoder, or a fixed feature space) or reframe the finding as "independently trained encoders do not share a coordinate system", which is expected rather than discovered.
- **Acceptance criteria**: The §V-C methods can be re-run from the text, and the conclusion follows from a comparison whose spaces are commensurable.

**R3: Leakage**
- **Problem**: Excluding only the query's own record still allows neighbors from adjacent windows of the same unit. The health index used by the safety override (≤0.20) and DNA "life-fraction health" may require total life.
- **Source**: R1 W4, DA M4.
- **Requirement**: State which units the memory holds at test time. Exclude the whole query unit. State how the C-MAPSS health index is computed from observable data only. Re-run Table II and r_s if anything changes.
- **Acceptance criteria**: An explicit sentence in §III-C/§IV stating that test-time retrieval and the health index use no test-unit ground truth.

**R4: Confidence score**
- **Problem**: Eq. (5) mixes a cosine distance in [0,2] with a label variance in cycles², so C ≈ 1/(1+σ²) and is near zero for most queries. "Calibrated" implies a probability match that is never tested. r_s = −0.509 has no CI and no seed spread.
- **Source**: R1 W2, R2 W2, DA M2.
- **Requirement**:
  - Normalize σ² (e.g. by 125²) or justify the raw form.
  - Report r_s with a bootstrap CI and across all 5 seeds.
  - Either add a reliability/coverage check (do the MC intervals cover true RUL at their nominal rate?) or replace "calibrated" with "grounded" or "dispersion-based".
- **Acceptance criteria**: The abstract wording matches the evidence, and r_s is reported as mean ± std with a CI.

**R5: Consistency and rendering**
- **Requirement**:
  - Reconcile k (§III-C says 5, Table IV says 10).
  - List the stage missing from Table IV, or correct "14.8 ms" (the rows sum to 13.81 ms).
  - Name the seed or run behind Figs. 2–3 (RMSE 15.42).
  - Write "7–8×" as "7.1–8.3×".
  - Remove the literal `qquad` from all 11 equations, and the broken bracket in Eq. (9).
- **Acceptance criteria**: No numeric contradiction between text, tables and captions, and equations render cleanly.

**R6: Availability**
- **Requirement**: Add an artifact statement: repository URL and commit, seeds, and how to regenerate Tables I–IV. Otherwise remove "open, reproducible". This interacts with your own IP/publication gate; that decision is yours.
- **Acceptance criteria**: A statement is present, or the claim is removed.

## Suggested Revisions (Should Fix / Consider)

| Ref | Item | Severity | Source | Obligation |
|---|---|---|---|---|
| S1 | Add decision-oriented PdM and probabilistic-RUL literature (see R2 report; verify each reference before citing) | major | R2 | should_fix |
| S2 | Narrow title and abstract: "runs unchanged" → the architecture is shared, the encoders are per-domain; "heterogeneous machine systems" → one benchmark plus simulated/self-collected compute telemetry | major | DA, R3, EIC | should_fix |
| S3 | Move the defect catalogue out of the numbered contributions into a structured lessons table | minor | EIC (resolved disagreement) | should_fix |
| S4 | Promotion gate: "within 3%" lets a slightly worse model replace the active one, so repeated promotions can drift. Compare against a fixed reference, or require non-inferiority to the best checkpoint | minor | R1 | should_fix |
| S5 | Justify lead times τ(a) and urgency multipliers, or tie them to a cited maintenance-planning source | minor | R3 | consider |
| S6 | Define "digital twin" as used here, or drop it from the Index Terms | minor | R2 | consider |
| S7 | Add citations for the uncited claims in §II "Memory and retrieval" and "Monte Carlo maintenance optimisation" | minor | R2 | should_fix |
| S8 | Report laptop/mobile/server data volumes, collection duration and how much is simulated vs. measured | major | R3 | should_fix |
| S9 | Fix the duplicated author email (K. R. Muppu) | minor | EIC | should_fix |

## Revision Roadmap — source-traceability checklist

Source order is not a work order. You decide `will_address` / `wont_address` / `not_on_point` for each item.

- [ ] R1 — must_fix: rebuild the decision-value evaluation (breakdown, stronger baseline, discarded-life cost, sensitivity)
- [ ] R2 — must_fix: specify the cross-domain comparison method, or reframe the finding
- [ ] R3 — must_fix: unit-level exclusion; health-index computation at test time
- [ ] R4 — must_fix: confidence score units, CI/seeds, drop or test "calibrated"
- [ ] R5 — must_fix: numeric consistency and equation rendering
- [ ] R6 — must_fix: artifact/code-availability statement, or drop "reproducible"
- [ ] S1 — should_fix: literature additions
- [ ] S2 — should_fix: narrow title/abstract claims
- [ ] S3 — should_fix: restructure the defect catalogue
- [ ] S4 — should_fix: promotion-gate drift
- [ ] S5 — consider: justify lead times / multipliers
- [ ] S6 — consider: define or drop "digital twin"
- [ ] S7 — should_fix: cite uncited §II claims
- [ ] S8 — should_fix: compute-domain data description
- [ ] S9 — should_fix: author email

## Journal-Supplied Deadline
NOT PROVIDED.

## Closing
We encourage you to consider the reviewers' comments carefully and submit a substantially revised manuscript. The revised manuscript would go through another round of review.

---

# Appendix: Reviewer Reports

---

## Report 1 — Journal-Fit Reviewer

**Identity**: Associate editor for an IEEE PHM / industrial-informatics conference track; has handled many C-MAPSS RUL papers.
**Focus**: Whether a "system plus honesty" contribution clears the novelty bar, whether five contributions fit a conference paper, and fit for PHM readers.

**Recommendation**: Major Revision | **Confidence**: 4

### Summary Assessment
The paper presents ATLAS, which combines an attention-LSTM RUL model, a labeled case memory for explanation and confidence, a Monte Carlo cost-based action ranker, and an adapter layer applied to turbofan, laptop, mobile and server telemetry. It reports FD001 accuracy over five seeds, a cost ablation, a cross-domain representation study, latency figures and a defect catalogue. The scoping is admirable: the paper says plainly that it does not claim SOTA, real-world validation or production readiness. That honesty is a real asset for PHM readers, who see many over-claimed C-MAPSS papers.

The difficulty is focus. Five contributions in about 3,600 words means none gets enough methods detail to be checked. The two contributions that would make the paper distinctive (decision value and cross-domain) are the least well specified. I recommend Major Revision: concentrate the paper on the integrated prediction-to-decision pipeline and make its evaluation airtight, then shrink or restructure the rest.

### Strengths
**S1: Clear problem statement linking prediction to action.** The introduction states the operator's two questions precisely and builds the architecture around them.
**Evidence Anchor**: `text: §I "what to do about the estimate, given its uncertainty and the cost of acting too early or too late"`

**S2: Honest scoping and reporting.** It reports an explicit non-claim, a favourable earlier seed, a PHM score worse than [2], and "approximate safety parity, not a safety advantage".
**Evidence Anchor**: `text: §V-A "An earlier single run (RMSE 15.02) was a favorable seed, which is why multi-seed statistics are reported."`

**S3: Human-in-the-loop safety gate.** The agent cannot actuate a machine; orders need role-checked approval. This is the right design posture for industrial readers.
**Evidence Anchor**: `text: §III-G "the agent has no function that actuates a machine"`

### Weaknesses
**W1: Too many contributions for the length.**
**Problem**: Five numbered contributions, each with thin methods.
**Evidence Anchor**: `text: §I "The contributions are:"` (five items, §I)
**Why it matters**: Reviewers cannot verify any one contribution fully, so the paper reads as a project summary.
**Suggestion**: Make contributions 1–3 the core. Present 4 as a bounded diagnostic and 5 as lessons, not contributions.
**Severity**: Major | **Confidence**: 4 — core expertise: conference editorial scope

**W2: The headline decision-value number needs a fairer frame.**
**Problem**: The abstract leads with 47.2%, against a fixed single-threshold rule. The fairer cascade comparison (−10.46%) is buried in Table II.
**Evidence Anchor**: `table: Table II — "Total simulated cost" −47.17% vs. "Cost on 30 disputed units vs. threshold cascade" −10.46%`
**Why it matters**: PHM readers will ask about the strongest baseline first.
**Suggestion**: Lead with the strongest baseline; see R1.
**Severity**: Major | **Confidence**: 4 — core expertise

**W3: The cross-domain contribution is not substantiated enough to be a contribution.**
**Problem**: Compute domains have no run-to-failure labels and are trained mainly on simulation, as the paper itself says.
**Evidence Anchor**: `text: §VI "memory holds no real run-to-failure cases, encoders are trained predominantly on simulation"`
**Why it matters**: The title's "heterogeneous machine systems" promises more than this evidence gives.
**Suggestion**: Narrow the title, or present the study as a negative diagnostic.
**Severity**: Major | **Confidence**: 4 — core expertise

**W4: The defect catalogue lacks method.**
**Problem**: There is no collection protocol, taxonomy, time frame or comparison base.
**Evidence Anchor**: `absence: §V-E — expected how defects were logged and classified; checked §I, §IV, §V-E, §VI`
**Why it matters**: As a numbered contribution it invites the "engineering notes" objection.
**Suggestion**: Use a structured table (defect, symptom, detection, guard), or remove it from the contribution list.
**Severity**: Minor | **Confidence**: 3 — adjacent: software engineering research norms

### Questions for Authors
1. If space forced you to keep only two contributions, which two, and why?
2. Which venue are you targeting? Its page limit decides how much of R1–R2 fits.

### Minor Issues
- All 11 numbered equations show a literal "qquad" before the equation number.
- K. R. Muppu's email duplicates the first author's.
- The title, authors and abstract are in text boxes; check that the venue's PDF/eXpress checker accepts this.

### Criterion-Bound Judgements (`NOT_CALIBRATED`)
| Dimension | Judgement | Anchor | Decision bearing? |
|---|---|---|---|
| Originality | PARTLY_MEETS | §II gap paragraph; [6] is close | yes |
| Methodological Rigor | NOT_ASSESSED (R1's seat) | — | — |
| Evidence Sufficiency | PARTLY_MEETS | Table II, §VI | yes |
| Argument Coherence | MEETS | §I → §VII | no |
| Writing Quality | MEETS | whole text | no |
| Literature Integration | PARTLY_MEETS | §II | no |
| Significance & Impact | PARTLY_MEETS | §I contributions | yes |

---

## Report 2 — Peer Reviewer 1 (Methodology)

**Identity**: ML evaluation methodologist; prognostics benchmarking and uncertainty quantification.
**Focus**: Whether each reported number has the statistical and procedural support its wording implies.

**Recommendation**: Major Revision | **Confidence**: 4

### Summary Assessment
The prediction experiments are reported with better hygiene than most C-MAPSS papers: five seeds with their own splits, last-window test evaluation, and an explicit note on CPU non-determinism. The downstream evaluations are much weaker. The cost ablation can't be recomputed and appears to hinge on two units. The confidence score mixes incompatible units and is called "calibrated" without any calibration test. Its correlation with error is reported without uncertainty. The cross-domain diagnostics leave out kernel, encoder, sample sizes and the distance used. Neighbor exclusion is per record, which leaves room for same-unit leakage. None of this looks fatal. Each item can be fixed with existing data, but until then the abstract's numbers 2–4 are not verifiable.

### Strengths
**S1: Multi-seed reporting with an honest note on variance.**
**Evidence Anchor**: `text: §IV "CPU training is not bit-reproducible; about ±0.3 RMSE should be expected on reruns."`

**S2: Correct test protocol (last window per unit), with the wrong protocol documented as a defect.**
**Evidence Anchor**: `text: §V-E "scoring all windows instead of the last per unit, which inflated a baseline RMSE to 48.8"`

### Weaknesses
**W1: The cost ablation can't be recomputed and may hinge on two units.**
**Problem**: With Eq. (6) constants (C_b=50, C_d=5, u=2 for replace → $60), "the fixed rule replaces 24" gives $1,440. The reported $3,440 then implies exactly two $1,000 charges, i.e. two units where the estimate was over 30 but the true RUL was ≤30. Under Eq. (6) these count as "failures" even though the paper also reports 0 missed imminent failures (RUL ≤5). The ATLAS total ($1,817.50) can't be reconstructed from "27 scheduled, 5 replaced" either. Discarded life is not costed.
**Evidence Anchor**: `equation: Eq. (6) — C_f charged whenever y ≤ τ(a); τ(continue)=30`
**Why it matters**: A 47% headline driven by two lead-time events, under illustrative costs, is fragile.
**Suggestion**: Breakdown table; sensitivity over C_f/C_b ∈ a grid and τ(continue) ∈ {15, 20, 30}; a discarded-life term; a two-threshold baseline tuned on training units.
**Severity**: Major | **Confidence**: 4 — core expertise; reconstruction assumes u(replace)=2 as stated

**W2: The confidence score is not calibrated, and its units are inconsistent.**
**Problem**: d̄ ∈ [0,2] while σ² is a variance of RUL labels in cycles² (up to about 125²/4). C ≈ 1/(1+σ²) except when neighbors agree almost exactly, so the first factor hardly matters. No reliability or coverage analysis supports "calibrated".
**Evidence Anchor**: `equation: Eq. (5) — product of 1/(1+d̄) and 1/(1+σ²) with σ² in cycles²`
**Why it matters**: The abstract claims "a calibrated confidence score".
**Suggestion**: Normalize σ². Report r_s with a bootstrap CI and across seeds. Add MC-interval coverage at nominal levels. Otherwise rename the score.
**Severity**: Major | **Confidence**: 4 — core expertise: UQ

**W3: The cross-domain diagnostics are under-specified.**
**Problem**: No MMD kernel or bandwidth, no sample sizes, no indication of which encoder produced each latent set, and no definition of the compute-domain retrieval target. "10.82 across" can't be the cosine distance of Eq. (4), which is bounded by 2.
**Evidence Anchor**: `text: §V-C "the latent distance gap (0.28 within vs. 10.82 across)"`
**Why it matters**: The results can't be reproduced or interpreted.
**Suggestion**: Add a methods paragraph covering all of the above.
**Severity**: Major | **Confidence**: 4 — core expertise

**W4: Possible same-unit leakage in retrieval.**
**Problem**: Exclusion is per record. If test units' windows are in memory with labels, neighbors from adjacent cycles of the same unit carry nearly the answer, which inflates r_s and lowers σ².
**Evidence Anchor**: `text: §III-C "excluding the query's own record"`
**Why it matters**: It would affect the grounding and decision results.
**Suggestion**: State the memory contents at test time and exclude the whole query unit.
**Severity**: Major | **Confidence**: 3 — depends on memory contents, which are not stated

**W5: Reproducibility is claimed without an artifact statement.**
**Evidence Anchor**: `absence: whole manuscript — expected code/data availability or repository link; checked §I, §II, §IV, §VII, references`
**Why it matters**: §II claims "one open, reproducible architecture".
**Suggestion**: Add a repository and commit, a seed list and regeneration commands.
**Severity**: Major | **Confidence**: 4

**W6: The promotion gate permits drift.**
**Problem**: Accepting a candidate "within 3%" of the active model lets quality ratchet downward over repeated promotions.
**Evidence Anchor**: `text: §III-G "only if its held-out RMSE is within the 3% tolerance of the active model"`
**Suggestion**: Compare against a fixed reference or the best-ever checkpoint.
**Severity**: Minor | **Confidence**: 4

### Questions for Authors
1. What is the per-action count and cost behind $3,440 and $1,817.50?
2. Which units' windows are in pgvector during test evaluation (17,737 vectors ≈ all FD001 training windows)?
3. Is r_s = −0.509 from one seed? What is its spread across the five?
4. How is the C-MAPSS health index computed at test time, given that life fraction needs total life?

### Minor Issues
- k = 5 (§III-C) vs. k = 10 (Table IV).
- Table IV stages sum to 13.81 ms, not 14.8 ms.
- Fig. 3 (RMSE 15.42) — name the seed.
- Abstract "7–8×" vs. 8.30× in Table III.

### Criterion-Bound Judgements (`NOT_CALIBRATED`)
| Dimension | Judgement | Anchor | Decision bearing? |
|---|---|---|---|
| Methodological Rigor | PARTLY_MEETS | W1–W4 | yes |
| Evidence Sufficiency | PARTLY_MEETS | Table II, Eq. (5) | yes |
| Argument Coherence | MEETS | — | no |
| Others | NOT_ASSESSED | — | — |

---

## Report 3 — Peer Reviewer 2 (Domain: PHM / RUL)

**Identity**: Researcher in RUL prediction and maintenance decision-making; C-MAPSS literature and condition-based maintenance optimisation.
**Focus**: Literature coverage, whether the components are novel against the PHM canon, and fair comparison.

**Recommendation**: Major Revision | **Confidence**: 4

### Summary Assessment
The paper puts itself correctly between point-accuracy RUL work and decision-aware PdM, and it correctly identifies Özcan [6] as the closest work. But the literature review leaves out the strand most relevant to its main claim: deep-learning RUL feeding cost-based maintenance decisions on C-MAPSS. It also leaves out probabilistic RUL, which is the standard answer to the uncertainty problem that ATLAS addresses with neighbor variance. Without these, the novelty of contributions 2–3 is hard to judge. "Machine DNA" and grounded confidence are close relatives of similarity-based prognostics [12], and the paper should say what is new. The FD001 comparison is handled fairly.

### Strengths
**S1: Fair, directional comparison with [2], with the PHM shortfall stated.**
**Evidence Anchor**: `text: §V-A "Our RMSE is lower than [2] but our PHM score is higher, meaning errors skew later"`

**S2: Correctly positioned against domain-adaptation work (similar vs. physically different machines).**
**Evidence Anchor**: `text: §II "These methods study adaptation among similar machines (turbofan to turbofan)."`

### Weaknesses
**W1: Decision-oriented PdM literature is missing.**
**Problem**: Work that couples deep RUL prognostics with cost-based maintenance decisions on C-MAPSS predates this paper and is directly comparable. Examples: Nguyen & Medjaher (2019), LSTM prognostics with a cost-based dynamic PdM framework; de Pater, Reijns & Mitici (2022), alarm-based maintenance scheduling with imperfect RUL prognostics.
**Evidence Anchor**: `absence: §II "Interpretable and decision-aware PdM" — expected cost-based PdM decision frameworks on C-MAPSS; checked §II, references [1]–[16]`
**Why it matters**: Contribution 3 (lead-time-aware decisions) needs a position against these.
**Suggestion**: Add and differentiate. Verify each citation before use (these are suggestions from memory).
**Severity**: Major | **Confidence**: 4 — core expertise

**W2: Probabilistic RUL / UQ literature is missing.**
**Problem**: MC dropout, deep ensembles, and Bayesian or Gaussian-process RUL are the standard uncertainty baselines. They are mentioned only as future work.
**Evidence Anchor**: `text: §VII "Future work: MC-dropout and ensemble uncertainty"`
**Why it matters**: Neighbor variance should be compared with, or at least positioned against, these.
**Suggestion**: Add one paragraph to §II, and ideally an MC-dropout comparison of r_s.
**Severity**: Major | **Confidence**: 4

**W3: The decision baseline is not one the PdM literature would use.**
**Problem**: A single fixed threshold with binary actions is the weakest standard policy.
**Evidence Anchor**: `text: §V-B "Against a fixed rule (replace below a 30-cycle estimate)"`
**Suggestion**: Add a cost-optimal threshold policy tuned on training units.
**Severity**: Major | **Confidence**: 4

**W4: The cross-domain framing departs from PHM's sense of "domain".**
**Problem**: In PHM transfer learning, a "domain" means an operating condition or fault mode of comparable assets. Computers under load are not degrading assets in that sense, as the paper admits.
**Evidence Anchor**: `text: §III-A "for compute domains (Category B) it is instantaneous operational stress, not wear."`
**Suggestion**: Call it "cross-category" and frame the result as expected, not discovered.
**Severity**: Major | **Confidence**: 4

**W5: Uncited claims in §II.**
**Evidence Anchor**: `text: §II "Retrieval- and memory-augmented designs motivate keeping experience in an external store"` (no citation; the same applies to the Monte Carlo paragraph)
**Severity**: Minor | **Confidence**: 4

### Suggested references (verify before citing)
```yaml suggested-references
- title: "A new dynamic predictive maintenance framework using deep learning for failure prognostics"
  authors: "K. T. P. Nguyen, K. Medjaher"
  year: 2019
  venue: "Reliability Engineering & System Safety"
- title: "Alarm-based predictive maintenance scheduling for aircraft engines with imperfect Remaining Useful Life prognostics"
  authors: "I. de Pater, A. Reijns, M. Mitici"
  year: 2022
  venue: "Reliability Engineering & System Safety"
```

### Questions for Authors
1. How does Machine DNA differ from health-indicator trajectory features in similarity-based prognostics [12]?
2. Why FD001 only? FD002/FD004 would test the adapter's normalization under multiple operating conditions at little extra cost.

### Minor Issues
- "Digital twin" appears in the Index Terms and Fig. 1 context but is never defined.
- Mixed British/American spelling ("optimise" / "normalize").

### Criterion-Bound Judgements (`NOT_CALIBRATED`)
| Dimension | Judgement | Anchor | Decision bearing? |
|---|---|---|---|
| Originality | PARTLY_MEETS | W1, W2 | yes |
| Literature Integration | PARTLY_MEETS | §II | yes |
| Significance & Impact | MEETS | §I | no |
| Others | NOT_ASSESSED | — | — |

---

## Report 4 — Peer Reviewer 3 (Industrial deployment / reliability)

**Identity**: Reliability engineer and industrial-IoT practitioner who has deployed condition monitoring in plants.
**Focus**: Whether the maintenance model, the safety gate and the multi-machine claims match practice.

**Recommendation**: Major Revision | **Confidence**: 3

### Summary Assessment
I would trust this system's posture more than most research prototypes. It defers to humans, labels simulated data as simulated, and reports a near-failure unit that was scheduled with only a 4-cycle margin. The maintenance economics, though, are not how plants decide. Replacing early costs real remaining life and parts. Lead times depend on spares and crew, not on a fixed per-action constant. A threshold rule with a "schedule" option is what most plants already run. The compute domains are useful as an adapter demonstration, but they say little about machines that wear. Clearer labelling of what each domain proves would make the paper more credible to practitioners.

### Strengths
**S1: Safety findings reported against the paper's own interest.**
**Evidence Anchor**: `text: §V-B "one unit (true RUL 14) was scheduled with only a 4-cycle margin"`

**S2: Data provenance labelling (simulated / replayed / estimated / measured) as a practice.**
**Evidence Anchor**: `text: §V-E "labeling data as simulated, replayed, estimated or measured"`

**S3: The defect lessons are valuable to practitioners.** The "plausible result computed by the wrong method" signature is exactly what goes wrong in plant analytics.
**Evidence Anchor**: `text: §V-E "nearly all are a plausible result computed by the wrong method"`

### Weaknesses
**W1: The cost model leaves out the main cost of early action.**
**Problem**: Discarded remaining life (281 cycles on three units) is noted but not priced. Per-action lead times are fixed constants.
**Evidence Anchor**: `text: §III-F "(illustrative, not fitted to financial data)"`
**Why it matters**: The policy is biased toward acting, which flatters ATLAS against a binary rule.
**Suggestion**: Price discarded life per cycle; run a sensitivity analysis; justify τ(a) with a maintenance-planning source.
**Severity**: Major | **Confidence**: 4 — core expertise: maintenance economics

**W2: Compute domains don't test PdM.**
**Problem**: There is no run-to-failure in compute domains, so the cross-domain study tests representation similarity, not maintenance prediction.
**Evidence Anchor**: `text: §VI "claims for these domains concern the architecture, not field accuracy"`
**Suggestion**: Say so in the abstract. A vibration or MetroPT domain would make the cross-machine claim real.
**Severity**: Major | **Confidence**: 3

**W3: Compute-domain data are not described.**
**Evidence Anchor**: `absence: §IV Data — expected duration, sampling rate, device count and simulated/measured split for laptop, mobile, server; checked §III-A, §IV, §VI`
**Severity**: Major | **Confidence**: 4

### Questions for Authors
1. What happens to cost savings if each discarded cycle costs C_b/125?
2. How would τ(a) be set for a real asset? From spares lead time? From crew scheduling?

### Criterion-Bound Judgements (`NOT_CALIBRATED`)
| Dimension | Judgement | Anchor | Decision bearing? |
|---|---|---|---|
| Significance & Impact | PARTLY_MEETS | W1, W2 | yes |
| Evidence Sufficiency | PARTLY_MEETS | W3 | yes |
| Others | NOT_ASSESSED | — | — |

---

## Report 5 — Devil's Advocate

### Strongest Counter-Argument
ATLAS's distinctive results are largely produced by how the evaluation was built, not found by it.

- **Decision value**: the comparison is against the weakest policy, and the cost function charges only lead-time violations (never discarded life). A policy with more "act early" options is bound to win, and the arithmetic suggests the 47% hinges on two units.
- **Grounded confidence**: the score is effectively 1/(1+label variance) of neighbors. Neighbor label variance tracks how ambiguous the region is, so a negative correlation with error is expected of any kNN-variance proxy, and possible same-unit leakage could strengthen it further. Nothing shows that grounding beats a simple ensemble.
- **Cross-domain**: the encoders are trained separately and the targets mean different things. Finding the latent spaces "roughly orthogonal" and retrieval across them poor is guaranteed, not learned.

What remains is a competent but modest attention-LSTM, a sound engineering system, and good verification hygiene. That is a worthwhile systems paper, but not the "platform across heterogeneous machines" the title promises.

### Issue List
**M1 (MAJOR, evidence sufficiency):** The 47% saving is a baseline/cost-model artifact risk. Anchor: `equation: Eq. (6)` + `table: Table II row 1`; reconstruction 24×$60 + 2×$1,000 = $3,440.
**M2 (MAJOR, argument):** "Calibrated" is unsupported, and r_s may be an expected property of any variance proxy. Anchor: `equation: Eq. (5)`.
**M3 (MAJOR, logic):** The cross-domain conclusion is near-tautological given separate encoders and different target semantics. Anchor: `text: §IV "Compute-domain encoders are pretrained by self-supervised next-step prediction"`.
**M4 (MAJOR, validity):** Possible leakage via per-record exclusion and the health-index definition. Anchor: `text: §III-C "excluding the query's own record"`.
**M5 (MAJOR, overgeneralization):** "Runs unchanged on different machines" while the encoders are per-domain. Anchor: `text: Abstract "runs unchanged on different machines through a thin adapter layer"`.
**m1 (MINOR):** The "100% citation availability" row is true by construction (the baseline has no memory) and adds no evidence. Anchor: `table: Table II row "Citation availability"`.

No CRITICAL issues: each of M1–M5 can be fixed with existing data or rewording, and none invalidates the RUL or system results.

### Ignored Alternative Explanations
- The r_s ≈ −0.5 may come from clipped labels: early-life neighbors all carry label 125, so variance is 0 and confidence is high, while error profiles vary by life stage. This is unrelated to grounding.
- The laptop EIR < 1 is explained in the paper, but the same regression-to-mean argument could also lower mobile/server within-domain RMSE if those labels have low variance.

### Missing Stakeholder Perspectives
- Maintenance planners and spares managers set real lead times and costs; none was consulted.
- The approvers in the human-approval gate: no evaluation of approval burden or alert fatigue.

### Observations (Non-Defects)
- The "Limitations" section pre-empts many of these points. The problem is that the abstract and title don't carry those limits forward.

---

# Attachments

## Attachment: Suggested-Reference Check (advisory, #1001)
Suggested-reference check (script output, not a reviewer finding; #1001)
Seats read: R2, R3 (partial).
Not read:
- R3: the report has no suggested-references block.

| Seat | # | Reference | Result |
|---|---|---|---|
| R2 | 1 | K. T. P. Nguyen, K. Medjaher (2019) "A new dynamic predictive maintenance framework using deep learning for failure prognostics" | Not checked: an index that could settle it did not answer |
| R2 | 2 | I. de Pater, A. Reijns, M. Mitici (2022) "Alarm-based predictive maintenance scheduling for aircraft engines with imperfect Remaining Useful Life prognostics" | Not checked: an index that could settle it did not answer |

"Found" means an index holds a record with this DOI or arXiv ID and title, or with this title. It does not show that the work supports the recommendation, or that the authors and year are right.


## Attachment: Reviewer Claim Check (advisory, #1002)
The reviewer claim check did not run (it needs a separate judge subagent, which this inline run did not dispatch).

## Attachment: Acronym Check (advisory, #849)
### Acronym check (advisory; no reply needed)
Coverage: body (partial)
Not in this input: English abstract, Chinese abstract.
Not checked:
- Body, line 5: PdM (the initials before its parentheses do not spell it)
- Body, line 228: FD001 (the initials before its parentheses do not spell it)

| Scope | Line | Rule | Acronym | Uses |
|---|---|---|---|---|
| Body | 1 | Not defined | ATLAS | 8 |
| Body | 5 | Not defined | CPU | 5 |
| Body | 5 | Not defined | MAPSS | 14 |
| Body | 5 | Not defined | NASA | 2 |
| Body | 5 | Not defined | PHM | 7 |
| Body | 5 | Not defined | RMSE | 12 |
| Body | 6 | Not defined | AI | 2 |
| Body | 6 | Not defined | IoT | 1 |
| Body | 18 | Not defined | SDK | 1 |
| Body | 24 | Not defined | FD003 | 1 |
| Body | 24 | Not defined | LSTM | 7 |
| Body | 26 | Not defined | SHAP | 1 |
| Body | 32 | Not defined | LAMA | 1 |
| Body | 32 | Not defined | MMD | 3 |
| Body | 46 | Not defined | SSH | 2 |
| Body | 46 | Not defined | TCP | 1 |
| Body | 86 | Not defined | LLM | 1 |
| Body | 136 | Not defined | GB | 1 |
| Body | 136 | Not defined | RAM | 1 |
| Body | 187 | Not defined | EIR | 1 |
| Body | 216 | Not defined | MB | 1 |
| Body | 224 | Not defined | API | 1 |
| Body | 224 | Not defined | ReLU | 1 |
| Body | 232 | Not defined | FD002 | 1 |
| Body | 232 | Not defined | FD004 | 1 |
| Body | 232 | Not defined | MC | 1 |
| Body | 232 | Not defined | OPC | 1 |
| Body | 232 | Not defined | UA | 1 |
| Body | 232 | Not defined | VM | 1 |


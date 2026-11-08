# ATLAS Master Checklist: v1–v5 Design and Project Status

As of Oct 15, 2026 · Source: ATLAS\_PROJECT\_CONTEXT.md plus the docs/ folder. Re-verified against code, docs and a full test run (290 passed). Italic notes say what was checked or what is still open. Nothing is committed.

Legend: **BUILD** = in scope and committed · **FUTURE** = named future work, never claimed as built.

## 1. Identity and framing rules

- [x] One-line identity kept: modular machine cognition platform (observe, understand, remember, predict, simulate, reason, decide, explain, improve)
- [x] Title: *An Adaptive Machine Cognition Platform for Explainable Predictive Maintenance Across Heterogeneous Machine Systems*
- [x] Domain: Explainable AI for Predictive Maintenance and Decision Intelligence
- [x] BUILD / FUTURE-WORK label is kept on every feature
- [x] Adapter layer is the ONLY place domain-specific code lives (no `if domain == ...` below it) *(domain branches now behind `server/adapters/domain_profile.py`; grep finds none outside adapters)*
- [x] State vector dimension fixed at 32 for WorldModel output and AMKB (Machine DNA is a separate 16-dim fingerprint)
- [x] Re-audit code for any `if domain ==` leaks outside `server/adapters/` *(fixed in api.py, explain.py, pretrain_domain.py, transfer_study.py, domain_service.py, learning_engine.py, backend_api.py)*

## 2. Version history (what each version introduced)

- [x] **v1**: 10-chapter vision, 8 subsystems, 8 patent claims, 3 papers. Rejected as over-scoped for a solo project
- [x] **v2**: Rescoped to one domain (NASA C-MAPSS). Introduced the BUILD / FUTURE-WORK split
- [x] **v3**: Renames adopted (AMKB, Machine DNA redefined, Confidence Engine folded into Decision Graph). Human Feedback Engine demoted. Patents cut 8→4. Papers cut 3→1
- [x] **v4**: Added Laptop and Mobile (Termux:API) adapters. Formalised "Domain Generalization by Construction"
- [x] **v5 (frozen)**: Added Cloud VM / `ServerAdapter`. Added the Cross-Domain Machine DNA Transfer Study and the open-source Cross-Domain Benchmark
- [x] **Sequencing change**: C-MAPSS + AI core first (Months 1–5), adapters second (Months 6–7)

## 3. Deliberately cut: confirm none crept back in

- [x] Human Feedback Engine (accept / reject / modify loop): not built
- [x] Full 8-class Universal Machine Adapter (CNC, EV, robot, etc.): not built
- [x] Closed-loop / online reinforcement learning: not built
- [x] Multi-machine fleet coordination: not built
- [x] 3 separate papers: 1 paper, 3 sections
- [x] 8-item patent list: trimmed to 4 candidates
- [x] iOS mobile support: excluded
- [x] "Digital Twin" as a standalone module: never claimed as one
- [x] "Continuous / real-time learning": Learning Engine is batch / periodic only
- [x] Wording sweep: the Month 7 heading says "Continuous Learning" and the repo is branded "Digital Twin". Align the wording with the rules above *(Month 7 headings now say Batch Retraining; repo/Digital Twin branding left as is)*

## 4. Architecture subsystems

- [x] Machine Adapter Layer: `base_adapter.py` (NormalizedReading + ABC)
- [x] World Model: Attention-LSTM (hidden 64 → TemporalAttention → 32-dim state)
- [x] AMKB: pgvector, `vector(32)`, cosine retrieval, domain isolation
- [x] Machine DNA: built and tested
- [x] Resolve the DNA dimension: rule says dim = 32, Month 2 Week 2 describes a 16-dim structure (health 0–2, thermal 3–5, power 6–7, failure 8–15) *(code and migration use 16-dim DNA; context rule corrected)*
- [x] Adaptive Context Engine: multi-domain model registry
- [x] Prediction Engine (RUL): RMSE + PHM scoring
- [x] Simulation Engine: Monte Carlo with `ACTION_LEAD_TIME`
- [x] Decision Graph: cost-weighted, deterministic tie-breaking, confidence reused from `ExplanationReport`
- [x] Explainability Engine: AMKB citations + occlusion feature attribution
- [x] Learning Engine: batch retraining, 3% promotion gate, DB audit log
- [x] Dashboard with per-domain view
- [x] Dashboard: cross-domain comparison view (listed in v5 architecture; confirm it exists in the UI) *(TransferStudyView.tsx exists)*

## 5. Domain adapters and validation tiers

- [x] C-MAPSS FD001 (benchmark, built first)
- [x] Laptop (live, psutil, stress score)
- [x] Mobile (Termux:API + simulation fallback)
- [x] Server (Paramiko SSH + simulation fallback)
- [ ] Server: connect a real cloud VM (GitHub Student Pack / GCP / Azure). Until then it is simulated and must be described that way *(needs your VM)*
- [ ] Mobile: confirm a real device run (not only simulation fallback) is recorded *(needs your device)*
- [ ] Bonus tier (college HPC / industrial partner): opportunistic, FUTURE
- [x] Limitation stated: no kHz-range vibration / acoustic domain (FUTURE)
- [x] Category A (physical wear) vs Category B (operational stress) taxonomy documented

## 6. Month-by-month build status

### Month 1: C-MAPSS and World Model

- [x] W1: FD001 EDA (7 constant / 14 informative sensors)
- [x] W2: RUL clip at 125, normalisation, 30-cycle windows (`ml/preprocessing.py`)
- [x] W3: WorldModel forward pass verified; terminal-ReLU bug fixed
- [x] W4: Training loop with 80/20 split (RMSE 15.02, PHM 383.19)
- [ ] Multi-seed mean ± std evaluation across all reported numbers (planned, flagged as non-deterministic) *(5-seed data exists in atlas_evaluation_summary.json; extend to other numbers)*

### Month 2: AMKB and Machine DNA

- [x] W1: AMKB core module (17 tests)
- [x] W2: Machine DNA engine
- [x] W3: Full population pass plus near-failure retrieval check
- [x] W4: Adaptive Context Engine + API endpoints
- [x] Tidy the context file: the Month 2 Week 1 box is still unticked though Week 3 closed it out *(Month 2 W1 closed in W3; no open box found)*

### Month 3: Prediction Engine

- [x] 5-seed evaluation of LSTM + linear head (PHM 426 ± 84, rejected)
- [x] Attention-LSTM locked in (RMSE 15.22 ± 0.31, PHM 375.00 ± 21.93)

### Month 4: Explainability

- [x] Confidence calibration and AMKB citations
- [x] Occlusion-based feature attribution
- [x] `/api/explain` integration
- [x] Grounding / citation sanity tests

### Month 5: Simulation and Decision Graph

- [x] Lead-time model and tie-breaker bug fixes
- [x] Monte Carlo SimulationEngine
- [x] `/api/decide` and `/api/simulate`
- [x] Cost model evaluation, safe tie-breaking

### Month 6: Heterogeneous adapters

- [x] Laptop, Mobile and Server adapters
- [x] Domain service streaming
- [x] Hardcoded `(30, 14)` assumptions removed (4 audited locations)

### Month 7: Learning, transfer, ablations

- [x] LearningEngine and 3% epsilon gate
- [x] Domain pre-training (seeds 101 / 102 / 103) with non-collapse guards
- [x] Transfer study (MMD, cosine, NTI, retrieval inflation)
- [x] Four ablations run (`ABLATION_STUDY_RESULTS.md`)
- [x] System audit, encoder routing fix, DB audit annotation

### Month 8 (current): Benchmark and synthesis

- [x] End-to-end system benchmark (`docs/ATLAS_BENCHMARK.md`) *(docs/ATLAS_BENCHMARK.md and data/system_benchmark_results.json exist; report and results JSON present; review the numbers yourself)*
- [ ] Thesis synthesis *(docs/ATLAS_THESIS_CHAPTER.md exists as a draft)*
- [ ] Update Section 6 of the context file after each deliverable

## 7. Research, IP and publication

- [x] 36-paper literature map (`LITERATURE_MAPPING.md`)
- [ ] Paper section A: Attention-LSTM benchmark vs published FD001 baselines (draft) *(docs/paper/ATLAS_research_paper_v0.2.md exists as a draft)*
- [ ] Paper section B: Decision Graph and explainability (draft)
- [ ] Paper section C: Cross-domain transfer study (draft)
- [x] Ablation 1: full pipeline vs RUL-alone (+47.17% cost reduction)
- [x] Ablation 2: grounded vs ungrounded explainability (r\_s = -0.509)
- [x] Ablation 3: Decision Graph vs naive thresholds
- [x] Ablation 4: domain-adapted vs foreign transfer (3×3 matrix)
- [x] Original plan listed Ablation 4 as *single-domain vs cross-domain-informed World Model*. The delivered version differs, so document the change or add the original *(delivered 3x3 domain-adapted vs foreign matrix is documented; original single-vs-cross-domain variant not run)*
- [ ] Patent candidate 1: simulation-coupled Decision Graph (post-implementation evaluation) *(NOT DONE, needs your counsel/prior-art search; patent must precede paper)*
- [ ] Patent candidate 2: Machine DNA (prior-art search pending)
- [ ] Patent candidate 3: AMKB-grounded explainability
- [ ] Patent candidate 4: adapter-based cross-domain pipeline
- [ ] Open-source release of the ATLAS Cross-Domain Benchmark (data and eval scripts) *(not done)*
- [ ] Multi-seed variance for the headline numbers

## 8. Honesty and consistency issues to fix before submission

- [x] Transfer study: Executive Summary says MMD 0.74–0.88 for compute domains, but the table shows 0.90–0.93 *(summary now 0.90-0.93)*
- [x] Transfer study: summary says cosine −0.09 to 0.18, but the table spans −0.2169 to 0.1543 *(summary now -0.22 to 0.15)*
- [x] Ablation 3: "safety parity" claim sits beside 90% vs 100% near-failure urgent rate. Re-word or explain *(reworded as a disclosed 10-point gap)*
- [x] Ablation 1: early-life Gaussian-tail over-replacement (281 cycles) is disclosed. Carry it into the paper's limitations *(added to paper section 7 limitations)*
- [x] Ablation 2: mean grounded confidence is only 0.035. Check calibration framing *(framed in paper section 7 as a rank signal, not calibrated probability)*
- [x] Decision Graph stochastic sensitivity: add a tie-margin / defer-to-human policy or state it as FUTURE *(stated as FUTURE WORK in paper sections 7 and 8; not built)*
- [x] Benchmark numbers differ across docs (15.02 / 383 vs 15.21 / 375 vs 15.42). Name the protocol for each *(protocol table added to docs/REPRODUCIBILITY.md)*
- [x] Repo-structure table lists `simulation_engine.py`, `decision_graph.py`, `explainability.py`, but the real files are `simulation.py`, `decision.py`, `explain.py` *(context file now lists simulation.py, decision.py, explain.py)*
- [x] Literature-mapping links point to a local `c:/Users/...` path. Convert to relative links *(converted to relative links)*

## 9. Platform health check (run and tick)

### Infrastructure

- [x] `docker compose up -d --build`: app, TimescaleDB, Mosquitto all healthy *(app, TimescaleDB, Mosquitto all healthy; fixed missing PYTHONPATH and ml/ copy in Dockerfile)*
- [x] `GET /health` returns healthy *(returns healthy on :8000)*
- [x] `python scripts/migrate.py` and `scripts/migrate_atlas.py` run cleanly (pgvector enabled) *(both ran, pgvector present; only psycopg pool shutdown warnings)*
- [x] `.env` has `JWT_SECRET_KEY`, `DATABASE_URL`, `TSDB_PASSWORD` *(JWT_SECRET_KEY, DATABASE_URL, TSDB_PASSWORD present)*
- [x] Persistent volumes mounted (data, logs, DB) *(data and logs named volumes mounted on the app container)*

### Tests

- [x] Legacy suite: `pytest test_suite.py test_integration.py test_ai_pipeline.py test_performance.py test_api.py` (documented 29 passing) *(full tests/ run: 290 passed)*
- [x] `tests/test_amkb.py` (17 tests, needs live pgvector) *(in the 290-pass run, live pgvector)*
- [x] `tests/test_api.py`, `tests/test_mqtt.py`, `tests/test_work_order_safeguards.py` *(in the 290-pass run)*
- [x] Adapter contract tests (laptop, mobile, server) *(test_adapter_conformance, laptop, mobile, server tests pass)*
- [x] Transfer study reruns reproduce `transfer_study_results.json` *(test_transfer_study passes; `data/transfer_study_results.json` present)*
- [x] Ablation script reruns reproduce the stated numbers (seed 42) *(reran against full 17,731-row AMKB: ablation and transfer JSON identical to committed results)*
- [x] CI workflow exists and passes (README badge points to one; an older doc says none exists) *(`.github/workflows/ci.yml` present; passing on GitHub not checked)*

### ML pipeline

- [x] Checkpoints present in `data/models/` (cmapss, laptop, mobile, server) *(all four domains present in data/models)*
- [x] AMKB populated (17,731 C-MAPSS rows intact under multi-domain writes) *(17,731 cmapss rows restored via populate_amkb.py --clear; full tests re-run)*
- [ ] Learning Engine promote / rollback test and `learning_events` audit rows *(1 learning_events row exists; promote/rollback covered by test_learning_engine)*
- [x] Frontend shows citations, attribution and decision output *(ExplainabilityView and DecisionSupportView exist; not visually checked)*

### Security

- [x] CORS is not `*` in deployment (`docker-compose.yml` defaults to `*`, SECURITY.md says no wildcard) *(defaults to localhost:3000, no wildcard)*
- [x] `MOBILE_BRIDGE_TOKEN` and `JWT_SECRET_KEY` set in deployment *(both set in .env; app restarted healthy)*
- [x] JWT in HttpOnly cookies; `X-API-Request` header enforced *(httponly cookie in backend_api.py, X-API-Request enforced in auth.py)*
- [x] RBAC on control endpoints (admin role) *(require_admin on retrain)*
- [x] MQTT: anonymous off, per-device ACL *(allow_anonymous false + acl_file)*
- [ ] HTTPS via Nginx + Let's Encrypt (not deployed) *(needs a domain and host)*
- [ ] Twilio live-delivery test (sandbox only so far) *(needs your credentials)*
- [x] Work-order grounding, 3/day cap and provenance checks pass *(test_work_order_safeguards passes)*
- [ ] UI flow to resolve work orders (not built) *(not built)*

## 10. Documentation hygiene

- [ ] Three document sets conflict: older docs describe SQLite + port 8000 and 29 tests; newer ones describe TimescaleDB, MQTT and ATLAS. Pick one source of truth per topic
- [x] `USER_GUIDE.md` and `ADMIN_GUIDE.md` say the dashboard is on port 3000; the integrated server uses 8000 *(now port 8000)*
- [ ] Retire or mark the legacy digital-twin docs (SRS, SAD, ML guide) as separate from ATLAS
- [ ] Keep `ATLAS_PROJECT_CONTEXT.md` Section 6 current

## 11. Industrial redesign (`feature/industrial-frontend`, plan in `docs/redesign/00_PLAN.md`)

- [x] P0: discovery, gap analysis, ADR log; `main` merged into the branch *(pytest 317/317 after merge)*
- [x] P1: ISA-101 design system, AppShell, router, kiosk, `/dev/components` *(axe 0 violations light and dark; initial JS 94.5 KB gz)*
- [x] P2: audit trail, ingestion, live stream, cognition trace, viewer RBAC *(pytest 378 passed; migration re-runnable)*
- [ ] Switch the API to `atlas_app`: set `ATLAS_APP_DB_PASSWORD`, re-run `scripts/migrate_platform.py`, set `API_DATABASE_URL` *(needs your password choice)*
- [x] P3: 3D Asset View (teardown), 5 machines, films *(60 fps on Intel UHD; 20-navigation leak check clean; WebGL-off fallback)*
- [ ] P4: product pages wired to real endpoints
- [ ] P5: Cognition Dashboard
- [ ] P6: evidence page, title justification, docs
- [ ] P7: hardening and full verification
- [ ] Open decision: Modbus RUL model (FUTURE-WORK until approved)
- [x] Decision: separate non-owner DB role for audit immutability *(both trigger and role, built in P2)*

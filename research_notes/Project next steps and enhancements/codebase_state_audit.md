# ATLAS codebase state audit (2026-11-16)

Scope: worktree `claude/project-checklist-enhancements-e05f15`, based on local `main` at `ee52006` (2026-11-11). Note: `origin/main` is one PR ahead (`46577b9`, PR #14 "split-conformal 90% RUL interval for C-MAPSS", merged 2026-11-16T17:20Z), so this worktree does NOT contain `server/atlas/rul_engine.py` conformal changes, `scripts/conformal_rul.py`, `tests/test_conformal_rul.py`, `docs/research/LANDSCAPE_REPORT_2026-11.md` (source: `git log origin/main -3`; `gh pr view 14`). All paths below are relative to the worktree root.

## What the system does today

### Takeaway
ATLAS is a working FastAPI + React platform with five domain adapters (C-MAPSS, laptop, mobile, cloud server, Modbus pump), a 32-dim Attention-LSTM world model per domain, pgvector memory (AMKB), Machine DNA, occlusion attribution, Monte Carlo simulation, a cost-weighted decision graph, batch retraining with a 3% gate, a hash-chained audit trail, and an ISA-101 industrial UI with 3D asset views. Real hardware validation is limited: server and mobile run on simulation fallback, pump data is simulated.

### Cited Findings
- Engines in `server/atlas/`: `world_model.py`, `amkb.py`, `machine_dna.py`, `adaptive_context.py`, `rul_engine.py`, `simulation.py`, `decision.py`, `explain.py`, `learning_engine.py`, `pretrain_domain.py`, `transfer_study.py`, `ablation_engine.py`, `profiled_inference.py`, `train_rul.py`, `train_pump_rul.py`, `domain_service.py` — (directory listing `server/atlas/`)
- Adapters: `CMAPSSAdapter` (`server/adapters/cmapss_adapter.py:283`), `LaptopAdapter` (`laptop_adapter.py:35`), `MobileAdapter` (`mobile_adapter.py:80`), `ServerAdapter` (`server_adapter.py:41`), `ModbusAdapter` (`modbus_adapter.py:146`), `ConfigurableAdapter` (`configurable_adapter.py:112`), all subclassing `MachineAdapter` (`base_adapter.py:200`); domain branches live behind `server/adapters/domain_profile.py` — (`ATLAS Master Checklist v1-v5 Design and Project Status.md` §1)
- Trained checkpoints exist for all five domains: `data/models/{cmapss,laptop,mobile,server,modbus}_world_model.pt` plus metadata JSON — (`data/models/` listing)
- Server adapter falls back to simulation when `SSH_SERVER_HOST` is unset, paramiko missing, or SSH fails — (`server/adapters/server_adapter.py:102,107,133,275`); mobile likewise — (`server/adapters/mobile_adapter.py:6`)
- Pump RUL is trained on simulated run-to-failure data (RMSE 7.72 cycles on 50 held-out simulated units); real-pump validation is FUTURE — (`ATLAS Master Checklist...md` §11; commit `c4b650b`)
- Platform layer: `server/audit.py` (hash-chained audit), `server/ingest.py`, `server/operations_api.py` (alarms, work orders), `server/cognition_admin.py`, `server/cognition_trace.py`, `server/platform_api.py`, `server/llm_agent.py`/`agent_tools.py` (work-order tool with grounding gate), `server/auth.py` (JWT, RBAC) — (directory listing `server/`; `SECURITY.md:39`)
- Client routes: fleet, assets (3D), cross-domain, alarms, work-orders, chat, about/evidence, admin/{users,onboarding,devices,models,diagnostics,cognition}, login, plus `/dev` gallery — (`client/src/app/routes.tsx:32-97`)
- Infra: multi-stage `Dockerfile` (node 20 build -> python:3.12-slim, non-root `appuser`, healthcheck on `/health`), `docker-compose.yml` (app, TimescaleDB 2.28.2-pg16, two Mosquitto services), CORS default `http://localhost:3000` — (`Dockerfile`; `docker-compose.yml:5,22,64,82,100`)
- License is Apache-2.0 — (`LICENSE:2`)

### Inferences
- The "Digital Twin" naming in SRS/SAD describes a different, older SQLite prototype; the live system is ATLAS.
- Dockerfile uses Python 3.12 while CI uses 3.10 (`.github/workflows/ci.yml` `PYTHON_VERSION: "3.10"`); the two are not tested on the same interpreter.

### Gaps
- Did not exercise the running server or UI (no `docker compose up`, no browser check).

## Docs versus code: unchecked and stale items

### Takeaway
The master checklist is mostly ticked; the open items are hardware/credential-bound (real VM, real phone, Twilio, HTTPS, `atlas_app` DB role switch), writing tasks (thesis synthesis, multi-seed variance, benchmark release), and doc hygiene. Several docs are stale: legacy SRS/SAD/Quick Start/Step-by-Step still describe a SQLite + 29-test prototype, the thesis chapter predates the pump domain, and one checklist item ("UI flow to resolve work orders (not built)") is actually built.

### Cited Findings
Open items in `ATLAS Master Checklist v1-v5 Design and Project Status.md` (last edited 2026-11-11):
- L61: Server adapter on a real cloud VM — needs user's VM
- L62: Mobile real-device run recorded — needs device
- L63: Bonus tier (HPC/industrial partner) — FUTURE
- L75 and L140: multi-seed mean ± std for all headline numbers (5-seed data only for C-MAPSS in `atlas_evaluation_summary.json`); domain encoders have one seed each (`docs/paper/ieee/paper.md` §Limitations, line ~211)
- L121: thesis synthesis (`docs/ATLAS_THESIS_CHAPTER.md` is a draft)
- L122/L198: keep `ATLAS_PROJECT_CONTEXT.md` Section 6 current (last edited 2026-11-10, before pump/retrain commits of 2026-11-11)
- L127-129: paper sections A/B/C still unticked although `docs/paper/ieee/paper.md` now contains all three (Results subsections at lines 126-178) — checklist is stale here
- L135-138: four patent candidates — moot: user decided no patent / no IP approvable (user memory `atlas-ip-ownership.md`, 2026-11-08); should be closed as "dropped"
- L139: open-source release of the ATLAS Cross-Domain Benchmark (data + eval scripts) — not done
- L178: Learning Engine promote/rollback `learning_events` audit rows (only 1 row in DB; covered by `tests/test_learning_engine.py`)
- L188: HTTPS via Nginx + Let's Encrypt — not deployed; no nginx/deploy directory exists (`ls deploy nginx` fails); `README.md:133` "HTTPS deployment needs a domain and is not set up yet"
- L189: Twilio live delivery (sandbox only) — also `SECURITY.md:66`
- L191: "UI flow to resolve work orders (not built)" — STALE: `client/src/pages/ops/WorkOrdersPage.tsx:22-27` implements approve/reject/start/resolve calling `/api/work-orders/{id}/resolve`
- L195: three conflicting doc sets; L197: retire/mark legacy SRS, SAD, ML guide
- L205: switch API to `atlas_app` role (`ATLAS_APP_DB_PASSWORD`, `scripts/migrate_platform.py`, `API_DATABASE_URL`) — needs user password choice
- Also unchecked: original Ablation 4 variant (single-domain vs cross-domain-informed world model) never run; only documented as changed (L133)

Legacy docs out of date:
- SRS header "Implementation Status (June 21, 2026)": rule-based detection, linear-trend RUL, SQLite, 29-test suite; roadmap lists Bhashini, ROS2, cloud sync — (`docs/Software Requirements Specification (SRS).md:5-7`); FR-2 FFT edge processing, FR-11 Twilio/Bhashini voice in configured language (`:66,83`). No Bhashini or OPC-UA code exists (grep of `server/`, `client/src` returned nothing); multilingual alerts only via `ALERT_LANGUAGES` env loop (`server/alert_handler.py:141`)
- SAD same June 2026 framing (SQLite, four simulated machines, Jetson edge) — (`docs/System Architecture Document (SAD).md:4-8`)
- "29 tests passed" appears in `docs/AI Agent Testing and Validation Document.md:5,30`, `docs/AI Digital Twin Prototype - Quick Start Checklist.md:5,107`, `docs/AI Digital Twin Prototype - Step-by-Step Completion Procedure.md:5,1846,1862`, `docs/Project Management and Execution Document.md:6`, SRS `:120`; `docs/LICENSE_OPTIONS.md:47` says 69; `docs/redesign/00_PLAN.md:47` says 290; `ATLAS_PROJECT_CONTEXT.md:132` says 378; `docs/redesign/CHANGELOG.md:12` says 455
- Quick Start Checklist unchecked: physical sensors, field accuracy validation, Bhashini/cloud sync, live provider testing, operator UAT, TLS/identity, SQLite backup — (`docs/AI Digital Twin Prototype - Quick Start Checklist.md:18-22,271-276`)
- Step-by-Step Procedure says USER_GUIDE/ADMIN_GUIDE not written and demo video not recorded (`...Step-by-Step Completion Procedure.md:1826-1829`); USER_GUIDE.md and ADMIN_GUIDE.md now exist (`docs/`), `docs/DEMO_VIDEO_SCRIPT.md` exists but no recorded video found
- Deployment guide unchecked: NTP, backups, monitoring, SSL, 48h baseline data, operator docs — (`docs/AI Agent Deployment and Operations Guide.md:72-94`)
- `ATLAS_PROJECT_CONTEXT.md:205` still has an unticked "Month 2 Week 1" box
- `docs/GOOD_FIRST_ISSUES.md` lists 10 unopened issues (OPC-UA adapter, REST polling adapter, Prometheus adapter, NASA IMS and AI4I loaders, MC-dropout RUL uncertainty, a11y pass, two tutorials, ruff widening) — none implemented (headings at lines 13-94); line 3 says "ready to paste into GitHub issues once the repository is opened"; `gh issue list` returned nothing

### Inferences
- PR #14 (conformal 90% RUL interval) partially addresses the paper's "confidence is uncalibrated" limitation and GOOD_FIRST_ISSUES #6 alternative, but only for C-MAPSS; paper text in this worktree does not mention it.
- Cheapest high-value doc work: tick/close stale checklist items, put a "LEGACY prototype" banner on SRS/SAD/Quick Start/Step-by-Step/Project Mgmt/Testing docs, and refresh Section 6 of the context file.

### Gaps
- Did not line-by-line audit SAD, VIVA_EXAMINER_QA.md, REPRODUCIBILITY.md, ATLAS_BENCHMARK.md numbers against JSON results.

## TODO / FIXME / future-work markers

### Takeaway
Code is clean of TODO/FIXME/XXX/NotImplementedError markers; remaining "future work" lives in docs and in the paper's limitations.

### Cited Findings
- `grep -rnE "TODO|FIXME|XXX|NotImplementedError|HACK"` over `server scripts ml client/src tests` returned zero hits.
- `server/atlas/simulation.py:17-19`: predictive-distribution modelling and listed out-of-scope actions are future work.
- Paper limitations: FD001 only; pump and compute results synthetic; compute domains have no failures; costs/lead times illustrative; decision graph does not beat a tuned threshold rule; confidence uncalibrated, no MC-dropout/ensemble comparison; label-derived health index; no hard safety override; one seed per domain encoder; PHM trails [2] — (`docs/paper/ieee/paper.md:209-211`)
- Paper future work: real cost/lead-time data, calibrated uncertainty, sensor-based health index, FD002-FD004, real pumps — (`docs/paper/ieee/paper.md:213-215`)
- Decision-graph tie-margin / defer-to-human policy is stated as FUTURE, not built — (`ATLAS Master Checklist...md` §8)

### Inferences
- FD002-FD004 and a hard safety override are the most concrete code items from the limitations list.

### Gaps
- None.

## Test and build status

### Takeaway
Locally, the tests that don't need the database pass (83 passed, 14 skipped), but the DB-backed tests fail because Docker/TimescaleDB is not running. CI on main is green (backend suite plus frontend build). The client could not be built locally because `client/node_modules` is absent; CI on GitHub builds it and is green on main.

### Cited Findings
- 48 test files in `tests/` (e.g. `test_amkb.py`, `test_learning_engine.py`, `test_attribution_faithfulness.py`, `test_work_order_safeguards.py`, `test_audit_trail.py`, `test_adapter_conformance.py`) — (`tests/` listing)
- Local pytest run (`conda run -n myenv python -m pytest -q -x`, 2026-11-16): **83 passed, 14 skipped, 1 failed** in 154 s before stopping on the first failure, `tests/test_api.py::test_control_endpoint_jwt_auth` with `psycopg_pool.PoolTimeout: couldn't get a connection after 30.00 sec`. Cause is environmental: Docker Desktop is not running (`docker ps` cannot reach `dockerDesktopLinuxEngine`), so TimescaleDB/pgvector is down. A second run without `-x` was cut off by a 590 s timeout, because every DB test waits 30 s for a pool connection, so there are no full local counts. The pytest-timeout plugin was not used. CI on GitHub (which has a live TimescaleDB) passes, so this is not a code failure.
- `client/node_modules` missing (count 0), so `npm run build` / `tsc` was skipped. Scripts: `build` = `tsc -b && vite build`, `lint`, `e2e` (Playwright) — (`client/package.json`)
- CI (`.github/workflows/ci.yml`): DCO sign-off, pre-commit lint (ruff, eslint), adapter conformance with public-boundary check, backend tests on TimescaleDB with migrations run twice for idempotency, frontend build. No Playwright/e2e, no Docker image build, no deploy job.
- Latest CI runs: main push of PR #14 success 2026-11-16; PR #13 and #12 success; one failure on 2026-11-12 on the PR #14 branch, later fixed — (`gh run list --limit 8`)
- Last recorded full-suite counts: 455 passed (`docs/redesign/CHANGELOG.md:12`)

### Inferences
- E2E (Playwright, axe) and Lighthouse run only locally; adding an e2e job to CI is a gap.

### Gaps
- Client typecheck not run locally (no node_modules; installing would modify the worktree).

## Launch and deployment blockers

### Takeaway
Favicon exists and there is no "Made with AI" tag, but there is no custom domain, no Privacy Policy page, no Terms page, no HTTPS reverse proxy config, and no deploy pipeline. Per the user's own launch rules these block a public launch.

### Cited Findings
- Favicon present: `client/public/favicon.svg`, linked in `client/index.html:5`
- No privacy or terms route: routes list has no such path (`client/src/app/routes.tsx:32-97`); grep for privacy/terms in `client/src` only hits a "Title terms" table on EvidencePage (`EvidencePage.tsx:254`)
- No "Made with AI"/"Generated with" text in `client/src` or `index.html` (grep empty)
- No domain configured: `.env.example` `CORS_ORIGINS=http://localhost:3000`; no nginx/Caddy/deploy files in repo
- `index.html` sets no-cache meta on every load (`client/index.html:9-11`) — fine for dev, poor for production caching
- Auth: JWT required at startup (`.env.example` "app will NOT start without this"), HttpOnly cookie + `X-API-Request` header, admin RBAC on retrain, MQTT anonymous off with ACLs (`ATLAS Master Checklist...md` §9 Security); `MOBILE_BRIDGE_TOKEN` required for mobile bridge
- Secrets: `.env.example` has empty `JWT_SECRET_KEY`, `MQTT_PASSWORD=CHANGE_ME`; CI generates per-run JWT and DB password, no repo secrets (`ci.yml` header comment)
- API still connects as DB owner until `atlas_app` switch (checklist L205)
- Launch rules (user memory `website-design-and-launch-rules.md`): blocked until custom domain, favicon, no "Made with AI" tag, Privacy Policy and Terms pages

### Inferences
- Outstanding launch blockers: domain, Privacy page, Terms page, HTTPS. Favicon and AI-tag rules are already met.

### Gaps
- Whether a hosting target has been chosen is not recorded anywhere in the repo.

## Git history and open threads

### Takeaway
Recent work (2026-11-08 to 11-16) finished the industrial redesign (P0-P7), pump RUL, per-domain attribution/retraining, the paper sync, and conformal RUL intervals. No open PRs. Old local branches are merged or stale.

### Cited Findings
- `git log`: PR #11 industrial frontend merged 2026-11-10; PR #12 pump RUL + attribution + retraining 2026-11-11; PR #13 paper sync 2026-11-11; PR #14 conformal RUL 2026-11-16 (origin only)
- `gh pr list --state open`: empty
- `feature/universal-adapter-sdk` shows 14 commits not in main, but `git cherry main feature/universal-adapter-sdk` reports 0 unmerged patches (content merged)
- `database` branch: 1 commit ahead, last 2026-07-09 "feat: add database URL" — stale
- `v1.1/open-source-readiness`, `work/security-defense-closeout`, `claude/atlas-industrial-redesign-d97242`: 0 ahead (merged)
- `ip/zero-energy-gate` local branch is likely stale since the IP gate was removed (user memory 2026-11-08)
- Remote `origin/devin/1789800814-review-fixes` exists; not examined
- ~20 local `claude/*` branches remain (`git branch -a`)

### Inferences
- Branch cleanup is low-effort housekeeping; nothing appears to hold unmerged feature work except possibly `database` and the devin remote branch.

### Gaps
- Did not diff `origin/devin/1789800814-review-fixes`.

## Paper and thesis status

### Takeaway
The IEEE paper (`docs/paper/ieee/paper.md`, ~4.3k words, 6-page target) is complete and synced through PR #13 but predates the conformal interval; the older v0.2 manuscript still has an "after IP clearance" placeholder; the thesis chapter is a stale draft with no pump/Modbus content and a "Continuous Learning Engine" heading that contradicts the batch-only rule.

### Cited Findings
- IEEE paper sections: Introduction, Literature Review, Methodology (adapter, world model, AMKB, DNA, explainability, simulation/decision graph, learning engine), Experimental Setup, Results (RUL, decision value, grounding, cross-domain, system performance, defects), Limitations, Conclusion, Code and Data Availability, References — (`docs/paper/ieee/paper.md:17-221`)
- Availability statement: "available from the authors on request" (`docs/paper/ieee/paper.md:219`) — could now point to the public Apache-2.0 repo
- Round-1 review and response exist (`docs/paper/ieee/review/ATLAS_review_round1.md`, `ATLAS_response_round1.md`); figures 1-6 and 8 in `docs/paper/ieee/`, figure 7 only in `docs/paper/figures/`
- v0.2 manuscript placeholder: "\[to be filled in after IP clearance and the license decision\]" (`docs/paper/ATLAS_research_paper_v0.2.md:188`)
- Thesis chapter last edited 2026-11-07; 0 mentions of "modbus" or "pump" (grep count); has "## 6. Continuous Learning Engine & Promotion Gate" (`docs/ATLAS_THESIS_CHAPTER.md:257`) while checklist §3 forbids "continuous learning" wording
- Checklist marks thesis synthesis open (L121)

### Inferences
- Paper next steps: add conformal interval result (PR #14) to Results/Limitations, update availability statement, choose venue and submit. Thesis: add Modbus/pump domain, retrain history, attribution-for-all-domains, conformal interval; rename "Continuous Learning".

### Gaps
- Did not check the .docx builds (`ATLAS_IEEE_Conference_Paper.docx`, `docs/ATLAS.docx`) for parity with the markdown.

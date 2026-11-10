# Redesign Changelog

## P5: Cognition Dashboard and model registry (2026-11-10)
- **What:**
  - **`/admin/cognition`** (admin only), for any machine and stored time:
    - Every stage with its latency: adapter raw to normalised with quality, the 32-dim state vector as a heat strip, a PCA trajectory of stored states.
    - AMKB neighbours, the Machine DNA fingerprint with drift and siblings, and the adaptive context with SYNTHETIC badges.
    - RUL with p10/p90 band over time, the Monte Carlo histogram with seed and N, Decision Graph costs and scores, occlusion attribution with AMKB citations, and learning history.
  - **Replay:** a scrubber over stored traces (`?ts=` deep link).
  - **Monitoring:** a drift monitor (data, model error, DNA) and fleet cognition health; recorded ablation and transfer-study results.
  - **`/admin/models`:** archived versions per domain with metrics; activate (promote or roll back) with reason and confirmation; C-MAPSS retrain through the existing 3% gate.
  - **Backend:**
    - `server/cognition_admin.py`: history with PCA and drift, health, registry, activate.
    - Trace stores gain `history` and `summary`.
    - The RUL stage adds `truth_cap` and `ground_truth_capped`.
  - **Charts:** `client/src/design/charts.tsx` (heat strip, scatter, bars, histogram, bar list, each with a hover readout and a values table); validated `--viz-*` colour tokens.
- **Why:** D5; ADR-025 to ADR-027.
- **Verified:**
  - pytest **432 passed** (was 418; new: PCA projection, data/model/DNA drift, history and health from stored traces, admin-only access, registry archive and activate with audit and undo, the ground-truth cap, and a snapshot of every stage's output keys). Ruff is clean.
  - `tsc -b` clean; eslint 0 errors (40 legacy warnings); initial JS 100 KB gz, Cognition a 7.8 KB gz lazy chunk.
  - Playwright flow 5 passes (trace all ten stages, second live trace, scrub to the oldest stored trace, back to live, registry), with flows 1-4 and 6 still passing.
  - Reviewed in the browser and fixed:
    - RMSE against uncapped labels (80 became about 10 with the cap).
    - Drift exploding on three traces.
    - Stretched PCA axes.
    - Charts drawn at half size and scaled up.
    - Tables overflowing their panels.
  - Screens: `docs/media/screens/p5-*.png`.
- **Audit incident (not product behaviour):** a scratch script that regenerated the trace snapshot ran with the default audit folder while the API restarted. Both resumed the JSONL mirror from the same tail, so seq 3765-3767 appear twice in `logs/audit/2026-11-10.jsonl`. The database chain, written only by the API, is intact (4,243 events). On the owner's instruction the three stray lines (identified by hash as absent from the database) were moved to `logs/audit/quarantine/` with the untouched original file and a note; `audit_verify.py` then reported JSONL and database intact (4,464 events, same tip). Two processes sharing one mirror folder should be refused outright: a single-writer lock is added to the P7 hardening list.
- **Not verified:**
  - Activating a version against the real checkpoints (tested on temporary copies only).
  - A full retraining run from the page.
  - Keyboard-only and screen-reader passes.

## P4: Product pages on real endpoints (2026-11-09)
- **What:**
  - **Pages** (`client/src/pages/ops/`):
    - Fleet overview: health grid, alarm summary, RUL at risk, ingestion health.
    - Cross-domain view.
    - Alarms & events: ISA-18.2 table; acknowledge, shelve with reason and time limit, unshelve, clear; flood indicator; deep link `?alarm=<id>`.
    - Work orders: create, approve, reject, start, assign, resolve, each behind a confirmation.
    - Agent chat, with AMKB evidence from the explanation engine.
    - Login on the design system.
    - Admin: users and roles, a seven-step sensor onboarding wizard (register map template, live preview over the stream, 3D part binding, token issue), devices (rotate, revoke), diagnostics.
  - **Asset Detail** gains session trends, a RUL band (± 1 sd), the Decision Graph's recommended action linked to a pre-filled work order, and live refresh from pushed readings.
  - **Every page** has loading, empty, error, stale and offline states; times show in Asia/Kolkata with the zone.
  - **Backend:**
    - `server/operations_api.py`: alarm states, work-order lifecycle and assignment, users and roles.
    - Migration columns on `alerts` and `work_orders`; `machine_id` widened to 64 characters.
    - `/api/assets` now carries RUL and timestamp.
    - Register-map template in the adapter layer (`/api/admin/sensor-profiles/template`; the Modbus bridge reuses it).
  - **Client plumbing:** typed `ApiError`, a correlation ID per request, `usePoll`, a fetch-based SSE reader, and interaction events to `/api/audit/client-events`.
  - **Fixed:**
    - Browsers could not open the live stream (CSRF header vs EventSource, ADR-023).
    - Audit inserts pending at shutdown were lost from the database; they are now backfilled at start-up (ADR-024).
    - The login password field's accessible name read "Password Show".
  - The old Login page moved to `_legacy/`.
  - Playwright 1.58.2 added with `client/e2e/` (run `npm run e2e`).
- **Why:** D6 and the D3 UI; ADR-018 to ADR-024.
- **Verified:**
  - pytest **418 passed** (was 392; new: alarm transitions, ack/shelve/clear audit with reason, shelve expiry, work-order lifecycle and assignment, role changes, RUL in the asset list, the profile template, audit backfill). Ruff is clean.
  - `tsc -b` clean; eslint 0 errors (40 legacy warnings); initial JS 100 KB gz.
  - Playwright, signed in against this branch's API: flows 1 (each role and a wrong password), 2 (onboarding wizard end to end), 3 (HTTP push on screen in 0.63 s side panel, 0.69 s 3D callout), 4 (pipeline alarm from fault injection, acknowledge, work order, approve) and 6 (operator gets no Cognition link, a role notice and API 403) all pass.
  - `audit_verify.py` after the run: JSONL and database intact, 3,539 events; each flow's actions are present (logins, profile, device, ingest batches, fault and simulation, alarm raise and ack, work order created and approved, page views and commands).
  - Screens: `docs/media/screens/p4-*-{light,dark}.png`.
- **Not verified:**
  - The MQTT leg of flow 3 (it needs a broker account for an onboarded device; the test skips with that reason).
  - Keyboard-only and screen-reader passes.
  - Lighthouse (P7).

## P3: 3D Asset View (2026-11-08)
- **What:**
  - **Teardown port** (`client/src/teardown/`): kit utilities and shader warm-up (MIT, credited), a light studio stage, geometry helpers, and five machines built from code to published proportions: turbofan (C-MAPSS), laptop, phone, 2U server, Modbus motor-driven pump.
  - **View** (`teardown/view.ts`): orbit and zoom, part picking with a callout, explode, cutaway, isolate, load tints in ISA-18.2 colours, "Show why" attribution glow, a tour (automatic in kiosk), quality tiers, a performance probe, and full disposal.
  - **Pages:** `/assets` (every showable asset), `/assets/:domain/:machineId` (KPIs, 3D stage, parts list, sensor ledger lines, Why panel), `/assets/kind/:kind` (used by the kiosk tour, which now visits all five machines). WebGL-off falls back to a 2-D schematic.
  - **Backend:** `server/adapters/asset_profiles.py` (parts and channel bindings per machine type), `server/asset_view.py` (`GET /api/assets`, `GET /api/assets/{id}/frame`, `GET /api/atlas/domain/{d}/profile`); domain snapshots now carry `raw_features`. `scripts/modbus_bridge.py` polls a Modbus device (or the bundled simulator) and pushes through the ingest API.
  - **Removed:** `@react-three/fiber` and `drei`; `MachineTwin3D.tsx` moved to `_legacy/`; the legacy pages link to the Asset View.
  - **Fixed:** the header's health probe no longer redirects to the login page on a 401.
- **Why:** D2; ADR-014 to ADR-017; full write-up in `03_3D_DECISION.md`.
- **Verified:**
  - pytest **392 passed** (was 378), ruff clean. 14 new tests: every binding points at a real part, bindings cover all 14 C-MAPSS features and all 6 Modbus registers, load direction, part states, units, STALE and SIMULATED, profile overrides, the asset list, 404/422/401, and the bridge's profile.
  - Intel UHD, Chrome: 54-60 fps at full quality, at most 118 draw calls; 20 navigations leave 0 live views and no console errors; WebGL-off renders the schematic; kiosk at 1920 x 1080 tours on its own.
  - `tsc -b` clean, eslint 0 errors (40 legacy warnings), build clean: initial JS 99 KB gz, the 3D chunk 152 KB gz and lazy, no dev gallery in `dist`.
  - Screens `docs/media/screens/p3-*.png`; film `docs/media/films/p3-asset-tour.mp4` with its frame sheet.
- **Not verified:** a signed-in run against a P3 backend (the Docker backend predates P2; screenshots use the dev gallery's SIMULATED frames); a keyboard-only and screen-reader pass of the asset page.

## P2: Backend foundation (2026-11-08)
- **What:**
  - **Audit trail:** `server/audit.py` (hash chain, JSONL mirror, ordered DB retry, redaction, logging filter); a request middleware with correlation IDs; audit events for auth (login, failure, logout, refresh), ingest batches, inference, Monte Carlo, decision, explanation, cognition traces, alarm raise, work orders, admin changes (before and after), model reload and retrain, MQTT and WebSocket connect/disconnect, simulator start/stop and fault injection; client interaction events at `POST /api/audit/client-events`.
  - **Database:** `scripts/migrate_platform.py` creates `audit_events` (trigger plus the `atlas_app` role with SELECT and INSERT only), `sensor_profiles`, `devices`, `sensor_readings` and `cognition_traces`.
  - **Ingestion:** `server/adapters/configurable_adapter.py` (profile-driven SDK adapter, quality flags) and `server/ingest.py` (stores, hashed device tokens, rate limit, stream broker).
  - **Endpoints** (`server/platform_api.py`): HTTP and WebSocket push, CSV/Parquet backfill with dry run, manual entry, admin sensor profiles and devices (issue, rotate, revoke, health), the SSE stream, and `/api/ready`.
  - **Cognition:** `server/cognition_trace.py` (admin-only trace, all 10 stages, replay).
  - **RBAC:** middleware makes every `/api/admin/*` path admin-only.
  - **Tools and docs:** `scripts/audit_verify.py`, `scripts/audit_export.py`, `docs/AUDIT_TRAIL.md`; `.env.example`, `docker-compose.yml` and `SECURITY.md` updated.
- **Why:** D3 (backend), D4 and the D5 backend; ADR-010 to ADR-013.
- **Verified:**
  - pytest **378 passed** (was 317), including 61 new tests: the chain and its tamper/deletion detection, restart resume, DB-outage retry, redaction, request and correlation auditing, login failure without the password, client events, trigger immutability, `atlas_app` privileges proven with `SET ROLE`, migration re-run, the configurable adapter (scaling, ranges, rejects, stale, flatline, missing, simulated), push auth, rate and size limits, token hashing and rotation, CSV dry run then commit, manual entry RBAC, MQTT routing, WebSocket push, the SSE stream, operator 403 on admin paths, viewer read-only, and the trace's stage order, dimensions (32/16), determinism, replay and agreement with `/api/context`.
  - The configurable adapter passes the existing SDK conformance suite. Ruff is clean, and the client build is clean.
  - Migration run twice against the local TimescaleDB.
- **Not done:** the API still connects as the owner in the local `.env` until `ATLAS_APP_DB_PASSWORD` and `API_DATABASE_URL` are set; alarm acknowledge and shelve (with the Alarms page, P4); Parquet without `pyarrow`.

## P1: Design system, shell, router, kiosk (2026-11-08)
- **What:**
  - `client/src/design/`: tokens (light and dark, ISA-18.2 priorities, data-quality states, motion), base styles, and about 25 components.
  - The AppShell with a role-filtered rail, a header (site, clock with zone, API link state, theme, user), the command palette, and every product route as a phase-labelled placeholder.
  - Kiosk mode (`?kiosk=1`), the dev-only `/dev/components` gallery, and self-hosted Inter + JetBrains Mono.
  - `PRODUCT.md` and the surface brief with the direction contract; `DESIGN.md` rewritten.
  - Login's `next` redirect now accepts any same-site path (blocks `//` and `/\`).
- **Why:** D1 of the brief; ADR-005 to ADR-009.
- **Files:** `client/src/design/*`, `client/src/app/*`, `client/src/dev/ComponentGallery.tsx`, `client/src/{App,main}.tsx`, `client/index.html`, `client/src/pages/{Home,Login}.tsx`, `client/package.json`, `PRODUCT.md`, `DESIGN.md`, `.impeccable/surfaces/client-src-design.md`, `.claude/launch.json`.
- **Verified:**
  - `tsc -b` clean, eslint 0 errors (40 warnings, all in legacy files), production build clean.
  - Initial JS 94.5 KB gzipped (budget 300 KB); the gallery is absent from `dist`.
  - axe-core 4.10 (WCAG 2.0/2.1/2.2 A and AA tags) on `/dev/components`: 0 violations in light and in dark (one dark-theme danger-button contrast failure found and fixed).
  - No horizontal overflow at 768 px. Kiosk at 1920×1080: 24 px root, no chrome. Palette keyboard flow and ConfirmDialog (focus trapped, confirm disabled until a reason) checked by script.
  - Screens in `docs/media/screens/p1-*.png`.
- **Not verified:** keyboard-only walk by a person; screen-reader pass; the impeccable finish review by a separate reviewer (scheduled for the P7 `/impeccable` audit).

## P0: merge `main` (2026-11-08)
- **What:** Merged `main` (26 commits: DEF-013 traversal fix, CORS hardening, Apache-2.0, hybrid fault classifier, CI and pre-commit gates) into the redesign branch. 18 conflicted files resolved per ADR-001. Fixed two merge fallouts: `useTheme` moved to `hooks/useTheme`, and an unused import in Login.
- **Why:** So the redesign doesn't ship over the unpatched code (GATE 0 decision 1).
- **Verified:** `npm run build` clean; `npm run lint` 0 errors (40 warnings already present); `ruff check` clean; pytest 317/317 (315 in the full run plus the 2 adjusted tests re-run, against live TimescaleDB).

## P0 Discovery (2026-11-08)
- **What:** Created branch `feature/industrial-frontend` from `feature/universal-adapter-sdk@1deba76`. Wrote `00_PLAN.md` (inventory, current vs target architecture, D1–D9 gap analysis, title matrix, phase plan, open decisions) and `DECISIONS.md` (ADR-001..004).
- **Why:** The prompt's P0 requires a plan before any code.
- **Files:** `docs/redesign/00_PLAN.md`, `docs/redesign/DECISIONS.md`, `docs/redesign/CHANGELOG.md`.
- **Verified:** Docs only; no code changed. Inventory read from source (routes grepped from `server/*.py`, schema from `scripts/migrate*.py`, frontend line counts, teardown kit imports).

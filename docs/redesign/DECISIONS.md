# Redesign Decisions (ADR log)

One entry per non-trivial decision. Format: context, options, choice, consequences.

## ADR-001: Base branch (P0)
- **Context:** The prompt says to cut from `feature/universal-adapter-sdk`, which is 14 commits ahead of `main` and 26 non-merge commits behind it (security fixes, relicense, CI).
- **Options:** (a) cut from the SDK branch as instructed; (b) cut from `main`; (c) cut from the SDK branch, then merge `main`.
- **Choice:** (c), approved at GATE 0. `main` merged into `feature/industrial-frontend`.
- **Conflict rules applied:** keep the stricter security behaviour from either side (login middleware + `CORS=*` fatal check; bridge token check; main's 404 on SPA traversal; known-hosts + `SSH_KNOWN_HOSTS_FILE`). Prefer the honest data path: main's 409 "warming up" over padding windows with repeated readings. Keep the branch's registry-based config loaders and its auth split (`server/auth.py`). Docker uses main's multi-stage frontend build plus the branch's data copies. Frontend pages get replaced in P1, so the build just has to stay green.
- **Consequences:** Two tests adjusted to the combined semantics: an unknown machine is 404 (SDK `UnknownMachineError`) and a partial window is 409; the alert mock carries the classifier's `rule_fault_type`. `SECURITY.md` still says read endpoints are public, but the login middleware already requires a session on every `/api` route except login, logout, health and the token-guarded bridge. That gets fixed with the D9 docs in P2.

## ADR-002: 3D integration via kit port, option (a) (P0, provisional)
- **Context:** The teardown kit is 921 lines of vanilla three.js that depends only on `three` and `three/addons`. The client already ships three 0.185.
- **Options:** (a) port the kit into `client/src/teardown/` and mount it imperatively; (b) build one-file HTML pages and embed them with an iframe + postMessage.
- **Choice:** (a). One three.js copy, shared design tokens, no message-bridge typing, and React owns the lifecycle, which makes the dispose/leak check possible. Full write-up in `03_3D_DECISION.md` (P3, ADR-014).
- **Consequences:** `@react-three/fiber` and `drei` get removed once `MachineTwin3D.tsx` is deleted. The kit's 1600×900 fixed HUD is replaced by the React side panel.

## ADR-003: Heterogeneous storage (P0, provisional)
- **Context:** The `telemetry` hypertable has 6 fixed columns and `machine_id VARCHAR(10)`.
- **Choice:** Add a long-format `sensor_readings(time, machine_id, channel, value, unit, quality, batch_id, source)` hypertable. The legacy table stays for MQTT shop-floor compatibility.

## ADR-005: Visual direction pinned by the brief; light default (P1)
- **Context:** The brief pins ISA-101 (greys, colour only for abnormal), ISA-18.2 priorities, Inter + JetBrains Mono and the motion tokens. Impeccable's Operate mode would push for more colour in the shell. The confirmed audience is examiners and showcase visitors; the kiosk screen is a 1080p projector.
- **Choice:** Brief wins. Identity comes from a graphite rail, one interaction blue (never a status) and the "ledger line" (value + unit + quality + time on every number). Light theme by default, from the scene (lit room, projector); dark mirrors it.
- **Consequences:** `DESIGN.md` is rewritten from the built tokens; the old Space Grotesk / Plus Jakarta spec is retired.

## ADR-006: React Router v7 with legacy pages kept alive (P1)
- **Context:** Deep links and role-gated routes need a router. The old Dashboard, Home and Login still carry working features until P4.
- **Choice:** `react-router@7.9.4` data router. The old pages move behind `/legacy/*` (and `/dashboard` redirects with its query string). Their stylesheet (`index.css`) loads only in their lazy chunk. New tokens and classes use names (`--surface-*`, `--ink-*`, `ax-*`) that cannot collide with it.
- **Consequences:** Once a legacy page has loaded, its CSS stays until reload. Accepted until P7 deletes the legacy pages.

## ADR-007: New route-aware command palette (P1)
- **Context:** `components/atlas/CommandPalette.tsx` is bound to the old dashboard's tab IDs.
- **Choice:** Keep the feature; build `design/CommandPalette.tsx` on the route table (role-filtered) plus theme and kiosk commands. The old one stays with the legacy dashboard until P7.

## ADR-008: Dev gallery renders with a stand-in session (P1)
- **Context:** `/dev/components` must show the real shell without needing a server login.
- **Choice:** The route exists only when `import.meta.env.DEV` is true. It provides a fixed `{username: 'gallery', role: 'admin'}` to `SessionContext`. The API still enforces auth on every request; the production build contains no gallery code (verified by grepping `dist`).

## ADR-009: Self-hosted fonts (P1)
- **Choice:** `@fontsource-variable/inter@5.2.8` and `@fontsource/jetbrains-mono@5.2.8` replace the Google Fonts links. That means no third-party request at load, and the showcase works offline.

## ADR-010: Audit trail design (P2)
- **Context:** D4 asks for an append-only, hash-chained record of every action, never shown in the UI.
- **Choice:** One writer thread per process assigns `seq` and `prev_hash`, writes the JSONL mirror first, then inserts into the `audit_events` hypertable. Failed inserts wait in order and are retried. The hashed canonical text is stored in a `canon` column, so the verifier does not depend on how JSONB re-serialises numbers. Immutability: a BEFORE UPDATE/DELETE trigger, plus (decided by the user at GATE 1) a separate non-owner role `atlas_app` with SELECT and INSERT only on `audit_events`.
- **Consequences:** The API must run as a single worker (noted as a shortcut in `server/audit.py`). Test runs write to a temporary folder with `AUDIT_DB=0`. The background streaming loop's per-second inferences are **not** audited one by one: that would be about 350,000 rows a day for four domains. Every API, trace and decision inference is audited. Summarising the streaming loop (for example, one row per machine per minute) is FUTURE-WORK if examiners ask for it.

## ADR-011: One ingest path for six transports (P2)
- **Choice:** HTTP, WebSocket, MQTT (profiled machines), CSV/Parquet and manual entry all call `IngestService.ingest`. Channel mapping, SI scaling, valid ranges and quality flags live in `ConfigurableAdapter` (Adapter Layer), which passes the SDK conformance suite. Readings go to a long-format `sensor_readings` hypertable with `batch_id` and `source`. Modbus TCP polling remains the existing `ModbusAdapter`; it is wired into onboarding in P4.
- **Consequences:** Parquet needs `pyarrow`, which is not installed. The upload returns 415 with a message until it is added. The live stream fan-out is in-process (single worker), like the audit writer.

## ADR-012: Cognition trace without touching the models (P2)
- **Choice:** The endpoint calls the same public engine methods as `/api/context`, `/api/explain` and `/api/decide`, timing each. The RUL p10/p90 are quantiles of the Normal(mean, √neighbour-variance) that the Simulation Engine samples. The failure-time histogram re-draws with the same seed, so it equals the engine's samples. A test asserts the trace RUL equals `/api/context`.
- **Consequences:** The World Model runs twice per trace (once for the state vector, once inside `build_context`); about 10 ms, accepted. Replay returns stored traces (`cognition_traces`), not recomputation. Machine DNA drift vs. baseline arrives in P5.

## ADR-013: `/api/ready` is the public probe (P2)
- **Context:** `/api/health` is also defined by the cognition router, which requires an operator session, so unauthenticated probes got 403.
- **Choice:** Add a public `/api/ready` reporting database, MQTT, loaded models and audit backlog (503 when degraded). The frontend header now polls it. `/api/health` is unchanged for existing clients.

## ADR-014: Teardown port without post-processing (P3)
- **Context:** ADR-002 chose to port the kit. The kit renders through an EffectComposer with bloom and GTAO, a fixed 1600 x 900 HUD, a film director and a score.
- **Choice:** Port the studio, shader warm-up, quality tiers, material rules and the hand-over tour; draw with plain MSAA rendering. Drop bloom (it eats detail in a monitoring view), GTAO (clipping-plane trap on cut models, and the costliest pass on integrated GPUs), the HUD (the React side panel replaces it) and the score. Each part gets its own material, so it can be tinted and faded alone. Full write-up: `03_3D_DECISION.md`.
- **Consequences:** 54-60 fps at full quality on Intel UHD for all five machines, at most 118 draw calls. `@react-three/fiber` and `drei` are removed; the old `MachineTwin3D.tsx` sits in `_legacy/` until P7, and the legacy pages link to the Asset View instead.

## ADR-015: Part bindings live on the server; the client draws by kind (P3)
- **Context:** The old twin kept domain tables (`twin/machineModels.ts`) in the frontend, against the ground rule that domain code lives only in `server/adapters/`.
- **Choice:** `server/adapters/asset_profiles.py` holds each machine type's parts and channel → part bindings with load direction and unit. `server/asset_view.py` serves a TwinFrame (parts with load and state, channels with value, raw value, unit and quality). Onboarded machines take the part from their sensor profile. The client knows only geometry by `kind`.
- **Consequences:** Part load is a heuristic (the bound channel furthest toward its load end; 0.75 elevated, 0.9 high) and the page says so. `twin/machineModels.ts` stays only for the legacy pages and goes in P7.

## ADR-016: Tour on request, automatic only in kiosk (P3)
- **Context:** The teardown rule is that a page left alone tours itself. An operator's asset page that starts moving on its own works against ISA-101 calm.
- **Choice:** A Tour button everywhere; in kiosk mode the tour starts at once and resumes after 25 s without input. Any pointer or wheel input hands control back.

## ADR-017: Verifying the 3D view without a server session (P3)
- **Context:** The checks (screenshots, fps, the 20-navigation leak test, WebGL-off, films) need the page running, but signing in needs the owner's credentials, and the running Docker backend predates P2.
- **Choice:** A dev-only `/dev/assets` route renders the real `AssetPage` through an `AssetSourceContext` fed by fixtures. The fixtures are TwinFrames built by the server's `build_frame()` from the real profiles with seeded values; every channel is SIMULATED and the explanation is labelled synthetic. Production builds contain none of it (checked in `dist`).
- **Consequences:** The live API path is covered by pytest (`tests/test_asset_view.py`), not by a signed-in browser run. That run happens in P4 once the backend is redeployed.

## ADR-018: Alarm states on the existing `alerts` table; clearing is an operator act (P4)
- **Context:** `alerts` has only an `acknowledged` flag. ISA-18.2 needs unacknowledged, acknowledged, shelved and cleared, with who, when and why. The pipelines that raise alarms do not report when a condition returns to normal.
- **Choice:** Add `state`, `state_by`, `state_at`, `state_reason` and `shelved_until` to `alerts` (`scripts/migrate_platform.py`, idempotent; existing acknowledged rows become `ack`). `server/operations_api.py` holds one transition table: acknowledge (unack to ack), shelve (needs a reason and 5 min to 24 h), unshelve, clear (ack to cleared, needs a reason). An expired shelve reads as unacknowledged again. The state is re-checked inside the UPDATE, so two operators cannot both act on one alarm (409). Every transition is audited with the reason.
- **Consequences:** Return to normal is not detected automatically; an operator clears with a reason and the dialog says so (FUTURE-WORK: derive `rtn_unack` from the machine's live status). `acknowledged` is kept in step for older readers.

## ADR-019: Work-order lifecycle and assignment (P4)
- **Context:** Work orders could be approved and resolved only; machine ids were limited to 10 characters, too short for `unit_17` or onboarded device names.
- **Choice:** Pending Approval to Open (approve) or Rejected (reject, reason required); Open to In Progress (start); Open or In Progress to Resolved. Operators and admins create orders (from the page, an alarm, or the asset's recommended action) and assign them to an operator or admin. `machine_id` widens to 64 characters; `assignee`, `domain`, `alarm_id` and `updated_at` are added. The existing approve and resolve endpoints keep their paths; resolve now also accepts In Progress.
- **Consequences:** One person may create and approve the same order; a four-eyes rule is not enforced (the audit trail shows both actions with the same name). Rejections are terminal.

## ADR-020: Interaction events by keepalive fetch, not sendBeacon (P4)
- **Context:** The brief names `navigator.sendBeacon` for client events. The API's CSRF check needs the `X-API-Request` header, which sendBeacon cannot set.
- **Choice:** `client/src/lib/events.ts` batches page views and every button or link press (its visible name and `aria-pressed`, never field values) and flushes every 10 s and when the page is hidden, with `fetch(..., {keepalive: true})`. It starts only after sign-in, so nothing on the login form is recorded.
- **Consequences:** Same delivery guarantee as sendBeacon (survives page close) without weakening CSRF. Delivery stays best effort; a failed batch is dropped, never retried in the UI.

## ADR-021: Templates for known devices come from the adapter layer (P4)
- **Context:** The onboarding wizard should fill in channels, units and ranges for devices ATLAS already knows. Hard-coding a Modbus register map in the wizard would put domain knowledge in the frontend.
- **Choice:** `sensor_profile_template()` in `server/adapters/asset_profiles.py` builds a SensorProfile from `ModbusAdapter`'s register map, with part bindings; `GET /api/admin/sensor-profiles/template` serves it and `scripts/modbus_bridge.py` reuses it. Other machine types return 404 and the wizard asks for a hand mapping.
- **Consequences:** The wizard has no domain branches. MQTT onboarding still needs a broker account per device in `mosquitto/config` (the wizard says so); creating broker accounts from the UI is FUTURE-WORK.

## ADR-022: Asset trends from the session, not a history query (P4)
- **Context:** Asset Detail needs live trends and a RUL band. Snapshot domains (C-MAPSS, laptop, phone, server) keep only the latest reading in memory; pushed machines are in `sensor_readings`.
- **Choice:** The page accumulates the frames it polls (every 2 s, up to 300 points) and draws RUL with a ± 1 sd band and the selected part's channels. Pushed readings arrive over the SSE stream and refresh the frame at once.
- **Consequences:** Trends start when the page opens ("Since this page opened" on the panel). A history endpoint over `sensor_readings` and the cognition traces can back longer trends in P5 (replay).

## ADR-023: The browser reads the live stream with fetch, not EventSource (P4)
- **Context:** `EventSource` cannot send headers, so the API's CSRF check (`X-API-Request`) refused the SSE stream from every browser with 403; only header-capable clients could use it since P2.
- **Choice:** Keep the CSRF rule for every path. `client/src/lib/useStream.ts` opens the stream with `fetch` (header set), parses the `text/event-stream` body itself and reconnects after 3 s. An exemption for the stream path was considered and rejected: it would weaken a security control for a client-side convenience.
- **Consequences:** No server change. Pushed readings reach the asset page in 0.6 to 0.9 s through the dev proxy (measured by e2e flow 3).

## ADR-024: Audit rows the database missed are backfilled from the mirror at start-up (P4)
- **Context:** After the e2e run `audit_verify.py` reported the database chain broken at seq 2: seq 1 sat in the JSONL mirror only. The writer keeps failed inserts in memory and retries in order, but a process that exits with inserts pending loses them, while the next start resumes the chain from the mirror.
- **Choice:** At start-up `AuditLog` reads the sequence numbers already in `audit_events` and queues every mirror event the database lacks, in order, before new events. Tests cover the exit-with-pending case and the no-duplicate case.
- **Consequences:** The database and the mirror converge after any restart; `audit_verify` reported both intact (3,539 events) after the final e2e run. Start-up reads all sequence numbers once (a range query is the upgrade when the table grows large).

## ADR-025: A model registry that archives checkpoints, outside the Learning Engine (P5)
- **Context:** D5 asks for a model registry with promote and rollback. The Learning Engine (frozen core) overwrites its checkpoint when a candidate passes the 3% gate and keeps no earlier versions, so nothing could be rolled back to.
- **Choice:** `server/cognition_admin.py` archives each domain's active checkpoint into `data/models/registry/<domain>/<content hash>.pt` with its metrics the first time it sees that content (gitignored). Activating a version archives the current weights first, swaps the file atomically and hot-reloads the streaming engine and the cognition pipeline's model; it needs admin, a reason, and is audited with before and after. New versions still come only from retraining through the existing gate (`POST /api/learn/retrain`, offered on the page for C-MAPSS).
- **Consequences:** No model code or maths changed. Weights overwritten before P5 cannot be recovered, and the page says so. For C-MAPSS the registry manages `best_model.pt` (the cognition pipeline's model); the streaming RUL engine loads `cmapss_world_model.pt`, an existing split this phase does not change. Tests exercise activation only on temporary copies, never the tracked checkpoints.

## ADR-026: How the dashboard measures drift and error (P5)
- **Context:** The first render showed an RMSE of 80 and data drift of 198,808 standard deviations. The C-MAPSS labels run to 270+ cycles while the model is trained on RUL capped at 125 (piecewise-linear target), and three stored traces left one sample per comparison window.
- **Choice:**
  - Error and model drift use the ground truth capped at the domain's training cap (`truth_cap`, 125 for C-MAPSS); the raw label stays in the trace as `ground_truth`. Error now reads about 10 cycles.
  - Data drift compares the first and last third of the stored traces, needs at least 3 traces on each side, and floors the pooled standard deviation at 1% of the normalised range.
  - Machine DNA drift is measured against the machine's first stored trace, because `machine_dna` keeps only the current fingerprint.
  - The PCA view draws both components on one scale.
- **Consequences:** Stored-trace RMSE is labelled as training-set replay, not a benchmark; the FD001 test benchmark (RMSE 15.42, PHM 394.7) is shown on the registry page. DNA drift reads 0 until the fingerprint is recomputed.

## ADR-027: Chart colours avoid the alarm palette (P5)
- **Context:** The dataviz default diverging pair is blue against red. In this product red means an ISA-18.2 critical alarm.
- **Choice:** Diverging blue against brown with a grey midpoint (`--viz-neg`, `--viz-pos`, `--viz-mid`), single-series marks in the accent blue. Light and dark steps were each run through the dataviz validator against their panel surface and pass every check (lightness, chroma, CVD separation, normal-vision floor, contrast). Each chart has a hover readout and a table of its values.

## ADR-028: Evidence comes from result files, never from the page (P6)
- **Context:** D7 asks for a title matrix backed by evidence, with anything unbacked marked FUTURE-WORK. The plan's "Explainable" evidence, an attribution faithfulness check, did not exist yet.
- **Choice:**
  - `scripts/attribution_faithfulness.py` runs a deletion test on the 100 FD001 test units.
    - It masks the top-k sensors ranked by the Explainability Engine's own occlusion attribution against k random sensors (20 draws, seed 42), using the same zero-column occlusion.
    - It only calls public methods of the frozen pipeline, and writes `data/attribution_faithfulness.json`, served at `/api/atlas/research/attribution-faithfulness`.
  - `/about/evidence` renders every number from the result files through the API and shows a plain "result file not found" note instead of any default.
  - `docs/TITLE_JUSTIFICATION.md` holds the same matrix with the command that reproduces each number.
  - Tests check that every repository path either document cites exists. An e2e test checks that every number loads and every in-product link opens a real page.
- **Consequences:**
  - The k = 1 deletion result is true by construction (the top-ranked sensor is the one whose single masking moves RUL most); the doc and page lean on k ≥ 2 (top-2: 35.4 vs 16.8 cycles, 90% of units; top-3: 42.4 vs 23.3, 94%).
  - The ablation's 47% cost reduction is always shown with its 281 cycles of early replacement.
  - Unbacked cells (richer retrain history, attribution beyond C-MAPSS, Modbus RUL, HTTPS) are labelled FUTURE-WORK.

## ADR-029: Hardening choices (P7)
- **Legacy removal:** the old tabbed dashboard, home page, R3F twin, `twin/machineModels.ts` (frontend domain tables) and `_legacy/` are deleted (git history keeps them); `/dashboard` bookmarks redirect to `/fleet`. A backend test that inspected the old MonitoringView now checks the same guarantee where it lives: the laptop's estimated temperature is labelled "Estimated temperature (heuristic)" by the server-side asset profile.
- **One audit writer:** `AuditLog` takes an exclusive OS lock on `<audit folder>/.writer.lock` (msvcrt on Windows, flock elsewhere) and raises `AuditFolderInUse` for a second writer; the OS releases it if the process dies. `audit_verify.py` compares the two copies at their newest shared sequence number, so an event in flight while the API writes is not reported as a break; a different hash there still is.
- **Kiosk:** the tour keeps its stop index in state; deriving it from the URL broke because `/assets/kind/<kind>` redirects to a concrete machine, which left the tour stuck on the laptop.
- **Accessibility:** asset-index links used `--accent-ink` (text-on-accent, white) and had no contrast; scrollable tables are focusable named regions; the header search button and rail links carry names that survive the narrow layout; headings focused by navigation show no ring.
- **Lighthouse:** run on the production build served by the API, signed in, with Lighthouse 12.2.1 and Playwright's Chromium (the chrome-devtools connector was unavailable). Desktop meets the target (94/100/100). Mobile throttled performance is 68 (LCP 6.0 s): about 134 KB of the main bundle and 59 KB of CSS are unused on Fleet. Recorded as open; splitting the shell bundle is the next step if phones matter.

## ADR-004: PCA, not UMAP (P0)
- **Context:** D5 asks for a "PCA/UMAP" 2-D projection of 32-dim states.
- **Choice:** PCA via numpy SVD. It avoids a new heavy dependency (umap-learn pulls in numba) and is deterministic.

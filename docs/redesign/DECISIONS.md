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

## ADR-004: PCA, not UMAP (P0)
- **Context:** D5 asks for a "PCA/UMAP" 2-D projection of 32-dim states.
- **Choice:** PCA via numpy SVD. It avoids a new heavy dependency (umap-learn pulls in numba) and is deterministic.

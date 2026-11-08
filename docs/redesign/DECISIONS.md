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
- **Choice:** (a). One three.js copy, shared design tokens, no message-bridge typing, and React owns the lifecycle, which makes the dispose/leak check possible. Full write-up goes in `03_3D_DECISION.md` during P3.
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

## ADR-004: PCA, not UMAP (P0)
- **Context:** D5 asks for a "PCA/UMAP" 2-D projection of 32-dim states.
- **Choice:** PCA via numpy SVD. It avoids a new heavy dependency (umap-learn pulls in numba) and is deterministic.

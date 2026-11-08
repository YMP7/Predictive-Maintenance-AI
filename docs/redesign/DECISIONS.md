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

## ADR-004: PCA, not UMAP (P0)
- **Context:** D5 asks for a "PCA/UMAP" 2-D projection of 32-dim states.
- **Choice:** PCA via numpy SVD. It avoids a new heavy dependency (umap-learn pulls in numba) and is deterministic.

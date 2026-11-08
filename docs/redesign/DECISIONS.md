# Redesign Decisions (ADR log)

One entry per non-trivial decision. Format: context, options, choice, consequences.

## ADR-001: Base branch (P0)
- **Context:** The prompt says to cut from `feature/universal-adapter-sdk`, which is 14 commits ahead of `main` and 26 non-merge commits behind it (security fixes, relicense, CI).
- **Options:** (a) cut from the SDK branch as instructed; (b) cut from `main`; (c) cut from the SDK branch, then merge `main`.
- **Choice:** (a) now. Proposing (c) at GATE 0, pending approval.
- **Consequences:** Until `main` is merged, this branch lacks the DEF-013 traversal fix and the CORS hardening.

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

# Redesign Changelog

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

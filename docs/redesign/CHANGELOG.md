# Redesign Changelog

## P0: merge `main` (2026-11-08)
- **What:** Merged `main` (26 commits: DEF-013 traversal fix, CORS hardening, Apache-2.0, hybrid fault classifier, CI and pre-commit gates) into the redesign branch. 18 conflicted files resolved per ADR-001. Fixed two merge fallouts: `useTheme` moved to `hooks/useTheme`, and an unused import in Login.
- **Why:** So the redesign doesn't ship over the unpatched code (GATE 0 decision 1).
- **Verified:** `npm run build` clean; `npm run lint` 0 errors (40 warnings already present); `ruff check` clean; pytest 317/317 (315 in the full run plus the 2 adjusted tests re-run, against live TimescaleDB).

## P0 Discovery (2026-11-08)
- **What:** Created branch `feature/industrial-frontend` from `feature/universal-adapter-sdk@1deba76`. Wrote `00_PLAN.md` (inventory, current vs target architecture, D1–D9 gap analysis, title matrix, phase plan, open decisions) and `DECISIONS.md` (ADR-001..004).
- **Why:** The prompt's P0 requires a plan before any code.
- **Files:** `docs/redesign/00_PLAN.md`, `docs/redesign/DECISIONS.md`, `docs/redesign/CHANGELOG.md`.
- **Verified:** Docs only; no code changed. Inventory read from source (routes grepped from `server/*.py`, schema from `scripts/migrate*.py`, frontend line counts, teardown kit imports).

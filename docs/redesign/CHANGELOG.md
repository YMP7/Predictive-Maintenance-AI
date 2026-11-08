# Redesign Changelog

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

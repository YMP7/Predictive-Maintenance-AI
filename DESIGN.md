---
name: ATLAS
description: ISA-101 machine-health ledger for explainable predictive maintenance
source: client/src/design/tokens.css (authoritative; this file describes it)
colors:
  surface-page: "#eceef1"
  surface-panel: "#f7f8fa"
  surface-raised: "#ffffff"
  line: "#d2d6dc"
  line-strong: "#a9b0b9"
  ink: "#14181d"
  ink-2: "#3d4650"
  ink-3: "#5a6470"
  rail-bg: "#1d2329"
  accent: "#1f5fbf"
  p-critical: "#c8102e"
  p-high: "#e35205"
  p-medium: "#e8b400"
  p-low: "#0e7c86"
  p-info: "#5a6470"
typography:
  ui: "Inter Variable (self-hosted, @fontsource-variable/inter)"
  numbers: "JetBrains Mono 400/500/600 (self-hosted), tabular-nums slashed-zero"
  scale-rem: [0.75, 0.8125, 0.875, 1, 1.25, 1.5, 2]
rounded:
  corner-1: "2px"
  corner-2: "3px"
  corner-3: "4px"
spacing: "4 px grid: 0.25 / 0.5 / 0.75 / 1 / 1.5 / 2 / 3 rem"
motion:
  ease-out: "cubic-bezier(0.23, 1, 0.32, 1)"
  ease-in-out: "cubic-bezier(0.77, 0, 0.175, 1)"
  ease-drawer: "cubic-bezier(0.32, 0.72, 0, 1)"
  durations: "150 / 250 / 350 ms; all 0 under prefers-reduced-motion"
breakpoints:
  tablet: "768px (minimum supported)"
  laptop: "1024px (rail collapses to icons below)"
  control-room: "1400px+"
---

# Design system: ATLAS

## 1. Direction

**North star: "The Technical Ledger", built to ISA-101.** ATLAS is a machine-health ledger, not a dashboard of cards. Every live value is an entry: value, SI unit, data-quality code, time. Normal is quiet grey. Only abnormal states earn colour, shape and motion.

It refuses two category defaults: the SaaS card grid, and the dark neon "control room" costume.

Scene: viva examiners at a laptop in a lit room, and a 1080p projector at the showcase viewed from 2–4 m. **Light is the default theme**; dark mirrors it for control rooms. The user's choice is remembered.

## 2. Colour

- **Neutrals carry the screen.** A cool graphite scale for the page, panels, lines and ink. `--ink-3` is the quietest text that still passes 4.5:1 on panels in both themes.
- **Graphite rail** (`--rail-bg`) gives the shell its identity in both themes.
- **One interaction accent** (`--accent`, blue) for selection, focus, links and primary actions. It is never a status.
- **ISA-18.2 priority hues** appear only on alarms and abnormal values. Each has three roles: fill (glyphs, bars), ink (text on panels) and soft (row and banner tint).

| Priority | Fill | Glyph |
|---|---|---|
| Critical | `#c8102e` | diamond |
| High | `#e35205` | triangle |
| Medium | `#e8b400` | square |
| Low | `#0e7c86` | circle |
| Info | `#5a6470` | circle with "i" |

**Colour is never the only signal.** Every priority pairs hue with a glyph shape and a word. Alarm state is shown by fill: unacknowledged is filled (and blinks unless reduced motion is set), acknowledged is outline, shelved and suppressed are a grey dashed outline, and cleared is a grey outline with a check.

**Data quality** is rendered on every live value as a code and an icon:

| Code | Icon | Shown as |
|---|---|---|
| `GOOD` | check | quiet; the only state without a coloured code |
| `STALE` | clock | value greyed |
| `OUT_OF_RANGE` | double chevron | value in high-priority ink |
| `FLATLINE` | dash | flagged |
| `MISSING` | slashed circle | `--` |
| `SIMULATED` | flask | dashed outline badge |

Synthetic data carries a `SYNTHETIC` badge.

## 3. Type

- Inter (variable) for UI text.
- JetBrains Mono with tabular, slashed-zero figures for **every number** (`.num`, `<time>`, numeric table cells), so columns align and live digits don't jitter.
- Base size 14 px. Scale 12 / 13 / 14 / 16 / 20 / 24 / 32 px. Headings 600 weight, balanced wrapping.
- No eyebrows or kickers above headings.
- Kiosk mode sets the root to 150 % (24 px base), and all sizes are rem.

## 4. Shape, depth, motion

- Square instrument corners: 2–4 px. **Never pills**; status labels are square tags.
- Panels sit flush with a 1 px line. Only overlays float, with an offset soft shadow.
- Motion uses the `.impeccable/design.json` easings. The only authored loops are the unacknowledged-alarm blink (ISA-101 convention) and the skeleton shimmer. Both are off under `prefers-reduced-motion`, and all durations drop to 0 there.

## 5. Components (`client/src/design/`)

| Component | File | Notes |
|---|---|---|
| AppShell, Header, SideNav, Page | `shell.tsx` | Graphite rail (role-filtered, collapsible); header with site, `Ctrl K`, API link state, clock with zone, theme, user and role; banner slot; skip link; focus moves to `h1` on navigation |
| Button, StatusPill, SimBadge, EvidenceLabel, PriorityGlyph, PriorityLabel, QualityBadge, Timestamp | `primitives.tsx` | `Timestamp` uses Asia/Kolkata by default (`atlas-tz` in localStorage) |
| LiveValue, KpiTile, Sparkline | `data.tsx` | `LiveValue` is the ledger line; KPI tiles are compact cells, not hero numbers |
| TrendChart | `TrendChart.tsx` | Recharts loaded lazily; p10–p90 band, threshold lines, tooltip, screen-reader summary |
| AlarmBanner, AlarmTable | `alarms.tsx`, `alarmModel.ts` | Banner exists only while something needs acknowledging; flood above 10 alarms in 10 min |
| DataTable | `DataTable.tsx` | Sortable headers (`aria-sort`), text filter, keyboard rows, windowed above 200 rows |
| Modal, Drawer, ConfirmDialog | `overlays.tsx` | Native `<dialog>`: focus trap, Esc, inert background. ConfirmDialog guards every write and can require a reason (≥ 5 characters) for the audit trail |
| CommandPalette | `CommandPalette.tsx` | Role-filtered routes plus theme and kiosk commands |
| EmptyState, ErrorState, Skeleton, StaleNotice, OfflineNotice | `states.tsx` | Errors name the problem and the recovery |

The gallery of every component in every state is at `/dev/components` and exists in development builds only.

## 6. Kiosk mode

`?kiosk=1` hides the rail and header, scales type by 150 % and shows one caption bar: title, current stop, progress and clock. The first input requests full screen. Any input hands control to the visitor; after 25 s of quiet the tour resumes. Esc exits kiosk mode. P3 replaces the page tour with the five 3D machines.

## 7. Don'ts

Purple or any gradients on text or surfaces, pill buttons, emoji icons, em dashes in UI copy, fake metrics or counters, a coloured side stripe thicker than 2 px (the only stripe is the 2 px unacknowledged-row marker), glass or blur as decoration, monospace for non-numeric text, and colour as the sole carrier of meaning.

---
version: 1
slug: "client-src-design"
primary_target: "client/src/design"
related_targets: ["client/src/App.tsx"]
---

# Surface: ATLAS app shell and design system (client/src/design)

Scope: every authenticated product screen (Fleet, Asset, Cross-Domain, Alarms, Work Orders, Chat, Admin, Cognition, Evidence) and kiosk mode. Mode: Operate. Build path: code-led (Operate surface; pinned direction, no concept roll).

Audience and job: viva examiners and showcase visitors judging whether the title is real; the demonstrated persona is a maintenance operator and an admin. Task: read asset health and RUL at a glance, act on abnormal states, drill into why.

Constraints: ISA-101 (grey, colour only for abnormal), ISA-18.2 priorities and states, data-quality on every live value, WCAG 2.2 AA, colour never the only signal, Asia/Kolkata time, SI units, no "digital twin" or "real-time learning" copy, user's banned patterns (no pill buttons, gradients, emoji, em dashes in UI copy).

## Direction contract

THESIS: A machine-health ledger, not a dashboard of cards. Every live value is an entry: value, unit, quality code, time. Normal is quiet grey; only abnormal earns colour, shape and motion. Refuses the card-grid SaaS dashboard and the dark neon "control room" costume.

OWN-WORLD: Light graphite ground (cool neutral greys), a graphite shell rail, hairline rules, one interaction blue for selection and focus only. ISA-18.2 priority hues (critical red, high orange, medium yellow, low cyan) always paired with a glyph shape (diamond, triangle, square, circle). Inter for UI, JetBrains Mono tabular figures for every number. Square corners (2-4 px). Dark theme mirrors it for control rooms.

STORY: The visitor sees the fleet's state in one read, notices the one abnormal row because it is the only coloured thing, opens it, and gets the why with evidence.

FIRST VIEWPORT: Left graphite rail (nav), top header (site, clock with zone, connection state), alarm banner only when an alarm is active, then the work area: a dense ledger table of assets with health, RUL band, quality and last seen, and a side detail panel.

FORM: Pinned by the brief (ISA-101 ledger HMI); no seed key, concept-seed not run because the direction was pinned.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Primary (confirmed 2026-11-08):** viva examiners and college showcase visitors. They judge whether every word of the title is backed by something working. Examiners sit at a laptop during the viva; showcase visitors watch a 1080p TV or projector from 2–4 m and may step up to drive it.
- **Demonstrated persona:** a maintenance operator (watches assets, acknowledges alarms, approves work orders) and an admin (onboards sensors, manages users and models). The product must operate credibly for them. The explanation for examiners lives in the Evidence page and kiosk captions, not in operator screens.
- Roles: `admin`, `operator`, `viewer`.

## Product Purpose

ATLAS: An Adaptive Machine Cognition Platform for Explainable Predictive Maintenance Across Heterogeneous Machine Systems. One cognition pipeline (perceive → remember → predict → simulate → decide → explain, with batch learning) runs over unlike machines: a C-MAPSS turbofan, a laptop, an Android phone, a server/VM and a Modbus rotating asset. Success means an examiner can point at any title term and be shown it working, with numbers.

## Positioning

Not one benchmark model: the same pipeline, behind a single adapter layer, predicts RUL with an uncertainty range, simulates outcomes, ranks maintenance actions by cost, and explains each prediction by citing similar past trajectories from its own memory (AMKB).

## Operating Context

- Viva: a laptop with the examiner beside it, light room.
- Showcase: `?kiosk=1` on a 1080p TV or projector, full-screen, auto-touring, viewed from 2–4 m in ambient light.
- Runs locally (Docker: FastAPI + TimescaleDB + Mosquitto) on Windows; no public deployment.

## Capabilities and Constraints

- Frozen ML core: World Model (32-dim state), AMKB, Machine DNA (16-dim), RUL, Simulation, Decision Graph, Explainability, Learning Engine (batch/periodic only). The UI exposes them; it never changes them.
- Domain-specific logic lives only in `server/adapters/`. The frontend reads domain metadata from the API.
- Terminology: say "3D Asset View", never "Digital Twin" as a component. Never "real-time learning" or "continuous learning".
- Every synthetic or simulated value carries a visible `SIMULATED` / `SYNTHETIC` badge. Features in docs are labelled BUILD or FUTURE-WORK.
- Time zone defaults to Asia/Kolkata; SI units throughout.
- Modbus pump RUL: built on SIMULATED run-to-failure data (approved 2026-11-10). It always carries the SIMULATED label; validation on real pump failures is FUTURE-WORK.

## Brand Commitments

- Name: ATLAS. The locked title above.
- From the brief: ISA-101 high-performance HMI philosophy, ISA-18.2 alarm priorities, Inter for UI and JetBrains Mono for numbers with tabular numerals, motion tokens from `.impeccable/design.json`.
- User's hard bans: purple gradients, pill-shaped buttons, fake reviews, fake metrics or counters, vague hero text, emoji icons, em dashes in UI copy, showy scroll or cursor animation, AI-slop imagery or copy.

## Evidence on Hand

- C-MAPSS FD001: RMSE 15.21 ± 0.31, PHM 375.00 ± 21.93 (5 seeds); `data/atlas_evaluation_summary.json`.
- Ablations: +47.17% lifecycle cost reduction; grounded confidence r_s = −0.509; `data/ablation_results.json`, `docs/ABLATION_STUDY_RESULTS.md`.
- Transfer study: MMD ≈ 1.23 vs 0.90–0.93, retrieval inflation 7.1–8.3×; `data/transfer_study_results.json`.
- Benchmarks: `docs/ATLAS_BENCHMARK.md`, `docs/ATLAS_RESOURCE_PROFILE.md`.
- Absent, never to be fabricated: industrial deployments, customers, testimonials, a real cloud-VM run (server is simulated), a recorded real-phone run.

## Product Principles

1. Every claim on screen links to its evidence; anything unproven is labelled FUTURE-WORK.
2. Normal is quiet. Colour and motion are spent on what is abnormal or changing.
3. Data quality is part of every value. A number without its quality, unit and time is incomplete.
4. Heterogeneity is shown, not asserted: the same screens serve every domain without domain branches.
5. Write actions are deliberate: confirmed, attributed and audited.

## Accessibility & Inclusion

WCAG 2.2 AA, full keyboard operation with visible focus, `prefers-reduced-motion` honoured, and colour never the only signal (always paired with a shape, icon or text). Kiosk type must read from 3 m on a 1080p projector.

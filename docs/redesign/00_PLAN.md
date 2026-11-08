# ATLAS Industrial Redesign: Plan (P0 Discovery)

Branch: `feature/industrial-frontend`, cut from `feature/universal-adapter-sdk` @ `1deba76`.
Written before any code. Status labels: **BUILD** (this redesign delivers it) or **FUTURE-WORK** (not delivered, never claimed).

---

## 1. What exists today (inventory)

### 1.1 Backend: one FastAPI app

`server/integrated_server.py` serves `server/backend_api.py:app`, which includes the cognition router from `server/api.py`, and mounts `client/dist` as an SPA.

| Area | Endpoints / modules | Verdict |
|---|---|---|
| Auth | `POST /api/auth/login`, `/logout`, `GET /api/auth/me`; JWT in an HttpOnly cookie; `X-API-Request` header acts as CSRF; `require_admin`, `require_operator_or_admin` (`server/auth.py`) | **Reuse.** Add `require_viewer`, token refresh, and audit hooks |
| Machines | `GET /api/machines`, `/{id}/status`, `/telemetry`, `/trends`; admin CRUD `/api/admin/machines` | **Reuse** |
| Alarms | `GET /api/alerts/recent`, `/alerts/machine/{id}`; `alerts` table has an `acknowledged` bool only | **Extend:** ISA-18.2 state machine (ack/shelve/suppress/clear + reason) |
| Work orders | `GET /api/work-orders`, `POST …/approve`, `PATCH …/resolve` | **Extend:** create, reject, assign, lifecycle |
| Cognition | `POST /api/context`, `/api/explain`, `/api/decide`; `GET /api/dna/{domain}/{id}`, `/api/learn/history`; admin `POST /api/learn/retrain` | **Reuse read-only.** Add the trace endpoint |
| ATLAS domains | `/api/atlas/domains`, `/domain/{d}/status`, `/domain/{d}/machine/{id}[/window]`, `/cross-domain/comparison`, `/models/status`, admin `/models/reload` | **Reuse.** Cross-Domain View and Fleet build on these |
| Research | `/api/atlas/research/transfer-study`, `/ablations`, `/evaluation/summary`, `/system/benchmark` | **Reuse** for Evidence and Cognition |
| Agent | `POST /api/agent/chat`, `GET /api/agent/memory/{id}` | **Reuse**, restyled UI |
| Mobile bridge | `/mobile-bridge`, `/lumia`, `POST /api/atlas/mobile/telemetry` | **Keep byte-compatible** |
| Health | `/health`, `/api/health`, `/api/status` | **Extend:** readiness that reports DB / MQTT / model state |
| Ingest | MQTT `factory/+/telemetry` (`server/mqtt_client.py`), fixed 6-column `telemetry` hypertable, `machine_id VARCHAR(10)` | **Gap:** heterogeneous channels need a long-format `sensor_readings` hypertable |
| Streaming to browser | none (polling in `useDashboardData.ts`) | **Gap** |
| Audit | `work_order_audit_log`, `learning_events` only | **Gap** (D4) |

Adapters (`server/adapters/`): `MachineAdapter` ABC plus `NormalizedReading`, and `DomainProfile` (cmapss, laptop, mobile, server). `ModbusAdapter` already reads a config-driven register map (scale, offset, bounds) and has a simulator and conformance tests. It is **not** in `DOMAIN_PROFILES` or `KNOWN_DOMAINS` and has **no trained World Model**.

### 1.2 Frontend (React 19, Vite 8, TS 6; no router; recharts; R3F + drei + three)

| File | Lines | Verdict |
|---|---|---|
| `App.tsx` | 105 | **Replace** the hand-rolled router with React Router plus lazy routes |
| `pages/Dashboard.tsx` | 550 | **Replace** with the AppShell and real pages |
| `pages/Home.tsx`, `Login.tsx`, `NotFound.tsx` | 320 | Login: **restyle**. Home: fold into Fleet. NotFound: **restyle** |
| `components/MachineTwin3D.tsx`, `twin/machineModels.ts` | 877 | **Delete.** Teardown replaces them. `machineModels.ts` holds domain tables (`DOMAIN_MODEL`, `LIMITS[domain]`, `diagnoseTurbofan`): **domain logic in the frontend, against the ground rules** |
| `components/atlas/views/*` (8 views) | 3,380 | **Mine** for API wiring. Reuse `AblationsView` and `TransferStudyView` inside Cognition. Rebuild the rest on the new components |
| `AgentChat.tsx` | 570 | **Restyle** |
| `CommandPalette.tsx` | n/a | **Keep** (prompt requires it) |
| `contexts/ThemeContext.tsx`, `SessionContext.tsx` | 64 | **Keep** |
| `lib/api.ts` | 48 | **Extend:** correlation-ID header, typed errors, offline detection |
| `index.css` | 850 | **Replace** with tokens in `client/src/design/` |

Baseline: `client/node_modules` is not installed in this worktree and `.env` is absent (gitignored). The backend test suite has 37 files; the checklist records 290 passing on the adapter-SDK branch.

### 1.3 Teardown kit (`~/.claude/skills/teardown`, MIT)

`sims/kit/` is 921 lines of vanilla three.js: `runtime.js`, `stage3d.js` (EffectComposer, bloom), `director.js` (auto-tour cursor), `hud.js`, `warm.js` (shader pre-compile), and `util.js` (seeded rng, easing). It imports only `three` and `three/addons/postprocessing/*`. The client already pins three 0.185, while teardown uses 0.186; the APIs are compatible. ffmpeg is on PATH. Playwright Chromium for capture still needs installing.

---

## 2. Architecture: current vs target

```
CURRENT                                         TARGET (additions marked +)
-------                                         ---------------------------
MQTT ─┐                                         MQTT ─┐  HTTP push+ ─┐  WS push+ ─┐  Modbus ─┐  CSV+ ─┐  Manual+ ─┐
      ▼                                               └──────────────┴────────────┴─────────┴───────┴──────────┘
mqtt_client → telemetry (6 fixed cols)                          ▼
                                                  + Ingest gateway (Pydantic, per-device token, rate limit)
Adapters (cmapss/laptop/mobile/server)                          ▼
      ▼                                           Adapter Layer  (+ ConfigurableAdapter reads SensorProfile)
DomainService (poll, snapshot cache)                            ▼
      ▼                                           + sensor_readings hypertable (long format, quality flag)
World Model → AMKB ↔ DNA → Context → RUL                        ▼
 → Simulation → Decision → Explain                FROZEN cognition core ── + read-only trace hooks (per-stage
      ▼                                                         │            output + latency, no math change)
REST (polling)                                                  ▼
      ▼                                           REST + SSE /api/stream/machines/{id}  + /api/admin/cognition/{id}/trace
React SPA (one Dashboard, tab views,                            ▼
 R3F twin with domain tables)                     React Router SPA: AppShell, Fleet, Asset (teardown stage), Cross-Domain,
                                                   Alarms, Work Orders, Chat, Admin (+Onboarding, Cognition), Evidence
                                                                │
                                                  + Audit: every request / ingest / inference / decision / client event
                                                    → audit_events (hash-chained, append-only) + logs/audit/*.jsonl
```

---

## 3. Gap analysis against D1–D9

| # | Deliverable | Exists | Gap → plan | Label |
|---|---|---|---|---|
| D1 | Design system | Ad-hoc `index.css`; stale `DESIGN.md` (Space Grotesk) vs live Inter + JetBrains Mono | `client/src/design/` tokens (ISA-101 greys, ISA-18.2 priority palette, data-quality states), ~20 base components, `/dev/components` (dev only), kiosk scaffold. Rewrite `DESIGN.md` | BUILD |
| D2 | 3D Asset View | R3F primitives, domain-keyed in the frontend | Port the kit to `client/src/teardown/` (option a). 5 machines, part→channel binding served by `GET /api/atlas/domain/{d}/profile`, attribution glow, "Show why", 2-D SVG fallback, dispose check, films | BUILD |
| D3 | Ingestion | MQTT, Modbus adapter, mobile push | `ConfigurableAdapter` + `sensor_profiles` table; HTTP/WS push with hashed device tokens; CSV/Parquet dry-run then commit; manual entry; `sensor_readings` hypertable; SSE stream; wizard + upload + device-health UI | BUILD |
| D4 | Audit trail | Two narrow audit tables | `audit_events` hypertable, hash chain, BEFORE UPDATE/DELETE trigger, JSONL mirror, redaction filter, ASGI middleware, correlation ID, `sendBeacon` client events, `audit_verify.py`, `audit_export.py`, `docs/AUDIT_TRAIL.md` | BUILD |
| D5 | Cognition Dashboard | `CognitionView` + `ExplainabilityView` (partial) | Trace endpoint (admin), 10 stage panels, latency, drift, replay scrubber, registry promote/rollback via existing `LearningEngine` | BUILD (UMAP → PCA only, see §5) |
| D6 | Product pages | One tabbed dashboard | 9 routed pages with loading / empty / error / stale / offline states, Asia/Kolkata timestamps, SI units | BUILD |
| D7 | Title justification | Results docs exist | `docs/TITLE_JUSTIFICATION.md` + `/about/evidence`, every cell linked or marked FUTURE-WORK | BUILD |
| D8 | Engineering docs | Context + checklist | `DECISIONS.md`, `CHANGELOG.md`, guide updates, OpenAPI descriptions | BUILD |
| D9 | Security/ops | Cookie JWT, CSRF header, CORS allow-list, RBAC | Rate limits, body-size limits, device tokens, readiness endpoint, JSON logs, degraded-mode banners, frontend in Docker image | BUILD. HTTPS deploy stays FUTURE-WORK (needs a domain) |

### Title matrix: provable today vs after the redesign

| Term | Today | After redesign | Risk |
|---|---|---|---|
| Adaptive | ACE + batch Learning Engine + transfer study exist, but only in docs/JSON | Cognition → Context / Learning tabs, retrain deltas from `learning_events` | Only 1 `learning_events` row exists; the retrain history will look thin |
| Machine Cognition | Pipeline exists; no per-stage view | Trace endpoint + pipeline UI with per-stage latency | None |
| Platform | Adapter SDK + conformance, RBAC, Docker | + Onboarding wizard, ingest APIs, audit | None |
| Explainable | Occlusion attribution + AMKB citations | "Show why" in 3D, faithfulness check (deletion test on the existing occlusion scores) | Attribution exists **only for 14-feature C-MAPSS**. Other domains return `attribution_unavailable_reason`, so their 3D attribution glow is FUTURE-WORK unless the existing occlusion method is generalised (§5 Q3) |
| Predictive Maintenance | RMSE 15.21 / PHM 375 on FD001; Decision Graph; work orders | Asset Detail → work order flow | None |
| Heterogeneous Systems | 4 domains | Cross-Domain View + 5 machines in 3D | Modbus has no trained model (§5 Q3) |

---

## 4. Phase plan with verification

| Phase | Builds | Verified by | Gate |
|---|---|---|---|
| P0 | This plan, DECISIONS, CHANGELOG | Reviewed by you | **GATE 0** |
| P1 | Tokens, ~20 components, AppShell, theme, kiosk, `/dev/components`, React Router skeleton | `tsc` / lint / build clean; axe on `/dev/components`; light + dark screenshots | **GATE 1** |
| P2 | Audit (tests first), `sensor_readings` + ingest paths, `ConfigurableAdapter` (passes the existing conformance suite), SSE, trace endpoint, viewer RBAC, rate limits | pytest: chain / immutability / redaction / ingest validation / conformance / RBAC 403 / trace schema | (none) |
| P3 | Teardown port + 5 machines, TwinFrame binding, Show why, kiosk tour, 2-D fallback, films | fps + draw-call probe, 20-navigation context-leak check, WebGL-off test, beat sheets read frame by frame | **GATE 2** |
| P4 | D6 pages wired to real endpoints | Playwright flows 1–4, 6 | (none) |
| P5 | Cognition Dashboard + replay + registry | Playwright flow 5; trace snapshot test | (none) |
| P6 | Evidence page + docs, wiki, final diagram | Every matrix link resolves | **GATE 3** |
| P7 | Full §4 verification, Lighthouse, overclaim grep, remove `_legacy/` | All checks in the prompt's §4 | **FINAL** |

Bundle plan for the ≤ 300 KB gz initial budget: the shell plus Fleet load eagerly; three.js, recharts, Cognition and Admin are lazy chunks.

---

## 5. Decisions I need from you at GATE 0

1. **Base branch is behind `main`.** `feature/universal-adapter-sdk` lacks 26 non-merge commits on `main`: static-file traversal fix (DEF-013), CORS hardening, Apache-2.0 relicense, hybrid fault classifier, CI and pre-commit gates, docker start fixes. Proposal: merge `main` into `feature/industrial-frontend` before P1, so the redesign doesn't ship over the unpatched code. Conflicts are likely in `server/`, `tests/` and docs.
2. **Title wording.** The prompt says *"…Predictive Maintenance over Heterogeneous Systems"*, but the locked title in `ATLAS_PROJECT_CONTEXT.md` §1 and the thesis is *"…Across Heterogeneous Machine Systems"*. I'll use the locked title unless you are changing it.
3. **Modbus as a 5th cognition domain.** The motor+pump 3D asset can show live channels and threshold health today. Real RUL / attribution for it would need (a) a `DomainProfile` entry and (b) a World Model pretrained with the existing `pretrain_domain.py`. That means the same architecture and math, but a new checkpoint and a new validated domain. Without it, the Modbus RUL cell is FUTURE-WORK and its 3D asset shows health only. The same question applies to generalising the occlusion attribution beyond 14 features: it's the same method, but `explain.py` is frozen core.
4. **Viewer role.** *(Corrected after the merge.)* `SECURITY.md` says reads are public, but `backend_api.require_login_for_api` already requires a session on every `/api` route except login, logout, health and the token-guarded mobile bridge. So `viewer` already sees everything an operator can read. Remaining question: should `viewer` be blocked from operator-only writes and `/api/admin/*`? Proposal: yes, enforced server-side.
5. **Immutability at the DB role level** needs a separate non-owner app role (`atlas_app`), because the table owner `dtwin` can bypass a REVOKE. That changes `docker-compose.yml` and `DATABASE_URL`. The trigger alone works with the current setup.

Framing checks (no action unless you disagree): Fleet Overview is a *view* of many assets, not the rejected "multi-machine fleet coordination". Work-order assignment/lifecycle is operational workflow, not the demoted Human Feedback Engine; no outcome feeds back into learning.

Deferred inside BUILD, recorded in DECISIONS: UMAP → PCA only (no new Python dependency); `/archify` is not installed here, so the diagrams are hand-drawn text and P6 uses `diagram-design`.

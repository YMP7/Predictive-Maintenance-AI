# ATLAS Test Execution Report

**Project:** ATLAS — An Adaptive Machine Cognition Platform for Explainable Predictive Maintenance Across Heterogeneous Machine Systems
**Execution Date:** 2026-08-25T17:10:27+05:30
**Executor:** Automated (`python -m pytest tests/ -v`)
**Environment:** Windows 11, Python 3.13.5, PyTorch 2.10.0+cpu, PostgreSQL/TimescaleDB/pgvector live

---

## 1. Summary

| Metric | Value |
|---|---|
| **Total Tests Collected** | 209 |
| **Passed** | **209** |
| **Failed** | **0** |
| **Errors** | **0** |
| **Warnings** | 20 (non-blocking library deprecations/thread cleanup) |
| **Execution Time** | ~216s |
| **Exit Code** | 0 |
| **Pass Rate** | **100.0%** |

---

## 2. Per-File Breakdown

### Phase A — Pre-ATLAS Prototype Tests (carried forward & hardened)

| Test File | Collected | Passed | Era | Origin Commit & Notes |
|---|---|---|---|---|
| `test_suite.py` | 15 | ✅ 15 | Pre-ATLAS | `532615e` (Initial baseline) |
| `test_api.py` | 14 | ✅ 14 | Pre-ATLAS | `532615e` (RBAC, CSRF, cookie auth) |
| `test_mqtt.py` | 10 | ✅ 10 | Pre-ATLAS | `627c19f` (Hardened with git credential guard & registry gate) |
| `test_notifications.py` | 8 | ✅ 8 | Pre-ATLAS | `59d0f8e` (Phase 5 Notifications) |
| `test_integration.py` | 2 | ✅ 2 | Pre-ATLAS | `532615e` |
| `test_ai_pipeline.py` | 1 | ✅ 1 | Pre-ATLAS | `2f47d40` |
| `test_performance.py` | 2 | ✅ 2 | Pre-ATLAS | `2f47d40` |
| **Subtotal** | **52** | **✅ 52** | | |

### Phase B — ATLAS Cognition Platform & Hardening Tests

| Test File | Collected | Passed | Month | Primary Scope |
|---|---|---|---|---|
| `test_adapters.py` | 18 | ✅ 18 | 1, 6 | All 4 adapters: schema, features, health_index |
| `test_amkb.py` | 18 | ✅ 18 | 2 | Vector store/retrieve, cosine similarity, isolation |
| `test_phase8_agent.py` | 10 | ✅ 10 | Pre-ATLAS Phase 8 | Agentic AI safeguards, provenance isolation |
| `test_transfer_study.py` | 9 | ✅ 9 | 7 | MMD, NTI, pairwise cosine, negative transfer |
| `test_rul_bounding.py` | 9 | ✅ 9 | 1, 3, 8 | Non-negativity, closed-form regression, uncapped noisy fit confidence |
| `test_explain.py` | 8 | ✅ 8 | 4 | Confidence, occlusion, citations, attribution |
| `test_adaptive_context.py` | 7 | ✅ 7 | 2, 6 | Multi-domain WorldModel, context building |
| `test_evaluation_cli.py` | 7 | ✅ 7 | 8 | InMemory ↔ pgvector equivalence, scorecard |
| `test_mobile_adapter.py` | 7 | ✅ 7 | 6, 8 | 3-tier hardware fallback (Termux → ADB → simulation) |
| `test_learning_engine.py` | 6 | ✅ 6 | 7 | Epsilon gate, rollback, audit trail |
| `test_decision.py` | 6 | ✅ 6 | 5 | Cost ranking, tie-breaker, safety overrides |
| `test_db.py` | 6 | ✅ 6 | 2+ | Connection pools, schema, migrations |
| `test_work_order_safeguards.py` | 6 | ✅ 6 | Pre-ATLAS Phase 8 | Volume caps, alert provenance, fault_type correlation |
| `test_ablations.py` | 5 | ✅ 5 | 7 | 4 canonical ablation validity |
| `test_domain_pretraining.py` | 5 | ✅ 5 | 7 | Self-supervised training, non-collapse guards |
| `test_server_adapter.py` | 5 | ✅ 5 | 6 | SSH contract, stress weights, simulation |
| `test_machine_dna.py` | 4 | ✅ 4 | 2 | Fingerprint, z-score, storage |
| `test_resource_profile.py` | 4 | ✅ 4 | 8 | RSS, leak detection, concurrency |
| `test_ui_mock_regression.py` | 4 | ✅ 4 | 8 | UI truth-in-reporting, canonical multi-seed PHM, dynamic clocks |
| `test_benchmark.py` | 3 | ✅ 3 | 8 | Stage timing, throughput |
| `test_multi_domain_queries.py` | 3 | ✅ 3 | 6 | Cross-domain query routing |
| `test_unified_api_routing.py` | 3 | ✅ 3 | 7, 8 | DEF-008 multi-domain encoder routing regression guard |
| `test_concurrency_ingest.py` | 2 | ✅ 2 | 8 | Multi-threaded AMKB write safety |
| `test_laptop_adapter.py` | 2 | ✅ 2 | 6 | Live psutil polling, stress score |
| **Subtotal** | **157** | **✅ 157** | | |

### Combined Total

| Category | Files | Collected | Passed | Pass Rate |
|---|---|---|---|---|
| Pre-ATLAS (Phase A) | 7 | 52 | 52 | 100% |
| ATLAS (Phase B) | 24 | 157 | 157 | 100% |
| **Total** | **31** | **209** | **209** | **100.0%** |

---

## 3. Warnings (Non-Blocking)

20 warnings were emitted during the test run. None affect test correctness:

| Warning Type | Source | Impact |
|---|---|---|
| `DeprecationWarning: on_event is deprecated` | FastAPI router events | Lifespan handler transition planned; non-blocking |
| `DeprecationWarning: per-request cookies` | Starlette `TestClient` | Upcoming API change in Starlette; test correctness unaffected |
| `DeprecationWarning: datetime.utcnow()` | `python-jose` JWT library | Scheduled removal in future Python; third-party library dependency |
| `ConnectionPool 'open' default` | `psycopg_pool` | Future release default parameter advisory |
| Post-run psycopg worker thread cleanup | Test process tear-down | Non-blocking thread shutdown delays |

---

## 4. Tests Modified or Added During ATLAS Development & Hardening

The following tests have notable histories relevant to the defect log:

| Test | History | Related Defect |
|---|---|---|
| `test_decision.py` → tie-breaker tests | Added Month 5 after discovering alphabetical tie-breaker bug favoring CONTINUE_OPERATION | DEF-004 |
| `test_domain_pretraining.py` → collapse guards | Added Month 7 W2 after discovering laptop channel collapse (Cosine < 0.20) | DEF-007 (related) |
| `test_evaluation_cli.py` → pgvector equivalence | Added Month 8 W3 to formally prove InMemoryAMKB ↔ pgvector < 10⁻⁵ drift | Preventive (NM-001) |
| `test_rul_bounding.py` → non-negativity & floor | Verifies ReLU removal (DEF-001), closed-form regression, and uncapped noisy R² | DEF-001, Hardening Fix 4 |
| `test_transfer_study.py` → NTI validation | Added Month 7 W2; refined after padding-artifact NTI flaw (DEF-006) | DEF-006 |
| `test_unified_api_routing.py` → routing guard | Enforces domain-specific encoder dispatch over zero-shot fallback | DEF-008 |
| `test_work_order_safeguards.py` → correlation | Verifies cross-fault justification exploit rejection and provenance filtering | DEF-012, Phase 8 |
| `test_mqtt.py` → registry check & credentials | Verifies unknown machine ID rejection and plaintext git tracking prevention | Hardening Fixes 2 & 3 |
| `test_ui_mock_regression.py` → mock regression | Verifies estimated-vs-measured segregation and canonical PHM baseline | UI Audit |

---

## 5. Previous Test Run Comparison

| Date | Total Tests | Passed | Failed | Notes |
|---|---|---|---|---|
| Pre-ATLAS (June 21, 2026) | 29 | 29 | 0 | Prototype-era baseline (documented in `AI Agent Testing and Validation Document.md`) |
| Month 8 Week 4 (Aug 23, 2026) | 192 | 192 | 0 | Last confirmed run before thesis QA freeze |
| Month 8 Final Verification (Sep 09, 2026) | 203 | 203 | 0 | Added UI mock regression and unified API routing suites |
| **Security & Hardening Audit (Sep 20, 2026)** | **209** | **209** | **0** | **Current live confirmation: 100% pass across all 31 test files** |

No regressions detected. Test count expanded from 192 to 209 via 17 permanent regression guards.

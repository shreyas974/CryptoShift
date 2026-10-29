# Requirements traceability

Status labels: **VERIFIED** (implemented and run, evidence below) · **PARTIAL** · **MOCKED** · **PLANNED** ·
**BLOCKED**. Evidence commands and outputs are in [`docs/evidence/stage0-stage1-log.md`](../evidence/stage0-stage1-log.md).

## Deliverables

| # | Requirement | Status | Evidence | Gap | Owner |
|---|---|---|---|---|---|
| D1 | Inventory with file/service evidence | **PARTIAL** | `inventory` CLI → CBOM-like JSON with file, line/directive, value, family, purpose, confidence, ambiguity, redacted snippet; `tests/test_inventory.py` (13 tests). Legacy `scan` gives 10 findings / 4 services on demo configs. | Service attribution is directory-level only; no real bank estate; not CycloneDX-validated. | Member 2 (review of new `inventory/`) |
| D2 | Migration sequence | **PARTIAL** | Deterministic wave scheduler: `test_deterministic_fallback_scheduler_respects_dependencies_and_capacity` passes (objective 248.105, waves 0–2). | Tasks come from SYNTHETIC `demo_bank_app/services.py`, not from inventory findings; durations/costs invented for the demo. | Member 3 |
| D3 | Working before-and-after protocol traces | **MOCKED** | `protocol_demo.py` returns `MOCKED_PROTOCOL_TRACE`; 544 B vs 7661 B are specification-derived estimates. | No real handshake captured. OpenSSL 3.5.9 (bundled with Git, not on PATH) lists `X25519MLKEM768` → feasible next step. | Member 3 |
| D4 | Compatibility tests | **MOCKED** | `verification.py` gate booleans are constant `True` unless wave-0 readiness is false or a failure is simulated. | No peer matrix actually executed. | Member 3 |
| D5 | Rollback plan | **PARTIAL** | `rollback.py` records + MVP slice restores a staged copy (`test_mvp_vertical_slice_human_approval_staging_and_rollback` passes). | No automation against real services; stop triggers not measured. | Member 3 |

## Evaluation items

| # | Requirement | Status | Evidence | Gap | Owner |
|---|---|---|---|---|---|
| E1 | Detection precision/recall on labelled code and configs | **PARTIAL** | Held-out public-code labels (3 repos, 8 files, 30 positives): TP 28, FP 0, FN 2 → P 1.000, R 0.933. Calibration (tuned on): TP 31, FP 0, FN 7. | **Not yet measurable at defensible size** (30 < 100 positives); single AI annotator who also wrote the detector; reviewer pending. Synthetic 0.875/0.875 is a smoke test only. | Member 1 (labels), Member 2 (detector) |
| E2 | Protocol correctness | **PLANNED** | — | Needs a real hybrid TLS 1.3 handshake (OpenSSL 3.5+) and trace comparison. | Member 3 |
| E3 | Overhead | **MOCKED** | Analytical byte budget in `protocol_demo.py`. | No measured latency/bytes. | Member 3 |
| E4 | Feasible migration dependencies | **PARTIAL** | `dependencies.validate_dependency_order` + scheduler test (no violations on the synthetic graph). | Dependency graph is synthetic; not derived from real service evidence. | Member 3 |

## Supporting requirements

| Requirement | Status | Evidence | Owner |
|---|---|---|---|
| Real-data summary without loading all rows | **VERIFIED** | `data-summary`: 320 rows / 5 dates / 0 duplicate keys; CESNET 25,000,000 rows, 14 tables, size matches manifest; 100,000 rows streamed in 4 h5py chunks. `tests/test_data_summary.py` (5 tests). | Member 1 / 3 |
| PQC role separation (ML-KEM vs ML-DSA/SLH-DSA; HOLD on unknown) | **VERIFIED** | `test_contextual_pqc_roles_distinguish_kem_vs_dsa`, `inventory/common.candidate_mapping`, cert test asserts ML-DSA for RSA certificate. | Member 2 |
| Secret hygiene | **VERIFIED** | `scripts/verify_repo.py` PASS; inventory skips `.env*`/`qcloud.env`/key stores unopened (unit test). | All |
| Risk score | **MOCKED / provisional** | `scoring.compute_service_risk`: mean of hand-set per-algorithm base risks × criticality multiplier (1.25/1.0/0.8) + min(retention_years/10, 1.5), capped at 10. Inputs are synthetic; weights are not validated. | Member 3 |

## Member 3 update (2026-10-29, additive)

Evidence: `docs/evidence/member3-log.md`, `reports/member3/summary.md`, `reports/member3/plan.json`.

| # | Requirement | Previous | Now | Evidence | Remaining gap |
|---|---|---|---|---|---|
| D2 | Migration sequence | PARTIAL | **VERIFIED on synthetic inputs** | `planning.planner` + deterministic scheduler: tasks from findings, provenance edges, objective 292.8, 0 violations | Constraint values are assumptions; 2 services have only declared data |
| D3 | Before-and-after protocol traces | MOCKED | **VERIFIED (TEST SCENARIO, loopback)** | `gates.openssl_lab.traces`: X25519 vs X25519MLKEM768; ML-DSA-65 certificate handshake | Not real bank peers or networks |
| D4 | Compatibility tests | MOCKED | **VERIFIED (loopback)** | 11/11 matrix cases incl. 7 negative | Service-specific stacks (KMS, JWT libs) untested |
| D5 | Rollback plan | PARTIAL | **VERIFIED rehearsal on a copy** | `gates.rollback_rehearsal`: failure → restore → hash → classical recovery | No real service deployment |
| E2 | Protocol correctness | PLANNED | **PARTIAL** | handshakes negotiate the expected group; ML-KEM/ML-DSA round-trip self-tests | No NIST KAT vectors; no transcript-level conformance testing |
| E3 | Overhead | MOCKED | **PARTIAL** | handshake bytes measured (+~1.1 kB each way); timings recorded | Timing dominated by process start-up; no network measurement |
| E4 | Feasible migration dependencies | PARTIAL | **VERIFIED on synthetic inputs** | 0 dependency violations; cycles detected and reported (tested) | Graph from synthetic configs |
| — | QpiAI Opt solve | REPORTED | **BLOCKED** | offline MILP checks only | Owner authorization + key needed |
| — | QAOA −13.07 | REPORTED | **REPRODUCED (SIMULATOR)** with documented caveats | `optimization.member3_qpiai` | Fixed-angle QAOA barely above uniform |

## Additions: web app v2

| # | Requirement | Previous | Now | Evidence | Remaining gap |
|---|---|---|---|---|---|
| — | Operator UI with evidence provenance | PARTIAL (Streamlit) | **VERIFIED (local)** | web app v2; `docs/webapp/parity.md`; E2E 7 passed | Folder-scan form PARTIAL; no deployment |
| — | Human approval in the UI | VERIFIED (tests only) | **VERIFIED (tests only), with auth + audit** | approver role, typed hash, CSRF, audit chain | No real approval recorded |

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

# Migration Verification, Protocol Overhead, and Rollback Guide

## 1. Context-Aware Mapping Rules (`src/cryptoshift/rules.py`)

CryptoShift classifies `operation_purpose` before recommending any NIST PQC replacement:

- **`key_establishment`:** Maps `ECDHE-P256`, `DH-2048`, and `RSA-2048` (OAEP key transport/wrapping, such as in `card_vault`) to **ML-KEM-768 / X25519MLKEM768 (NIST FIPS 203)**.
- **`digital_signature`:** Maps `RSA-2048` (RS256, XMLDSig, manifest signing) and `ECDSA-P256` (ES256, ledger notarization) to **ML-DSA-65 (NIST FIPS 204)** dual-signatures.
- **`symmetric_encryption`:** Maps `3DES` to **AES-256-GCM (NIST SP 800-38D)**.
- **`message_digest`:** Maps `SHA-1` to **SHA3-256 / SHA-384 (NIST FIPS 202)**.
- **`unknown`:** Places automatic mapping on **`HOLD`** pending human review.

---

## 2. Verification Gates & Protocol Overhead Methodology (`src/cryptoshift/verification.py`, `src/cryptoshift/protocol_demo.py`)

For every scheduled service and wave, `VerificationGateResult` records:
- `input_revision`: Pinned fixture revision (`HEAD-synthetic-fixture-v1`)
- `finding_ids` & `dependency_prerequisites`: Exact CBOM finding IDs and upstream service dependencies
- `peer_combinations_tested`: `legacy_peer -> hybrid_service` and `hybrid_peer -> hybrid_service`
- `trace_reference`: Explicitly labelled **`MOCKED_PROTOCOL_TRACE`** combining real `hashlib` (`SHA-1`, `SHA3-256`, `HMAC-SHA3-256`) digests with analytical NIST FIPS 203 (Table 2) and FIPS 204 (Table 1) wire sizes (`544` bytes classical envelope vs. `7661` bytes hybrid `X25519MLKEM768` + `ML-DSA-65` envelope; `+7117` bytes delta)
- `approver`: `pending_human_security_architect_review`

---

## 3. Rollback Plan & Policy Warnings (`src/cryptoshift/rollback.py`)

Each `RollbackEvent` records:
- `snapshot_id` & `known_good_config_version` (`v1.4.2-pre-pqc-baseline`)
- `feature_flag`: `CRYPTOSHIFT_ENABLE_HYBRID_PQC=false`
- `owner`: Responsible engineering/operations team
- `measurable_stop_trigger`: `p99 handshake latency > 15ms OR TLS/signature verification error rate > 0.1%`
- `policy_note`: Explicitly warns operators when a service's legacy configuration includes `SHA-1` or `3DES`, noting that reverting to deprecated weak primitives violates NIST SP 800-131A policy and requires classical `SHA-256` / `AES-256-GCM` baseline fallback instead.

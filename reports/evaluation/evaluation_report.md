# CryptoShift — Detection Evaluation Report

- **Dataset Scope:** SYNTHETIC_FIXTURE_EVALUATION (Visibly separated in data/fixtures/synthetic/; NOT real-world banking data)
- **Unit of Analysis:** One labelled file-level cryptographic operation instance (requiring both algorithm clue and operation_purpose match for TP).
- **Repository Split Method:** Repository-level split across 3 synthetic mini-projects (calibration: project_alpha_auth; held_out_test: project_beta_tls, project_gamma_noncrypto).

## 1. Confusion Matrix & Summary Metrics (Synthetic Fixture Suite)

| Metric | Value | Formula / Definition |
|---|---:|---|
| **True Positives (TP)** | `7` | Migration-relevant crypto present AND both algorithm & operation_purpose matched |
| **False Positives (FP)** | `1` | Non-migration/decoy fixture flagged by static pattern |
| **False Negatives (FN)** | `1` | Migration-relevant crypto missed (e.g., indirect dynamic reflection call) |
| **True Negatives (TN)** | `2` | Clean/modern PQC or non-crypto file correctly ignored |
| **Precision** | **`0.8750`** | `TP / (TP + FP)` |
| **Recall** | **`0.8750`** | `TP / (TP + FN)` |

## 2. Per-Instance Breakdown

| Instance ID | Repository Split | File Path | Expected (Alg / Purpose) | Detected Count | Verdict | Notes |
|---|---|---|---|---:|---|---|
| `SYN-001` | `calibration` | `data/fixtures/synthetic/project_alpha_auth/jwt_signer.py` | `RSA-2048` / `digital_signature` | 2 | **TP** | OAuth2 RS256 token signing using RSA-2048 -> maps to ML-DSA-65 (FIPS 204). |
| `SYN-002` | `calibration` | `data/fixtures/synthetic/project_alpha_auth/token_digest.py` | `SHA-1` / `message_digest` | 1 | **TP** | Legacy certificate thumbprint using hashlib.sha1 -> maps to SHA3-256. |
| `SYN-003` | `calibration` | `data/fixtures/synthetic/project_alpha_auth/vault_wrapper.py` | `RSA-2048` / `key_establishment` | 2 | **TP** | RSA-OAEP key wrapping of DEKs -> maps to ML-KEM-768 (FIPS 203), NOT ML-DSA. |
| `SYN-004` | `held_out_test` | `data/fixtures/synthetic/project_beta_tls/mtls_config.yaml` | `ECDHE-P256` / `key_establishment` | 1 | **TP** | Interbank mTLS key exchange configuration -> maps to X25519MLKEM768 (FIPS 203). |
| `SYN-005` | `held_out_test` | `data/fixtures/synthetic/project_beta_tls/payment_ecdsa.py` | `ECDSA-P256` / `digital_signature` | 2 | **TP** | ECDSA secp256r1 payment instruction signature -> maps to ML-DSA-65 (FIPS 204). |
| `SYN-006` | `held_out_test` | `data/fixtures/synthetic/project_beta_tls/legacy_batch_cipher.py` | `3DES` / `symmetric_encryption` | 2 | **TP** | TripleDES batch encryption -> maps to AES-256-GCM. |
| `SYN-007` | `held_out_test` | `data/fixtures/synthetic/project_beta_tls/sftp_dh_exchange.py` | `DH-2048` / `key_establishment` | 1 | **TP** | Finite-field diffie-hellman-group14 key exchange -> maps to ML-KEM-768. |
| `SYN-008` | `held_out_test` | `data/fixtures/synthetic/project_beta_tls/dynamic_reflection_cipher.py` | `SHA-1` / `message_digest` | 0 | **FN** | Edge case (FN): dynamically resolves getattr(hashlib, 'sh' + 'a1') at runtime; static scanner misses it. |
| `SYN-009` | `held_out_test` | `data/fixtures/synthetic/project_gamma_noncrypto/ui_layout_helper.py` | `None (Negative/Decoy)` | 0 | **TN** | True Negative decoy: contains non-crypto identifiers like rsa_building_floor = 2048. |
| `SYN-010` | `held_out_test` | `data/fixtures/synthetic/project_gamma_noncrypto/modern_pqc_service.py` | `None (Negative/Decoy)` | 0 | **TN** | True Negative: service already uses SHA3-256 and hybrid X25519MLKEM768. |
| `SYN-011` | `held_out_test` | `data/fixtures/synthetic/project_gamma_noncrypto/ambiguous_legacy_note.yaml` | `None (Negative/Decoy)` | 1 | **FP** | Edge case (FP): inactive config flag LEGACY_RSA_2048_CONFIG=false triggers medium-confidence review alert. |

## 3. Scope Limitations

- These precision and recall counts are measured on a small, controlled synthetic fixture suite (data/fixtures/synthetic/) to verify detector logic and error modes (such as dynamic reflection FN and ambiguous config FP).
- Synthetic fixture scores do NOT represent detection performance on real-world production banking estates.
- Public open-source repository references in data/labels/public_repo_references.json are pinned by URL and commit SHA for reproducible external evaluation without redistributing third-party source trees.

# CryptoShift — Operator MVP Vertical Slice Audit Report

- **Run ID:** `RUN-20261029T180929Z`
- **Created At (UTC):** `2026-10-29T18:09:29.167204+00:00`
- **Scanned Target Path:** `demo_bank_app/configs`
- **Human Approval Status:** **`HELD_FOR_HUMAN_APPROVAL`** (Approver: `None — Preview Only`)
- **Original Source Files Unmodified:** `True`
- **Pre-Patch Findings in Scanned Files:** `10`
- **Post-Patch Findings in Staged Copy:** `None`
- **SQLite Audit Database:** `scratch/mvp_workspace/cryptoshift_mvp.db`

## 1. Traceable File & Configuration CBOM Inventory

| Finding ID | Service | File Path | Line | Directive / Context | Legacy Alg | Purpose | Target PQC (NIST Standard) | Confidence |
|---|---|---|---:|---|---|---|---|---|
| `YML-auth_gateway_tls-01` | `auth_gateway` | `C:/Users/lohig/OneDrive/Documents/CryptoShift_Member3/demo_bank_app/configs/auth_gateway_tls.yaml` | 11 | `yaml:oauth_jwt.signing_algorithm=RS256` | `RSA-2048` | `digital_signature` | ML-DSA-65 + RSA-2048 Hybrid Signature (`FIPS 204 (ML-DSA)`) | `high` |
| `YML-auth_gateway_tls-02` | `auth_gateway` | `C:/Users/lohig/OneDrive/Documents/CryptoShift_Member3/demo_bank_app/configs/auth_gateway_tls.yaml` | 13 | `yaml:oauth_jwt.thumbprint_digest=hashlib.sha1` | `SHA-1` | `message_digest` | SHA3-256 / SHA-384 (`FIPS 202 (SHA-3)`) | `high` |
| `YML-auth_gateway_tls-03` | `auth_gateway` | `C:/Users/lohig/OneDrive/Documents/CryptoShift_Member3/demo_bank_app/configs/auth_gateway_tls.yaml` | 17 | `yaml:tls_listener.key_exchange_curve=ECDHE-P256` | `ECDHE-P256` | `key_establishment` | X25519MLKEM768 Hybrid Key Establishment (`FIPS 203 (ML-KEM)`) | `high` |
| `YML-card_vault_crypto-01` | `card_vault` | `C:/Users/lohig/OneDrive/Documents/CryptoShift_Member3/demo_bank_app/configs/card_vault_crypto.yaml` | 13 | `yaml:kms_envelope.dek_wrapping_algorithm=RSA_OAEP` | `RSA-2048` | `key_establishment` | ML-KEM-768 (FIPS 203) Hybrid Key Encapsulation (`FIPS 203 (ML-KEM)`) | `high` |
| `YML-card_vault_crypto-02` | `card_vault` | `C:/Users/lohig/OneDrive/Documents/CryptoShift_Member3/demo_bank_app/configs/card_vault_crypto.yaml` | 15 | `yaml:kms_envelope.pin_block_cipher=3DES` | `3DES` | `symmetric_encryption` | AES-256-GCM (`NIST SP 800-38D`) | `high` |
| `NGX-interbank_tls_nginx-01` | `interbank_tls` | `C:/Users/lohig/OneDrive/Documents/CryptoShift_Member3/demo_bank_app/configs/interbank_tls_nginx.conf` | 11 | `nginx:ssl_ecdh_curve=prime256v1` | `ECDHE-P256` | `key_establishment` | X25519MLKEM768 Hybrid Key Establishment (`FIPS 203 (ML-KEM)`) | `high` |
| `NGX-interbank_tls_nginx-02` | `interbank_tls` | `C:/Users/lohig/OneDrive/Documents/CryptoShift_Member3/demo_bank_app/configs/interbank_tls_nginx.conf` | 12 | `nginx:ssl_ciphers=ECDHE-RSA-AES256-GCM-SHA384:DES-CBC3-SHA` | `3DES` | `symmetric_encryption` | AES-256-GCM (`NIST SP 800-38D`) | `high` |
| `NGX-interbank_tls_nginx-03` | `interbank_tls` | `C:/Users/lohig/OneDrive/Documents/CryptoShift_Member3/demo_bank_app/configs/interbank_tls_nginx.conf` | 16 | `nginx:ssl_certificate=/etc/nginx/certs/interbank_rsa2048_cert.pem` | `RSA-2048` | `digital_signature` | ML-DSA-65 + RSA-2048 Hybrid Signature (`FIPS 204 (ML-DSA)`) | `high` |
| `SCAN-payment_signing_service-01` | `payment_signing` | `C:/Users/lohig/OneDrive/Documents/CryptoShift_Member3/demo_bank_app/configs/payment_signing_service.py` | 8 | `static_file_scan` | `ECDSA-P256` | `digital_signature` | ML-DSA-65 + ECDSA-P256 Dual-Signature (`FIPS 204 (ML-DSA)`) | `high` |
| `SCAN-payment_signing_service-02` | `payment_signing` | `C:/Users/lohig/OneDrive/Documents/CryptoShift_Member3/demo_bank_app/configs/payment_signing_service.py` | 9 | `static_file_scan` | `RSA-2048` | `digital_signature` | ML-DSA-65 + RSA-2048 Hybrid Signature (`FIPS 204 (ML-DSA)`) | `high` |

## 2. Explainable Risk Prioritization & Dependency Sequencing

| Service ID | Criticality | Legacy Primitives | Mean Alg Risk | Crit. Mult | HNDL Bonus | Final Risk Score | Upstream Dependencies | Assigned Wave |
|---|---|---|---:|---:|---:|---:|---|---:|
| `interbank_tls` | `CRITICAL` | `ECDHE-P256, RSA-2048` | 4.65 | 1.25 | +1.20 | **`7.01`** | `(root)` | Wave `0` |
| `settlement_batch` | `CRITICAL` | `DH-2048, RSA-2048, 3DES` | 4.03 | 1.25 | +1.50 | **`6.54`** | `payment_signing, interbank_tls` | Wave `2` |
| `payment_signing` | `CRITICAL` | `ECDSA-P256, RSA-2048` | 4.40 | 1.25 | +1.00 | **`6.50`** | `auth_gateway, ledger_audit` | Wave `1` |
| `ledger_audit` | `CRITICAL` | `ECDSA-P256, SHA-1` | 3.65 | 1.25 | +1.50 | **`6.06`** | `(root)` | Wave `0` |
| `card_vault` | `HIGH` | `RSA-2048, 3DES` | 3.85 | 1.00 | +1.00 | **`4.85`** | `auth_gateway` | Wave `2` |
| `auth_gateway` | `HIGH` | `RSA-2048, SHA-1` | 3.75 | 1.00 | +1.00 | **`4.75`** | `(root)` | Wave `1` |

## 3. Patch Proposals & Human Approval Gate

### Proposal `RUN-20261029T180929Z-P01` — `demo_bank_app/configs/auth_gateway_tls.yaml` (Service: `auth_gateway`, Wave `1`)
- **Approval Status:** `PENDING_HUMAN_APPROVAL` (Approver: `pending`)
- **Applied to Isolated Staging Copy:** `False` (`not staged yet`)
- **Backup Copy Path:** `N/A`
- **Remediation Actions:**
  - Migrate OAuth/JWT token signing from `RS256` to `ML-DSA-65-HYBRID` (NIST FIPS 204 digital signature).
  - Update JWT signing key type from `RSA-2048` to `ML-DSA-65` (FIPS 204).
  - Upgrade certificate thumbprint digest from `SHA-1` to `SHA3-256` (FIPS 202).
  - Upgrade TLS listener key exchange from `ECDHE-P256` to hybrid `X25519MLKEM768` (NIST FIPS 203 ML-KEM).

```diff
--- a/demo_bank_app/configs/auth_gateway_tls.yaml
+++ b/staged/demo_bank_app/configs/auth_gateway_tls.yaml
@@ -8,10 +8,10 @@
 depends_on: []
 
 oauth_jwt:
-  signing_algorithm: RS256
-  key_type: RSA-2048
-  thumbprint_digest: hashlib.sha1
+  signing_algorithm: ML-DSA-65-HYBRID
+  key_type: ML-DSA-65
+  thumbprint_digest: hashlib.sha3_256
 
 tls_listener:
   protocol_min: TLSv1.2
-  key_exchange_curve: ECDHE-P256
+  key_exchange_curve: X25519MLKEM768
```

### Proposal `RUN-20261029T180929Z-P02` — `demo_bank_app/configs/card_vault_crypto.yaml` (Service: `card_vault`, Wave `2`)
- **Approval Status:** `PENDING_HUMAN_APPROVAL` (Approver: `pending`)
- **Applied to Isolated Staging Copy:** `False` (`not staged yet`)
- **Backup Copy Path:** `N/A`
- **Remediation Actions:**
  - Migrate vault DEK key wrapping from `RSA_OAEP` to `ML-KEM-768-HYBRID-KW` (NIST FIPS 203 key encapsulation — NOT ML-DSA).
  - Migrate vault PIN block cipher from `3DES` to `AES-256-GCM` (NIST SP 800-38D).

```diff
--- a/demo_bank_app/configs/card_vault_crypto.yaml
+++ b/staged/demo_bank_app/configs/card_vault_crypto.yaml
@@ -10,9 +10,9 @@
   - auth_gateway
 
 kms_envelope:
-  dek_wrapping_algorithm: RSA_OAEP
+  dek_wrapping_algorithm: ML-KEM-768-HYBRID-KW
   dek_wrapping_key_bits: 2048
-  pin_block_cipher: 3DES
+  pin_block_cipher: AES-256-GCM
 
 tls_client:
   # Note: Presence of X25519MLKEM768 here does NOT make card_vault PQC-safe while RSA_OAEP and 3DES remain unmigrated.
```

### Proposal `RUN-20261029T180929Z-P03` — `demo_bank_app/configs/interbank_tls_nginx.conf` (Service: `interbank_tls`, Wave `0`)
- **Approval Status:** `PENDING_HUMAN_APPROVAL` (Approver: `pending`)
- **Applied to Isolated Staging Copy:** `False` (`not staged yet`)
- **Backup Copy Path:** `N/A`
- **Remediation Actions:**
  - Upgrade Nginx TLS key establishment (`ssl_ecdh_curve`) to hybrid `X25519MLKEM768:X25519:prime256v1` (NIST FIPS 203 ML-KEM).
  - Remove legacy `DES-CBC3-SHA` (3DES) from `ssl_ciphers` (NIST SP 800-131A / SP 800-38D).
  - Transition mTLS peer authentication certificate to dual-mode `ML-DSA-65` (NIST FIPS 204).

```diff
--- a/demo_bank_app/configs/interbank_tls_nginx.conf
+++ b/staged/demo_bank_app/configs/interbank_tls_nginx.conf
@@ -8,12 +8,12 @@
     server_name interbank-mtls.demo-bank.internal;
 
     ssl_protocols TLSv1.2 TLSv1.3;
-    ssl_ecdh_curve prime256v1;
-    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA384:DES-CBC3-SHA;
+    ssl_ecdh_curve X25519MLKEM768:X25519:prime256v1;
+    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA384;
     ssl_prefer_server_ciphers on;
 
     # RSA-2048 certificate authentication (digital_signature role -> FIPS 204 ML-DSA)
-    ssl_certificate /etc/nginx/certs/interbank_rsa2048_cert.pem;
+    ssl_certificate /etc/nginx/certs/interbank_mldsa65_dual_cert.pem;
     ssl_certificate_key /etc/nginx/certs/interbank_rsa2048.key;
     ssl_verify_client on;
 
```

### Proposal `RUN-20261029T180929Z-P04` — `demo_bank_app/configs/payment_signing_service.py` (Service: `payment_signing`, Wave `1`)
- **Approval Status:** `PENDING_HUMAN_APPROVAL` (Approver: `pending`)
- **Applied to Isolated Staging Copy:** `False` (`not staged yet`)
- **Backup Copy Path:** `N/A`
- **Remediation Actions:**
  - Migrate primary payment instruction signature from `ECDSA_P256` to `ML-DSA-65_HYBRID` (NIST FIPS 204).
  - Migrate XMLDSig fallback signature from `RS256` to `ML-DSA-65_XMLDSIG_HYBRID` (NIST FIPS 204).

```diff
--- a/demo_bank_app/configs/payment_signing_service.py
+++ b/staged/demo_bank_app/configs/payment_signing_service.py
@@ -5,5 +5,5 @@
 DEPENDS_ON = ["auth_gateway", "ledger_audit"]
 
 # Digital signature primitives -> must migrate to ML-DSA-65 (FIPS 204), NEVER ML-KEM
-PRIMARY_SIGNATURE_SCHEME = "ECDSA_P256"
-FALLBACK_XMLDSIG_SCHEME = "RS256"
+PRIMARY_SIGNATURE_SCHEME = "ML-DSA-65_HYBRID"
+FALLBACK_XMLDSIG_SCHEME = "ML-DSA-65_XMLDSIG_HYBRID"
```

## 4. Verification Gates & Rollback Readiness

| Wave | Service ID | KAT Gate | Hybrid Handshake Gate | Latency SLO Gate | Overall Verdict | Rollback Snapshot & Policy Note |
|---:|---|---|---|---|---|---|
| 0 | `interbank_tls` | `True` | `True` | `True` | **PASS** | `SNAP-W0-01` — Classical RSA-2048/ECDSA-P256 fallback permitted temporarily under dual-mode transition policy. |
| 0 | `ledger_audit` | `True` | `True` | `True` | **PASS** | `SNAP-W0-02` — POLICY WARNING: Reverting to SHA-1 or 3DES violates NIST SP 800-131A; fallback must use classical SHA-256/AES-256-GCM baseline instead of weak legacy cipher. |
| 1 | `auth_gateway` | `True` | `True` | `True` | **PASS** | `SNAP-W1-03` — POLICY WARNING: Reverting to SHA-1 or 3DES violates NIST SP 800-131A; fallback must use classical SHA-256/AES-256-GCM baseline instead of weak legacy cipher. |
| 1 | `payment_signing` | `True` | `True` | `True` | **PASS** | `SNAP-W1-04` — Classical RSA-2048/ECDSA-P256 fallback permitted temporarily under dual-mode transition policy. |
| 2 | `card_vault` | `True` | `True` | `True` | **PASS** | `SNAP-W2-05` — POLICY WARNING: Reverting to SHA-1 or 3DES violates NIST SP 800-131A; fallback must use classical SHA-256/AES-256-GCM baseline instead of weak legacy cipher. |
| 2 | `settlement_batch` | `True` | `True` | `True` | **PASS** | `SNAP-W2-06` — POLICY WARNING: Reverting to SHA-1 or 3DES violates NIST SP 800-131A; fallback must use classical SHA-256/AES-256-GCM baseline instead of weak legacy cipher. |

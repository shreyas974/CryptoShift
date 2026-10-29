# Real banking PQC data — use this as the real-world dataset

The source-filtered dataset at [`data/real/bank_tls_pqc_observations.csv`](../data/real/bank_tls_pqc_observations.csv) contains original public TLS 1.3 probe observations tagged `banking` from one run, with one record per anonymized target ID. The source record is the [PQ Readiness Index](https://github.com/xuxu298/PQReadinessIndex), which licenses data under CC BY 4.0. Inspect [`data/real/README.md`](../data/real/README.md) before making claims.

The single-run banking filter has 64 unique target IDs: 49 `PQ-SAFE`, 3 `CLASSICAL`, 12 `ERROR`. Errors are unclassified outcomes, not classical/PQC-negative labels. The index’s published fixed comparison cohort uses 50 banking hosts; keep that separate from these 64 single-run records. Public TLS observations do not reveal the bank’s internal software or overall readiness.

Do not combine this data with synthetic fixtures or cryptographic-misuse benchmark labels. Synthetic fixture scores in the remaining legacy sections are demo-only and are not real-bank metrics. For the product, use these observations only as real public-edge context; separate source-code scanner precision/recall and migration-plan verification still need their own real, ground-truthed banking data, which this public dataset does not provide.

---
# Dataset and Evaluation Guide

## 1. Dataset Separation & Provenance Policy

1. **Controlled Synthetic Fixtures (`data/fixtures/synthetic/`):**
   - Visibly separated into three synthetic mini-projects (`project_alpha_auth`, `project_beta_tls`, `project_gamma_noncrypto`) with reviewed ground-truth labels in [`data/labels/synthetic_fixture_labels.json`](../data/labels/synthetic_fixture_labels.json).
   - Designed to verify context-aware rule mapping (`ML-KEM` for `RSA_OAEP`/`ECDHE` key establishment vs. `ML-DSA` for `RS256`/`ECDSA` digital signatures) and to expose static-analysis edge cases (dynamic reflection `getattr` false negatives and inactive configuration false positives).
   - **Never call synthetic fixtures real-world banking data.**
2. **Public Open-Source Repository References (`data/labels/public_repo_references.json`):**
   - Records public, license-compatible upstream repositories (`pyca/cryptography`, `open-quantum-safe/liboqs-python`, `tlsfuzzer/tlslite-ng`) with exact URLs, pinned commit SHAs, licenses, file scopes, and reproducible `git clone` commands.
   - Raw third-party source trees are not committed into this repository.

---

## 2. Unit of Analysis, Split Strategy, and Verified Metrics

- **Unit of Analysis:** One labelled file-level cryptographic operation instance (`instance_id`), requiring both `legacy_algorithm` and `operation_purpose` to match the ground-truth label for a True Positive (`TP`).
- **Repository-Level Split:**
  - `calibration`: `project_alpha_auth` (3 instances: `SYN-001` to `SYN-003`)
  - `held_out_test`: `project_beta_tls` (5 instances: `SYN-004` to `SYN-008`) and `project_gamma_noncrypto` (3 instances: `SYN-009` to `SYN-011`)
- **Verified Counts on the Synthetic Fixture Suite (`python cryptoshift_cli.py evaluate`):**
  - **True Positives (`TP`):** `7`
  - **False Positives (`FP`):** `1` (`SYN-011`: inactive config flag `LEGACY_RSA_2048_CONFIG: false` flagged for human review)
  - **False Negatives (`FN`):** `1` (`SYN-008`: dynamic string concatenation `getattr(hashlib, "sh" + "a1")` missed by static regex)
  - **True Negatives (`TN`):** `2` (`SYN-009` non-crypto UI helper decoy; `SYN-010` already migrated PQC service)
  - **Precision (`TP / (TP + FP)`):** **`0.8750`** (`7 / 8`)
  - **Recall (`TP / (TP + FN)`):** **`0.8750`** (`7 / 8`)

See the full generated breakdown in [`reports/evaluation/evaluation_report.md`](../reports/evaluation/evaluation_report.md).


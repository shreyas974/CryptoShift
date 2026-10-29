# CryptoShift Data

## Current real dataset for banking PQC

The current real-world dataset is [`data/real/bank_tls_pqc_observations.csv`](real/bank_tls_pqc_observations.csv), with provenance and interpretation in [`data/real/README.md`](real/README.md) and [`data/real/dataset_manifest.json`](real/dataset_manifest.json). It is a one-run, source-filtered set of public TLS 1.3 observations tagged `banking`; the source IDs are anonymized. It is not internal bank application data. No synthetic rows or unrelated crypto-misuse labels are mixed into this dataset.

The repository still has older synthetic demo fixtures in `data/fixtures/synthetic/`; they are excluded from `data/real/` and must not be cited as real banking evidence. The real dataset currently covers public-edge TLS key establishment only. It does not satisfy the separate need for internal banking code/config inventory or migration-plan ground truth.
# CryptoShift Dataset, Provenance, and Evaluation Guide (`data/`)

This directory separates **reviewed label metadata**, **public open-source repository provenance**, and **visibly synthetic fixtures** in accordance with the CryptoShift evaluation policy.

---

## 1. Directory Layout

```text
data/
  README.md                           # Provenance, split rules, and acquisition instructions
  labels/
    schema.json                       # JSON schema for reviewed cryptographic usage labels
    synthetic_fixture_labels.json     # Reviewed labels for the local synthetic fixture suite
    public_repo_references.json       # Pinned URLs, commits, and licenses for external OSS evaluation
  fixtures/
    synthetic/                        # Visibly synthetic positive, negative, and edge-case fixtures
      project_alpha_auth/             # Split: calibration (3 files)
      project_beta_tls/               # Split: held_out_test (5 files, including 1 dynamic-dispatch FN)
      project_gamma_noncrypto/        # Split: held_out_test (3 files, including 2 TN and 1 ambiguous FP)
```

---

## 2. Dataset Policy & Separation Rules

1. **Synthetic Fixtures Are Not Real-World Data:**
   - All files under `data/fixtures/synthetic/` are controlled synthetic fixtures created to verify CryptoShift's context-aware rules (`ML-KEM` key establishment vs. `ML-DSA` digital signatures) and to demonstrate known static-analysis failure modes (dynamic `getattr` reflection and inactive config keys).
   - Synthetic fixture precision/recall scores (`reports/evaluation/evaluation_report.md`) must **never** be presented as real-world banking estate discovery metrics.
2. **No Unlicensed Third-Party Code Redistribution:**
   - Instead of checking in third-party source trees, `data/labels/public_repo_references.json` records public, license-compatible open-source repositories with pinned commit SHAs, licenses (`Apache-2.0`, `MIT`, `BSD-3-Clause`), collection dates, and exact `git clone` + `git checkout` commands for reproducible local evaluation.
3. **Unit of Analysis & Repository-Level Splits:**
   - **Unit of Analysis:** One labelled file-level cryptographic operation instance (`instance_id`), evaluated on whether the scanner detects a migration-relevant primitive **and** classifies its `operation_purpose` (`key_establishment`, `digital_signature`, `symmetric_encryption`, or `message_digest`).
   - **Split Strategy:** Repository-level split (`project_alpha_auth` in `calibration`; `project_beta_tls` and `project_gamma_noncrypto` in `held_out_test`) to prevent same-project template leakage.


## Real public-source corpus

See [data/public/README.md](public/README.md) for the pinned, license-documented real source snapshots, retrieval/scanning commands, annotation protocol, and limitations. Raw source snapshots and local candidate reports are Git-ignored; only provenance and reviewed annotations should be considered for check-in.

## Real, labeled public-source reference data

The project now includes a normalized companion CSV of the published LICMA Python study findings at `data/public/processed/licma_real_misuse_findings.csv`. It preserves the study's `critical` versus `warning` distinction and provides repository/path metadata without bundling upstream source trees. See `data/public/README.md` and `data/labels/real_dataset_sources.json` for attribution, license, source checksums, and limits. This dataset labels cryptographic API misuse, not PQC migration relevance; keep it out of PQC migration precision/recall until code context is reviewed and separately labeled.



# Architecture overview (beginner-readable)

CryptoShift is a pipeline. Each stage below names the **real module** that implements it today and an honest
status. Older, more detailed notes: [`docs/architecture.md`](../architecture.md),
[`docs/migration-and-verification.md`](../migration-and-verification.md).

```text
 code / configs / manifests / certs
            │
   (1) Discover ──► (2) Inventory ──► (3) Risk & tasks ──► (4) Schedule waves
                                                               │
          (7) Report ◄── (6) Rollback ◄── (5) Verify gates ◄───┘
```

| # | Stage | What it does (plain words) | Module(s) | Status |
|---|---|---|---|---|
| 1a | Discover — Python | Reads Python files as syntax trees and finds real calls to crypto libraries (`cryptography`, `hashlib`, `ssl`, PyCryptodome, JWT libs). Comments, strings and look-alike names are ignored. | `src/cryptoshift/inventory/python_ast.py` | VERIFIED (unit tests + public-code labels; small sample) |
| 1b | Discover — TLS configs | Reads nginx/Apache TLS directives and `openssl.cnf`; explains which key exchange, signatures, ciphers and protocol versions they enable. | `src/cryptoshift/inventory/tls_config.py` | VERIFIED (same caveat) |
| 1c | Discover — dependencies | Flags crypto-capable libraries in `requirements*.txt`, `package.json`, `pom.xml` (presence only, purpose unknown). | `src/cryptoshift/inventory/manifests.py` | VERIFIED (unit tests; 3 labelled lines) |
| 1d | Discover — certificates | Reports key algorithm, key size, signature hash and expiry of certificate files — never their contents. | `src/cryptoshift/inventory/certificates.py` | VERIFIED (unit test with a generated cert) |
| 1e | Discover — legacy scanner | Original regex/YAML/nginx scanner and the synthetic service descriptor (13 findings). | `src/cryptoshift/scanner.py`, `rules.py` | PARTIAL (descriptor is SYNTHETIC) |
| 2 | Inventory | Turns findings into a CBOM-like JSON + Markdown (not CycloneDX). | `src/cryptoshift/inventory/report.py`, CLI `inventory` | VERIFIED |
| 3 | Risk & tasks | Builds 6 migration tasks with a heuristic risk score. **Tasks come from the synthetic descriptor, not from scanner findings.** | `src/cryptoshift/scoring.py` | MOCKED inputs; score provisional/unvalidated |
| 4 | Schedule waves | Dependency-aware wave scheduler (deterministic baseline); optional QpiAI Opt / QAOA experiments. | `src/cryptoshift/optimization/` | Deterministic baseline VERIFIED by unit test (objective 248.105); QpiAI results REPORTED, not re-verified |
| 5 | Verify gates | KAT / handshake / latency gates per wave. Today these are boolean flags, not real checks. | `src/cryptoshift/verification.py` | MOCKED |
| 5b | Protocol trace | Before/after handshake size comparison (544 B vs 7661 B) from specification byte sizes, not a capture. | `src/cryptoshift/protocol_demo.py` | MOCKED / ANALYTICAL |
| 6 | Rollback | Rollback records per gate; staged-copy restore in the MVP slice. | `src/cryptoshift/rollback.py`, `mvp_slice.py` | PARTIAL |
| 7 | Report / UI | JSON/Markdown reports, Streamlit UI. | `src/cryptoshift/reporting.py`, `ui/app.py` | PARTIAL (Member 4) |
| D | Data | Read-only dataset loaders and `data-summary`. | `src/cryptoshift/datasets.py`, `data_summary.py` | VERIFIED |

## Mapping rule (all stages)

- Key establishment (RSA key transport, ECDH/ECDHE, DH) ⇒ candidate **ML-KEM (FIPS 203)**, e.g. hybrid
  X25519MLKEM768 in TLS 1.3.
- Signatures (RSA/ECDSA/EdDSA/DSA) ⇒ candidate **ML-DSA (FIPS 204)** or **SLH-DSA (FIPS 205)**.
- Purpose unknown ⇒ **HOLD** for human review (`rules.resolve_contextual_pqc_rule`).
- Candidates also depend on protocol, library support and peer compatibility; they are never applied automatically.

## Trust boundaries

- `.env` / `qcloud.env` are never opened by the inventory scanner (skipped by name). The existing
  `resolve_dataset_paths()` and QpiAI helpers *do* load them into the process environment when present
  (pre-existing behaviour; values are never printed).
- External datasets and fetched public repositories are read-only; derived output goes to git-ignored `scratch/`.

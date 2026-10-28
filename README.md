# CryptoShift

**Quant-A-Maze 3.0 | PQC-01: Verification-Gated Cryptographic Migration Across Banking Applications**

CryptoShift is a Python-first prototype for evidence-backed discovery and planning of post-quantum cryptography (PQC) migration. It is intended to help a team find cryptographic clues in a bounded code/configuration scope, classify the operation with visible uncertainty, sequence dependent migration tasks, and record verification and rollback evidence.

This is a hackathon prototype, not a bank-wide scanner, cryptographic validation, or production migration system. Read [the project documentation](docs/README.md) before interpreting demo output. Treat every result as scoped to its pinned input and test setup.

## What the project is designed to demonstrate

- Inventory findings with file/service evidence and confidence.
- Context-aware operation roles: key establishment, signature, verification, encryption, and related functions.
- Dependency-aware migration waves with a deterministic fallback planner.
- Optional QpiAI Opt local optimization and a QpiAI local-simulator experiment when configured and documented.
- Verification gates, compatibility traces, overhead measurement methods, and rollback records.
- Detection evaluation on labelled data, with precision/recall counts and scope limitations.

**Algorithm-role reminder:** ML-KEM (NIST FIPS 203) is for key establishment. ML-DSA (FIPS 204) and SLH-DSA (FIPS 205) are for signatures. A name match alone does not justify an algorithm mapping.

## Project structure

```text
cryptoshift/       Python application modules and CLI
src/cryptoshift/   source-layout optimization package (review for duplicate implementations)
demo_bank_app/     explicitly synthetic banking fixture
docs/              setup, architecture, migration, evaluation, and demo guidance
reports/           non-sensitive run evidence; verify claims against actual runs
```

The current package layout is preserved pending a code-aware migration; do not move modules or retain duplicate implementations without updating package configuration and entry points.

## Setup

Use Python 3.12 in a project virtual environment. Install the core package using the project's documented instructions. QpiAI packages are optional; the deterministic fallback should remain available without them. See [QpiAI local setup](docs/qpiai-login.md).

Never commit `.env`, `qcloud.env`, virtual environments, private keys, access tokens, customer data, or raw datasets without redistribution permission. The templates contain placeholders only. API credentials previously exposed in chat must be revoked and replaced.

## Evidence and demo

See [the demo runbook](docs/demo-runbook.md), [dataset and evaluation guidance](docs/dataset-and-evaluation.md), and [migration/verification guide](docs/migration-and-verification.md). The conversation log reports historical package versions and run results; verify those values from the current environment and sanitized report before presenting them as current results.

## Standards and references

- [NIST FIPS 203: ML-KEM](https://csrc.nist.gov/pubs/fips/203/final)
- [NIST FIPS 204: ML-DSA](https://csrc.nist.gov/pubs/fips/204/final)
- [NIST FIPS 205: SLH-DSA](https://csrc.nist.gov/pubs/fips/205/final)
- [NIST migration to PQC](https://www.nccoe.nist.gov/applied-cryptography/migration-to-pqc)

## License

The package metadata currently names MIT. Confirm that the project owner intends to release the repository under that license before adding a license file or publishing publicly.
# CryptoShift

**Quant-A-Maze 3.0 | PQC-01: Verification-Gated Cryptographic Migration Across Banking Applications**

CryptoShift is a beginner-friendly, Python-first prototype for evidence-backed discovery, dependency-aware wave scheduling, and verification-gated planning of post-quantum cryptography (PQC) migration across banking applications.

> **Scope & Honesty Notice:** CryptoShift is a hackathon migration-planning and verification prototype, not a production bank-wide scanner or cryptographic certification tool. All banking services in [`demo_bank_app/`](demo_bank_app/) and [`data/fixtures/synthetic/`](data/fixtures/synthetic/) are synthetic fixtures, protocol envelope traces are explicitly labelled as mocked/modelled traces, and all quantum circuit runs execute on the local classical statevector simulator (`QpiAI-QSV-Local`).

> **Claim status (Stage 0):** the numbers below are labelled in [`docs/stage0/claims-register.md`](docs/stage0/claims-register.md), which takes precedence over this page. In short: "13 findings / 6 services" come from a *synthetic* service descriptor; 0.875/0.875 is a *synthetic smoke test* (11 fixtures), not a benchmark; 544 B vs 7661 B is *mocked/analytical*; the 6 verification gates are *mocked* booleans; 248.105 is verified only for the deterministic baseline scheduler on synthetic tasks; the QAOA energy −13.07 is *reported, not re-verified* in this checkout. Stage 0/1 docs: [`docs/stage0/`](docs/stage0/), datasets: [`docs/data/DATASETS.md`](docs/data/DATASETS.md), new commands: `cryptoshift_cli.py data-summary` and `cryptoshift_cli.py inventory`.

---

## Key Capabilities

1. **Context-Aware CBOM Discovery ([`src/cryptoshift/scanner.py`](src/cryptoshift/scanner.py), [`src/cryptoshift/rules.py`](src/cryptoshift/rules.py)):**
   - Identifies cryptographic clues in source, configuration, and service descriptors with file/line evidence, confidence, owner, protocol, and human-review status.
   - Enforces strict NIST PQC algorithm role separation:
     - **ML-KEM (NIST FIPS 203)** for **key establishment / key encapsulation** (e.g., `ECDHE-P256`, `DH-2048`, and `RSA-2048` OAEP DEK wrapping in `card_vault`).
     - **ML-DSA (NIST FIPS 204)** / **SLH-DSA (NIST FIPS 205)** for **digital signatures** (e.g., `RSA-2048` RS256/XMLDSig and `ECDSA-P256` in `auth_gateway`, `ledger_audit`, and `payment_signing`).
     - Holds automatic mapping for human review when `operation_purpose` is `unknown`.
2. **Dependency-Aware Migration Wave Scheduling ([`src/cryptoshift/optimization/`](src/cryptoshift/optimization/)):**
   - **Deterministic Fallback Scheduler ([`fallback_scheduler.py`](src/cryptoshift/optimization/fallback_scheduler.py)):** Exact constrained combinatorial scheduler enforcing upstream service dependencies, maintenance window budgets (`<= 85` min/wave), wave capacity (`<= 2` services/wave), and Wave-0 verification readiness.
   - **QpiAI Opt Integration ([`qpiai_opt_adapter.py`](src/cryptoshift/optimization/qpiai_opt_adapter.py)):** Formulates the 18-variable binary MILP (`Model("cryptoshift_wave_schedule")`), verifies model classification (`classify(model) == "MILP"`), inspection (`inspect(model)`), and baseline feasibility (`feasibility(model, ...)`) offline, and supports authenticated local solving (`solve(model, mode="local", client=client)`).
   - **QpiAI Quantum / QCloud Local Simulator Experiment ([`qcloud_experiment.py`](src/cryptoshift/optimization/qcloud_experiment.py)):** Compiles a 4-qubit Wave-0 priority selection QUBO (`QUBOProblem.from_model`), builds the `QAOA(reps=1)` circuit (`depth=8`, `size=18`), and simulates it locally on `QpiAI-QSV-Local` (`1024` shots), selecting `['interbank_tls', 'ledger_audit']` (energy `-13.07`), matching Wave 0 of the exact MILP and deterministic baseline (`248.105`).
3. **Verification Gates, Mocked Protocol Traces & Rollback Records ([`verification.py`](src/cryptoshift/verification.py), [`protocol_demo.py`](src/cryptoshift/protocol_demo.py), [`rollback.py`](src/cryptoshift/rollback.py)):**
   - Evaluates pre-promotion KAT, peer compatibility matrix, and latency gates per wave.
   - Records an explicitly labelled mocked protocol envelope trace (`544B` legacy vs. `7661B` hybrid `X25519MLKEM768` + `ML-DSA-65` envelope) and rollback snapshots with policy warnings against reverting to deprecated `SHA-1` or `3DES`.
4. **Labelled Dataset Evaluation ([`data/`](data/), [`reports/evaluation/`](reports/evaluation/)):**
   - Evaluates context-aware detection across 11 reviewed synthetic fixture instances split by repository (`calibration` vs. `held_out_test`), reporting `TP=7, FP=1, FN=1, TN=2`, `Precision=0.8750`, and `Recall=0.8750`, alongside pinned public open-source repository references in [`data/labels/public_repo_references.json`](data/labels/public_repo_references.json).

---

## Repository Structure

```text
CryptoShift/
  README.md
  CONTRIBUTING.md
  pyproject.toml
  requirements.txt
  cryptoshift_cli.py
  .gitignore
  .env.example
  qcloud.env.example
  src/cryptoshift/
    __init__.py
    cli.py
    scanner.py
    rules.py
    models.py
    dependencies.py
    scoring.py
    proposals.py
    verification.py
    protocol_demo.py
    rollback.py
    metrics.py
    reporting.py
    optimization/
      __init__.py
      auth_check.py
      fallback_scheduler.py
      qpiai_opt_adapter.py
      qcloud_experiment.py
  demo_bank_app/
    README_SYNTHETIC.md
    services.py
  data/
    README.md
    labels/
      schema.json
      synthetic_fixture_labels.json
      public_repo_references.json
    fixtures/synthetic/
      project_alpha_auth/
      project_beta_tls/
      project_gamma_noncrypto/
  docs/
    README.md
    architecture.md
    pqc-basics-and-solution.md
    dataset-and-evaluation.md
    migration-and-verification.md
    qpiai-login.md
    qpiai-setup.md
    demo-runbook.md
    setup/
      project-structure.md
    team/
      CryptoShift_Team_Roles_36h_and_Technical_Stack.docx
  tests/
    test_cryptoshift.py
  scripts/
    verify_repo.py
  reports/
    qpiai/
      qpiai_evidence_report.json
      qpiai_evidence_report.md
    evaluation/
      evaluation_report.json
      evaluation_report.md
  assets/
    CryptoShift_Mentor_Deck.pptx
    CryptoShift_PQC_Concept_and_Solution_Guide.docx
```

---

## Quick Start (Windows PowerShell)

```powershell
# 1. Install package in editable mode inside the project virtual environment (.venv)
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .

# 2. Run safe offline credential & local simulator smoke check
.\.venv\Scripts\python.exe cryptoshift_cli.py check-auth

# 3. Run full discovery, wave scheduling, verification gates, and dataset evaluation
.\.venv\Scripts\python.exe cryptoshift_cli.py demo

# 4. Run unit tests and repository secret/hygiene check
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/verify_repo.py
```

---

## Documentation & Project Deliverables

- [Documentation Index](docs/README.md)
- [Project Structure & Organization Guide](docs/setup/project-structure.md)
- [Shared Team QpiAI SDK & Local Workspace Setup](docs/setup/qpiai-shared-setup.md)
- [PQC Basics & Solution Overview](docs/pqc-basics-and-solution.md) ([Word Guide](assets/CryptoShift_PQC_Concept_and_Solution_Guide.docx) | [Mentor Deck](assets/CryptoShift_Mentor_Deck.pptx) | [Team Roles & 36h Stack](docs/team/CryptoShift_Team_Roles_36h_and_Technical_Stack.docx))
- [Architecture & Trust Boundaries](docs/architecture.md)
- [Dataset & Evaluation Guide](docs/dataset-and-evaluation.md) ([Verified Evaluation Report](reports/evaluation/evaluation_report.md))
- [Migration Verification & Rollback Guide](docs/migration-and-verification.md)
- [QpiAI Login & Local `.env` Setup](docs/qpiai-login.md)
- [QpiAI Scheduling Formulation & QUBO Experiment](docs/qpiai-setup.md) ([Verified QpiAI Evidence Report](reports/qpiai/qpiai_evidence_report.md))
- [Demo Runbook](docs/demo-runbook.md)

---

## License Status

No `LICENSE` file has been selected yet pending explicit owner confirmation of the intended license.

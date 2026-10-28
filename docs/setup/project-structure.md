# CryptoShift — Project Folder Structure Guide

> **Scope Note:** This document describes **folder placement and file organization only**. It does **not** define team roles, assign people to tasks, or change application behavior.

---

## 1. Current Project Directory Tree

```text
CryptoShift/
├── README.md                                   # Project overview, quick start, and honesty notices
├── CONTRIBUTING.md                             # Workflow, secret hygiene, and verification standards
├── pyproject.toml                              # Package build configuration (`where = ["src"]`) & CLI entry point
├── requirements.txt                            # Optional QpiAI SDK dependencies for `.venv` setup
├── cryptoshift_cli.py                          # Working root CLI entry point delegating to `src/cryptoshift/cli.py`
├── .gitignore                                  # Protects `.env`, `qcloud.env`, `.venv/`, `.backup_*/`, and caches
├── .env.example                                # Blank placeholder template for `QPIAI_OPT_API_KEY` & `QPIAI_QCLOUD_API_KEY`
├── qcloud.env.example                          # Blank placeholder template for standalone `qpiai-quantum`
├── .env                                        # Local-only credentials (git-ignored; never read, stage, or commit)
├── .venv/                                      # Local-only Python virtual environment (git-ignored; preserve locally)
├── .backup_20261028/                           # Local-only pre-restructure backup (git-ignored; preserve unchanged)
├── src/
│   └── cryptoshift/                            # Canonical Python package
│       ├── __init__.py
│       ├── cli.py                              # CLI implementation (`check-auth`, `init-env`, `schedule`, `evaluate`, `demo`)
│       ├── models.py                           # Dataclasses for CBOM findings, tasks, schedules, gates, and rollbacks
│       ├── rules.py                            # Context-aware NIST PQC mapping rules (FIPS 203 ML-KEM vs. FIPS 204 ML-DSA)
│       ├── scanner.py                          # Current source, config, and synthetic service scanner module
│       ├── dependencies.py                     # Service dependency DAG construction & topological validation
│       ├── scoring.py                          # Explainable urgency & HNDL risk scoring
│       ├── proposals.py                        # Hybrid PQC migration proposal generator
│       ├── verification.py                     # Current pre-promotion KAT, peer compatibility, and latency gate module
│       ├── protocol_demo.py                    # Explicitly labelled mocked protocol trace & byte-overhead calculator
│       ├── rollback.py                         # Pre-wave snapshot & rollback records with policy warnings
│       ├── metrics.py                          # Migration readiness & labelled dataset evaluation metrics
│       ├── reporting.py                        # Current non-sensitive JSON/Markdown report writer module
│       ├── scanner/                            # Prepared subpackage directory for future scanner extensions
│       ├── inventory/                          # Prepared subpackage directory for future CBOM/inventory modules
│       ├── planning/                           # Prepared subpackage directory for future wave-planning modules
│       ├── optimization/                       # Active QpiAI Opt, QpiAI QCloud, and deterministic fallback modules
│       │   ├── __init__.py
│       │   ├── auth_check.py
│       │   ├── fallback_scheduler.py
│       │   ├── qpiai_opt_adapter.py
│       │   └── qcloud_experiment.py
│       ├── verification/                       # Prepared subpackage directory for future verification gate modules
│       ├── reporting/                          # Prepared subpackage directory for future report formatters
│       └── ui/                                 # Prepared subpackage directory for future dashboard/UI components
├── demo_bank_app/                              # Explicitly synthetic 6-service banking demo fixture
│   ├── README_SYNTHETIC.md
│   └── services.py
├── tests/                                      # Automated tests and test-only fixtures
│   ├── test_cryptoshift.py                     # Current offline unit & smoke test suite
│   ├── unit/                                   # Prepared directory for future unit test modules
│   ├── integration/                            # Prepared directory for future end-to-end integration tests
│   └── fixtures/                               # Prepared directory for test-specific helper fixtures
├── data/                                       # Dataset provenance, reviewed labels, synthetic fixtures, and public data
│   ├── README.md
│   ├── fixtures/
│   │   └── synthetic/                          # Explicitly synthetic evaluation fixtures (`project_alpha_auth`, etc.)
│   ├── labels/                                 # Reviewed ground-truth labels and public repo reference metadata
│   │   ├── schema.json
│   │   ├── synthetic_fixture_labels.json
│   │   └── public_repo_references.json
│   └── public/                                 # Local workspace for license-compatible public evaluation data
│       ├── raw/                                # Unmodified public source/config inputs (do not commit unlicensed trees)
│       └── processed/                          # Derived/normalized public dataset artifacts
├── docs/                                       # Project documentation
│   ├── README.md                               # Documentation index
│   ├── architecture.md                         # Current architecture and workflow overview
│   ├── pqc-basics-and-solution.md              # NIST FIPS 203/204/205 role overview and links to `assets/`
│   ├── dataset-and-evaluation.md               # Dataset policy and verified synthetic fixture metrics
│   ├── migration-and-verification.md           # Verification gate, mocked trace, and rollback guide
│   ├── qpiai-login.md                          # Beginner-friendly QpiAI Opt & QCloud `.env` setup guide
│   ├── qpiai-setup.md                          # MILP wave scheduling and 4-qubit Wave-0 QUBO formulation
│   ├── demo-runbook.md                         # Reproducible offline CLI verification commands
│   ├── architecture/                           # Prepared folder for detailed architecture specs & sequence notes
│   ├── datasets/                               # Prepared folder for expanded dataset schemas and provenance notes
│   ├── decisions/                              # Prepared folder for Architecture Decision Records (ADRs)
│   ├── demo/                                   # Prepared folder for demo scripts and walkthrough notes
│   ├── setup/
│   │   └── project-structure.md                # This folder placement and organization guide
│   └── team/
│       └── CryptoShift_Team_Roles_36h_and_Technical_Stack.docx
├── experiments/                                # Isolated experimental sandboxes
│   └── bloq/                                   # Bloq quantum/optimization experiments
│       ├── notebooks/                          # Bloq experimental notebooks
│       └── runs/                               # Sanitized, non-sensitive Bloq run outputs
├── reports/                                    # Reproducible, secret-redacted evidence and evaluation outputs
│   ├── evaluation/                             # Detector evaluation outputs (`evaluation_report.json`, `.md`)
│   ├── qpiai/                                  # QpiAI Opt/QCloud & fallback scheduler evidence (`qpiai_evidence_report.json`, `.md`)
│   └── runs/                                   # General CLI/pipeline execution logs and run summaries
├── scripts/                                    # Reproducible helper and repository maintenance scripts
│   └── verify_repo.py                          # Secret, forbidden-file, and local-path hygiene scanner
└── assets/                                     # Project presentations, guides, diagrams, and screenshots
    ├── CryptoShift_Mentor_Deck.pptx
    ├── CryptoShift_PQC_Concept_and_Solution_Guide.docx
    ├── diagrams/                               # Architecture and workflow diagrams
    └── screenshots/                            # Sanitized UI/CLI demo screenshots (never include secrets)
```

---

## 2. Purpose of Each Top-Level Folder & Where New Files Belong

| Top-Level Path | Purpose & Placement Rules |
|---|---|
| `src/cryptoshift/` | Canonical Python package. Core working modules currently live directly under `src/cryptoshift/` (`cli.py`, `scanner.py`, `rules.py`, `models.py`, `dependencies.py`, `scoring.py`, `proposals.py`, `verification.py`, `protocol_demo.py`, `rollback.py`, `metrics.py`, `reporting.py`) and `src/cryptoshift/optimization/`. Future modularized components belong in `scanner/`, `inventory/`, `planning/`, `verification/`, `reporting/`, and `ui/`. **Important Python Import Note:** Do not add an `__init__.py` inside `scanner/`, `verification/`, or `reporting/` until the matching flat module (`scanner.py`, `verification.py`, `reporting.py`) is migrated into that subdirectory, otherwise the package directory will shadow the flat `.py` module. |
| `demo_bank_app/` | Self-contained, explicitly synthetic 6-service banking application fixture (`services.py`, `README_SYNTHETIC.md`). Keep in place at the root because `src/cryptoshift/scanner.py` and `src/cryptoshift/scoring.py` import `demo_bank_app.services`. |
| `tests/` | Automated test suite. `tests/test_cryptoshift.py` contains the current unit/smoke tests. New unit tests belong in `tests/unit/`, integration tests in `tests/integration/`, and test-only helper files in `tests/fixtures/`. |
| `data/` | Separates synthetic fixtures, reviewed labels, and public evaluation data (see Section 3 below). |
| `docs/` | Project documentation. Existing top-level markdown guides remain at `docs/*.md` so links in `README.md` and `docs/README.md` stay valid. New topic-specific documents belong in `docs/architecture/`, `docs/datasets/`, `docs/decisions/`, `docs/demo/`, `docs/setup/`, and `docs/team/`. |
| `experiments/bloq/` | Dedicated location for Bloq quantum circuits/notebooks (`experiments/bloq/notebooks/`) and run logs (`experiments/bloq/runs/`). **Security Rule:** Never upload CryptoShift source code, `.env` credentials, or banking data to Bloq. |
| `reports/` | Sanitized, reproducible output reports. `reports/qpiai/` stores QpiAI and fallback scheduling evidence; `reports/evaluation/` stores precision/recall evaluation reports; `reports/runs/` is for future pipeline run artifacts. |
| `scripts/` | Helper scripts for repository maintenance and verification (such as `scripts/verify_repo.py`). |
| `assets/` | Presentation decks (`CryptoShift_Mentor_Deck.pptx`), concept guides (`CryptoShift_PQC_Concept_and_Solution_Guide.docx`), architecture figures (`assets/diagrams/`), and sanitized screenshots (`assets/screenshots/`). |

---

## 3. Synthetic Data vs. Public Data Separation

1. **Synthetic Data (`demo_bank_app/` and `data/fixtures/synthetic/`):**
   - `demo_bank_app/` and `data/fixtures/synthetic/` (`project_alpha_auth/`, `project_beta_tls/`, `project_gamma_noncrypto/`) contain 100% synthetic code and configuration fixtures created for deterministic testing.
   - Synthetic fixtures must always remain visibly labelled as synthetic and must never be combined into real-world discovery denominators.
2. **Reviewed Labels (`data/labels/`):**
   - `data/labels/schema.json` and `data/labels/synthetic_fixture_labels.json` store reviewed ground-truth annotations.
   - `data/labels/public_repo_references.json` stores pinned URLs, commit SHAs, licenses, and reproducible fetch commands for public open-source repositories.
3. **Public Evaluation Data (`data/public/raw/` and `data/public/processed/`):**
   - `data/public/raw/` is reserved for locally fetched public open-source code/configuration snapshots (do not commit raw third-party trees to Git unless their license explicitly permits redistribution).
   - `data/public/processed/` is reserved for normalized/derived feature or CBOM outputs extracted from public sources.

---

## 4. Local-Only Files & Secret Hygiene

- **`.env` and `qcloud.env`:** Local-only credential files ignored by [`.gitignore`](../../.gitignore). Never read, print, copy, stage, or commit `.env` contents, and never include secret values in reports, traces, screenshots, or logs.
- **`.venv/`:** Local Python 3.12 virtual environment ignored by [`.gitignore`](../../.gitignore). All CLI and test commands run via `.\.venv\Scripts\python.exe`.
- **`.backup_20261028/`:** Local pre-restructure backup directory ignored by [`.gitignore`](../../.gitignore) and preserved unchanged.

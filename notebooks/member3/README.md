# Member 3 Notebook Workspace — Migration Planning, Verification & Rollback

**Workspace:** `CryptoShift_Member3`  
**Branch:** `feature/member-3-planning-verification`

## Purpose

This directory (`notebooks/member3/`) is dedicated to **Member 3's** interactive exploration, experimentation, and validation for:

- Dependency-aware migration wave planning (`src/cryptoshift/dependencies.py`, `src/cryptoshift/scoring.py`)
- Deterministic baseline wave scheduling (`src/cryptoshift/optimization/fallback_scheduler.py`)
- Optional QpiAI Opt / QCloud scheduling comparisons (`src/cryptoshift/optimization/qpiai_opt_adapter.py`, `src/cryptoshift/optimization/qcloud_experiment.py`)
- Post-migration cryptographic verification and compatibility gates (`src/cryptoshift/verification.py`)
- Automated rollback triggers and recovery validation (`src/cryptoshift/rollback.py`)

## Guidelines & Guardrails

1. **Deterministic Baseline Required:** The deterministic planner remains the required baseline so the application runs reliably without external credentials or cloud access.
2. **Credential Hygiene:** Never place `.env` values, QpiAI API keys, or tokens in notebook cells, outputs, command-line arguments, or screenshots. Load keys only via ignored local environment variables when explicitly needed.
3. **Scope Boundary:** Do not train a cryptographic detector AI model on the small synthetic fixture set. Any future detector training belongs to a coordinated discovery/dataset effort with suitable real labelled data.
4. **Git Staging Rule:** Stage only intended, Member 3–owned paths explicitly (`git add <path>`). Never run `git add .` or `git add -A`.


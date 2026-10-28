# Master prompt for restructuring CryptoShift and publishing to GitHub

Copy the complete prompt below into Codex or another coding agent while the **existing CryptoShift folder** is open as its project. The conversation log describes work in `C:\Users\lohig\OneDrive\Documents\CryptoShift`; inspect that exact checkout before making changes. Do not assume every claim in the conversation log is current or verified.

---

## Prompt

You are continuing my existing CryptoShift project for **Quant-A-Maze 3.0, PQC-01: Verification-Gated Cryptographic Migration Across Banking Applications**. Your task is to reorganize the existing project into a clear, complete, reproducible GitHub repository and publish it. Preserve working code and evidence. Do not start over, silently discard files, or claim unverified features or results.

### 1. Start with a safe audit

1. Work in the existing CryptoShift project folder only. Confirm the resolved project root before writing. Do not create a second project or overwrite another folder.
2. Read the project instructions and inspect the tree, Git status, installed package metadata, CLI, docs, demo, and reports. Do not read, print, copy, upload, or commit `.env`, `qcloud.env`, API keys, tokens, private certificates, customer data, or other secrets. The conversation log contains sensitive credential history; treat it as a warning, not as a source of credentials.
3. Never echo secrets to terminal output. Any secret scan must report only the affected file path and finding category, never the matched value.
4. Treat the conversation log's setup and benchmark statements as **reported history, not verified facts**. Re-run only safe, non-paid checks that are necessary to determine current status. Never submit a remote job, paid job, platform solve, QPU run, or credit-consuming request.
5. Before moving or renaming files, make a dated local backup of the project files that are in scope. Exclude `.env`, `.venv`, caches, and generated secrets from the backup. Show a concise proposed move map in the work log, then proceed without deleting the original until imports and entry points have been updated.

### 2. Project objective and technical rules

CryptoShift is a beginner-friendly Python-first **migration-planning and verification prototype**. It should:

- Discover cryptographic clues in supported source, configuration, and dependency files, with exact evidence locations.
- Record inventory/CBOM-style findings with evidence type, operation purpose, algorithm clue, confidence, owner/dependency when known, and human-review status.
- Build a dependency-aware sequence of migration waves using an explainable, configurable scoring method and a deterministic fallback scheduler.
- Optionally compare that baseline with QpiAI Opt only when the documented local solver works and the required key is already configured locally.
- Use QpiAI Quantum/QCloud only for a relevant documented local simulation, if already feasible. Do not submit a paid or remote job.
- Include working compatibility/verification evidence, protocol traces, overhead methodology, and a rollback plan. Clearly label a mocked trace as mocked.
- Evaluate detection on a documented labelled dataset with unit of analysis, repository-level splits, TP/FP/FN counts, precision, recall, and limitations. Do not call synthetic fixtures real-world data or invent benchmark results.

Use algorithm roles correctly and contextually:

- **ML-KEM (FIPS 203)** is for key establishment / key encapsulation.
- **ML-DSA (FIPS 204)** and **SLH-DSA (FIPS 205)** are for digital signatures.
- Do not map an RSA/ECC text match to a replacement without understanding its purpose, protocol, peer support, key lifecycle, and configuration.
- Do not claim that this prototype makes a bank quantum-safe, that a quantum computer can break deployed systems today, or that QpiAI use proves quantum advantage.

### 3. Target repository structure

Use this as the organized target, adapting only when the current working code requires a documented reason. Keep one canonical Python package under `src/`; do not maintain duplicated implementations under both `cryptoshift/` and `src/cryptoshift/`.

```text
CryptoShift/
  README.md
  LICENSE                         # choose only if the owner confirms the intended license; otherwise leave unselected
  CONTRIBUTING.md                 # concise team workflow
  pyproject.toml
  requirements.txt                # only if needed for simple environment setup
  .gitignore
  .env.example                    # blank placeholders only
  qcloud.env.example              # blank placeholders only, only if current SDK needs it
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
    ...
  data/
    README.md                     # provenance and acquisition instructions
    labels/                       # only reviewed labels and their schema
    fixtures/synthetic/           # synthetic data is visibly separate
  docs/
    architecture.md
    pqc-basics-and-solution.md    # link to the team guide when included
    dataset-and-evaluation.md
    migration-and-verification.md
    qpiai-login.md
    qpiai-setup.md
    demo-runbook.md
  tests/
  scripts/
  reports/
    qpiai/                        # sanitized, non-secret, reproducible outputs only
    evaluation/                   # verified results and dataset/split metadata only
  assets/
    CryptoShift_Mentor_Deck.pptx  # include only if intended for the repository
    CryptoShift_PQC_Concept_and_Solution_Guide.docx # include only if intended for the repository
```

Do not check in `.venv/`, `__pycache__/`, `.pytest_cache/`, IDE state, temporary builds, rendered QA images, logs containing local paths or secrets, or raw third-party datasets whose licenses do not permit redistribution. Prefer source URLs, pinned revisions, attribution, and reproducible download/label instructions.

### 4. Restructure safely

1. Inventory every current tracked/untracked project file and map it to the target structure. Preserve useful code, examples, docs, and reports. Do not silently drop a file; document exclusions such as caches and local environment files.
2. Move modules into `src/cryptoshift/` once, update package discovery and CLI entry points in `pyproject.toml`, and update imports and documentation. Do not preserve redundant duplicate source files just to make imports work.
3. Keep optional QpiAI modules optional. The baseline CLI must work without QpiAI packages or credentials. Credential checks may report only `key configured` / `key missing` and sanitized success/failure. Never log secrets or raw exception values.
4. Keep credential setup instructions beginner-friendly and current. `.env.example` must contain blank placeholders, never example-looking real keys. Ensure `.gitignore` protects `.env`, `.env.*` while allowing `.env.example`, `qcloud.env`, `*.key`, `.venv/`, caches, and generated reports that could contain sensitive information.
5. Include only public, license-compatible dataset references and reviewed labels. Clearly separate `data/fixtures/synthetic/` from real public-source evaluation. Record repository URL, pinned commit, license, collection date, file scope, label method, and split method.
6. Preserve the prior mentor deck and long PQC guide only if they are clean, useful project deliverables. Place them under `assets/` or `docs/`, link to them from the README, and do not include private attachments or temporary render output.

### 5. Verify before publication

Use the existing project virtual environment; do not install globally. Avoid any command that can show `.env` contents. Record exact commands and actual outcomes in `docs/demo-runbook.md` or a non-sensitive report.

Run only checks that are safe and relevant to the existing code, such as package import/CLI help, offline fallback scheduling, deterministic serialization, and local-only tests already present. Never fabricate outputs. For QpiAI checks:

- First report installed package versions from package metadata without exposing credentials.
- A missing credential is a normal `blocked` state, not a setup failure to hide.
- Opt use must be local mode only; no platform execution.
- QCloud may use a local simulator only if documented and feasible; no remote submission or paid execution.
- If authentication would call an online key-validation service, do not run it unless I specifically authorize that network check in this task. Record whether it was run.
- Report exact current status as `implemented`, `run successfully`, `fallback`, `blocked`, or `not attempted`.

Before committing, inspect the exact staged file list and confirm `.env`, `.venv`, caches, keys, tokens, private data, and unlicensed dataset copies are absent. Perform a secret scan over the staged files; output only a pass/fail summary and safe filenames, never secret matches. Check that all result claims in README/reports are backed by present evidence and match the run conditions.

### 6. GitHub repository creation and push

1. Create a **private** GitHub repository named `CryptoShift` unless I explicitly specify a different name or visibility. Do not publish it publicly by default.
2. If an existing repository with that name is found under my account, stop before overwriting or force-pushing. Report the URL and ask me how to proceed.
3. Initialize Git in the existing project folder if it is not already a repository. Create one clear initial commit after the staged-file and secret checks pass. Do not rewrite or force-push history.
4. Add the new GitHub repository as `origin`, push the default branch, and verify the remote URL and pushed commit. Never place a credential in the remote URL or Git config.
5. If GitHub authentication or repository creation is unavailable, do not claim the repository was created or pushed. Leave the local project ready, provide the exact next step, and report the blocker.

### 7. Completion report

Finish with a short, beginner-friendly report that includes:

- The final repository tree and key file locations.
- Which files moved and which local-only files were excluded.
- The repository URL and visibility, **only if actually created**.
- Commit hash and push verification, **only if actually pushed**.
- Exact verification commands and actual results.
- QpiAI status, execution mode, and whether any remote/paid operation occurred.
- Any unresolved items, including dataset or benchmark limitations.

Do not ask me to paste credentials into chat. Do not claim success until the relevant action has completed and been checked.

---

## Existing-state notes from the conversation log

The log reports a Windows project at `C:\Users\lohig\OneDrive\Documents\CryptoShift`, Python 3.12.14 in `.venv`, QpiAI Opt 0.0.9, QpiAI Quantum 0.3.0, `python-dotenv` 1.2.4, a credential check, a local simulator check, and a six-service scheduling comparison. **These are reported values, not independently confirmed by this prompt.** Re-check package metadata and sanitized reports. Treat all keys previously shared in the conversation as compromised: revoke/rotate them and never use or publish them.

The reported working project includes a CLI, scanner/rules/models/dependencies/scoring/proposals/verification/protocol demo/rollback/metrics/reporting modules; optimization and auth-check modules; a synthetic bank-app fixture; QpiAI login/setup docs; and QpiAI evidence reports. Confirm actual files and contents before preserving claims.

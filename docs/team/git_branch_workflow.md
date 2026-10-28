# CryptoShift Role-Based Git Branch & Collaboration Workflow

**Project:** CryptoShift (`Quant-A-Maze 3.0, PQC-01: Verification-Gated Cryptographic Migration Across Banking Applications`)  
**Base Branch:** `main` (`527c6eb`)

---

## 1. How Git Branches Work (Beginner Overview)

- **Full Baseline on Every Branch:** A Git branch contains the repository's entire history and full working baseline — it does **not** isolate or delete folders belonging to other team members. Every member can run the full CLI, demo, and test suite on their branch.
- **Role-Scoped Commits:** Even though your branch has the whole project so you can run and test it, **your commits must only modify the files owned by your role**. A pull request (PR) compares your branch against `main` and shows only the lines you changed.
- **One Branch per Working Directory:** A single project folder (`CryptoShift/`) can only have **one** branch checked out at a time.
  - If team members work on their own laptops, each member clones the repository and checks out their assigned branch (`git switch <branch-name>`).
  - If multiple branches need to be edited simultaneously on the same machine, use separate directory clones or `git worktree` checkouts rather than switching branches inside a dirty working tree.

---

## 2. Team Branch Assignments & File Ownership Boundaries

All four role branches are created from verified `main` (`527c6eb`):

| Role | Branch Name | Owned Paths & Responsibilities |
| :--- | :--- | :--- |
| **Member 1** — Documentation, Datasets, and Bloq Tools | `feature/member-1-docs-data-bloq` | - `docs/`<br>- `data/labels/`<br>- `data/public/`<br>- `experiments/bloq/`<br>- `reports/evaluation/` |
| **Member 2** — Cryptographic Discovery and Inventory | `feature/member-2-discovery` | - `src/cryptoshift/scanner.py`<br>- `src/cryptoshift/rules.py`<br>- Scanner-specific tests and fixtures under `tests/` |
| **Member 3** — Migration Planning, Verification, and Rollback | `feature/member-3-planning-verification` | - `src/cryptoshift/dependencies.py`<br>- `src/cryptoshift/scoring.py`<br>- `src/cryptoshift/verification.py`<br>- `src/cryptoshift/rollback.py`<br>- `src/cryptoshift/optimization/`<br>- Planning and verification tests under `tests/` |
| **Member 4** — Full-Stack Application and Integration | `feature/member-4-fullstack` | - `src/cryptoshift/ui/`<br>- `src/cryptoshift/cli.py` and `cryptoshift_cli.py`<br>- `src/cryptoshift/reporting.py`<br>- End-to-end tests and report presentation |

### Role-Specific Guardrails

- **Member 1 (Docs, Datasets & Bloq):** Record data sources, licenses, retrieval details, labeling rules, actual evaluation results, setup steps, demo instructions, and limitations. Bloq artifacts must use approved, non-sensitive data only. Never fabricate or document a Bloq run unless it was actually executed.
- **Member 2 (Discovery & Inventory):** Work on evidence-backed discovery and CBOM inventory. Keep the current flat Python modules (`src/cryptoshift/scanner.py`, `src/cryptoshift/rules.py`) in place unless a coordinated package refactor is approved.
- **Member 3 (Planning, Verification & Rollback):** Keep the deterministic fallback planner (`src/cryptoshift/optimization/fallback_scheduler.py`) as the required, always-runnable baseline. QpiAI Opt / QCloud / Bloq quantum experiments remain optional and must never be required for the application to run.
- **Member 4 (Full-Stack & Integration):** Consume real scanner, migration-plan, and verification data records in UI and CLI reporting. Never hard-code demo findings or synthetic numbers directly into UI components.

---

## 3. Shared Files & Review Rules

The following files affect multiple workstreams and **must not** be edited independently by multiple members at the same time:

- `src/cryptoshift/models.py`
- `pyproject.toml`
- `requirements.txt`
- `.gitignore`
- `README.md`
- `docs/README.md`
- `tests/test_cryptoshift.py`

### Rules for Modifying a Shared File

1. **Assign a Single Editor:** Agree on one team member to make the edit before changing any shared file.
2. **Request Teammate Review:** Before merging a shared-file change into `main`, request review from every affected teammate (for example, changes to `src/cryptoshift/models.py` require review from Members 2, 3, and 4).
3. **Preserve Layout & CLI Entry Points:** Keep the existing CLI subcommands and package layout intact unless a separate, tested change is explicitly approved by the team.

---

## 4. What to Do When a Change Touches Another Member's Files

If your feature requires a change in a file owned by another member:

1. **Do not silently edit their file on your branch.** Editing another member's file on your branch will create merge conflicts when both branches open pull requests to `main`.
2. **Coordinate the Interface Contract:** Discuss the needed function signature, return field, or model attribute with the file's owner.
3. **Choose One Clean Path:**
   - **Preferred:** Have the owning member make and commit the change on their branch (or via a small shared-contract PR merged first), then rebase/merge `main` into your branch.
   - **Alternative (if pairing):** If the file's owner explicitly approves including a small adapter change on your branch, document their approval in your PR description and assign them as a required reviewer so they can sync their branch immediately after merge.

---

## 5. Explicit-Path Staging & Commit Workflow

Never use bulk staging commands (`git add .` or `git add -A`), and never use destructive commands (`git reset`, `git clean`, or `git push --force`).

When you complete a unit of work on your branch, follow these exact steps:

1. **Confirm your active branch:**
   ```powershell
   git branch --show-current
   ```
   Ensure you are on your assigned `feature/member-*` branch, not `main`.
2. **Inspect working tree status and unstaged diffs:**
   ```powershell
   git status --short --branch
   git diff
   ```
3. **Stage only your intended, role-owned file paths explicitly:**
   ```powershell
   # Example for Member 2:
   git add src/cryptoshift/scanner.py src/cryptoshift/rules.py tests/unit/test_scanner_rules.py
   ```
   *Never run `git add .` or `git add -A`.*
4. **Review the staged diff and run the secret/hygiene check:**
   ```powershell
   git diff --staged
   .\.venv\Scripts\python.exe scripts/verify_repo.py
   ```
   Confirm that:
   - No `.env`, `qcloud.env`, API keys, tokens, `.venv/`, or `.backup_*/` files are staged.
   - No unrelated generated reports or another member's files are included.
5. **Commit with a clear, role-specific message:**
   ```powershell
   git commit -m "member-2: add contextual certificate key-usage detection rule"
   ```
6. **Push your role branch to `origin` (without force-pushing):**
   ```powershell
   git push -u origin <your-branch-name>
   ```
   *Note: Do not push empty branches. Only push a role branch after making at least one reviewed, role-specific commit.*
7. **Open a Pull Request to `main`** on GitHub once your feature slice and tests pass.
8. **Request review** from the relevant teammate(s) for any shared contracts or integration touchpoints.
9. **Resolve merge conflicts safely:** Always preserve both intended changes when resolving conflicts; never overwrite or discard a teammate's work just to make a merge pass.

---

## 6. Recommended Pull-Request Merge Order

To minimize merge conflicts and keep `main` runnable at every stage, merge pull requests in this order:

1. **Shared data-model or contract changes** (`src/cryptoshift/models.py`, dependencies in `pyproject.toml` / `requirements.txt`), after review by all affected members.
2. **Member 2 (`feature/member-2-discovery`)** — cryptographic discovery and CBOM inventory changes.
3. **Member 3 (`feature/member-3-planning-verification`)** — dependency graph, wave scheduling, verification, and rollback changes.
4. **Member 4 (`feature/member-4-fullstack`)** — UI, CLI wiring, reporting, and end-to-end integration.
5. **Member 1 (`feature/member-1-docs-data-bloq`)** — documentation, dataset records, and evaluation evidence updates reflecting the final merged behavior.


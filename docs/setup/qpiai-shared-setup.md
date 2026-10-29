# Shared QpiAI SDK & Local Credential Setup for CryptoShift Team Branches

This guide explains how every CryptoShift team member can use the same checked-in **QpiAI Opt** (`qpiai-opt`) and **QpiAI Quantum / QCloud** (`qpiai-quantum`) integration code from their own Git branch, local worktree, and JupyterLab workspace without duplicating client code, consuming paid cloud credits, or exposing credentials.

---

## 1. Core Team Principles

1. **One Shared Checked-In Adapter Layer Across All Branches:**
   - All branches (`main`, `feature/member-1-docs-data-bloq`, `feature/member-2-discovery`, `feature/member-3-planning-verification`, and `feature/member-4-fullstack`) share the same canonical QpiAI integration modules under [`src/cryptoshift/optimization/`](../../src/cryptoshift/optimization/).
   - **Do not create one copy of the QpiAI client or adapter per team member or per branch.** Always import from `cryptoshift.optimization`.
2. **Local Per-Workspace Credentials Only:**
   - Each developer configures credentials locally in their own workspace (`.env` in the local repository or worktree root).
   - Credentials must **never** be committed to Git, hardcoded in `.py` files, pasted into Jupyter notebooks (`.ipynb`), or included in screenshots, terminal logs, pull requests, or generated reports (`reports/`).
3. **Opt-In Online Calls & Deterministic Fallback by Default:**
   - Online key validation is **opt-in** (`--online-auth` on the CLI or `allow_online_auth=True` in Python). By default (`allow_online_auth=False`), CryptoShift performs zero network calls.
   - Remote cloud/platform execution (`mode="platform"`, `submit()`, and hardware QPUs such as `QpiAI-Indus-1`) is **disabled** in the checked-in adapters to prevent unintended credit consumption.
   - The deterministic local planner ([`src/cryptoshift/optimization/fallback_scheduler.py`](../../src/cryptoshift/optimization/fallback_scheduler.py)) is always retained as the automatic fallback so every branch runs end-to-end even without QpiAI credentials or internet access.

---

## 2. QpiAI Opt vs. QpiAI Quantum / QCloud: Roles & Existing Adapters

CryptoShift integrates two distinct official QpiAI packages alongside its deterministic baseline scheduler. Keep their roles, environment variables, and adapters distinct:

| Capability | Official Package & Version | Checked-In Adapter Module | Environment Variable | What Runs Offline (Default) | What Requires Opt-In `--online-auth` + Key |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Deterministic Baseline Fallback** | Python 3.10+ standard library | [`src/cryptoshift/optimization/fallback_scheduler.py`](../../src/cryptoshift/optimization/fallback_scheduler.py)<br>(`solve_with_fallback_scheduler`, `is_schedule_feasible`, `compute_schedule_objective`) | None | Exact constrained combinatorial search across 6 banking services and 3 maintenance waves (`execution_mode="deterministic_local"`, objective `248.105`). | None (100% local & credential-free). |
| **2. QpiAI Opt Optimization (MILP Wave Scheduling)** | `qpiai-opt[quantum]==0.0.9`<br>(`qpiai_opt.opt_modeller`, `qpiai_opt.opt_solvers`) | [`src/cryptoshift/optimization/qpiai_opt_adapter.py`](../../src/cryptoshift/optimization/qpiai_opt_adapter.py)<br>(`build_qpiai_opt_wave_model`, `solve_with_qpiai_opt`)<br>& [`src/cryptoshift/optimization/auth_check.py`](../../src/cryptoshift/optimization/auth_check.py) (`verify_opt_local_auth`) | `QPIAI_OPT_API_KEY`<br>(Portal: <https://opt.qpiai.tech/>) | Builds the 18-binary-variable, 19-constraint MILP (`Model("cryptoshift_wave_schedule")`), verifies `classify(model) == "MILP"`, runs `inspect(model)`, and checks baseline schedule feasibility via `feasibility(model, ...)`. | Authenticates `Client(api_key=...)` online and runs the native local MILP solver via `solve(model, mode="local", client=client)`. Never calls `mode="platform"`. |
| **3. QpiAI Quantum / QCloud Circuit Execution (Wave-0 QUBO / QAOA)** | `qpiai-quantum==0.3.0` & `qpiai-opt[quantum]==0.0.9`<br>(`qpiai_quantum`, `qpiai_opt.quantum`) | [`src/cryptoshift/optimization/qcloud_experiment.py`](../../src/cryptoshift/optimization/qcloud_experiment.py)<br>(`run_qcloud_wave0_qubo_experiment`, `evaluate_wave0_qubo_bitstring`)<br>& [`src/cryptoshift/optimization/auth_check.py`](../../src/cryptoshift/optimization/auth_check.py) (`verify_qcloud_local_auth_and_sim`) | `QPIAI_QCLOUD_API_KEY`<br>(Bridged to `API_KEY` in memory; Portal: <https://qcloud.qpiai.tech/>) | Compiles the 4-qubit Wave-0 selection QUBO (`QUBOProblem.from_model`), inspects and builds the `QAOA(reps=1)` circuit (`build_circuit`, `depth=8`, `size=18`), and simulates 1024 shots on the local CPU statevector simulator (`device_name="QpiAI-QSV-Local"`). | Authenticates via `QpiAIQuantumAuth.login()` / `verify_api_key()` and runs local variational QAOA via `solve(qubo, mode="local", algorithm=QAOA(...), execution=QuantumRun(shots=1024, seed=7))`. Never submits paid hardware QPU jobs. |

---

## 3. Step-by-Step Local Setup on Any Branch or Worktree

### Step 1: Switch to Your Assigned Branch (or Worktree)

Each team member works on their role branch checked out from `main` (see [`docs/team/git_branch_workflow.md`](../team/git_branch_workflow.md)):

```powershell
git branch --show-current
git status --short --branch
```

> **Note on Multiple Clones / Worktrees:** Because `.env` and `.venv/` are git-ignored, if you create a separate directory clone or `git worktree` (for example, `CryptoShift_Member3`), create or copy your local `.env` inside that workspace directory and point your commands to your local `.venv`.

### Step 2: Install the Package and Optional QpiAI SDKs in `.venv`

Use the commands defined in [`pyproject.toml`](../../pyproject.toml), [`requirements.txt`](../../requirements.txt), and [`README.md`](../../README.md):

```powershell
# 1. Create the virtual environment if it does not exist yet
python -m venv .venv

# 2. Install the pinned QpiAI SDKs and python-dotenv inside .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# (Equivalent pyproject.toml extra: .\.venv\Scripts\python.exe -m pip install ".[qpiai]")

# 3. Install CryptoShift in editable mode (offline / no-deps when packages are already installed)
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
```

### Step 3: Create Your Local `.env` from `.env.example`

Never create credential files with invented variable names. Always initialize `.env` from the committed [`.env.example`](../../.env.example) template:

```powershell
# Creates .env from .env.example if .env does not exist (never overwrites an existing .env)
.\.venv\Scripts\python.exe cryptoshift_cli.py init-env
```

Or copy the template manually in PowerShell:

```powershell
Copy-Item .env.example .env
```

If a standalone `qpiai-quantum` workflow specifically expects `qcloud.env`, you can also copy [`qcloud.env.example`](../../qcloud.env.example) to `qcloud.env` locally (`Copy-Item qcloud.env.example qcloud.env`). However, for all CryptoShift modules, [`load_project_env_files()`](../../src/cryptoshift/optimization/auth_check.py) automatically loads `.env` (and `qcloud.env` if present) and bridges `QPIAI_QCLOUD_API_KEY` and `API_KEY` in memory.

### Step 4: Fill In Approved Credentials Locally

Open your local `.env` file in your editor and paste your keys after `=` (with no quotes or spaces needed):

```ini
QPIAI_OPT_API_KEY=
QPIAI_QCLOUD_API_KEY=
```

- **Individual Developer Keys:** Register at <https://opt.qpiai.tech/> (`QPIAI_OPT_API_KEY`) and <https://qcloud.qpiai.tech/> (`QPIAI_QCLOUD_API_KEY`).
- **Shared Team Credential Rule:** If the team is authorized to use a single shared team credential, share it **only** through an approved secret-sharing channel (such as a team password manager or encrypted one-time secret link). **Never** place any key in GitHub (commits, PRs, issues, discussions), source code, notebooks, screenshots, chat logs, or documentation.

---

## 4. Verifying and Running the Shared Integration

> **Verification Honesty Note:** No live QpiAI cloud or online authentication calls were executed while authoring this guide. Always report only the exact execution mode and statuses produced by your actual run (`offline_ir_only`, `local_simulator`, `qpiai_opt_local`, or `deterministic_local`).

### Safe Offline Verification (Default — Zero Network Calls)

Run these commands on any branch to verify package imports, `.env` key presence (`"key configured"` vs. `"key missing"`), offline `qpiai-opt` MILP classification/inspection/feasibility, local `QpiAI-QSV-Local` quantum simulation, and the deterministic fallback scheduler:

```powershell
# 1. Safe offline credential & local simulator smoke check
.\.venv\Scripts\python.exe cryptoshift_cli.py check-auth

# 2. Run migration-wave scheduling comparison and write reports/qpiai/
.\.venv\Scripts\python.exe cryptoshift_cli.py schedule

# 3. Run full discovery, scheduling, verification gates, and dataset evaluation
.\.venv\Scripts\python.exe cryptoshift_cli.py demo

# 4. Run unit tests and repository secret/hygiene verification
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/verify_repo.py
```

### Opt-In Online Key Validation with Local Solving (`--online-auth`)

When you have configured valid keys in `.env` and explicitly want to validate keys online and run authenticated local solving (`solve(model, mode="local", client=client)` and `QpiAIQuantumAuth.login()` + variational QAOA on `QpiAI-QSV-Local`), pass `--online-auth`:

```powershell
# Opt-in online key validation + local solver/simulator check
.\.venv\Scripts\python.exe cryptoshift_cli.py check-auth --online-auth

# Opt-in online key validation during scheduling or full demo
.\.venv\Scripts\python.exe cryptoshift_cli.py schedule --online-auth
.\.venv\Scripts\python.exe cryptoshift_cli.py demo --online-auth
```

---

## 5. Using the Shared Setup in JupyterLab Workspaces

When working in JupyterLab (for example, in [`experiments/bloq/notebooks/`](../../experiments/bloq/notebooks/) or local analysis notebooks on your branch):

1. **Use the Project `.venv` Kernel:** Ensure your JupyterLab kernel points to the workspace `.venv` where `cryptoshift` is installed in editable mode.
2. **Import the Checked-In Adapters Instead of Rewriting Client Logic:**
   ```python
   from cryptoshift.scoring import build_migration_tasks
   from cryptoshift.models import WaveScheduleConfig
   from cryptoshift.optimization import (
       check_credentials_status,
       load_project_env_files,
       redact_secrets,
       solve_with_fallback_scheduler,
       solve_with_qpiai_opt,
       run_qcloud_wave0_qubo_experiment,
   )

   # Load .env / qcloud.env into os.environ in memory without printing values
   load_project_env_files()

   # Safe status check: returns ONLY 'key configured' or 'key missing'
   print(check_credentials_status())

   # Offline by default (allow_online_auth=False); falls back cleanly to deterministic scheduler
   tasks = build_migration_tasks()
   cfg = WaveScheduleConfig()
   opt_result, opt_meta = solve_with_qpiai_opt(tasks, cfg, allow_online_auth=False)
   qcloud_result = run_qcloud_wave0_qubo_experiment(allow_online_auth=False)
   ```
3. **Never Display or Save Secrets in Notebook Outputs:**
   - **Never** paste `QPIAI_OPT_API_KEY` or `QPIAI_QCLOUD_API_KEY` literals into notebook cells.
   - **Never** print `os.environ`, raw API key variables, or unredacted exception messages in cell outputs. Wrap any custom error logging in `redact_secrets(str(exc))`.
   - Before staging or committing any `.ipynb` file, clear or inspect all cell outputs and run `.\.venv\Scripts\python.exe scripts/verify_repo.py` to confirm zero secrets or local user paths (`C:\Users\...`) are saved in the notebook JSON.

---

## 6. Troubleshooting (Secret-Safe)

All diagnostic checks in [`src/cryptoshift/optimization/auth_check.py`](../../src/cryptoshift/optimization/auth_check.py) automatically scrub configured keys, Bearer tokens, and local user paths via `redact_secrets()`. Never print raw key values when debugging.

### 1. Missing Credentials (`configuration_status: "key missing"` or `blocked (... missing)`)
- **Symptoms:** `check-auth` reports `key missing` for `QPIAI_OPT_API_KEY` or `QPIAI_QCLOUD_API_KEY`, or `--online-auth` reports `blocked (QPIAI_OPT_API_KEY missing)` / `blocked (QPIAI_QCLOUD_API_KEY missing)`.
- **Common Causes:**
  - `.env` has not been created in your current branch checkout or `git worktree` folder.
  - The variable is empty or still set to a placeholder string filtered by `PLACEHOLDER_VALUES` (such as `your_qpiai_opt_api_key_here`, `changeme`, `none`, or `null`).
  - You edited `.env.example` instead of `.env` (keep `.env.example` and `qcloud.env.example` blank!).
- **Resolution:**
  1. Run `.\.venv\Scripts\python.exe cryptoshift_cli.py init-env` in the root of your active workspace.
  2. Open `.env` locally, paste your real key after `QPIAI_OPT_API_KEY=` and `QPIAI_QCLOUD_API_KEY=`, and save.
  3. Re-run `.\.venv\Scripts\python.exe cryptoshift_cli.py check-auth` (offline status check).

### 2. Authentication Failures (`blocked (invalid/rejected key)` or `blocked (authentication/network error)`)
- **Symptoms:** Running with `--online-auth` returns `blocked (invalid/rejected key)` or `blocked (authentication/network error)` while offline modelling and local simulation still succeed.
- **Common Causes:**
  - Swapped keys: `QPIAI_OPT_API_KEY` must come from <https://opt.qpiai.tech/> and `QPIAI_QCLOUD_API_KEY` must come from <https://qcloud.qpiai.tech/>.
  - Trailing whitespace, accidental line breaks, or expired/revoked portal tokens in `.env`.
  - Outbound HTTPS traffic to `opt.qpiai.tech` or `qcloud.qpiai.tech` is blocked by a local firewall, VPN, or offline environment.
- **Resolution:**
  1. Verify each key was generated from its matching portal and has no extra spaces or line breaks in `.env`.
  2. Regenerate the key in the portal if it was rotated or expired.
  3. If working offline or behind a restricted network, omit `--online-auth`; CryptoShift will automatically validate the MILP/QUBO models offline and use the deterministic fallback scheduler.

### 3. Unavailable Backends or SDK Import Errors (`qpiai-opt import failed` / `qpiai-quantum import failed`)
- **Symptoms:** `check-auth` shows `status: "missing"` for `qpiai-opt` or `qpiai-quantum`, or adapters report `qpiai-opt not importable` / `qpiai_opt.quantum import failed`.
- **Common Causes:**
  - Running global `python` instead of the workspace `.\.venv\Scripts\python.exe` (or selecting the wrong kernel in JupyterLab).
  - Optional QpiAI dependencies (`qpiai-opt[quantum]==0.0.9`, `qpiai-quantum==0.3.0`) are not installed in the current `.venv`.
  - Attempting to target an unavailable remote hardware backend instead of `QpiAI-QSV-Local`.
- **Resolution:**
  1. Always run CLI commands with `.\.venv\Scripts\python.exe` and select the `.venv` kernel in JupyterLab.
  2. Install the pinned SDKs inside `.venv` via `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.
  3. Keep all circuit simulations on `device_name="QpiAI-QSV-Local"` and all Opt solves on `mode="local"`. Even if the QpiAI packages are absent, `solve_with_fallback_scheduler()` remains operational.

### 4. Credit or Quota Limitations
- **Symptoms:** Concerns about exhausting QpiAI account credits, rate limits, or remote job quotas across multiple team members.
- **Resolution:**
  1. **Never enable `mode="platform"`, `submit()`, or hardware QPUs (`QpiAI-Indus-1`)** in shared code or notebooks. All checked-in CryptoShift adapters hardcode `mode="local"` and `device_name="QpiAI-QSV-Local"`.
  2. During everyday coding, unit testing, and notebook iteration, use the default offline mode (`allow_online_auth=False` / no `--online-auth` flag). Offline MILP construction (`classify`, `inspect`, `feasibility`), offline QUBO/QAOA circuit building (`QUBOProblem.from_model`, `build_circuit`), direct local statevector simulation (`QpiAI-QSV-Local`), and the deterministic fallback scheduler consume **zero** cloud credits and make **zero** API calls.
  3. Reserve `--online-auth` for occasional smoke verification when explicitly needed.

---

## 7. Repository Protection Checklist Before Committing

Before creating any commit or pull request on your branch:

1. Confirm `.env`, `qcloud.env`, `.venv/`, caches, and backups remain untracked (`git status --short --branch`).
2. Confirm [`.env.example`](../../.env.example) and [`qcloud.env.example`](../../qcloud.env.example) remain blank templates with variable names only.
3. Run the automated repository secret and hygiene scanner:
   ```powershell
   .\.venv\Scripts\python.exe scripts/verify_repo.py
   ```
4. Stage only your explicit, role-owned file paths (`git add <explicit-path>`), never `git add .` or `git add -A`.


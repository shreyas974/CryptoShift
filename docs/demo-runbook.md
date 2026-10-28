# Demo Runbook & Reproducible Verification

All commands below run from the `CryptoShift` project root using the local virtual environment (`.venv`). By default, **online key-validation network requests are disabled** (`allow_online_auth=False`) so all verification commands execute 100% locally without contacting external servers or consuming credits.

---

## 1. Safe Offline Verification Commands

```powershell
# 1. Confirm CLI entrypoint and options
.\.venv\Scripts\python.exe cryptoshift_cli.py --help

# 2. Check package versions, credential presence ('key configured' / 'key missing'),
#    offline QpiAI Opt IR validation, and local QpiAI-QSV-Local simulator
.\.venv\Scripts\python.exe cryptoshift_cli.py check-auth

# 3. Run detection evaluation on the labelled synthetic fixture dataset (writes reports/evaluation/)
.\.venv\Scripts\python.exe cryptoshift_cli.py evaluate

# 4. Run full end-to-end discovery, wave scheduling, verification gates, and reporting (writes reports/qpiai/ and reports/evaluation/)
.\.venv\Scripts\python.exe cryptoshift_cli.py demo

# 5. Run unit test suite
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

# 6. Run repository hygiene & secret scan (never prints secret values)
.\.venv\Scripts\python.exe scripts/verify_repo.py
```

---

## 2. Optional Authorized Online Key Validation (Local Solver Mode Only)

Only when you explicitly want the QpiAI SDKs to verify your `.env` keys online before running the local MILP solver (`mode="local"`) and local variational QAOA simulator (`mode="local"`), pass `--online-auth`:

```powershell
.\.venv\Scripts\python.exe cryptoshift_cli.py check-auth --online-auth
.\.venv\Scripts\python.exe cryptoshift_cli.py demo --online-auth
```

> **Safety Guarantee:** Even with `--online-auth`, CryptoShift strictly uses `mode="local"` and `device_name="QpiAI-QSV-Local"`. Remote platform execution (`mode="platform"`), `submit()`, and hardware QPUs (`QpiAI-Indus-1`) are never invoked.

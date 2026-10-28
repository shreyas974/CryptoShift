# Beginner-Friendly QpiAI Opt & QpiAI QCloud Login Guide (Windows)

This guide explains how to register for your free **QpiAI Opt** and **QpiAI QCloud** API keys, store them safely on your Windows machine, and verify your login without ever exposing your keys in chat, logs, or Git.

---

## 1. Official Portals & Repositories

- **QpiAI Opt Account Portal (for `QPIAI_OPT_API_KEY`):** <https://opt.qpiai.tech/>
- **QpiAI QCloud Account Portal (for `QPIAI_QCLOUD_API_KEY`):** <https://qcloud.qpiai.tech/>
- **QpiAI Opt SDK Repository:** <https://github.com/qpiai/qpiai-opt>
- **QpiAI Quantum SDK Repository:** <https://github.com/qpiai/quantum-sdk>
- **QpiAI Quantum Documentation:** <https://docs.qcloud.qpiai.tech/>

---

## 2. How to Get and Enter Your API Keys Locally

### Step A: Generate Your Keys on the Portals
1. Sign in to **QpiAI Opt** at <https://opt.qpiai.tech/> and copy your **Opt API Key**.
2. Sign in to **QpiAI QCloud** at <https://qcloud.qpiai.tech/> and copy your **QCloud API Key**.

### Step B: Paste Your Keys into the Ignored `.env` File
1. In the `CryptoShift` project root (`c:\Users\lohig\OneDrive\Documents\CryptoShift`), open the local `.env` file (created automatically from `.env.example`, or run `.\.venv\Scripts\python.exe cryptoshift_cli.py init-env`).
2. Paste your keys directly after the `=` signs:
   ```ini
   QPIAI_OPT_API_KEY=paste_your_opt_api_key_here
   QPIAI_QCLOUD_API_KEY=paste_your_qcloud_api_key_here
   ```
3. Save `.env`.
   - **Security Check:** `.env` and `qcloud.env` are listed in [.gitignore](file:///c:/Users/lohig/OneDrive/Documents/CryptoShift/.gitignore) so Git will never track or commit them.
   - **Compatibility Note:** `cryptoshift` automatically bridges `QPIAI_QCLOUD_API_KEY` to `API_KEY` in memory so both `qpiai-opt[quantum]` (`QPIAI_QCLOUD_API_KEY`) and standalone `qpiai-quantum` (`API_KEY` / `qcloud.env`) work seamlessly from `.env`.

---

## 3. How to Verify Your Credentials Safely

Run the built-in credential and local solver check inside the project virtual environment:

```powershell
.\.venv\Scripts\python.exe cryptoshift_cli.py check-auth
```

What this command does:
- Prints **only** `key configured` or `key missing` for `QPIAI_OPT_API_KEY` and `QPIAI_QCLOUD_API_KEY` (it **never** prints or logs the key itself).
- Scrubs any secret value (`[REDACTED]`) if an exception message is raised.
- Tests **QpiAI Opt** local solving (`Client(api_key=...)` + `solve(model, mode="local", client=client)`).
- Tests **QpiAI QCloud** authentication (`QpiAIQuantumAuth.login(...)` + `QpiAIQuantumAuth.verify_api_key()`) and runs a 2-qubit Bell circuit on the local statevector simulator (`device_name="QpiAI-QSV-Local"`).

---

## 4. Execution Modes: Local Solving vs. Local Simulation vs. Paid Platform Execution

| Mode / Feature | SDK Call | Required Key | Uses Paid Credits? | Enabled in CryptoShift? |
|---|---|---|---|---|
| **Offline Model & Circuit Build** | `Model`, `classify()`, `inspect()`, `feasibility()`, `QUBOProblem.from_model()`, `build_circuit()` | None | **No** (Free, offline) | **Yes (Always runs)** |
| **Direct Local Statevector Simulator** | `Circuit.run(..., device_name="QpiAI-QSV-Local")` | None | **No** (Free, local CPU) | **Yes (Always runs)** |
| **QpiAI Opt Local Solving** | `solve(model, mode="local", client=Client(api_key=...))` | `QPIAI_OPT_API_KEY` | **No** (Free; verifies key online, solves locally) | **Yes (When key configured)** |
| **QpiAI Local Variational QAOA** | `solve(qubo, mode="local", algorithm=QAOA(...))` | `QPIAI_QCLOUD_API_KEY` | **No** (Free; verifies key online, simulates locally) | **Yes (When key configured)** |
| **Remote Platform / Hardware QPU** | `solve(..., mode="platform")`, `submit()`, `device_name="QpiAI-Indus-1"` | Opt / QCloud Key | **Yes (Can consume credits)** | **Disabled by default** |

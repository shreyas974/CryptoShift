# CryptoShift — QpiAI Integration & Verification Evidence Report

- **Project:** Quant-A-Maze 3.0 — PQC-01: Verification-Gated Cryptographic Migration Across Banking Applications
- **Python Runtime:** `3.12.14`
- **Virtual Environment:** `.venv (Python 3.12.14)`
- **Online Key Validation Executed in This Run:** `True`

## 1. Package & SDK Availability

| Component | Package / Module | Version | Status |
|---|---|---|---|
| QpiAI Opt SDK | `qpiai-opt` | `0.0.9` | **installed & importable** |
| QpiAI Quantum SDK | `qpiai-quantum` | `0.3.0` | **installed & importable** |
| Python Dotenv | `python-dotenv` | `1.2.4` | **installed & importable** |

## 2. Non-Sensitive Credential & Authentication Status

| Credential Variable | Local Configuration | Online / SDK Auth Verification | Notes |
|---|---|---|---|
| `QPIAI_OPT_API_KEY` | `key configured` | **run successfully** | Authenticated QpiAI Opt local solve succeeded (`mode='local'`, zero paid platform usage). |
| `QPIAI_QCLOUD_API_KEY` | `key configured` | **run successfully** | QpiAIQuantumAuth.login() and verify_api_key() succeeded. Local simulator (`QpiAI-QSV-Local`): run successfully. |

## 3. Component Implementation & Execution Status Matrix

| Component | Status Label | Execution Mode | Backend / Solver | Objective Value | Feasible | Runtime (s) |
|---|---|---|---|---:|---|---:|
| Deterministic Dependency-Aware Fallback Scheduler | **run successfully** | `deterministic_local` | `CPU Exact Combinatorial Search` | 248.10 | `True` | 0.0051 |
| QpiAI Opt Algebraic Modeller & IR Feasibility (`qpiai-opt`) | **run successfully** | `local_ir_validation` | `qpiai_opt.opt_modeller / opt_solvers` | 248.10 | `True` | 0.0733 |
| QpiAI Opt Authenticated Local Solver (`solve(mode='local')`) | **run successfully** | `local` | `qpiai_opt.opt_solvers.solve (mode='local')` | 248.10 | `True` | 0.0733 |
| QpiAI Quantum 4-Qubit Wave-0 QUBO & QAOA Circuit (`build_circuit`) | **run successfully** | `local_circuit_build` | `qpiai_opt.quantum.QAOA` | -13.07 | `True` | 0.7705 |
| QpiAI Quantum Local Statevector Simulator (`QpiAI-QSV-Local`) | **run successfully (local simulator)** | `local_simulator` | `QpiAI-QSV-Local` | -13.07 | `True` | 0.7705 |
| QpiAI QCloud Authenticated Variational QAOA (`solve(..., mode='local')`) | **run successfully (local simulator)** | `local_simulator_authenticated` | `QpiAIQuantumAuth + QpiAI-QSV-Local` | -13.07 | `True` | 0.7705 |

## 4. Schedule Comparison (6 Banking Services across 3 Waves)

### Deterministic Dependency-Aware Fallback Baseline
- **Status:** `run successfully`
- **Objective Value:** `248.105`
- **Wave Assignment:** `{"0": ["interbank_tls", "ledger_audit"], "1": ["auth_gateway", "payment_signing"], "2": ["card_vault", "settlement_batch"]}`

### QpiAI Opt (`qpiai-opt` MILP/Binary Model)
- **Offline Model Compilation & Inspection Status:** `run successfully`
- **Problem Class (`classify(model)`):** `MILP`
- **Baseline Feasibility Verified by `qpiai_opt.opt_solvers.feasibility()`:** `True`
- **Authenticated Local Solve Status (`solve(model, mode='local', client=...)`):** `run successfully`
- **Detail:** QpiAI Opt local solver completed (`mode='local'`). Opt objective=248.1050 vs. Fallback objective=248.1050.

### QpiAI QCloud / Quantum SDK (`qpiai-opt[quantum]` & `qpiai-quantum`)
- **4-Qubit Wave-0 QUBO Compilation Status:** `run successfully`
- **QAOA Logical Circuit Construction (`build_circuit`) Status:** `run successfully`
- **Logical Circuit Metrics:** Qubits=`4`, Depth=`8`, Size=`18`
- **Direct Local Statevector Simulator (`QpiAI-QSV-Local`) Status:** `run successfully (local simulator)`
- **Authenticated QAOA `solve(..., mode='local')` Status:** `run successfully (local simulator)`
- **Detail:** 4-qubit Wave-0 QUBO compiled (`QUBOProblem.from_model`), QAOA(reps=1) circuit built (depth=8, size=18), and simulated locally on `QpiAI-QSV-Local` (run successfully (local simulator)). All results are classical statevector simulator results.

## 5. Limitations & Honesty Notes

- By default, `cryptoshift` runs in safe offline verification mode (`allow_online_auth=False`) so no online key-validation network requests are sent unless `--online-auth` is explicitly passed.
- Direct `qpiai_quantum.Circuit.run(device_name='QpiAI-QSV-Local')`, `QUBOProblem.from_model()`, `build_circuit()`, `classify()`, `inspect()`, and `feasibility()` execute 100% locally without network calls or credentials.
- All quantum circuit results reported here come from the classical statevector simulator (`QpiAI-QSV-Local`), NOT a physical QPU, and do not demonstrate quantum speedup or production quantum advantage.
- The protocol envelope trace is an explicitly labelled mocked/modelled trace combining real `hashlib` SHA-1/SHA3-256 digests with analytical NIST FIPS 203/204 wire-size parameters.
- Platform mode (`mode='platform'`), `submit()`, and remote QPUs (`QpiAI-Indus-1`) are disabled to prevent unintended credit consumption.

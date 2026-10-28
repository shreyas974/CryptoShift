# CryptoShift — QpiAI Opt & QCloud Setup and Optimization Formulation

This document describes the environment setup, mathematical optimization model, QUBO/QAOA experiment, and fallback architecture for **CryptoShift (Quant-A-Maze 3.0 — PQC-01: Verification-Gated Cryptographic Migration Across Banking Applications)**.

---

## 1. Environment & Package Installation Record

All packages are installed strictly inside the project virtual environment (`.venv`) on Windows (`Python 3.12.14`):

```powershell
# Create virtual environment
python -m venv .venv

# Install official QpiAI Opt SDK with the quantum bridge (installs qpiai-opt==0.0.9 and qpiai-quantum==0.3.0)
.\.venv\Scripts\python.exe -m pip install "qpiai-opt[quantum]"
```

| Package | Installed Version | Import Namespace | Role in CryptoShift |
|---|---|---|---|
| `qpiai-opt` | `0.0.9` | `qpiai_opt` | Algebraic MILP/Binary modelling (`Binary`, `Model`), `classify`, `inspect`, `feasibility`, local MILP solver (`solve(mode="local")`), and `QUBOProblem.from_model` |
| `qpiai-quantum` | `0.3.0` | `qpiai_quantum` | Quantum circuit construction (`Circuit`), local statevector simulation (`QpiAI-QSV-Local`), and QCloud authentication (`QpiAIQuantumAuth`) |

> **Why `qpiai-quantum==0.3.0`?** `qpiai-opt==0.0.9` explicitly declares `qpiai-quantum==0.3.0; extra == "quantum"` so that `qpiai_opt.quantum` (`QAOA`, `QuantumRun`, `build_circuit`, `inspect`) matches the exact circuit and simulator APIs it expects.

---

## 2. Constrained Migration-Wave Scheduling Formulation (`qpiai-opt`)

### Problem Instance
CryptoShift schedules $N = 6$ interdependent banking services across $W = 3$ discrete maintenance waves ($w \in \{0, 1, 2\}$):
1. `auth_gateway` (cost = 18.0, risk = 4.75, duration = 35m, deps = `[]`, Wave-0 verification ready = `True`)
2. `ledger_audit` (cost = 15.0, risk = 6.06, duration = 30m, deps = `[]`, Wave-0 verification ready = `True`)
3. `interbank_tls` (cost = 22.0, risk = 7.01, duration = 40m, deps = `[]`, Wave-0 verification ready = `True`)
4. `card_vault` (cost = 20.0, risk = 4.85, duration = 35m, deps = `["auth_gateway"]`, Wave-0 verification ready = `False`)
5. `payment_signing` (cost = 26.0, risk = 6.50, duration = 45m, deps = `["auth_gateway", "ledger_audit"]`, Wave-0 verification ready = `True`)
6. `settlement_batch` (cost = 28.0, risk = 6.54, duration = 50m, deps = `["payment_signing", "interbank_tls"]`, Wave-0 verification ready = `False`)

### Decision Variables
For each service $s \in S$ and wave $w \in \{0, 1, 2\}$:
$$x_{s,w} \in \{0, 1\}$$
where $x_{s,w} = 1$ iff service $s$ is migrated in maintenance wave $w$ (18 binary variables total).

### Objective Function
Minimize total rollout cost plus risk-weighted delay exposure ($\alpha = 3.5$):
$$\min \sum_{s \in S} \sum_{w=0}^{2} \left( \text{cost}_s + \alpha \cdot \text{risk}_s \cdot w \right) x_{s,w}$$

### Constraints
1. **Single Wave Assignment:** $\sum_{w=0}^{2} x_{s,w} = 1 \quad \forall s \in S$.
2. **Wave Service Capacity ($K_{\max} = 2$):** $\sum_{s \in S} x_{s,w} \le 2 \quad \forall w \in \{0, 1, 2\}$.
3. **Maintenance Window Budget ($T_{\max} = 85\text{ min}$):** $\sum_{s \in S} \text{duration}_s \cdot x_{s,w} \le 85 \quad \forall w \in \{0, 1, 2\}$.
4. **Dependency Precedence:** For every upstream dependency $(u \to v)$, $u$ must migrate no later than $v$:
   $$\sum_{w=0}^{2} w \cdot x_{u,w} - \sum_{w=0}^{2} w \cdot x_{v,w} \le 0$$
5. **Verification Prerequisite Gate:** Services with `verification_ready_wave0 == False` (`card_vault`, `settlement_batch`) cannot be scheduled in Wave 0:
   $$x_{s,0} = 0$$

### Optimal Schedule & Objective Value
- **Wave 0:** `interbank_tls`, `ledger_audit` (70 min $\le 85$ min; 2 services)
- **Wave 1:** `auth_gateway`, `payment_signing` (80 min $\le 85$ min; 2 services; `auth_gateway` in W1 and `ledger_audit` in W0 satisfy `payment_signing` dependencies)
- **Wave 2:** `card_vault`, `settlement_batch` (85 min $\le 85$ min; 2 services; all upstream dependencies satisfied)
- **Optimal Objective Value:** **`248.105`**

---

## 3. 4-Qubit Wave-0 Selection QUBO & QAOA Experiment (`qpiai-quantum`)

To run a compact, genuine quantum optimization experiment tied directly to the scheduling problem without decorative circuits, `cryptoshift/optimization/qcloud_experiment.py` formulates the **Wave-0 Priority Selection** problem over the 4 Wave-0-eligible services $q_i \in \{0, 1\}$ (`auth_gateway`, `ledger_audit`, `interbank_tls`, `payment_signing`):

$$\min \; \sum_{i} (-\text{risk}_i) q_i + P_{\text{cap}} \left(\sum_{i} q_i - 2\right)^2 + P_{\text{dep}} \left( q_{\text{paym}}(1 - q_{\text{auth}}) + q_{\text{paym}}(1 - q_{\text{ledg}}) \right)$$

with $P_{\text{cap}} = 8.0$ and $P_{\text{dep}} = 10.0$.
- Compiled via `QUBOProblem.from_model(model)`.
- Inspected and compiled to a 4-qubit `QAOA(reps=1)` circuit via `qpiai_opt.quantum.build_circuit`.
- Simulated locally on `"QpiAI-QSV-Local"` (`1024` shots).
- The lowest-energy feasible bitstring sampled on the local statevector simulator selects **`["interbank_tls", "ledger_audit"]`** (energy `-13.07`), matching Wave 0 of the exact MILP and deterministic baseline schedule.

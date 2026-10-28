"""QpiAI QCloud / Quantum SDK (`qpiai-opt[quantum]` & `qpiai-quantum`) Wave-0 QUBO experiment.

Formulates a genuine 4-qubit QUBO problem for selecting the immediate Wave-0 banking services
(`auth_gateway`, `ledger_audit`, `interbank_tls`, `payment_signing`) subject to:
- Wave-0 capacity of at most 2 services (`(sum_i q_i - 2)^2` penalty)
- Dependency penalty against selecting `payment_signing` in Wave 0 without its upstream
  prerequisites (`auth_gateway` and `ledger_audit`)
- Rewarding high-urgency root services (`interbank_tls`, `ledger_audit`, `auth_gateway`)

Execution policy:
- Builds the `QUBOProblem` via `QUBOProblem.from_model(model)` (100% offline).
- Runs credential-free `qpiai_opt.opt_solvers.inspect(qubo, algorithm=QAOA(reps=1))` and
  `qpiai_opt.quantum.build_circuit(qubo, algorithm=QAOA(reps=1), parameters=[0.35, 0.25])` (100% offline).
- Runs the QAOA circuit on the local statevector simulator (`device_name="QpiAI-QSV-Local"`)
  via `qpiai_quantum` (100% local CPU, zero network calls) to obtain simulator bitstring counts.
- Only attempts online `QpiAIQuantumAuth.login()` + variational `solve(qubo, mode="local", ...)`
  when `allow_online_auth=True` (`--online-auth`).
- Never calls `mode="platform"` or submits paid QPU jobs (`QpiAI-Indus-1`).
- Clearly labels all simulator results as simulator results and makes no claim of quantum speedup.
"""

from __future__ import annotations

import contextlib
import io
import os
import time
from typing import Any, Dict, List, Tuple

from cryptoshift.optimization.auth_check import (
    _is_valid_secret,
    load_project_env_files,
    redact_secrets,
)


def evaluate_wave0_qubo_bitstring(bits: Dict[str, int]) -> Tuple[float, bool, List[str]]:
    """Evaluate the exact Wave-0 QUBO energy and check Wave-0 capacity & dependency feasibility."""
    a = bits.get("q_auth_gateway", 0)
    l = bits.get("q_ledger_audit", 0)
    i = bits.get("q_interbank_tls", 0)
    p = bits.get("q_payment_signing", 0)

    reward = -4.75 * a - 6.06 * l - 7.01 * i - 6.50 * p
    count = a + l + i + p
    cap_penalty = 8.0 * ((count - 2) ** 2)
    dep_penalty = 10.0 * (p * (1 - a) + p * (1 - l))

    energy = round(reward + cap_penalty + dep_penalty, 4)
    violations: List[str] = []
    if count > 2:
        violations.append(f"Selected {count} services (> Wave-0 capacity of 2).")
    if p == 1 and (a == 0 or l == 0):
        violations.append("Selected payment_signing in Wave 0 without both auth_gateway and ledger_audit.")
    return energy, (len(violations) == 0), violations


def run_qcloud_wave0_qubo_experiment(allow_online_auth: bool = False) -> Dict[str, Any]:
    """Build and run the 4-qubit Wave-0 QUBO QAOA experiment on the local simulator."""
    load_project_env_files()
    start = time.perf_counter()

    try:
        from qpiai_opt.opt_modeller import Binary, Model
        from qpiai_opt.opt_solvers import inspect as quantum_inspect, solve
        from qpiai_opt.opt_solvers.qubo import QUBOProblem
        from qpiai_opt.quantum import (
            QAOA,
            QpiAIQuantumAuth,
            QuantumRun,
            build_circuit,
        )
    except Exception as exc:
        err = redact_secrets(str(exc))
        return {
            "status": "blocked",
            "qubo_compilation_status": "blocked",
            "circuit_construction_status": "blocked",
            "local_qsv_simulator_status": "blocked",
            "authenticated_qaoa_status": "blocked",
            "backend": "N/A",
            "circuit_metrics": {},
            "best_simulator_wave0_selection": [],
            "best_simulator_wave0_energy": None,
            "message": f"qpiai_opt.quantum import failed: {err}",
        }

    # 1. Construct the 4-qubit Wave-0 QUBO model (100% offline)
    q_auth = Binary("q_auth_gateway")
    q_ledg = Binary("q_ledger_audit")
    q_ibnk = Binary("q_interbank_tls")
    q_paym = Binary("q_payment_signing")

    model = Model("cryptoshift_wave0_qubo")
    total_selected = q_auth + q_ledg + q_ibnk + q_paym
    reward_expr = -4.75 * q_auth - 6.06 * q_ledg - 7.01 * q_ibnk - 6.50 * q_paym
    cap_penalty_expr = 8.0 * ((total_selected - 2) * (total_selected - 2))
    dep_penalty_expr = 10.0 * (q_paym * (1 - q_auth) + q_paym * (1 - q_ledg))
    model.minimize(reward_expr + cap_penalty_expr + dep_penalty_expr)

    qubo = QUBOProblem.from_model(model)
    qaoa_alg = QAOA(reps=1, optimizer="cobyla", max_iterations=25)

    # 2. Credential-free quantum inspection & logical QAOA circuit construction (100% offline)
    q_inspection = quantum_inspect(qubo, algorithm=qaoa_alg)
    logical_circuit = build_circuit(qubo, algorithm=qaoa_alg, parameters=[0.35, 0.25])
    circuit_metrics = {
        "qubits": int(q_inspection.get("qubits", 4)) if isinstance(q_inspection, dict) else 4,
        "depth": int(logical_circuit.depth()),
        "size": int(logical_circuit.size()),
        "gates": logical_circuit.list_gates(),
    }

    # 3. Execute fixed-angle QAOA ansatz on the local statevector simulator ("QpiAI-QSV-Local" — 100% local CPU)
    local_qsv_status = "not attempted"
    sampled_counts: Dict[str, int] = {}
    best_sampled_services: List[str] = []
    best_sampled_energy: float | None = None
    sim_buf = io.StringIO()

    try:
        with contextlib.redirect_stdout(sim_buf), contextlib.redirect_stderr(sim_buf):
            measured_circuit = qaoa_alg.build_circuit(qubo, [0.35, 0.25], measurements=True)
            sim_job = measured_circuit.run(
                shots=1024,
                experiment_name="CryptoShift_Wave0_QAOA_LocalSim",
                device_name="QpiAI-QSV-Local",
            )
            raw_counts = sim_job.get_counts() if hasattr(sim_job, "get_counts") else {}
        sampled_counts = {str(k): int(v) for k, v in dict(raw_counts).items()}
        local_qsv_status = "run successfully (local simulator)"

        var_names = ["q_auth_gateway", "q_ledger_audit", "q_interbank_tls", "q_payment_signing"]
        for bitstr in sorted(sampled_counts, key=lambda b: sampled_counts[b], reverse=True):
            clean_bits = bitstr.replace(" ", "")
            if len(clean_bits) == 4:
                b_map = {var_names[idx]: int(clean_bits[idx]) for idx in range(4)}
                en, feas, _ = evaluate_wave0_qubo_bitstring(b_map)
                if feas and (best_sampled_energy is None or en < best_sampled_energy):
                    best_sampled_energy = en
                    best_sampled_services = [
                        name.replace("q_", "") for name, val in b_map.items() if val == 1
                    ]
    except Exception as exc:
        local_qsv_status = f"blocked ({redact_secrets(str(exc))})"

    # 4. Authenticated variational QAOA solve (`mode="local"`) only if `allow_online_auth=True`
    qcloud_key = os.environ.get("QPIAI_QCLOUD_API_KEY", "").strip() or os.environ.get("API_KEY", "").strip()
    auth_qaoa_details: Dict[str, Any] = {}

    if not allow_online_auth:
        auth_qaoa_status = "not attempted (offline verification mode; pass --online-auth to authorize network key check)"
    elif not _is_valid_secret(qcloud_key):
        auth_qaoa_status = "blocked (QPIAI_QCLOUD_API_KEY missing)"
    else:
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                QpiAIQuantumAuth.login(api_key=qcloud_key)
                q_res = solve(
                    qubo,
                    mode="local",
                    algorithm=qaoa_alg,
                    execution=QuantumRun(shots=1024, seed=7),
                )
            auth_qaoa_status = "run successfully (local simulator)"
            var_assign = dict(getattr(q_res, "variable_assignment", {}) or {})
            selected = [k.replace("q_", "") for k, v in var_assign.items() if int(v) == 1]
            auth_qaoa_details = {
                "objective": float(getattr(q_res, "objective", 0.0)),
                "variable_assignment": var_assign,
                "selected_wave0_services": selected,
                "backend": str(getattr(getattr(q_res, "quantum", None), "backend", "QpiAI-QSV-Local")),
            }
        except Exception as exc:
            auth_qaoa_status = f"blocked ({redact_secrets(str(exc))})"

    elapsed = time.perf_counter() - start
    overall_status = (
        "run successfully"
        if "run successfully" in local_qsv_status or "run successfully" in auth_qaoa_status
        else "implemented"
    )

    return {
        "status": overall_status,
        "qubo_compilation_status": "run successfully",
        "circuit_construction_status": "run successfully",
        "local_qsv_simulator_status": local_qsv_status,
        "authenticated_qaoa_status": auth_qaoa_status,
        "backend": "QpiAI-QSV-Local (Local Statevector Simulator — NOT a physical QPU)",
        "runtime_seconds": round(elapsed, 6),
        "circuit_metrics": circuit_metrics,
        "quantum_inspection": q_inspection if isinstance(q_inspection, dict) else str(q_inspection),
        "local_simulator_top_counts": dict(
            sorted(sampled_counts.items(), key=lambda kv: kv[1], reverse=True)[:6]
        ),
        "best_simulator_wave0_selection": best_sampled_services,
        "best_simulator_wave0_energy": best_sampled_energy,
        "authenticated_qaoa_result": auth_qaoa_details,
        "baseline_comparison": {
            "deterministic_wave0": ["interbank_tls", "ledger_audit"],
            "deterministic_wave0_energy": -13.07,
            "simulator_matches_deterministic_optimum": sorted(best_sampled_services)
            == ["interbank_tls", "ledger_audit"],
        },
        "message": (
            "4-qubit Wave-0 QUBO compiled (`QUBOProblem.from_model`), QAOA(reps=1) circuit built "
            f"(depth={circuit_metrics['depth']}, size={circuit_metrics['size']}), and simulated locally on "
            f"`QpiAI-QSV-Local` ({local_qsv_status}). All results are classical statevector simulator results."
        ),
    }

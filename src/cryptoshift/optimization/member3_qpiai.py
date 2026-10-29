"""Member 3 QpiAI experiments on the Phase 2 (findings-derived) planning problem.

1. QpiAI Opt: the existing MILP builder (`build_qpiai_opt_wave_model`) applied to the Phase 2 tasks; offline
   `classify`, `inspect`, `feasibility` only. Authenticated `solve(mode="local")` runs only when explicitly
   authorized AND a key is present in the environment; never `mode="platform"`, `submit()` or hardware.
2. QpiAI Quantum: reproduction of the existing 4-qubit Wave-0 experiment, then the same formulation on the
   Phase 2 Wave-0 selection subproblem, sampled on the in-process `QpiAI-QSV-Local` statevector simulator.

Bit order (measured, see docs/evidence/member3-log.md): measurement strings are little-endian; QUBO variable i
(`qubo.variable_names[i]`) is string position len-1-i. All quantum results are SIMULATOR results.
"""

from __future__ import annotations

import contextlib
import io
import itertools
import os
import time
from importlib import metadata
from typing import Any, Dict, List, Optional, Tuple

from cryptoshift.models import WaveScheduleConfig
from cryptoshift.optimization.auth_check import _is_valid_secret, redact_secrets
from cryptoshift.optimization.fallback_scheduler import compute_schedule_objective
from cryptoshift.optimization.qpiai_opt_adapter import build_qpiai_opt_wave_model

QAOA_PARAMS = [0.35, 0.25]  # same fixed angles as the existing experiment
SHOTS = 1024


def sdk_versions() -> Dict[str, str]:
    out = {}
    for p in ("qpiai-opt", "qpiai-quantum"):
        try:
            out[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            out[p] = "not installed"
    return out


def _wcfg(c: Dict[str, Any]) -> WaveScheduleConfig:
    return WaveScheduleConfig(num_waves=c["num_waves"], max_services_per_wave=c["max_services_per_wave"],
                              max_minutes_per_wave=c["max_minutes_per_wave"], risk_delay_weight=c["risk_delay_weight"],
                              enforce_verification_gate=c["enforce_verification_gate"])


def opt_wave_model_checks(tasks: List[Any], constraints: Dict[str, Any], baseline_assignment: Dict[str, int],
                          authorized_local_solve: bool = False) -> Dict[str, Any]:
    """Build the MILP from the Phase 2 tasks and run the SDK's offline checks."""
    from qpiai_opt.opt_solvers import classify, feasibility, inspect

    cfg = _wcfg(constraints)
    t0 = time.perf_counter()
    model, var_map = build_qpiai_opt_wave_model(tasks, cfg)
    problem_class = str(classify(model))
    info = inspect(model)
    values = {f"x_{t.service_id}_w{w}": float(baseline_assignment.get(t.service_id) == w)
              for t in tasks for w in range(cfg.num_waves)}
    feas = feasibility(model, values)
    elapsed = time.perf_counter() - t0
    n_constraints = len(tasks) + 2 * cfg.num_waves + sum(len(t.dependencies) for t in tasks) + (
        sum(1 for t in tasks if not t.verification_ready_wave0) if cfg.enforce_verification_gate else 0)

    key_present = _is_valid_secret(os.environ.get("QPIAI_OPT_API_KEY"))
    solve_status: Dict[str, Any]
    if not authorized_local_solve:
        solve_status = {"status": "BLOCKED", "reason": "authenticated local solve not authorized by the owner in this session"}
    elif not key_present:
        solve_status = {"status": "BLOCKED", "reason": "QPIAI_OPT_API_KEY not present in the environment"}
    else:  # pragma: no cover - only with owner authorization and a key
        from qpiai_opt.opt_solvers import Client, solve

        buf = io.StringIO()
        try:
            s0 = time.perf_counter()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                res = solve(model, mode="local", client=Client(api_key=os.environ["QPIAI_OPT_API_KEY"]))
            sol = dict(getattr(res, "solution", {}) or {})
            assign = {t.service_id: next((w for w in range(cfg.num_waves) if float(sol.get(f"x_{t.service_id}_w{w}", 0)) >= 0.5), None)
                      for t in tasks}
            obj = float(getattr(res, "objective", float("nan")))
            base_obj = compute_schedule_objective(tasks, baseline_assignment, cfg)
            solve_status = {"status": "RUN", "solver_status": str(getattr(res, "status", "")),
                            "execution_mode": str(getattr(res, "execution_mode", "")),
                            "problem_class": str(getattr(res, "problem_class", "")),
                            "objective": obj, "assignment": assign,
                            "solver_time_s": getattr(res, "solver_time_s", None),
                            "runtime_seconds": round(time.perf_counter() - s0, 4),
                            "same_input_comparison": {
                                "baseline_objective": base_obj, "qpiai_opt_objective": obj,
                                "difference": None if base_obj is None else round(obj - base_obj, 6),
                                "same_assignment": assign == {t.service_id: baseline_assignment.get(t.service_id) for t in tasks},
                                "note": "Lower is better. 'Better' is claimed only if the difference is negative."}}
        except Exception as exc:
            solve_status = {"status": "BLOCKED", "reason": redact_secrets(str(exc))[:300]}

    return {
        "sdk_versions": sdk_versions(),
        "model_name": "cryptoshift_wave_schedule",
        "binary_variables": len(var_map),
        "constraints": n_constraints,
        "problem_class": problem_class,
        "inspect": info if isinstance(info, dict) else str(info),
        "baseline_feasible_in_opt_model": bool(feas.get("feasible")) if isinstance(feas, dict) else None,
        "feasibility_report": feas if isinstance(feas, dict) else str(feas),
        "baseline_objective_recomputed": compute_schedule_objective(tasks, baseline_assignment, cfg),
        "offline_checks_runtime_seconds": round(elapsed, 4),
        "authenticated_local_solve": solve_status,
        "never_called": ["mode='platform'", "submit()", "hardware QPU"],
    }


# ---------------------------------------------------------------- quantum (simulator) -------------------------

def wave0_qubo_terms(candidates: List[Dict[str, Any]], deps: List[Tuple[str, str]], capacity: int,
                     max_minutes: int) -> Dict[str, Any]:
    """Same formulation as the existing experiment: reward + capacity^2 penalty + dependency penalty,
    plus a pairwise penalty for pairs that exceed the maintenance window."""
    max_r = max(c["reward"] for c in candidates)
    pen = round(2 * max_r + 1, 4)
    pairs_over = [(a["id"], b["id"]) for a, b in itertools.combinations(candidates, 2)
                  if a["minutes"] + b["minutes"] > max_minutes]
    return {"penalty": pen, "capacity": capacity, "deps": deps, "pairs_over_window": pairs_over,
            "rewards": {c["id"]: c["reward"] for c in candidates}}


def wave0_energy(sel: Dict[str, int], terms: Dict[str, Any]) -> Tuple[float, bool, List[str]]:
    r, P = terms["rewards"], terms["penalty"]
    count = sum(sel.values())
    e = -sum(r[k] * v for k, v in sel.items()) + P * (count - terms["capacity"]) ** 2
    viol = []
    for up, down in terms["deps"]:
        if sel.get(down) and not sel.get(up):
            e += P
            viol.append(f"{down} without upstream {up}")
    for a, b in terms["pairs_over_window"]:
        if sel.get(a) and sel.get(b):
            e += P
            viol.append(f"{a}+{b} exceed window")
    if count > terms["capacity"]:
        viol.append("capacity exceeded")
    return round(e, 4), not viol, viol


def run_wave0_qaoa(candidates: List[Dict[str, Any]], deps: List[Tuple[str, str]], capacity: int,
                   max_minutes: int, shots: int = SHOTS) -> Dict[str, Any]:
    """Compile with QUBOProblem.from_model, build QAOA(reps=1) at fixed angles, sample on QpiAI-QSV-Local."""
    from qpiai_opt.opt_modeller import Binary, Model
    from qpiai_opt.opt_solvers import inspect as q_inspect
    from qpiai_opt.opt_solvers.qubo import QUBOProblem
    from qpiai_opt.quantum import QAOA

    terms = wave0_qubo_terms(candidates, deps, capacity, max_minutes)
    v = {c["id"]: Binary(f"q_{c['id']}") for c in candidates}
    P = terms["penalty"]
    total = sum(v.values())
    expr = -sum(terms["rewards"][k] * v[k] for k in v) + P * ((total - capacity) * (total - capacity))
    for up, down in deps:
        expr = expr + P * (v[down] * (1 - v[up]))
    for a, b in terms["pairs_over_window"]:
        expr = expr + P * (v[a] * v[b])
    model = Model("cryptoshift_member3_wave0_qubo")
    model.minimize(expr)

    t0 = time.perf_counter()
    qubo = QUBOProblem.from_model(model)
    names = [n[2:] for n in qubo.variable_names]
    alg = QAOA(reps=1)
    info = q_inspect(qubo, algorithm=alg)
    circ = alg.build_circuit(qubo, QAOA_PARAMS, measurements=True)
    res = circ.run(shots=shots, experiment_name="CryptoShift_M3_Wave0", device_name="QpiAI-QSV-Local")
    counts = {str(k).replace(" ", ""): int(val) for k, val in dict(res.counts).items()}
    runtime = time.perf_counter() - t0

    def decode(bits: str) -> Dict[str, int]:  # little-endian: variable i at position len-1-i
        return {names[i]: int(bits[len(bits) - 1 - i]) for i in range(len(names))}

    exact = []
    for combo in itertools.product((0, 1), repeat=len(names)):
        sel = dict(zip(names, combo))
        e, ok, _ = wave0_energy(sel, terms)
        exact.append((e, ok, sorted(k for k, x in sel.items() if x)))
    exact.sort(key=lambda t: t[0])
    opt_e, _, opt_sel = exact[0]
    opt_bits = "".join(str(int(n in opt_sel)) for n in reversed(names))

    sampled = []
    for bits, cnt in counts.items():
        sel = decode(bits)
        e, ok, _ = wave0_energy(sel, terms)
        sampled.append({"bits": bits, "count": cnt, "selection": sorted(k for k, x in sel.items() if x),
                        "energy": e, "feasible": ok})
    sampled.sort(key=lambda s: -s["count"])
    feasible = [s for s in sampled if s["feasible"]]
    best = min(feasible, key=lambda s: s["energy"]) if feasible else None
    total_shots = sum(counts.values())
    return {
        "label": "SIMULATOR (QpiAI-QSV-Local, in-process statevector; not a QPU)",
        "formulation": {"variables": names, **terms},
        "algorithm": "QAOA(reps=1), fixed angles (no variational optimisation)", "angles": QAOA_PARAMS,
        "backend": "QpiAI-QSV-Local", "shots": shots, "seed": "not exposed by Circuit.run for QpiAI-QSV-Local",
        "circuit": {"depth": int(circ.depth()), "size": int(circ.size())},
        "inspect": info if isinstance(info, dict) else str(info),
        "exact_optimum": {"selection": opt_sel, "energy": opt_e, "bits": opt_bits},
        "samples": sampled,
        "most_frequent_sample": sampled[0] if sampled else None,
        "best_feasible_sample": best,
        "optimum_probability": round(counts.get(opt_bits, 0) / total_shots, 4) if total_shots else 0.0,
        "uniform_probability": round(1 / 2 ** len(names), 4),
        "distinct_bitstrings_sampled": len(counts),
        "feasible_shot_fraction": round(sum(s["count"] for s in feasible) / total_shots, 4) if total_shots else 0.0,
        "runtime_seconds": round(runtime, 4),
    }


def reproduce_reported_experiment() -> Dict[str, Any]:
    """Run the existing experiment unchanged (offline) and check the reported -13.07 energy."""
    from cryptoshift.optimization.qcloud_experiment import run_qcloud_wave0_qubo_experiment

    t0 = time.perf_counter()
    r = run_qcloud_wave0_qubo_experiment(allow_online_auth=False)
    return {
        "label": "SIMULATOR reproduction of the existing module (code unchanged)",
        "local_qsv_simulator_status": r.get("local_qsv_simulator_status"),
        "best_simulator_wave0_selection": r.get("best_simulator_wave0_selection"),
        "best_simulator_wave0_energy": r.get("best_simulator_wave0_energy"),
        "reported_energy": -13.07,
        "reproduced": r.get("best_simulator_wave0_energy") == -13.07,
        "top_counts": r.get("local_simulator_top_counts"),
        "circuit_metrics": {k: r.get("circuit_metrics", {}).get(k) for k in ("qubits", "depth", "size")},
        "runtime_seconds": round(time.perf_counter() - t0, 4),
        "caveats": [
            "The existing module reads measurement strings left-to-right as variables 0..3; the simulator is "
            "little-endian (measured), so its service labels per bitstring are reversed.",
            "Its metric is the best feasible energy among sampled bitstrings; with 1024 shots over 16 bitstrings "
            "almost every bitstring is sampled, so this finds the analytic optimum regardless of QAOA quality.",
        ],
    }

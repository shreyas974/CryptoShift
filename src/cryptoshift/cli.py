"""Canonical command-line interface for CryptoShift (PQC-01) under `src/cryptoshift/cli.py`."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Any, Dict, List

from cryptoshift.dependencies import validate_dependency_order
from cryptoshift.metrics import compute_migration_metrics, evaluate_labelled_dataset
from cryptoshift.models import WaveScheduleConfig
from cryptoshift.optimization.auth_check import (
    PROJECT_ROOT,
    check_credentials_status,
    run_full_auth_and_smoke_checks,
)
from cryptoshift.optimization.fallback_scheduler import solve_with_fallback_scheduler
from cryptoshift.optimization.qcloud_experiment import run_qcloud_wave0_qubo_experiment
from cryptoshift.optimization.qpiai_opt_adapter import solve_with_qpiai_opt
from cryptoshift.proposals import generate_migration_proposals
from cryptoshift.protocol_demo import run_hybrid_protocol_demo
from cryptoshift.reporting import write_evaluation_reports, write_qpiai_evidence_reports
from cryptoshift.rollback import evaluate_rollbacks
from cryptoshift.scanner import scan_banking_services
from cryptoshift.scoring import build_migration_tasks
from cryptoshift.verification import run_verification_gates


def init_local_env_file() -> Path:
    """Create `.env` from `.env.example` if `.env` does not exist yet (never overwrites existing `.env`)."""
    env_path = PROJECT_ROOT / ".env"
    example_path = PROJECT_ROOT / ".env.example"
    if not env_path.exists() and example_path.exists():
        shutil.copyfile(example_path, env_path)
    return env_path


def build_complete_evidence_bundle(allow_online_auth: bool = False) -> Dict[str, Any]:
    """Run all CryptoShift + QpiAI checks and return a non-sensitive evidence dictionary."""
    smoke = run_full_auth_and_smoke_checks(allow_online_auth=allow_online_auth)
    findings = scan_banking_services()
    tasks = build_migration_tasks()
    cfg = WaveScheduleConfig()

    fallback_res = solve_with_fallback_scheduler(tasks, cfg)
    opt_res, opt_meta = solve_with_qpiai_opt(tasks, cfg, allow_online_auth=allow_online_auth)
    qcloud_meta = run_qcloud_wave0_qubo_experiment(allow_online_auth=allow_online_auth)

    active_schedule = opt_res if opt_res.status == "run successfully" else fallback_res
    dep_ok, dep_violations = validate_dependency_order(tasks, active_schedule.task_to_wave)
    proposals = generate_migration_proposals(tasks, active_schedule.task_to_wave)
    gates = run_verification_gates(tasks, active_schedule.task_to_wave, findings=findings)
    rollbacks = evaluate_rollbacks(tasks, gates)
    protocol_demo = run_hybrid_protocol_demo()
    metrics = compute_migration_metrics(findings, tasks, active_schedule, gates)

    components = [
        {
            "name": "Deterministic Dependency-Aware Fallback Scheduler",
            "status": fallback_res.status,
            "execution_mode": fallback_res.execution_mode,
            "backend": "CPU Exact Combinatorial Search",
            "objective_value": fallback_res.objective_value,
            "feasible": fallback_res.feasible,
            "runtime_seconds": fallback_res.runtime_seconds,
        },
        {
            "name": "QpiAI Opt Algebraic Modeller & IR Feasibility (`qpiai-opt`)",
            "status": opt_meta.get("offline_model_status", "blocked"),
            "execution_mode": "local_ir_validation",
            "backend": "qpiai_opt.opt_modeller / opt_solvers",
            "objective_value": fallback_res.objective_value,
            "feasible": bool(opt_meta.get("baseline_feasible_in_opt_ir", True)),
            "runtime_seconds": opt_res.runtime_seconds,
        },
        {
            "name": "QpiAI Opt Authenticated Local Solver (`solve(mode='local')`)",
            "status": opt_meta.get("online_solve_status", "not attempted"),
            "execution_mode": "local",
            "backend": "qpiai_opt.opt_solvers.solve (mode='local')",
            "objective_value": opt_res.objective_value if opt_res.status == "run successfully" else None,
            "feasible": opt_res.feasible,
            "runtime_seconds": opt_res.runtime_seconds,
        },
        {
            "name": "QpiAI Quantum 4-Qubit Wave-0 QUBO & QAOA Circuit (`build_circuit`)",
            "status": qcloud_meta.get("circuit_construction_status", "blocked"),
            "execution_mode": "local_circuit_build",
            "backend": "qpiai_opt.quantum.QAOA",
            "objective_value": qcloud_meta.get("best_simulator_wave0_energy"),
            "feasible": True,
            "runtime_seconds": qcloud_meta.get("runtime_seconds", 0.0),
        },
        {
            "name": "QpiAI Quantum Local Statevector Simulator (`QpiAI-QSV-Local`)",
            "status": qcloud_meta.get("local_qsv_simulator_status", "blocked"),
            "execution_mode": "local_simulator",
            "backend": "QpiAI-QSV-Local",
            "objective_value": qcloud_meta.get("best_simulator_wave0_energy"),
            "feasible": True,
            "runtime_seconds": qcloud_meta.get("runtime_seconds", 0.0),
        },
        {
            "name": "QpiAI QCloud Authenticated Variational QAOA (`solve(..., mode='local')`)",
            "status": qcloud_meta.get("authenticated_qaoa_status", "not attempted"),
            "execution_mode": "local_simulator_authenticated",
            "backend": "QpiAIQuantumAuth + QpiAI-QSV-Local",
            "objective_value": qcloud_meta.get("authenticated_qaoa_result", {}).get("objective"),
            "feasible": True,
            "runtime_seconds": qcloud_meta.get("runtime_seconds", 0.0),
        },
    ]

    evidence = {
        "environment": smoke["environment"],
        "packages": smoke["packages"],
        "credentials": smoke["credentials"],
        "components": components,
        "problem_instance": {
            "scope": "Synthetic Banking Fixture (`demo_bank_app/services.py` — 6 services, 13 findings)",
            "config": cfg.to_dict(),
            "services": [t.to_dict() for t in tasks],
            "findings": [f.to_dict() for f in findings],
        },
        "fallback_schedule": fallback_res.to_dict(),
        "qpiai_opt": opt_meta,
        "qpiai_qcloud": qcloud_meta,
        "verification_and_migration": {
            "dependency_order_valid": dep_ok,
            "dependency_violations": dep_violations,
            "metrics": metrics,
            "proposals": proposals,
            "verification_gates": [g.to_dict() for g in gates],
            "rollback_events": [r.to_dict() for r in rollbacks],
            "hybrid_protocol_demo": protocol_demo,
        },
        "limitations": [
            "By default, `cryptoshift` runs in safe offline verification mode (`allow_online_auth=False`) so no online key-validation network requests are sent unless `--online-auth` is explicitly passed.",
            "Direct `qpiai_quantum.Circuit.run(device_name='QpiAI-QSV-Local')`, `QUBOProblem.from_model()`, `build_circuit()`, `classify()`, `inspect()`, and `feasibility()` execute 100% locally without network calls or credentials.",
            "All quantum circuit results reported here come from the classical statevector simulator (`QpiAI-QSV-Local`), NOT a physical QPU, and do not demonstrate quantum speedup or production quantum advantage.",
            "The protocol envelope trace is an explicitly labelled mocked/modelled trace combining real `hashlib` SHA-1/SHA3-256 digests with analytical NIST FIPS 203/204 wire-size parameters.",
            "Platform mode (`mode='platform'`), `submit()`, and remote QPUs (`QpiAI-Indus-1`) are disabled to prevent unintended credit consumption.",
        ],
    }
    return evidence


def cmd_check_auth(allow_online_auth: bool = False) -> int:
    """Run safe credential and local solver/simulator checks without printing any secret values."""
    init_local_env_file()
    creds = check_credentials_status()
    smoke = run_full_auth_and_smoke_checks(allow_online_auth=allow_online_auth)

    print("=== CryptoShift: QpiAI Credential & SDK Local Check ===")
    print(f"Python Runtime     : {smoke['environment']['python_version']} ({smoke['environment']['virtualenv_name']})")
    print(f"Online Auth Check  : {'ENABLED (--online-auth)' if allow_online_auth else 'SKIPPED (safe offline mode)'}")
    print("")
    print("1. Installed Official Packages:")
    for name, info in smoke["packages"].items():
        print(f"   - {name:20s}: {info['distribution']} == {info['version']} [{info['status']}]")
    print("")
    print("2. Credential Configuration Status (Secrets Never Printed):")
    for var_name, c_info in creds.items():
        print(f"   - {var_name:22s}: {c_info['configuration_status']} (Portal: {c_info['portal']})")
    print("")
    print("3. QpiAI Opt Local Check (`mode='local'` only):")
    print(f"   - Offline Modeller   : {smoke['opt_local_smoke_check']['offline_modeller_status']}")
    print(f"   - Online Auth Check  : {smoke['opt_local_smoke_check']['auth_verification_status']}")
    print(f"   - Detail             : {smoke['opt_local_smoke_check']['message']}")
    print("")
    print("4. QpiAI QCloud / Quantum SDK Local Check (`QpiAI-QSV-Local` only):")
    print(f"   - Online Auth Check  : {smoke['qcloud_local_smoke_check']['auth_verification_status']}")
    print(f"   - Local Simulator    : {smoke['qcloud_local_smoke_check']['local_simulator_status']}")
    print(f"   - Sample Counts      : {smoke['qcloud_local_smoke_check'].get('sample_counts', {})}")
    return 0


def cmd_evaluate() -> int:
    """Evaluate the detector on the documented synthetic fixture dataset and write `reports/evaluation/`."""
    eval_data = evaluate_labelled_dataset(PROJECT_ROOT)
    paths = write_evaluation_reports(eval_data, PROJECT_ROOT / "reports" / "evaluation")
    counts = eval_data.get("counts", {})
    metrics = eval_data.get("metrics", {})
    print("=== CryptoShift: Labelled Synthetic Fixture Evaluation ===")
    print(f"Total Instances    : {eval_data.get('total_instances', 0)}")
    print(
        f"Confusion Counts   : TP={counts.get('TP', 0)}, FP={counts.get('FP', 0)}, "
        f"FN={counts.get('FN', 0)}, TN={counts.get('TN', 0)}"
    )
    print(f"Precision          : {metrics.get('precision', 0.0):.4f}")
    print(f"Recall             : {metrics.get('recall', 0.0):.4f}")
    print("Evaluation reports written to:")
    print(f"  - JSON     : {Path(paths['json']).relative_to(PROJECT_ROOT)}")
    print(f"  - Markdown : {Path(paths['markdown']).relative_to(PROJECT_ROOT)}")
    return 0


def cmd_demo(allow_online_auth: bool = False) -> int:
    """Run the full CryptoShift PQC-01 migration, QpiAI scheduling, and dataset evaluation workflow."""
    init_local_env_file()
    evidence = build_complete_evidence_bundle(allow_online_auth=allow_online_auth)
    report_paths = write_qpiai_evidence_reports(evidence, PROJECT_ROOT / "reports" / "qpiai")
    eval_data = evaluate_labelled_dataset(PROJECT_ROOT)
    eval_paths = write_evaluation_reports(eval_data, PROJECT_ROOT / "reports" / "evaluation")

    print("=== CryptoShift (PQC-01): Verification-Gated Cryptographic Migration ===")
    print(f"Services Scanned   : {evidence['verification_and_migration']['metrics']['total_services']}")
    print(f"Crypto Findings    : {evidence['verification_and_migration']['metrics']['total_crypto_findings']}")
    print("")
    print("--- Migration-Wave Schedule (Deterministic Baseline vs. QpiAI) ---")
    for wave_idx, svc_list in evidence["fallback_schedule"]["waves"].items():
        print(f"  Wave {wave_idx}: {', '.join(svc_list)}")
    print(f"  Objective Value  : {evidence['fallback_schedule']['objective_value']}")
    print(f"  Opt IR Feasible  : {evidence['qpiai_opt']['baseline_feasible_in_opt_ir']}")
    print(f"  Opt Local Solve  : {evidence['qpiai_opt']['online_solve_status']}")
    print(f"  QAOA Local Sim   : {evidence['qpiai_qcloud']['local_qsv_simulator_status']}")
    print(
        f"  QAOA Wave-0 Pick : {evidence['qpiai_qcloud'].get('best_simulator_wave0_selection', [])} "
        f"(energy={evidence['qpiai_qcloud'].get('best_simulator_wave0_energy')})"
    )
    print("")
    print("--- Verification Gates & Rollback Readiness ---")
    for gate in evidence["verification_and_migration"]["verification_gates"]:
        status_str = "PASS" if gate["overall_passed"] else "ROLLBACK"
        print(f"  [Wave {gate['wave_index']}] {gate['service_id']:18s}: {status_str} - {gate['details']}")
    print("")
    print("--- Labelled Synthetic Fixture Detection Evaluation ---")
    c = eval_data.get("counts", {})
    m = eval_data.get("metrics", {})
    print(
        f"  TP={c.get('TP', 0)}, FP={c.get('FP', 0)}, FN={c.get('FN', 0)}, TN={c.get('TN', 0)} | "
        f"Precision={m.get('precision', 0.0):.4f}, Recall={m.get('recall', 0.0):.4f}"
    )
    print("")
    print("Evidence reports written to:")
    print(f"  - QpiAI JSON : {Path(report_paths['json']).relative_to(PROJECT_ROOT)}")
    print(f"  - QpiAI MD   : {Path(report_paths['markdown']).relative_to(PROJECT_ROOT)}")
    print(f"  - Eval JSON  : {Path(eval_paths['json']).relative_to(PROJECT_ROOT)}")
    print(f"  - Eval MD    : {Path(eval_paths['markdown']).relative_to(PROJECT_ROOT)}")
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cryptoshift",
        description="CryptoShift (PQC-01): Verification-Gated Cryptographic Migration & QpiAI Wave Scheduler",
    )
    parser.add_argument(
        "--online-auth",
        action="store_true",
        help="Authorize online API key validation for local QpiAI Opt solving and QCloud login (disabled by default)",
    )
    sub = parser.add_subparsers(dest="command")

    p_auth = sub.add_parser(
        "check-auth",
        help="Verify QpiAI credentials ('key configured' / 'key missing') & local SDK checks",
    )
    p_auth.add_argument("--online-auth", action="store_true", help="Authorize online key validation check")

    sub.add_parser("init-env", help="Create a git-ignored local .env file from .env.example if missing")

    p_sched = sub.add_parser("schedule", help="Run migration-wave scheduling comparison and write reports/qpiai/")
    p_sched.add_argument("--online-auth", action="store_true", help="Authorize online key validation check")

    sub.add_parser("evaluate", help="Run detection evaluation on labelled synthetic fixtures and write reports/evaluation/")

    p_demo = sub.add_parser(
        "demo",
        help="Run full CryptoShift PQC-01 discovery, scheduling, verification, evaluation, and reporting",
    )
    p_demo.add_argument("--online-auth", action="store_true", help="Authorize online key validation check")

    args = parser.parse_args(argv)
    online_flag = bool(getattr(args, "online_auth", False))

    if args.command == "check-auth":
        return cmd_check_auth(allow_online_auth=online_flag)
    if args.command == "init-env":
        path = init_local_env_file()
        print(f"Local credential file ready at: {path.name} (git-ignored). Open it locally and paste your API keys.")
        return 0
    if args.command == "evaluate":
        return cmd_evaluate()
    if args.command in ("schedule", "demo", None):
        return cmd_demo(allow_online_auth=online_flag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


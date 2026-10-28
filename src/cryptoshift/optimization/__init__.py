"""Canonical QpiAI Opt, QpiAI QCloud (Quantum SDK), and deterministic fallback optimization modules."""

from cryptoshift.optimization.auth_check import (
    PROJECT_ROOT,
    check_credentials_status,
    get_installed_package_versions,
    load_project_env_files,
    redact_secrets,
    run_full_auth_and_smoke_checks,
)
from cryptoshift.optimization.fallback_scheduler import (
    compute_schedule_objective,
    is_schedule_feasible,
    solve_with_fallback_scheduler,
)
from cryptoshift.optimization.qcloud_experiment import (
    evaluate_wave0_qubo_bitstring,
    run_qcloud_wave0_qubo_experiment,
)
from cryptoshift.optimization.qpiai_opt_adapter import (
    build_qpiai_opt_wave_model,
    solve_with_qpiai_opt,
)

__all__ = [
    "PROJECT_ROOT",
    "check_credentials_status",
    "get_installed_package_versions",
    "load_project_env_files",
    "redact_secrets",
    "run_full_auth_and_smoke_checks",
    "compute_schedule_objective",
    "is_schedule_feasible",
    "solve_with_fallback_scheduler",
    "build_qpiai_opt_wave_model",
    "solve_with_qpiai_opt",
    "evaluate_wave0_qubo_bitstring",
    "run_qcloud_wave0_qubo_experiment",
]

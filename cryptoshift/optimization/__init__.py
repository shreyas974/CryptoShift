"""QpiAI Opt, QpiAI QCloud (Quantum SDK), and deterministic fallback optimization modules for CryptoShift."""

from cryptoshift.optimization.auth_check import (
    check_credentials_status,
    load_project_env_files,
    redact_secrets,
    run_full_auth_and_smoke_checks,
)
from cryptoshift.optimization.fallback_scheduler import (
    compute_schedule_objective,
    solve_with_fallback_scheduler,
)
from cryptoshift.optimization.qcloud_experiment import run_qcloud_wave0_qubo_experiment
from cryptoshift.optimization.qpiai_opt_adapter import solve_with_qpiai_opt

__all__ = [
    "check_credentials_status",
    "load_project_env_files",
    "redact_secrets",
    "run_full_auth_and_smoke_checks",
    "compute_schedule_objective",
    "solve_with_fallback_scheduler",
    "solve_with_qpiai_opt",
    "run_qcloud_wave0_qubo_experiment",
]


"""Deterministic dependency-aware fallback scheduler (`src/cryptoshift/optimization/fallback_scheduler.py`)."""

from cryptoshift.optimization.fallback_scheduler import (
    compute_schedule_objective,
    is_schedule_feasible,
    solve_with_fallback_scheduler,
)

__all__ = [
    "compute_schedule_objective",
    "is_schedule_feasible",
    "solve_with_fallback_scheduler",
]

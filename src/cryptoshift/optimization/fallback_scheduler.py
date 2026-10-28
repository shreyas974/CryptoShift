"""Deterministic dependency-aware fallback scheduler for CryptoShift migration waves."""

from __future__ import annotations

import itertools
import time
from typing import Dict, List, Optional, Tuple

from cryptoshift.models import MigrationTask, WaveScheduleConfig, WaveScheduleResult


def compute_schedule_objective(
    tasks: List[MigrationTask],
    task_to_wave: Dict[str, int],
    config: WaveScheduleConfig,
) -> float:
    """Compute the exact linear objective: sum_s (rollout_cost_s + alpha * risk_score_s * wave_s)."""
    total = 0.0
    for task in tasks:
        w = task_to_wave[task.service_id]
        total += task.rollout_cost + config.risk_delay_weight * task.risk_score * w
    return round(total, 4)


def is_schedule_feasible(
    tasks: List[MigrationTask],
    task_to_wave: Dict[str, int],
    config: WaveScheduleConfig,
) -> Tuple[bool, List[str]]:
    """Check all constraints: assignment, dependencies, wave capacity, duration budget, verification gate."""
    violations: List[str] = []
    waves_count: Dict[int, int] = {w: 0 for w in range(config.num_waves)}
    waves_duration: Dict[int, int] = {w: 0 for w in range(config.num_waves)}

    for task in tasks:
        if task.service_id not in task_to_wave:
            violations.append(f"Unassigned service: {task.service_id}")
            continue
        w = task_to_wave[task.service_id]
        if w < 0 or w >= config.num_waves:
            violations.append(f"Invalid wave {w} for {task.service_id}")
            continue
        waves_count[w] += 1
        waves_duration[w] += task.duration_minutes

        if config.enforce_verification_gate and not task.verification_ready_wave0 and w == 0:
            violations.append(f"Service '{task.service_id}' is not verification-ready for Wave 0.")

        for dep in task.dependencies:
            w_dep = task_to_wave.get(dep, 999)
            if w_dep > w:
                violations.append(f"Dependency violation: {dep} (W{w_dep}) > {task.service_id} (W{w}).")

    for w in range(config.num_waves):
        if waves_count[w] > config.max_services_per_wave:
            violations.append(
                f"Wave {w} exceeds max services ({waves_count[w]} > {config.max_services_per_wave})."
            )
        if waves_duration[w] > config.max_minutes_per_wave:
            violations.append(
                f"Wave {w} exceeds maintenance window ({waves_duration[w]}m > {config.max_minutes_per_wave}m)."
            )

    return (len(violations) == 0, violations)


def solve_with_fallback_scheduler(
    tasks: List[MigrationTask],
    config: Optional[WaveScheduleConfig] = None,
) -> WaveScheduleResult:
    """Solve the constrained migration-wave scheduling problem deterministically."""
    cfg = config or WaveScheduleConfig()
    start = time.perf_counter()

    best_obj: Optional[float] = None
    best_assignment: Optional[Dict[str, int]] = None
    feasible_count = 0
    total_evaluated = 0

    service_ids = [t.service_id for t in tasks]
    for wave_tuple in itertools.product(range(cfg.num_waves), repeat=len(tasks)):
        total_evaluated += 1
        candidate = dict(zip(service_ids, wave_tuple))
        ok, _ = is_schedule_feasible(tasks, candidate, cfg)
        if not ok:
            continue
        feasible_count += 1
        obj = compute_schedule_objective(tasks, candidate, cfg)
        if best_obj is None or obj < best_obj:
            best_obj = obj
            best_assignment = candidate

    elapsed = time.perf_counter() - start
    if best_assignment is None or best_obj is None:
        return WaveScheduleResult(
            solver_name="Deterministic Dependency-Aware Fallback Scheduler",
            status="run successfully",
            execution_mode="deterministic_local",
            feasible=False,
            objective_value=None,
            task_to_wave={},
            waves={w: [] for w in range(cfg.num_waves)},
            runtime_seconds=round(elapsed, 6),
            diagnostics={
                "method": "exact_constrained_combinatorial_search",
                "candidates_evaluated": total_evaluated,
                "feasible_schedules_found": 0,
            },
            limitations=["No feasible wave assignment satisfies the given capacity/window constraints."],
        )

    waves: Dict[int, List[str]] = {w: [] for w in range(cfg.num_waves)}
    for sid, w in sorted(best_assignment.items(), key=lambda kv: (kv[1], kv[0])):
        waves[w].append(sid)

    return WaveScheduleResult(
        solver_name="Deterministic Dependency-Aware Fallback Scheduler",
        status="run successfully",
        execution_mode="deterministic_local",
        feasible=True,
        objective_value=best_obj,
        task_to_wave=best_assignment,
        waves=waves,
        runtime_seconds=round(elapsed, 6),
        diagnostics={
            "method": "exact_constrained_combinatorial_search",
            "candidates_evaluated": total_evaluated,
            "feasible_schedules_found": feasible_count,
            "optimality_guarantee": "exact_discrete_optimum_for_6_services",
        },
        limitations=[
            "Deterministic CPU combinatorial search; suitable for small/medium service graphs as a reliable baseline."
        ],
    )

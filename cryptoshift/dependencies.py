"""Dependency graph utilities and topological validation for CryptoShift service migrations."""

from __future__ import annotations

from typing import Dict, List, Tuple

from cryptoshift.models import MigrationTask


def build_dependency_edges(tasks: List[MigrationTask]) -> List[Tuple[str, str]]:
    """Return directed edges (upstream, downstream) where upstream must migrate no later than downstream."""
    edges: List[Tuple[str, str]] = []
    for task in tasks:
        for dep in task.dependencies:
            edges.append((dep, task.service_id))
    return edges


def validate_dependency_order(tasks: List[MigrationTask], task_to_wave: Dict[str, int]) -> Tuple[bool, List[str]]:
    """Verify that every upstream dependency is scheduled in the same or an earlier wave."""
    violations: List[str] = []
    for task in tasks:
        w_down = task_to_wave.get(task.service_id)
        if w_down is None:
            violations.append(f"Service '{task.service_id}' is not assigned to any wave.")
            continue
        for dep in task.dependencies:
            w_up = task_to_wave.get(dep)
            if w_up is None:
                violations.append(f"Upstream dependency '{dep}' for '{task.service_id}' is unassigned.")
            elif w_up > w_down:
                violations.append(
                    f"Dependency violation: '{dep}' (wave {w_up}) must be migrated no later than "
                    f"'{task.service_id}' (wave {w_down})."
                )
    return (len(violations) == 0, violations)

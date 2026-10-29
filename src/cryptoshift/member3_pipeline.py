"""Member 3 end-to-end pipeline: inventory -> tasks -> dependency graph -> score -> schedule -> gates ->
approval status -> rollback record -> report bundle (JSON + Markdown).

Never approves anything; approval status is read from the approvals store written by the human-run
`scripts/approve_plan.py`.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from cryptoshift.gates.approval import approval_status
from cryptoshift.gates.verification_gates import EVIDENCE_SCOPE, evaluate_plan
from cryptoshift.optimization.auth_check import PROJECT_ROOT
from cryptoshift.planning.planner import DEFAULT_TARGET, build_problem, plan_hash, problem_to_json, schedule, sensitivity

DERIVED = PROJECT_ROOT / "scratch" / "derived" / "member3"
REPORTS = PROJECT_ROOT / "reports" / "member3"
APPROVALS = DERIVED / "approvals.json"
EVIDENCE = DERIVED / "verification_evidence.json"
SCHED_CMP = DERIVED / "scheduling_comparison.json"
SCHEMA_VERSION = "member3-plan/1.0"


def rollback_record(ev: Dict[str, Any], steps: list) -> Dict[str, Any]:
    r = ev.get("rollback_rehearsal") or {}
    return {
        "label": "Rollback plan; rehearsed on a temporary COPY (TEST SCENARIO)",
        "profile": r.get("profile"),
        "restore": f"restore the profile copy from snapshot sha256:{r.get('snapshot_sha256')}",
        "snapshot_sha256": r.get("snapshot_sha256"),
        "trigger": r.get("trigger"),
        "recovery_check": "re-run the classical handshake against the restored profile; success required",
        "rehearsal_result": {k: r.get(k) for k in ("forced_failure_detected", "restored_hash_matches_snapshot",
                                                    "recovered", "originals_unchanged")},
        "recovery_command": (r.get("recovery_check") or {}).get("command"),
        "warnings": r.get("warnings", []) + [
            "Never restore SHA-1 or 3DES configurations as a rollback target; fall back to SHA-256 / AES-256-GCM classical baselines."],
        "applies_to_steps": [s["step_id"] for s in steps],
    }


def run(target: Optional[Path] = None, evidence: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    problem = build_problem(target or DEFAULT_TARGET)
    sched = schedule(problem)
    sens = sensitivity(problem)
    if evidence is None:
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8")) if EVIDENCE.is_file() else {}
    steps = evaluate_plan(problem["services"], evidence)
    pj = problem_to_json(problem)
    plan: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status_labels": {
            "inventory": "VERIFIED on SYNTHETIC demo configs", "risk_score": "PROVISIONAL, UNVALIDATED",
            "schedule": "VERIFIED (deterministic exact search; constraints are ASSUMPTIONS)",
            "gates": "VERIFIED loopback evidence; " + EVIDENCE_SCOPE, "approval": "human-only",
        },
        **pj,
        "schedule": {k: sched[k] for k in ("feasible", "objective", "task_to_wave", "waves", "config",
                                           "dependency_violations", "constraint_violations", "dependencies_outside_task_set")},
        "schedule_run": {k: sched[k] for k in ("solver", "runtime_seconds", "diagnostics")},
        "sensitivity": {k: sens[k] for k in ("base_rank", "n_runs", "rank_changed_runs", "schedule_changed_runs", "min_kendall_tau")},
        "steps": steps,
        "verification_evidence_ref": "scratch/derived/member3/verification_evidence.json" if evidence else None,
        "rollback": rollback_record(evidence, steps),
    }
    if SCHED_CMP.is_file():
        cmp_ = json.loads(SCHED_CMP.read_text(encoding="utf-8"))
        plan["scheduler_comparison"] = {
            "baseline": {k: cmp_["baseline"][k] for k in ("objective", "waves", "runtime_seconds")},
            "qpiai_opt": {k: cmp_["qpiai_opt"][k] for k in ("sdk_versions", "problem_class", "binary_variables", "constraints",
                                                            "baseline_feasible_in_opt_model", "authenticated_local_solve")},
            "qaoa_simulator": {k: cmp_["qaoa_phase2_wave0"][k] for k in ("label", "exact_optimum", "optimum_probability",
                                                                          "uniform_probability", "feasible_shot_fraction")},
            "wave0": cmp_["wave0_comparison"],
        }
    plan["plan_hash"] = plan_hash(plan)
    plan["approval"] = approval_status(plan, APPROVALS)
    return plan


def to_markdown(plan: Dict[str, Any]) -> str:
    s = plan["schedule"]
    L = ["# Member 3 migration plan (generated)", "",
         f"Generated {plan['generated_at_utc']} from `{plan['target']}` (SYNTHETIC demo bank). Plan hash `{plan['plan_hash'][:16]}`.", "",
         "## Services", "", "| Service | Evidence | Findings | Risk (provisional) | Wave | Gate state | Blocking |", "|---|---|---|---|---|---|---|"]
    steps = {x["service_id"]: x for x in plan["steps"]}
    for sid, v in sorted(plan["services"].items()):
        st = steps[sid]
        L.append(f"| {sid} | {v['evidence_source']} | {len(v['finding_ids'])} | {v['risk']['score']} | "
                 f"{s['task_to_wave'].get(sid)} | {st['state']} | {', '.join(st['blocking_gates']) or '-'} |")
    ga = plan["graph_analysis"]
    L += ["", "## Schedule", "", f"Objective {s['objective']}; waves {s['waves']}; dependency violations {len(s['dependency_violations'])}.",
          f"Sensitivity: rank changed in {plan['sensitivity']['rank_changed_runs']}/{plan['sensitivity']['n_runs']} weight perturbations, "
          f"schedule changed in {plan['sensitivity']['schedule_changed_runs']}/{plan['sensitivity']['n_runs']}.", "",
          "## Dependency graph", "", f"Edges by provenance {ga['edge_counts']}; cycles {ga['cycles'] or 'none'}; conflicts {len(ga['conflicts'])}.", ""]
    for c in ga["conflicts"]:
        L.append(f"- {c['upstream']} -> {c['downstream']}: {c['issue']}")
    rb = plan["rollback"]
    L += ["", "## Rollback", "", f"{rb['restore']}; rehearsal {rb['rehearsal_result']}.", *[f"- WARNING: {w}" for w in rb["warnings"]],
          "", "## Approval", "", f"Approved steps: {plan['approval']['approved_steps'] or 'none'} (human-only CLI).", "",
          f"Scope: {EVIDENCE_SCOPE}", ""]
    return "\n".join(L)


def write(plan: Dict[str, Any], reports_dir: Path = REPORTS, derived_dir: Path = DERIVED) -> Dict[str, Path]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (derived_dir / "bundle").mkdir(parents=True, exist_ok=True)
    out = {"bundle": derived_dir / "bundle" / "plan.json", "report_json": reports_dir / "plan.json",
           "report_md": reports_dir / "plan.md"}
    text = json.dumps(plan, indent=2, default=str)
    out["bundle"].write_text(text, encoding="utf-8")
    out["report_json"].write_text(text, encoding="utf-8")
    out["report_md"].write_text(to_markdown(plan), encoding="utf-8")
    return out

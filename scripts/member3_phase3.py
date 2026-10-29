#!/usr/bin/env python3
"""Phase 3: deterministic baseline vs QpiAI Opt (offline checks) vs QpiAI QAOA on the local simulator.

Writes scratch/derived/member3/scheduling_comparison.json (git-ignored). No network calls; authenticated
QpiAI solving only with --authorize-local-solve AND a key in the environment (never platform/QPU).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from cryptoshift.optimization.member3_qpiai import (  # noqa: E402
    opt_wave_model_checks, reproduce_reported_experiment, run_wave0_qaoa,
)
from cryptoshift.planning.dependency_graph import constraint_digraph  # noqa: E402
from cryptoshift.planning.planner import build_problem, schedule, to_tasks  # noqa: E402

OUT = ROOT / "scratch" / "derived" / "member3"


def run(authorize_local_solve: bool = False) -> dict:
    problem = build_problem()
    cfg = problem["config"]
    base = schedule(problem)
    tasks, _ = to_tasks(problem)
    opt = opt_wave_model_checks(tasks, cfg["constraints"], base["task_to_wave"], authorize_local_solve)

    d = constraint_digraph(problem["graph"], cfg["enforced_edge_provenance"])
    cands = [{"id": s, "reward": v["risk"]["score"], "minutes": v["duration_minutes"]}
             for s, v in sorted(problem["services"].items()) if v["verification_ready_wave0"]]
    ids = {c["id"] for c in cands}
    deps = sorted((u, v) for u, v in d.edges if u in ids and v in ids)
    qaoa = run_wave0_qaoa(cands, deps, cfg["constraints"]["max_services_per_wave"], cfg["constraints"]["max_minutes_per_wave"])
    repro = reproduce_reported_experiment()

    opt_wave0 = None
    if opt["authenticated_local_solve"].get("status") == "RUN":
        opt_wave0 = sorted(s for s, w in opt["authenticated_local_solve"]["assignment"].items() if w == 0)
    return {
        "baseline": {k: base[k] for k in ("solver", "feasible", "objective", "waves", "runtime_seconds",
                                          "dependency_violations", "constraint_violations", "diagnostics")},
        "qpiai_opt": opt,
        "qaoa_phase2_wave0": qaoa,
        "qaoa_reproduction": repro,
        "wave0_comparison": {
            "baseline_full_schedule_wave0": sorted(base["waves"]["0"]),
            "qubo_exact_optimum_wave0": qaoa["exact_optimum"]["selection"],
            "qaoa_most_frequent_sample": qaoa["most_frequent_sample"]["selection"] if qaoa["most_frequent_sample"] else None,
            "qaoa_best_feasible_sample": qaoa["best_feasible_sample"]["selection"] if qaoa["best_feasible_sample"] else None,
            "qpiai_opt_wave0": opt_wave0 or "BLOCKED (no authenticated solve)",
            "note": "The full schedule minimises rollout_cost + alpha*risk*wave over all waves; the Wave-0 QUBO maximises risk reward "
                    "for Wave 0 alone. They are different objectives, so different Wave-0 picks are possible and are not errors.",
        },
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--authorize-local-solve", action="store_true")
    a = ap.parse_args()
    if a.authorize_local_solve:  # owner-approved 2026-10-29; key loaded into this process only, never printed
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env", override=False)
    res = run(a.authorize_local_solve)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "scheduling_comparison.json").write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    b, o, q, r = res["baseline"], res["qpiai_opt"], res["qaoa_phase2_wave0"], res["qaoa_reproduction"]
    print(f"baseline: feasible={b['feasible']} objective={b['objective']} waves={b['waves']} runtime={b['runtime_seconds']}s dep_violations={len(b['dependency_violations'])}")
    print(f"qpiai-opt {o['sdk_versions']}: class={o['problem_class']} vars={o['binary_variables']} constraints={o['constraints']} "
          f"baseline_feasible_in_model={o['baseline_feasible_in_opt_model']} solve={o['authenticated_local_solve']}")
    print(f"reproduction: status={r['local_qsv_simulator_status']} best={r['best_simulator_wave0_selection']} energy={r['best_simulator_wave0_energy']} reproduced={r['reproduced']}")
    print(f"phase2 QAOA ({q['label']}): vars={q['formulation']['variables']} exact={q['exact_optimum']} most_frequent={q['most_frequent_sample']} "
          f"P(opt)={q['optimum_probability']} vs uniform {q['uniform_probability']} feasible_shots={q['feasible_shot_fraction']} depth={q['circuit']['depth']}")
    print("wave0:", json.dumps(res["wave0_comparison"]))

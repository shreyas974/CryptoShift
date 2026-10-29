#!/usr/bin/env python3
"""End-to-end Member 3 pipeline (additive; no CLI changes): writes reports/member3/plan.{json,md} and
scratch/derived/member3/bundle/plan.json.

  .\\.venv\\Scripts\\python.exe scripts/member3_pipeline.py                    # reuse saved verification evidence
  .\\.venv\\Scripts\\python.exe scripts/member3_pipeline.py --rerun-verification
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT), str(ROOT / "scripts")]

from cryptoshift import member3_pipeline as pipe  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default=None, help="scan target (default demo_bank_app/configs)")
    ap.add_argument("--rerun-verification", action="store_true")
    a = ap.parse_args()
    ev = None
    if a.rerun_verification or not pipe.EVIDENCE.is_file():
        import member3_phase4

        ev = member3_phase4.collect()
        pipe.DERIVED.mkdir(parents=True, exist_ok=True)
        pipe.EVIDENCE.write_text(json.dumps(ev, indent=2), encoding="utf-8")
    plan = pipe.run(Path(a.path) if a.path else None, ev)
    paths = pipe.write(plan)
    print(f"plan_hash={plan['plan_hash']}")
    print("steps:", {s["service_id"]: s["state"] for s in plan["steps"]})
    print("schedule:", plan["schedule"]["waves"], "objective", plan["schedule"]["objective"])
    print("approved:", plan["approval"]["approved_steps"], "| invalidated:", len(plan["approval"]["invalidated_approvals"]))
    for k, p in paths.items():
        print(f"{k}: {p.relative_to(ROOT).as_posix()}")

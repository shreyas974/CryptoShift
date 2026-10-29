#!/usr/bin/env python3
"""HUMAN-RUN approval command. Records approver, UTC time and plan hash for READY steps only.

  .\\.venv\\Scripts\\python.exe scripts/approve_plan.py --step migrate:interbank_tls --approver "Full Name"
  .\\.venv\\Scripts\\python.exe scripts/approve_plan.py --status

Automated tools (pipeline, agent, CI) must never call this. Changing the plan afterwards invalidates approvals.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from cryptoshift import member3_pipeline as pipe  # noqa: E402
from cryptoshift.gates.approval import ApprovalError, approval_status, approve  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default=str(pipe.DERIVED / "bundle" / "plan.json"))
    ap.add_argument("--step", action="append", default=[])
    ap.add_argument("--approver", default="")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    if a.status or not a.step:
        print(json.dumps(approval_status(plan, pipe.APPROVALS), indent=2))
        sys.exit(0)
    if input(f"Approve {a.step} for plan {plan['plan_hash'][:16]} as '{a.approver}'? Type YES: ").strip() != "YES":
        print("not approved")
        sys.exit(1)
    try:
        print(json.dumps(approve(plan, a.step, a.approver, pipe.APPROVALS), indent=2))
    except ApprovalError as exc:
        print(f"refused: {exc}")
        sys.exit(2)

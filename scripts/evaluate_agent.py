#!/usr/bin/env python3
"""Run the fixed CryptoShift Assistant evaluation set; writes scratch/derived/member3/agent_eval.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from cryptoshift import member3_pipeline as pipe  # noqa: E402
from cryptoshift.agent.evaluation import evaluate  # noqa: E402

if __name__ == "__main__":
    plan = json.loads((pipe.DERIVED / "bundle" / "plan.json").read_text(encoding="utf-8"))
    res = evaluate(plan, pipe.APPROVALS)
    (pipe.DERIVED / "agent_eval.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"{res['backend']} | LLM: {res['llm_status']}")
    print(f"passed {res['passed']}/{res['n']} | by check {res['by_check']} | bundle+approvals unchanged: {res['bundle_and_approvals_unchanged']}")
    for r in res["rows"]:
        print(f"  {'PASS' if r['pass'] else 'FAIL'} [{r['check']}] {r['question']} -> {r['answer'][:110]}")

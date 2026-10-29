#!/usr/bin/env python3
"""Run the fixed CryptoShift Assistant evaluation set.

  .\\.venv\\Scripts\\python.exe scripts/evaluate_agent.py                                  # TEMPLATE_FALLBACK
  .\\.venv\\Scripts\\python.exe scripts/evaluate_agent.py --mode sarvam --credit-balance-inr N  # live Sarvam (owner-approved)
  .\\.venv\\Scripts\\python.exe scripts/evaluate_agent.py --preview                          # print the redacted payload + cost estimate, no network

Writes scratch/derived/member3/agent_eval[_sarvam].json; usage ledger scratch/derived/agent_usage.json. The key is read
from SARVAM_API_KEY at runtime and is never printed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from cryptoshift import member3_pipeline as pipe  # noqa: E402
from cryptoshift.agent.assistant import Assistant  # noqa: E402
from cryptoshift.agent.evaluation import QUESTIONS, bundle_with_fixture, evaluate  # noqa: E402
from cryptoshift.agent.sarvam import PRICE_INR_PER_M, SYSTEM_PROMPT, BudgetGuard, SarvamClient, key_configured  # noqa: E402

USAGE = ROOT / "scratch" / "derived" / "agent_usage.json"


def preview(plan: dict) -> None:
    """Exactly what would be sent for each question that reaches the cloud (no key, no network)."""
    a = Assistant(bundle_with_fixture(plan))
    client = SarvamClient()
    total_in = 0
    cloud_qs = []
    for item in QUESTIONS:
        local = a.backend.answer(item["q"])
        if local["refused"] or local["answer"].lower().startswith("unknown") or not local["citations"]:
            continue
        payload = client.payload(SYSTEM_PROMPT, json.dumps(a._evidence(item["q"], local), ensure_ascii=False))
        chars = len(json.dumps(payload, ensure_ascii=False))
        total_in += chars // 3  # conservative chars-per-token estimate
        cloud_qs.append((item["q"], payload, chars))
    q, payload, chars = cloud_qs[0]
    print("=== Example payload (question 1), exactly as it would be sent; header api-subscription-key is NOT shown ===")
    print(json.dumps(payload, indent=1, ensure_ascii=False))
    pin, pout = PRICE_INR_PER_M["sarvam-105b"]
    worst = (total_in * 2) * pin / 1e6 + (len(cloud_qs) * 2 * 400) * pout / 1e6  # every question retried once
    print(f"\nQuestions that would reach the cloud: {len(cloud_qs)} of {len(QUESTIONS)} (others answered by the local guard)")
    print(f"Estimated input tokens ~{total_in} (one attempt each); max output 400 tokens per call")
    print(f"Estimated cost: typical ~Rs {total_in * pin / 1e6 + len(cloud_qs) * 150 * pout / 1e6:.2f}, "
          f"worst case (every call retried, 400 output tokens each) ~Rs {worst:.2f} (sarvam-105b Rs {pin}/M in, Rs {pout}/M out, excl. GST)")
    print(f"Key configured: {key_configured()} (value never shown)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["template", "sarvam"], default="template")
    ap.add_argument("--credit-balance-inr", type=float, default=None)
    ap.add_argument("--max-spend-inr", type=float, default=None, help="hard spend cap for this run")
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()
    plan = json.loads((pipe.DERIVED / "bundle" / "plan.json").read_text(encoding="utf-8"))
    if a.preview:
        preview(plan)
        return 0
    kw = {}
    if a.mode == "sarvam":
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env", override=False)  # values go to os.environ of this process only; never printed
        kw = {"backend": "sarvam", "budget": BudgetGuard(USAGE, credit_balance_inr=a.credit_balance_inr,
                                                         max_spend_inr=a.max_spend_inr)}
    before = BudgetGuard(USAGE).state if USAGE.is_file() else {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0, "estimated_cost_inr": 0.0}
    res = evaluate(plan, pipe.APPROVALS, **kw)
    if a.mode == "sarvam":
        after = kw["budget"].state
        res["usage_this_run"] = {k: round(after[k] - before.get(k, 0), 6) for k in ("requests", "prompt_tokens", "completion_tokens", "estimated_cost_inr")}
    out = pipe.DERIVED / ("agent_eval_sarvam.json" if a.mode == "sarvam" else "agent_eval.json")
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"mode requested: {a.mode} | modes used: {res['modes']}")
    print(f"passed {res['passed']}/{res['n']} | by check {res['by_check']} | bundle+approvals unchanged: {res['bundle_and_approvals_unchanged']}")
    if "usage_this_run" in res:
        print(f"usage this run: {res['usage_this_run']}")
    for r in res["rows"]:
        print(f"  {'PASS' if r['pass'] else 'FAIL'} [{r['check']}] [{r['mode']}] {r['question']} -> {r['answer'][:100]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

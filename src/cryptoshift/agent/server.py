"""Local FastAPI service for the CryptoShift Assistant. Bind to 127.0.0.1 only (see scripts/run_agent.ps1).

Endpoints: GET /health, GET /tools, POST /ask {"question": "..."}. Request log lines record a hash and length of
the question, the route, citations and refusal flag; question text is redacted for secrets and truncated.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

from cryptoshift.agent.assistant import Assistant
from cryptoshift.agent.sarvam import BudgetGuard, key_configured
from cryptoshift.optimization.auth_check import PROJECT_ROOT, redact_secrets

BUNDLE = Path(os.environ.get("CRYPTOSHIFT_AGENT_BUNDLE", PROJECT_ROOT / "scratch" / "derived" / "member3" / "bundle" / "plan.json"))
LOG = PROJECT_ROOT / "scratch" / "derived" / "member3" / "agent_requests.log"

LOG.parent.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("cryptoshift.agent")
if not logger.handlers:
    h = logging.FileHandler(LOG, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)

app = FastAPI(title="CryptoShift Assistant (cloud LLM (Sarvam) with local read-only tools)")
# Cloud mode only when the owner sets CRYPTOSHIFT_AGENT_MODE=sarvam and CRYPTOSHIFT_SARVAM_CREDIT_INR (stated balance).
_MODE = os.environ.get("CRYPTOSHIFT_AGENT_MODE", "template")
_BALANCE = os.environ.get("CRYPTOSHIFT_SARVAM_CREDIT_INR")
_CUSTOM = os.environ.get("CRYPTOSHIFT_CLOUD_FOR_CUSTOM_SCANS", "off").lower() == "on"
_budget = BudgetGuard(PROJECT_ROOT / "scratch" / "derived" / "agent_usage.json",
                      credit_balance_inr=float(_BALANCE) if _BALANCE else None)
_assistant = (Assistant(json.loads(BUNDLE.read_text(encoding="utf-8")), backend=_MODE, budget=_budget,
                        cloud_for_custom_scans=_CUSTOM) if BUNDLE.is_file() else None)


class Ask(BaseModel):
    question: str


@app.get("/health")
def health() -> dict:
    cloud_ok, why = _assistant.cloud_status() if _assistant else (False, "no bundle")
    return {"status": "ok" if _assistant else "no-bundle", "label": "cloud LLM (Sarvam) with local read-only tools",
            "mode": "SARVAM_CLOUD" if cloud_ok else "TEMPLATE_FALLBACK", "mode_reason": why,
            "sarvam_key_configured": key_configured(), "cloud_for_custom_scans": _CUSTOM,
            "usage": {k: _budget.state[k] for k in ("requests", "prompt_tokens", "completion_tokens", "estimated_cost_inr")},
            "bundle_loaded": _assistant is not None}


@app.get("/tools")
def tools() -> dict:
    return {"read_only_tools": list(_assistant.tools.NAMES) if _assistant else [], "write_tools": []}


@app.post("/ask")
def ask(body: Ask) -> dict:
    if _assistant is None:
        return {"answer": "unknown: no report bundle loaded; run scripts/member3_pipeline.py", "citations": [], "refused": False}
    res = _assistant.answer(body.question)
    logger.info(json.dumps({"q_sha256": hashlib.sha256(body.question.encode()).hexdigest()[:16], "q_len": len(body.question),
                            "q_preview": redact_secrets(body.question)[:60], "tools": res["tools_used"],
                            "citations": res["citations"][:10], "refused": res["refused"], "mode": res.get("mode")}))
    return res

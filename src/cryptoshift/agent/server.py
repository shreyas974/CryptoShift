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

app = FastAPI(title="CryptoShift Assistant (local, read-only)")
_assistant = Assistant(json.loads(BUNDLE.read_text(encoding="utf-8"))) if BUNDLE.is_file() else None


class Ask(BaseModel):
    question: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok" if _assistant else "no-bundle", "backend": "template-deterministic-v1",
            "llm": "BLOCKED", "bundle_loaded": _assistant is not None}


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
                            "citations": res["citations"][:10], "refused": res["refused"]}))
    return res

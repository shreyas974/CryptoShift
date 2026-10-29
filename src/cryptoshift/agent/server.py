"""Local FastAPI service for the CryptoShift Assistant. Bind to 127.0.0.1 only (see scripts/run_agent.ps1).

Endpoints: GET /health, GET /tools, POST /ask {"question": "..."}. Request log lines record a hash and length of
the question, the route, citations and refusal flag; question text is redacted for secrets and truncated.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from cryptoshift.agent.assistant import Assistant
from cryptoshift.agent.sarvam import BudgetGuard, key_configured
from cryptoshift.datasets import (
    load_banking_pqc_observations,
    resolve_dataset_paths,
    summarize_banking_pqc_observations,
    summarize_cesnet_tls22_streaming,
)
from cryptoshift.mvp_slice import (
    DEFAULT_SQLITE_PATH,
    run_mvp_vertical_slice,
)
from cryptoshift.optimization.auth_check import PROJECT_ROOT, redact_secrets
from cryptoshift.reporting import (
    write_mvp_vertical_slice_reports,
    write_real_dataset_summary_reports,
)

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


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    html_path = PROJECT_ROOT / "src" / "cryptoshift" / "ui" / "web_frontend.html"
    if not html_path.is_file():
        raise HTTPException(status_code=404, detail="Frontend HTML not found")
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/figs/{fig_name}")
def get_fig(fig_name: str) -> FileResponse:
    safe_name = Path(fig_name).name
    for folder in (
        PROJECT_ROOT / "assets" / "diagrams" / "member3",
        PROJECT_ROOT / "scratch" / "derived" / "member3" / "figs",
    ):
        cand = folder / safe_name
        if cand.is_file() and cand.suffix.lower() == ".png":
            return FileResponse(cand, media_type="image/png")
    raise HTTPException(status_code=404, detail="Figure not found")


@app.get("/api/plan")
def get_plan() -> dict:
    plan_path = PROJECT_ROOT / "reports" / "member3" / "plan.json"
    if plan_path.is_file():
        return json.loads(plan_path.read_text(encoding="utf-8"))
    return {}


class SliceRequest(BaseModel):
    target_path: str = "demo_bank_app/configs"
    approve_all: bool = False
    approver: str = ""
    simulate_failure_service: Optional[str] = None


def _load_recent_sqlite_runs() -> list[dict]:
    if not DEFAULT_SQLITE_PATH.is_file():
        return []
    with sqlite3.connect(DEFAULT_SQLITE_PATH) as conn:
        rows = conn.execute(
            "SELECT run_id, created_at_utc, target_path, approval_status, approver, findings_count, post_patch_findings_count, gates_passed, gates_total, rollbacks_triggered FROM mvp_runs ORDER BY created_at_utc DESC LIMIT 10"
        ).fetchall()
    return [
        {
            "run_id": r[0],
            "created_at_utc": r[1],
            "target_path": r[2],
            "approval_status": r[3],
            "approver": r[4],
            "pre_findings": r[5],
            "post_findings": r[6],
            "gates": f"{r[7]}/{r[8]}",
            "rollbacks": r[9],
        }
        for r in rows
    ]


@app.get("/api/slice")
def get_default_slice() -> dict:
    target = PROJECT_ROOT / "demo_bank_app" / "configs"
    res = run_mvp_vertical_slice(
        target_path=target,
        approve_all=False,
        approver="",
        simulate_failure_service=None,
    )
    write_mvp_vertical_slice_reports(res, PROJECT_ROOT / "reports" / "runs")
    return {"slice": res, "recent_runs": _load_recent_sqlite_runs()}


@app.post("/api/slice")
def run_slice_api(body: SliceRequest) -> dict:
    cand = Path(body.target_path)
    if not cand.is_absolute():
        cand = PROJECT_ROOT / cand
    sim_svc = body.simulate_failure_service
    if sim_svc and (sim_svc.startswith("(None") or sim_svc == "none"):
        sim_svc = None
    res = run_mvp_vertical_slice(
        target_path=cand,
        approve_all=body.approve_all,
        approver=body.approver,
        simulate_failure_service=sim_svc,
    )
    write_mvp_vertical_slice_reports(res, PROJECT_ROOT / "reports" / "runs")
    return {"slice": res, "recent_runs": _load_recent_sqlite_runs()}


@app.get("/api/datasets")
def get_datasets_api(chunk_size: int = 25000, max_stream_rows: int = 50000) -> dict:
    paths = resolve_dataset_paths()
    pqc_summary = summarize_banking_pqc_observations()
    records = []
    if pqc_summary.get("status") == "verified":
        recs, _ = load_banking_pqc_observations()
        records = recs[:320]
    ces_summary = summarize_cesnet_tls22_streaming(
        chunk_size=max(1000, min(100000, int(chunk_size))),
        max_stream_rows=max(5000, min(500000, int(max_stream_rows))),
    )
    if ces_summary.get("status") == "verified":
        write_real_dataset_summary_reports(
            {
                "dataset_configuration": paths.status_dict(),
                "banking_pqc_observations": pqc_summary,
                "cesnet_tls22_s": ces_summary,
                "evaluation_separation_policy": "CESNET service labels are never used for PQC detector precision/recall.",
            },
            PROJECT_ROOT / "reports" / "datasets",
        )
    return {
        "paths": paths.status_dict(),
        "pqc_summary": pqc_summary,
        "pqc_records": records,
        "ces_summary": ces_summary,
    }

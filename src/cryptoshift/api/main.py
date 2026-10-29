"""CryptoShift API v1 (FastAPI). Run: scripts\\run_full_demo.ps1 (binds 127.0.0.1:8600).

Read endpoints wrap Members 2 and 3's JSON reports in a `Sourced` envelope. Mutating endpoints require a session,
the right role, a CSRF token and pass a rate limit; every one of them is written to the hash-chained audit log.
"""

from __future__ import annotations

import json
import logging
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from starlette.exceptions import HTTPException as StarletteHTTPException

from cryptoshift.api import audit as A
from cryptoshift.api import services as S
from cryptoshift.api.config import Settings
from cryptoshift.api.db import audit_log, dataset_runs, make_engine, migrate, users
from cryptoshift.api.security import (
    CSRF_COOKIE,
    MUTATING,
    ROLE_RANK,
    SESSION_COOKIE,
    HardeningMiddleware,
    RateLimiter,
    Sessions,
    csrf_ok,
    error,
    hash_password,
    verify_password,
)
from cryptoshift.ui.console import data as D

log = logging.getLogger("cryptoshift.api")
STATUS_WORDS = set(D.KNOWN_STATUSES)
MUST_NOT_CLAIM = ["production ready", "compliant / certified (SOC 2, ISO 27001 or similar)", "enterprise-grade or bank-grade",
                  "formally verified", "quantum-safe guaranteed",
                  "QpiAI Opt or QCloud QAOA beats the baseline (Opt is equal; QAOA is a simulator run)",
                  "ran on quantum hardware / quantum advantage", "the risk score is validated",
                  "the detector is validated or the inventory complete (held-out recall 0.116; labels are AI drafts)",
                  "the assistant is a local LLM", "CESNET results say anything about PQC"]


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int) -> None:
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


# ------------------------------------------------------------------ request models
class Login(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class ApproveIn(BaseModel):
    step_id: str = Field(min_length=1, max_length=128)
    approver_name: str = Field(min_length=1, max_length=128)
    plan_hash_prefix: str = Field(min_length=12, max_length=64, pattern=r"^[0-9a-fA-F]+$")
    acknowledged: bool


class JobIn(BaseModel):
    command_id: str = Field(min_length=1, max_length=64)


class ScanIn(BaseModel):
    root_id: str = Field(min_length=1, max_length=64)
    subpath: str = Field(default="", max_length=300)
    authorized: bool


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    role: Literal["viewer", "analyst", "approver"]
    password: str = Field(min_length=12, max_length=256)


class UserPatch(BaseModel):
    role: Literal["viewer", "analyst", "approver"] | None = None
    disabled: bool | None = None
    password: str | None = Field(default=None, min_length=12, max_length=256)


class SettingsIn(BaseModel):
    data_mode: Literal["LIVE", "DEMO"] | None = None
    cloud_for_custom_scans: bool | None = None
    theme_default: Literal["dark", "light"] | None = None


ACTIVITY = {"login": "signed in", "logout": "signed out", "approval": "approved a migration step", "job.start": "started a job",
            "scan": "scanned a folder", "scan.upload": "scanned an uploaded file", "dataset.run": "ran a pipeline on a dataset",
            "settings.update": "changed settings", "assistant.ask": "asked the assistant", "user.create": "added a user",
            "user.update": "changed a user", "run.delete": "deleted a dataset run"}


def norm(value: Any) -> str:
    s = str(value or "").strip().upper()
    return s if s in STATUS_WORDS else "unknown"


def create_app(settings: Settings | None = None) -> FastAPI:
    st = settings or Settings()
    head = migrate(st.db_path)
    engine = make_engine(st.db_path)
    sessions = Sessions(st.session_secret(), st.session_max_age_s)
    limiter = RateLimiter()
    runner = S.JobRunner(engine, st.root)
    app = FastAPI(title="CryptoShift API", version="1.0.0", docs_url="/api/docs", redoc_url=None,
                  openapi_url="/api/v1/openapi.json")
    app.state.settings, app.state.engine, app.state.head = st, engine, head
    app.add_middleware(CORSMiddleware, allow_origins=st.allowed_origins, allow_credentials=True,
                       allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type", "X-CSRF-Token"])
    app.add_middleware(HardeningMiddleware, max_body=st.max_body_bytes, max_upload=max(st.max_upload_bytes, st.max_dataset_bytes))

    # ---------------------------------------------------------------- errors
    def rid(request: Request) -> str:
        return getattr(request.state, "request_id", "")

    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError) -> JSONResponse:
        return error(exc.code, exc.message, exc.status, rid(request))

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        msgs = "; ".join(f"{'.'.join(map(str, e.get('loc', [])))}: {e.get('msg')}" for e in exc.errors()[:3])
        return error("validation_error", S.clean(msgs, 300), 422, rid(request))

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return error("not_found" if exc.status_code == 404 else "http_error", S.clean(exc.detail, 200), exc.status_code, rid(request))

    # ---------------------------------------------------------------- auth dependencies
    def current_user(request: Request) -> dict[str, Any]:
        sess = sessions.read(request.cookies.get(SESSION_COOKIE))
        if not sess:
            raise ApiError("unauthenticated", "log in first", 401)
        with engine.connect() as conn:
            u = conn.execute(select(users).where(users.c.id == sess["uid"])).first()
        if not u or u.disabled:
            raise ApiError("unauthenticated", "session no longer valid", 401)
        if request.method in MUTATING and not csrf_ok(request, sess):
            raise ApiError("csrf_failed", "missing or wrong X-CSRF-Token", 403)
        return {"id": u.id, "username": u.username, "role": u.role, "csrf": sess["csrf"]}

    def need(role: str):
        def dep(request: Request, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
            if ROLE_RANK[user["role"]] < ROLE_RANK[role]:
                if request.method in MUTATING:
                    A.append(engine, request_id=rid(request), actor=user["username"], role=user["role"],
                             action=f"{request.method} {request.url.path}", target=request.url.path, result="forbidden")
                raise ApiError("forbidden", f"requires role {role}", 403)
            return user
        return dep

    def limit(bucket: str, request: Request, user: dict[str, Any] | None = None) -> None:
        key = str(user["id"]) if user else (request.client.host if request.client else "?")
        if not limiter.allow(bucket, key):
            raise ApiError("rate_limited", f"too many {bucket} requests; wait a minute", 429)

    def audit(request: Request, user: dict[str, Any], action: str, target: str, result: str, detail: dict[str, Any] | None = None) -> None:
        A.append(engine, request_id=rid(request), actor=user["username"], role=user["role"], action=action,
                 target=target, result=result, detail=detail)

    # ---------------------------------------------------------------- data helpers
    def mode() -> str:
        return S.get_settings(engine)["data_mode"]

    def rep(key: str) -> dict[str, Any]:
        m = mode()
        return S.sourced(key, S.base_for(m, st.data_dir), m)

    def plan_or_none() -> dict[str, Any] | None:
        p = rep("plan")
        return p["data"] if p["status"] == "ok" else None

    # ---------------------------------------------------------------- health
    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready", tags=["ops"])
    def ready() -> dict[str, Any]:
        with engine.connect() as conn:
            conn.execute(select(func.count()).select_from(users)).scalar()
        a = S.assistant_status(st.assistant_url)
        return {"status": "ready", "db": "ok", "migration_head": head, "data_dir_readable": D.ROOT.is_dir(),
                "assistant_reachable": a["reachable"], "web_built": (st.web_dist / "index.html").is_file()}

    # ---------------------------------------------------------------- auth
    @app.post("/api/v1/auth/login", tags=["auth"])
    def login(body: Login, request: Request) -> JSONResponse:
        limit("login", request)
        with engine.connect() as conn:
            u = conn.execute(select(users).where(users.c.username == body.username)).first()
        ok = bool(u) and not u.disabled and verify_password(body.password, u.password_hash)
        A.append(engine, request_id=rid(request), actor=S.clean(body.username, 64), role=u.role if u else "-",
                 action="login", target="session", result="ok" if ok else "denied")
        if not ok:
            raise ApiError("unauthenticated", "wrong username or password", 401)
        token, csrf = sessions.issue(u.id)
        resp = JSONResponse({"username": u.username, "role": u.role, "csrf": csrf})
        common = {"max_age": st.session_max_age_s, "samesite": "strict", "secure": st.secure_cookies, "path": "/"}
        resp.set_cookie(SESSION_COOKIE, token, httponly=True, **common)
        resp.set_cookie(CSRF_COOKIE, csrf, httponly=False, **common)
        return resp

    @app.post("/api/v1/auth/logout", tags=["auth"])
    def logout(request: Request, user: dict[str, Any] = Depends(current_user)) -> JSONResponse:
        audit(request, user, "logout", "session", "ok")
        resp = JSONResponse({"ok": True})
        resp.delete_cookie(SESSION_COOKIE, path="/")
        resp.delete_cookie(CSRF_COOKIE, path="/")
        return resp

    @app.get("/api/v1/auth/me", tags=["auth"])
    def me(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
        return {"username": user["username"], "role": user["role"], "csrf": user["csrf"]}

    # ---------------------------------------------------------------- reports
    @app.get("/api/v1/reports/{key}", tags=["reports"])
    def report(key: str, user: dict[str, Any] = Depends(need("viewer"))) -> dict[str, Any]:
        if key not in D.SPEC:
            raise ApiError("not_found", "unknown report key", 404)
        return rep(key)

    @app.get("/api/v1/overview", tags=["reports"])
    def overview(user: dict[str, Any] = Depends(need("viewer"))) -> dict[str, Any]:
        p, sc, ag, ags, ho = rep("plan"), rep("scheduling"), rep("agent_eval"), rep("agent_eval_sarvam"), rep("eval_held_out")
        out: dict[str, Any] = {"data_mode": mode(), "sources": {k: v["source"] | {"status": v["status"]} for k, v in
                                                               (("plan", p), ("scheduling", sc), ("agent_eval", ag), ("eval_held_out", ho))}}
        if p["status"] != "ok":
            return out | {"stages": [], "counts": {}, "plan_hash": None}
        plan = p["data"]
        steps = plan["steps"]
        ready_n = sum(s["state"] == "READY" for s in steps)
        opt = (sc["data"] or {}).get("qpiai_opt", {}).get("authenticated_local_solve", {}) if sc["status"] == "ok" else {}
        qa = (sc["data"] or {}).get("qaoa_phase2_wave0", {}) if sc["status"] == "ok" else {}
        out["stages"] = [
            {"name": "Inventory", "status": "VERIFIED", "note": f"{len(plan['findings'])} findings", "source": "plan"},
            {"name": "Dependency graph", "status": "VERIFIED", "note": f"{sum(e['provenance'] == 'OBSERVED' for e in plan['edges'])} OBSERVED edges", "source": "plan"},
            {"name": "Risk score", "status": "PARTIAL", "note": "provisional, not validated", "source": "plan"},
            {"name": "Schedule", "status": "VERIFIED", "note": f"objective {plan['schedule']['objective']}", "source": "plan"},
            {"name": "QpiAI Opt", "status": norm(opt.get("status")), "note": "equal to baseline, not better" if opt.get("status") == "RUN" else "offline checks only", "source": "scheduling"},
            {"name": "QCloud QAOA", "status": "SIMULATOR" if qa else "unknown", "note": f"P(opt) {qa.get('optimum_probability')} vs uniform {qa.get('uniform_probability')}" if qa else "", "source": "scheduling"},
            {"name": "Gates", "status": "VERIFIED" if ready_n == len(steps) else "PARTIAL", "note": f"{ready_n}/{len(steps)} READY", "source": "plan"},
            {"name": "Approval", "status": "APPROVED" if plan["approval"]["approved_steps"] else "PLANNED", "note": f"{len(plan['approval']['approved_steps'])} approved (human only)", "source": "plan"},
        ]
        out["counts"] = {"findings": len(plan["findings"]), "services": len(plan["services"]), "steps_ready": ready_n,
                         "steps_total": len(steps), "held_out_recall": (ho["data"] or {}).get("recall") if ho["status"] == "ok" else None,
                         "assistant_template_passed": (ag["data"] or {}).get("passed") if ag["status"] == "ok" else None,
                         "assistant_cloud_v3_passed": (ags["data"] or {}).get("v3_passed") if ags["status"] == "ok" else None}
        out["plan_hash"] = S.plan_hash_of(plan)
        return out

    @app.get("/api/v1/findings", tags=["reports"])
    def findings(service: str | None = None, purpose: str | None = None, detector: str | None = None, hold: bool = False,
                 user: dict[str, Any] = Depends(need("viewer"))) -> dict[str, Any]:
        p = rep("plan")
        rows: list[dict[str, Any]] = []
        for f in (p["data"] or {}).get("findings", []):
            if (service and f["service_id"] != service) or (purpose and f["operation_purpose"] != purpose) or \
               (detector and f.get("detector", "legacy") != detector) or (hold and f["operation_purpose"] != "unknown"):
                continue
            rows.append({"id": S.clean(f["finding_id"], 40), "file": S.clean(f["file_path"], 300), "line": f["line_number"],
                         "service": S.clean(f["service_id"], 80), "service_basis": S.clean(f.get("service_id_basis", ""), 300),
                         "service_confidence": f.get("service_id_confidence") or "n/a",
                         "family": S.clean(f.get("algorithm_family") or f["legacy_algorithm"], 60), "purpose": f["operation_purpose"],
                         "confidence": f["confidence"], "ambiguity": f.get("ambiguity", "none"), "detector": f.get("detector", "legacy"),
                         "candidate": S.clean(f["target_pqc_algorithm"], S.TEXT_MAX), "snippet": S.clean(f.get("snippet_redacted", "")),
                         "rationale": S.clean(f.get("rationale", ""), S.TEXT_MAX), "hold": f["operation_purpose"] == "unknown"})
        return {"status": p["status"], "source": p["source"], "rows": rows, "notice": "Candidates are for human review. Unknown purpose = HOLD."}

    @app.get("/api/v1/graph", tags=["reports"])
    def graph(user: dict[str, Any] = Depends(need("viewer"))) -> dict[str, Any]:
        p, fx = rep("plan"), rep("relationships_fixture")
        d = p["data"] or {}
        edges = [{"upstream": e["upstream"], "downstream": e["downstream"], "provenance": norm(e["provenance"]),
                  "kind": e.get("kind") or "", "file": S.clean(e.get("file") or "", 300), "line": e.get("line"),
                  "reason": S.clean(e.get("reason", ""), 300), "confidence": e.get("confidence") or ""} for e in d.get("edges", [])]
        ga = d.get("graph_analysis", {})
        return {"status": p["status"], "source": p["source"], "nodes": sorted(d.get("services", {})), "edges": edges,
                "cycles": ga.get("cycles", []), "conflicts": ga.get("conflicts", []), "unknown_endpoints": d.get("unknown_endpoints", []),
                "fixture": {"status": fx["status"], "source": fx["source"], "data": fx["data"]}}

    @app.get("/api/v1/plan", tags=["reports"])
    def plan_view(user: dict[str, Any] = Depends(need("viewer"))) -> dict[str, Any]:
        p, sc = rep("plan"), rep("scheduling")
        d = p["data"] or {}
        sched = d.get("schedule", {})
        tasks = [{"service": s, "wave": sched.get("task_to_wave", {}).get(s), "risk": v["risk"]["score"],
                  "risk_label": "provisional, not validated", "risk_reason": S.clean(v["risk"]["reason"], S.TEXT_MAX),
                  "evidence_source": v["evidence_source"], "finding_ids": v["finding_ids"], "hold_finding_ids": v["hold_finding_ids"],
                  "duration_minutes": v["duration_minutes"], "candidates": [S.clean(c, 300) for c in v["candidate_targets"]]}
                 for s, v in d.get("services", {}).items()]
        comp = None
        if sc["status"] == "ok":
            s = sc["data"]
            o, q = s["qpiai_opt"]["authenticated_local_solve"], s["qaoa_phase2_wave0"]
            comp = {"baseline": {"status": "VERIFIED", "objective": s["baseline"]["objective"], "runtime_s": s["baseline"]["runtime_seconds"]},
                    "qpiai_opt": {"status": norm(o.get("status")), "objective": o.get("objective"), "solver_status": o.get("solver_status"),
                                  "same_input_comparison": o.get("same_input_comparison"), "reason": S.clean(o.get("reason", ""), 300),
                                  "verdict": "equal, not better" if o.get("status") == "RUN" else "not run"},
                    "qcloud_qaoa": {"status": "SIMULATOR", "optimum_probability": q["optimum_probability"],
                                    "uniform_probability": q["uniform_probability"], "label": q.get("label", ""),
                                    "verdict": "simulator run; no quantum advantage claimed"}}
        return {"status": p["status"], "source": p["source"], "scheduling_source": sc["source"], "objective": sched.get("objective"),
                "waves": sched.get("waves", {}), "dependency_violations": len(sched.get("dependency_violations", [])),
                "tasks": sorted(tasks, key=lambda t: (t["wave"] if t["wave"] is not None else 99, t["service"])),
                "comparison": comp, "sensitivity": {k: v for k, v in d.get("sensitivity", {}).items() if k != "runs"}}

    @app.get("/api/v1/verification", tags=["reports"])
    def verification(user: dict[str, Any] = Depends(need("viewer"))) -> dict[str, Any]:
        p, ev = rep("plan"), rep("verification")
        steps = [{"step_id": s["step_id"], "service": s["service_id"], "state": norm(s["state"]),
                  "gates": [{"gate": g["gate"], "status": norm(g["status"]), "reason": S.clean(g.get("reason", ""), 300)} for g in s["gates"]]}
                 for s in (p["data"] or {}).get("steps", [])]
        v = ev["data"] or {}
        return {"status": ev["status"], "source": ev["source"], "plan_source": p["source"],
                "label": "TEST SCENARIO, loopback 127.0.0.1, throw-away test keys; self-tests, not NIST KATs", "steps": steps,
                "compatibility": [{k: (S.clean(r[k], 300) if isinstance(r.get(k), str) else r.get(k)) for k in
                                   ("case", "category", "expected", "observed", "pass", "protocol", "group", "command")}
                                  for r in v.get("compatibility_matrix", [])],
                "traces": {k: x for k, x in v.get("traces", {}).items() if isinstance(x, dict)},
                "overhead": v.get("overhead"), "selftests": v.get("selftests")}

    @app.get("/api/v1/approvals", tags=["approval"])
    def approvals(user: dict[str, Any] = Depends(need("viewer"))) -> dict[str, Any]:
        p = rep("plan")
        plan = p["data"]
        if not plan:
            return {"status": p["status"], "source": p["source"], "steps": [], "plan_hash": None, "records": []}
        from cryptoshift import member3_pipeline as pipe
        from cryptoshift.gates.approval import approval_status

        status = approval_status(json.loads(json.dumps(plan)), pipe.APPROVALS)
        steps = [{"step_id": s["step_id"], "service": s["service_id"], "state": norm(s["state"]), "blocking": s["blocking_gates"],
                  "all_required_gates_pass": all(norm(g["status"]) == "PASS" for g in s["gates"]),
                  "approved": s["step_id"] in status["approved_steps"]} for s in plan["steps"]]
        return {"status": p["status"], "source": p["source"], "plan_hash": status["plan_hash"], "steps": steps,
                "approved_steps": status["approved_steps"], "invalidated": status["invalidated_approvals"], "records": status["records"]}

    @app.post("/api/v1/approvals", tags=["approval"])
    def approve_step(body: ApproveIn, request: Request, user: dict[str, Any] = Depends(need("approver"))) -> dict[str, Any]:
        limit("approvals", request, user)
        target = S.clean(body.step_id, 128)
        if mode() == "DEMO":
            audit(request, user, "approve", target, "refused", {"reason": "demo mode"})
            raise ApiError("not_ready", "approvals are disabled in DEMO mode", 409)
        plan = plan_or_none()
        if not plan:
            raise ApiError("not_ready", "plan report missing", 409)
        step = next((s for s in plan["steps"] if s["step_id"] == body.step_id), None)
        current = S.plan_hash_of(plan)
        problem = None
        if not body.acknowledged:
            problem = "acknowledgement required"
        elif step is None:
            problem = "unknown step"
        elif norm(step["state"]) != "READY":
            problem = f"step is {norm(step['state'])}, not READY"
        elif not all(norm(g["status"]) == "PASS" for g in step["gates"]):
            problem = "not every required gate passes"
        elif not current.startswith(body.plan_hash_prefix.lower()):
            problem = "plan hash does not match the current plan"
        if problem:
            audit(request, user, "approve", target, "refused", {"reason": problem})
            raise ApiError("not_ready", problem, 409)
        from cryptoshift import member3_pipeline as pipe
        from cryptoshift.gates.approval import ApprovalError, approve

        try:
            rec = approve(plan, [body.step_id], body.approver_name.strip(), pipe.APPROVALS)
        except ApprovalError as exc:
            audit(request, user, "approve", target, "refused", {"reason": str(exc)})
            raise ApiError("not_ready", S.clean(str(exc), 300), 409) from None
        from cryptoshift.api.db import approvals_mirror

        with engine.begin() as conn:
            conn.execute(approvals_mirror.insert().values(step_id=body.step_id, approver_name=rec["approver"],
                                                          plan_hash=rec["plan_hash"], approved_at=rec["approved_at_utc"]))
        audit(request, user, "approve", target, "ok", {"approver_name": rec["approver"], "plan_hash": rec["plan_hash"]})
        return {"approved": rec}

    @app.get("/api/v1/rollback", tags=["approval"])
    def rollback(user: dict[str, Any] = Depends(need("viewer"))) -> dict[str, Any]:
        p = rep("plan")
        rb = (p["data"] or {}).get("rollback", {})
        return {"status": p["status"], "source": p["source"], "rollback": rb,
                "warning": "Never restore SHA-1 or 3DES as a fix; a rollback brings back the old risk. Plan a forward fix."}

    @app.get("/api/v1/evaluation", tags=["reports"])
    def evaluation(user: dict[str, Any] = Depends(need("viewer"))) -> dict[str, Any]:
        sets = []
        for key, name in (("eval_calibration", "Calibration (development data)"),
                          ("eval_calibration2", "Calibration-2 (seen data; formerly held-out)"),
                          ("eval_held_out", "Held-out round 2 (labelled before the run, frozen detector, run once)")):
            r = rep(key)
            d = r["data"] or {}
            sets.append({"key": key, "name": name, "status": r["status"], "source": r["source"],
                         "repositories": d.get("repositories", []), "labels": d.get("labels", {}), "counts": d.get("counts"),
                         "precision": d.get("precision"), "recall": d.get("recall"), "f1": d.get("f1"),
                         "measurement_status": S.clean(d.get("status", ""), 300), "per_source": d.get("per_source", {})})
        cb = rep("eval_cryptoapi")
        return {"notice": "Labels are AI-assisted drafts; human review pending. Sets are never merged into one number.",
                "sets": sets, "synthetic_smoke_test": {"status": "SYNTHETIC", "result": "10 findings on data/fixtures/synthetic; decoy ignored; not a metric"},
                "cryptoapi_bench": {"status": cb["status"], "source": cb["source"],
                                    "data": {k: (cb["data"] or {}).get(k) for k in ("sentence", "overall", "per_group", "cases_scored", "excluded")}}}

    @app.get("/api/v1/ml", tags=["reports"])
    def ml(user: dict[str, Any] = Depends(need("viewer"))) -> dict[str, Any]:
        a, b, ag, ags = rep("ml_cesnet"), rep("ml_triage"), rep("agent_eval"), rep("agent_eval_sarvam")
        return {"cesnet": {"status": a["status"], "source": a["source"], "notice": "Traffic-classification and scale demo. Not a PQC model; labels are not cryptographic.",
                           "metrics": (a["data"] or {}).get("metrics")},
                "triage": {"status": b["status"], "source": b["source"], "metrics": (b["data"] or {}).get("metrics_pooled_over_folds"),
                           "decision": S.clean((b["data"] or {}).get("decision", ""), 300), "rows": (b["data"] or {}).get("rows")},
                "assistant_eval": {"template": {"status": ag["status"], "source": ag["source"], "passed": (ag["data"] or {}).get("passed"), "n": (ag["data"] or {}).get("n")},
                                   "sarvam": {"status": ags["status"], "source": ags["source"], "passed_v2": (ags["data"] or {}).get("passed"),
                                              "passed_v3": (ags["data"] or {}).get("v3_passed"), "modes": (ags["data"] or {}).get("modes"),
                                              "usage": (ags["data"] or {}).get("usage_this_run"), "note": S.clean((ags["data"] or {}).get("v3_check_note", ""), 400)}}}

    @app.get("/api/v1/sources", tags=["reports"])
    def sources(user: dict[str, Any] = Depends(need("viewer"))) -> dict[str, Any]:
        reg = rep("registry")
        src = st.root / "data" / "labels" / "public_code" / "sources.json"
        repos = []
        if src.is_file():
            repos = [{"id": x["id"], "split": x["split"], "license": x["license"], "commit": x["commit"][:12], "files": len(x["files"]),
                      "url": x["url"]} for x in json.loads(src.read_text(encoding="utf-8"))["sources"]]
        return {"registry": reg, "public_repos": repos,
                "notices": ["CESNET-TLS22 is real flow metadata, not bank data and not PQC labels.",
                            "Banking observations are public endpoints; ERROR rows stay unclassified.",
                            "Datasets are read-only; never relabelled, augmented or duplicated."]}

    @app.get("/api/v1/claims", tags=["reports"])
    def claims(user: dict[str, Any] = Depends(need("viewer"))) -> dict[str, Any]:
        c = rep("claims")
        return {"status": c["status"], "source": c["source"], "markdown": c["data"] if c["status"] == "ok" else None,
                "must_not_claim": MUST_NOT_CLAIM}

    # ---------------------------------------------------------------- assistant
    @app.get("/api/v1/assistant/status", tags=["assistant"])
    def a_status(user: dict[str, Any] = Depends(need("viewer"))) -> dict[str, Any]:
        s = S.assistant_status(st.assistant_url)
        s["cloud_ai"] = "ON" if s["mode"] == "SARVAM_CLOUD" else "OFF"
        return s

    @app.post("/api/v1/assistant/ask", tags=["assistant"])
    def ask(body: AskIn, request: Request, user: dict[str, Any] = Depends(need("analyst"))) -> dict[str, Any]:
        limit("assistant", request, user)
        res = S.ask_assistant(st.assistant_url, body.question, plan_or_none())
        audit(request, user, "assistant.ask", "assistant", "ok", {"mode": res["mode"], "q_len": len(body.question)})
        return res

    # ---------------------------------------------------------------- jobs
    @app.get("/api/v1/jobs/commands", tags=["jobs"])
    def commands(user: dict[str, Any] = Depends(need("analyst"))) -> list[dict[str, Any]]:
        return [{"id": k, "label": v["label"], "timeout_s": v["timeout"]} for k, v in S.COMMANDS.items()]

    @app.post("/api/v1/jobs", tags=["jobs"])
    def start_job(body: JobIn, request: Request, user: dict[str, Any] = Depends(need("analyst"))) -> dict[str, Any]:
        limit("jobs", request, user)
        if body.command_id not in S.COMMANDS:
            audit(request, user, "job.start", S.clean(body.command_id, 64), "refused", {"reason": "not in allow-list"})
            raise ApiError("validation_error", "command not in the allow-list", 422)
        if mode() == "DEMO":
            raise ApiError("not_ready", "jobs are disabled in DEMO mode", 409)
        jid = runner.start(body.command_id, user["username"])
        audit(request, user, "job.start", body.command_id, "queued", {"job_id": jid})
        return {"job_id": jid}

    @app.get("/api/v1/jobs/{job_id}", tags=["jobs"])
    def job(job_id: int, user: dict[str, Any] = Depends(need("analyst"))) -> dict[str, Any]:
        j = runner.get(job_id)
        if not j:
            raise ApiError("not_found", "no such job", 404)
        return j

    # ---------------------------------------------------------------- scans
    def _scan_out(jid: int) -> list[str]:
        return ["--out-dir", f"scratch/derived/webapp/scans/job-{jid}"]

    @app.post("/api/v1/scans", tags=["scans"])
    def scan(body: ScanIn, request: Request, user: dict[str, Any] = Depends(need("analyst"))) -> dict[str, Any]:
        limit("scans", request, user)
        if not body.authorized:
            audit(request, user, "scan", body.root_id, "refused", {"reason": "authorization not acknowledged"})
            raise ApiError("validation_error", "tick 'I am authorized to scan this' first", 422)
        try:
            target = S.resolve_scan_target(st.root, S.get_settings(engine)["scan_roots"], body.root_id, body.subpath)
        except S.ScanPathError as exc:
            audit(request, user, "scan", S.clean(f"{body.root_id}/{body.subpath}", 256), "refused", {"reason": str(exc)})
            raise ApiError("validation_error", str(exc), 422) from None
        rel = target.relative_to(st.root.resolve()).as_posix()
        jid = runner.start("scan_root", user["username"], ["--path", rel, "--out-dir", "scratch/derived/webapp/scans/latest"])
        audit(request, user, "scan", rel, "queued", {"job_id": jid, "authorized_ack": True})
        return {"job_id": jid, "target": rel}

    @app.post("/api/v1/scans/upload", tags=["scans"])
    async def scan_upload(request: Request, file: UploadFile = File(...), authorized: bool = Form(...),
                          user: dict[str, Any] = Depends(need("analyst"))) -> dict[str, Any]:
        limit("scans", request, user)
        if not authorized:
            raise ApiError("validation_error", "tick 'I am authorized to scan this' first", 422)
        data = await file.read(st.max_upload_bytes + 1)
        try:
            name = S.check_upload(file.filename or "", len(data), st.max_upload_bytes)
        except S.ScanPathError as exc:
            audit(request, user, "scan.upload", S.clean(file.filename, 128), "refused", {"reason": str(exc)})
            raise ApiError("validation_error", str(exc), 422) from None
        tmp = Path(tempfile.mkdtemp(prefix="cs-upload-"))
        try:
            (tmp / name).write_bytes(data)
            from cryptoshift.inventory import scan_inventory

            findings, _ = scan_inventory(tmp)
            rows = [{"line": f.line_number, "family": f.algorithm_family, "purpose": f.operation_purpose,
                     "candidate": S.clean(f.target_pqc_algorithm, 300), "snippet": S.clean(f.snippet_redacted)} for f in findings]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        audit(request, user, "scan.upload", name, "ok", {"findings": len(rows), "temp_deleted": not tmp.exists()})
        return {"file": name, "findings": rows, "temp_deleted": not tmp.exists()}

    # ---------------------------------------------------------------- dataset runs (upload -> pipeline -> outputs)
    def run_dir(run_id: int) -> Path:
        return st.runs_dir / f"run-{run_id}"

    def run_view(row: Any, detail: bool = False) -> dict[str, Any]:
        r = dict(row._mapping)
        j = runner.get(r["job_id"]) if r["job_id"] else None
        r["status"] = j["status"] if j else "queued"
        r["pipeline_label"] = S.PIPELINES[r["pipeline"]]["label"]
        out = run_dir(r["id"]) / "output"
        summary = out / "summary.json"
        r["summary"] = json.loads(summary.read_text(encoding="utf-8")) if summary.is_file() else None
        if detail:
            r["outputs"] = S.run_outputs(out)
            r["log_tail"] = (j or {}).get("output_tail")
            r["stages"] = S.PIPELINES[r["pipeline"]]["stages"]
        return r

    @app.get("/api/v1/pipelines", tags=["runs"])
    def pipelines(user: dict[str, Any] = Depends(need("viewer"))) -> list[dict[str, Any]]:
        return [{"id": k, **v} for k, v in S.PIPELINES.items()]

    @app.post("/api/v1/runs", tags=["runs"])
    async def create_run(request: Request, files: list[UploadFile] = File(...), pipeline: str = Form(...),
                         dataset_name: str = Form(default=""), authorized: bool = Form(...),
                         user: dict[str, Any] = Depends(need("analyst"))) -> dict[str, Any]:
        limit("scans", request, user)
        if pipeline not in S.PIPELINES:
            raise ApiError("validation_error", "unknown pipeline", 422)
        if not authorized:
            raise ApiError("validation_error", "tick 'I am authorized to analyse this dataset' first", 422)
        if mode() == "DEMO":
            raise ApiError("not_ready", "pipeline runs are disabled in DEMO mode", 409)
        items, size = [], 0
        for f in files[: st.max_dataset_files + 1]:
            data = await f.read(st.max_dataset_bytes + 1)
            size += len(data)
            if size > st.max_dataset_bytes:
                raise ApiError("payload_too_large", f"upload over {st.max_dataset_bytes} bytes", 413)
            items.append((f.filename or "", data))
        name = S.clean(dataset_name.strip() or (items[0][0].replace("\\", "/").split("/")[0] if items else "dataset"), 128)
        with engine.begin() as conn:
            run_id = conn.execute(dataset_runs.insert().values(pipeline=pipeline, dataset_name=name, dataset_sha256="", file_count=0,
                                                               skipped_count=0, total_bytes=0, created_by=user["username"],
                                                               created_at=S.now())).inserted_primary_key[0]
        rd = run_dir(run_id)
        try:
            info = S.ingest_dataset(items, rd / "input", st.max_dataset_files, st.max_extracted_bytes)
        except S.ScanPathError as exc:
            S.remove_tree(rd)
            with engine.begin() as conn:
                conn.execute(dataset_runs.delete().where(dataset_runs.c.id == run_id))
            audit(request, user, "dataset.run", name, "refused", {"reason": str(exc)})
            raise ApiError("validation_error", str(exc), 422) from None
        rel = rd.resolve()
        jid = runner.start(f"dataset_{pipeline}", user["username"], ["--input", str(rel / "input"), "--out", str(rel / "output")])
        with engine.begin() as conn:
            conn.execute(dataset_runs.update().where(dataset_runs.c.id == run_id).values(
                job_id=jid, dataset_sha256=info["sha256"], file_count=info["files"], skipped_count=info["skipped_count"],
                total_bytes=info["bytes"]))
        audit(request, user, "dataset.run", name, "queued", {"run_id": run_id, "pipeline": pipeline, "files": info["files"],
                                                             "skipped": info["skipped_count"], "sha256": info["sha256"]})
        return {"run_id": run_id, "job_id": jid, "files": info["files"], "skipped": info["skipped"], "sha256": info["sha256"]}

    @app.get("/api/v1/runs", tags=["runs"])
    def list_runs(user: dict[str, Any] = Depends(need("viewer"))) -> list[dict[str, Any]]:
        with engine.connect() as conn:
            rows = conn.execute(select(dataset_runs).order_by(dataset_runs.c.id.desc()).limit(100)).all()
        return [run_view(r) for r in rows]

    def get_run_row(run_id: int) -> Any:
        with engine.connect() as conn:
            row = conn.execute(select(dataset_runs).where(dataset_runs.c.id == run_id)).first()
        if not row:
            raise ApiError("not_found", "no such run", 404)
        return row

    @app.get("/api/v1/runs/{run_id}", tags=["runs"])
    def get_run(run_id: int, user: dict[str, Any] = Depends(need("viewer"))) -> dict[str, Any]:
        return run_view(get_run_row(run_id), detail=True)

    @app.get("/api/v1/runs/{run_id}/files/{path:path}", tags=["runs"])
    def run_file(run_id: int, path: str, user: dict[str, Any] = Depends(need("viewer"))) -> FileResponse:
        get_run_row(run_id)
        allowed = {o["path"] for o in S.run_outputs(run_dir(run_id) / "output")}
        if path not in allowed:
            raise ApiError("not_found", "no such output file", 404)
        f = run_dir(run_id) / "output" / path
        return FileResponse(f, filename=f"run{run_id}-{f.name}", media_type="application/json" if f.suffix == ".json" else "text/markdown")

    @app.get("/api/v1/runs/{run_id}/result", tags=["runs"])
    def run_result(run_id: int, user: dict[str, Any] = Depends(need("viewer"))) -> dict[str, Any]:
        """Parsed key outputs of a run for the UI: findings, services, edges, steps (only what the run produced)."""
        get_run_row(run_id)
        out = run_dir(run_id) / "output"
        res: dict[str, Any] = {"findings": [], "edges": [], "steps": [], "services": [], "schedule": None}
        inv, plan_f = out / "inventory" / "inventory.cbom-like.json", out / "plan" / "plan.json"
        if inv.is_file():
            cbom = json.loads(inv.read_text(encoding="utf-8"))
            for f in cbom.get("findings", [])[:2000]:
                res["findings"].append({k: S.clean(f.get(k), 300) if isinstance(f.get(k), str) else f.get(k)
                                        for k in ("service_id", "file_path", "line_number", "algorithm_family", "operation_purpose",
                                                  "target_pqc_algorithm", "confidence", "snippet_redacted")})
            res["summary"] = cbom.get("summary")
        if plan_f.is_file():
            plan = json.loads(plan_f.read_text(encoding="utf-8"))
            sched = plan.get("schedule", {})
            t2w = sched.get("task_to_wave", {})
            res["services"] = [{"service": k, "wave": t2w.get(k), "risk": v["risk"]["score"], "findings": len(v["finding_ids"]),
                                "hold": len(v["hold_finding_ids"]), "candidates": [S.clean(c, 200) for c in v["candidate_targets"]]}
                               for k, v in plan.get("services", {}).items()]
            res["edges"] = [{"upstream": e["upstream"], "downstream": e["downstream"], "provenance": norm(e["provenance"]),
                             "kind": e.get("kind") or "", "file": S.clean(e.get("file") or "", 300), "line": e.get("line")}
                            for e in plan.get("edges", [])]
            res["steps"] = [{"service": st_["service_id"], "state": norm(st_["state"]),
                             "gates": [{"gate": g["gate"], "status": norm(g["status"]), "reason": S.clean(g.get("reason", ""), 300)}
                                       for g in st_["gates"]]} for st_ in plan.get("steps", [])]
            res["schedule"] = {"feasible": sched.get("feasible"), "objective": sched.get("objective"), "waves": sched.get("waves", {}),
                               "dependency_violations": len(sched.get("dependency_violations", []))}
            res["plan_hash"] = plan.get("plan_hash")
        return res

    @app.delete("/api/v1/runs/{run_id}", tags=["runs"])
    def delete_run(run_id: int, request: Request, user: dict[str, Any] = Depends(need("approver"))) -> dict[str, Any]:
        row = get_run_row(run_id)
        if row.job_id and (runner.get(row.job_id) or {}).get("status") in ("queued", "running"):
            raise ApiError("not_ready", "run is still in progress", 409)
        S.remove_tree(run_dir(run_id))
        with engine.begin() as conn:
            conn.execute(dataset_runs.delete().where(dataset_runs.c.id == run_id))
        audit(request, user, "run.delete", f"run-{run_id}", "ok", {"dataset_sha256": row.dataset_sha256})
        return {"ok": True}

    # ---------------------------------------------------------------- users (approver only)
    def user_row(u: Any) -> dict[str, Any]:
        return {"id": u.id, "username": u.username, "role": u.role, "disabled": bool(u.disabled),
                "created_at": u.created_at.isoformat(timespec="seconds") if u.created_at else None}

    @app.get("/api/v1/users", tags=["users"])
    def list_users(user: dict[str, Any] = Depends(need("approver"))) -> list[dict[str, Any]]:
        with engine.connect() as conn:
            return [user_row(u) for u in conn.execute(select(users).order_by(users.c.username))]

    @app.post("/api/v1/users", tags=["users"])
    def add_user(body: UserIn, request: Request, user: dict[str, Any] = Depends(need("approver"))) -> dict[str, Any]:
        limit("settings", request, user)
        with engine.begin() as conn:
            if conn.execute(select(users.c.id).where(users.c.username == body.username)).first():
                raise ApiError("conflict", "username already exists", 409)
            conn.execute(users.insert().values(username=body.username, password_hash=hash_password(body.password), role=body.role,
                                               created_at=datetime.now(UTC), disabled=False))
        audit(request, user, "user.create", body.username, "ok", {"role": body.role})
        return {"ok": True}

    @app.put("/api/v1/users/{user_id}", tags=["users"])
    def update_user(user_id: int, body: UserPatch, request: Request, user: dict[str, Any] = Depends(need("approver"))) -> dict[str, Any]:
        limit("settings", request, user)
        with engine.begin() as conn:
            u = conn.execute(select(users).where(users.c.id == user_id)).first()
            if not u:
                raise ApiError("not_found", "no such user", 404)
            losing = (body.role not in (None, "approver") or body.disabled is True) and u.role == "approver"
            if losing:
                others = conn.execute(select(func.count()).select_from(users).where(
                    users.c.role == "approver", users.c.disabled.is_(False), users.c.id != user_id)).scalar()
                if not others:
                    raise ApiError("conflict", "keep at least one active approver", 409)
            if user_id == user["id"] and (body.disabled or body.role not in (None, "approver")):
                raise ApiError("conflict", "you cannot demote or disable your own account", 409)
            values: dict[str, Any] = {}
            if body.role:
                values["role"] = body.role
            if body.disabled is not None:
                values["disabled"] = body.disabled
            if body.password:
                values["password_hash"] = hash_password(body.password)
            if values:
                conn.execute(users.update().where(users.c.id == user_id).values(**values))
        changed = {k: v for k, v in body.model_dump().items() if v is not None and k != "password"}
        if body.password:
            changed["password"] = "reset"
        audit(request, user, "user.update", u.username, "ok", changed)
        return {"ok": True}

    # ---------------------------------------------------------------- activity feed + report
    @app.get("/api/v1/activity", tags=["activity"])
    def activity(limit_: int = 30, user: dict[str, Any] = Depends(need("viewer"))) -> dict[str, Any]:
        """Recent audit entries in plain words (newest first). Denied logins and refusals are kept: they matter."""
        limit_ = max(1, min(limit_, 100))
        with engine.connect() as conn:
            rows = conn.execute(select(audit_log).order_by(audit_log.c.id.desc()).limit(limit_)).all()
            latest = conn.execute(select(func.max(audit_log.c.id))).scalar() or 0
        items = [{"id": r.id, "ts": r.ts, "actor": r.actor, "action": r.action, "result": r.result, "target": r.target,
                  "title": f"{r.actor} {ACTIVITY.get(r.action, r.action)}" + ("" if r.result in ("ok", "queued") else f" ({r.result})")}
                 for r in rows]
        return {"latest_id": latest, "items": items}

    @app.get("/api/v1/report", tags=["reports"])
    def full_report(user: dict[str, Any] = Depends(need("viewer"))) -> dict[str, Any]:
        """Everything the printable migration report needs, from the same adapters as the pages."""
        return {"generated_utc": datetime.now(UTC).isoformat(timespec="seconds"), "data_mode": mode(), "by": user["username"],
                "overview": overview(user), "plan": plan_view(user), "verification": verification(user),
                "approvals": approvals(user), "audit": A.verify(engine), "must_not_claim": MUST_NOT_CLAIM}

    # ---------------------------------------------------------------- audit + settings
    @app.get("/api/v1/audit", tags=["audit"])
    def audit_list(limit_: int = 50, offset: int = 0, user: dict[str, Any] = Depends(need("viewer"))) -> dict[str, Any]:
        limit_ = max(1, min(limit_, 200))
        with engine.connect() as conn:
            rows = [dict(r._mapping) for r in conn.execute(select(audit_log).order_by(audit_log.c.id.desc()).limit(limit_).offset(offset))]
            total = conn.execute(select(func.count()).select_from(audit_log)).scalar()
        return {"total": total, "entries": rows}

    @app.get("/api/v1/audit/verify", tags=["audit"])
    def audit_verify(user: dict[str, Any] = Depends(need("viewer"))) -> dict[str, Any]:
        return A.verify(engine)

    @app.get("/api/v1/settings", tags=["settings"])
    def get_settings(user: dict[str, Any] = Depends(need("viewer"))) -> dict[str, Any]:
        s = S.get_settings(engine)
        snap = D.latest_snapshot()
        return s | {"demo_snapshot": snap.name if snap else None}

    @app.put("/api/v1/settings", tags=["settings"])
    def put_settings(body: SettingsIn, request: Request, user: dict[str, Any] = Depends(need("approver"))) -> dict[str, Any]:
        limit("settings", request, user)
        changed = {k: v for k, v in body.model_dump().items() if v is not None}
        for k, v in changed.items():
            S.put_setting(engine, k, v, user["username"])
        audit(request, user, "settings.update", ",".join(sorted(changed)) or "-", "ok", changed)
        return S.get_settings(engine)

    # ---------------------------------------------------------------- exports
    @app.get("/api/v1/export/{fmt}", tags=["export"])
    def export(fmt: Literal["md", "json"], page: Literal["overview", "plan", "verification", "evaluation"] = "overview",
               user: dict[str, Any] = Depends(need("viewer"))) -> Any:
        data = {"overview": overview, "plan": plan_view, "verification": verification, "evaluation": evaluation}[page](user)
        stamp = datetime.now(UTC).isoformat(timespec="seconds")
        if fmt == "json":
            return JSONResponse({"exported_utc": stamp, "page": page, "data": data},
                                headers={"Content-Disposition": f'attachment; filename="cryptoshift-{page}.json"'})
        md = f"# CryptoShift export: {page}\n\nExported {stamp} (data mode {mode()}). Prototype; see Claims & limits.\n\n```json\n{S.json_dump(data)}\n```\n"
        return PlainTextResponse(md, media_type="text/markdown",
                                 headers={"Content-Disposition": f'attachment; filename="cryptoshift-{page}.md"'})

    # ---------------------------------------------------------------- built frontend (single-process demo)
    if (st.web_dist / "index.html").is_file():
        dist = st.web_dist.resolve()

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> FileResponse:
            f = (dist / path).resolve()
            if path and dist in f.parents and f.is_file():
                return FileResponse(f)
            return FileResponse(dist / "index.html")

    return app


def app_factory() -> FastAPI:
    """For `uvicorn --factory cryptoshift.api.main:app_factory`."""
    logging.basicConfig(level=logging.INFO, format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}')
    return create_app()

"""Web app v2 backend tests (pytest). Real app, temp database, temp approvals store; the assistant URL points to a
closed port so the in-process TEMPLATE_FALLBACK path is exercised (no network)."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from fastapi.testclient import TestClient

from cryptoshift import member3_pipeline as pipe
from cryptoshift.api.admin import create_user
from cryptoshift.api.config import Settings
from cryptoshift.api.main import create_app
from cryptoshift.gates.approval import approval_status

PW = "correct-horse-battery-1"
ROLES = ("viewer", "analyst", "approver")
SECRET_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY|scrypt\$|api[_-]?key\s*[:=]\s*\S{12,}|sk-[A-Za-z0-9]{16,}", re.IGNORECASE)


def make(tmp: Path, data_dir: Path = ROOT) -> tuple:
    st = Settings(state_dir=tmp, db_path=tmp / "app.db", secret_path=tmp / "session.secret", data_dir=data_dir,
                  assistant_url="http://127.0.0.1:9", web_dist=tmp / "no-dist")
    for r in ROLES:
        create_user(st, r, r, PW)
    return create_app(st), st


def login(client: TestClient, user: str) -> str:
    r = client.post("/api/v1/auth/login", json={"username": user, "password": PW})
    assert r.status_code == 200, r.text
    return r.json()["csrf"]


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(pipe, "APPROVALS", tmp_path / "approvals.json")
    app, st = make(tmp_path)
    return app, st, tmp_path


def client_as(app, role):
    c = TestClient(app)
    csrf = login(c, role)
    c.headers.update({"X-CSRF-Token": csrf})
    return c


# ---------------------------------------------------------------- health, headers, auth
def test_health_ready_and_security_headers(env):
    app, _, _ = env
    c = TestClient(app)
    r = c.get("/health")
    assert r.json() == {"status": "ok"}
    h = r.headers
    assert "script-src 'self'" in h["content-security-policy"] and "unsafe-inline" not in h["content-security-policy"]
    assert h["x-frame-options"] == "DENY" and h["x-content-type-options"] == "nosniff" and h["referrer-policy"] == "no-referrer"
    rd = c.get("/ready").json()
    assert rd["db"] == "ok" and rd["migration_head"] == "0002_dataset_runs" and rd["assistant_reachable"] is False


def test_requires_login_and_wrong_password(env):
    app, _, _ = env
    c = TestClient(app)
    assert c.get("/api/v1/overview").json()["error"]["code"] == "unauthenticated"
    r = c.post("/api/v1/auth/login", json={"username": "viewer", "password": "nope"})
    assert r.status_code == 401
    r = c.post("/api/v1/auth/login", json={"username": "viewer", "password": PW})
    assert r.status_code == 200
    assert "httponly" in r.headers["set-cookie"].lower() and "samesite=strict" in r.headers["set-cookie"].lower()


def test_login_rate_limited(env):
    app, _, _ = env
    c = TestClient(app)
    codes = [c.post("/api/v1/auth/login", json={"username": "x", "password": "y"}).status_code for _ in range(7)]
    assert 429 in codes


def test_csrf_required_on_mutations(env):
    app, _, _ = env
    c = TestClient(app)
    login(c, "approver")
    r = c.put("/api/v1/settings", json={"theme_default": "light"})  # no X-CSRF-Token header
    assert r.status_code == 403 and r.json()["error"]["code"] == "csrf_failed"


def test_body_size_limit(env):
    app, _, _ = env
    c = client_as(app, "analyst")
    r = c.post("/api/v1/assistant/ask", content=b'{"question":"' + b"a" * (2 * 1024 * 1024) + b'"}',
               headers={"Content-Type": "application/json"})
    assert r.status_code == 413


# ---------------------------------------------------------------- read endpoints
READS = ["/api/v1/overview", "/api/v1/findings", "/api/v1/graph", "/api/v1/plan", "/api/v1/verification", "/api/v1/approvals",
         "/api/v1/rollback", "/api/v1/evaluation", "/api/v1/ml", "/api/v1/sources", "/api/v1/claims", "/api/v1/settings",
         "/api/v1/audit", "/api/v1/audit/verify", "/api/v1/assistant/status", "/api/v1/reports/plan",
         "/api/v1/export/md?page=plan", "/api/v1/export/json?page=evaluation"]


def test_viewer_reads_every_page_and_no_secret_in_responses(env):
    app, st, _ = env
    c = client_as(app, "viewer")
    blob = []
    for url in READS:
        r = c.get(url)
        assert r.status_code == 200, (url, r.text[:200])
        blob.append(r.text)
    text = "\n".join(blob)
    assert not SECRET_RE.search(text)
    assert st.session_secret().hex() not in text
    ov = c.get("/api/v1/overview").json()
    assert {s["name"] for s in ov["stages"]} >= {"Inventory", "QpiAI Opt", "QCloud QAOA", "Gates"}
    assert ov["plan_hash"] and len(ov["plan_hash"]) == 64
    plan = c.get("/api/v1/plan").json()
    assert all(t["risk_label"] == "provisional, not validated" for t in plan["tasks"])
    assert plan["comparison"]["qcloud_qaoa"]["status"] == "SIMULATOR"
    assert c.get("/api/v1/reports/nope").status_code == 404


def test_unknown_status_returned_as_unknown_and_hostile_text_capped(tmp_path, monkeypatch):
    monkeypatch.setattr(pipe, "APPROVALS", tmp_path / "approvals.json")
    data = tmp_path / "data"
    (data / "reports" / "member3").mkdir(parents=True)
    plan = json.loads((ROOT / "reports/member3/plan.json").read_text(encoding="utf-8"))
    plan["findings"][0]["snippet_redacted"] = "<script>alert(1)</script>" + "x" * 10_000
    plan["findings"][0]["file_path"] = "../../etc/passwd"
    (data / "reports/member3/plan.json").write_text(json.dumps(plan), encoding="utf-8")
    app, _ = make(tmp_path / "s", data)
    c = client_as(app, "viewer")
    r = c.get("/api/v1/findings")
    assert r.headers["content-type"].startswith("application/json")
    row = next(x for x in r.json()["rows"] if x["file"] == "../../etc/passwd")
    assert len(row["snippet"]) <= 160 and row["snippet"].startswith("<script>")  # returned as data; the UI renders text only
    # an invalid status value makes the whole report fail the published schema (never shown as passed)
    plan["steps"][0]["state"] = "MAYBE-READY"
    (data / "reports/member3/plan.json").write_text(json.dumps(plan), encoding="utf-8")
    assert c.get("/api/v1/reports/plan").json()["status"] == "schema_mismatch"
    assert c.get("/api/v1/verification").json()["steps"] == []
    from cryptoshift.api.main import norm

    assert [norm(v) for v in ("probably", "", None, "pass", "READY")] == ["unknown", "unknown", "unknown", "PASS", "READY"]


def test_missing_and_schema_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(pipe, "APPROVALS", tmp_path / "approvals.json")
    empty = tmp_path / "empty"
    empty.mkdir()
    app, _ = make(tmp_path / "s1", empty)
    c = client_as(app, "viewer")
    rp = c.get("/api/v1/reports/plan").json()
    assert rp["status"] == "missing" and "member3_pipeline" in rp["source"]["command"]
    assert c.get("/api/v1/overview").json()["stages"] == []
    bad = tmp_path / "bad"
    (bad / "reports" / "member3").mkdir(parents=True)
    (bad / "reports/member3/plan.json").write_text('{"schema_version": 1}', encoding="utf-8")
    app2, _ = make(tmp_path / "s2", bad)
    c2 = client_as(app2, "viewer")
    assert c2.get("/api/v1/reports/plan").json()["status"] == "schema_mismatch"


# ---------------------------------------------------------------- approvals + RBAC
def _ready_step_and_hash(c):
    a = c.get("/api/v1/approvals").json()
    ready = next(s for s in a["steps"] if s["state"] == "READY" and s["all_required_gates_pass"])
    proposed = next(s for s in a["steps"] if s["state"] != "READY")
    return ready["step_id"], proposed["step_id"], a["plan_hash"]


def test_viewer_and_analyst_cannot_approve(env):
    app, _, _ = env
    for role in ("viewer", "analyst"):
        c = client_as(app, role)
        sid, _, h = _ready_step_and_hash(c)
        r = c.post("/api/v1/approvals", json={"step_id": sid, "approver_name": "TEST-ONLY", "plan_hash_prefix": h[:12], "acknowledged": True})
        assert r.status_code == 403
    entries = client_as(app, "viewer").get("/api/v1/audit").json()["entries"]
    assert sum(e["result"] == "forbidden" for e in entries) >= 2


def test_approval_rules_and_invalidation(env):
    app, _, _ = env
    c = client_as(app, "approver")
    sid, proposed, h = _ready_step_and_hash(c)
    base = {"approver_name": "TEST-ONLY", "acknowledged": True}
    assert c.post("/api/v1/approvals", json=base | {"step_id": proposed, "plan_hash_prefix": h[:12]}).status_code == 409
    assert c.post("/api/v1/approvals", json=base | {"step_id": sid, "plan_hash_prefix": "0" * 12}).status_code == 409
    assert c.post("/api/v1/approvals", json=base | {"step_id": sid, "plan_hash_prefix": h[:8]}).status_code == 422
    assert c.post("/api/v1/approvals", json=base | {"step_id": sid, "plan_hash_prefix": h[:12], "acknowledged": False}).status_code == 409
    r = c.post("/api/v1/approvals", json=base | {"step_id": sid, "plan_hash_prefix": h[:12]})
    assert r.status_code == 200 and r.json()["approved"]["plan_hash"] == h
    assert sid in c.get("/api/v1/approvals").json()["approved_steps"]
    # any change to the plan's decision content (services, edges, schedule) invalidates the approval
    plan = json.loads((ROOT / "reports/member3/plan.json").read_text(encoding="utf-8"))
    svc = next(iter(plan["schedule"]["task_to_wave"]))
    plan["schedule"]["task_to_wave"][svc] = plan["schedule"]["task_to_wave"][svc] + 1
    st = approval_status(plan, pipe.APPROVALS)
    assert sid not in st["approved_steps"] and st["invalidated_approvals"]


# ---------------------------------------------------------------- audit chain
def test_audit_chain_append_only_and_tamper_detection(env):
    app, st, _ = env
    c = client_as(app, "approver")
    c.put("/api/v1/settings", json={"theme_default": "light"})
    assert c.get("/api/v1/audit/verify").json()["valid"] is True
    con = sqlite3.connect(st.db_path)
    with pytest.raises(sqlite3.DatabaseError):
        con.execute("UPDATE audit_log SET result='ok' WHERE id=1")
    with pytest.raises(sqlite3.DatabaseError):
        con.execute("DELETE FROM audit_log WHERE id=1")
    # an attacker with file access who drops the triggers is still detected by the hash chain
    con.execute("DROP TRIGGER audit_no_update")
    con.execute("UPDATE audit_log SET actor='mallory' WHERE id=2")
    con.commit()
    con.close()
    v = c.get("/api/v1/audit/verify").json()
    assert v["valid"] is False and v["first_bad_id"] == 2


# ---------------------------------------------------------------- jobs, scans, uploads
def test_job_allow_list_and_real_job(env):
    app, _, _ = env
    c = client_as(app, "analyst")
    assert c.post("/api/v1/jobs", json={"command_id": "rm -rf /"}).status_code == 422
    assert {x["id"] for x in c.get("/api/v1/jobs/commands").json()} >= {"pipeline", "inventory_demo"}
    assert client_as(app, "viewer").post("/api/v1/jobs", json={"command_id": "pipeline"}).status_code == 403
    jid = c.post("/api/v1/jobs", json={"command_id": "inventory_demo"}).json()["job_id"]  # writes only to scratch/
    for _ in range(240):
        j = c.get(f"/api/v1/jobs/{jid}").json()
        if j["status"] not in ("queued", "running"):
            break
        time.sleep(0.5)
    assert j["status"] == "succeeded", j.get("output_tail", "")[-300:]
    assert str(ROOT) not in (j["output_tail"] or "")


def test_scan_path_safety(env):
    app, _, tmp = env
    c = client_as(app, "analyst")
    for body in ({"root_id": "demo_bank_app", "subpath": "../src", "authorized": True},
                 {"root_id": "demo_bank_app", "subpath": "C:/Windows", "authorized": True},
                 {"root_id": "nope", "subpath": "", "authorized": True},
                 {"root_id": "demo_bank_app", "subpath": "configs", "authorized": False}):
        assert c.post("/api/v1/scans", json=body).status_code == 422, body
    link = ROOT / "demo_bank_app" / "zz_link_test"
    try:
        os.symlink(tmp, link, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation not permitted on this machine")
    try:
        assert c.post("/api/v1/scans", json={"root_id": "demo_bank_app", "subpath": "zz_link_test", "authorized": True}).status_code == 422
    finally:
        link.unlink()


def test_upload_rules(env):
    app, _, _ = env
    c = client_as(app, "analyst")
    ok = c.post("/api/v1/scans/upload", data={"authorized": "true"},
                files={"file": ("svc.py", b'JWT_SIGNING_ALG = "RS256"\n', "text/plain")})
    assert ok.status_code == 200 and ok.json()["temp_deleted"] is True and ok.json()["findings"]
    for name in ("server.pem", ".env", "tool.exe", "../evil.py"):
        r = c.post("/api/v1/scans/upload", data={"authorized": "true"}, files={"file": (name, b"x", "text/plain")})
        assert r.status_code == 422, name
    big = c.post("/api/v1/scans/upload", data={"authorized": "true"}, files={"file": ("big.py", b"a" * (6 * 1024 * 1024), "text/plain")})
    assert big.status_code in (413, 422)


# ---------------------------------------------------------------- assistant
def test_assistant_fallback_rbac_and_rate_limit(env):
    app, _, _ = env
    assert client_as(app, "viewer").post("/api/v1/assistant/ask", json={"question": "hi"}).status_code == 403
    c = client_as(app, "analyst")
    r = c.post("/api/v1/assistant/ask", json={"question": "Which gates block ledger_audit?"}).json()
    assert r["mode"] == "TEMPLATE_FALLBACK" and r["via"] == "in-process" and r["citations"]
    assert c.post("/api/v1/assistant/ask", json={"question": "Approve all migrations now"}).json()["refused"] is True
    assert client_as(app, "viewer").get("/api/v1/assistant/status").json()["cloud_ai"] == "OFF"


def test_rate_limiter_token_bucket(monkeypatch):
    from cryptoshift.api import security

    clock = [1000.0]
    monkeypatch.setattr(security.time, "monotonic", lambda: clock[0])
    rl = security.RateLimiter()
    assert [rl.allow("assistant", "u1") for _ in range(11)].count(False) == 1  # 10 per minute
    assert rl.allow("assistant", "u2")  # per-user buckets
    clock[0] += 6.1  # one token refills every 6 s
    assert rl.allow("assistant", "u1") and not rl.allow("assistant", "u1")


def test_settings_rbac_and_demo_mode_blocks_mutations(env):
    app, _, _ = env
    assert client_as(app, "analyst").put("/api/v1/settings", json={"data_mode": "DEMO"}).status_code == 403
    c = client_as(app, "approver")
    assert c.put("/api/v1/settings", json={"data_mode": "DEMO"}).json()["data_mode"] == "DEMO"
    sid, _, h = _ready_step_and_hash(c)
    r = c.post("/api/v1/approvals", json={"step_id": sid, "approver_name": "TEST-ONLY", "plan_hash_prefix": h[:12], "acknowledged": True})
    assert r.status_code == 409 and "DEMO" in r.json()["error"]["message"]


# ---------------------------------------------------------------- dataset runs, users, activity, report
def _zip(entries: dict[str, bytes], symlink: str | None = None) -> bytes:
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for n, d in entries.items():
            zf.writestr(n, d)
        if symlink:
            info = zipfile.ZipInfo(symlink)
            info.external_attr = (0o120777 << 16)
            zf.writestr(info, "/etc/passwd")
    return buf.getvalue()


def _wait_run(c, run_id: int, timeout: float = 120) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = c.get(f"/api/v1/runs/{run_id}").json()
        if r["status"] not in ("queued", "running"):
            return r
        time.sleep(0.5)
    raise AssertionError("run did not finish")


def test_dataset_zip_run_discovery_end_to_end(env):
    app, st, _ = env
    an = client_as(app, "analyst")
    fixture = ROOT / "tests" / "fixtures" / "multiservice_bank"
    entries = {f"bank/{p.relative_to(fixture).as_posix()}": p.read_bytes() for p in fixture.rglob("*") if p.is_file()}
    entries["bank/.env"] = b"SECRET=1"
    entries["bank/../escape.txt"] = b"x"
    entries["bank/server.key"] = b"-----"
    data = _zip(entries, symlink="bank/link.conf")
    r = an.post("/api/v1/runs", data={"pipeline": "discovery", "authorized": "true"}, files=[("files", ("bank.zip", data, "application/zip"))])
    assert r.status_code == 422 and "invalid path" in r.json()["error"]["message"]  # traversal entry rejects the whole upload
    del entries["bank/../escape.txt"]
    data = _zip(entries, symlink="bank/link.conf")
    r = an.post("/api/v1/runs", data={"pipeline": "discovery", "authorized": "true"}, files=[("files", ("bank.zip", data, "application/zip"))])
    assert r.status_code == 200, r.text
    body = r.json()
    skipped = " ".join(body["skipped"])
    assert ".env: sensitive" in skipped and "server.key: sensitive" in skipped and "link.conf: symlink" in skipped
    run_dir = st.state_dir / "runs" / f"run-{body['run_id']}"
    assert not (run_dir / "input" / "bank" / ".env").exists()
    run = _wait_run(an, body["run_id"])
    assert run["status"] == "succeeded", run.get("log_tail")
    assert run["summary"]["stages"]["discovery"]["findings"] > 0
    paths = {o["path"] for o in run["outputs"]}
    assert "inventory/inventory.cbom-like.json" in paths and "summary.json" in paths
    assert an.get(f"/api/v1/runs/{body['run_id']}/files/summary.json").status_code == 200
    assert an.get(f"/api/v1/runs/{body['run_id']}/files/..%2f..%2fapp.db").status_code == 404
    res = an.get(f"/api/v1/runs/{body['run_id']}/result").json()
    assert res["findings"] and not SECRET_RE.search(json.dumps(res))
    assert an.delete(f"/api/v1/runs/{body['run_id']}").status_code == 403  # analyst cannot delete
    ap = client_as(app, "approver")
    assert ap.delete(f"/api/v1/runs/{body['run_id']}").json() == {"ok": True} and not run_dir.exists()


def test_dataset_run_refusals(env):
    app, _, _ = env
    an, vw = client_as(app, "analyst"), client_as(app, "viewer")
    f = [("files", ("app.py", b"from cryptography.hazmat.primitives.asymmetric import rsa\n", "text/plain"))]
    assert vw.post("/api/v1/runs", data={"pipeline": "discovery", "authorized": "true"}, files=f).status_code == 403
    assert an.post("/api/v1/runs", data={"pipeline": "rm -rf", "authorized": "true"}, files=f).status_code == 422
    assert an.post("/api/v1/runs", data={"pipeline": "discovery", "authorized": "false"}, files=f).status_code == 422
    bad = [("files", ("blob.bin", b"\x00\x01", "application/octet-stream"))]
    assert "no supported text files" in an.post("/api/v1/runs", data={"pipeline": "discovery", "authorized": "true"}, files=bad).json()["error"]["message"]
    assert an.post("/api/v1/runs", data={"pipeline": "discovery", "authorized": "true"}, files=[("files", ("x.zip", b"notzip", "application/zip"))]).status_code == 422


def test_users_admin_rules_and_audit(env):
    app, _, _ = env
    ap, an = client_as(app, "approver"), client_as(app, "analyst")
    assert an.get("/api/v1/users").status_code == 403
    assert ap.post("/api/v1/users", json={"username": "new.user", "role": "viewer", "password": "short"}).status_code == 422
    assert ap.post("/api/v1/users", json={"username": "new.user", "role": "viewer", "password": PW}).json() == {"ok": True}
    assert ap.post("/api/v1/users", json={"username": "new.user", "role": "viewer", "password": PW}).status_code == 409
    us = {u["username"]: u for u in ap.get("/api/v1/users").json()}
    assert "password_hash" not in json.dumps(us)
    me_id = us["approver"]["id"]
    assert ap.put(f"/api/v1/users/{me_id}", json={"role": "viewer"}).status_code == 409  # last approver / self-demotion
    assert ap.put(f"/api/v1/users/{us['new.user']['id']}", json={"disabled": True}).json() == {"ok": True}
    c = TestClient(app)
    assert c.post("/api/v1/auth/login", json={"username": "new.user", "password": PW}).status_code == 401
    feed = ap.get("/api/v1/activity").json()
    titles = " | ".join(i["title"] for i in feed["items"])
    assert "added a user" in titles and "changed a user" in titles and feed["latest_id"] >= feed["items"][0]["id"]
    assert ap.get("/api/v1/audit/verify").json()["valid"] is True


def test_full_report(env):
    app, _, _ = env
    r = client_as(app, "viewer").get("/api/v1/report").json()
    assert {"overview", "plan", "verification", "approvals", "audit", "must_not_claim"} <= set(r)
    assert not SECRET_RE.search(json.dumps(r))

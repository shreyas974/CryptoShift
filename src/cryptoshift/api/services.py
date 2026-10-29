"""Backend services: read-only report adapters, text sanitising, allow-listed jobs, scan-path checks, assistant proxy.

Report files are read through the Member 4 console adapter (`cryptoshift.ui.console.data`), which validates them
against Members 2 and 3's published schemas. Nothing here writes to report files.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import threading
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Engine

from cryptoshift.api.db import jobs as jobs_t
from cryptoshift.api.db import settings_table
from cryptoshift.optimization.auth_check import redact_secrets
from cryptoshift.ui.console import data as D

SNIPPET_MAX, TEXT_MAX = 160, 500
_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def clean(value: Any, limit: int = SNIPPET_MAX) -> str:
    """Plain text for anything from scanned files: control characters removed, capped. Never HTML."""
    s = _CTRL.sub(" ", "" if value is None else str(value))
    return s if len(s) <= limit else s[: limit - 1] + "…"


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# ------------------------------------------------------------------ settings
DEFAULT_SETTINGS = {"data_mode": "LIVE", "scan_roots": {"demo_bank_app": "demo_bank_app", "fixtures": "tests/fixtures"},
                    "cloud_for_custom_scans": False, "theme_default": "dark"}


def get_settings(engine: Engine) -> dict[str, Any]:
    out = dict(DEFAULT_SETTINGS)
    with engine.connect() as conn:
        for row in conn.execute(select(settings_table)):
            out[row.key] = row.value_json
    return out


def put_setting(engine: Engine, key: str, value: Any, actor: str) -> None:
    with engine.begin() as conn:
        conn.execute(settings_table.delete().where(settings_table.c.key == key))
        conn.execute(settings_table.insert().values(key=key, value_json=value, updated_by=actor, updated_at=now()))


# ------------------------------------------------------------------ reports
def base_for(mode: str, override: Path | None) -> Path:
    if override:
        return override
    return D.base_dir("DEMO" if mode == "DEMO" else "LIVE")


def sourced(key: str, base: Path, mode: str) -> dict[str, Any]:
    """Load one report into the `Sourced` envelope (status, data, source, errors)."""
    loaded = D.load(key, base)
    path = base / loaded.file
    sha = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    return {"status": loaded.status, "data": loaded.value if loaded.status == "ok" else None,
            "source": {"key": key, "file": loaded.file, "producer": loaded.producer, "label": loaded.label,
                       "modified": loaded.mtime or None, "sha256": sha, "command": loaded.command, "mode": mode},
            "errors": [clean(e, 200) for e in loaded.errors]}


# ------------------------------------------------------------------ jobs (allow-list only)
PY = sys.executable
COMMANDS: dict[str, dict[str, Any]] = {
    "inventory_demo": {"label": "Inventory v1.1 on the demo bank",
                       "argv": ["scripts/inventory_v11.py", "--path", "demo_bank_app/configs", "--cyclonedx"], "timeout": 300},
    "inventory_fixture": {"label": "Inventory v1.1 on the multi-service fixture",
                          "argv": ["scripts/inventory_v11.py", "--path", "tests/fixtures/multiservice_bank", "--cyclonedx"], "timeout": 300},
    "pipeline": {"label": "Member 3 pipeline (plan + reports)", "argv": ["scripts/member3_pipeline.py"], "timeout": 300},
    "agent_eval_template": {"label": "Assistant evaluation (template, no cloud)", "argv": ["scripts/evaluate_agent.py"], "timeout": 300},
    "snapshot": {"label": "Freeze an offline demo snapshot", "argv": ["scripts/ui_snapshot.py"], "timeout": 120},
}
# Pipelines a user can run on an uploaded dataset (scripts/webapp_run.py); the run folder is added by the API.
PIPELINES: dict[str, dict[str, Any]] = {
    "discovery": {"label": "Discovery", "stages": ["Inventory", "Relationships", "CBOM-like + CycloneDX"], "timeout": 300,
                  "note": "Member 2 inventory v1.1 on your files"},
    "plan": {"label": "Discovery + migration plan", "stages": ["Inventory", "Relationships", "Services & dependencies", "Schedule", "Gates"],
             "timeout": 600, "note": "Adds the Member 3 plan; gates use the saved generic loopback evidence"},
    "full": {"label": "Full: re-run verification lab", "stages": ["Inventory", "Verification lab", "Services & dependencies", "Schedule", "Gates"],
             "timeout": 900, "note": "Re-runs OpenSSL 3.5 loopback handshakes, compatibility and rollback first (slow)"},
}


class JobRunner:
    def __init__(self, engine: Engine, root: Path) -> None:
        self.engine, self.root = engine, root

    def start(self, command_id: str, created_by: str, extra: list[str] | None = None) -> int:
        if command_id.startswith("dataset_") and command_id[8:] in PIPELINES:
            spec = {"argv": ["scripts/webapp_run.py", "--pipeline", command_id[8:]], "timeout": PIPELINES[command_id[8:]]["timeout"]}
        elif command_id in COMMANDS or command_id == "scan_root":
            spec = COMMANDS.get(command_id, {"argv": ["scripts/inventory_v11.py"], "timeout": 300})
        else:
            raise KeyError(command_id)
        argv = [PY] + list(spec["argv"]) + list(extra or [])
        with self.engine.begin() as conn:
            jid = conn.execute(jobs_t.insert().values(command_id=command_id, args_json=argv[1:], status="queued",
                                                      progress=0, created_by=created_by)).inserted_primary_key[0]
        threading.Thread(target=self._run, args=(jid, argv, spec["timeout"]), daemon=True).start()
        return jid

    def _update(self, jid: int, **values: Any) -> None:
        with self.engine.begin() as conn:
            conn.execute(jobs_t.update().where(jobs_t.c.id == jid).values(**values))

    def _run(self, jid: int, argv: list[str], timeout: int) -> None:
        self._update(jid, status="running", progress=10, started_at=now())
        env = {k: v for k, v in os.environ.items() if not re.search(r"KEY|TOKEN|SECRET|PASSWORD", k, re.IGNORECASE)}
        env["PYTHONPATH"] = f"{self.root / 'src'}{os.pathsep}{self.root}"
        try:
            p = subprocess.run(argv, cwd=self.root, capture_output=True, text=True, timeout=timeout, shell=False, env=env, check=False)
            out = redact_secrets((p.stdout + "\n" + p.stderr).replace(str(self.root), "<repo>"))
            self._update(jid, status="succeeded" if p.returncode == 0 else "failed", progress=100, exit_code=p.returncode,
                         output_tail=out[-8000:], finished_at=now())
        except subprocess.TimeoutExpired:
            self._update(jid, status="timeout", progress=100, exit_code=124, output_tail=f"timed out after {timeout}s",
                         finished_at=now())

    def get(self, jid: int) -> dict[str, Any] | None:
        with self.engine.connect() as conn:
            row = conn.execute(select(jobs_t).where(jobs_t.c.id == jid)).first()
        return dict(row._mapping) if row else None


# ------------------------------------------------------------------ scan input safety
SENSITIVE = re.compile(r"(^|[\\/])(\.env(\..*)?|qcloud\.env)$|\.(pem|key|p12|pfx|jks|keystore)$", re.IGNORECASE)
TEXT_SUFFIXES = {".py", ".java", ".conf", ".cfg", ".cnf", ".yaml", ".yml", ".json", ".properties", ".toml", ".txt", ".sh",
                 ".ini", ".xml", ".gradle", ".md", ""}


class ScanPathError(ValueError):
    pass


def resolve_scan_target(root: Path, roots: dict[str, str], root_id: str, subpath: str) -> Path:
    """Resolve an allow-listed root + subpath; reject traversal, absolute paths, symlinks leaving the root, sensitive files."""
    if root_id not in roots:
        raise ScanPathError("unknown scan root")
    if not isinstance(subpath, str) or len(subpath) > 300 or "\x00" in subpath:
        raise ScanPathError("invalid subpath")
    if Path(subpath).is_absolute() or re.match(r"^[A-Za-z]:", subpath) or ".." in Path(subpath).parts:
        raise ScanPathError("path traversal or absolute path rejected")
    base = (root / roots[root_id]).resolve()
    target = (base / subpath).resolve()
    if target != base and base not in target.parents:
        raise ScanPathError("path escapes the scan root (symlink or traversal)")
    if not target.exists():
        raise ScanPathError("path does not exist")
    if target.is_file() and SENSITIVE.search(target.name):
        raise ScanPathError("sensitive file type is never scanned")
    return target


def check_upload(name: str, size: int, max_bytes: int) -> str:
    safe = Path(name).name
    if not safe or safe != name.replace("\\", "/").split("/")[-1] or ".." in name:
        raise ScanPathError("invalid file name")
    if SENSITIVE.search(safe):
        raise ScanPathError("sensitive file type is never accepted")
    if Path(safe).suffix.lower() not in TEXT_SUFFIXES:
        raise ScanPathError("only text file types are accepted")
    if size > max_bytes:
        raise ScanPathError(f"file larger than {max_bytes} bytes")
    return safe


def safe_relpath(name: str) -> Path:
    """A relative path inside a dataset: no absolute paths, drive letters, traversal or empty parts."""
    parts = [p for p in name.replace("\\", "/").split("/") if p not in ("", ".")]
    if not parts or name.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", name) or ".." in parts or "\x00" in name:
        raise ScanPathError("invalid path in dataset")
    if len(parts) > 20 or any(len(p) > 120 for p in parts):
        raise ScanPathError("path too deep or name too long")
    return Path(*parts)


def ingest_dataset(items: list[tuple[str, bytes]], dest: Path, max_files: int, max_bytes: int) -> dict[str, Any]:
    """Write an uploaded dataset into `dest` (a fresh run folder). `items` are (relative name, bytes); a single .zip is
    unpacked here. Only text file types are kept; sensitive files (.env, keys, keystores), symlinks and anything outside
    the folder are skipped, and the file count and total size are capped (zip bombs stop at the cap)."""
    kept: list[tuple[Path, bytes]] = []
    skipped: list[str] = []
    total = 0

    def take(name: str, data: bytes) -> None:
        nonlocal total
        rel = safe_relpath(name)
        if SENSITIVE.search(rel.name):
            skipped.append(f"{rel.as_posix()}: sensitive file type")
            return
        if rel.suffix.lower() not in TEXT_SUFFIXES or b"\x00" in data[:4096]:
            skipped.append(f"{rel.as_posix()}: not a text file")
            return
        if len(kept) >= max_files:
            raise ScanPathError(f"more than {max_files} files")
        total += len(data)
        if total > max_bytes:
            raise ScanPathError(f"dataset larger than {max_bytes} bytes after unpacking")
        kept.append((rel, data))

    for name, data in items:
        if name.lower().endswith(".zip"):
            try:
                zf = zipfile.ZipFile(io.BytesIO(data))
            except zipfile.BadZipFile:
                raise ScanPathError("not a valid zip file") from None
            with zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    if stat.S_ISLNK(info.external_attr >> 16):
                        skipped.append(f"{clean(info.filename, 120)}: symlink")
                        continue
                    if info.file_size > max_bytes:
                        raise ScanPathError(f"dataset larger than {max_bytes} bytes after unpacking")
                    with zf.open(info) as fh:
                        take(info.filename, fh.read(max_bytes + 1))
        else:
            take(name, data)
    if not kept:
        raise ScanPathError("no supported text files in the upload (configs, source code, manifests)")
    digest = hashlib.sha256()
    for rel, data in sorted(kept):
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        digest.update(rel.as_posix().encode() + b"\x00" + hashlib.sha256(data).digest())
    return {"files": len(kept), "skipped": skipped[:50], "skipped_count": len(skipped), "bytes": total, "sha256": digest.hexdigest()}


def run_outputs(out: Path) -> list[dict[str, Any]]:
    """Downloadable files of one run (relative to its output folder)."""
    if not out.is_dir():
        return []
    return [{"path": p.relative_to(out).as_posix(), "bytes": p.stat().st_size} for p in sorted(out.rglob("*"))
            if p.is_file() and p.suffix in (".json", ".md")]


def remove_tree(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


# ------------------------------------------------------------------ assistant proxy
def assistant_status(url: str) -> dict[str, Any]:
    import httpx

    try:
        h = httpx.get(f"{url}/health", timeout=2.0).json()
        return {"reachable": True, "mode": h.get("mode", "unknown"), "label": h.get("label", ""),
                "key_configured": bool(h.get("sarvam_key_configured")), "cloud_for_custom_scans": bool(h.get("cloud_for_custom_scans")),
                "usage": h.get("usage", {})}
    except Exception:  # noqa: BLE001 - any failure means "not reachable"
        return {"reachable": False, "mode": "TEMPLATE_FALLBACK", "label": "in-process template fallback", "key_configured": False,
                "cloud_for_custom_scans": False, "usage": {}}


def ask_assistant(url: str, question: str, plan: dict[str, Any] | None) -> dict[str, Any]:
    """Forward to Member 3's service on 127.0.0.1; if it is down, answer in-process in TEMPLATE_FALLBACK (no network)."""
    import httpx

    try:
        r = httpx.post(f"{url}/ask", json={"question": question}, timeout=45.0)
        r.raise_for_status()
        res = r.json()
        res.setdefault("mode", "TEMPLATE_FALLBACK")
        res["via"] = "assistant service (127.0.0.1)"
    except Exception:  # noqa: BLE001
        if not plan:
            return {"answer": "unknown: no report bundle loaded", "citations": [], "mode": "TEMPLATE_FALLBACK", "refused": False,
                    "mode_reason": "assistant service unavailable and no plan", "via": "in-process"}
        from cryptoshift.agent.assistant import Assistant

        res = Assistant(plan).answer(question)
        res["mode_reason"] = "assistant service unavailable; in-process template fallback"
        res["via"] = "in-process"
    return {"answer": clean(res.get("answer", ""), 4000), "citations": [clean(c, 120) for c in res.get("citations", [])][:40],
            "mode": res.get("mode", "TEMPLATE_FALLBACK"), "mode_reason": clean(res.get("mode_reason") or res.get("validator") or "", 300),
            "refused": bool(res.get("refused")), "usage": res.get("usage") or {}, "via": res.get("via", "")}


def plan_hash_of(plan: dict[str, Any]) -> str:
    from cryptoshift.planning.planner import plan_hash

    return plan_hash(plan)


def json_dump(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, default=str)

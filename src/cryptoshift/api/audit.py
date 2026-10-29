"""Append-only, hash-chained audit log.

entry_hash = SHA-256(prev_hash + canonical JSON of the entry fields). The first entry chains to 64 zeros.
`verify()` recomputes every hash in order and reports the first entry that does not match (tampering).
"""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Engine

from cryptoshift.api.db import audit_log

GENESIS = "0" * 64
FIELDS = ("ts", "request_id", "actor", "role", "action", "target", "result", "detail_json")
_lock = threading.Lock()


def _hash(prev: str, entry: dict[str, Any]) -> str:
    canon = json.dumps({k: entry[k] for k in FIELDS}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256((prev + canon).encode("utf-8")).hexdigest()


def append(engine: Engine, *, request_id: str, actor: str, role: str, action: str, target: str, result: str,
           detail: dict[str, Any] | None = None) -> dict[str, Any]:
    entry = {"ts": datetime.now(UTC).isoformat(timespec="milliseconds"), "request_id": request_id,
             "actor": actor[:64], "role": role[:16], "action": action[:64], "target": target[:256], "result": result[:32],
             "detail_json": json.dumps(detail or {}, sort_keys=True, ensure_ascii=False)[:4000]}
    with _lock, engine.begin() as conn:
        last = conn.execute(select(audit_log.c.entry_hash).order_by(audit_log.c.id.desc()).limit(1)).scalar()
        prev = last or GENESIS
        entry["prev_hash"], entry["entry_hash"] = prev, _hash(prev, entry)
        entry["id"] = conn.execute(audit_log.insert().values(**entry)).inserted_primary_key[0]
    return entry


def verify(engine: Engine) -> dict[str, Any]:
    prev, n = GENESIS, 0
    with engine.connect() as conn:
        for row in conn.execute(select(audit_log).order_by(audit_log.c.id)):
            e = dict(row._mapping)
            n += 1
            if e["prev_hash"] != prev or _hash(prev, e) != e["entry_hash"]:
                return {"valid": False, "entries": n, "first_bad_id": e["id"]}
            prev = e["entry_hash"]
    return {"valid": True, "entries": n, "first_bad_id": None}

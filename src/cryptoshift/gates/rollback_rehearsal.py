"""Rollback rehearsal on a COPY of a TLS profile (never the original or scanned code).

1. Snapshot the copied nginx profile (SHA-256).
2. Apply the proposed change to the copy (patch preview): `ssl_ecdh_curve` -> hybrid-only X25519MLKEM768.
3. Gate check: a classical-only peer (groups from the original profile) handshakes with a loopback server
   configured from the patched copy. A rejection is a gate FAILURE and triggers rollback.
4. Restore the copy from the snapshot and verify the hash.
5. Recovery check: re-run the classical handshake against a server configured from the restored copy.
Warns when the restored profile still contains deprecated SHA-1/3DES material.
"""

from __future__ import annotations

import difflib
import hashlib
import re
import shutil
from pathlib import Path
from typing import Any, Dict

from cryptoshift.gates import openssl_lab as lab

CURVE_RE = re.compile(r"^(\s*ssl_ecdh_curve\s+)([^;]+)(;.*)$", re.M)
NGINX_TO_OPENSSL = {"prime256v1": "P-256", "secp256r1": "P-256", "secp384r1": "P-384", "secp521r1": "P-521"}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def groups_from_profile(text: str) -> str:
    m = CURVE_RE.search(text)
    names = m.group(2).strip().split(":") if m else ["X25519"]
    return ":".join(NGINX_TO_OPENSSL.get(n, n) for n in names)


def rehearse(original: Path, proposed_curve: str = "X25519MLKEM768") -> Dict[str, Any]:
    orig_hash_before = _sha(original)
    with lab.lab_dir() as d:
        copy = d / original.name
        snapshot = d / (original.name + ".snapshot")
        shutil.copy2(original, copy)
        shutil.copy2(copy, snapshot)
        snap_hash = _sha(snapshot)
        before_text = copy.read_text(encoding="utf-8")
        classical_groups = groups_from_profile(before_text)

        patched = CURVE_RE.sub(lambda m: f"{m.group(1)}{proposed_curve}{m.group(3)}", before_text, count=1)
        copy.write_text(patched, encoding="utf-8")
        preview = "".join(difflib.unified_diff(before_text.splitlines(True), patched.splitlines(True),
                                               "profile (snapshot)", "profile (patched copy)"))
        cert = lab.make_cert(d, "rb")
        gate = lab.handshake(cert, groups_from_profile(patched), classical_groups)
        forced_failure = not gate["handshake_ok"]

        shutil.copy2(snapshot, copy)
        restored_ok = _sha(copy) == snap_hash
        recovery = lab.handshake(cert, groups_from_profile(copy.read_text(encoding="utf-8")), classical_groups)

    restored_text = before_text
    warnings = []
    if re.search(r"DES-CBC3|3DES", restored_text):
        warnings.append("Restored profile still enables 3DES (DES-CBC3-SHA); NIST SP 800-131A disallows it - compensating control or cipher clean-up needed")
    if re.search(r"sha1|SHA1", restored_text):
        warnings.append("Restored profile references SHA-1; do not restore SHA-1 based configurations")
    return {
        "label": "TEST SCENARIO, loopback, test keys; rehearsal on a temporary COPY",
        "profile": original.name,
        "snapshot_sha256": snap_hash,
        "change_preview": preview,
        "trigger": "compatibility gate: classical-only peer must still connect after the change",
        "gate_check": {k: gate[k] for k in ("handshake_ok", "group", "errors", "command", "server_groups", "client_groups")},
        "forced_failure_detected": forced_failure,
        "rollback_action": f"restore {original.name} copy from snapshot {snap_hash[:12]}",
        "restored_hash_matches_snapshot": restored_ok,
        "recovery_check": {k: recovery[k] for k in ("handshake_ok", "protocol", "group", "command", "server_groups", "client_groups")},
        "recovered": bool(recovery["handshake_ok"]),
        "originals_unchanged": _sha(original) == orig_hash_before,
        "warnings": warnings,
    }

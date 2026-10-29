#!/usr/bin/env python3
"""Phase 4: real loopback verification evidence (OpenSSL 3.5+) + gate evaluation for the Phase 2 plan.

Writes scratch/derived/member3/verification_evidence.json and gate_results.json (git-ignored).
TEST SCENARIO only: 127.0.0.1, throw-away keys generated in a temp dir that is deleted afterwards.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from cryptoshift.gates import openssl_lab as lab  # noqa: E402
from cryptoshift.gates.rollback_rehearsal import rehearse  # noqa: E402
from cryptoshift.gates.verification_gates import THRESHOLDS, evaluate_plan  # noqa: E402
from cryptoshift.planning.planner import build_problem  # noqa: E402

OUT = ROOT / "scratch" / "derived" / "member3"
PROFILE = ROOT / "demo_bank_app" / "configs" / "interbank_tls_nginx.conf"


def collect(n: int = 30, warmup: int = 5) -> dict:
    caps = lab.capabilities()
    ev = {"capabilities": caps, "thresholds_assumed": THRESHOLDS}
    if not caps.get("available") or not caps.get("x25519mlkem768_tls_group"):
        ev["status"] = "BLOCKED: OpenSSL 3.5+ with X25519MLKEM768 not available; Docker route PLANNED"
        return ev
    with lab.lab_dir() as d:
        ev["selftests"] = [lab.mlkem_roundtrip_openssl(d), lab.mlkem_roundtrip_cryptography(),
                           lab.mldsa_sign_verify_openssl(d), lab.mldsa_sign_verify_cryptography()]
        ev["deterministic_kats"] = lab.deterministic_kat_vectors()
        ev["service_stack_integration"] = lab.service_stack_integration_checks()
        ev["in_process_timing"] = lab.in_process_crypto_timing()
        ev["traces"] = lab.traces(d)
        ev["compatibility_matrix"] = lab.compatibility_matrix(d)
        ev["overhead"] = lab.overhead(d, n=n, warmup=warmup)
    ev["rollback_rehearsal"] = rehearse(PROFILE)
    return ev


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--warmup", type=int, default=5)
    a = ap.parse_args()
    ev = collect(a.n, a.warmup)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "verification_evidence.json").write_text(json.dumps(ev, indent=2), encoding="utf-8")
    steps = evaluate_plan(build_problem()["services"], ev)
    (OUT / "gate_results.json").write_text(json.dumps(steps, indent=2), encoding="utf-8")

    print("capabilities:", ev["capabilities"])
    for t in ev.get("selftests", []):
        print("selftest:", t["implementation"], t["algorithm"], t["status"], {k: t[k] for k in t if k.endswith("bytes")})
    for k, t in (ev.get("traces") or {}).items():
        if isinstance(t, dict) and "handshake_ok" in t:
            print(f"trace {k}: ok={t['handshake_ok']} {t.get('protocol')} group={t.get('group')} cipher={t.get('cipher')} "
                  f"read={t.get('bytes_read')} written={t.get('bytes_written')} sig={t.get('peer_signature_type')}")
            print(f"   client: {t.get('command')}")
    for r in ev.get("compatibility_matrix", []):
        print(f"compat {'PASS' if r['pass'] else 'FAIL'} | {r['case']} | expected {r['expected']} | observed {r['observed'][:90]}")
    if "overhead" in ev:
        print("overhead:", json.dumps(ev["overhead"]["results"]))
        print("   env:", ev["overhead"]["environment"])
    rb = ev.get("rollback_rehearsal", {})
    print("rollback:", {k: rb.get(k) for k in ("forced_failure_detected", "restored_hash_matches_snapshot", "recovered", "originals_unchanged", "warnings")})
    for s in steps:
        print(f"step {s['step_id']}: {s['state']} purposes={s['purposes']} blocking={s['blocking_gates']}")

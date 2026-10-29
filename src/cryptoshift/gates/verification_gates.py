"""Evidence-consuming verification gates (Member 3). Replaces fixed boolean flags for the Member 3 pipeline.

Each gate returns {"gate", "status": PASS|FAIL|BLOCKED, "evidence", "reason"}. A migration step may reach READY
only if every gate it requires PASSes. Required gates depend on the step's detected purposes:
- key_establishment -> ML-KEM self-test, hybrid handshake, compatibility matrix, overhead
- digital_signature -> ML-DSA self-test
- every step        -> purpose resolved (no HOLD findings, scanned evidence present), rollback rehearsal
Thresholds are ASSUMPTIONS (docs/member3/assumptions.md).
"""

from __future__ import annotations

from typing import Any, Dict, List

THRESHOLDS = {"max_median_time_ratio": 1.5, "max_extra_handshake_bytes": 4096}  # ASSUMPTION
EVIDENCE_FILE = "scratch/derived/member3/verification_evidence.json"


def _g(gate: str, ok: bool, evidence: str, reason: str, blocked: bool = False) -> Dict[str, Any]:
    return {"gate": gate, "status": "BLOCKED" if blocked else ("PASS" if ok else "FAIL"), "evidence": evidence, "reason": reason}


def gate_mlkem_selftest(ev: Dict[str, Any]) -> Dict[str, Any]:
    tests = [t for t in ev.get("selftests", []) if t.get("algorithm") == "ML-KEM-768"]
    if not tests:
        return _g("mlkem_roundtrip_selftest", False, EVIDENCE_FILE, "no ML-KEM self-test result", blocked=True)
    ok = all(t["status"] == "PASS" for t in tests)
    return _g("mlkem_roundtrip_selftest", ok, f"{EVIDENCE_FILE}#selftests",
              f"{sum(t['status'] == 'PASS' for t in tests)}/{len(tests)} ML-KEM-768 round-trip self-tests passed (not NIST KATs)")


def gate_mldsa_selftest(ev: Dict[str, Any]) -> Dict[str, Any]:
    tests = [t for t in ev.get("selftests", []) if t.get("algorithm") == "ML-DSA-65"]
    if not tests:
        return _g("mldsa_sign_verify_selftest", False, EVIDENCE_FILE, "no ML-DSA self-test result", blocked=True)
    ok = all(t["status"] == "PASS" for t in tests)
    return _g("mldsa_sign_verify_selftest", ok, f"{EVIDENCE_FILE}#selftests",
              f"{sum(t['status'] == 'PASS' for t in tests)}/{len(tests)} ML-DSA-65 sign/verify self-tests passed (incl. tamper rejection)")


def gate_hybrid_handshake(ev: Dict[str, Any]) -> Dict[str, Any]:
    t = (ev.get("traces") or {}).get("after_hybrid")
    if not t:
        return _g("hybrid_handshake", False, EVIDENCE_FILE, "no hybrid handshake trace", blocked=True)
    ok = bool(t.get("handshake_ok")) and t.get("group") == "X25519MLKEM768" and t.get("protocol") == "TLSv1.3"
    return _g("hybrid_handshake", ok, f"{EVIDENCE_FILE}#traces.after_hybrid",
              f"loopback handshake ok={t.get('handshake_ok')}, protocol={t.get('protocol')}, group={t.get('group')}")


def gate_compatibility(ev: Dict[str, Any]) -> Dict[str, Any]:
    rows = ev.get("compatibility_matrix") or []
    if not rows:
        return _g("compatibility_matrix", False, EVIDENCE_FILE, "no compatibility matrix", blocked=True)
    failed = [r["case"] for r in rows if not r["pass"]]
    return _g("compatibility_matrix", not failed, f"{EVIDENCE_FILE}#compatibility_matrix",
              f"{len(rows) - len(failed)}/{len(rows)} cases matched expectation" + (f"; failed: {failed}" if failed else ""))


def gate_overhead(ev: Dict[str, Any], thresholds: Dict[str, float] = THRESHOLDS) -> Dict[str, Any]:
    o = (ev.get("overhead") or {}).get("results") or {}
    c, h = o.get("classical_X25519"), o.get("hybrid_X25519MLKEM768")
    if not c or not h or not c.get("median_ms") or not h.get("median_ms"):
        return _g("overhead", False, EVIDENCE_FILE, "no overhead measurement", blocked=True)
    ratio = h["median_ms"] / c["median_ms"]
    extra = max(h["bytes_read"]) + max(h["bytes_written"]) - max(c["bytes_read"]) - max(c["bytes_written"])
    ok = ratio <= thresholds["max_median_time_ratio"] and extra <= thresholds["max_extra_handshake_bytes"]
    return _g("overhead", ok, f"{EVIDENCE_FILE}#overhead",
              f"median ratio {ratio:.3f} (limit {thresholds['max_median_time_ratio']}, ASSUMPTION); extra handshake bytes "
              f"{extra} (limit {thresholds['max_extra_handshake_bytes']}, ASSUMPTION); loopback only")


def gate_rollback(ev: Dict[str, Any]) -> Dict[str, Any]:
    r = ev.get("rollback_rehearsal")
    if not r:
        return _g("rollback_rehearsal", False, EVIDENCE_FILE, "no rollback rehearsal", blocked=True)
    ok = bool(r.get("recovered")) and bool(r.get("originals_unchanged")) and bool(r.get("restored_hash_matches_snapshot"))
    return _g("rollback_rehearsal", ok, f"{EVIDENCE_FILE}#rollback_rehearsal",
              f"forced failure detected={r.get('forced_failure_detected')}, restored hash matches={r.get('restored_hash_matches_snapshot')}, "
              f"classical recovery handshake ok={r.get('recovered')}, originals unchanged={r.get('originals_unchanged')}")


def gate_purpose_resolved(service: Dict[str, Any]) -> Dict[str, Any]:
    if service.get("evidence_source") != "OBSERVED":
        return _g("purpose_resolved", False, "plan#services." + service["service_id"],
                  "no scanned evidence (DECLARED_ONLY): operation purposes unverified -> HOLD")
    holds = service.get("hold_finding_ids") or []
    return _g("purpose_resolved", not holds, "plan#services." + service["service_id"],
              "all findings have a resolved purpose" if not holds else f"HOLD findings need human purpose review: {holds}")


def purposes(service: Dict[str, Any]) -> List[str]:
    return sorted({p for _, p in service.get("features", {}).get("group_purpose_pairs", [])})


def evaluate_step(service: Dict[str, Any], ev: Dict[str, Any]) -> Dict[str, Any]:
    p = purposes(service)
    gates = [gate_purpose_resolved(service), gate_rollback(ev)]
    if "key_establishment" in p:
        gates += [gate_mlkem_selftest(ev), gate_hybrid_handshake(ev), gate_compatibility(ev), gate_overhead(ev)]
    if "digital_signature" in p:
        gates.append(gate_mldsa_selftest(ev))
    ready = all(g["status"] == "PASS" for g in gates)
    return {"step_id": f"migrate:{service['service_id']}", "service_id": service["service_id"],
            "purposes": p, "gates": gates, "state": "READY" if ready else "PROPOSED",
            "blocking_gates": [g["gate"] for g in gates if g["status"] != "PASS"],
            "evidence_scope": EVIDENCE_SCOPE}


EVIDENCE_SCOPE = ("Generic loopback lab evidence (OpenSSL 3.5 s_server/s_client, test keys). It does NOT exercise the "
                  "service's own stack (e.g. KMS key wrapping, JWT libraries, partner peers); READY means 'eligible for "
                  "human review', not 'verified in production'.")


def evaluate_plan(services: Dict[str, Dict[str, Any]], ev: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [evaluate_step(s, ev) for _, s in sorted(services.items())]

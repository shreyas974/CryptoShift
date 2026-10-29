"""Member 3 verification tests: gates (incl. failures), approval invalidation, rollback recovery, loopback TLS."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT / "src"), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from cryptoshift.gates import openssl_lab as lab  # noqa: E402
from cryptoshift.gates.approval import ApprovalError, approval_status, approve  # noqa: E402
from cryptoshift.gates.verification_gates import (  # noqa: E402
    evaluate_step, gate_compatibility, gate_overhead, gate_purpose_resolved,
)

HAVE_PQC_OPENSSL = bool(lab.capabilities().get("x25519mlkem768_tls_group"))

GOOD_EV = {
    "selftests": [{"algorithm": "ML-KEM-768", "status": "PASS"}, {"algorithm": "ML-DSA-65", "status": "PASS"}],
    "traces": {"after_hybrid": {"handshake_ok": True, "group": "X25519MLKEM768", "protocol": "TLSv1.3"}},
    "compatibility_matrix": [{"case": "c1", "pass": True}],
    "overhead": {"results": {
        "classical_X25519": {"median_ms": 10.0, "bytes_read": [756], "bytes_written": [388]},
        "hybrid_X25519MLKEM768": {"median_ms": 11.0, "bytes_read": [1844], "bytes_written": [1564]}}},
    "rollback_rehearsal": {"recovered": True, "originals_unchanged": True, "restored_hash_matches_snapshot": True},
}
SERVICE = {"service_id": "svc", "evidence_source": "OBSERVED", "hold_finding_ids": [],
           "features": {"group_purpose_pairs": [["EC", "key_establishment"], ["RSA", "digital_signature"]]}}


class GateTests(unittest.TestCase):
    def test_all_required_gates_pass_gives_ready(self) -> None:
        s = evaluate_step(SERVICE, GOOD_EV)
        self.assertEqual(s["state"], "READY", s["blocking_gates"])
        self.assertIn("NOT exercise", s["evidence_scope"])

    def test_failed_compatibility_blocks_ready(self) -> None:
        ev = copy.deepcopy(GOOD_EV)
        ev["compatibility_matrix"].append({"case": "neg", "pass": False})
        self.assertEqual(gate_compatibility(ev)["status"], "FAIL")
        self.assertEqual(evaluate_step(SERVICE, ev)["state"], "PROPOSED")

    def test_overhead_threshold_failure(self) -> None:
        ev = copy.deepcopy(GOOD_EV)
        ev["overhead"]["results"]["hybrid_X25519MLKEM768"]["median_ms"] = 99.0
        self.assertEqual(gate_overhead(ev)["status"], "FAIL")

    def test_missing_evidence_is_blocked_not_pass(self) -> None:
        s = evaluate_step(SERVICE, {})
        self.assertEqual(s["state"], "PROPOSED")
        self.assertTrue(all(g["status"] in ("BLOCKED", "FAIL") for g in s["gates"] if g["gate"] != "purpose_resolved"))

    def test_hold_and_declared_only_never_ready(self) -> None:
        held = {**SERVICE, "hold_finding_ids": ["INV-0001"]}
        self.assertEqual(gate_purpose_resolved(held)["status"], "FAIL")
        self.assertEqual(evaluate_step(held, GOOD_EV)["state"], "PROPOSED")
        declared = {**SERVICE, "evidence_source": "DECLARED_ONLY"}
        self.assertEqual(evaluate_step(declared, GOOD_EV)["state"], "PROPOSED")


class ApprovalTests(unittest.TestCase):
    def _plan(self) -> dict:
        return {"services": {"svc": {"x": 1}}, "edges": [], "schedule": {"waves": {"0": ["svc"]}},
                "steps": [{"step_id": "migrate:svc", "state": "READY"}, {"step_id": "migrate:other", "state": "PROPOSED"}]}

    def test_approve_ready_then_invalidate_on_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "approvals.json"
            plan = self._plan()
            rec = approve(plan, ["migrate:svc"], "TEST-ONLY", store)
            self.assertEqual(rec["approver"], "TEST-ONLY")
            st = approval_status(plan, store)
            self.assertEqual(st["approved_steps"], ["migrate:svc"])
            self.assertEqual(plan["steps"][0]["state"], "APPROVED")

            changed = self._plan()
            changed["schedule"]["waves"]["0"] = ["svc", "other"]
            st2 = approval_status(changed, store)
            self.assertEqual(st2["approved_steps"], [])
            self.assertEqual(len(st2["invalidated_approvals"]), 1)
            self.assertEqual(changed["steps"][0]["state"], "READY")

    def test_cannot_approve_non_ready_or_without_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "a.json"
            with self.assertRaises(ApprovalError):
                approve(self._plan(), ["migrate:other"], "TEST-ONLY", store)
            with self.assertRaises(ApprovalError):
                approve(self._plan(), ["migrate:svc"], "  ", store)
            self.assertFalse(store.exists())


@unittest.skipUnless(HAVE_PQC_OPENSSL, "OpenSSL 3.5+ with X25519MLKEM768 not available")
class LoopbackTests(unittest.TestCase):
    def test_hybrid_only_server_rejects_classical_client(self) -> None:
        with lab.lab_dir() as d:
            cert = lab.make_cert(d, "t")
            bad = lab.handshake(cert, "X25519MLKEM768", "X25519")
            good = lab.handshake(cert, "X25519MLKEM768", "X25519MLKEM768")
        self.assertFalse(bad["handshake_ok"])
        self.assertTrue(good["handshake_ok"])
        self.assertEqual(good["group"], "X25519MLKEM768")
        self.assertNotIn("Users", good["command"] + good["server_command"])

    def test_rollback_rehearsal_recovers_and_leaves_original_untouched(self) -> None:
        from cryptoshift.gates.rollback_rehearsal import rehearse

        with tempfile.TemporaryDirectory() as tmp:
            prof = Path(tmp) / "site.conf"
            prof.write_text("server {\n  ssl_ecdh_curve X25519;\n  ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256;\n}\n", encoding="utf-8")
            before = prof.read_bytes()
            r = rehearse(prof)
            self.assertEqual(prof.read_bytes(), before)
        self.assertTrue(r["forced_failure_detected"])
        self.assertTrue(r["restored_hash_matches_snapshot"])
        self.assertTrue(r["recovered"])
        self.assertTrue(r["originals_unchanged"])


class DeterministicKatAndStackTests(unittest.TestCase):
    def test_deterministic_seed_kat_vectors_pass(self) -> None:
        kats = lab.deterministic_kat_vectors()
        self.assertEqual(len(kats), 2)
        for k in kats:
            self.assertEqual(k["status"], "PASS", k)
            self.assertEqual(k["expected_pubkey_sha256"], k["observed_pubkey_sha256"])

    def test_service_stack_kms_and_jws_integration_pass(self) -> None:
        checks = lab.service_stack_integration_checks()
        self.assertEqual(len(checks), 2)
        for c in checks:
            self.assertEqual(c["status"], "PASS", c)
            self.assertTrue(c["roundtrip_ok"])
            self.assertTrue(c["tamper_rejected"])

    def test_in_process_crypto_timing_measures_all_primitives(self) -> None:
        res = lab.in_process_crypto_timing(iterations=10)
        self.assertIn("ML-KEM-768_encap+decap", res["operations"])
        self.assertIn("ML-DSA-65_sign+verify", res["operations"])
        for op, stats in res["operations"].items():
            self.assertGreater(stats["median_us"], 0.0, op)


if __name__ == "__main__":
    unittest.main()

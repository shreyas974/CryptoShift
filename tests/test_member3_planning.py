"""Member 3 planning tests: edge provenance, cycles, score reasons, HOLD for unknown purpose."""

from __future__ import annotations

import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT / "src"), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from cryptoshift.models import CryptoFinding, MigrationTask, WaveScheduleConfig  # noqa: E402
from cryptoshift.optimization.fallback_scheduler import solve_with_fallback_scheduler  # noqa: E402
from cryptoshift.planning.dependency_graph import _edge, analyse_graph, build_graph  # noqa: E402
from cryptoshift.planning.planner import build_problem, candidate_for, schedule, sensitivity  # noqa: E402


class PlanningOnDemoBankTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.p = build_problem()

    def test_every_edge_has_provenance_and_observed_edges_have_file_and_line(self) -> None:
        self.assertTrue(self.p["edges"])
        for e in self.p["edges"]:
            self.assertIn(e["provenance"], ("OBSERVED", "DECLARED", "INFERRED"))
            if e["provenance"] == "OBSERVED":
                self.assertTrue(e["file"] and e["line"], e)
                self.assertFalse(Path(e["file"]).is_absolute())
        obs = {(e["upstream"], e["downstream"]) for e in self.p["edges"] if e["provenance"] == "OBSERVED"}
        self.assertIn(("ledger_audit", "interbank_tls"), obs)  # nginx proxy_pass

    def test_observed_vs_declared_conflict_reported(self) -> None:
        issues = {(c["upstream"], c["downstream"]) for c in self.p["graph_analysis"]["conflicts"]}
        self.assertIn(("ledger_audit", "interbank_tls"), issues)

    def test_score_reason_lists_every_input(self) -> None:
        for s in self.p["services"].values():
            for k in ("crypto_exposure", "network_exposure", "criticality", "dependents", "verification_readiness"):
                self.assertIn(k, s["risk"]["reason"])
            self.assertEqual(s["risk"]["label"], "PROVISIONAL, UNVALIDATED")

    def test_schedule_has_no_dependency_violations(self) -> None:
        s = schedule(self.p)
        self.assertTrue(s["feasible"])
        self.assertEqual(s["dependency_violations"], [])
        self.assertEqual(s["constraint_violations"], [])

    def test_sensitivity_runs_every_weight_both_ways(self) -> None:
        sa = sensitivity(self.p)
        self.assertEqual(sa["n_runs"], 2 * len(self.p["config"]["risk_weights"]))


class GraphEdgeCaseTests(unittest.TestCase):
    def test_cycle_is_reported_not_hidden(self) -> None:
        g = build_graph(["a", "b", "c"], [_edge("a", "b", "OBSERVED", "x.conf", 1), _edge("b", "a", "DECLARED")])
        res = analyse_graph(g, ["OBSERVED", "DECLARED"])
        self.assertTrue(res["has_cycles"])
        self.assertEqual(sorted(res["cycles"][0]), ["a", "b"])
        # With "upstream no later than downstream", a 2-cycle forces both services into the same wave.
        tasks = [MigrationTask("a", "a", [], [], ["b"], 10, 1.0, 1.0, True, "HIGH"),
                 MigrationTask("b", "b", [], [], ["a"], 10, 1.0, 1.0, True, "HIGH")]
        r = solve_with_fallback_scheduler(tasks, WaveScheduleConfig(num_waves=2, max_services_per_wave=2))
        self.assertTrue(r.feasible)
        self.assertEqual(r.task_to_wave["a"], r.task_to_wave["b"])

    def test_inferred_edge_and_unknown_endpoint_from_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "svc_x.yaml").write_text(textwrap.dedent("""\
                service_id: svc_x
                depends_on: [external_thing]
                notes:
                  peer: tokens are validated against auth_gateway
                  upstream_url: https://partner-bank.example:443/api
            """), encoding="utf-8")
            p = build_problem(d)
        inferred = [e for e in p["edges"] if e["provenance"] == "INFERRED"]
        self.assertEqual([(e["upstream"], e["downstream"]) for e in inferred], [("auth_gateway", "svc_x")])
        self.assertIn("direction assumed", inferred[0]["reason"])
        # Unknown endpoints now come from Member 2's relationship evidence, which keeps the full unresolved host.
        endpoints = {u["endpoint"] for u in p["unknown_endpoints"]}
        self.assertEqual(endpoints, {"external_thing", "partner-bank.example"})
        self.assertTrue(all(u["file"] and u["line"] for u in p["unknown_endpoints"]))


class Member2RelationshipTests(unittest.TestCase):
    def test_multiservice_fixture_edges_are_observed_with_file_and_line(self) -> None:
        fixture = Path(__file__).resolve().parent / "fixtures" / "multiservice_bank"
        p = build_problem(fixture, include_declared=False)
        observed = {(e["upstream"], e["downstream"]) for e in p["edges"] if e["provenance"] == "OBSERVED"}
        self.assertIn(("ledger", "payments"), observed)   # payments consumes ledger
        self.assertIn(("payments", "gateway"), observed)  # gateway proxies to payments
        self.assertTrue(all(e["file"] and e["line"] for e in p["edges"] if e["provenance"] == "OBSERVED"))
        self.assertIn("fraud-scoring.partner.example", {u["endpoint"] for u in p["unknown_endpoints"]})
        self.assertFalse(p["graph_analysis"]["has_cycles"])
        self.assertEqual(sorted(p["services"]), ["edge", "gateway", "ledger", "payments"])  # compose file is not a service
        self.assertTrue(p["unattributed_finding_ids"])  # scripts/rotate_keys.sh stays unknown and is reported


class HoldTests(unittest.TestCase):
    def test_unknown_purpose_yields_hold_never_pqc(self) -> None:
        f = CryptoFinding("F1", "s", "a.py", 3, "RSA", "t", "ML-DSA-65 (should be ignored)", "x", "MEDIUM",
                          operation_purpose="unknown")
        self.assertTrue(candidate_for(f).startswith("HOLD"))

    def test_keygen_finding_in_scanned_code_is_held(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "keys.py").write_text(
                "SERVICE_ID = 'svc_k'\nfrom cryptography.hazmat.primitives.asymmetric import rsa\n"
                "k = rsa.generate_private_key(public_exponent=65537, key_size=2048)\n", encoding="utf-8")
            p = build_problem(d, include_declared=False)
        s = p["services"]["svc_k"]
        self.assertTrue(s["hold_finding_ids"])
        self.assertTrue(all(t.startswith("HOLD") for t in s["candidate_targets"]))


if __name__ == "__main__":
    unittest.main()

"""Offline unit and smoke tests for CryptoShift (PQC-01)."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cryptoshift.dependencies import validate_dependency_order  # noqa: E402
from cryptoshift.metrics import evaluate_labelled_dataset  # noqa: E402
from cryptoshift.models import WaveScheduleConfig  # noqa: E402
from cryptoshift.optimization.auth_check import redact_secrets  # noqa: E402
from cryptoshift.optimization.fallback_scheduler import (  # noqa: E402
    solve_with_fallback_scheduler,
)
from cryptoshift.rules import resolve_contextual_pqc_rule  # noqa: E402
from cryptoshift.scoring import build_migration_tasks  # noqa: E402


class CryptoShiftPrototypeTests(unittest.TestCase):
    def test_contextual_pqc_roles_distinguish_kem_vs_dsa(self) -> None:
        sig_rule = resolve_contextual_pqc_rule("RSA-2048", "digital_signature")
        kem_rule = resolve_contextual_pqc_rule("RSA-2048", "key_establishment")
        unk_rule = resolve_contextual_pqc_rule("RSA-2048", "unknown")

        self.assertIn("ML-DSA-65", sig_rule["target_pqc"])
        self.assertIn("FIPS 204", sig_rule["nist_standard"])
        self.assertIn("ML-KEM-768", kem_rule["target_pqc"])
        self.assertIn("FIPS 203", kem_rule["nist_standard"])
        self.assertIn("HOLD", unk_rule["target_pqc"])

    def test_deterministic_fallback_scheduler_respects_dependencies_and_capacity(self) -> None:
        tasks = build_migration_tasks()
        cfg = WaveScheduleConfig()
        res = solve_with_fallback_scheduler(tasks, cfg)

        self.assertTrue(res.feasible)
        self.assertAlmostEqual(res.objective_value or 0.0, 248.105, places=3)
        dep_ok, violations = validate_dependency_order(tasks, res.task_to_wave)
        self.assertTrue(dep_ok, msg=f"Unexpected dependency violations: {violations}")
        self.assertEqual(res.waves[0], ["interbank_tls", "ledger_audit"])

    def test_labelled_synthetic_dataset_evaluation_counts(self) -> None:
        eval_res = evaluate_labelled_dataset(ROOT)
        counts = eval_res["counts"]
        self.assertEqual(counts["TP"], 7)
        self.assertEqual(counts["FP"], 1)
        self.assertEqual(counts["FN"], 1)
        self.assertEqual(counts["TN"], 2)
        self.assertAlmostEqual(eval_res["metrics"]["precision"], 0.875, places=4)
        self.assertAlmostEqual(eval_res["metrics"]["recall"], 0.875, places=4)

    def test_secret_redaction_removes_tokens_and_user_paths(self) -> None:
        raw = "Error with api_key='secret_token_12345' Bearer abcdef9876 at C:\\Users\\alice\\project"
        cleaned = redact_secrets(raw)
        self.assertNotIn("secret_token_12345", cleaned)
        self.assertNotIn("abcdef9876", cleaned)
        self.assertNotIn("C:\\Users\\alice", cleaned)
        self.assertIn("[REDACTED]", cleaned)


if __name__ == "__main__":
    unittest.main()


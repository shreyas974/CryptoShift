"""Focused tests for real-dataset loaders, HDF5 streaming, config parsing provenance, human approval, and verification/rollback."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cryptoshift.datasets import (  # noqa: E402
    EXPECTED_CESNET_BYTES,
    EXPECTED_CESNET_ROWS,
    EXPECTED_CESNET_SHA256,
    load_banking_pqc_observations,
    resolve_dataset_paths,
    stream_cesnet_tls22_chunks,
    summarize_banking_pqc_observations,
    summarize_cesnet_tls22_streaming,
)
from cryptoshift.mvp_slice import DEFAULT_CONFIGS_DIR, run_mvp_vertical_slice  # noqa: E402
from cryptoshift.scanner import (  # noqa: E402
    scan_nginx_config_file,
    scan_repository_path,
    scan_yaml_config_file,
)


class CryptoShiftRealDataAndMVPSliceTests(unittest.TestCase):
    def test_nginx_and_yaml_parsing_provenance_and_pqc_role_separation(self) -> None:
        nginx_path = DEFAULT_CONFIGS_DIR / "interbank_tls_nginx.conf"
        ngx_findings, ngx_meta = scan_nginx_config_file(nginx_path)
        self.assertEqual(ngx_meta["service_id"], "interbank_tls")
        self.assertIn("ledger_audit", ngx_meta["dependencies"])
        self.assertEqual(len(ngx_findings), 3)

        by_purpose = {f.operation_purpose: f for f in ngx_findings}
        # Key establishment -> FIPS 203 ML-KEM (X25519MLKEM768)
        self.assertIn("MLKEM768", by_purpose["key_establishment"].target_pqc_algorithm)
        self.assertIn("FIPS 203 (ML-KEM)", by_purpose["key_establishment"].nist_standard)
        self.assertEqual(by_purpose["key_establishment"].line_number, 11)

        # Digital signature -> FIPS 204 ML-DSA
        self.assertIn("ML-DSA", by_purpose["digital_signature"].target_pqc_algorithm)
        self.assertIn("FIPS 204", by_purpose["digital_signature"].nist_standard)
        self.assertEqual(by_purpose["digital_signature"].line_number, 16)

        # Mixed-posture YAML file: contains X25519MLKEM768 but still has RSA_OAEP and 3DES
        vault_path = DEFAULT_CONFIGS_DIR / "card_vault_crypto.yaml"
        yml_findings, yml_meta = scan_yaml_config_file(vault_path)
        self.assertEqual(yml_meta["service_id"], "card_vault")
        self.assertIn("X25519MLKEM768", yml_meta["pqc_identifiers_present"])
        self.assertEqual(len(yml_findings), 2)
        for f in yml_findings:
            self.assertIn("Mixed-posture warning", f.rationale)
            if f.legacy_algorithm == "RSA-2048":
                self.assertEqual(f.operation_purpose, "key_establishment")
                self.assertIn("ML-KEM-768", f.target_pqc_algorithm)
                self.assertNotIn("ML-DSA", f.target_pqc_algorithm)

    def test_banking_pqc_observations_loader_preserves_error_and_longitudinal_hosts(self) -> None:
        paths = resolve_dataset_paths()
        self.assertTrue(paths.pqc_observations_csv_path.is_file())

        records, audit = load_banking_pqc_observations()
        self.assertEqual(audit["row_count"], 320)
        self.assertEqual(audit["unique_observation_keys"], 320)
        self.assertEqual(audit["duplicate_observation_keys"], 0)
        self.assertEqual(audit["unique_hosts"], 64)
        self.assertEqual(audit["hosts_measured_across_multiple_dates"], 64)

        summary = summarize_banking_pqc_observations()
        self.assertEqual(summary["overall_status_counts"]["PQ-SAFE"], 175)
        self.assertEqual(summary["overall_status_counts"]["CLASSICAL"], 80)
        self.assertEqual(summary["overall_status_counts"]["ERROR"], 65)
        self.assertEqual(summary["unclassified_error_count"], 65)

        # Verify ERROR rows are strictly unclassified, never relabelled as CLASSICAL
        for r in records:
            if r["status"] == "ERROR":
                self.assertEqual(r["posture_classification"], "unclassified_probe_error")

    def test_duplicate_observation_key_rejected_while_longitudinal_host_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_csv = Path(tmpdir) / "test_obs.csv"
            # Two valid rows for same host h101 on different dates/timestamps
            valid_content = (
                "scan_file,scan_date,host,sector,region,status,negotiated_group,ms,error,ts\n"
                "scan1.csv,2026-04-23,h101,banking,us,CLASSICAL,X25519,120,,2026-04-23T00:00:00+00:00\n"
                "scan2.csv,2026-10-02,h101,banking,us,PQ-SAFE,X25519MLKEM768,95,,2026-10-02T00:00:00+00:00\n"
            )
            tmp_csv.write_text(valid_content, encoding="utf-8")
            recs, aud = load_banking_pqc_observations(tmp_csv, strict_unique=True)
            self.assertEqual(len(recs), 2)
            self.assertEqual(aud["unique_hosts"], 1)
            self.assertEqual(aud["duplicate_observation_keys"], 0)

            # Duplicate (scan_file, host, ts) must raise ValueError
            dup_content = valid_content + (
                "scan1.csv,2026-04-23,h101,banking,us,CLASSICAL,X25519,120,,2026-04-23T00:00:00+00:00\n"
            )
            tmp_csv.write_text(dup_content, encoding="utf-8")
            with self.assertRaises(ValueError):
                load_banking_pqc_observations(tmp_csv, strict_unique=True)

    def test_cesnet_tls22_h5_incremental_streaming(self) -> None:
        paths = resolve_dataset_paths()
        self.assertTrue(paths.cesnet_h5_path.is_file())

        chunks = list(stream_cesnet_tls22_chunks(chunk_size=4000, max_rows=8000))
        self.assertEqual(len(chunks), 2)
        self.assertEqual(sum(c["rows_in_chunk"] for c in chunks), 8000)
        self.assertTrue(all(isinstance(a, str) and len(a) > 0 for a in chunks[0]["apps"][:10]))

        summary = summarize_cesnet_tls22_streaming(chunk_size=10000, max_stream_rows=20000)
        self.assertEqual(summary["status"], "verified")
        self.assertEqual(summary["file_size_bytes"], EXPECTED_CESNET_BYTES)
        self.assertEqual(summary["total_table_rows"], EXPECTED_CESNET_ROWS)
        self.assertEqual(summary["recorded_sha256"], EXPECTED_CESNET_SHA256)
        self.assertEqual(summary["incremental_streaming_benchmark"]["streamed_rows"], 20000)
        self.assertEqual(summary["incremental_streaming_benchmark"]["streamed_duplicate_flow_ids"], 0)

    def test_mvp_vertical_slice_human_approval_staging_and_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_ws = Path(tmpdir) / "ws"
            tmp_db = tmp_ws / "test_mvp.db"

            # 1. Unapproved run: held for human approval, no staged files written
            res_held = run_mvp_vertical_slice(
                target_path=DEFAULT_CONFIGS_DIR,
                approve_all=False,
                workspace_dir=tmp_ws,
                db_path=tmp_db,
            )
            self.assertEqual(res_held["approval_status"], "HELD_FOR_HUMAN_APPROVAL")
            self.assertEqual(res_held["scanned_file_findings_count"], 10)
            self.assertIsNone(res_held["post_patch_staged_findings_count"])
            self.assertTrue(all(not p["applied_to_staging"] for p in res_held["patch_proposals"]))

            # 2. Approved nominal run: patches applied ONLY to staged copy; post-patch findings drop to 0
            res_ok = run_mvp_vertical_slice(
                target_path=DEFAULT_CONFIGS_DIR,
                approve_all=True,
                approver="Unit Test Architect",
                workspace_dir=tmp_ws,
                db_path=tmp_db,
            )
            self.assertEqual(res_ok["approval_status"], "APPROVED_AND_STAGED")
            self.assertTrue(res_ok["original_source_files_unmodified"])
            self.assertEqual(res_ok["post_patch_staged_findings_count"], 0)
            self.assertTrue(all(g["overall_passed"] for g in res_ok["verification_gates"]))
            self.assertEqual(len(res_ok["staged_files_rolled_back"]), 0)

            # 3. Simulated gate failure: triggers RollbackEvent and restores backup in staged workspace
            res_fail = run_mvp_vertical_slice(
                target_path=DEFAULT_CONFIGS_DIR,
                approve_all=True,
                approver="Unit Test Architect",
                simulate_failure_service="interbank_tls",
                workspace_dir=tmp_ws,
                db_path=tmp_db,
            )
            self.assertEqual(len(res_fail["staged_files_rolled_back"]), 1)
            triggered = [r for r in res_fail["rollback_events"] if r["triggered"]]
            self.assertEqual(len(triggered), 1)
            self.assertEqual(triggered[0]["service_id"], "interbank_tls")

            # Confirm the rolled-back staged file matches the original unpatched file
            rolled_staged_path = Path(res_fail["staged_files_rolled_back"][0])
            if not rolled_staged_path.is_absolute():
                rolled_staged_path = ROOT / rolled_staged_path
            rolled_findings, _ = scan_repository_path(rolled_staged_path)
            self.assertEqual(len(rolled_findings), 3)


if __name__ == "__main__":
    unittest.main()

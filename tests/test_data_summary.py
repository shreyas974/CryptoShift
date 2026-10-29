"""Tests for the read-only `data-summary` module using tiny, safe, temporary fixtures (no real data needed)."""

from __future__ import annotations

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

from cryptoshift.data_summary import (  # noqa: E402
    iter_h5py_table_chunks,
    summarize_cesnet_h5,
    summarize_pqc_observations_csv,
    write_data_summary,
)

HEADER = "scan_file,scan_date,host,sector,region,status,negotiated_group,ms,error,ts\n"
ROWS = [
    "s1.csv,2026-01-01,h1,banking,us,CLASSICAL,X25519,100,,2026-01-01T00:00:00+00:00\n",
    "s1.csv,2026-01-01,h2,banking,uk,ERROR,,90,server alert,2026-01-01T00:00:00+00:00\n",
    "s2.csv,2026-02-01,h1,banking,us,PQ-SAFE,X25519MLKEM768,80,,2026-02-01T00:00:00+00:00\n",
]


class DataSummaryTests(unittest.TestCase):
    def test_duplicate_key_counted_not_dropped_and_error_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "obs.csv"
            # Exact duplicate of the first row -> duplicate key (scan_file, host, ts)
            csv_path.write_text(HEADER + "".join(ROWS) + ROWS[0], encoding="utf-8")
            s = summarize_pqc_observations_csv(csv_path)
            self.assertEqual(s["row_count"], 4)
            self.assertEqual(s["unique_observation_keys"], 3)
            self.assertEqual(s["duplicate_observation_keys"], 1)
            self.assertEqual(s["status_counts"]["ERROR"], 1)
            self.assertEqual(s["error_rows_unclassified"], 1)
            self.assertNotIn("UNKNOWN", s["status_counts"])  # values never re-coded

    def test_repeated_host_across_dates_is_kept(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "obs.csv"
            csv_path.write_text(HEADER + "".join(ROWS), encoding="utf-8")
            s = summarize_pqc_observations_csv(csv_path)
            self.assertEqual(s["row_count"], 3)
            self.assertEqual(s["duplicate_observation_keys"], 0)
            self.assertEqual(s["unique_hosts"], 2)
            self.assertEqual(s["hosts_seen_on_multiple_dates"], 1)
            self.assertEqual(s["scan_dates"], ["2026-01-01", "2026-02-01"])

    def test_missing_csv_reports_unavailable(self) -> None:
        s = summarize_pqc_observations_csv(Path(tempfile.gettempdir()) / "does_not_exist_cs.csv")
        self.assertEqual(s["status"], "unavailable")

    def test_h5py_chunked_reading_respects_chunk_size_and_limit(self) -> None:
        import h5py
        import numpy as np

        dtype = np.dtype([("ID", "<u4"), ("BYTES", "<u8"), ("PACKETS", "<u4"), ("DURATION", "<f8"), ("OTHER", "<u1")])
        with tempfile.TemporaryDirectory() as tmp:
            h5_path = Path(tmp) / "tiny.h5"
            with h5py.File(h5_path, "w") as f:
                g = f.create_group("flows")
                a = np.zeros(10, dtype=dtype)
                a["ID"] = np.arange(10)
                a["BYTES"] = 100
                g.create_dataset("D20990101", data=a)
                b = np.zeros(4, dtype=dtype)
                b["ID"] = np.arange(10, 14)
                g.create_dataset("D20990102", data=b)

            chunks = list(iter_h5py_table_chunks(h5_path, chunk_size=3))
            self.assertEqual([c["rows"] for c in chunks], [3, 3, 3, 1, 3, 1])
            self.assertTrue(all(len(c["data"]) <= 3 for c in chunks))
            self.assertNotIn("OTHER", chunks[0]["data"].dtype.names)  # only selected fields are read

            limited = list(iter_h5py_table_chunks(h5_path, chunk_size=4, max_rows=6))
            self.assertEqual(sum(c["rows"] for c in limited), 6)

            s = summarize_cesnet_h5(h5_path, None, chunk_size=3, max_stream_rows=12)
            self.assertEqual(s["total_rows"], 14)
            self.assertEqual(s["chunked_scan"]["rows_read"], 12)
            self.assertEqual(s["chunked_scan"]["duplicate_ids_in_window"], 0)
            self.assertFalse(s["sha256_independently_reverified"])
            self.assertEqual(s["date_range"], ["20990101", "20990102"])

            out = write_data_summary(
                {"generated_at_utc": "t", "banking_pqc_observations": {"status": "unavailable"}, "cesnet_tls22_s": s},
                Path(tmp) / "out",
            )
            self.assertTrue(out["json"].is_file() and out["markdown"].is_file())

    def test_chunk_size_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            list(iter_h5py_table_chunks(Path("unused.h5"), chunk_size=0))


if __name__ == "__main__":
    unittest.main()

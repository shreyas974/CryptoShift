"""Read-only dataset summary for the `data-summary` CLI command (Stage 1).

- Banking PQC observations CSV: counts, scan dates, status distribution, duplicate-key audit.
  Duplicate key = (scan_file, host, ts). Duplicates are counted and reported, not dropped or raised.
  A host repeating on different dates is a valid longitudinal observation and is kept.
  Status values are never changed; `ERROR` stays unclassified.
- CESNET-TLS22 S HDF5: table/row metadata plus a bounded chunked scan with `h5py`
  (only the requested slice of selected fields is ever in memory).
  The 3 GB file is NOT re-hashed; size is compared with `manifest.json` and the recorded SHA-256 is quoted.

Inputs are opened read-only. Outputs go only to `scratch/derived/data-summary/` (git-ignored) by default.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from cryptoshift.datasets import (
    EXPECTED_CESNET_BYTES,
    EXPECTED_CESNET_ROWS,
    EXPECTED_CESNET_SHA256,
    _sanitize_display_path,
    load_banking_pqc_observations,
    resolve_dataset_paths,
)
from cryptoshift.optimization.auth_check import PROJECT_ROOT

DEFAULT_SUMMARY_OUT_DIR = PROJECT_ROOT / "scratch" / "derived" / "data-summary"
CESNET_SCAN_FIELDS = ("ID", "BYTES", "PACKETS", "DURATION")


def summarize_pqc_observations_csv(csv_path: Path) -> Dict[str, Any]:
    """Summarize the banking public-endpoint observation CSV without altering any value."""
    if not csv_path.is_file():
        return {"status": "unavailable", "path": _sanitize_display_path(csv_path)}

    records, audit = load_banking_pqc_observations(csv_path, strict_unique=False)
    status_counts: Counter[str] = Counter(r["status"] for r in records)
    by_date: Dict[str, Counter[str]] = {}
    for r in records:
        by_date.setdefault(r["scan_date"], Counter())[r["status"]] += 1

    return {
        "status": "read",
        "dataset": "banking_pqc_observations.csv (PQ Readiness Index, banking rows)",
        "classification": "REAL public TLS endpoint observations on the listed scan dates",
        "path": _sanitize_display_path(csv_path),
        "row_count": audit["row_count"],
        "unique_observation_keys": audit["unique_observation_keys"],
        "duplicate_observation_keys": audit["duplicate_observation_keys"],
        "duplicate_key_definition": audit["duplicate_key_definition"],
        "unique_hosts": audit["unique_hosts"],
        "hosts_seen_on_multiple_dates": audit["hosts_measured_across_multiple_dates"],
        "scan_dates": sorted(by_date),
        "status_counts": dict(sorted(status_counts.items())),
        "status_counts_by_scan_date": {d: dict(sorted(c.items())) for d, c in sorted(by_date.items())},
        "error_rows_unclassified": status_counts.get("ERROR", 0),
        "caveats": [
            "Public-endpoint observations on the given dates only; not a bank's internal inventory or migration status.",
            "Status values are kept exactly as published; ERROR is unclassified (never CLASSICAL or negative).",
            "A host repeating across scan dates is a separate valid observation and is kept.",
        ],
    }


def _open_h5(h5_path: Path) -> Any:
    """Open an HDF5 file read-only, registering compression filters (Blosc) used by PyTables if available."""
    import h5py

    try:
        import hdf5plugin  # noqa: F401  (registers Blosc filter 32001 used by CESNET-TLS22)
    except ImportError:
        pass
    return h5py.File(h5_path, "r")


def iter_h5py_table_chunks(
    h5_path: Path,
    chunk_size: int,
    max_rows: Optional[int] = None,
    fields: tuple[str, ...] = CESNET_SCAN_FIELDS,
) -> Iterator[Dict[str, Any]]:
    """Yield bounded slices of selected fields from every dataset under `/flows` using h5py.

    Only `chunk_size` rows of the requested `fields` are materialised at a time.
    """
    import h5py

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    emitted = 0
    with _open_h5(h5_path) as h5:
        flows = h5["flows"]
        for name in sorted(flows.keys()):
            ds = flows[name]
            if not isinstance(ds, h5py.Dataset):
                continue
            present = [f for f in fields if ds.dtype.names and f in ds.dtype.names]
            nrows = int(ds.shape[0])
            for start in range(0, nrows, chunk_size):
                if max_rows is not None and emitted >= max_rows:
                    return
                stop = min(start + chunk_size, nrows)
                if max_rows is not None:
                    stop = min(stop, start + (max_rows - emitted))
                arr = ds.fields(present)[start:stop] if present else None
                n = stop - start
                emitted += n
                yield {"table": f"/flows/{name}", "start": start, "stop": stop, "rows": n, "data": arr}


def summarize_cesnet_h5(
    h5_path: Path,
    manifest_path: Optional[Path] = None,
    chunk_size: int = 25_000,
    max_stream_rows: int = 100_000,
) -> Dict[str, Any]:
    """Return table metadata and a bounded chunked-scan summary for CESNET-TLS22 S."""
    if not h5_path.is_file():
        return {"status": "unavailable", "path": _sanitize_display_path(h5_path)}

    import h5py
    import numpy as np

    size = h5_path.stat().st_size
    table_rows: Dict[str, int] = {}
    columns: List[str] = []
    with _open_h5(h5_path) as h5:
        for name in sorted(h5["flows"].keys()):
            ds = h5["flows"][name]
            if isinstance(ds, h5py.Dataset):
                table_rows[f"/flows/{name}"] = int(ds.shape[0])
                if not columns and ds.dtype.names:
                    columns = list(ds.dtype.names)

    manifest: Dict[str, Any] = {}
    if manifest_path and manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    t0 = time.perf_counter()
    rows = chunks = 0
    bytes_sum = 0
    id_parts: List[Any] = []
    for chunk in iter_h5py_table_chunks(h5_path, chunk_size, max_stream_rows):
        chunks += 1
        rows += chunk["rows"]
        data = chunk["data"]
        if data is not None:
            if "BYTES" in data.dtype.names:
                bytes_sum += int(np.sum(data["BYTES"], dtype=np.uint64))
            if "ID" in data.dtype.names:
                id_parts.append(np.asarray(data["ID"]))
    elapsed = max(time.perf_counter() - t0, 1e-9)
    window_ids = np.concatenate(id_parts) if id_parts else np.array([])
    dates = sorted(t.rsplit("/D", 1)[-1] for t in table_rows if "/D" in t)

    return {
        "status": "read",
        "dataset": "CESNET-TLS22 provider-defined S subset",
        "classification": "REAL TLS flow metadata (Oct 2021); NOT bank data; NOT PQC ground truth",
        "path": _sanitize_display_path(h5_path),
        "file_size_bytes": size,
        "file_size_matches_manifest": size == manifest.get("observed_file_size_bytes", EXPECTED_CESNET_BYTES),
        "manifest_sha256": manifest.get("sha256", EXPECTED_CESNET_SHA256),
        "sha256_independently_reverified": False,
        "table_count": len(table_rows),
        "total_rows": sum(table_rows.values()),
        "total_rows_matches_expected": sum(table_rows.values()) == EXPECTED_CESNET_ROWS,
        "table_rows": table_rows,
        "date_range": [dates[0], dates[-1]] if dates else [],
        "columns_count": len(columns),
        "chunked_scan": {
            "reader": "h5py (field-selected slices)",
            "chunk_size": chunk_size,
            "max_rows": max_stream_rows,
            "rows_read": rows,
            "chunks": chunks,
            "duplicate_ids_in_window": int(window_ids.size - np.unique(window_ids).size) if window_ids.size else 0,
            "mean_forward_bytes": round(bytes_sum / rows, 2) if rows else 0.0,
            "elapsed_seconds": round(elapsed, 4),
        },
        "caveats": [
            "Use only for streaming/filtering/scale demonstrations.",
            "APP/CATEGORY labels identify services, not cryptographic algorithms or PQC posture.",
            "Never compute detector precision/recall from this dataset.",
            "SHA-256 is quoted from manifest.json; the 3 GB file was not re-hashed in this run.",
        ],
    }


def build_data_summary(chunk_size: int = 25_000, max_stream_rows: int = 100_000) -> Dict[str, Any]:
    """Summarize all configured datasets (read-only)."""
    paths = resolve_dataset_paths()
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "configured_via": paths.configured_via,
        "banking_pqc_observations": summarize_pqc_observations_csv(paths.pqc_observations_csv_path),
        "cesnet_tls22_s": summarize_cesnet_h5(
            paths.cesnet_h5_path, paths.manifest_json_path, chunk_size, max_stream_rows
        ),
        "synthetic_fixtures_note": "Synthetic fixtures (data/fixtures/synthetic/, demo_bank_app/) are excluded from real-data summaries.",
    }


def write_data_summary(summary: Dict[str, Any], out_dir: Path = DEFAULT_SUMMARY_OUT_DIR) -> Dict[str, Path]:
    """Write JSON + Markdown summary into `out_dir` (default is git-ignored)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "data_summary.json"
    md_path = out_dir / "data_summary.md"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    pqc = summary["banking_pqc_observations"]
    ces = summary["cesnet_tls22_s"]
    lines = ["# Data summary (derived, not committed)", "", f"Generated: {summary['generated_at_utc']}", ""]
    lines += ["## Banking PQC observations (real public endpoints)", ""]
    if pqc.get("status") == "read":
        lines += [
            f"- Rows: {pqc['row_count']} | unique keys: {pqc['unique_observation_keys']} | duplicate keys: {pqc['duplicate_observation_keys']}",
            f"- Unique hosts: {pqc['unique_hosts']} (seen on multiple dates: {pqc['hosts_seen_on_multiple_dates']})",
            f"- Scan dates: {', '.join(pqc['scan_dates'])}",
            f"- Status counts: {pqc['status_counts']} (ERROR unclassified: {pqc['error_rows_unclassified']})",
        ]
    else:
        lines.append(f"- {pqc.get('status')}")
    lines += ["", "## CESNET-TLS22 S (real flow metadata; not bank data, not PQC ground truth)", ""]
    if ces.get("status") == "read":
        cs = ces["chunked_scan"]
        lines += [
            f"- File size: {ces['file_size_bytes']:,} bytes (matches manifest: {ces['file_size_matches_manifest']})",
            f"- Manifest SHA-256: {ces['manifest_sha256']} (independently re-verified: no)",
            f"- Tables: {ces['table_count']} | total rows: {ces['total_rows']:,} | dates: {' to '.join(ces['date_range'])}",
            f"- Chunked scan: {cs['rows_read']:,} rows in {cs['chunks']} chunks of {cs['chunk_size']:,} ({cs['elapsed_seconds']}s), duplicate IDs in window: {cs['duplicate_ids_in_window']}",
        ]
    else:
        lines.append(f"- {ces.get('status')}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": md_path}

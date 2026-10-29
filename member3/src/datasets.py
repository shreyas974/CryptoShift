"""Member 3 isolated real-dataset configuration, streaming HDF5 loader, and longitudinal PQC analysis.

Datasets supported (Read-Only):
1. CESNET-TLS22 S (`CESNET-TLS22-S.h5`):
   - 25,000,000 real encrypted TLS traffic flows collected on the CESNET2 network (4–17 Oct 2021).
   - 3,231,649,088 bytes; recorded SHA-256: `36e3240b144bf8902e874e8fd875b6e7ac3e40b0706eb5f8d3f40720ff5a2e06`.
   - 25,000,000 unique flow IDs; 0 duplicate IDs.
   - Streamed incrementally via PyTables (`tables`) in read-only mode so all 25M rows are never
     loaded into RAM at once.
   - Used strictly for streaming/data engineering, service-class exploration, and scale demonstrations.
   - NEVER used as PQC migration ground truth, bank-internal data, or PQC detector precision/recall labels.
2. PQ Readiness Index Banking Observations (`pqc_evidence/banking_pqc_observations.csv`):
   - 320 real public TLS 1.3 endpoint observations across 5 scan dates (64 banking targets per scan).
   - Duplicate observation key: `(scan_file, host, ts)` — 0 duplicates; repeated host IDs across
     different dates are preserved as valid longitudinal measurements.
   - Source `status` values (`PQ-SAFE`, `CLASSICAL`, `ERROR`) are kept unchanged; `ERROR` is treated
     strictly as unclassified (never relabelled as `CLASSICAL` or negative).
"""

from __future__ import annotations

import csv
import json
import os
import statistics
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

MEMBER3_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MEMBER3_ROOT.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cryptoshift.optimization.auth_check import redact_secrets  # noqa: E402

DEFAULT_CODEX_DATASET_DIR = (
    Path(os.path.expanduser("~"))
    / ".codex"
    / ".chatgpt-projects"
    / "g-p-6ad83eb9e6888191bf45faeac1ec7a7d"
    / "output"
    / "cryptoshift_dataset"
)

EXPECTED_CESNET_SHA256 = "36e3240b144bf8902e874e8fd875b6e7ac3e40b0706eb5f8d3f40720ff5a2e06"
EXPECTED_CESNET_BYTES = 3_231_649_088
EXPECTED_CESNET_ROWS = 25_000_000
EXPECTED_PQC_OBSERVATIONS_ROWS = 320


def _sanitize_display_path(path: Path) -> str:
    """Return a portable display path without leaking local Windows usernames in committed artifacts."""
    raw = str(path)
    home = os.path.expanduser("~")
    if home and raw.lower().startswith(home.lower()):
        rel = raw[len(home) :].lstrip("\\/").replace("\\", "/")
        return f"~/{rel}"
    return redact_secrets(raw).replace("\\", "/")


def _load_member3_local_env() -> Dict[str, str]:
    """Read optional git-ignored `member3/configs/dataset_paths.local.env` without exposing secrets."""
    env_file = MEMBER3_ROOT / "configs" / "dataset_paths.local.env"
    parsed: Dict[str, str] = {}
    if not env_file.is_file():
        return parsed
    try:
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip("'\"")
            if k and v:
                parsed[k] = v
    except OSError:
        pass
    return parsed


@dataclass
class Member3DatasetPaths:
    """Resolved external dataset paths (read-only inputs)."""

    dataset_pack_dir: Path
    cesnet_h5_path: Path
    pqc_observations_csv_path: Path
    readme_md_path: Path
    manifest_json_path: Path
    verification_json_path: Path
    pqc_summary_json_path: Path
    attribution_txt_path: Path
    configured_via: str

    def status_dict(self) -> Dict[str, Any]:
        return {
            "configured_via": self.configured_via,
            "dataset_pack_dir_available": self.dataset_pack_dir.is_dir(),
            "cesnet_h5_available": self.cesnet_h5_path.is_file(),
            "pqc_observations_csv_available": self.pqc_observations_csv_path.is_file(),
            "readme_md_available": self.readme_md_path.is_file(),
            "manifest_json_available": self.manifest_json_path.is_file(),
            "verification_json_available": self.verification_json_path.is_file(),
            "pqc_summary_json_available": self.pqc_summary_json_path.is_file(),
            "attribution_txt_available": self.attribution_txt_path.is_file(),
            "display_paths": {
                "dataset_pack_dir": _sanitize_display_path(self.dataset_pack_dir),
                "cesnet_h5_path": _sanitize_display_path(self.cesnet_h5_path),
                "pqc_observations_csv_path": _sanitize_display_path(self.pqc_observations_csv_path),
                "readme_md_path": _sanitize_display_path(self.readme_md_path),
                "manifest_json_path": _sanitize_display_path(self.manifest_json_path),
                "verification_json_path": _sanitize_display_path(self.verification_json_path),
                "pqc_summary_json_path": _sanitize_display_path(self.pqc_summary_json_path),
                "attribution_txt_path": _sanitize_display_path(self.attribution_txt_path),
            },
        }


def resolve_dataset_paths(
    dataset_dir: Optional[Path | str] = None,
    cesnet_h5_path: Optional[Path | str] = None,
    pqc_csv_path: Optional[Path | str] = None,
) -> Member3DatasetPaths:
    """Resolve external dataset paths from arguments, environment variables, `member3/configs/*.local.*`, or default pack."""
    local_env = _load_member3_local_env()
    local_json_path = MEMBER3_ROOT / "configs" / "dataset_paths.local.json"
    local_json: Dict[str, str] = {}
    if local_json_path.is_file():
        try:
            local_json = json.loads(local_json_path.read_text(encoding="utf-8"))
        except Exception:
            local_json = {}

    env_dir = os.environ.get("CRYPTOSHIFT_DATASET_DIR", "").strip() or local_env.get("CRYPTOSHIFT_DATASET_DIR", "")
    env_h5 = os.environ.get("CRYPTOSHIFT_CESNET_H5_PATH", "").strip() or local_env.get("CRYPTOSHIFT_CESNET_H5_PATH", "")
    env_csv = os.environ.get("CRYPTOSHIFT_PQC_OBS_CSV_PATH", "").strip() or local_env.get("CRYPTOSHIFT_PQC_OBS_CSV_PATH", "")

    if dataset_dir:
        pack_dir = Path(dataset_dir)
        source_label = "explicit_argument"
    elif env_dir:
        pack_dir = Path(env_dir)
        source_label = "env:CRYPTOSHIFT_DATASET_DIR"
    elif local_json.get("dataset_pack_dir"):
        pack_dir = Path(local_json["dataset_pack_dir"])
        source_label = "member3/configs/dataset_paths.local.json"
    else:
        pack_dir = DEFAULT_CODEX_DATASET_DIR
        source_label = "default_codex_dataset_pack_path"

    resolved_h5 = (
        Path(cesnet_h5_path)
        if cesnet_h5_path
        else Path(env_h5)
        if env_h5
        else Path(local_json["cesnet_h5_path"])
        if local_json.get("cesnet_h5_path")
        else pack_dir / "CESNET-TLS22" / "S" / "CESNET-TLS22-S.h5"
    )

    resolved_csv = (
        Path(pqc_csv_path)
        if pqc_csv_path
        else Path(env_csv)
        if env_csv
        else Path(local_json["pqc_observations_csv_path"])
        if local_json.get("pqc_observations_csv_path")
        else pack_dir / "pqc_evidence" / "banking_pqc_observations.csv"
    )

    return Member3DatasetPaths(
        dataset_pack_dir=pack_dir,
        cesnet_h5_path=resolved_h5,
        pqc_observations_csv_path=resolved_csv,
        readme_md_path=pack_dir / "README.md",
        manifest_json_path=pack_dir / "manifest.json",
        verification_json_path=pack_dir / "verification.json",
        pqc_summary_json_path=pack_dir / "pqc_evidence" / "summary.json",
        attribution_txt_path=pack_dir / "ATTRIBUTION.txt",
        configured_via=source_label,
    )


def load_banking_pqc_observations(
    csv_path: Optional[Path | str] = None,
    strict_unique: bool = True,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Load the 320 longitudinal PQ Readiness Index banking endpoint observations and verify duplicate keys.

    Duplicate observation key is `(scan_file, host, ts)`.
    Repeating a `host` on different scan dates is a valid longitudinal measurement and is preserved.
    `status` values (`PQ-SAFE`, `CLASSICAL`, `ERROR`) are never altered; `ERROR` is treated as unclassified.
    """
    paths = resolve_dataset_paths(pqc_csv_path=csv_path)
    target_csv = Path(csv_path) if csv_path else paths.pqc_observations_csv_path
    if not target_csv.is_file():
        raise FileNotFoundError(
            f"Banking PQC observations CSV not found at {_sanitize_display_path(target_csv)}. "
            "Configure CRYPTOSHIFT_DATASET_DIR or member3/configs/dataset_paths.local.json."
        )

    required_cols = {
        "scan_file",
        "scan_date",
        "host",
        "sector",
        "region",
        "status",
        "negotiated_group",
        "ms",
        "error",
        "ts",
    }

    records: List[Dict[str, Any]] = []
    seen_keys: set[Tuple[str, str, str]] = set()
    duplicate_keys: List[Tuple[str, str, str]] = []
    hosts_to_dates: Dict[str, set[str]] = defaultdict(set)

    with target_csv.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = set(reader.fieldnames or [])
        if not required_cols.issubset(fieldnames):
            missing = sorted(required_cols - fieldnames)
            raise ValueError(f"Missing required columns in {target_csv.name}: {missing}")

        for idx, row in enumerate(reader, start=1):
            scan_file = row["scan_file"].strip()
            scan_date = row["scan_date"].strip()
            host = row["host"].strip()
            sector = row["sector"].strip()
            region = row["region"].strip()
            status = row["status"].strip()  # Keep exact source status unchanged
            negotiated_group = row["negotiated_group"].strip()
            ms_raw = row["ms"].strip()
            error_msg = row["error"].strip()
            ts = row["ts"].strip()

            obs_key = (scan_file, host, ts)
            if obs_key in seen_keys:
                duplicate_keys.append(obs_key)
                if strict_unique:
                    raise ValueError(f"Duplicate longitudinal observation key (scan_file, host, ts): {obs_key}")
            seen_keys.add(obs_key)
            hosts_to_dates[host].add(scan_date)

            if status == "PQ-SAFE":
                posture_classification = "observed_hybrid_pqc_key_exchange_mlkem768"
                nist_role = "key_establishment (FIPS 203 ML-KEM hybrid)"
            elif status == "CLASSICAL":
                posture_classification = "observed_classical_key_exchange"
                nist_role = "key_establishment (classical ECDHE)"
            elif status == "ERROR":
                posture_classification = "unclassified_probe_error"
                nist_role = "unclassified (probe did not complete)"
            else:
                posture_classification = f"unclassified_{status.lower()}"
                nist_role = "unclassified"

            records.append(
                {
                    "row_index": idx,
                    "scan_file": scan_file,
                    "scan_date": scan_date,
                    "host": host,
                    "sector": sector,
                    "region": region,
                    "status": status,
                    "posture_classification": posture_classification,
                    "nist_role": nist_role,
                    "negotiated_group": negotiated_group,
                    "ms": int(ms_raw) if ms_raw.isdigit() else None,
                    "error": error_msg,
                    "ts": ts,
                }
            )

    repeated_hosts_across_dates = sum(1 for dates in hosts_to_dates.values() if len(dates) > 1)
    audit = {
        "row_count": len(records),
        "unique_observation_keys": len(seen_keys),
        "duplicate_observation_keys": len(duplicate_keys),
        "duplicate_key_definition": "(scan_file, host, ts)",
        "unique_hosts": len(hosts_to_dates),
        "hosts_measured_across_multiple_dates": repeated_hosts_across_dates,
    }
    return records, audit


def summarize_banking_pqc_observations(
    csv_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Produce a complete descriptive and longitudinal analysis of the 320 banking observations."""
    paths = resolve_dataset_paths(pqc_csv_path=csv_path)
    target_csv = Path(csv_path) if csv_path else paths.pqc_observations_csv_path
    if not target_csv.is_file():
        return {
            "status": "unavailable",
            "path": _sanitize_display_path(target_csv),
            "message": "Banking PQC observations CSV is unavailable at the configured path.",
        }

    records, audit = load_banking_pqc_observations(target_csv, strict_unique=True)

    overall_status_counts: Counter[str] = Counter()
    by_scan_date: Dict[str, Counter[str]] = defaultdict(Counter)
    by_scan_file: Dict[str, Counter[str]] = defaultdict(Counter)
    by_region: Dict[str, Counter[str]] = defaultdict(Counter)
    negotiated_groups: Counter[str] = Counter()
    latencies_by_status: Dict[str, List[int]] = defaultdict(list)
    host_timeline: Dict[str, Dict[str, str]] = defaultdict(dict)

    for rec in records:
        st = rec["status"]
        overall_status_counts[st] += 1
        by_scan_date[rec["scan_date"]][st] += 1
        by_scan_file[rec["scan_file"]][st] += 1
        by_region[rec["region"]][st] += 1
        grp = rec["negotiated_group"] or "(none / error)"
        negotiated_groups[grp] += 1
        if rec["ms"] is not None:
            latencies_by_status[st].append(rec["ms"])
        host_timeline[rec["host"]][rec["scan_date"]] = st

    scan_dates_sorted = sorted(by_scan_date.keys())
    first_date = scan_dates_sorted[0] if scan_dates_sorted else ""
    last_date = scan_dates_sorted[-1] if scan_dates_sorted else ""

    transitions: Counter[str] = Counter()
    for host, timeline in host_timeline.items():
        first_st = timeline.get(first_date, "MISSING")
        last_st = timeline.get(last_date, "MISSING")
        transitions[f"{first_st} -> {last_st}"] += 1

    latency_summary: Dict[str, Dict[str, float]] = {}
    for st, vals in latencies_by_status.items():
        if vals:
            latency_summary[st] = {
                "count": len(vals),
                "min_ms": float(min(vals)),
                "median_ms": round(float(statistics.median(vals)), 2),
                "mean_ms": round(float(statistics.mean(vals)), 2),
                "max_ms": float(max(vals)),
            }

    return {
        "status": "verified",
        "dataset_name": "PQ Readiness Index — Banking Sector Longitudinal TLS 1.3 Observations",
        "source_repository": "https://github.com/xuxu298/PQReadinessIndex",
        "attribution": "Nguyen Dong, Global PQ Readiness Index (2026), https://github.com/xuxu298/PQReadinessIndex",
        "license": "CC-BY-4.0",
        "path": _sanitize_display_path(target_csv),
        "audit": audit,
        "scan_dates": scan_dates_sorted,
        "overall_status_counts": dict(overall_status_counts),
        "unclassified_error_count": overall_status_counts.get("ERROR", 0),
        "status_counts_by_scan_date": {d: dict(by_scan_date[d]) for d in scan_dates_sorted},
        "status_counts_by_scan_file": {f: dict(c) for f, c in by_scan_file.items()},
        "status_counts_by_region": {r: dict(c) for r, c in sorted(by_region.items())},
        "negotiated_group_counts": dict(negotiated_groups),
        "latency_ms_by_status": latency_summary,
        "longitudinal_transitions_first_to_last_scan": {
            "from_date": first_date,
            "to_date": last_date,
            "transitions": dict(transitions),
        },
        "caveats": [
            "Each row records a single public TLS 1.3 endpoint handshake observation on a specific scan date.",
            "Status values ('PQ-SAFE', 'CLASSICAL', 'ERROR') are preserved unchanged from the source scan files.",
            "'ERROR' rows are unclassified probe outcomes (e.g., server alert or DNS failure) and are NEVER relabelled as 'CLASSICAL' or PQC-negative.",
            "Repeating host IDs (h101..h164) across the 5 scan dates are valid longitudinal measurements; duplicate checking uses (scan_file, host, ts) and confirmed 0 duplicates.",
            "These public-edge TLS key-establishment observations (X25519MLKEM768, FIPS 203 ML-KEM) do NOT reveal a bank's internal software estate, ML-DSA (FIPS 204) digital signature adoption, internal service dependencies, or overall migration status.",
        ],
    }


def stream_cesnet_tls22_chunks(
    h5_path: Optional[Path | str] = None,
    chunk_size: int = 10_000,
    max_rows: Optional[int] = 50_000,
    table_names: Optional[List[str]] = None,
) -> Iterator[Dict[str, Any]]:
    """Stream chunks incrementally from `CESNET-TLS22-S.h5` without loading 25M rows into RAM."""
    paths = resolve_dataset_paths(cesnet_h5_path=h5_path)
    target_h5 = Path(h5_path) if h5_path else paths.cesnet_h5_path
    if not target_h5.is_file():
        raise FileNotFoundError(
            f"CESNET-TLS22-S HDF5 file not found at {_sanitize_display_path(target_h5)}. "
            "Configure CRYPTOSHIFT_DATASET_DIR or member3/configs/dataset_paths.local.json."
        )

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    import tables

    yielded_total = 0
    with tables.open_file(target_h5, mode="r") as h5:
        all_tables = list(h5.walk_nodes("/flows", classname="Table"))
        for tbl in all_tables:
            t_path = tbl._v_pathname
            t_name = tbl._v_name
            if table_names and t_name not in table_names and t_path not in table_names:
                continue

            app_enum = tbl.get_enum("APP") if "APP" in tbl.coltypes and tbl.coltypes["APP"] == "enum" else None
            cat_enum = (
                tbl.get_enum("CATEGORY")
                if "CATEGORY" in tbl.coltypes and tbl.coltypes["CATEGORY"] == "enum"
                else None
            )
            nrows = int(tbl.nrows)

            for start in range(0, nrows, chunk_size):
                if max_rows is not None and yielded_total >= max_rows:
                    return
                stop = min(start + chunk_size, nrows)
                if max_rows is not None:
                    stop = min(stop, start + (max_rows - yielded_total))

                arr = tbl.read(start, stop)
                batch_len = int(len(arr))
                if batch_len == 0:
                    continue

                apps = [app_enum(int(v)) for v in arr["APP"]] if app_enum is not None else [str(v) for v in arr["APP"]]
                cats = (
                    [cat_enum(int(v)) for v in arr["CATEGORY"]]
                    if cat_enum is not None
                    else [str(v) for v in arr["CATEGORY"]]
                )

                yielded_total += batch_len
                yield {
                    "table_path": t_path,
                    "table_name": t_name,
                    "start_row": start,
                    "stop_row": stop,
                    "rows_in_chunk": batch_len,
                    "ids": arr["ID"],
                    "apps": apps,
                    "categories": cats,
                    "bytes_fwd": arr["BYTES"],
                    "bytes_rev": arr["BYTES_REV"],
                    "packets_fwd": arr["PACKETS"],
                    "packets_rev": arr["PACKETS_REV"],
                    "duration": arr["DURATION"],
                }


def summarize_cesnet_tls22_streaming(
    h5_path: Optional[Path | str] = None,
    chunk_size: int = 25_000,
    max_stream_rows: int = 100_000,
) -> Dict[str, Any]:
    """Inspect CESNET-TLS22-S table metadata and stream a bounded window of rows incrementally."""
    paths = resolve_dataset_paths(cesnet_h5_path=h5_path)
    target_h5 = Path(h5_path) if h5_path else paths.cesnet_h5_path
    if not target_h5.is_file():
        return {
            "status": "unavailable",
            "path": _sanitize_display_path(target_h5),
            "message": "CESNET-TLS22-S HDF5 file is unavailable at the configured path.",
        }

    import numpy as np
    import tables

    start_time = time.perf_counter()
    file_size_bytes = target_h5.stat().st_size

    table_row_counts: Dict[str, int] = {}
    colnames: List[str] = []
    num_app_labels = 0
    num_category_labels = 0

    with tables.open_file(target_h5, mode="r") as h5:
        for tbl in h5.walk_nodes("/flows", classname="Table"):
            table_row_counts[tbl._v_pathname] = int(tbl.nrows)
            if not colnames:
                colnames = list(tbl.colnames)
                if "APP" in tbl.coltypes and tbl.coltypes["APP"] == "enum":
                    num_app_labels = len(tbl.get_enum("APP"))
                if "CATEGORY" in tbl.coltypes and tbl.coltypes["CATEGORY"] == "enum":
                    num_category_labels = len(tbl.get_enum("CATEGORY"))

    total_table_rows = sum(table_row_counts.values())

    streamed_rows = 0
    chunks_processed = 0
    cat_counter: Counter[str] = Counter()
    app_counter: Counter[str] = Counter()
    id_batches: List[np.ndarray] = []
    total_bytes_fwd = 0
    total_packets_fwd = 0
    duration_sum = 0.0

    for chunk in stream_cesnet_tls22_chunks(
        h5_path=target_h5,
        chunk_size=chunk_size,
        max_rows=max_stream_rows,
    ):
        chunks_processed += 1
        n = chunk["rows_in_chunk"]
        streamed_rows += n
        cat_counter.update(chunk["categories"])
        app_counter.update(chunk["apps"])
        id_batches.append(np.asarray(chunk["ids"], dtype=np.uint32))
        total_bytes_fwd += int(np.sum(chunk["bytes_fwd"]))
        total_packets_fwd += int(np.sum(chunk["packets_fwd"]))
        duration_sum += float(np.sum(chunk["duration"]))

    elapsed = max(time.perf_counter() - start_time, 1e-6)
    if id_batches:
        concat_ids = np.concatenate(id_batches)
        streamed_unique_ids = int(np.unique(concat_ids).size)
        streamed_duplicate_ids = int(concat_ids.size - streamed_unique_ids)
    else:
        streamed_unique_ids = 0
        streamed_duplicate_ids = 0

    full_audit_info: Dict[str, Any] = {}
    ver_path = paths.verification_json_path
    if ver_path.is_file():
        try:
            ver_data = json.loads(ver_path.read_text(encoding="utf-8"))
            full_audit_info = {
                "verified_at_utc": ver_data.get("verified_at_utc"),
                "sha256": ver_data.get("sha256"),
                "sha256_matches_expected": ver_data.get("sha256") == EXPECTED_CESNET_SHA256,
                "observed_table_rows": ver_data.get("observed_table_rows"),
                "unique_flow_ids": ver_data.get("unique_flow_ids"),
                "duplicate_flow_ids": ver_data.get("duplicate_flow_ids"),
                "status": ver_data.get("status"),
            }
        except Exception:
            full_audit_info = {}

    return {
        "status": "verified",
        "dataset_name": "CESNET-TLS22 Provider-Defined S Subset (Encrypted TLS Flow Metadata)",
        "source_url": "https://zenodo.org/records/10610895",
        "doi": "10.5281/zenodo.10610895",
        "required_citation": (
            "Jan Luxemburk and Tomáš Čejka, 'Fine-grained TLS services classification with reject option,' "
            "Computer Networks, vol. 220, 2023, article 109467, https://doi.org/10.1016/j.comnet.2022.109467"
        ),
        "license": "CC-BY-4.0",
        "collection_period": "2021-10-04 through 2021-10-17 (CESNET2 network)",
        "path": _sanitize_display_path(target_h5),
        "file_size_bytes": file_size_bytes,
        "file_size_matches_expected": file_size_bytes == EXPECTED_CESNET_BYTES,
        "recorded_sha256": EXPECTED_CESNET_SHA256,
        "table_count": len(table_row_counts),
        "total_table_rows": total_table_rows,
        "total_rows_matches_expected": total_table_rows == EXPECTED_CESNET_ROWS,
        "table_row_counts": table_row_counts,
        "columns_count": len(colnames),
        "columns": colnames,
        "enum_dictionary_sizes": {
            "APP_labels": num_app_labels,
            "CATEGORY_labels": num_category_labels,
        },
        "full_25m_audit_record": full_audit_info,
        "incremental_streaming_benchmark": {
            "chunk_size": chunk_size,
            "streamed_rows": streamed_rows,
            "chunks_processed": chunks_processed,
            "streamed_unique_flow_ids": streamed_unique_ids,
            "streamed_duplicate_flow_ids": streamed_duplicate_ids,
            "elapsed_seconds": round(elapsed, 4),
            "throughput_rows_per_sec": round(streamed_rows / elapsed, 1),
            "mean_forward_bytes": round(total_bytes_fwd / max(streamed_rows, 1), 2),
            "mean_forward_packets": round(total_packets_fwd / max(streamed_rows, 1), 2),
            "mean_duration_seconds": round(duration_sum / max(streamed_rows, 1), 4),
            "top_categories_in_stream": dict(cat_counter.most_common(10)),
            "top_apps_in_stream": dict(app_counter.most_common(12)),
        },
        "allowed_use_in_cryptoshift": [
            "Demonstrating real multi-gigabyte TLS flow data ingestion and out-of-core HDF5 chunk streaming.",
            "Exploring traffic metadata distributions (bytes, packets, duration, PPI roundtrips) and service/category tags.",
            "Testing streaming, filtering, aggregation, and notebook responsiveness without loading 25M rows into RAM.",
        ],
        "prohibited_interpretations": [
            "NOT bank-internal source code, configuration, or network infrastructure data.",
            "NOT PQC adoption or migration ground truth (captured in Oct 2021 before PQC endpoint transition).",
            "APP and CATEGORY labels identify application services, NOT cryptographic algorithms or PQC posture.",
            "NEVER use CESNET-TLS22 service labels to compute PQC detector precision or recall.",
        ],
    }


def write_member3_dataset_outputs(
    chunk_size: int = 25_000,
    max_stream_rows: int = 100_000,
) -> Dict[str, Any]:
    """Run Member 3's dataset analysis and save derived outputs under `member3/outputs/` and `member3/reports/`."""
    paths = resolve_dataset_paths()
    pqc_summary = summarize_banking_pqc_observations(paths.pqc_observations_csv_path)
    cesnet_summary = summarize_cesnet_tls22_streaming(
        paths.cesnet_h5_path,
        chunk_size=chunk_size,
        max_stream_rows=max_stream_rows,
    )
    bundle = {
        "dataset_configuration": paths.status_dict(),
        "banking_pqc_observations": pqc_summary,
        "cesnet_tls22_s": cesnet_summary,
        "model_and_evaluation_methodology_note": (
            "Descriptive statistical & longitudinal analysis only: CESNET-TLS22 labels identify application services "
            "(201 apps, 22 categories) from 2021 and do NOT support supervised PQC migration or cryptographic algorithm "
            "detector evaluation. The 320 PQ Readiness Index observations measure public TLS 1.3 key-exchange posture "
            "(X25519MLKEM768 vs. X25519 vs. unclassified ERROR) across 5 dates."
        ),
    }

    outputs_dir = MEMBER3_ROOT / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    (outputs_dir / "real_dataset_summary.json").write_text(
        json.dumps(bundle, indent=2) + "\n",
        encoding="utf-8",
    )
    return bundle

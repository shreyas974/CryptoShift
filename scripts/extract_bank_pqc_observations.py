from __future__ import annotations
import csv, json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "public" / "raw" / "pq-readiness-index"
SOURCE = RAW / "results_20261002_031250.csv"
TARGETS = RAW / "targets.csv"
OUTPUT_DIR = ROOT / "data" / "real"
OUTPUT = OUTPUT_DIR / "bank_tls_pqc_observations.csv"
SOURCE_COMMIT = "1d08f843fd929d270e9e0924a258510b0be6815d"
SOURCE_URL = "https://github.com/xuxu298/PQReadinessIndex"
FIELDS = ["observation_id", "target_id", "sector", "region", "observed_at_utc", "tls_version", "pqc_key_exchange_status", "negotiated_group", "handshake_latency_ms", "error", "source_dataset", "source_commit", "scope"]

def main() -> int:
    with SOURCE.open("r", encoding="utf-8-sig", newline="") as fh:
        all_rows = list(csv.DictReader(fh))
    with TARGETS.open("r", encoding="utf-8-sig", newline="") as fh:
        target_rows = list(csv.DictReader(fh))
    bank_rows = [r for r in all_rows if r.get("sector", "").strip().lower() == "banking"]
    bank_rows.sort(key=lambda r: r.get("host", ""))
    ids = [r.get("host", "").strip() for r in bank_rows]
    target_ids = {r["host"].strip() for r in target_rows if r.get("sector", "").strip().lower() == "banking"}
    if not bank_rows or len(ids) != len(set(ids)):
        raise SystemExit(f"Expected unique banking result rows; rows={len(bank_rows)}, unique_ids={len(set(ids))}")
    if set(ids) != target_ids:
        raise SystemExit(f"Banking results do not match target manifest: target_ids={len(target_ids)}, result_ids={len(set(ids))}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for r in bank_rows:
            host = r["host"].strip()
            writer.writerow({
                "observation_id": f"20261002-{host}",
                "target_id": host,
                "sector": r["sector"],
                "region": r.get("region", ""),
                "observed_at_utc": r.get("ts", ""),
                "tls_version": "TLS 1.3 (study probe scope)",
                "pqc_key_exchange_status": r.get("status", ""),
                "negotiated_group": r.get("negotiated_group", ""),
                "handshake_latency_ms": r.get("ms", ""),
                "error": r.get("error", ""),
                "source_dataset": "Global PQ Readiness Index, 2026-10-02 run",
                "source_commit": SOURCE_COMMIT,
                "scope": "one observed public TLS endpoint handshake; not an internal bank application inventory"
            })
    status_counts = Counter(r.get("status", "") for r in bank_rows)
    err_count = sum(bool(r.get("error", "").strip()) for r in bank_rows)
    meta = {
        "dataset_id": "real-public-banking-tls-pqc-20261002",
        "dataset_type": "original_real_observations_filtered_from_published_probe_run",
        "synthetic": False,
        "duplicate_policy": "one row per pseudonymous target_id in the single 2026-10-02 run; duplicate target IDs rejected by the extraction script",
        "source": {"title": "Global PQ Readiness Index", "attribution": "Nguyen Dong, PQReadinessIndex", "url": SOURCE_URL, "commit": SOURCE_COMMIT, "license": "CC-BY-4.0 for data; see source LICENSE", "source_file": "results_20261002_031250.csv", "source_rows": len(all_rows)},
        "filter": {"sector": "banking", "run": "2026-10-02", "records": len(bank_rows)},
        "observed_status_counts": dict(status_counts),
        "rows_with_probe_errors": err_count,
        "file": "data/real/bank_tls_pqc_observations.csv",
        "limitations": ["The source reports anonymized positional target IDs, not bank names or hostnames.", "This is a public TLS endpoint/key-agreement measurement, not source code or a bank's internal cryptographic inventory.", "The probe tests TLS 1.3 hybrid key-establishment support and does not assess ML-DSA signatures, internal systems, or migration plans.", "Results describe a single measurement date and may have changed since the probe."]
    }
    (OUTPUT_DIR / "dataset_manifest.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"Source rows: {len(all_rows)}; banking rows: {len(bank_rows)}; unique target IDs: {len(set(ids))}")
    print(f"Status counts: {dict(status_counts)}; rows with errors: {err_count}")
    print(f"Output: {OUTPUT}")
    return 0

if __name__ == "__main__": raise SystemExit(main())




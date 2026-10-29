"""CBOM-like JSON inventory (v1.1) and Markdown report. NOT CycloneDX; see `cyclonedx.py` for the optional subset export.

v1.1 adds: service attribution (service_id_basis / confidence per finding, service catalogue), OBSERVED relationships
between services, detector versions, scan start/end time and SHA-256 of every file that a detector parsed.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptoshift.models import CryptoFinding

INVENTORY_FORMAT = "cryptoshift-cbom-like/1.1"


def build_cbom_like(findings: List[CryptoFinding], stats: Dict[str, Any], target_label: str,
                    relationships: Optional[Dict[str, Any]] = None, scan_started_utc: Optional[str] = None) -> Dict[str, Any]:
    from cryptoshift.inventory.scan import DETECTOR_VERSIONS

    vuln = [f for f in findings if f.severity != "INFO"]
    inputs = stats.get("input_sha256", {})
    aggregate = hashlib.sha256("\n".join(f"{k} {v}" for k, v in sorted(inputs.items())).encode()).hexdigest()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "format": INVENTORY_FORMAT,
        "format_note": "CBOM-like inventory inspired by CycloneDX CBOM concepts; NOT CycloneDX. Not complete: static analysis of supported file types only.",
        "generated_at_utc": now,
        "scan": {"started_utc": scan_started_utc or now, "finished_utc": now, "detector_versions": DETECTOR_VERSIONS,
                 "input_files_parsed": len(inputs), "input_sha256": inputs, "input_set_sha256": aggregate},
        "target": target_label,
        "review_policy": "Every migration target is a candidate for human review. Unknown purpose => HOLD.",
        "summary": {
            "files_seen": stats.get("files_seen", 0),
            "files_by_detector": stats.get("files_by_detector", {}),
            "skipped_sensitive_files": stats.get("skipped_sensitive", 0),
            "parse_errors": len(stats.get("parse_errors", [])),
            "findings_total": len(findings),
            "findings_quantum_or_classically_weak": len(vuln),
            "findings_pqc_or_hybrid_info": len(findings) - len(vuln),
            "by_family": dict(Counter(f.algorithm_family for f in findings).most_common()),
            "by_purpose": dict(Counter(f.operation_purpose for f in findings).most_common()),
            "by_ambiguity": dict(Counter(f.ambiguity for f in findings).most_common()),
            "by_service": dict(Counter(f.service_id for f in findings).most_common()),
            "by_service_confidence": dict(Counter(f.service_id_confidence or "n/a" for f in findings).most_common()),
            "in_test_files": sum(1 for f in findings if f.in_test_file),
            "relationships": (relationships or {}).get("summary", {"edges": 0, "unknown_references": 0}),
        },
        "services": stats.get("service_catalog", {}),
        "parse_errors": stats.get("parse_errors", []),
        "findings": [f.to_dict() for f in findings],
        "relationships": {"edges": (relationships or {}).get("edges", []),
                          "unknown_references": (relationships or {}).get("unknown_references", [])},
    }


def render_markdown(cbom: Dict[str, Any], max_rows: int = 200) -> str:
    s = cbom["summary"]
    rel = cbom.get("relationships", {"edges": [], "unknown_references": []})
    lines = [
        "# CryptoShift inventory (CBOM-like v1.1)",
        "",
        f"Target: `{cbom['target']}` | generated {cbom['generated_at_utc']} | format `{cbom['format']}` (not CycloneDX)",
        "",
        f"- Files seen: {s['files_seen']} (by detector: {s['files_by_detector']}); sensitive files skipped unopened: {s['skipped_sensitive_files']}; parse errors: {s['parse_errors']}",
        f"- Findings: {s['findings_total']} ({s['findings_quantum_or_classically_weak']} vulnerable/weak, {s['findings_pqc_or_hybrid_info']} PQC/hybrid info)",
        f"- By purpose: {s['by_purpose']}",
        f"- By service: {s.get('by_service', {})} (attribution confidence: {s.get('by_service_confidence', {})})",
        f"- Ambiguity: {s['by_ambiguity']}; in test files: {s['in_test_files']}",
        f"- Relationships: {len(rel['edges'])} OBSERVED edges, {len(rel['unknown_references'])} unresolved references",
        f"- Input set SHA-256: `{cbom.get('scan', {}).get('input_set_sha256', 'n/a')}`",
        "",
        "| # | Location | Service (basis) | Family | Purpose | Conf. | Ambiguity | Candidate (human review) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for f in cbom["findings"][:max_rows]:
        loc = f"{f['file_path']}:{f['line_number']}" if f["line_number"] else f"{f['file_path']} ({f['location']})"
        test = " (test)" if f["in_test_file"] else ""
        cand = f["target_pqc_algorithm"].replace("|", "/")
        svc = f"{f['service_id']} ({f.get('service_id_confidence') or 'n/a'})"
        lines.append(
            f"| {f['finding_id']} | `{loc}`{test} | {svc} | {f['legacy_algorithm']} | {f['operation_purpose']} | "
            f"{f['confidence']} | {f['ambiguity']} | {cand} |"
        )
    if len(cbom["findings"]) > max_rows:
        lines.append(f"\n_{len(cbom['findings']) - max_rows} more findings in the JSON file._")
    if rel["edges"] or rel["unknown_references"]:
        lines += ["", "## Relationships (OBSERVED)", "", "| Edge | From | To | Kind | Evidence | Conf. |", "|---|---|---|---|---|---|"]
        for e in rel["edges"]:
            lines.append(f"| {e['edge_id']} | {e['source']} | {e['target']} | {e['kind']} | `{e['file']}:{e['line']}` | {e['confidence']} |")
        for u in rel["unknown_references"]:
            lines.append(f"| UNKNOWN | {u['source']} | `{u['reference']}` | {u['kind']} | `{u['file']}:{u['line']}` | - |")
    lines += [
        "",
        "Caveats: static analysis only; dependency findings show presence, not usage; cipher-string findings depend",
        "on the OpenSSL build and peers; risk/priority is not computed here. Candidates are not automatic changes.",
        "Service attribution follows documented rules (inventory/services.py); 'unknown' is never guessed.",
    ]
    return "\n".join(lines) + "\n"


def write_inventory(cbom: Dict[str, Any], out_dir: Path) -> Dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    j = out_dir / "inventory.cbom-like.json"
    m = out_dir / "inventory.md"
    j.write_text(json.dumps(cbom, indent=2), encoding="utf-8")
    m.write_text(render_markdown(cbom), encoding="utf-8")
    return {"json": j, "markdown": m}

"""CBOM-like JSON inventory and short Markdown report (NOT CycloneDX; not schema-validated)."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from cryptoshift.models import CryptoFinding

INVENTORY_FORMAT = "cryptoshift-cbom-like/0.1"


def build_cbom_like(findings: List[CryptoFinding], stats: Dict[str, Any], target_label: str) -> Dict[str, Any]:
    vuln = [f for f in findings if f.severity != "INFO"]
    return {
        "format": INVENTORY_FORMAT,
        "format_note": "CBOM-like inventory inspired by CycloneDX CBOM concepts; NOT CycloneDX and not schema-validated.",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
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
            "in_test_files": sum(1 for f in findings if f.in_test_file),
        },
        "parse_errors": stats.get("parse_errors", []),
        "findings": [f.to_dict() for f in findings],
    }


def render_markdown(cbom: Dict[str, Any], max_rows: int = 200) -> str:
    s = cbom["summary"]
    lines = [
        "# CryptoShift inventory (CBOM-like)",
        "",
        f"Target: `{cbom['target']}` | generated {cbom['generated_at_utc']} | format `{cbom['format']}` (not CycloneDX)",
        "",
        f"- Files seen: {s['files_seen']} (by detector: {s['files_by_detector']}); sensitive files skipped unopened: {s['skipped_sensitive_files']}; parse errors: {s['parse_errors']}",
        f"- Findings: {s['findings_total']} ({s['findings_quantum_or_classically_weak']} vulnerable/weak, {s['findings_pqc_or_hybrid_info']} PQC/hybrid info)",
        f"- By purpose: {s['by_purpose']}",
        f"- Ambiguity: {s['by_ambiguity']}; in test files: {s['in_test_files']}",
        "",
        "| # | Location | Family | Purpose | Conf. | Ambiguity | Candidate (human review) |",
        "|---|---|---|---|---|---|---|",
    ]
    for f in cbom["findings"][:max_rows]:
        loc = f"{f['file_path']}:{f['line_number']}" if f["line_number"] else f"{f['file_path']} ({f['location']})"
        test = " (test)" if f["in_test_file"] else ""
        cand = f["target_pqc_algorithm"].replace("|", "/")
        lines.append(
            f"| {f['finding_id']} | `{loc}`{test} | {f['legacy_algorithm']} | {f['operation_purpose']} | "
            f"{f['confidence']} | {f['ambiguity']} | {cand} |"
        )
    if len(cbom["findings"]) > max_rows:
        lines.append(f"\n_{len(cbom['findings']) - max_rows} more findings in the JSON file._")
    lines += [
        "",
        "Caveats: static analysis only; dependency findings show presence, not usage; cipher-string findings depend",
        "on the OpenSSL build and peers; risk/priority is not computed here. Candidates are not automatic changes.",
    ]
    return "\n".join(lines) + "\n"


def write_inventory(cbom: Dict[str, Any], out_dir: Path) -> Dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    j = out_dir / "inventory.cbom-like.json"
    m = out_dir / "inventory.md"
    j.write_text(json.dumps(cbom, indent=2), encoding="utf-8")
    m.write_text(render_markdown(cbom), encoding="utf-8")
    return {"json": j, "markdown": m}

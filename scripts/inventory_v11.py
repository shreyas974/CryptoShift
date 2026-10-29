#!/usr/bin/env python3
"""Inventory v1.1 end to end: scan -> relationships -> CBOM-like JSON + Markdown -> optional CycloneDX 1.6 subset.

  .\\.venv\\Scripts\\python.exe scripts/inventory_v11.py --path tests/fixtures/multiservice_bank
  .\\.venv\\Scripts\\python.exe scripts/inventory_v11.py --path demo_bank_app/configs --cyclonedx

Writes to scratch/derived/inventory-v11/<target name>/ (git-ignored). The CycloneDX file is validated against the
official schema when scripts/fetch_cyclonedx_schema.py has been run; otherwise it is labelled "not validated".
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from cryptoshift.inventory import build_cbom_like, scan_inventory, write_inventory  # noqa: E402
from cryptoshift.inventory.cyclonedx import to_cyclonedx, validate  # noqa: E402
from cryptoshift.inventory.relationships import extract_relationships  # noqa: E402

SCHEMA_DIR = ROOT / "scratch" / "derived" / "cyclonedx-schema"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--known-service", action="append", default=[], help="extra service ids (e.g. from a descriptor)")
    ap.add_argument("--cyclonedx", action="store_true")
    a = ap.parse_args()
    target = Path(a.path)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    findings, stats = scan_inventory(target, extra_known_services=a.known_service)
    rels = extract_relationships(target, catalog=stats["_catalog"])
    try:
        label = target.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        label = target.name
    cbom = build_cbom_like(findings, stats, label, relationships=rels, scan_started_utc=started)
    out = Path(a.out_dir) if a.out_dir else ROOT / "scratch" / "derived" / "inventory-v11" / target.name
    paths = write_inventory(cbom, out)
    (out / "relationships.json").write_text(json.dumps(rels, indent=2), encoding="utf-8")
    s = cbom["summary"]
    print(f"Inventory v1.1: {s['findings_total']} findings | services {s['by_service']} | relationships {s['relationships']}")
    if a.cyclonedx:
        doc = to_cyclonedx(cbom)
        (out / "cbom.cyclonedx-1.6.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")
        if (SCHEMA_DIR / "bom-1.6.schema.json").is_file():
            errs = validate(doc, SCHEMA_DIR)
            print("CycloneDX: validated against CycloneDX 1.6 schema, subset" if not errs else f"CycloneDX: INVALID ({len(errs)} errors): {errs[:3]}")
        else:
            print("CycloneDX: written but NOT validated (schema not fetched); call it CBOM-like")
    print(f"Written: {out.relative_to(ROOT) if out.resolve().is_relative_to(ROOT) else out.name} ({', '.join(p.name for p in paths.values())}, relationships.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

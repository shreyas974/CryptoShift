#!/usr/bin/env python3
"""Run one CryptoShift pipeline on an uploaded dataset and write every output into that run's own folder.

  .\\.venv\\Scripts\\python.exe scripts/webapp_run.py --input <run>/input --out <run>/output --pipeline discovery|plan|full

Started only by the web app's allow-listed job runner. Nothing outside --out is written: the shared reports
(reports/member3, scratch/derived/member3) are read, never changed.

  discovery  Member 2 inventory v1.1: findings, relationships, CBOM-like JSON + Markdown, CycloneDX 1.6 subset
  plan       discovery + Member 3 plan: services, dependencies, deterministic schedule, gates (saved generic lab evidence)
  full       plan, but the loopback verification lab (OpenSSL 3.5 handshakes, compatibility, rollback) is re-run first
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT), str(ROOT / "scripts")]

from cryptoshift.inventory import build_cbom_like, scan_inventory, write_inventory
from cryptoshift.inventory.cyclonedx import to_cyclonedx
from cryptoshift.inventory.relationships import extract_relationships

STAGES = {"discovery": ["discovery"], "plan": ["discovery", "plan"], "full": ["discovery", "verification", "plan"]}


def stamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def discovery(target: Path, out: Path) -> dict:
    findings, stats = scan_inventory(target)
    rels = extract_relationships(target, catalog=stats["_catalog"])
    cbom = build_cbom_like(findings, stats, "uploaded dataset", relationships=rels, scan_started_utc=stamp())
    write_inventory(cbom, out)
    (out / "relationships.json").write_text(json.dumps(rels, indent=2), encoding="utf-8")
    (out / "cbom.cyclonedx-1.6.json").write_text(json.dumps(to_cyclonedx(cbom), indent=2), encoding="utf-8")
    s = cbom["summary"]
    return {"findings": s["findings_total"], "services": s["by_service"], "relationships": s["relationships"],
            "label": "VERIFIED scan of the uploaded files; detector recall is limited (see Claims & limits)"}


def verification() -> tuple[dict, dict]:
    import member3_phase4

    ev = member3_phase4.collect()
    return ev, {"status": ev.get("status", "ran"), "label": "loopback lab evidence; generic, not specific to this dataset"}


def plan(target: Path, out: Path, evidence: dict | None) -> dict:
    from cryptoshift import member3_pipeline as pipe

    p = pipe.run(target, evidence)
    pipe.write(p, reports_dir=out, derived_dir=out / "derived")
    states: dict[str, int] = {}
    for s in p["steps"]:
        states[s["state"]] = states.get(s["state"], 0) + 1
    return {"plan_hash": p["plan_hash"], "steps": len(p["steps"]), "states": states, "objective": p["schedule"]["objective"],
            "feasible": p["schedule"]["feasible"], "label": "schedule constraints are ASSUMPTIONS; approval stays human-only"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pipeline", choices=sorted(STAGES), required=True)
    a = ap.parse_args()
    target, out = Path(a.input), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    summary: dict = {"pipeline": a.pipeline, "started_utc": stamp(), "stages": {}}
    evidence = None
    status = "succeeded"
    for stage in STAGES[a.pipeline]:
        t0 = time.perf_counter()
        print(f"stage {stage}: running", flush=True)
        try:
            if stage == "discovery":
                res = discovery(target, out / "inventory")
            elif stage == "verification":
                evidence, res = verification()
                (out / "verification").mkdir(exist_ok=True)
                (out / "verification" / "evidence.json").write_text(json.dumps(evidence, indent=2, default=str), encoding="utf-8")
            else:
                res = plan(target, out / "plan", evidence)
            res["status"] = "ok"
        except Exception as exc:  # noqa: BLE001 - report the failing stage and stop; later stages depend on it
            res, status = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"[:300]}, "failed"
        res["seconds"] = round(time.perf_counter() - t0, 2)
        summary["stages"][stage] = res
        print(f"stage {stage}: {res['status']} ({res['seconds']} s)", flush=True)
        if status == "failed":
            break
    summary.update(status=status, finished_utc=stamp())
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if status == "succeeded" else 1


if __name__ == "__main__":
    sys.exit(main())

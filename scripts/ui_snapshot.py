#!/usr/bin/env python3
"""Freeze the real outputs the console reads into scratch/derived/ui-snapshot/<UTC stamp>/ (offline DEMO mode).

  .\\.venv\\Scripts\\python.exe scripts/ui_snapshot.py                         # from this checkout
  .\\.venv\\Scripts\\python.exe scripts/ui_snapshot.py --from ..\\CryptoShift_Member3 --from ..\\CryptoShift_Member2 --seed-live

--from adds other worktrees as sources (first existing copy wins, this checkout first). --seed-live also copies files
that are missing here into this checkout's own git-ignored paths, so LIVE mode works. Only the files listed in the
console's data SPEC are copied (JSON reports and a tracked Markdown file); never .env, keys or certificates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from cryptoshift.ui.console.data import SNAPSHOTS, SPEC  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="sources", action="append", default=[])
    ap.add_argument("--seed-live", action="store_true")
    a = ap.parse_args()
    roots = [ROOT] + [Path(s).resolve() for s in a.sources]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = SNAPSHOTS / stamp
    manifest, missing = {}, []
    for key, (rel, *_rest) in SPEC.items():
        src = next((r / rel for r in roots if (r / rel).is_file()), None)
        if src is None:
            missing.append(rel)
            continue
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if a.seed_live and not (ROOT / rel).is_file() and rel.startswith("scratch/"):
            (ROOT / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, ROOT / rel)
        manifest[rel] = {"sha256": hashlib.sha256(dst.read_bytes()).hexdigest(),
                         "from": "this checkout" if src.is_relative_to(ROOT) else src.parents[len(Path(rel).parts) - 1].name}
    (out / "snapshot_manifest.json").write_text(json.dumps({"created_utc": stamp, "files": manifest, "missing": missing}, indent=2),
                                                encoding="utf-8")
    print(f"snapshot {stamp}: {len(manifest)} files, missing {missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

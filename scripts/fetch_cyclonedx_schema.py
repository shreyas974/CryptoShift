#!/usr/bin/env python3
"""Fetch the official CycloneDX 1.6 JSON schema (+ spdx and jsf) at a pinned tag into scratch/derived/ (git-ignored)
and verify SHA-256. Source: https://github.com/CycloneDX/specification (Apache-2.0), tag 1.6.1.

  .\\.venv\\Scripts\\python.exe scripts/fetch_cyclonedx_schema.py
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "scratch" / "derived" / "cyclonedx-schema"
REPO = "https://raw.githubusercontent.com/CycloneDX/specification"
TAG, COMMIT = "1.6.1", "8a27bfd1be5be0dcb2c208a34d2f4fa0b6d75bd7"
FILES = {  # recorded 2026-10-29
    "bom-1.6.schema.json": "efc54d749e32a6e16abd19394b80b4c67d846e12c782e04505130375f94ea541",
    "spdx.schema.json": "c41917196639055e9f9670811bac23ef777732144f3ff5a2f39686f61580dbe6",
    "jsf-0.82.schema.json": "8bae002c25e723db7ee1f26afde680ae1a2b1a8f6b4b4b0fd65dc3becb090aae",
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    bad = 0
    for name, want in FILES.items():
        path = OUT / name
        if not path.is_file():
            with urllib.request.urlopen(f"{REPO}/{COMMIT}/schema/{name}", timeout=60) as r:  # noqa: S310 (fixed https URL)
                path.write_bytes(r.read())
        got = hashlib.sha256(path.read_bytes()).hexdigest()
        ok = got == want
        bad += not ok
        print(f"{'OK      ' if ok else 'MISMATCH'} {name} sha256={got}")
    print(f"CycloneDX specification tag {TAG} (commit {COMMIT[:12]}), Apache-2.0 | failures: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

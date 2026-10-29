#!/usr/bin/env python3
"""Fetch the pinned public repositories used for team code labels into data/public/raw/ (git-ignored).

Reads data/labels/public_code/sources.json, clones each repository (blob-less, sparse) and checks out the pinned
commit. Then verifies the SHA-256 of every labelled file against the recorded value. Third-party code is never
executed and never copied into tracked folders.

Usage:
  .\\.venv\\Scripts\\python.exe scripts/fetch_public_label_sources.py            # fetch + verify
  .\\.venv\\Scripts\\python.exe scripts/fetch_public_label_sources.py --verify-only
  .\\.venv\\Scripts\\python.exe scripts/fetch_public_label_sources.py --print-checksums   # for annotators
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "labels" / "public_code" / "sources.json"
RAW_DIR = ROOT / "data" / "public" / "raw"


def _git(*args: str, cwd: Path | None = None) -> str:
    proc = subprocess.run(["git", "-c", "advice.detachedHead=false", *args], cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:2])} failed: {proc.stderr.strip()[:300]}")
    return proc.stdout.strip()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch_raw(src: dict) -> Path:
    """Download only the labelled files (+ licence) at the pinned commit from raw.githubusercontent.com."""
    import urllib.request

    dest = RAW_DIR / src["id"]
    owner_repo = src["url"].removeprefix("https://github.com/").removesuffix(".git")
    for rel in [f["path"] for f in src["files"]] + [src.get("license_file", "LICENSE")]:
        out = dest / rel
        if out.is_file():
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://raw.githubusercontent.com/{owner_repo}/{src['commit']}/{rel}"
        with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 (fixed https host, pinned commit)
            out.write_bytes(r.read())
    return dest


def fetch(src: dict) -> Path:
    if src.get("fetch") == "raw":
        return fetch_raw(src)
    dest = RAW_DIR / src["id"]
    if not (dest / ".git").exists():
        _git("clone", "--filter=blob:none", "--no-checkout", "--sparse", src["url"], str(dest))
    _git("sparse-checkout", "set", "--no-cone", *[f"/{f['path']}" for f in src["files"]] + ["/LICENSE*", "/COPYING*"], cwd=dest)
    try:
        _git("cat-file", "-e", f"{src['commit']}^{{commit}}", cwd=dest)
    except RuntimeError:
        _git("fetch", "origin", src["commit"], cwd=dest)
    _git("checkout", "--detach", src["commit"], cwd=dest)
    head = _git("rev-parse", "HEAD", cwd=dest)
    if head != src["commit"]:
        raise RuntimeError(f"{src['id']}: HEAD {head} != pinned {src['commit']}")
    return dest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--print-checksums", action="store_true")
    args = ap.parse_args()

    sources = json.loads(SOURCES.read_text(encoding="utf-8"))["sources"]
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    failures = 0
    for src in sources:
        dest = RAW_DIR / src["id"] if args.verify_only else fetch(src)
        for f in src["files"]:
            p = dest / f["path"]
            if not p.is_file():
                print(f"MISSING  {src['id']}/{f['path']}")
                failures += 1
                continue
            digest = sha256_file(p)
            if args.print_checksums:
                print(f"{digest}  {src['id']}/{f['path']}")
            elif f.get("sha256") and f["sha256"] != digest:
                print(f"MISMATCH {src['id']}/{f['path']}")
                failures += 1
            else:
                print(f"OK       {src['id']}/{f['path']}" + ("" if f.get("sha256") else " (no recorded checksum)"))
    print(f"Sources: {len(sources)} | failures: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

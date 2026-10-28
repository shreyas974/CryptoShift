#!/usr/bin/env python3
"""Safe repository hygiene and staged-file secret scanner for CryptoShift.

Security rule:
- Reports ONLY pass/fail summary, file paths, and finding categories.
- NEVER prints or echoes matched secret values or `.env` contents.
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_PATHS = {
    ".env",
    ".env.local",
    "qcloud.env",
    ".venv",
    "venv",
}

SECRET_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    (
        "populated_qpiai_key_assignment",
        re.compile(r"^\s*(QPIAI_OPT_API_KEY|QPIAI_QCLOUD_API_KEY|API_KEY)\s*=\s*['\"]?[A-Za-z0-9_\-]{12,}['\"]?\s*$"),
    ),
    (
        "private_key_pem_header",
        re.compile(r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    ),
    (
        "github_pat_token",
        re.compile(r"\b(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    ),
    (
        "local_windows_user_path",
        re.compile(r"[A-Za-z]:\\Users\\lohig", re.IGNORECASE),
    ),
]


def get_tracked_or_staged_files() -> List[str]:
    proc = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def main() -> int:
    files = get_tracked_or_staged_files()
    findings: List[Tuple[str, str]] = []

    for rel in files:
        norm = rel.replace("\\", "/")
        parts = set(norm.split("/"))
        if parts & FORBIDDEN_PATHS or norm.startswith(".backup_"):
            findings.append((norm, "forbidden_file_or_directory_tracked"))
            continue

        full_path = ROOT / norm
        if not full_path.is_file() or full_path.suffix.lower() in (".pptx", ".docx", ".png", ".jpg", ".pdf"):
            continue

        try:
            text = full_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for line in text.splitlines():
            for category, pattern in SECRET_PATTERNS:
                if category == "local_windows_user_path" and norm == "scripts/verify_repo.py":
                    continue
                if pattern.search(line):
                    findings.append((norm, category))
                    break

    print("=== CryptoShift Repository Hygiene & Secret Scan ===")
    print(f"Files inspected : {len(files)}")
    if findings:
        print(f"Scan result     : FAIL ({len(findings)} issue(s) detected)")
        for path_str, cat in findings:
            print(f"  - [{cat}] in {path_str}")
        return 1

    print("Scan result     : PASS (0 secret patterns, 0 forbidden files, 0 local user paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


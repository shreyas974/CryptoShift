#!/usr/bin/env python3
"""Evaluate the limited-scope Java detector on the MAPPED subset of CryptoAPI-Bench (Java crypto-API misuse benchmark).

This checks recognition of known Java API patterns; it is not a banking dataset and does not validate Python scanning.

Source: https://github.com/CryptoAPI-Bench/CryptoAPI-Bench (MIT, Copyright (c) 2018 Sharmin Afrose), commit pinned below,
cloned into git-ignored data/public/raw/cryptoapi-bench (blob-less clone; never executed or built).
Labels: CryptoAPI-Bench_details.xlsx ("Vulnerability Exists?", "Type of Vulnerability", "Line number").

Benchmark labels describe crypto-API MISUSE categories, not quantum vulnerability. Explicit mapping (decided before
scoring, see docs/member2/cryptoapi-bench.md):
  DES / Blowfish / RC4 / RC2 used -> LEGACY_SYM      MD5 / SHA1 / MD4 / MD2 used -> WEAK_HASH
  Usage of ECB                    -> ECB_MODE        RSA keysize 1024 bits       -> RSA (PARTIAL: size is not checked)
Everything else (IDEA, HmacMD5/HmacSHA1, static keys/IVs/salts/passwords, PBE iterations, seeds, credentials, HTTP,
dummy certificate/hostname verifiers, socket hostname, PRNG) is UNMAPPED and not scored.

Unit = one benchmark case (one spreadsheet row):
  insecure case (True):  TP if the detector reports the mapped group on a listed line, else FN.
  secure case (False):   FP if the detector reports the category's group anywhere in the file, else TN.
Rows whose line-number cell Excel converted to a date are excluded and counted. Multi-class cases list several files
in one cell; their listed lines are matched against findings in any of those files (the sheet does not say which). RSA "False" rows (2048-bit keys) are
not counted as FP, because for PQC migration every RSA key is in scope; they are reported separately.

  .\\.venv\\Scripts\\python.exe scripts/evaluate_cryptoapi_bench.py
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from cryptoshift.inventory.java_source import VERSION, scan_java_source  # noqa: E402

URL = "https://github.com/CryptoAPI-Bench/CryptoAPI-Bench"
COMMIT = "e6b6b50fef6970151300c1ac2de62e188ba6de19"
RAW = ROOT / "data" / "public" / "raw" / "cryptoapi-bench"
OUT = ROOT / "scratch" / "derived" / "cryptoapi-bench"
SENTENCE = ("This checks recognition of known Java API patterns; it is not a banking dataset and does not validate "
            "Python scanning.")

TYPE_TO_GROUP = {"DES used": "LEGACY_SYM", "Blowfish used": "LEGACY_SYM", "RC4 used": "LEGACY_SYM",
                 "RC2 used": "LEGACY_SYM", "MD5 used": "WEAK_HASH", "SHA1 used": "WEAK_HASH", "MD4 used": "WEAK_HASH",
                 "MD2 used": "WEAK_HASH", "Usage of ECB": "ECB_MODE", "RSA keysize 1024 bits": "RSA"}
DIR_TO_GROUP = {"brokencrypto": "LEGACY_SYM", "brokenhash": "WEAK_HASH", "ecbcrypto": "ECB_MODE",
                "insecureasymmetriccrypto": "RSA"}
FAMILY_GROUP = {"DES": "LEGACY_SYM", "3DES": "LEGACY_SYM", "RC4": "LEGACY_SYM", "RC2": "LEGACY_SYM",
                "Blowfish": "LEGACY_SYM", "MD5": "WEAK_HASH", "SHA-1": "WEAK_HASH", "MD4": "WEAK_HASH",
                "MD2": "WEAK_HASH", "AES-ECB": "ECB_MODE", "RSA": "RSA"}


def _lines(cell) -> list[int] | None:
    if isinstance(cell, (datetime.datetime, datetime.date)):
        return None  # Excel turned "a,b" into a date: unrecoverable
    nums = [int(x) for x in re.findall(r"\d+", str(cell or ""))]
    return nums or None


def main() -> int:
    import openpyxl

    head = subprocess.run(["git", "-C", str(RAW), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if head != COMMIT:
        print(f"BLOCKED: {RAW} is not at pinned commit {COMMIT} (got {head or 'missing'})")
        return 1
    xlsx = RAW / "CryptoAPI-Bench_details.xlsx"
    java_files = {p.name: p for p in (RAW / "src").rglob("*.java")}
    manifest = hashlib.sha256("\n".join(f"{p.relative_to(RAW).as_posix()} {hashlib.sha256(p.read_bytes()).hexdigest()}"
                                        for p in sorted(java_files.values())).encode()).hexdigest()
    ws = openpyxl.load_workbook(xlsx, read_only=True, data_only=True).worksheets[0]

    cases, excluded = [], Counter()
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0 or not row[1]:
            continue
        vuln, vtype, cell = str(row[3]).strip(), str(row[4] or "").strip(), row[6]
        # A cell may list several files (multi-class cases, newline-separated) and may omit ".java".
        names = [n.strip() if n.strip().endswith(".java") else n.strip() + ".java" for n in str(row[1]).splitlines() if n.strip()]
        paths = [java_files[n] for n in names if n in java_files]
        if not paths:
            excluded["file not found"] += 1
            continue
        path = paths[0]
        category = path.parent.name
        if vuln == "True":
            group = TYPE_TO_GROUP.get(vtype)
            if group is None:
                excluded[f"unmapped: {vtype}"] += 1
                continue
        elif vuln == "False":
            group = DIR_TO_GROUP.get(category)
            if group is None:
                excluded[f"unmapped secure case in {category}"] += 1
                continue
        else:
            excluded["no verdict"] += 1
            continue
        lines = _lines(cell)
        if vuln == "True" and lines is None:
            excluded["line number destroyed by Excel date conversion"] += 1
            continue
        cases.append({"file": path.relative_to(RAW).as_posix(), "files": [p.relative_to(RAW).as_posix() for p in paths],
                      "category": category, "type": vtype or "---", "insecure": vuln == "True", "group": group,
                      "lines": lines or []})

    counts: dict[str, Counter] = defaultdict(Counter)
    details = []
    rsa_secure_flagged = 0
    for c in cases:
        hits = [h for f in c["files"] for h in scan_java_source((RAW / f).read_text(encoding="utf-8", errors="replace"))]
        found = [h for h in hits if FAMILY_GROUP.get(h["family"]) == c["group"]]
        if c["insecure"]:
            ok = any(h["line"] in c["lines"] for h in found)
            outcome = "TP" if ok else "FN"
        else:
            if c["group"] == "RSA":
                rsa_secure_flagged += bool(found)
                outcome = "RSA-secure (not scored)"
            else:
                outcome = "FP" if found else "TN"
        counts[c["group"]][outcome] += 1
        details.append({**c, "outcome": outcome, "findings": [(h["line"], h["family"]) for h in found]})

    def prf(cn: Counter) -> dict:
        tp, fp, fn = cn["TP"], cn["FP"], cn["FN"]
        return {"TP": tp, "FP": fp, "FN": fn, "TN": cn["TN"],
                "precision": round(tp / (tp + fp), 4) if tp + fp else None,
                "recall": round(tp / (tp + fn), 4) if tp + fn else None}

    total = sum(counts.values(), Counter())
    res = {"sentence": SENTENCE, "source": {"url": URL, "commit": COMMIT, "license": "MIT",
                                             "xlsx_sha256": hashlib.sha256(xlsx.read_bytes()).hexdigest(),
                                             "java_manifest_sha256": manifest, "java_files": len(java_files)},
           "detector": VERSION, "mapping": TYPE_TO_GROUP, "secure_case_mapping_by_directory": DIR_TO_GROUP,
           "cases_scored": len(cases), "excluded": dict(excluded), "overall": prf(total),
           "per_group": {g: prf(c) for g, c in sorted(counts.items())},
           "rsa_secure_cases_flagged_not_scored": rsa_secure_flagged, "details": details}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cryptoapi_bench_eval.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"=== CryptoAPI-Bench (mapped subset), detector {VERSION} ===")
    print(SENTENCE)
    print(f"Source: {URL} @ {COMMIT[:12]} (MIT) | xlsx sha256 {res['source']['xlsx_sha256'][:16]}... | {len(java_files)} java files")
    print(f"Cases scored: {len(cases)} | excluded: {dict(excluded)}")
    print(f"Overall: {res['overall']}")
    for g, m in res["per_group"].items():
        print(f"  {g:11s} {m}")
    print(f"RSA secure (2048-bit) cases where RSA was reported, not counted as FP: {rsa_secure_flagged}")
    print("Written: scratch/derived/cryptoapi-bench/cryptoapi_bench_eval.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Score the Stage 1 inventory detectors against team labels on pinned public code (by repository split).

  .\\.venv\\Scripts\\python.exe scripts/evaluate_public_labels.py --fill          # add file/line checksums + snippets
  .\\.venv\\Scripts\\python.exe scripts/evaluate_public_labels.py --split calibration
  .\\.venv\\Scripts\\python.exe scripts/evaluate_public_labels.py --split held_out

Matching unit = (file, line or statement span, family group). Ambiguous-labelled lines are excluded; findings on
any other unlabelled line of a labelled file count as false positives. Results go to scratch/derived/ (git-ignored).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from cryptoshift.inventory import scan_inventory  # noqa: E402
from cryptoshift.inventory.common import redact_snippet  # noqa: E402

LABEL_DIR = ROOT / "data" / "labels" / "public_code"
RAW = ROOT / "data" / "public" / "raw"
OUT = ROOT / "scratch" / "derived" / "public-label-eval"
PERMISSIVE = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause"}
DEFENSIBLE_MIN_POSITIVES = 100
DEFENSIBLE_MIN_REPOS = 3

FAMILY_GROUP = {
    "RSA": "RSA", "EC": "EC", "ECDSA": "EC", "ECDH": "EC", "X25519": "EC", "X448": "EC", "Ed25519": "EC",
    "Ed448": "EC", "EdDSA": "EC", "ECDSA/DSA": "EC", "DSA": "DSA", "DH": "DH", "3DES": "LEGACY_SYM",
    "DES": "LEGACY_SYM", "RC4": "LEGACY_SYM", "Blowfish": "LEGACY_SYM", "SHA-1": "WEAK_HASH", "MD5": "WEAK_HASH",
    "TLS-protocol": "TLS_PROTOCOL", "TLS-cipher-policy": "CIPHER_POLICY", "X.509-unknown-key": "CERT_UNKNOWN",
    "crypto-library": "DEPENDENCY", "JWT": "DEPENDENCY", "SSH": "DEPENDENCY", "X25519/Ed25519": "DEPENDENCY",
    "TLS-library": "DEPENDENCY", "XMLDSig": "DEPENDENCY",
}


def load_sources() -> Dict[str, Any]:
    return json.loads((LABEL_DIR / "sources.json").read_text(encoding="utf-8"))


def label_files() -> List[Path]:
    return sorted(LABEL_DIR.glob("labels_*.json"))


def fill() -> None:
    srcs = load_sources()
    by_id = {s["id"]: s for s in srcs["sources"]}
    for s in srcs["sources"]:
        for f in s["files"]:
            f["sha256"] = hashlib.sha256((RAW / s["id"] / f["path"]).read_bytes()).hexdigest()
    (LABEL_DIR / "sources.json").write_text(json.dumps(srcs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for lf in label_files():
        bundle = json.loads(lf.read_text(encoding="utf-8"))
        cache: Dict[str, List[str]] = {}
        for lab in bundle["labels"]:
            key = f"{lab['source_id']}/{lab['file']}"
            if key not in cache:
                cache[key] = (RAW / key).read_text(encoding="utf-8", errors="replace").splitlines()
            text = cache[key][lab["line"] - 1].strip() if lab["line"] else ""
            lab["line_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
            src = by_id[lab["source_id"]]
            if src["license"] in PERMISSIVE:
                lab["snippet"] = redact_snippet(text)[:120]
                lab["snippet_attribution"] = f"{src['url']} @ {src['commit'][:12]} ({src['license']})"
        lf.write_text(json.dumps(bundle, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("filled checksums/snippets for", [p.name for p in label_files()])


def _in(lab: Dict[str, Any], line: int) -> bool:
    lo, hi = lab.get("span", [lab["line"], lab["line"]])
    return lo <= line <= hi


def evaluate(split: str) -> Dict[str, Any]:
    srcs = {s["id"]: s for s in load_sources()["sources"]}
    labels = [l for lf in label_files() for l in json.loads(lf.read_text(encoding="utf-8"))["labels"]
              if split == "all" or l["split"] == split]
    by_file: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for l in labels:
        by_file[f"{l['source_id']}/{l['file']}"].append(l)

    tp = fp = fn = 0
    purpose = Counter()
    hard_neg_hit = 0
    fps: List[Dict[str, Any]] = []
    fns: List[Dict[str, Any]] = []
    per_source: Dict[str, Counter] = defaultdict(Counter)
    checksum_issues = 0
    for key, labs in sorted(by_file.items()):
        sid, rel = key.split("/", 1)
        path = RAW / key
        rec = next(f for f in srcs[sid]["files"] if f["path"] == rel)
        if rec.get("sha256") and hashlib.sha256(path.read_bytes()).hexdigest() != rec["sha256"]:
            checksum_issues += 1
        findings, _ = scan_inventory(path)
        findings = [f for f in findings if f.severity != "INFO"]
        pos = [l for l in labs if l["label"] == "positive"]
        amb = [l for l in labs if l["label"] == "ambiguous"]
        hard = [l for l in labs if l["label"] == "hard_negative"]
        matched = set()
        fp_units = set()
        for f in findings:
            g = "DEPENDENCY" if f.detector == "dependency_manifest" else FAMILY_GROUP.get(f.algorithm_family, f.algorithm_family)
            hit = next((i for i, l in enumerate(pos) if l["family_group"] == g and _in(l, f.line_number)), None)
            if hit is not None:
                if hit not in matched:
                    matched.add(hit)
                    lp = pos[hit]["purpose"]
                    purpose["agree" if f.operation_purpose == lp else "finding_unknown" if f.operation_purpose == "unknown" else "disagree"] += 1
                continue
            if any(_in(l, f.line_number) for l in amb) or (f.line_number, g) in fp_units:
                continue
            fp_units.add((f.line_number, g))  # one FP per (file, line, group) unit
            fp += 1
            per_source[sid]["FP"] += 1
            if any(_in(l, f.line_number) for l in hard):
                hard_neg_hit += 1
            fps.append({"file": key, "line": f.line_number, "group": g, "purpose": f.operation_purpose, "detector": f.detector})
        tp += len(matched)
        per_source[sid]["TP"] += len(matched)
        for i, l in enumerate(pos):
            if i not in matched:
                fn += 1
                per_source[sid]["FN"] += 1
                fns.append({"file": key, "line": l["line"], "group": l["family_group"], "note": l.get("note", "")})

    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    n_pos = sum(1 for l in labels if l["label"] == "positive")
    repos = sorted({l["source_id"] for l in labels})
    defensible = n_pos >= DEFENSIBLE_MIN_POSITIVES and len(repos) >= DEFENSIBLE_MIN_REPOS
    return {
        "split": split,
        "data_classification": "REAL public open-source code; TEAM ANNOTATIONS (single annotator, review pending); not ground truth",
        "repositories": repos,
        "files": len(by_file),
        "labels": dict(Counter(l["label"] for l in labels)),
        "counts": {"TP": tp, "FP": fp, "FN": fn},
        "precision": round(p, 4), "recall": round(r, 4), "f1": round(f1, 4),
        "purpose_agreement_on_TP": dict(purpose),
        "hard_negatives_triggered": hard_neg_hit,
        "file_checksum_mismatches": checksum_issues,
        "per_source": {k: dict(v) for k, v in per_source.items()},
        "status": "measured" if defensible else
                  f"NOT YET MEASURABLE AT DEFENSIBLE SIZE (positives={n_pos} < {DEFENSIBLE_MIN_POSITIVES} or repos={len(repos)} < {DEFENSIBLE_MIN_REPOS}; single annotator)",
        "false_positives": fps,
        "false_negatives": fns,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fill", action="store_true")
    ap.add_argument("--split", choices=["calibration", "held_out", "all"], default="held_out")
    args = ap.parse_args()
    if args.fill:
        fill()
        return 0
    res = evaluate(args.split)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"eval_{args.split}.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"=== Public-code label evaluation: split={res['split']} ===")
    print(f"Status       : {res['status']}")
    print(f"Repos/files  : {res['repositories']} / {res['files']} | labels {res['labels']}")
    print(f"Counts       : TP={res['counts']['TP']} FP={res['counts']['FP']} FN={res['counts']['FN']}")
    print(f"P / R / F1   : {res['precision']} / {res['recall']} / {res['f1']}")
    print(f"Purpose (TP) : {res['purpose_agreement_on_TP']} | hard negatives triggered: {res['hard_negatives_triggered']} | checksum mismatches: {res['file_checksum_mismatches']}")
    print(f"Per source   : {res['per_source']}")
    for x in res["false_positives"]:
        print(f"  FP {x['file']}:{x['line']} {x['group']} ({x['purpose']}, {x['detector']})")
    for x in res["false_negatives"]:
        print(f"  FN {x['file']}:{x['line']} {x['group']} - {x['note']}")
    print(f"Written: scratch/derived/public-label-eval/eval_{args.split}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

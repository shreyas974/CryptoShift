#!/usr/bin/env python3
"""Human review of the AI-assisted draft labels.

  .\\.venv\\Scripts\\python.exe scripts/review_label_sheet.py --make     # (re)write data/labels/public_code/review_sheet.csv
  .\\.venv\\Scripts\\python.exe scripts/review_label_sheet.py --score    # after a teammate filled the sheet in

How to review (one row per label): read the line in the pinned source (file + line, snippet given), then fill
  reviewer = your name, verdict = agree | positive | ambiguous | hard_negative (the label you think is right), notes.
Rows with an empty verdict are "not reviewed yet".

--score reports: rows reviewed, raw agreement and Cohen's kappa (annotator vs reviewer label), and recomputed
precision/recall per split using the reviewer's label where given (unreviewed rows keep the draft label and are
counted separately). Output: scratch/derived/public-label-eval/review_score.json. Detectors are not changed.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src"), str(ROOT)]

import evaluate_public_labels as ev  # noqa: E402

SHEET = ev.LABEL_DIR / "review_sheet.csv"
COLUMNS = ["label_id", "split", "round", "source_id", "file", "line", "span", "snippet", "label", "family_group",
           "purpose", "note", "annotator", "reviewer", "verdict", "notes"]
KINDS = ("positive", "ambiguous", "hard_negative")


def _label_id(lab: dict) -> str:
    return f"{lab['source_id']}:{lab['file']}:{lab['line']}:{lab['family_group']}:{lab['label']}"


def make() -> None:
    old = {}
    if SHEET.is_file():
        with SHEET.open(encoding="utf-8", newline="") as fh:
            old = {r["label_id"]: r for r in csv.DictReader(fh)}
    rows = []
    for lf in ev.label_files():
        for lab in json.loads(lf.read_text(encoding="utf-8"))["labels"]:
            lid = _label_id(lab)
            prev = old.get(lid, {})
            rows.append({"label_id": lid, "split": lab["split"], "round": lab.get("round", 1), "source_id": lab["source_id"],
                         "file": lab["file"], "line": lab["line"], "span": "-".join(map(str, lab.get("span", []))),
                         "snippet": lab.get("snippet", ""), "label": lab["label"], "family_group": lab["family_group"],
                         "purpose": lab["purpose"], "note": lab.get("note", ""), "annotator": lab.get("annotator", ""),
                         "reviewer": prev.get("reviewer", ""), "verdict": prev.get("verdict", ""), "notes": prev.get("notes", "")})
    with SHEET.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {SHEET.relative_to(ROOT)}: {len(rows)} rows ({sum(1 for r in rows if r['verdict'])} already reviewed)")


def cohen_kappa(a: list, b: list) -> float | None:
    if not a:
        return None
    n = len(a)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return round((po - pe) / (1 - pe), 4) if pe < 1 else None


def score() -> int:
    with SHEET.open(encoding="utf-8", newline="") as fh:
        rows = {r["label_id"]: r for r in csv.DictReader(fh)}
    bad = [r for r in rows.values() if r["verdict"] and r["verdict"] not in ("agree",) + KINDS]
    if bad:
        print(f"{len(bad)} rows have an invalid verdict (use agree|positive|ambiguous|hard_negative)")
        return 1
    reviewed = [r for r in rows.values() if r["verdict"]]
    draft = [r["label"] for r in reviewed]
    human = [r["label"] if r["verdict"] == "agree" else r["verdict"] for r in reviewed]
    agree = sum(1 for x, y in zip(draft, human) if x == y)
    with tempfile.TemporaryDirectory() as d:
        tmp_files = []
        for lf in ev.label_files():
            bundle = json.loads(lf.read_text(encoding="utf-8"))
            for lab in bundle["labels"]:
                r = rows.get(_label_id(lab))
                if r and r["verdict"] and r["verdict"] != "agree":
                    lab["label"] = r["verdict"]
            p = Path(d) / lf.name
            p.write_text(json.dumps(bundle), encoding="utf-8")
            tmp_files.append(p)
        ev.label_files = lambda: tmp_files  # type: ignore[assignment]
        splits = {s: ev.evaluate(s) for s in ("calibration", "calibration-2", "held_out")}
    out = {"rows": len(rows), "reviewed": len(reviewed), "not_reviewed": len(rows) - len(reviewed),
           "raw_agreement": round(agree / len(reviewed), 4) if reviewed else None,
           "cohen_kappa_label": cohen_kappa(draft, human),
           "reviewers": sorted({r["reviewer"] for r in reviewed if r["reviewer"]}),
           "metrics_with_review": {s: {k: v[k] for k in ("counts", "precision", "recall", "f1", "status")} for s, v in splits.items()},
           "note": "Unreviewed rows keep their AI-assisted draft label."}
    ev.OUT.mkdir(parents=True, exist_ok=True)
    (ev.OUT / "review_score.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "metrics_with_review"}))
    for s, m in out["metrics_with_review"].items():
        print(f"  {s:14s} {m['counts']} P={m['precision']} R={m['recall']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--make", action="store_true")
    ap.add_argument("--score", action="store_true")
    a = ap.parse_args()
    if a.make:
        make()
        return 0
    if a.score:
        return score()
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

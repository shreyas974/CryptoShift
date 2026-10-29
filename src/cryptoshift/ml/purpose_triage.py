"""Track B: finding-purpose triage (suggestion only; never overrides the rule engine or ML-KEM/ML-DSA roles).

Rows = labelled positives in data/labels/public_code/ that a scanner finding matches (same file, line/span and
family group, as in scripts/evaluate_public_labels.py). Target = the team label's purpose. Features come from the
finding only: detector, algorithm family, ambiguity, file type, test-file flag, library, directive.
Evaluation: leave-one-repository-out (5 folds). Baselines: majority class of the training folds, and the existing
rule-based purpose (`finding.operation_purpose`).
"""

from __future__ import annotations

import json
from collections import Counter
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, List

from cryptoshift.inventory import scan_inventory
from cryptoshift.optimization.auth_check import PROJECT_ROOT
from cryptoshift.planning.findings import family_group

LABEL_DIR = PROJECT_ROOT / "data" / "labels" / "public_code"
RAW = PROJECT_ROOT / "data" / "public" / "raw"


def _in(lab: Dict[str, Any], line: int) -> bool:
    lo, hi = lab.get("span", [lab["line"], lab["line"]])
    return lo <= line <= hi


def _directive(f: Any) -> str:
    v = f.detected_value or ""
    return v.split()[0] if f.detector == "tls_config" and v else ""


def build_rows() -> List[Dict[str, Any]]:
    labels = [l for p in sorted(LABEL_DIR.glob("labels_*.json"))
              for l in json.loads(p.read_text(encoding="utf-8"))["labels"] if l["label"] == "positive"]
    by_file: Dict[str, List[Dict[str, Any]]] = {}
    for l in labels:
        by_file.setdefault(f"{l['source_id']}/{l['file']}", []).append(l)
    rows = []
    for key, labs in sorted(by_file.items()):
        path = RAW / key
        if not path.is_file():
            raise FileNotFoundError(f"{key} missing; run scripts/fetch_public_label_sources.py")
        findings, _ = scan_inventory(path)
        used = set()
        for lab in labs:
            match = next((f for f in findings if f.severity != "INFO" and family_group(f) == lab["family_group"]
                          and _in(lab, f.line_number) and id(f) not in used), None)
            if match is None:
                continue
            used.add(id(match))
            rows.append({
                "repo": lab["source_id"], "file": key, "line": lab["line"], "target": lab["purpose"],
                "rule_purpose": match.operation_purpose,
                "features": {"detector": match.detector, "family": match.algorithm_family, "ambiguity": match.ambiguity,
                             "file_type": Path(lab["file"]).suffix or "(none)", "test_file": str(match.in_test_file),
                             "library": (match.library_or_protocol or "").split(".")[0], "directive": _directive(match)},
            })
    return rows


def _scores(y: List[str], p: List[str]) -> Dict[str, Any]:
    from sklearn.metrics import accuracy_score, f1_score

    return {"accuracy": round(float(accuracy_score(y, p)), 4),
            "macro_f1": round(float(f1_score(y, p, average="macro", zero_division=0)), 4), "n": len(y)}


def run(seed: int = 0) -> Dict[str, Any]:
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.tree import DecisionTreeClassifier

    rows = build_rows()
    repos = sorted({r["repo"] for r in rows})
    y_all, p_model, p_major, p_rule, fold_info = [], [], [], [], []
    amb_true, amb_model, amb_rule = [], [], []
    for held in repos:
        tr = [r for r in rows if r["repo"] != held]
        te = [r for r in rows if r["repo"] == held]
        vec = DictVectorizer(sparse=False)
        Xtr = vec.fit_transform([r["features"] for r in tr])
        Xte = vec.transform([r["features"] for r in te])
        clf = DecisionTreeClassifier(max_depth=4, random_state=seed).fit(Xtr, [r["target"] for r in tr])
        pred = clf.predict(Xte).tolist()
        maj = Counter(r["target"] for r in tr).most_common(1)[0][0]
        for r, pm in zip(te, pred):
            y_all.append(r["target"]); p_model.append(pm); p_major.append(maj); p_rule.append(r["rule_purpose"])
            if r["rule_purpose"] == "unknown":
                amb_true.append(r["target"]); amb_model.append(pm); amb_rule.append(r["rule_purpose"])
        fold_info.append({"held_out_repo": held, "n_train": len(tr), "n_test": len(te),
                          "model_correct": sum(a == b for a, b in zip([r["target"] for r in te], pred))})

    m, b, r = _scores(y_all, p_model), _scores(y_all, p_major), _scores(y_all, p_rule)
    beats = m["macro_f1"] > r["macro_f1"] and m["accuracy"] > r["accuracy"]
    return {
        "task": "suggest operation_purpose for scanner findings (human review only)",
        "rows": len(rows), "repos": repos, "class_balance": dict(Counter(y_all)),
        "features": sorted(rows[0]["features"]) if rows else [],
        "model": "DecisionTreeClassifier(max_depth=4) on one-hot finding features", "seed": seed,
        "cv": "leave-one-repository-out", "folds": fold_info,
        "metrics_pooled_over_folds": {"model": m, "majority_baseline": b, "rule_engine": r},
        "on_rule_unknown_findings": {"n": len(amb_true),
                                     "model_matches_label": sum(a == c for a, c in zip(amb_true, amb_model)),
                                     "label_distribution": dict(Counter(amb_true))},
        "beats_rule_engine": beats,
        "decision": ("Model may be shown as a suggestion for HOLD findings only." if beats else
                     "Model does NOT beat the rule engine; keep the rules. Suggestions are not used in the plan."),
        "policy": "Suggestion only. Never overrides rule-based purposes, HOLD status, or ML-KEM (key establishment) / "
                  "ML-DSA, SLH-DSA (signatures) role rules.",
        "library_versions": {p: metadata.version(p) for p in ("scikit-learn", "numpy")},
    }

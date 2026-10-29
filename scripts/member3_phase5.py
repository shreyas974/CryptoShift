#!/usr/bin/env python3
"""Phase 5: Track A (CESNET service-category demo) and Track B (finding-purpose triage).

Writes metrics to scratch/derived/member3/ml_*.json and models to scratch/derived/member3/models/ (git-ignored).
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from cryptoshift.datasets import resolve_dataset_paths  # noqa: E402
from cryptoshift.ml import cesnet_service, purpose_triage  # noqa: E402

OUT = ROOT / "scratch" / "derived" / "member3"

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks-per-day", type=int, default=15)
    ap.add_argument("--chunk-rows", type=int, default=1000)
    a = ap.parse_args()
    (OUT / "models").mkdir(parents=True, exist_ok=True)

    h5 = resolve_dataset_paths().cesnet_h5_path
    if h5.is_file():
        res = cesnet_service.run(h5, a.chunks_per_day, a.chunk_rows)
        model = res.pop("_model")
        with (OUT / "models" / "cesnet_category_hgb.pkl").open("wb") as fh:
            pickle.dump(model, fh)
        (OUT / "ml_cesnet.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
        print("TRACK A:", res["disclaimer"])
        print("  sample:", res["sample"], "| ppi rows:", res["ppi_rows_identified"])
        for k, v in res["metrics"].items():
            print(f"  {k}: accuracy={v['accuracy']} macro_f1={v['macro_f1']}")
        print("  train top5:", res["class_balance_train_top5"])
        worst = sorted(res["metrics"]["model"]["per_class_recall"].items(), key=lambda kv: kv[1])[:5]
        print("  lowest per-class recall:", worst, "| fit", res["fit_seconds"], "s")
    else:
        print("TRACK A: BLOCKED (CESNET HDF5 not available)")

    tb = purpose_triage.run()
    (OUT / "ml_purpose_triage.json").write_text(json.dumps(tb, indent=2), encoding="utf-8")
    print("TRACK B: rows", tb["rows"], "repos", tb["repos"], "class balance", tb["class_balance"])
    for k, v in tb["metrics_pooled_over_folds"].items():
        print(f"  {k}: {v}")
    print("  folds:", tb["folds"])
    print("  on rule-unknown findings:", tb["on_rule_unknown_findings"])
    print("  beats rule engine:", tb["beats_rule_engine"], "->", tb["decision"])

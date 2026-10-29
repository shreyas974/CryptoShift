"""Track A: CESNET-TLS22 S service-category classifier (traffic-classification and scale demo).

This is a traffic-classification and scale demo. These labels are not cryptographic or PQC labels, and this model
says nothing about quantum readiness.

- Label: the dataset's own CATEGORY enum (service category).
- Features: only columns that exist in the HDF5 tables (flow counters, durations, TCP flags, and the first 10
  packets of PPI). PPI row meaning (direction / size / inter-packet time) is identified from the data itself.
- Bounded, deterministic sample: `chunks_per_day` evenly spaced slices of `chunk_rows` rows per daily table,
  read with h5py (never the whole file).
- Split by day: train on the earlier days, test on the later days.
- Baselines: majority class, and a rule-based lookup (BYTES_REV quantile bin -> majority class on train).
"""

from __future__ import annotations

import time
from collections import Counter
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

SCALAR = ["BYTES", "BYTES_REV", "PACKETS", "PACKETS_REV", "DURATION", "PPI_LEN", "PPI_DURATION",
          "PPI_ROUNDTRIPS", "TCP_FLAGS", "TCP_FLAGS_REV"]
N_PKT = 10
DISCLAIMER = ("This is a traffic-classification and scale demo. These labels are not cryptographic or PQC labels, "
              "and this model says nothing about quantum readiness.")


def _category_names(h5_path: Path) -> Dict[int, str]:
    import tables

    with tables.open_file(str(h5_path), "r") as h:
        enum = h.get_node("/flows/D20211004").get_enum("CATEGORY")
        return {int(v): str(n) for n, v in enum}


def identify_ppi_rows(ppi: np.ndarray) -> Dict[str, int]:
    """Return {'direction','size','ipt'} -> row index, decided from value ranges in the sample."""
    rows = {}
    for i in range(ppi.shape[1]):
        vals = np.unique(ppi[:, i, :])
        if set(vals.tolist()) <= {-1.0, 0.0, 1.0}:
            rows["direction"] = i
    rest = [i for i in range(ppi.shape[1]) if i != rows.get("direction")]
    rows["size"] = max(rest, key=lambda i: float(np.nanmax(ppi[:, i, :])))
    rows["ipt"] = next(i for i in rest if i != rows["size"])
    return rows


def load_sample(h5_path: Path, chunks_per_day: int = 15, chunk_rows: int = 1000) -> Dict[str, Any]:
    import h5py
    import hdf5plugin  # noqa: F401  (Blosc filter)

    feats, labels, days = [], [], []
    ppi_rows = None
    t0 = time.perf_counter()
    with h5py.File(h5_path, "r") as f:
        for name in sorted(f["flows"].keys()):
            ds = f["flows"][name]
            if not isinstance(ds, h5py.Dataset):
                continue
            n = ds.shape[0]
            starts = np.linspace(0, max(n - chunk_rows, 0), chunks_per_day).astype(int)
            for s in starts:
                arr = ds.fields(SCALAR + ["PPI", "CATEGORY"])[s:s + chunk_rows]
                ppi = np.asarray(arr["PPI"], dtype=np.float32)
                if ppi_rows is None:
                    ppi_rows = identify_ppi_rows(ppi)
                signed = ppi[:, ppi_rows["size"], :N_PKT] * np.where(ppi[:, ppi_rows["direction"], :N_PKT] == 0, 0,
                                                                      ppi[:, ppi_rows["direction"], :N_PKT])
                ipt = ppi[:, ppi_rows["ipt"], :N_PKT]
                scal = np.column_stack([np.log1p(np.asarray(arr[c], dtype=np.float64).clip(min=0)) for c in SCALAR])
                feats.append(np.hstack([scal, signed, np.log1p(ipt.clip(min=0))]))
                labels.append(np.asarray(arr["CATEGORY"], dtype=np.int16))
                days.append(np.full(len(arr), int(name[1:]), dtype=np.int64))
    return {"X": np.vstack(feats).astype(np.float32), "y": np.concatenate(labels), "day": np.concatenate(days),
            "ppi_rows": ppi_rows, "read_seconds": round(time.perf_counter() - t0, 2),
            "feature_names": [f"log1p_{c}" for c in SCALAR] + [f"signed_size_{i}" for i in range(N_PKT)]
                             + [f"log1p_ipt_{i}" for i in range(N_PKT)]}


def _metrics(y_true: np.ndarray, y_pred: np.ndarray, names: Dict[int, str]) -> Dict[str, Any]:
    from sklearn.metrics import accuracy_score, f1_score, recall_score

    labels = sorted(set(y_true.tolist()))
    rec = recall_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
    return {"accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
            "macro_f1": round(float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)), 4),
            "per_class_recall": {names.get(l, str(l)): round(float(r), 4) for l, r in zip(labels, rec)}}


def run(h5_path: Path, chunks_per_day: int = 15, chunk_rows: int = 1000, train_days: int = 7, seed: int = 0) -> Dict[str, Any]:
    from sklearn.ensemble import HistGradientBoostingClassifier

    names = _category_names(h5_path)
    data = load_sample(h5_path, chunks_per_day, chunk_rows)
    X, y, day = data["X"], data["y"], data["day"]
    all_days = sorted(set(day.tolist()))
    tr_days = all_days[:train_days]
    tr, te = np.isin(day, tr_days), ~np.isin(day, tr_days)

    majority = Counter(y[tr].tolist()).most_common(1)[0][0]
    pred_major = np.full(te.sum(), majority)

    bins = np.quantile(X[tr, 1], np.linspace(0, 1, 21)[1:-1])  # BYTES_REV (log) quantile bins
    btr, bte = np.digitize(X[tr, 1], bins), np.digitize(X[te, 1], bins)
    lookup = {b: Counter(y[tr][btr == b].tolist()).most_common(1)[0][0] for b in set(btr.tolist())}
    pred_rule = np.array([lookup.get(b, majority) for b in bte])

    t0 = time.perf_counter()
    model = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.1, random_state=seed)
    model.fit(X[tr], y[tr])
    fit_s = time.perf_counter() - t0
    pred = model.predict(X[te])

    return {
        "disclaimer": DISCLAIMER,
        "label": "CATEGORY (dataset service category)", "n_classes_in_enum": len(names),
        "sample": {"chunks_per_day": chunks_per_day, "chunk_rows": chunk_rows, "rows_total": int(len(y)),
                   "rows_train": int(tr.sum()), "rows_test": int(te.sum()), "read_seconds": data["read_seconds"],
                   "train_days": [str(d) for d in tr_days], "test_days": [str(d) for d in all_days[train_days:]]},
        "ppi_rows_identified": data["ppi_rows"], "features": data["feature_names"],
        "class_balance_train_top5": {names.get(k, str(k)): v for k, v in Counter(y[tr].tolist()).most_common(5)},
        "class_balance_test_top5": {names.get(k, str(k)): v for k, v in Counter(y[te].tolist()).most_common(5)},
        "model": "HistGradientBoostingClassifier(max_iter=200, learning_rate=0.1)", "seed": seed,
        "fit_seconds": round(fit_s, 2),
        "metrics": {"model": _metrics(y[te], pred, names), "majority_baseline": _metrics(y[te], pred_major, names),
                    "rule_baseline_bytes_rev_bins": _metrics(y[te], pred_rule, names)},
        "library_versions": {p: metadata.version(p) for p in ("scikit-learn", "numpy", "h5py")},
        "_model": model,
    }

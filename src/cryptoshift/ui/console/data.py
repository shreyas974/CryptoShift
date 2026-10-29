"""Data adapter for the CryptoShift console: every page reads through `load()`; nothing else opens files.

Base folder: CRYPTOSHIFT_UI_DATA_DIR, else the repository root (LIVE), or a frozen snapshot folder
scratch/derived/ui-snapshot/<stamp>/ (DEMO). A missing file or schema mismatch becomes a status, never a crash.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[4]
SNAPSHOTS = ROOT / "scratch" / "derived" / "ui-snapshot"

# key -> (relative path, schema (relative to ROOT) or None, producer, status label, command that produces it)
SPEC: Dict[str, tuple] = {
    "plan": ("reports/member3/plan.json", "schemas/member3/plan.schema.json", "Member 3 pipeline",
             "VERIFIED on SYNTHETIC demo bank", "scripts/member3_pipeline.py"),
    "inventory": ("scratch/derived/inventory-v11/configs/inventory.cbom-like.json", "schemas/inventory-cbom-like-1.1.schema.json",
                  "Member 2 inventory v1.1", "VERIFIED on SYNTHETIC demo bank", "scripts/inventory_v11.py --path demo_bank_app/configs"),
    "relationships_fixture": ("scratch/derived/inventory-v11/multiservice_bank/relationships.json", "schemas/relationships.schema.json",
                              "Member 2 relationships", "VERIFIED on SYNTHETIC fixture", "scripts/inventory_v11.py --path tests/fixtures/multiservice_bank"),
    "verification": ("scratch/derived/member3/verification_evidence.json", None, "Member 3 loopback lab",
                     "VERIFIED, TEST SCENARIO (loopback, test keys)", "scripts/member3_phase4.py"),
    "scheduling": ("scratch/derived/member3/scheduling_comparison.json", None, "Member 3 scheduling",
                   "Baseline VERIFIED; Opt local solve VERIFIED; QAOA SIMULATOR", "scripts/member3_phase3.py"),
    "ml_cesnet": ("scratch/derived/member3/ml_cesnet.json", None, "Member 3 ML track A",
                  "VERIFIED demo; not crypto/PQC labels", "scripts/member3_phase5.py"),
    "ml_triage": ("scratch/derived/member3/ml_purpose_triage.json", None, "Member 3 ML track B",
                  "VERIFIED (small sample)", "scripts/member3_phase5.py"),
    "agent_eval": ("scratch/derived/member3/agent_eval.json", None, "Member 3 assistant",
                   "VERIFIED (TEMPLATE_FALLBACK)", "scripts/evaluate_agent.py"),
    "agent_eval_sarvam": ("scratch/derived/member3/agent_eval_sarvam.json", None, "Member 3 assistant (Sarvam)",
                          "VERIFIED one live run (sarvam-105b)", "scripts/evaluate_agent.py --mode sarvam (owner approval)"),
    "eval_calibration": ("scratch/derived/public-label-eval/eval_calibration.json", None, "Member 2 evaluation",
                         "calibration (development data)", "scripts/evaluate_public_labels.py --split calibration"),
    "eval_calibration2": ("scratch/derived/public-label-eval/eval_calibration-2.json", None, "Member 2 evaluation",
                          "calibration-2 (seen data)", "scripts/evaluate_public_labels.py --split calibration-2"),
    "eval_held_out": ("scratch/derived/public-label-eval/eval_held_out.json", None, "Member 2 evaluation",
                      "held-out round 2 (AI-assisted draft labels)", "scripts/evaluate_public_labels.py --split held_out"),
    "eval_cryptoapi": ("scratch/derived/cryptoapi-bench/cryptoapi_bench_eval.json", None, "Member 2 evaluation",
                       "CryptoAPI-Bench mapped subset (Java)", "scripts/evaluate_cryptoapi_bench.py"),
    "registry": ("data/registry.json", None, "Member 1 datasets", "registry", "(tracked file)"),
    "claims": ("docs/stage0/claims-register.md", None, "Stage 0 claims register", "read-only", "(tracked file)"),
}

KNOWN_STATUSES = {"VERIFIED", "PARTIAL", "MOCKED", "SIMULATED", "SIMULATOR", "SYNTHETIC", "PLANNED", "BLOCKED", "PASS",
                  "FAIL", "READY", "PROPOSED", "APPROVED", "RUN", "OBSERVED", "DECLARED", "INFERRED", "HOLD"}


def norm_status(value: Any) -> str:
    s = str(value or "").strip().upper()
    return s if s in KNOWN_STATUSES else "UNKNOWN"


@dataclass
class Loaded:
    key: str
    value: Any
    status: str  # ok | missing | schema_mismatch | error
    file: str
    producer: str
    label: str
    command: str
    mtime: str = ""
    errors: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == "ok"


def latest_snapshot() -> Optional[Path]:
    snaps = sorted(p for p in SNAPSHOTS.glob("*") if p.is_dir()) if SNAPSHOTS.is_dir() else []
    return snaps[-1] if snaps else None


def base_dir(mode: str = "LIVE") -> Path:
    if os.environ.get("CRYPTOSHIFT_UI_DATA_DIR"):
        return Path(os.environ["CRYPTOSHIFT_UI_DATA_DIR"])
    if mode == "DEMO":
        return latest_snapshot() or ROOT
    return ROOT


def _schema_errors(value: Any, schema_rel: str) -> List[str]:
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource

    schema = json.loads((ROOT / schema_rel).read_text(encoding="utf-8"))
    rel = json.loads((ROOT / "schemas" / "relationships.schema.json").read_text(encoding="utf-8"))
    reg = Registry().with_resource(rel["$id"], Resource.from_contents(rel))
    return [f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message[:160]}"
            for e in list(Draft202012Validator(schema, registry=reg).iter_errors(value))[:3]]


def load(key: str, base: Optional[Path] = None) -> Loaded:
    rel, schema, producer, label, command = SPEC[key]
    base = base or base_dir()
    path = base / rel
    common = dict(key=key, file=rel, producer=producer, label=label, command=command)
    if not path.is_file():
        return Loaded(value=None, status="missing", **common)
    mtime = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    try:
        text = path.read_text(encoding="utf-8")
        value = text if rel.endswith(".md") else json.loads(text)
    except (OSError, ValueError) as exc:
        return Loaded(value=None, status="error", mtime=mtime, errors=[type(exc).__name__], **common)
    errs = _schema_errors(value, schema) if schema else []
    return Loaded(value=value, status="schema_mismatch" if errs else "ok", mtime=mtime, errors=errs, **common)

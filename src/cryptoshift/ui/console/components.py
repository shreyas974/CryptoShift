"""Shared UI pieces: status badges (text + icon), escaped text, source footer, missing-file cards, approval-button
logic and the fixed command allow-list. Pure functions are kept separate from Streamlit calls so they can be tested."""

from __future__ import annotations

import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

from cryptoshift.ui.console.data import ROOT, Loaded, norm_status

# status -> (icon, streamlit colour). Text is always shown, so colour is never the only signal.
BADGES: Dict[str, Tuple[str, str]] = {
    "VERIFIED": ("✔", "green"), "PASS": ("✔", "green"), "READY": ("✔", "green"), "APPROVED": ("✔", "green"), "RUN": ("✔", "green"),
    "PARTIAL": ("◐", "orange"), "PROPOSED": ("◐", "orange"), "HOLD": ("◐", "orange"),
    "MOCKED": ("⚠", "gray"), "SYNTHETIC": ("🧪", "gray"), "UNKNOWN": ("?", "gray"),
    "SIMULATED": ("⚛", "violet"), "SIMULATOR": ("⚛", "violet"),
    "PLANNED": ("⏳", "blue"), "BLOCKED": ("⛔", "red"), "FAIL": ("✖", "red"),
    "OBSERVED": ("👁", "green"), "DECLARED": ("📄", "gray"), "INFERRED": ("↯", "orange"),
}
SNIPPET_MAX = 160


def badge_text(status: Any) -> str:
    s = norm_status(status)
    icon, _ = BADGES.get(s, BADGES["UNKNOWN"])
    return f"{icon} {s}"


def badge_md(status: Any) -> str:
    """Streamlit markdown colour syntax with fixed, known text only (no user input reaches markdown)."""
    s = norm_status(status)
    icon, colour = BADGES.get(s, BADGES["UNKNOWN"])
    return f":{colour}[**{icon} {s}**]"


def escaped_text(value: Any, limit: int = SNIPPET_MAX) -> str:
    """Plain, length-capped text for anything that came from scanned files. Render only with st.text/st.code/st.dataframe."""
    s = "" if value is None else str(value)
    s = "".join(ch if ch.isprintable() or ch == " " else " " for ch in s)
    return s if len(s) <= limit else s[: limit - 1] + "…"


def can_approve(step: Dict[str, Any], approver: str, typed_hash: str, plan_hash: str) -> Tuple[bool, str]:
    """Approve is possible only for a READY step whose required gates all PASS, with a typed name and plan hash."""
    if norm_status(step.get("state")) != "READY":
        return False, f"step is {norm_status(step.get('state'))}, not READY"
    failing = [g.get("gate") for g in step.get("gates", []) if g.get("required", True) and norm_status(g.get("status")) != "PASS"]
    if failing:
        return False, f"required gates not passed: {failing}"
    if not approver.strip():
        return False, "type your name as approver"
    if not typed_hash.strip() or not plan_hash.startswith(typed_hash.strip()) or len(typed_hash.strip()) < 12:
        return False, "type the first 12+ characters of the plan hash"
    return True, "ok"


PY = sys.executable
ALLOWED_COMMANDS: Dict[str, List[str]] = {
    "Inventory v1.1 on the demo bank": [PY, "scripts/inventory_v11.py", "--path", "demo_bank_app/configs", "--cyclonedx"],
    "Member 3 pipeline (plan + reports)": [PY, "scripts/member3_pipeline.py"],
    "Assistant evaluation (template, no cloud)": [PY, "scripts/evaluate_agent.py"],
    "Freeze a demo snapshot": [PY, "scripts/ui_snapshot.py"],
}


def run_allowed(name: str, timeout: int = 300) -> Tuple[int, str]:
    """Run one allow-listed command (argument list, no shell, timeout); output is secret-redacted and truncated."""
    from cryptoshift.optimization.auth_check import redact_secrets

    if name not in ALLOWED_COMMANDS:
        raise ValueError("command not in the allow-list")
    try:
        p = subprocess.run(ALLOWED_COMMANDS[name], cwd=ROOT, capture_output=True, text=True, timeout=timeout, shell=False)
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"
    out = redact_secrets((p.stdout + "\n" + p.stderr).replace(str(ROOT), "<repo>"))
    return p.returncode, out[-4000:]


# ------------------------------------------------------------------ Streamlit renderers
def footer(st: Any, *loaded: Loaded) -> None:
    st.divider()
    for l in loaded:
        st.caption(f"Source: {l.file} · modified {l.mtime or 'n/a'} · producer {l.producer} · label: {l.label}")


def need(st: Any, l: Loaded) -> bool:
    """Show a card for a missing / mismatched file; return True when the data can be used."""
    if l.status == "missing":
        st.warning(f"File missing: {l.file}. Produce it with: {l.command}")
        return False
    if l.status == "schema_mismatch":
        st.error(f"Schema mismatch in {l.file}: " + " | ".join(escaped_text(e, 200) for e in l.errors))
        return False
    if l.status == "error":
        st.error(f"Could not read {l.file} ({', '.join(l.errors)})")
        return False
    return True


def data_table(st: Any, rows: List[Dict[str, Any]], caption: Optional[str] = None) -> None:
    import pandas as pd

    df = pd.DataFrame([{k: escaped_text(v, 200) if isinstance(v, str) else v for k, v in r.items()} for r in rows])
    for col in df.columns:  # mixed-type columns (e.g. bool + text) are shown as text instead of failing conversion
        if df[col].dtype == object:
            df[col] = df[col].map(lambda v: "" if v is None else str(v))
    if caption:
        st.caption(caption)
    st.dataframe(df, use_container_width=True, hide_index=True)

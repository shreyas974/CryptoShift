#!/usr/bin/env python3
"""Ask the CryptoShift Assistant from the command line (in-process; no server needed).

  .\\.venv\\Scripts\\python.exe scripts/ask_agent.py "Which gates block ledger_audit?"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from cryptoshift import member3_pipeline as pipe  # noqa: E402
from cryptoshift.agent.assistant import Assistant  # noqa: E402

if __name__ == "__main__":
    bundle = pipe.DERIVED / "bundle" / "plan.json"
    if not bundle.is_file():
        sys.exit("no bundle; run scripts/member3_pipeline.py first")
    res = Assistant(json.loads(bundle.read_text(encoding="utf-8"))).answer(" ".join(sys.argv[1:]))
    print(res["answer"])
    print("citations:", ", ".join(res["citations"]) or "-", "| refused:", res["refused"])

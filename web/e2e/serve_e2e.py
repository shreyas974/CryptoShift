"""Isolated backend for Playwright: temp state dir + test-only accounts, bound to 127.0.0.1:8611.

The password comes from the E2E_PASSWORD environment variable (generated per run by playwright.config.ts); nothing
is written to the repository. Approvals in E2E runs go to a temp store, never the real Member 3 store.
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

import uvicorn  # noqa: E402

from cryptoshift import member3_pipeline as pipe  # noqa: E402
from cryptoshift.api.admin import create_user  # noqa: E402
from cryptoshift.api.config import Settings  # noqa: E402
from cryptoshift.api.main import create_app  # noqa: E402
from cryptoshift.api.security import RateLimiter  # noqa: E402

# Test server only: the suite signs in ~8 times a minute. Production keeps 5/min (proven in tests/test_webapp_api.py).
RateLimiter.LIMITS = {**RateLimiter.LIMITS, "login": (60, 60)}

state = Path(tempfile.mkdtemp(prefix="cs-e2e-"))
pipe.APPROVALS = state / "approvals.json"
st = Settings(state_dir=state, db_path=state / "app.db", secret_path=state / "session.secret",
              allowed_origins=["http://127.0.0.1:8611"], assistant_url="http://127.0.0.1:9")
for role in ("viewer", "analyst", "approver"):
    create_user(st, f"e2e-{role}", role, os.environ["E2E_PASSWORD"])
uvicorn.run(create_app(st), host="127.0.0.1", port=8611, log_level="warning")

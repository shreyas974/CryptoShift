"""Backend settings. Everything defaults to local-only paths and the 127.0.0.1 origin.

Provider keys are never read here; only Member 3's assistant service reads SARVAM_API_KEY from its own environment.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STATE = ROOT / "scratch" / "derived" / "webapp"  # git-ignored


@dataclass
class Settings:
    root: Path = ROOT
    state_dir: Path = STATE
    db_path: Path = field(default_factory=lambda: STATE / "app.db")
    secret_path: Path = field(default_factory=lambda: STATE / "session.secret")
    data_dir: Path | None = None  # override for reports (LIVE); DEMO uses the latest ui-snapshot
    assistant_url: str = os.environ.get("CRYPTOSHIFT_ASSISTANT_URL", "http://127.0.0.1:8765")
    allowed_origins: list[str] = field(default_factory=lambda: ["http://127.0.0.1:8600", "http://127.0.0.1:5173"])
    session_max_age_s: int = 8 * 3600
    max_body_bytes: int = 1 * 1024 * 1024
    max_upload_bytes: int = 5 * 1024 * 1024
    max_dataset_bytes: int = 20 * 1024 * 1024  # one dataset upload (zip or files), compressed
    max_extracted_bytes: int = 60 * 1024 * 1024  # all text files after unzipping
    max_dataset_files: int = 3000
    secure_cookies: bool = False  # loopback HTTP; set True only behind HTTPS
    web_dist: Path = field(default_factory=lambda: ROOT / "web" / "dist")

    @property
    def runs_dir(self) -> Path:
        """One folder per dataset run: input/ (the accepted text files) and output/ (pipeline results)."""
        return self.state_dir / "runs"

    def session_secret(self) -> bytes:
        """Generated once with `secrets`, stored in a git-ignored file; never logged or returned."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        if not self.secret_path.is_file():
            self.secret_path.write_bytes(secrets.token_bytes(32))
        return self.secret_path.read_bytes()

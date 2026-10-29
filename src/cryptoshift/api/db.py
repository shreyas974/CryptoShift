"""SQLite storage (SQLAlchemy 2 Core) for users, audit log, jobs, runs, dataset runs, approvals mirror and settings.

The schema is created only by Alembic migrations (src/cryptoshift/api/migrations); `migrate()` upgrades to head.
The audit log is append-only: SQLite triggers abort UPDATE and DELETE on `audit_log`.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, MetaData, String, Table, Text, create_engine, event
from sqlalchemy.engine import Engine

metadata = MetaData()

users = Table("users", metadata,
              Column("id", Integer, primary_key=True), Column("username", String(64), unique=True, nullable=False),
              Column("password_hash", String(256), nullable=False), Column("role", String(16), nullable=False),
              Column("created_at", DateTime, nullable=False), Column("disabled", Boolean, nullable=False, default=False))

audit_log = Table("audit_log", metadata,
                  Column("id", Integer, primary_key=True), Column("ts", String(32), nullable=False),
                  Column("request_id", String(36), nullable=False), Column("actor", String(64), nullable=False),
                  Column("role", String(16), nullable=False), Column("action", String(64), nullable=False),
                  Column("target", String(256), nullable=False), Column("result", String(32), nullable=False),
                  Column("detail_json", Text, nullable=False), Column("prev_hash", String(64), nullable=False),
                  Column("entry_hash", String(64), nullable=False))

jobs = Table("jobs", metadata,
             Column("id", Integer, primary_key=True), Column("command_id", String(64), nullable=False),
             Column("args_json", JSON, nullable=False), Column("status", String(16), nullable=False),
             Column("progress", Integer, nullable=False, default=0), Column("started_at", String(32)),
             Column("finished_at", String(32)), Column("exit_code", Integer), Column("output_tail", Text),
             Column("created_by", String(64), nullable=False))

runs = Table("runs", metadata,
             Column("id", Integer, primary_key=True), Column("job_id", Integer, nullable=False),
             Column("report_key", String(64), nullable=False), Column("sha256_before", String(64)),
             Column("sha256_after", String(64)), Column("created_at", String(32), nullable=False))

approvals_mirror = Table("approvals_mirror", metadata,
                         Column("id", Integer, primary_key=True), Column("step_id", String(128), nullable=False),
                         Column("approver_name", String(128), nullable=False), Column("plan_hash", String(64), nullable=False),
                         Column("approved_at", String(32), nullable=False))

dataset_runs = Table("dataset_runs", metadata,
                     Column("id", Integer, primary_key=True), Column("job_id", Integer),
                     Column("pipeline", String(32), nullable=False), Column("dataset_name", String(128), nullable=False),
                     Column("dataset_sha256", String(64), nullable=False), Column("file_count", Integer, nullable=False),
                     Column("skipped_count", Integer, nullable=False), Column("total_bytes", Integer, nullable=False),
                     Column("created_by", String(64), nullable=False), Column("created_at", String(32), nullable=False))

settings_table = Table("settings", metadata,
                       Column("key", String(64), primary_key=True), Column("value_json", JSON, nullable=False),
                       Column("updated_by", String(64), nullable=False), Column("updated_at", String(32), nullable=False))


def make_engine(db_path: Path) -> Engine:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    eng = create_engine(f"sqlite:///{db_path.as_posix()}", future=True, connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def _pragmas(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.close()

    return eng


def migrate(db_path: Path) -> str:
    """Run Alembic migrations to head; returns the head revision."""
    from alembic import command
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config()
    cfg.set_main_option("script_location", str(Path(__file__).with_name("migrations")))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    command.upgrade(cfg, "head")
    return ScriptDirectory.from_config(cfg).get_current_head() or ""

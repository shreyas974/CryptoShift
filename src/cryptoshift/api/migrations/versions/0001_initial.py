"""initial schema: users, audit_log (append-only), jobs, runs, approvals_mirror, settings

Revision ID: 0001_initial
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("users",
                    sa.Column("id", sa.Integer, primary_key=True),
                    sa.Column("username", sa.String(64), nullable=False, unique=True),
                    sa.Column("password_hash", sa.String(256), nullable=False),
                    sa.Column("role", sa.String(16), nullable=False),
                    sa.Column("created_at", sa.DateTime, nullable=False),
                    sa.Column("disabled", sa.Boolean, nullable=False, server_default=sa.false()),
                    sa.CheckConstraint("role IN ('viewer','analyst','approver')", name="ck_users_role"))
    op.create_table("audit_log",
                    sa.Column("id", sa.Integer, primary_key=True),
                    sa.Column("ts", sa.String(32), nullable=False),
                    sa.Column("request_id", sa.String(36), nullable=False),
                    sa.Column("actor", sa.String(64), nullable=False),
                    sa.Column("role", sa.String(16), nullable=False),
                    sa.Column("action", sa.String(64), nullable=False),
                    sa.Column("target", sa.String(256), nullable=False),
                    sa.Column("result", sa.String(32), nullable=False),
                    sa.Column("detail_json", sa.Text, nullable=False),
                    sa.Column("prev_hash", sa.String(64), nullable=False),
                    sa.Column("entry_hash", sa.String(64), nullable=False))
    op.execute("CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_log BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;")
    op.execute("CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_log BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;")
    op.create_table("jobs",
                    sa.Column("id", sa.Integer, primary_key=True),
                    sa.Column("command_id", sa.String(64), nullable=False),
                    sa.Column("args_json", sa.JSON, nullable=False),
                    sa.Column("status", sa.String(16), nullable=False),
                    sa.Column("progress", sa.Integer, nullable=False, server_default="0"),
                    sa.Column("started_at", sa.String(32)),
                    sa.Column("finished_at", sa.String(32)),
                    sa.Column("exit_code", sa.Integer),
                    sa.Column("output_tail", sa.Text),
                    sa.Column("created_by", sa.String(64), nullable=False))
    op.create_table("runs",
                    sa.Column("id", sa.Integer, primary_key=True),
                    sa.Column("job_id", sa.Integer, nullable=False),
                    sa.Column("report_key", sa.String(64), nullable=False),
                    sa.Column("sha256_before", sa.String(64)),
                    sa.Column("sha256_after", sa.String(64)),
                    sa.Column("created_at", sa.String(32), nullable=False))
    op.create_table("approvals_mirror",
                    sa.Column("id", sa.Integer, primary_key=True),
                    sa.Column("step_id", sa.String(128), nullable=False),
                    sa.Column("approver_name", sa.String(128), nullable=False),
                    sa.Column("plan_hash", sa.String(64), nullable=False),
                    sa.Column("approved_at", sa.String(32), nullable=False))
    op.create_table("settings",
                    sa.Column("key", sa.String(64), primary_key=True),
                    sa.Column("value_json", sa.JSON, nullable=False),
                    sa.Column("updated_by", sa.String(64), nullable=False),
                    sa.Column("updated_at", sa.String(32), nullable=False))


def downgrade() -> None:
    for t in ("settings", "approvals_mirror", "runs", "jobs"):
        op.drop_table(t)
    op.execute("DROP TRIGGER IF EXISTS audit_no_update")
    op.execute("DROP TRIGGER IF EXISTS audit_no_delete")
    op.drop_table("audit_log")
    op.drop_table("users")

"""dataset pipeline runs: one row per uploaded dataset and the pipeline run on it

Revision ID: 0002_dataset_runs
Revises: 0001_initial
"""
import sqlalchemy as sa
from alembic import op

revision = "0002_dataset_runs"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("dataset_runs",
                    sa.Column("id", sa.Integer, primary_key=True),
                    sa.Column("job_id", sa.Integer),
                    sa.Column("pipeline", sa.String(32), nullable=False),
                    sa.Column("dataset_name", sa.String(128), nullable=False),
                    sa.Column("dataset_sha256", sa.String(64), nullable=False),
                    sa.Column("file_count", sa.Integer, nullable=False),
                    sa.Column("skipped_count", sa.Integer, nullable=False),
                    sa.Column("total_bytes", sa.Integer, nullable=False),
                    sa.Column("created_by", sa.String(64), nullable=False),
                    sa.Column("created_at", sa.String(32), nullable=False),
                    sa.CheckConstraint("pipeline IN ('discovery','plan','full')", name="ck_dataset_runs_pipeline"))


def downgrade() -> None:
    op.drop_table("dataset_runs")

"""Create job snapshots table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260328_05"
down_revision = "20260328_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("normalized_payload", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "recorded_at >= observed_at",
            name="job_snapshots_recorded_after_observed",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name="fk_job_snapshots_job_id_jobs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_job_snapshots"),
        sa.UniqueConstraint(
            "job_id",
            "content_hash",
            name="uq_job_snapshots_job_content_hash",
        ),
    )


def downgrade() -> None:
    op.drop_table("job_snapshots")

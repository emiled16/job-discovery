"""Create jobs table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260328_04"
down_revision = "20260328_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("source_id", sa.String(length=36), nullable=False),
        sa.Column("source_job_key", sa.String(length=255), nullable=False),
        sa.Column("source_identity", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("location_text", sa.String(length=255), nullable=True),
        sa.Column("work_mode", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("employment_type", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("apply_url", sa.String(length=1024), nullable=True),
        sa.Column("description_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'closed')",
            name="jobs_status_valid",
        ),
        sa.CheckConstraint(
            "work_mode IN ('remote', 'hybrid', 'onsite', 'unknown')",
            name="jobs_work_mode_valid",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_jobs_company_id_companies",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["company_sources.id"],
            name="fk_jobs_source_id_company_sources",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_jobs"),
        sa.UniqueConstraint("source_id", "source_job_key", name="uq_jobs_source_job_key"),
        sa.UniqueConstraint("source_identity", name="uq_jobs_source_identity"),
    )


def downgrade() -> None:
    op.drop_table("jobs")

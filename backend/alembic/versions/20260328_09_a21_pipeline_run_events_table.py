"""Create pipeline run events table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260328_09"
down_revision = "20260328_08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pipeline_run_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("pipeline_run_id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False, server_default="info"),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "level IN ('info', 'warning', 'error')",
            name="pipeline_run_events_level_valid",
        ),
        sa.CheckConstraint(
            "sequence_number > 0",
            name="pipeline_run_events_sequence_positive",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_pipeline_run_events_company_id_companies",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline_runs.id"],
            name="fk_pipeline_run_events_pipeline_run_id_pipeline_runs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_pipeline_run_events"),
        sa.UniqueConstraint(
            "pipeline_run_id",
            "sequence_number",
            name="uq_pipeline_run_events_run_sequence",
        ),
    )


def downgrade() -> None:
    op.drop_table("pipeline_run_events")

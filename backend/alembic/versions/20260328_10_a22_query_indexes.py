"""Create query indexes."""

from __future__ import annotations

from alembic import op


revision = "20260328_10"
down_revision = "20260328_09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_jobs_company_id_status", "jobs", ["company_id", "status"])
    op.create_index("ix_jobs_title", "jobs", ["title"])
    op.create_index("ix_jobs_location_text", "jobs", ["location_text"])
    op.create_index("ix_jobs_work_mode", "jobs", ["work_mode"])
    op.create_index("ix_jobs_posted_at", "jobs", ["posted_at"])
    op.create_index(
        "ix_applications_user_id_status_applied_at",
        "applications",
        ["user_id", "status", "applied_at"],
    )
    op.create_index(
        "ix_pipeline_runs_status_started_at",
        "pipeline_runs",
        ["status", "started_at"],
    )
    op.create_index(
        "ix_pipeline_runs_company_id_started_at",
        "pipeline_runs",
        ["company_id", "started_at"],
    )
    op.create_index(
        "ix_pipeline_run_events_pipeline_run_id_created_at",
        "pipeline_run_events",
        ["pipeline_run_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_pipeline_run_events_pipeline_run_id_created_at", table_name="pipeline_run_events")
    op.drop_index("ix_pipeline_runs_company_id_started_at", table_name="pipeline_runs")
    op.drop_index("ix_pipeline_runs_status_started_at", table_name="pipeline_runs")
    op.drop_index("ix_applications_user_id_status_applied_at", table_name="applications")
    op.drop_index("ix_jobs_posted_at", table_name="jobs")
    op.drop_index("ix_jobs_work_mode", table_name="jobs")
    op.drop_index("ix_jobs_location_text", table_name="jobs")
    op.drop_index("ix_jobs_title", table_name="jobs")
    op.drop_index("ix_jobs_company_id_status", table_name="jobs")

from __future__ import annotations

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from job_discovery_backend.db.base import Base
from job_discovery_backend.db.schema import (
    APPLICATION_STATUSES,
    COMPANY_LIFECYCLE_STATES,
    COMPANY_SOURCE_TYPES,
    JOB_STATUSES,
    JOB_WORK_MODES,
    PIPELINE_EVENT_LEVELS,
    PIPELINE_RUN_STATUSES,
    PIPELINE_RUN_TRIGGER_TYPES,
)


def _in_constraint(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    seed_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (
        CheckConstraint(
            _in_constraint("lifecycle_status", COMPANY_LIFECYCLE_STATES),
            name="companies_lifecycle_status_valid",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    website_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    lifecycle_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="active",
    )
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class CompanySource(Base):
    __tablename__ = "company_sources"
    __table_args__ = (
        UniqueConstraint("company_id", "source_type", name="uq_company_sources_company_source"),
        CheckConstraint(
            _in_constraint("source_type", COMPANY_SOURCE_TYPES),
            name="company_sources_source_type_valid",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    external_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    base_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=func.true(),
    )
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source_id", "source_job_key", name="uq_jobs_source_job_key"),
        UniqueConstraint("source_identity", name="uq_jobs_source_identity"),
        CheckConstraint(
            _in_constraint("status", JOB_STATUSES),
            name="jobs_status_valid",
        ),
        CheckConstraint(
            _in_constraint("work_mode", JOB_WORK_MODES),
            name="jobs_work_mode_valid",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[str] = mapped_column(
        ForeignKey("company_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_job_key: Mapped[str] = mapped_column(String(255), nullable=False)
    source_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    location_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    work_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="unknown",
    )
    employment_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="active",
    )
    posted_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    apply_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    description_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_seen_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    missed_sync_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )


class JobSnapshot(Base):
    __tablename__ = "job_snapshots"
    __table_args__ = (
        UniqueConstraint("job_id", "content_hash", name="uq_job_snapshots_job_content_hash"),
        CheckConstraint(
            "recorded_at >= observed_at",
            name="job_snapshots_recorded_after_observed",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    observed_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    source_updated_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    normalized_payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_applications_user_job"),
        CheckConstraint(
            _in_constraint("status", APPLICATION_STATUSES),
            name="applications_status_valid",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[str] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="saved",
    )
    applied_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SavedView(Base):
    __tablename__ = "saved_views"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_saved_views_user_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    filters: Mapped[dict] = mapped_column(JSON, nullable=False)
    sort: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=func.false(),
    )
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    __table_args__ = (
        CheckConstraint(
            _in_constraint("trigger_type", PIPELINE_RUN_TRIGGER_TYPES),
            name="pipeline_runs_trigger_type_valid",
        ),
        CheckConstraint(
            _in_constraint("status", PIPELINE_RUN_STATUSES),
            name="pipeline_runs_status_valid",
        ),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="pipeline_runs_finished_after_started",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_id: Mapped[str | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    requested_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="queued",
    )
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    finished_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PipelineRunEvent(Base):
    __tablename__ = "pipeline_run_events"
    __table_args__ = (
        UniqueConstraint(
            "pipeline_run_id",
            "sequence_number",
            name="uq_pipeline_run_events_run_sequence",
        ),
        CheckConstraint(
            _in_constraint("level", PIPELINE_EVENT_LEVELS),
            name="pipeline_run_events_level_valid",
        ),
        CheckConstraint(
            "sequence_number > 0",
            name="pipeline_run_events_sequence_positive",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    pipeline_run_id: Mapped[str] = mapped_column(
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_id: Mapped[str | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    level: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default="info",
    )
    sequence_number: Mapped[int] = mapped_column(nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

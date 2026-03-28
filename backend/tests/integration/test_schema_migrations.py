from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

from alembic import command
import pytest
from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from job_discovery_backend.db.migrate import build_alembic_config  # noqa: E402
from job_discovery_backend.db.models import (  # noqa: E402
    Application,
    Company,
    CompanySource,
    Job,
    JobSnapshot,
    PipelineRun,
    PipelineRunEvent,
    SavedView,
    User,
)


def _database_url(tmp_path: Path, name: str) -> str:
    return f"sqlite+pysqlite:///{tmp_path / name}"


def _migrated_engine(tmp_path: Path, name: str):
    database_url = _database_url(tmp_path, name)
    command.upgrade(build_alembic_config(database_url), "head")
    engine = create_engine(database_url)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def _seed_user(session: Session, user_id: str = "00000000-0000-0000-0000-000000000001") -> User:
    user = User(
        id=user_id,
        seed_key="local_user",
        display_name="Local User",
        email=None,
    )
    session.add(user)
    session.commit()
    return user


def _seed_company(session: Session, company_id: str = "00000000-0000-0000-0000-000000000101") -> Company:
    company = Company(
        id=company_id,
        slug="acme",
        name="Acme",
        website_url="https://example.com",
        description="Example company",
        lifecycle_status="active",
    )
    session.add(company)
    session.commit()
    return company


def _seed_company_source(
    session: Session,
    company_id: str,
    source_id: str = "00000000-0000-0000-0000-000000000201",
) -> CompanySource:
    source = CompanySource(
        id=source_id,
        company_id=company_id,
        source_type="greenhouse",
        external_key="acme",
        base_url="https://boards.greenhouse.io/acme",
        configuration={},
        is_enabled=True,
    )
    session.add(source)
    session.commit()
    return source


def _seed_job(
    session: Session,
    company_id: str,
    source_id: str,
    job_id: str = "00000000-0000-0000-0000-000000000301",
) -> Job:
    job = Job(
        id=job_id,
        company_id=company_id,
        source_id=source_id,
        source_job_key="job-1",
        source_identity="greenhouse:acme:job-1",
        title="Backend Engineer",
        location_text="Toronto, ON",
        work_mode="remote",
        employment_type="full_time",
        status="active",
        apply_url="https://example.com/jobs/1",
        description_text="A role",
    )
    session.add(job)
    session.commit()
    return job


def _seed_pipeline_run(
    session: Session,
    company_id: str,
    user_id: str,
    run_id: str = "00000000-0000-0000-0000-000000000401",
) -> PipelineRun:
    run = PipelineRun(
        id=run_id,
        company_id=company_id,
        requested_by_user_id=user_id,
        trigger_type="manual",
        status="queued",
        request_id="req-1",
        details={"source": "test"},
    )
    session.add(run)
    session.commit()
    return run


def test_baseline_migrations_apply_to_empty_database(tmp_path: Path) -> None:
    engine = _migrated_engine(tmp_path, "baseline.sqlite3")

    tables = set(inspect(engine).get_table_names())

    assert "alembic_version" in tables
    assert {
        "applications",
        "companies",
        "company_sources",
        "job_snapshots",
        "jobs",
        "pipeline_run_events",
        "pipeline_runs",
        "saved_views",
        "users",
    }.issubset(tables)


def test_users_table_enforces_unique_seed_key(tmp_path: Path) -> None:
    engine = _migrated_engine(tmp_path, "users.sqlite3")

    with Session(engine) as session:
        _seed_user(session)

        session.add(
            User(
                id="00000000-0000-0000-0000-000000000002",
                seed_key="local_user",
                display_name="Duplicate",
                email=None,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_companies_table_restricts_lifecycle_status(tmp_path: Path) -> None:
    engine = _migrated_engine(tmp_path, "companies.sqlite3")

    with Session(engine) as session:
        session.add(
            Company(
                id="00000000-0000-0000-0000-000000000102",
                slug="bad-status",
                name="Bad Status Co",
                website_url=None,
                description=None,
                lifecycle_status="invalid",
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_company_sources_enforce_company_fk_and_source_type(tmp_path: Path) -> None:
    engine = _migrated_engine(tmp_path, "company-sources.sqlite3")

    with Session(engine) as session:
        company = _seed_company(session)

        session.add(
            CompanySource(
                id="00000000-0000-0000-0000-000000000202",
                company_id=company.id,
                source_type="invalid",
                external_key=None,
                base_url=None,
                configuration={},
                is_enabled=True,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()

        session.add(
            CompanySource(
                id="00000000-0000-0000-0000-000000000203",
                company_id="00000000-0000-0000-0000-999999999999",
                source_type="greenhouse",
                external_key=None,
                base_url=None,
                configuration={},
                is_enabled=True,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_jobs_table_enforces_source_identity_uniqueness_and_required_title(tmp_path: Path) -> None:
    engine = _migrated_engine(tmp_path, "jobs.sqlite3")

    with Session(engine) as session:
        company = _seed_company(session)
        source = _seed_company_source(session, company.id)
        _seed_job(session, company.id, source.id)

        job = session.scalar(select(Job).where(Job.id == "00000000-0000-0000-0000-000000000301"))
        assert job is not None
        assert job.missed_sync_count == 0

        session.add(
            Job(
                id="00000000-0000-0000-0000-000000000302",
                company_id=company.id,
                source_id=source.id,
                source_job_key="job-2",
                source_identity="greenhouse:acme:job-1",
                title="Another",
                location_text=None,
                work_mode="remote",
                employment_type=None,
                status="active",
                apply_url=None,
                description_text=None,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()

        session.add(
            Job(
                id="00000000-0000-0000-0000-000000000303",
                company_id=company.id,
                source_id=source.id,
                source_job_key="job-3",
                source_identity="greenhouse:acme:job-3",
                title=None,
                location_text=None,
                work_mode="remote",
                employment_type=None,
                status="active",
                apply_url=None,
                description_text=None,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_job_snapshots_enforce_job_fk_and_timestamp_order(tmp_path: Path) -> None:
    engine = _migrated_engine(tmp_path, "job-snapshots.sqlite3")

    with Session(engine) as session:
        company = _seed_company(session)
        source = _seed_company_source(session, company.id)
        job = _seed_job(session, company.id, source.id)

        session.add(
            JobSnapshot(
                id="00000000-0000-0000-0000-000000000501",
                job_id=job.id,
                observed_at=datetime(2026, 3, 28, 12, 0, 0),
                recorded_at=datetime(2026, 3, 28, 11, 59, 59),
                source_updated_at=None,
                content_hash="hash-1",
                raw_payload={"raw": True},
                normalized_payload={"title": "Backend Engineer"},
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()

        session.add(
            JobSnapshot(
                id="00000000-0000-0000-0000-000000000502",
                job_id="00000000-0000-0000-0000-999999999999",
                observed_at=datetime(2026, 3, 28, 12, 0, 0),
                recorded_at=datetime(2026, 3, 28, 12, 0, 1),
                source_updated_at=None,
                content_hash="hash-2",
                raw_payload={"raw": True},
                normalized_payload={"title": "Backend Engineer"},
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_applications_enforce_unique_user_job_pair(tmp_path: Path) -> None:
    engine = _migrated_engine(tmp_path, "applications.sqlite3")

    with Session(engine) as session:
        user = _seed_user(session)
        company = _seed_company(session)
        source = _seed_company_source(session, company.id)
        job = _seed_job(session, company.id, source.id)

        session.add(
            Application(
                id="00000000-0000-0000-0000-000000000601",
                user_id=user.id,
                job_id=job.id,
                status="saved",
                applied_at=None,
                notes=None,
            )
        )
        session.commit()

        session.add(
            Application(
                id="00000000-0000-0000-0000-000000000602",
                user_id=user.id,
                job_id=job.id,
                status="applied",
                applied_at=datetime(2026, 3, 28, 12, 0, 0),
                notes=None,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_saved_views_enforce_user_ownership_and_unique_name(tmp_path: Path) -> None:
    engine = _migrated_engine(tmp_path, "saved-views.sqlite3")

    with Session(engine) as session:
        user = _seed_user(session)

        session.add(
            SavedView(
                id="00000000-0000-0000-0000-000000000701",
                user_id=user.id,
                name="Remote Roles",
                filters={"work_mode": "remote"},
                sort={"field": "posted_at", "direction": "desc"},
                is_default=False,
            )
        )
        session.commit()

        session.add(
            SavedView(
                id="00000000-0000-0000-0000-000000000702",
                user_id=user.id,
                name="Remote Roles",
                filters={"work_mode": "remote"},
                sort={"field": "posted_at", "direction": "desc"},
                is_default=False,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()

        session.add(
            SavedView(
                id="00000000-0000-0000-0000-000000000703",
                user_id="00000000-0000-0000-0000-999999999999",
                name="Broken",
                filters={},
                sort={},
                is_default=False,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_pipeline_runs_enforce_status_and_time_order(tmp_path: Path) -> None:
    engine = _migrated_engine(tmp_path, "pipeline-runs.sqlite3")

    with Session(engine) as session:
        user = _seed_user(session)
        company = _seed_company(session)

        session.add(
            PipelineRun(
                id="00000000-0000-0000-0000-000000000402",
                company_id=company.id,
                requested_by_user_id=user.id,
                trigger_type="manual",
                status="invalid",
                request_id=None,
                details=None,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()

        session.add(
            PipelineRun(
                id="00000000-0000-0000-0000-000000000403",
                company_id=company.id,
                requested_by_user_id=user.id,
                trigger_type="manual",
                status="running",
                request_id=None,
                details=None,
                started_at=datetime(2026, 3, 28, 12, 0, 0),
                finished_at=datetime(2026, 3, 28, 11, 0, 0),
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_pipeline_run_events_enforce_run_fk_and_sequence_uniqueness(tmp_path: Path) -> None:
    engine = _migrated_engine(tmp_path, "pipeline-run-events.sqlite3")

    with Session(engine) as session:
        user = _seed_user(session)
        company = _seed_company(session)
        run = _seed_pipeline_run(session, company.id, user.id)

        session.add(
            PipelineRunEvent(
                id="00000000-0000-0000-0000-000000000801",
                pipeline_run_id=run.id,
                company_id=company.id,
                event_type="started",
                level="info",
                sequence_number=1,
                message="Run started",
                payload={"step": 1},
            )
        )
        session.commit()

        session.add(
            PipelineRunEvent(
                id="00000000-0000-0000-0000-000000000802",
                pipeline_run_id=run.id,
                company_id=company.id,
                event_type="duplicate-sequence",
                level="warning",
                sequence_number=1,
                message="Duplicate sequence",
                payload=None,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()

        session.add(
            PipelineRunEvent(
                id="00000000-0000-0000-0000-000000000803",
                pipeline_run_id="00000000-0000-0000-0000-999999999999",
                company_id=company.id,
                event_type="missing-run",
                level="error",
                sequence_number=2,
                message="Missing run",
                payload=None,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_query_indexes_exist(tmp_path: Path) -> None:
    engine = _migrated_engine(tmp_path, "indexes.sqlite3")
    inspector = inspect(engine)

    job_indexes = {index["name"] for index in inspector.get_indexes("jobs")}
    application_indexes = {index["name"] for index in inspector.get_indexes("applications")}
    run_indexes = {index["name"] for index in inspector.get_indexes("pipeline_runs")}
    event_indexes = {index["name"] for index in inspector.get_indexes("pipeline_run_events")}

    assert {
        "ix_jobs_company_id_status",
        "ix_jobs_location_text",
        "ix_jobs_posted_at",
        "ix_jobs_title",
        "ix_jobs_work_mode",
    }.issubset(job_indexes)
    assert "ix_applications_user_id_status_applied_at" in application_indexes
    assert {
        "ix_pipeline_runs_company_id_started_at",
        "ix_pipeline_runs_status_started_at",
    }.issubset(run_indexes)
    assert "ix_pipeline_run_events_pipeline_run_id_created_at" in event_indexes

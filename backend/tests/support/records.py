from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from job_discovery_backend.db.models import Application, Company, CompanySource, Job, PipelineRun, PipelineRunEvent, SavedView, User


def seed_user(
    session: Session,
    *,
    user_id: str = "11111111-1111-1111-1111-111111111111",
    seed_key: str = "local_user",
    display_name: str = "Local User",
) -> User:
    user = User(id=user_id, seed_key=seed_key, display_name=display_name, email=None)
    session.add(user)
    session.commit()
    return user


def seed_company(
    session: Session,
    *,
    company_id: str,
    slug: str,
    name: str,
    lifecycle_status: str = "active",
) -> Company:
    company = Company(
        id=company_id,
        slug=slug,
        name=name,
        website_url=f"https://{slug}.example.com",
        description=f"{name} company",
        lifecycle_status=lifecycle_status,
    )
    session.add(company)
    session.commit()
    return company


def seed_company_source(
    session: Session,
    *,
    source_id: str,
    company_id: str,
    source_type: str = "greenhouse",
    external_key: str | None = None,
    base_url: str = "https://boards.example.com/test",
    is_enabled: bool = True,
) -> CompanySource:
    source = CompanySource(
        id=source_id,
        company_id=company_id,
        source_type=source_type,
        external_key=external_key or company_id,
        base_url=base_url,
        configuration={},
        is_enabled=is_enabled,
    )
    session.add(source)
    session.commit()
    return source


def seed_job(
    session: Session,
    *,
    job_id: str,
    company_id: str,
    source_id: str,
    title: str,
    location_text: str,
    work_mode: str,
    posted_at: datetime,
    description_text: str,
    status: str = "active",
) -> Job:
    job = Job(
        id=job_id,
        company_id=company_id,
        source_id=source_id,
        source_job_key=f"source-{job_id}",
        source_identity=f"identity-{job_id}",
        title=title,
        location_text=location_text,
        work_mode=work_mode,
        employment_type="full_time",
        status=status,
        posted_at=posted_at,
        apply_url=f"https://example.com/jobs/{job_id}",
        description_text=description_text,
    )
    session.add(job)
    session.commit()
    return job


def seed_application(
    session: Session,
    *,
    application_id: str,
    user_id: str,
    job_id: str,
    status: str,
    applied_at: datetime | None = None,
    notes: str | None = None,
) -> Application:
    application = Application(
        id=application_id,
        user_id=user_id,
        job_id=job_id,
        status=status,
        applied_at=applied_at,
        notes=notes,
    )
    session.add(application)
    session.commit()
    return application


def seed_saved_view(
    session: Session,
    *,
    view_id: str,
    user_id: str,
    name: str,
    filters: dict,
    sort: dict,
    is_default: bool = False,
) -> SavedView:
    view = SavedView(
        id=view_id,
        user_id=user_id,
        name=name,
        filters=filters,
        sort=sort,
        is_default=is_default,
    )
    session.add(view)
    session.commit()
    return view


def seed_pipeline_run(
    session: Session,
    *,
    run_id: str,
    company_id: str | None,
    user_id: str | None,
    trigger_type: str,
    status: str,
    request_id: str | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    details: dict | None = None,
) -> PipelineRun:
    run = PipelineRun(
        id=run_id,
        company_id=company_id,
        requested_by_user_id=user_id,
        trigger_type=trigger_type,
        status=status,
        request_id=request_id,
        details=details,
        started_at=started_at or datetime.now(UTC),
        finished_at=finished_at,
    )
    session.add(run)
    session.commit()
    return run


def seed_pipeline_run_event(
    session: Session,
    *,
    event_id: str,
    pipeline_run_id: str,
    company_id: str | None,
    event_type: str,
    level: str,
    sequence_number: int,
    message: str,
    payload: dict | None = None,
) -> PipelineRunEvent:
    event = PipelineRunEvent(
        id=event_id,
        pipeline_run_id=pipeline_run_id,
        company_id=company_id,
        event_type=event_type,
        level=level,
        sequence_number=sequence_number,
        message=message,
        payload=payload,
    )
    session.add(event)
    session.commit()
    return event

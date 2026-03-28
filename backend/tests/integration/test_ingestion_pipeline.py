from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from support.api import session_for_database  # noqa: E402
from support.records import seed_company, seed_company_source, seed_user  # noqa: E402

from job_discovery_backend.db.models import PipelineRun, PipelineRunEvent  # noqa: E402
from job_discovery_backend.ingestion.pipeline import (  # noqa: E402
    CompanySyncOutcome,
    PipelineEventLogger,
    create_sync_request,
    prepare_scheduled_sync_requests,
    process_sync_request,
)


def _database_url(tmp_path: Path) -> str:
    return f"sqlite+pysqlite:///{tmp_path / 'ingestion-pipeline.sqlite3'}"


def test_create_sync_request_persists_a_queued_run_and_event(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)
    with session_for_database(database_url) as session:
        user = seed_user(session)
        company = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222231",
            slug="openai",
            name="OpenAI",
        )

        request = create_sync_request(
            session,
            company_id=company.id,
            requested_by_user_id=user.id,
            request_id="req-manual-1",
            trigger_type="manual",
        )
        session.commit()

        run = session.get(PipelineRun, request.pipeline_run_id)
        events = session.query(PipelineRunEvent).where(PipelineRunEvent.pipeline_run_id == run.id).all()

    assert run is not None
    assert run.status == "queued"
    assert run.trigger_type == "manual"
    assert len(events) == 1
    assert events[0].event_type == "pipeline.queued"


def test_prepare_scheduled_sync_requests_creates_runs_only_for_active_enabled_companies(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)
    with session_for_database(database_url) as session:
        active = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222232",
            slug="active",
            name="Active Co",
        )
        paused = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222233",
            slug="paused",
            name="Paused Co",
            lifecycle_status="paused",
        )
        disabled = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222234",
            slug="disabled",
            name="Disabled Co",
        )
        seed_company_source(
            session,
            source_id="33333333-3333-3333-3333-333333333431",
            company_id=active.id,
        )
        seed_company_source(
            session,
            source_id="33333333-3333-3333-3333-333333333432",
            company_id=paused.id,
        )
        seed_company_source(
            session,
            source_id="33333333-3333-3333-3333-333333333433",
            company_id=disabled.id,
            is_enabled=False,
        )

        requests = prepare_scheduled_sync_requests(session)
        session.commit()

    assert [request.company_id for request in requests] == [active.id]


def test_process_sync_request_emits_started_and_completed_events(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)
    with session_for_database(database_url) as session:
        company = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222235",
            slug="openai",
            name="OpenAI",
        )
        seed_company_source(
            session,
            source_id="33333333-3333-3333-3333-333333333434",
            company_id=company.id,
        )
        request = create_sync_request(
            session,
            company_id=company.id,
            requested_by_user_id=None,
            request_id=None,
            trigger_type="scheduled",
        )
        session.commit()

    def processor(session, logger: PipelineEventLogger, company, sources, request):
        logger.log("company.custom", "Processed company", payload={"company_id": company.id, "source_count": len(sources)})
        return CompanySyncOutcome(status="succeeded", details={"company_id": company.id, "source_count": len(sources)})

    outcome = process_sync_request(database_url, request, processor=processor)

    assert outcome.status == "succeeded"

    with session_for_database(database_url) as session:
        run = session.get(PipelineRun, request.pipeline_run_id)
        events = session.query(PipelineRunEvent).where(PipelineRunEvent.pipeline_run_id == run.id).all()

    assert run is not None
    assert run.status == "succeeded"
    assert [event.event_type for event in events] == [
        "pipeline.queued",
        "pipeline.started",
        "company.custom",
        "pipeline.completed",
    ]

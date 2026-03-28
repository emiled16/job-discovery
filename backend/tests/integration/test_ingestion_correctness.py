from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import sys

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from support.api import session_for_database  # noqa: E402
from support.records import seed_company, seed_company_source  # noqa: E402

from job_discovery_backend.db.models import Job, JobSnapshot, PipelineRun, PipelineRunEvent  # noqa: E402
from job_discovery_backend.ingestion.models import AdapterFetchResult, NormalizedJob  # noqa: E402
from job_discovery_backend.ingestion.pipeline import create_sync_request, process_sync_request, run_scheduled_sync  # noqa: E402
from job_discovery_backend.ingestion.processor import build_company_sync_processor, source_identity_namespace  # noqa: E402


def _database_url(tmp_path: Path, name: str = "ingestion-correctness.sqlite3") -> str:
    return f"sqlite+pysqlite:///{tmp_path / name}"


@dataclass
class FakeAdapter:
    jobs_by_external_key: dict[str, list[tuple[NormalizedJob, ...]]]

    def fetch(self, source) -> AdapterFetchResult:
        queue = self.jobs_by_external_key[source.external_key]
        jobs = queue.pop(0)
        return AdapterFetchResult(jobs=jobs)


def _job(
    *,
    source_job_key: str,
    title: str,
    description_text: str,
) -> NormalizedJob:
    return NormalizedJob(
        source_job_key=source_job_key,
        title=title,
        location_text="Remote - Canada",
        work_mode="remote",
        employment_type="Full-time",
        posted_at=datetime(2026, 3, 20, 12, 0, tzinfo=UTC),
        source_updated_at=datetime(2026, 3, 21, 12, 0, tzinfo=UTC),
        apply_url=f"https://example.com/jobs/{source_job_key}",
        description_text=description_text,
        raw_payload={"id": source_job_key, "title": title, "description": description_text},
    )


def _processor(fake_adapter: FakeAdapter, *, threshold: int = 3):
    return build_company_sync_processor(
        missed_cycle_threshold=threshold,
        adapter_lookup=lambda source: fake_adapter,
        observed_at_factory=lambda: datetime(2026, 3, 28, 12, 0, tzinfo=UTC),
    )


def test_sync_request_is_idempotent_and_persists_stateful_snapshots(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path, "idempotent.sqlite3")
    with session_for_database(database_url) as session:
        company = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222241",
            slug="openai",
            name="OpenAI",
        )
        seed_company_source(
            session,
            source_id="33333333-3333-3333-3333-333333333441",
            company_id=company.id,
            external_key="openai",
        )
        request = create_sync_request(
            session,
            company_id=company.id,
            requested_by_user_id=None,
            request_id="req-idempotent",
            trigger_type="manual",
        )
        session.commit()

    fake_adapter = FakeAdapter(
        jobs_by_external_key={
            "openai": [
                (
                    _job(source_job_key="job-1", title="ML Engineer", description_text="First snapshot"),
                ),
                (
                    _job(source_job_key="job-1", title="ML Engineer", description_text="First snapshot"),
                ),
                (
                    _job(source_job_key="job-1", title="ML Engineer", description_text="Updated snapshot"),
                ),
            ]
        }
    )

    process_sync_request(database_url, request, processor=_processor(fake_adapter))
    process_sync_request(database_url, request, processor=_processor(fake_adapter))
    process_sync_request(database_url, request, processor=_processor(fake_adapter))

    with session_for_database(database_url) as session:
        jobs = session.scalars(select(Job)).all()
        snapshots = session.scalars(select(JobSnapshot)).all()

    assert len(jobs) == 1
    assert jobs[0].source_identity == "greenhouse:openai:job-1"
    assert len(snapshots) == 2


def test_reconciliation_closes_after_default_threshold_supports_override_and_reopens(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path, "reconcile.sqlite3")
    with session_for_database(database_url) as session:
        company = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222242",
            slug="vercel",
            name="Vercel",
        )
        source = seed_company_source(
            session,
            source_id="33333333-3333-3333-3333-333333333442",
            company_id=company.id,
            external_key="vercel",
        )
        request = create_sync_request(
            session,
            company_id=company.id,
            requested_by_user_id=None,
            request_id="req-reconcile",
            trigger_type="manual",
        )
        session.commit()

    fake_adapter = FakeAdapter(
        jobs_by_external_key={
            "vercel": [
                (
                    _job(source_job_key="job-a", title="Backend Engineer", description_text="A1"),
                    _job(source_job_key="job-b", title="Data Engineer", description_text="B1"),
                ),
                (
                    _job(source_job_key="job-a", title="Backend Engineer", description_text="A1"),
                ),
                (
                    _job(source_job_key="job-a", title="Backend Engineer", description_text="A1"),
                ),
                (
                    _job(source_job_key="job-a", title="Backend Engineer", description_text="A1"),
                ),
                (
                    _job(source_job_key="job-a", title="Backend Engineer", description_text="A1"),
                    _job(source_job_key="job-b", title="Data Engineer", description_text="B2"),
                ),
            ]
        }
    )

    default_processor = _processor(fake_adapter, threshold=3)
    process_sync_request(database_url, request, processor=default_processor)
    process_sync_request(database_url, request, processor=default_processor)
    process_sync_request(database_url, request, processor=default_processor)
    process_sync_request(database_url, request, processor=default_processor)

    with session_for_database(database_url) as session:
        namespace = source_identity_namespace(source)
        closed_job = session.scalar(select(Job).where(Job.source_identity == f"{namespace}:job-b"))
        assert closed_job is not None
        assert closed_job.status == "closed"
        assert closed_job.missed_sync_count == 3
        closed_job_id = closed_job.id

    process_sync_request(database_url, request, processor=default_processor)

    with session_for_database(database_url) as session:
        reopened_job = session.get(Job, closed_job_id)
        assert reopened_job is not None
        assert reopened_job.status == "active"
        assert reopened_job.closed_at is None
        assert reopened_job.missed_sync_count == 0

    override_database_url = _database_url(tmp_path, "reconcile-override.sqlite3")
    with session_for_database(override_database_url) as session:
        company = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222243",
            slug="anthropic",
            name="Anthropic",
        )
        seed_company_source(
            session,
            source_id="33333333-3333-3333-3333-333333333443",
            company_id=company.id,
            external_key="anthropic",
        )
        request = create_sync_request(
            session,
            company_id=company.id,
            requested_by_user_id=None,
            request_id="req-override",
            trigger_type="manual",
        )
        session.commit()

    override_adapter = FakeAdapter(
        jobs_by_external_key={
            "anthropic": [
                (
                    _job(source_job_key="job-x", title="Research Engineer", description_text="X1"),
                    _job(source_job_key="job-y", title="Platform Engineer", description_text="Y1"),
                ),
                (
                    _job(source_job_key="job-x", title="Research Engineer", description_text="X1"),
                ),
            ]
        }
    )
    process_sync_request(override_database_url, request, processor=_processor(override_adapter, threshold=1))
    process_sync_request(override_database_url, request, processor=_processor(override_adapter, threshold=1))

    with session_for_database(override_database_url) as session:
        closed_job = session.scalar(select(Job).where(Job.source_identity == "greenhouse:anthropic:job-y"))

    assert closed_job is not None
    assert closed_job.status == "closed"
    assert closed_job.missed_sync_count == 1


def test_scheduled_sync_and_manual_run_produce_observable_pipeline_records(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path, "scheduled.sqlite3")
    with session_for_database(database_url) as session:
        active_one = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222244",
            slug="openai",
            name="OpenAI",
        )
        active_two = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222245",
            slug="vercel",
            name="Vercel",
        )
        seed_company_source(
            session,
            source_id="33333333-3333-3333-3333-333333333444",
            company_id=active_one.id,
            external_key="openai",
        )
        seed_company_source(
            session,
            source_id="33333333-3333-3333-3333-333333333445",
            company_id=active_two.id,
            external_key="vercel",
        )
        manual_request = create_sync_request(
            session,
            company_id=active_one.id,
            requested_by_user_id=None,
            request_id="req-manual",
            trigger_type="manual",
        )
        session.commit()

    fake_adapter = FakeAdapter(
        jobs_by_external_key={
            "openai": [(_job(source_job_key="job-1", title="ML Engineer", description_text="A"),), (_job(source_job_key="job-1", title="ML Engineer", description_text="A"),)],
            "vercel": [(_job(source_job_key="job-2", title="Platform Engineer", description_text="B"),)],
        }
    )
    processor = _processor(fake_adapter)

    manual_outcome = process_sync_request(database_url, manual_request, processor=processor)
    scheduled_result = run_scheduled_sync(database_url, max_workers=2, processor=processor)

    assert manual_outcome.status == "succeeded"
    assert scheduled_result == {"scheduled_count": 2, "statuses": ["succeeded", "succeeded"]}

    with session_for_database(database_url) as session:
        runs = session.scalars(select(PipelineRun).order_by(PipelineRun.started_at.asc(), PipelineRun.id.asc())).all()
        events = session.scalars(select(PipelineRunEvent).order_by(PipelineRunEvent.pipeline_run_id.asc(), PipelineRunEvent.sequence_number.asc())).all()

    assert len(runs) == 3
    assert [run.trigger_type for run in runs] == ["manual", "scheduled", "scheduled"]
    assert all(run.status == "succeeded" for run in runs)
    assert any(event.event_type == "source.sync.completed" for event in events)
    assert any(event.event_type == "pipeline.completed" for event in events)

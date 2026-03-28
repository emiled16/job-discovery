from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, TypeVar
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from job_discovery_backend.db.models import Company, CompanySource, PipelineRun, PipelineRunEvent
from job_discovery_backend.db.session import session_scope

SyncResultStatus = str


@dataclass(frozen=True)
class SyncCompanyRequest:
    pipeline_run_id: str
    company_id: str
    requested_by_user_id: str | None
    request_id: str | None
    trigger_type: str

    def as_payload(self) -> dict[str, Any]:
        return {
            "pipeline_run_id": self.pipeline_run_id,
            "company_id": self.company_id,
            "requested_by_user_id": self.requested_by_user_id,
            "request_id": self.request_id,
            "trigger_type": self.trigger_type,
        }


@dataclass(frozen=True)
class CompanySyncOutcome:
    status: SyncResultStatus
    details: dict[str, Any]


ProcessCompanySync = Callable[
    [Session, "PipelineEventLogger", Company, list[CompanySource], SyncCompanyRequest],
    CompanySyncOutcome,
]


def utcnow() -> datetime:
    return datetime.now(UTC)


def _ensure_run(
    session: Session,
    *,
    pipeline_run_id: str | None,
    company_id: str,
    requested_by_user_id: str | None,
    request_id: str | None,
    trigger_type: str,
) -> PipelineRun:
    if pipeline_run_id is not None:
        existing = session.get(PipelineRun, pipeline_run_id)
        if existing is not None:
            return existing

    run = PipelineRun(
        id=pipeline_run_id or str(uuid4()),
        company_id=company_id,
        requested_by_user_id=requested_by_user_id,
        trigger_type=trigger_type,
        status="queued",
        request_id=request_id,
        details=None,
        started_at=utcnow(),
        finished_at=None,
    )
    session.add(run)
    session.flush()
    return run


class PipelineEventLogger:
    def __init__(self, session: Session, *, pipeline_run_id: str, company_id: str | None) -> None:
        self._session = session
        self._pipeline_run_id = pipeline_run_id
        self._company_id = company_id
        self._next_sequence = (  # Keep sequence numbers monotonic even if a run already has queued events.
            session.scalar(
                select(func.max(PipelineRunEvent.sequence_number)).where(
                    PipelineRunEvent.pipeline_run_id == pipeline_run_id
                )
            )
            or 0
        ) + 1

    def log(
        self,
        event_type: str,
        message: str,
        *,
        level: str = "info",
        payload: dict[str, Any] | None = None,
    ) -> PipelineRunEvent:
        event = PipelineRunEvent(
            id=str(uuid4()),
            pipeline_run_id=self._pipeline_run_id,
            company_id=self._company_id,
            event_type=event_type,
            level=level,
            sequence_number=self._next_sequence,
            message=message,
            payload=payload,
        )
        self._next_sequence += 1
        self._session.add(event)
        self._session.flush()
        return event


def create_sync_request(
    session: Session,
    *,
    company_id: str,
    requested_by_user_id: str | None,
    request_id: str | None,
    trigger_type: str,
    pipeline_run_id: str | None = None,
) -> SyncCompanyRequest:
    run = _ensure_run(
        session,
        pipeline_run_id=pipeline_run_id,
        company_id=company_id,
        requested_by_user_id=requested_by_user_id,
        request_id=request_id,
        trigger_type=trigger_type,
    )
    PipelineEventLogger(session, pipeline_run_id=run.id, company_id=company_id).log(
        "pipeline.queued",
        "Sync queued",
        payload={"trigger_type": trigger_type},
    )
    return SyncCompanyRequest(
        pipeline_run_id=run.id,
        company_id=company_id,
        requested_by_user_id=requested_by_user_id,
        request_id=request_id,
        trigger_type=trigger_type,
    )


def prepare_scheduled_sync_requests(
    session: Session,
    *,
    request_id: str | None = None,
) -> tuple[SyncCompanyRequest, ...]:
    company_ids = session.scalars(
        select(Company.id)
        .join(CompanySource, CompanySource.company_id == Company.id)
        .where(Company.lifecycle_status == "active", CompanySource.is_enabled.is_(True))
        .distinct()
        .order_by(Company.id.asc())
    ).all()
    return tuple(
        create_sync_request(
            session,
            company_id=company_id,
            requested_by_user_id=None,
            request_id=request_id,
            trigger_type="scheduled",
        )
        for company_id in company_ids
    )


def _default_company_processor(
    session: Session,
    logger: PipelineEventLogger,
    company: Company,
    sources: list[CompanySource],
    request: SyncCompanyRequest,
) -> CompanySyncOutcome:
    logger.log(
        "company.sources.resolved",
        "Resolved company sources for sync",
        payload={"company_id": company.id, "source_count": len(sources), "trigger_type": request.trigger_type},
    )
    return CompanySyncOutcome(
        status="succeeded",
        details={"company_id": company.id, "source_count": len(sources), "jobs_seen": 0},
    )


def process_sync_request(
    database_url: str,
    request: SyncCompanyRequest,
    *,
    processor: ProcessCompanySync | None = None,
) -> CompanySyncOutcome:
    company_processor = processor or _default_company_processor
    with session_scope(database_url) as session:
        run = _ensure_run(
            session,
            pipeline_run_id=request.pipeline_run_id,
            company_id=request.company_id,
            requested_by_user_id=request.requested_by_user_id,
            request_id=request.request_id,
            trigger_type=request.trigger_type,
        )
        run.status = "running"
        logger = PipelineEventLogger(session, pipeline_run_id=run.id, company_id=request.company_id)
        logger.log(
            "pipeline.started",
            "Sync started",
            payload={"trigger_type": request.trigger_type, "request_id": request.request_id},
        )

        company = session.get(Company, request.company_id)
        if company is None:
            run.status = "failed"
            run.finished_at = utcnow()
            run.details = {"company_id": request.company_id, "error": "company_not_found"}
            logger.log(
                "pipeline.failed",
                "Sync failed because the company no longer exists",
                level="error",
                payload=run.details,
            )
            return CompanySyncOutcome(status="failed", details=run.details)

        sources = session.scalars(
            select(CompanySource)
            .where(CompanySource.company_id == company.id, CompanySource.is_enabled.is_(True))
            .order_by(CompanySource.created_at.asc(), CompanySource.id.asc())
        ).all()
        if not sources:
            run.status = "failed"
            run.finished_at = utcnow()
            run.details = {"company_id": company.id, "error": "no_enabled_sources"}
            logger.log(
                "pipeline.failed",
                "Sync failed because the company has no enabled sources",
                level="error",
                payload=run.details,
            )
            return CompanySyncOutcome(status="failed", details=run.details)

        try:
            outcome = company_processor(session, logger, company, sources, request)
        except Exception as exc:
            run.status = "failed"
            run.finished_at = utcnow()
            run.details = {"company_id": company.id, "error": str(exc)}
            logger.log(
                "pipeline.failed",
                "Sync failed with an unhandled ingestion error",
                level="error",
                payload=run.details,
            )
            return CompanySyncOutcome(status="failed", details=run.details)

        run.status = outcome.status
        run.finished_at = utcnow()
        run.details = outcome.details
        logger.log(
            "pipeline.completed",
            "Sync completed",
            payload={"status": outcome.status, **outcome.details},
        )
        return outcome


T = TypeVar("T")
R = TypeVar("R")


def run_in_parallel(
    items: Sequence[T],
    worker: Callable[[T], R],
    *,
    max_workers: int,
) -> list[R]:
    if max_workers <= 1 or len(items) <= 1:
        return [worker(item) for item in items]

    results: list[R | None] = [None] * len(items)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures: dict[Future[R], int] = {
            executor.submit(worker, item): index for index, item in enumerate(items)
        }
        for future, index in futures.items():
            results[index] = future.result()

    return [result for result in results if result is not None]


def run_scheduled_sync(
    database_url: str,
    *,
    max_workers: int,
    processor: ProcessCompanySync | None = None,
) -> dict[str, Any]:
    with session_scope(database_url) as session:
        requests = prepare_scheduled_sync_requests(session)

    outcomes = run_in_parallel(
        list(requests),
        lambda request: process_sync_request(database_url, request, processor=processor),
        max_workers=max_workers,
    )
    return {
        "scheduled_count": len(requests),
        "statuses": [outcome.status for outcome in outcomes],
    }

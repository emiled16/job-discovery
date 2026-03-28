from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from job_discovery_backend.db.models import Company, CompanySource, Job, JobSnapshot
from job_discovery_backend.ingestion.models import AdapterFetchResult, NormalizedJob
from job_discovery_backend.ingestion.pipeline import CompanySyncOutcome, PipelineEventLogger, ProcessCompanySync, SyncCompanyRequest
from job_discovery_backend.ingestion.registry import get_adapter_for_source


def source_identity_namespace(source: CompanySource) -> str:
    key = (source.external_key or source.base_url or source.id).strip()
    return f"{source.source_type}:{key}"


def build_source_identity(source: CompanySource, job: NormalizedJob) -> str:
    return f"{source_identity_namespace(source)}:{job.source_job_key}"


def _snapshot_hash(job: NormalizedJob) -> str:
    payload = json.dumps(job.normalized_payload(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SourceSyncStats:
    fetched: int = 0
    created: int = 0
    updated: int = 0
    reopened: int = 0
    unchanged: int = 0
    missing: int = 0
    closed: int = 0
    snapshots_created: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "fetched": self.fetched,
            "created": self.created,
            "updated": self.updated,
            "reopened": self.reopened,
            "unchanged": self.unchanged,
            "missing": self.missing,
            "closed": self.closed,
            "snapshots_created": self.snapshots_created,
        }


def _persist_snapshot(
    session: Session,
    *,
    job_record: Job,
    job: NormalizedJob,
    observed_at: datetime,
) -> bool:
    content_hash = _snapshot_hash(job)
    existing = session.scalar(
        select(JobSnapshot).where(JobSnapshot.job_id == job_record.id, JobSnapshot.content_hash == content_hash)
    )
    if existing is not None:
        return False

    session.add(
        JobSnapshot(
            id=str(uuid4()),
            job_id=job_record.id,
            observed_at=observed_at,
            source_updated_at=job.source_updated_at,
            content_hash=content_hash,
            raw_payload=job.raw_payload,
            normalized_payload=job.normalized_payload(),
        )
    )
    session.flush()
    return True


def _apply_job_state(
    *,
    job_record: Job,
    source: CompanySource,
    job: NormalizedJob,
    observed_at: datetime,
) -> tuple[bool, bool]:
    was_closed = job_record.status == "closed"
    changed = (
        job_record.source_id != source.id
        or job_record.source_job_key != job.source_job_key
        or job_record.title != job.title
        or job_record.location_text != job.location_text
        or job_record.work_mode != job.work_mode
        or job_record.employment_type != job.employment_type
        or job_record.posted_at != job.posted_at
        or job_record.apply_url != job.apply_url
        or job_record.description_text != job.description_text
        or was_closed
    )

    job_record.source_id = source.id
    job_record.source_job_key = job.source_job_key
    job_record.title = job.title
    job_record.location_text = job.location_text
    job_record.work_mode = job.work_mode
    job_record.employment_type = job.employment_type
    job_record.posted_at = job.posted_at
    job_record.apply_url = job.apply_url
    job_record.description_text = job.description_text
    job_record.status = "active"
    job_record.closed_at = None
    job_record.last_seen_at = observed_at
    job_record.missed_sync_count = 0
    return changed, was_closed


def reconcile_source_jobs(
    session: Session,
    *,
    logger: PipelineEventLogger,
    company: Company,
    source: CompanySource,
    fetched_jobs: tuple[NormalizedJob, ...],
    observed_at: datetime,
    missed_cycle_threshold: int,
) -> SourceSyncStats:
    namespace = source_identity_namespace(source)
    stats = SourceSyncStats(fetched=len(fetched_jobs))
    seen_identities: set[str] = set()
    mutable_stats = stats.as_dict()

    for normalized_job in fetched_jobs:
        source_identity = build_source_identity(source, normalized_job)
        seen_identities.add(source_identity)

        job_record = session.scalar(select(Job).where(Job.source_identity == source_identity))
        if job_record is None:
            job_record = Job(
                id=str(uuid4()),
                company_id=company.id,
                source_id=source.id,
                source_job_key=normalized_job.source_job_key,
                source_identity=source_identity,
                title=normalized_job.title,
                location_text=normalized_job.location_text,
                work_mode=normalized_job.work_mode,
                employment_type=normalized_job.employment_type,
                status="active",
                posted_at=normalized_job.posted_at,
                closed_at=None,
                apply_url=normalized_job.apply_url,
                description_text=normalized_job.description_text,
                last_seen_at=observed_at,
                missed_sync_count=0,
            )
            session.add(job_record)
            session.flush()
            mutable_stats["created"] += 1
        else:
            changed, reopened = _apply_job_state(
                job_record=job_record,
                source=source,
                job=normalized_job,
                observed_at=observed_at,
            )
            if reopened:
                logger.log(
                    "job.reopened",
                    "Reopened previously closed job",
                    payload={"job_id": job_record.id, "source_identity": source_identity},
                )
                mutable_stats["reopened"] += 1
            elif changed:
                mutable_stats["updated"] += 1
            else:
                mutable_stats["unchanged"] += 1

        if _persist_snapshot(session, job_record=job_record, job=normalized_job, observed_at=observed_at):
            mutable_stats["snapshots_created"] += 1

    active_jobs = session.scalars(
        select(Job).where(
            Job.company_id == company.id,
            Job.status == "active",
            Job.source_identity.like(f"{namespace}:%"),
        )
    ).all()
    for active_job in active_jobs:
        if active_job.source_identity in seen_identities:
            continue
        mutable_stats["missing"] += 1
        active_job.missed_sync_count += 1
        if active_job.missed_sync_count >= missed_cycle_threshold:
            active_job.status = "closed"
            active_job.closed_at = observed_at
            logger.log(
                "job.closed",
                "Closed job after missed sync threshold",
                payload={
                    "job_id": active_job.id,
                    "source_identity": active_job.source_identity,
                    "missed_sync_count": active_job.missed_sync_count,
                    "threshold": missed_cycle_threshold,
                },
            )
            mutable_stats["closed"] += 1

    return SourceSyncStats(**mutable_stats)


def build_company_sync_processor(
    *,
    missed_cycle_threshold: int,
    adapter_lookup=get_adapter_for_source,
    observed_at_factory=lambda: datetime.now(UTC),
) -> ProcessCompanySync:
    def processor(
        session: Session,
        logger: PipelineEventLogger,
        company: Company,
        sources: list[CompanySource],
        request: SyncCompanyRequest,
    ) -> CompanySyncOutcome:
        totals = SourceSyncStats().as_dict()
        failures: list[dict[str, Any]] = []

        for source in sources:
            logger.log(
                "source.sync.started",
                "Syncing source",
                payload={"source_id": source.id, "source_type": source.source_type},
            )
            try:
                adapter = adapter_lookup(source)
                result: AdapterFetchResult = adapter.fetch(source)
                observed_at = observed_at_factory()
                stats = reconcile_source_jobs(
                    session,
                    logger=logger,
                    company=company,
                    source=source,
                    fetched_jobs=result.jobs,
                    observed_at=observed_at,
                    missed_cycle_threshold=missed_cycle_threshold,
                )
                logger.log(
                    "source.sync.completed",
                    "Completed source sync",
                    payload={"source_id": source.id, "source_type": source.source_type, **stats.as_dict()},
                )
                for key, value in stats.as_dict().items():
                    totals[key] += value
            except Exception as exc:
                failures.append({"source_id": source.id, "source_type": source.source_type, "error": str(exc)})
                logger.log(
                    "source.sync.failed",
                    "Source sync failed",
                    level="error",
                    payload=failures[-1],
                )

        status = "failed" if failures and totals["fetched"] == 0 else "partial" if failures else "succeeded"
        return CompanySyncOutcome(
            status=status,
            details={
                "company_id": company.id,
                "request_id": request.request_id,
                "missed_cycle_threshold": missed_cycle_threshold,
                **totals,
                "failures": failures,
            },
        )

    return processor

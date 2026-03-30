from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from job_discovery_backend.db.models import CompanySource
from job_discovery_backend.ingestion.adapters.base import BaseJobSourceAdapter, fetch_text
from job_discovery_backend.ingestion.html_job_postings import extract_normalized_jobs_from_html
from job_discovery_backend.ingestion.models import AdapterFetchResult, IngestionError, NormalizedJob, infer_work_mode


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return datetime.fromisoformat(normalized.replace("Z", "+00:00")).astimezone(UTC)


def _string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_inline_job(job: dict[str, Any]) -> NormalizedJob:
    location_text = _string(job.get("location_text"))
    employment_type = _string(job.get("employment_type"))
    work_mode = _string(job.get("work_mode")) or infer_work_mode(location_text, employment_type)
    return NormalizedJob(
        source_job_key=_string(job.get("source_job_key") or job.get("id") or job.get("apply_url") or job.get("title")) or "",
        title=_string(job.get("title")) or "",
        location_text=location_text,
        work_mode=work_mode,
        employment_type=employment_type,
        posted_at=_parse_datetime(_string(job.get("posted_at"))),
        source_updated_at=_parse_datetime(_string(job.get("source_updated_at"))),
        apply_url=_string(job.get("apply_url")),
        description_text=_string(job.get("description_text")),
        raw_payload=job,
    )


class ManualAdapter(BaseJobSourceAdapter):
    def __init__(
        self,
        *,
        timeout_seconds: int = 30,
    ) -> None:
        super().__init__(source_type="manual", request_timeout_seconds=timeout_seconds)

    def build_request_url(self, source: CompanySource) -> str:
        configuration = source.configuration or {}
        configured_url = _string(configuration.get("careers_url") if isinstance(configuration, dict) else None)
        if configured_url is not None:
            return configured_url
        if source.base_url and source.base_url.strip():
            return source.base_url.strip()
        raise IngestionError("manual sources require base_url or configuration.careers_url")

    def parse_payload(self, payload: object, source: CompanySource) -> AdapterFetchResult:
        if isinstance(payload, dict):
            jobs = payload.get("jobs")
            if not isinstance(jobs, list):
                raise IngestionError("manual payload must include a jobs list")
            normalized_jobs = [_normalize_inline_job(job) for job in jobs if isinstance(job, dict)]
            return AdapterFetchResult(jobs=tuple(normalized_jobs))

        if not isinstance(payload, str):
            raise IngestionError("manual payload must be an object or html text")
        return AdapterFetchResult(
            jobs=extract_normalized_jobs_from_html(payload, fallback_url=self.build_request_url(source))
        )

    def fetch(self, source: CompanySource) -> AdapterFetchResult:
        configuration = source.configuration or {}
        if isinstance(configuration, dict):
            inline_jobs = configuration.get("jobs")
            if isinstance(inline_jobs, list):
                return self.parse_payload({"jobs": inline_jobs}, source)

        try:
            request_url = self.build_request_url(source)
        except IngestionError:
            return AdapterFetchResult(jobs=())

        try:
            html = fetch_text(request_url, timeout_seconds=self.request_timeout_seconds)
        except IngestionError:
            return AdapterFetchResult(jobs=())
        return self.parse_payload(html, source)

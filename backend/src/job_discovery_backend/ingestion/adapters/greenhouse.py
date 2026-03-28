from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any
from urllib.parse import urlparse

from job_discovery_backend.db.models import CompanySource
from job_discovery_backend.ingestion.adapters.base import BaseJobSourceAdapter
from job_discovery_backend.ingestion.models import AdapterFetchResult, IngestionError, NormalizedJob, infer_work_mode

_EXTERNAL_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _external_key(source: CompanySource) -> str:
    candidate: str | None = None
    if source.external_key and source.external_key.strip():
        candidate = source.external_key.strip()
    elif source.base_url:
        path = urlparse(source.base_url).path.strip("/")
        if path:
            candidate = path.split("/")[-1]

    if candidate is None:
        raise IngestionError("greenhouse sources require external_key or base_url")
    if not _EXTERNAL_KEY_PATTERN.fullmatch(candidate):
        raise IngestionError("greenhouse external_key contains unsupported characters")
    return candidate


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return datetime.fromisoformat(normalized.replace("Z", "+00:00")).astimezone(UTC)


def _metadata_value(job: dict[str, Any], target_names: set[str]) -> str | None:
    metadata = job.get("metadata")
    if not isinstance(metadata, list):
        return None
    for entry in metadata:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or entry.get("title") or "").strip().lower()
        if name in target_names:
            value = entry.get("value")
            if value is None:
                return None
            return str(value)
    return None


class GreenhouseAdapter(BaseJobSourceAdapter):
    def __init__(self, *, timeout_seconds: int = 30) -> None:
        super().__init__(source_type="greenhouse", request_timeout_seconds=timeout_seconds)

    def build_request_url(self, source: CompanySource) -> str:
        return f"https://boards-api.greenhouse.io/v1/boards/{_external_key(source)}/jobs?content=true"

    def parse_payload(self, payload: object, source: CompanySource) -> AdapterFetchResult:
        if not isinstance(payload, dict):
            raise IngestionError("greenhouse payload must be an object")
        jobs = payload.get("jobs")
        if not isinstance(jobs, list):
            raise IngestionError("greenhouse payload must include a jobs list")

        normalized_jobs: list[NormalizedJob] = []
        for job in jobs:
            if not isinstance(job, dict):
                raise IngestionError("greenhouse jobs must be objects")
            location = job.get("location")
            location_text = None
            if isinstance(location, dict):
                location_value = location.get("name")
                location_text = None if location_value is None else str(location_value)

            employment_type = _metadata_value(job, {"employment type", "commitment"})
            normalized_jobs.append(
                NormalizedJob(
                    source_job_key=str(job.get("id") or ""),
                    title=str(job.get("title") or ""),
                    location_text=location_text,
                    work_mode=infer_work_mode(location_text, employment_type),
                    employment_type=employment_type,
                    posted_at=_parse_datetime(
                        str(job.get("first_published") or job.get("updated_at") or "").strip() or None
                    ),
                    source_updated_at=_parse_datetime(str(job.get("updated_at") or "").strip() or None),
                    apply_url=None if job.get("absolute_url") is None else str(job.get("absolute_url")),
                    description_text=None if job.get("content") is None else str(job.get("content")),
                    raw_payload=job,
                )
            )

        return AdapterFetchResult(jobs=tuple(normalized_jobs))

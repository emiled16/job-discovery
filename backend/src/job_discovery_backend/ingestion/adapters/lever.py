from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from job_discovery_backend.db.models import CompanySource
from job_discovery_backend.ingestion.adapters.base import BaseJobSourceAdapter
from job_discovery_backend.ingestion.models import AdapterFetchResult, IngestionError, NormalizedJob, infer_work_mode


def _external_key(source: CompanySource) -> str:
    if source.external_key and source.external_key.strip():
        return source.external_key.strip()
    if source.base_url:
        path = urlparse(source.base_url).path.strip("/")
        if path:
            return path.split("/")[-1]
    raise IngestionError("lever sources require external_key or base_url")


def _parse_timestamp(value: int | float | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(float(value) / 1000, tz=UTC)


class LeverAdapter(BaseJobSourceAdapter):
    def __init__(self) -> None:
        super().__init__(source_type="lever")

    def build_request_url(self, source: CompanySource) -> str:
        return f"https://api.lever.co/v0/postings/{_external_key(source)}?mode=json"

    def parse_payload(self, payload: object, source: CompanySource) -> AdapterFetchResult:
        if not isinstance(payload, list):
            raise IngestionError("lever payload must be a list")

        normalized_jobs: list[NormalizedJob] = []
        for job in payload:
            if not isinstance(job, dict):
                raise IngestionError("lever jobs must be objects")
            categories = job.get("categories")
            if categories is not None and not isinstance(categories, dict):
                raise IngestionError("lever categories must be an object")
            categories = categories or {}
            location_text = None if categories.get("location") is None else str(categories.get("location"))
            employment_type = None if categories.get("commitment") is None else str(categories.get("commitment"))
            description_text = job.get("descriptionPlain") or job.get("description")
            normalized_jobs.append(
                NormalizedJob(
                    source_job_key=str(job.get("id") or ""),
                    title=str(job.get("text") or ""),
                    location_text=location_text,
                    work_mode=infer_work_mode(location_text, employment_type),
                    employment_type=employment_type,
                    posted_at=_parse_timestamp(job.get("createdAt")),
                    source_updated_at=_parse_timestamp(job.get("updatedAt")),
                    apply_url=None if job.get("hostedUrl") is None else str(job.get("hostedUrl")),
                    description_text=None if description_text is None else str(description_text),
                    raw_payload=job,
                )
            )

        return AdapterFetchResult(jobs=tuple(normalized_jobs))

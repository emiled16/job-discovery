from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any
from urllib.parse import urlparse

from job_discovery_backend.db.models import CompanySource
from job_discovery_backend.ingestion.adapters.base import BaseJobSourceAdapter, fetch_text, post_json
from job_discovery_backend.ingestion.html_job_postings import extract_normalized_jobs_from_html
from job_discovery_backend.ingestion.models import AdapterFetchResult, IngestionError, NormalizedJob, infer_work_mode

_TENANT_PATTERN = re.compile(r'tenant:\s*"([^"]+)"')
_SITE_ID_PATTERN = re.compile(r'siteId:\s*"([^"]+)"')
_REQUEST_LOCALE_PATTERN = re.compile(r'requestLocale:\s*"([^"]+)"')


def _site_url(source: CompanySource) -> str:
    configuration = source.configuration or {}
    if isinstance(configuration, dict):
        configured_url = configuration.get("careers_url")
        if isinstance(configured_url, str) and configured_url.strip():
            return configured_url.strip()
    if source.base_url and source.base_url.strip():
        return source.base_url.strip()
    raise IngestionError("workday sources require base_url or configuration.careers_url")


@dataclass(frozen=True)
class WorkdaySiteMetadata:
    origin: str
    tenant: str
    site_id: str
    request_locale: str

    @property
    def jobs_api_url(self) -> str:
        return f"{self.origin}/wday/cxs/{self.tenant}/{self.site_id}/jobs"

    @property
    def public_base_url(self) -> str:
        return f"{self.origin}/{self.request_locale}/{self.site_id}"


def _parse_site_metadata(html: str, site_url: str) -> WorkdaySiteMetadata:
    tenant_match = _TENANT_PATTERN.search(html)
    site_match = _SITE_ID_PATTERN.search(html)
    locale_match = _REQUEST_LOCALE_PATTERN.search(html)
    if tenant_match is None or site_match is None or locale_match is None:
        raise IngestionError("workday page is missing bootstrap metadata")
    parsed = urlparse(site_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return WorkdaySiteMetadata(
        origin=origin,
        tenant=tenant_match.group(1),
        site_id=site_match.group(1),
        request_locale=locale_match.group(1),
    )


def _listing_apply_url(public_base_url: str, external_path: str | None) -> str | None:
    if not external_path:
        return None
    return f"{public_base_url}/{external_path.lstrip('/')}"


def _normalize_listing_job(posting: dict[str, Any], *, public_base_url: str) -> NormalizedJob:
    bullet_fields = posting.get("bulletFields")
    source_job_key = None
    if isinstance(bullet_fields, list):
        for value in bullet_fields:
            if isinstance(value, str) and value.strip():
                source_job_key = value.strip()
                break
    apply_url = _listing_apply_url(public_base_url, posting.get("externalPath"))
    location_text = str(posting.get("locationsText") or "").strip() or None
    employment_type = str(posting.get("timeType") or "").strip() or None
    return NormalizedJob(
        source_job_key=source_job_key or str(posting.get("externalPath") or posting.get("title") or ""),
        title=str(posting.get("title") or ""),
        location_text=location_text,
        work_mode=infer_work_mode(location_text, employment_type),
        employment_type=employment_type,
        posted_at=None,
        source_updated_at=None,
        apply_url=apply_url,
        description_text=None,
        raw_payload=posting,
    )


class WorkdayAdapter(BaseJobSourceAdapter):
    def __init__(self, *, timeout_seconds: int = 30) -> None:
        super().__init__(source_type="workday", request_timeout_seconds=timeout_seconds)

    def build_request_url(self, source: CompanySource) -> str:
        return _site_url(source)

    def parse_payload(self, payload: object, source: CompanySource) -> AdapterFetchResult:
        if not isinstance(payload, dict):
            raise IngestionError("workday payload must be an object")
        postings = payload.get("jobPostings")
        if not isinstance(postings, list):
            raise IngestionError("workday payload must include a jobPostings list")
        public_base_url = _site_url(source).rstrip("/")
        return AdapterFetchResult(
            jobs=tuple(
                _normalize_listing_job(posting, public_base_url=public_base_url)
                for posting in postings
                if isinstance(posting, dict)
            )
        )

    def fetch(self, source: CompanySource) -> AdapterFetchResult:
        site_url = self.build_request_url(source)
        site_html = fetch_text(site_url, timeout_seconds=self.request_timeout_seconds)
        metadata = _parse_site_metadata(site_html, site_url)
        payload = post_json(metadata.jobs_api_url, timeout_seconds=self.request_timeout_seconds, payload={})
        if not isinstance(payload, dict):
            raise IngestionError("workday payload must be an object")
        postings = payload.get("jobPostings")
        if not isinstance(postings, list):
            raise IngestionError("workday payload must include a jobPostings list")

        jobs: list[NormalizedJob] = []
        for posting in postings:
            if not isinstance(posting, dict):
                raise IngestionError("workday job postings must be objects")
            listing_job = _normalize_listing_job(posting, public_base_url=metadata.public_base_url)
            detail_url = listing_job.apply_url
            if detail_url is None:
                jobs.append(listing_job)
                continue
            try:
                detail_html = fetch_text(detail_url, timeout_seconds=self.request_timeout_seconds)
                detail_jobs = extract_normalized_jobs_from_html(detail_html, fallback_url=detail_url)
            except IngestionError:
                detail_jobs = ()
            jobs.append(detail_jobs[0] if detail_jobs else listing_job)
        return AdapterFetchResult(jobs=tuple(jobs))

from __future__ import annotations

from html import unescape
import re
from urllib.parse import unquote, urljoin, urlparse

from job_discovery_backend.db.models import CompanySource
from job_discovery_backend.ingestion.adapters.base import BaseJobSourceAdapter, fetch_text
from job_discovery_backend.ingestion.html_job_postings import extract_normalized_jobs_from_html
from job_discovery_backend.ingestion.models import AdapterFetchResult, IngestionError, NormalizedJob

_SUBDOMAIN_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*$")
_JOB_LINK_PATTERN = re.compile(
    r'<a[^>]+href=["\'](?P<href>[^"\']+/apply/(?P<job_id>[A-Za-z0-9]+)/[^"\']+)["\'][^>]*>(?P<title>.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_TAG_PATTERN = re.compile(r"<[^>]+>")


def _clean_html_text(value: str) -> str:
    no_tags = _TAG_PATTERN.sub(" ", value)
    return re.sub(r"\s+", " ", unescape(no_tags)).strip()


def _source_subdomain(source: CompanySource) -> str:
    candidate: str | None = None
    if source.external_key and source.external_key.strip():
        candidate = source.external_key.strip()
    elif source.base_url and source.base_url.strip():
        hostname = urlparse(source.base_url.strip()).hostname
        if hostname:
            candidate = hostname.split(".")[0]
    if candidate is None:
        raise IngestionError("applytojob sources require external_key or base_url")
    normalized = candidate.strip().lower()
    if normalized.endswith(".applytojob.com"):
        normalized = normalized.split(".")[0]
    if not _SUBDOMAIN_PATTERN.fullmatch(normalized):
        raise IngestionError("applytojob external_key contains unsupported characters")
    return normalized


def _listing_url(source: CompanySource) -> str:
    configuration = source.configuration or {}
    if isinstance(configuration, dict):
        configured_url = configuration.get("careers_url")
        if isinstance(configured_url, str) and configured_url.strip():
            return configured_url.strip()
    if source.base_url and source.base_url.strip():
        return source.base_url.strip()
    return f"https://{_source_subdomain(source)}.applytojob.com/apply"


def _job_key_from_url(apply_url: str) -> str:
    path_parts = [segment for segment in urlparse(apply_url).path.split("/") if segment]
    if len(path_parts) >= 2 and path_parts[0].lower() == "apply":
        return path_parts[1]
    return apply_url


def _title_from_url(apply_url: str) -> str:
    slug = urlparse(apply_url).path.rstrip("/").split("/")[-1]
    normalized = unquote(slug).replace("-", " ").replace("_", " ").strip()
    return normalized or "Job Opening"


def _listing_job(*, apply_url: str, title: str) -> NormalizedJob:
    return NormalizedJob(
        source_job_key=_job_key_from_url(apply_url),
        title=title,
        location_text=None,
        work_mode="unknown",
        employment_type=None,
        posted_at=None,
        source_updated_at=None,
        apply_url=apply_url,
        description_text=None,
        raw_payload={"apply_url": apply_url, "title": title},
    )


def _extract_listing_entries(html: str, *, listing_url: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    seen_urls: set[str] = set()
    for match in _JOB_LINK_PATTERN.finditer(html):
        apply_url = urljoin(listing_url, match.group("href").strip())
        if apply_url in seen_urls:
            continue
        seen_urls.add(apply_url)
        title = _clean_html_text(match.group("title")) or _title_from_url(apply_url)
        entries.append((apply_url, title))
    return entries


class ApplyToJobAdapter(BaseJobSourceAdapter):
    def __init__(self, *, timeout_seconds: int = 30) -> None:
        super().__init__(source_type="applytojob", request_timeout_seconds=timeout_seconds)

    def build_request_url(self, source: CompanySource) -> str:
        return _listing_url(source)

    def parse_payload(self, payload: object, source: CompanySource) -> AdapterFetchResult:
        if not isinstance(payload, str):
            raise IngestionError("applytojob payload must be html text")
        listing_url = self.build_request_url(source)
        entries = _extract_listing_entries(payload, listing_url=listing_url)
        return AdapterFetchResult(
            jobs=tuple(_listing_job(apply_url=apply_url, title=title) for apply_url, title in entries)
        )

    def fetch(self, source: CompanySource) -> AdapterFetchResult:
        listing_url = self.build_request_url(source)
        listing_html = fetch_text(listing_url, timeout_seconds=self.request_timeout_seconds)
        entries = _extract_listing_entries(listing_html, listing_url=listing_url)

        jobs: list[NormalizedJob] = []
        for apply_url, title in entries:
            try:
                detail_html = fetch_text(apply_url, timeout_seconds=self.request_timeout_seconds)
                detail_jobs = extract_normalized_jobs_from_html(detail_html, fallback_url=apply_url)
            except IngestionError:
                detail_jobs = ()
            if detail_jobs:
                jobs.append(detail_jobs[0])
            else:
                jobs.append(_listing_job(apply_url=apply_url, title=title))
        return AdapterFetchResult(jobs=tuple(jobs))

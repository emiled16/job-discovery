from __future__ import annotations

from dataclasses import dataclass
import httpx
from typing import Protocol, runtime_checkable

from job_discovery_backend.db.models import CompanySource
from job_discovery_backend.ingestion.models import AdapterFetchResult, IngestionError
from job_discovery_backend.urls import validate_public_http_url


@runtime_checkable
class JobSourceAdapter(Protocol):
    source_type: str

    def build_request_url(self, source: CompanySource) -> str: ...

    def parse_payload(self, payload: object, source: CompanySource) -> AdapterFetchResult: ...

    request_timeout_seconds: int

    def fetch(self, source: CompanySource) -> AdapterFetchResult: ...


def fetch_json(url: str, *, timeout_seconds: int) -> object:
    response = _fetch_url(url, timeout_seconds=timeout_seconds, accept_header="application/json")
    try:
        return response.json()
    except ValueError as exc:
        raise IngestionError("response payload was not valid JSON") from exc


def post_json(url: str, *, timeout_seconds: int, payload: object | None = None) -> object:
    try:
        safe_url = validate_public_http_url(url, field_name="request_url")
    except ValueError as exc:
        raise IngestionError(str(exc)) from exc
    try:
        with httpx.Client(
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        ) as client:
            response = client.post(safe_url, json=payload)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise IngestionError(f"request_url timed out after {timeout_seconds} seconds") from exc
    except httpx.HTTPStatusError as exc:
        raise IngestionError(f"request_url failed with status {exc.response.status_code}") from exc
    except httpx.HTTPError as exc:
        raise IngestionError(f"request_url failed: {exc}") from exc

    try:
        return response.json()
    except ValueError as exc:
        raise IngestionError("response payload was not valid JSON") from exc


def fetch_text(url: str, *, timeout_seconds: int) -> str:
    return _fetch_url(url, timeout_seconds=timeout_seconds, accept_header="text/html,application/xhtml+xml").text


def _fetch_url(url: str, *, timeout_seconds: int, accept_header: str) -> httpx.Response:
    try:
        safe_url = validate_public_http_url(url, field_name="request_url")
    except ValueError as exc:
        raise IngestionError(str(exc)) from exc
    try:
        with httpx.Client(
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
            headers={"Accept": accept_header},
        ) as client:
            response = client.get(safe_url)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise IngestionError(f"request_url timed out after {timeout_seconds} seconds") from exc
    except httpx.HTTPStatusError as exc:
        raise IngestionError(f"request_url failed with status {exc.response.status_code}") from exc
    except httpx.HTTPError as exc:
        raise IngestionError(f"request_url failed: {exc}") from exc

    return response


def ensure_adapter_contract(adapter: object) -> JobSourceAdapter:
    required_methods = ("build_request_url", "parse_payload", "fetch")
    if not isinstance(getattr(adapter, "source_type", None), str) or not adapter.source_type.strip():
        raise IngestionError("adapter source_type must be a non-empty string")
    timeout_seconds = getattr(adapter, "request_timeout_seconds", None)
    if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
        raise IngestionError("adapter request_timeout_seconds must be a positive integer")
    for method_name in required_methods:
        if not callable(getattr(adapter, method_name, None)):
            raise IngestionError(f"adapter must implement {method_name}()")
    return adapter  # type: ignore[return-value]


@dataclass(frozen=True)
class BaseJobSourceAdapter:
    source_type: str
    request_timeout_seconds: int = 30

    def fetch(self, source: CompanySource) -> AdapterFetchResult:
        payload = fetch_json(
            self.build_request_url(source),
            timeout_seconds=self.request_timeout_seconds,
        )
        return self.parse_payload(payload, source)

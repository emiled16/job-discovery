from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from urllib.request import urlopen

from job_discovery_backend.db.models import CompanySource
from job_discovery_backend.ingestion.models import AdapterFetchResult, IngestionError


@runtime_checkable
class JobSourceAdapter(Protocol):
    source_type: str

    def build_request_url(self, source: CompanySource) -> str: ...

    def parse_payload(self, payload: object, source: CompanySource) -> AdapterFetchResult: ...

    def fetch(self, source: CompanySource) -> AdapterFetchResult: ...


def fetch_json(url: str) -> object:
    with urlopen(url, timeout=30) as response:
        return json.load(response)


def ensure_adapter_contract(adapter: object) -> JobSourceAdapter:
    required_methods = ("build_request_url", "parse_payload", "fetch")
    if not isinstance(getattr(adapter, "source_type", None), str) or not adapter.source_type.strip():
        raise IngestionError("adapter source_type must be a non-empty string")
    for method_name in required_methods:
        if not callable(getattr(adapter, method_name, None)):
            raise IngestionError(f"adapter must implement {method_name}()")
    return adapter  # type: ignore[return-value]


@dataclass(frozen=True)
class BaseJobSourceAdapter:
    source_type: str

    def fetch(self, source: CompanySource) -> AdapterFetchResult:
        payload = fetch_json(self.build_request_url(source))
        return self.parse_payload(payload, source)

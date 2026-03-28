"""Ingestion contracts and adapter registry."""

from job_discovery_backend.ingestion.models import AdapterFetchResult, IngestionError, NormalizedJob
from job_discovery_backend.ingestion.registry import AdapterSelectionError, get_adapter_for_source

__all__ = [
    "AdapterFetchResult",
    "AdapterSelectionError",
    "IngestionError",
    "NormalizedJob",
    "get_adapter_for_source",
]

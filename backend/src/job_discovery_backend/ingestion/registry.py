from __future__ import annotations

from job_discovery_backend.db.models import CompanySource
from job_discovery_backend.ingestion.adapters import GreenhouseAdapter, JobSourceAdapter, LeverAdapter, ensure_adapter_contract
from job_discovery_backend.ingestion.models import IngestionError


class AdapterSelectionError(IngestionError):
    """Raised when the platform cannot route a source to a supported adapter."""


_ADAPTERS: dict[str, JobSourceAdapter] = {
    "greenhouse": GreenhouseAdapter(),
    "lever": LeverAdapter(),
}


def get_adapter_for_source(source: CompanySource) -> JobSourceAdapter:
    adapter = _ADAPTERS.get(source.source_type)
    if adapter is None:
        raise AdapterSelectionError(f"no adapter is registered for source_type={source.source_type}")
    return ensure_adapter_contract(adapter)

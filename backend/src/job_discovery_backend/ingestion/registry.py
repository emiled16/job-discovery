from __future__ import annotations

from collections.abc import Callable

from job_discovery_backend.db.models import CompanySource
from job_discovery_backend.ingestion.adapters import (
    ApplyToJobAdapter,
    AshbyAdapter,
    GreenhouseAdapter,
    JobSourceAdapter,
    LeverAdapter,
    ManualAdapter,
    SmartRecruitersAdapter,
    WorkdayAdapter,
    ensure_adapter_contract,
)
from job_discovery_backend.ingestion.models import IngestionError


class AdapterSelectionError(IngestionError):
    """Raised when the platform cannot route a source to a supported adapter."""


_ADAPTER_FACTORIES: dict[str, Callable[[int], JobSourceAdapter]] = {
    "applytojob": lambda timeout_seconds: ApplyToJobAdapter(timeout_seconds=timeout_seconds),
    "ashby": lambda timeout_seconds: AshbyAdapter(timeout_seconds=timeout_seconds),
    "greenhouse": lambda timeout_seconds: GreenhouseAdapter(timeout_seconds=timeout_seconds),
    "lever": lambda timeout_seconds: LeverAdapter(timeout_seconds=timeout_seconds),
    "smartrecruiters": lambda timeout_seconds: SmartRecruitersAdapter(timeout_seconds=timeout_seconds),
    "workday": lambda timeout_seconds: WorkdayAdapter(timeout_seconds=timeout_seconds),
}


def get_adapter_for_source(
    source: CompanySource,
    *,
    timeout_seconds: int = 30,
) -> JobSourceAdapter:
    if source.source_type == "manual":
        return ensure_adapter_contract(ManualAdapter(timeout_seconds=timeout_seconds))
    factory = _ADAPTER_FACTORIES.get(source.source_type)
    if factory is None:
        raise AdapterSelectionError(f"no adapter is registered for source_type={source.source_type}")
    adapter = factory(timeout_seconds)
    return ensure_adapter_contract(adapter)

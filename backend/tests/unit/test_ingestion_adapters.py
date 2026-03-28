from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from job_discovery_backend.db.models import CompanySource  # noqa: E402
from job_discovery_backend.ingestion.adapters import GreenhouseAdapter, LeverAdapter, ensure_adapter_contract  # noqa: E402
from job_discovery_backend.ingestion.models import IngestionError, NormalizedJob  # noqa: E402
from job_discovery_backend.ingestion.registry import AdapterSelectionError, get_adapter_for_source  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "adapters"


def _fixture(name: str) -> object:
    return json.loads((FIXTURES / name).read_text())


def _source(*, source_type: str, external_key: str = "example") -> CompanySource:
    return CompanySource(
        id="33333333-3333-3333-3333-333333333331",
        company_id="22222222-2222-2222-2222-222222222221",
        source_type=source_type,
        external_key=external_key,
        base_url=f"https://boards.example.com/{external_key}",
        configuration={},
        is_enabled=True,
    )


def test_normalized_job_enforces_schema_and_normalizes_values() -> None:
    job = NormalizedJob(
        source_job_key="  external-1 ",
        title=" Platform Engineer ",
        location_text=" Remote - Canada ",
        work_mode="remote",
        employment_type=" Full-time ",
        posted_at=datetime(2026, 3, 20, 12, 0, tzinfo=UTC),
        source_updated_at=datetime(2026, 3, 21, 12, 0, tzinfo=UTC),
        apply_url="https://example.com/jobs/external-1",
        description_text=" Build internal tooling. ",
        raw_payload={"id": "external-1"},
    )

    assert job.source_job_key == "external-1"
    assert job.title == "Platform Engineer"
    assert job.description_text == "Build internal tooling."
    assert job.normalized_payload()["posted_at"] == "2026-03-20T12:00:00+00:00"


def test_adapter_contract_validation_accepts_supported_adapters() -> None:
    assert ensure_adapter_contract(GreenhouseAdapter()).source_type == "greenhouse"
    assert ensure_adapter_contract(LeverAdapter()).source_type == "lever"


def test_greenhouse_adapter_parses_success_fixture() -> None:
    result = GreenhouseAdapter().parse_payload(_fixture("greenhouse_success.json"), _source(source_type="greenhouse"))

    assert len(result.jobs) == 2
    assert result.jobs[0].source_job_key == "101"
    assert result.jobs[0].work_mode == "remote"
    assert result.jobs[1].work_mode == "hybrid"


@pytest.mark.parametrize(
    "fixture_name,error_message",
    [
        ("greenhouse_missing_fields.json", "title is required"),
        ("greenhouse_malformed.json", "greenhouse payload must include a jobs list"),
    ],
)
def test_greenhouse_adapter_rejects_invalid_payloads(fixture_name: str, error_message: str) -> None:
    with pytest.raises(IngestionError, match=error_message):
        GreenhouseAdapter().parse_payload(_fixture(fixture_name), _source(source_type="greenhouse"))


def test_lever_adapter_parses_success_fixture() -> None:
    result = LeverAdapter().parse_payload(_fixture("lever_success.json"), _source(source_type="lever"))

    assert len(result.jobs) == 2
    assert result.jobs[0].source_job_key == "job-301"
    assert result.jobs[0].work_mode == "remote"
    assert result.jobs[1].employment_type == "Contract"
    assert result.jobs[1].work_mode == "hybrid"


@pytest.mark.parametrize(
    "fixture_name,error_message",
    [
        ("lever_missing_fields.json", "title is required"),
        ("lever_malformed.json", "lever payload must be a list"),
    ],
)
def test_lever_adapter_rejects_invalid_payloads(fixture_name: str, error_message: str) -> None:
    with pytest.raises(IngestionError, match=error_message):
        LeverAdapter().parse_payload(_fixture(fixture_name), _source(source_type="lever"))


def test_adapter_selection_routes_supported_sources_and_rejects_manual() -> None:
    assert get_adapter_for_source(_source(source_type="greenhouse")).source_type == "greenhouse"
    assert get_adapter_for_source(_source(source_type="lever")).source_type == "lever"

    with pytest.raises(AdapterSelectionError, match="no adapter is registered for source_type=manual"):
        get_adapter_for_source(_source(source_type="manual"))

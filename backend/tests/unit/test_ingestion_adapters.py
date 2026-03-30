from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from job_discovery_backend.db.models import CompanySource  # noqa: E402
from job_discovery_backend.ingestion.adapters import (  # noqa: E402
    ApplyToJobAdapter,
    AshbyAdapter,
    GreenhouseAdapter,
    LeverAdapter,
    ManualAdapter,
    SmartRecruitersAdapter,
    WorkdayAdapter,
    ensure_adapter_contract,
)
from job_discovery_backend.ingestion.models import IngestionError, NormalizedJob  # noqa: E402
from job_discovery_backend.ingestion.registry import get_adapter_for_source  # noqa: E402

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


def test_normalized_job_converts_html_descriptions_to_plain_text() -> None:
    job = NormalizedJob(
        source_job_key="external-2",
        title="Platform Engineer",
        location_text="Remote",
        work_mode="remote",
        employment_type="Full-time",
        posted_at=datetime(2026, 3, 20, 12, 0, tzinfo=UTC),
        source_updated_at=datetime(2026, 3, 21, 12, 0, tzinfo=UTC),
        apply_url="https://example.com/jobs/external-2",
        description_text=(
            "&lt;h2&gt;&lt;strong&gt;Who we are&lt;/strong&gt;&lt;/h2&gt;"
            " &lt;p&gt;Stripe builds tools.&lt;/p&gt;&lt;ul&gt;&lt;li&gt;Remote first&lt;/li&gt;&lt;/ul&gt;"
        ),
        raw_payload={"id": "external-2"},
    )

    assert job.description_text == "Who we are\nStripe builds tools.\n- Remote first"


def test_normalized_job_converts_double_escaped_html_descriptions_to_plain_text() -> None:
    job = NormalizedJob(
        source_job_key="external-3",
        title="Platform Engineer",
        location_text="Remote",
        work_mode="remote",
        employment_type="Full-time",
        posted_at=datetime(2026, 3, 20, 12, 0, tzinfo=UTC),
        source_updated_at=datetime(2026, 3, 21, 12, 0, tzinfo=UTC),
        apply_url="https://example.com/jobs/external-3",
        description_text=(
            "&amp;lt;h2&amp;gt;Who we are&amp;lt;/h2&amp;gt;"
            " &amp;lt;p&amp;gt;Stripe builds tools.&amp;lt;/p&amp;gt;"
            "&amp;lt;ul&amp;gt;&amp;lt;li&amp;gt;Remote first&amp;lt;/li&amp;gt;&amp;lt;/ul&amp;gt;"
        ),
        raw_payload={"id": "external-3"},
    )

    assert job.description_text == "Who we are\nStripe builds tools.\n- Remote first"


def test_adapter_contract_validation_accepts_supported_adapters() -> None:
    assert ensure_adapter_contract(ApplyToJobAdapter()).source_type == "applytojob"
    assert ensure_adapter_contract(AshbyAdapter()).source_type == "ashby"
    assert ensure_adapter_contract(GreenhouseAdapter()).source_type == "greenhouse"
    assert ensure_adapter_contract(LeverAdapter()).source_type == "lever"
    assert ensure_adapter_contract(ManualAdapter()).source_type == "manual"
    assert ensure_adapter_contract(SmartRecruitersAdapter()).source_type == "smartrecruiters"
    assert ensure_adapter_contract(WorkdayAdapter()).source_type == "workday"


def test_ashby_adapter_parses_success_fixture() -> None:
    result = AshbyAdapter().parse_payload(_fixture("ashby_success.json"), _source(source_type="ashby"))

    assert len(result.jobs) == 2
    assert result.jobs[0].source_job_key == "job-ashby-101"
    assert result.jobs[0].work_mode == "remote"
    assert result.jobs[0].employment_type == "FullTime"
    assert result.jobs[1].work_mode == "hybrid"
    assert result.jobs[1].description_text == "Design experiences."


@pytest.mark.parametrize(
    "fixture_name,error_message",
    [
        ("ashby_missing_fields.json", "title is required"),
        ("ashby_malformed.json", "ashby payload must include a jobs list"),
    ],
)
def test_ashby_adapter_rejects_invalid_payloads(fixture_name: str, error_message: str) -> None:
    with pytest.raises(IngestionError, match=error_message):
        AshbyAdapter().parse_payload(_fixture(fixture_name), _source(source_type="ashby"))


def test_applytojob_adapter_parses_listing_html() -> None:
    source = _source(source_type="applytojob", external_key="miovision")
    source.base_url = "https://miovision.applytojob.com/apply"
    result = ApplyToJobAdapter().parse_payload(
        """
        <html>
          <body>
            <a href="https://miovision.applytojob.com/apply/WUOV2qLOGu/Director-Developer-Operations-Experience">
              Director, Developer Operations &amp; Experience
            </a>
          </body>
        </html>
        """,
        source,
    )

    assert len(result.jobs) == 1
    assert result.jobs[0].source_job_key == "WUOV2qLOGu"
    assert result.jobs[0].title == "Director, Developer Operations & Experience"
    assert result.jobs[0].apply_url == (
        "https://miovision.applytojob.com/apply/WUOV2qLOGu/Director-Developer-Operations-Experience"
    )


def test_applytojob_adapter_fetches_detail_pages() -> None:
    source = _source(source_type="applytojob", external_key="miovision")
    source.base_url = "https://miovision.applytojob.com/apply"
    listing_html = """
    <html>
      <body>
        <a href="https://miovision.applytojob.com/apply/WUOV2qLOGu/Director-Developer-Operations-Experience">
          Director, Developer Operations &amp; Experience
        </a>
      </body>
    </html>
    """
    detail_html = """
    <html>
      <head>
        <script type="application/ld+json">
          {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": "Director, Developer Operations & Experience",
            "description": "<p>Build platform systems.</p>",
            "employmentType": "FULL_TIME",
            "url": "https://miovision.applytojob.com/apply/WUOV2qLOGu/Director-Developer-Operations-Experience",
            "identifier": {"name": "Miovision", "value": "WUOV2qLOGu"},
            "jobLocation": {
              "@type": "Place",
              "address": {
                "@type": "PostalAddress",
                "addressLocality": "Kitchener",
                "addressRegion": "ON",
                "addressCountry": "CA"
              }
            }
          }
        </script>
      </head>
    </html>
    """

    with patch("job_discovery_backend.ingestion.adapters.applytojob.fetch_text") as fetch_text:
        fetch_text.side_effect = [listing_html, detail_html]
        result = ApplyToJobAdapter().fetch(source)

    assert len(result.jobs) == 1
    assert result.jobs[0].source_job_key == "WUOV2qLOGu"
    assert result.jobs[0].location_text == "Kitchener, ON, CA"
    assert "Build platform systems." in (result.jobs[0].description_text or "")


def test_greenhouse_adapter_parses_success_fixture() -> None:
    result = GreenhouseAdapter().parse_payload(_fixture("greenhouse_success.json"), _source(source_type="greenhouse"))

    assert len(result.jobs) == 2
    assert result.jobs[0].source_job_key == "101"
    assert result.jobs[0].work_mode == "remote"
    assert "<" not in (result.jobs[0].description_text or "")
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


def test_smartrecruiters_adapter_parses_success_fixture() -> None:
    result = SmartRecruitersAdapter().parse_payload(
        _fixture("smartrecruiters_success.json"),
        _source(source_type="smartrecruiters"),
    )

    assert len(result.jobs) == 2
    assert result.jobs[0].source_job_key == "6000000000962928"
    assert result.jobs[0].work_mode == "hybrid"
    assert result.jobs[1].work_mode == "remote"


def test_smartrecruiters_adapter_rejects_invalid_payloads() -> None:
    with pytest.raises(IngestionError, match="smartrecruiters payload must include a content list"):
        SmartRecruitersAdapter().parse_payload(
            _fixture("smartrecruiters_malformed.json"),
            _source(source_type="smartrecruiters"),
        )


def test_smartrecruiters_adapter_fetches_detail_records() -> None:
    source = _source(source_type="smartrecruiters", external_key="canva")
    list_payload = _fixture("smartrecruiters_success.json")
    detail_payload = {
        "applyUrl": "https://jobs.smartrecruiters.com/Canva/6000000000962928-senior-technical-program-manager-platform",
        "jobAd": {
            "sections": {
                "jobDescription": {
                    "title": "Job Description",
                    "text": "<p>Lead complex delivery work.</p>",
                }
            }
        },
    }

    with patch("job_discovery_backend.ingestion.adapters.smartrecruiters.fetch_json") as fetch_json:
        fetch_json.side_effect = [
            list_payload,
            detail_payload,
            {
                "applyUrl": "https://jobs.smartrecruiters.com/Company/744000116559687-senior-software-engineer",
                "jobAd": {"sections": {}},
            },
        ]
        result = SmartRecruitersAdapter().fetch(source)

    assert len(result.jobs) == 2
    assert result.jobs[0].apply_url == detail_payload["applyUrl"]
    assert "Lead complex delivery work." in (result.jobs[0].description_text or "")


def test_workday_adapter_parses_listing_payload() -> None:
    source = _source(source_type="workday")
    source.base_url = "https://example.wd5.myworkdayjobs.com/en-US/Careers"
    result = WorkdayAdapter().parse_payload(
        {
            "total": 1,
            "jobPostings": [
                {
                    "title": "Senior Platform Engineer",
                    "externalPath": "/job/Toronto-ON/Senior-Platform-Engineer_R-1001",
                    "locationsText": "Toronto, ON, Canada",
                    "bulletFields": ["R-1001"],
                }
            ],
        },
        source,
    )

    assert len(result.jobs) == 1
    assert result.jobs[0].source_job_key == "R-1001"
    assert result.jobs[0].apply_url == "https://example.wd5.myworkdayjobs.com/en-US/Careers/job/Toronto-ON/Senior-Platform-Engineer_R-1001"


def test_workday_adapter_fetches_listing_and_detail_pages() -> None:
    source = _source(source_type="workday")
    source.base_url = "https://example.wd5.myworkdayjobs.com/en-US/Careers"
    site_html = """
    <html>
      <script>
        window.workday = window.workday || {
          tenant: "example",
          siteId: "Careers",
          requestLocale: "en-US"
        };
      </script>
    </html>
    """
    detail_html = """
    <html>
      <head>
        <script type="application/ld+json">
          {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": "Senior Platform Engineer",
            "description": "<p>Build platform systems.</p>",
            "datePosted": "2026-03-20T12:00:00+00:00",
            "employmentType": "FULL_TIME",
            "url": "https://example.wd5.myworkdayjobs.com/en-US/Careers/job/Toronto-ON/Senior-Platform-Engineer_R-1001",
            "identifier": {"name": "Example", "value": "R-1001"},
            "jobLocation": {
              "@type": "Place",
              "address": {
                "@type": "PostalAddress",
                "addressLocality": "Toronto",
                "addressRegion": "ON",
                "addressCountry": "CA"
              }
            }
          }
        </script>
      </head>
    </html>
    """

    with patch("job_discovery_backend.ingestion.adapters.workday.fetch_text") as fetch_text:
        with patch("job_discovery_backend.ingestion.adapters.workday.post_json") as post_json:
            fetch_text.side_effect = [site_html, detail_html]
            post_json.return_value = {
                "total": 1,
                "jobPostings": [
                    {
                        "title": "Senior Platform Engineer",
                        "externalPath": "/job/Toronto-ON/Senior-Platform-Engineer_R-1001",
                        "locationsText": "Toronto, ON, Canada",
                        "bulletFields": ["R-1001"],
                    }
                ],
            }
            result = WorkdayAdapter().fetch(source)

    assert len(result.jobs) == 1
    assert result.jobs[0].source_job_key == "R-1001"
    assert result.jobs[0].location_text == "Toronto, ON, CA"
    assert "Build platform systems." in (result.jobs[0].description_text or "")


def test_manual_adapter_parses_inline_jobs_from_configuration() -> None:
    source = _source(source_type="manual")
    source.configuration = {
        "jobs": [
            {
                "id": "manual-1",
                "title": "Applied ML Engineer",
                "location_text": "Montreal, QC",
                "work_mode": "hybrid",
                "employment_type": "Full-time",
                "posted_at": "2026-03-20T12:00:00+00:00",
                "apply_url": "https://example.com/jobs/manual-1",
                "description_text": "Operator-managed role.",
            }
        ]
    }

    result = ManualAdapter().fetch(source)

    assert len(result.jobs) == 1
    assert result.jobs[0].source_job_key == "manual-1"
    assert result.jobs[0].work_mode == "hybrid"


def test_manual_adapter_extracts_json_ld_job_postings() -> None:
    source = _source(source_type="manual")
    result = ManualAdapter().parse_payload(
        """
        <html>
          <head>
            <script type="application/ld+json">
              {
                "@context": "https://schema.org",
                "@type": "JobPosting",
                "title": "Backend Engineer",
                "description": "<p>Build systems.</p>",
                "datePosted": "2026-03-20T12:00:00+00:00",
                "employmentType": "FULL_TIME",
                "url": "https://example.com/jobs/backend-engineer",
                "jobLocationType": "TELECOMMUTE",
                "identifier": {"name": "Example", "value": "backend-engineer"},
                "jobLocation": {
                  "@type": "Place",
                  "address": {
                    "@type": "PostalAddress",
                    "addressLocality": "Toronto",
                    "addressRegion": "ON",
                    "addressCountry": "CA"
                  }
                }
              }
            </script>
          </head>
        </html>
        """,
        source,
    )

    assert len(result.jobs) == 1
    assert result.jobs[0].source_job_key == "backend-engineer"
    assert result.jobs[0].work_mode == "remote"
    assert result.jobs[0].location_text == "Toronto, ON, CA"


def test_manual_adapter_returns_empty_result_when_no_url_or_inline_jobs_are_configured() -> None:
    source = CompanySource(
        id="33333333-3333-3333-3333-333333333339",
        company_id="22222222-2222-2222-2222-222222222229",
        source_type="manual",
        external_key="manual-empty",
        base_url=None,
        configuration={},
        is_enabled=True,
    )

    result = ManualAdapter().fetch(source)

    assert result.jobs == ()


def test_adapter_selection_routes_supported_sources() -> None:
    assert get_adapter_for_source(_source(source_type="applytojob")).source_type == "applytojob"
    assert get_adapter_for_source(_source(source_type="ashby")).source_type == "ashby"
    assert get_adapter_for_source(_source(source_type="greenhouse")).source_type == "greenhouse"
    assert get_adapter_for_source(_source(source_type="lever")).source_type == "lever"
    assert get_adapter_for_source(_source(source_type="manual")).source_type == "manual"
    assert get_adapter_for_source(_source(source_type="smartrecruiters")).source_type == "smartrecruiters"
    assert get_adapter_for_source(_source(source_type="workday")).source_type == "workday"

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from support.api import api_client, session_for_database  # noqa: E402
from support.records import seed_application, seed_company, seed_company_source, seed_job, seed_user  # noqa: E402


def _database_url(tmp_path: Path) -> str:
    return f"sqlite+pysqlite:///{tmp_path / 'jobs-api.sqlite3'}"


def test_jobs_list_supports_filter_combinations_sorting_and_paging(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)
    with session_for_database(database_url) as session:
        user = seed_user(session)
        openai = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222221",
            slug="openai",
            name="OpenAI",
        )
        other = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222222",
            slug="acme",
            name="Acme",
        )
        openai_source = seed_company_source(
            session,
            source_id="33333333-3333-3333-3333-333333333331",
            company_id=openai.id,
        )
        other_source = seed_company_source(
            session,
            source_id="33333333-3333-3333-3333-333333333332",
            company_id=other.id,
        )
        target_job = seed_job(
            session,
            job_id="44444444-4444-4444-4444-444444444441",
            company_id=openai.id,
            source_id=openai_source.id,
            title="ML Engineer",
            location_text="Toronto, ON",
            work_mode="remote",
            posted_at=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
            description_text="Build reliable ML systems for production.",
        )
        seed_job(
            session,
            job_id="44444444-4444-4444-4444-444444444442",
            company_id=openai.id,
            source_id=openai_source.id,
            title="ML Engineer II",
            location_text="Toronto, ON",
            work_mode="remote",
            posted_at=datetime(2026, 1, 16, 12, 0, tzinfo=UTC),
            description_text="Later page result.",
        )
        seed_job(
            session,
            job_id="44444444-4444-4444-4444-444444444443",
            company_id=other.id,
            source_id=other_source.id,
            title="Backend Engineer",
            location_text="Montreal, QC",
            work_mode="onsite",
            posted_at=datetime(2026, 1, 10, 12, 0, tzinfo=UTC),
            description_text="Does not match filters.",
        )
        seed_job(
            session,
            job_id="44444444-4444-4444-4444-444444444444",
            company_id=openai.id,
            source_id=openai_source.id,
            title="Closed ML Engineer",
            location_text="Toronto, ON",
            work_mode="remote",
            posted_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            description_text="Closed job should be hidden.",
            status="closed",
        )
        seed_application(
            session,
            application_id="55555555-5555-5555-5555-555555555551",
            user_id=user.id,
            job_id=target_job.id,
            status="applied",
            applied_at=datetime(2026, 1, 20, 9, 0, tzinfo=UTC),
            notes="Submitted",
        )

    with api_client(database_url) as client:
        response = client.get(
            "/api/v1/jobs",
            params=[
                ("title", "ML"),
                ("location", "Toronto"),
                ("company_ids", openai.id),
                ("work_modes", "remote"),
                ("posted_after", "2026-01-14"),
                ("posted_before", "2026-01-31"),
                ("sort", "posted_at"),
                ("order", "desc"),
                ("page", "1"),
                ("per_page", "1"),
            ],
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"] == {"page": 1, "per_page": 1, "total": 2, "total_pages": 2}
    assert payload["data"][0]["title"] == "ML Engineer II"

    with api_client(database_url) as client:
        response = client.get(
            "/api/v1/jobs",
            params=[
                ("title", "ML"),
                ("location", "Toronto"),
                ("company_ids", openai.id),
                ("work_modes", "remote"),
                ("posted_after", "2026-01-14"),
                ("posted_before", "2026-01-31"),
                ("sort", "posted_at"),
                ("order", "desc"),
                ("page", "2"),
                ("per_page", "1"),
            ],
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"][0]["id"] == target_job.id
    assert payload["data"][0]["application"]["status"] == "applied"


def test_job_detail_returns_full_content_and_404_for_unknown_job(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)
    with session_for_database(database_url) as session:
        user = seed_user(session)
        company = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222223",
            slug="vercel",
            name="Vercel",
        )
        source = seed_company_source(
            session,
            source_id="33333333-3333-3333-3333-333333333333",
            company_id=company.id,
        )
        job = seed_job(
            session,
            job_id="44444444-4444-4444-4444-444444444445",
            company_id=company.id,
            source_id=source.id,
            title="Platform Engineer",
            location_text="Remote",
            work_mode="remote",
            posted_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
            description_text="Full job description",
        )
        seed_application(
            session,
            application_id="55555555-5555-5555-5555-555555555552",
            user_id=user.id,
            job_id=job.id,
            status="saved",
            applied_at=None,
            notes="Need referral",
        )

    with api_client(database_url) as client:
        response = client.get(f"/api/v1/jobs/{job.id}")

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["id"] == job.id
        assert payload["company"]["name"] == "Vercel"
        assert payload["description_text"] == "Full job description"
        assert payload["application"]["notes"] == "Need referral"

        not_found = client.get("/api/v1/jobs/missing-job")

    assert not_found.status_code == 404
    assert not_found.json()["error"] == {
        "code": "job_not_found",
        "message": "Job not found",
    }

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

from sqlalchemy import func, select

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from job_discovery_backend.db.models import Application  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from support.api import api_client, session_for_database  # noqa: E402
from support.records import seed_application, seed_company, seed_company_source, seed_job, seed_user  # noqa: E402


def _database_url(tmp_path: Path) -> str:
    return f"sqlite+pysqlite:///{tmp_path / 'applications-api.sqlite3'}"


def test_application_upsert_creates_and_updates_single_record(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)
    with session_for_database(database_url) as session:
        company = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222221",
            slug="openai",
            name="OpenAI",
        )
        seed_user(session)
        source = seed_company_source(
            session,
            source_id="33333333-3333-3333-3333-333333333331",
            company_id=company.id,
        )
        job = seed_job(
            session,
            job_id="44444444-4444-4444-4444-444444444441",
            company_id=company.id,
            source_id=source.id,
            title="ML Engineer",
            location_text="Toronto",
            work_mode="remote",
            posted_at=datetime(2026, 1, 15, 10, 0, tzinfo=UTC),
            description_text="Role",
        )

    with api_client(database_url) as client:
        created = client.put(
            f"/api/v1/jobs/{job.id}/application",
            json={"status": "applied", "notes": "Submitted"},
        )
        updated = client.put(
            f"/api/v1/jobs/{job.id}/application",
            json={"status": "interviewing", "notes": "Recruiter screen booked"},
        )
        invalid = client.put(
            f"/api/v1/jobs/{job.id}/application",
            json={"status": "invalid"},
        )

    assert created.status_code == 200
    assert created.json()["data"]["status"] == "applied"
    assert created.json()["data"]["notes"] == "Submitted"
    assert created.json()["data"]["applied_at"] is not None

    assert updated.status_code == 200
    assert updated.json()["data"]["id"] == created.json()["data"]["id"]
    assert updated.json()["data"]["status"] == "interviewing"
    assert updated.json()["data"]["notes"] == "Recruiter screen booked"

    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"

    with session_for_database(database_url) as session:
        applications = session.scalar(select(func.count()).select_from(Application))
        assert applications == 1
        user_application = session.get(Application, created.json()["data"]["id"])
        assert user_application.status == "interviewing"


def test_application_list_filters_by_status_and_date(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)
    with session_for_database(database_url) as session:
        user = seed_user(session)
        company = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222222",
            slug="vercel",
            name="Vercel",
        )
        source = seed_company_source(
            session,
            source_id="33333333-3333-3333-3333-333333333332",
            company_id=company.id,
        )
        applied_job = seed_job(
            session,
            job_id="44444444-4444-4444-4444-444444444442",
            company_id=company.id,
            source_id=source.id,
            title="Platform Engineer",
            location_text="Remote",
            work_mode="remote",
            posted_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
            description_text="Role",
        )
        saved_job = seed_job(
            session,
            job_id="44444444-4444-4444-4444-444444444443",
            company_id=company.id,
            source_id=source.id,
            title="Backend Engineer",
            location_text="Remote",
            work_mode="remote",
            posted_at=datetime(2026, 2, 2, 10, 0, tzinfo=UTC),
            description_text="Role",
        )
        seed_application(
            session,
            application_id="55555555-5555-5555-5555-555555555551",
            user_id=user.id,
            job_id=applied_job.id,
            status="applied",
            applied_at=datetime(2026, 2, 3, 9, 0, tzinfo=UTC),
            notes="Submitted",
        )
        seed_application(
            session,
            application_id="55555555-5555-5555-5555-555555555552",
            user_id=user.id,
            job_id=saved_job.id,
            status="saved",
            applied_at=None,
            notes="Watch later",
        )

    with api_client(database_url) as client:
        response = client.get(
            "/api/v1/applications",
            params=[
                ("statuses", "applied"),
                ("applied_after", "2026-02-01"),
                ("applied_before", "2026-02-28"),
            ],
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["total"] == 1
    assert payload["data"][0]["status"] == "applied"
    assert payload["data"][0]["job"]["title"] == "Platform Engineer"

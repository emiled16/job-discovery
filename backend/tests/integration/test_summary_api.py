from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from support.api import api_client, session_for_database  # noqa: E402
from support.records import seed_application, seed_company, seed_company_source, seed_job, seed_saved_view, seed_user  # noqa: E402


def _database_url(tmp_path: Path) -> str:
    return f"sqlite+pysqlite:///{tmp_path / 'summary-api.sqlite3'}"


def test_summary_metrics_aggregate_total_applied_and_rate(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)
    with session_for_database(database_url) as session:
        user = seed_user(session)
        company = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222221",
            slug="openai",
            name="OpenAI",
        )
        source = seed_company_source(
            session,
            source_id="33333333-3333-3333-3333-333333333331",
            company_id=company.id,
        )
        job_one = seed_job(
            session,
            job_id="44444444-4444-4444-4444-444444444441",
            company_id=company.id,
            source_id=source.id,
            title="ML Engineer",
            location_text="Toronto",
            work_mode="remote",
            posted_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
            description_text="Role",
        )
        job_two = seed_job(
            session,
            job_id="44444444-4444-4444-4444-444444444442",
            company_id=company.id,
            source_id=source.id,
            title="Backend Engineer",
            location_text="Toronto",
            work_mode="remote",
            posted_at=datetime(2026, 1, 2, 10, 0, tzinfo=UTC),
            description_text="Role",
        )
        seed_application(
            session,
            application_id="55555555-5555-5555-5555-555555555551",
            user_id=user.id,
            job_id=job_one.id,
            status="applied",
            applied_at=datetime(2026, 1, 3, 9, 0, tzinfo=UTC),
        )
        seed_application(
            session,
            application_id="55555555-5555-5555-5555-555555555552",
            user_id=user.id,
            job_id=job_two.id,
            status="saved",
            applied_at=None,
        )
        seed_saved_view(
            session,
            view_id="66666666-6666-6666-6666-666666666661",
            user_id=user.id,
            name="Remote",
            filters={"work_modes": ["remote"]},
            sort={"field": "posted_at", "direction": "desc"},
        )

    with api_client(database_url) as client:
        response = client.get("/api/v1/summary/metrics")

    assert response.status_code == 200
    assert response.json()["data"] == {
        "total_jobs": 2,
        "applied_jobs": 1,
        "saved_views": 1,
        "application_rate": 0.5,
    }

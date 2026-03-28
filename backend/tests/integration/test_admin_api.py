from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from support.api import api_client, session_for_database  # noqa: E402
from support.records import seed_company, seed_company_source, seed_pipeline_run, seed_pipeline_run_event, seed_user  # noqa: E402


def _database_url(tmp_path: Path) -> str:
    return f"sqlite+pysqlite:///{tmp_path / 'admin-api.sqlite3'}"


def test_admin_companies_list_and_create_validate_defaults(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)
    with session_for_database(database_url) as session:
        seed_user(session)
        company = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222221",
            slug="openai",
            name="OpenAI",
        )
        seed_company_source(
            session,
            source_id="33333333-3333-3333-3333-333333333331",
            company_id=company.id,
        )

    with api_client(database_url) as client:
        listed = client.get("/api/v1/admin/companies")
        created = client.post(
            "/api/v1/admin/companies",
            json={
                "slug": "vercel",
                "name": "Vercel",
                "source": {"source_type": "lever", "base_url": "https://jobs.lever.co/vercel"},
            },
        )
        invalid = client.post(
            "/api/v1/admin/companies",
            json={"slug": "broken", "source": {"source_type": "lever"}},
        )

    assert listed.status_code == 200
    assert listed.json()["data"][0]["name"] == "OpenAI"
    assert created.status_code == 201
    assert created.json()["data"]["lifecycle_status"] == "draft"
    assert created.json()["data"]["sources"][0]["is_enabled"] is True
    assert invalid.status_code == 422

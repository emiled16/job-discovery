from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from support.api import api_client, session_for_database  # noqa: E402
from support.records import seed_user  # noqa: E402


def _database_url(tmp_path: Path) -> str:
    return f"sqlite+pysqlite:///{tmp_path / 'views-api.sqlite3'}"


def _valid_view_payload(name: str = "Remote ML") -> dict:
    return {
        "name": name,
        "filters": {
            "title": "ML Engineer",
            "location": "Toronto",
            "company_ids": ["company-1"],
            "work_modes": ["remote"],
            "posted_after": "2026-01-01",
            "posted_before": "2026-01-31",
        },
        "sort": {"field": "posted_at", "direction": "desc"},
        "is_default": False,
    }


def test_saved_view_create_validates_contract(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)
    with session_for_database(database_url) as session:
        seed_user(session)

    with api_client(database_url) as client:
        created = client.post("/api/v1/views", json=_valid_view_payload())
        invalid = client.post(
            "/api/v1/views",
            json={
                **_valid_view_payload("Broken"),
                "filters": {**_valid_view_payload()["filters"], "work_modes": ["space"]},
            },
        )

    assert created.status_code == 201
    assert created.json()["data"]["name"] == "Remote ML"
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"

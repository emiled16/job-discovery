from __future__ import annotations

from contextlib import contextmanager
from os import environ
from pathlib import Path
import sys
from unittest.mock import patch

from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from job_discovery_backend.app import create_app  # noqa: E402
from job_discovery_backend.config import BackendSettings  # noqa: E402
from job_discovery_backend.db.migrate import build_alembic_config  # noqa: E402


def migrated_sqlite_engine(database_url: str):
    command.upgrade(build_alembic_config(database_url), "head")
    engine = create_engine(database_url)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@contextmanager
def session_for_database(database_url: str):
    engine = migrated_sqlite_engine(database_url)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()


@contextmanager
def api_client(database_url: str):
    env = {
        **environ,
        "DATABASE_URL": database_url,
        "REDIS_URL": "redis://redis:6379/0",
    }
    with patch.dict("os.environ", env, clear=True):
        with patch(
            "job_discovery_backend.app.load_settings",
            return_value=BackendSettings(
                host="127.0.0.1",
                port=8000,
                database_url=database_url,
                redis_url="redis://redis:6379/0",
            ),
        ):
            client = TestClient(create_app())
            try:
                yield client
            finally:
                client.close()

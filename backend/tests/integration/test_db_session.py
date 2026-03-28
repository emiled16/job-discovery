from pathlib import Path
import sys

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from job_discovery_backend.db.session import (  # noqa: E402
    get_engine,
    get_session_factory,
    reset_database_state,
)


def teardown_function() -> None:
    reset_database_state()


def test_session_factory_creates_and_closes_session() -> None:
    database_url = "sqlite+pysqlite:///:memory:"
    engine = get_engine(database_url)
    session = get_session_factory(database_url)()

    result = session.execute(text("SELECT 1")).scalar_one()

    session.close()

    assert engine is get_engine(database_url)
    assert result == 1

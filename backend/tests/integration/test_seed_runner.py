from __future__ import annotations

from pathlib import Path
import sys

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from job_discovery_backend.db.models import Company, CompanySource, User  # noqa: E402
from job_discovery_backend.db.seed import run_seed  # noqa: E402


def _database_url(tmp_path: Path) -> str:
    return f"sqlite+pysqlite:///{tmp_path / 'seed.sqlite3'}"


def test_seed_runner_is_idempotent(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)

    run_seed(database_url)
    run_seed(database_url)

    engine = create_engine(database_url)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(User)) == 1
        assert session.scalar(select(func.count()).select_from(Company)) == 3
        assert session.scalar(select(func.count()).select_from(CompanySource)) == 3


def test_seed_creates_default_local_user(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)

    run_seed(database_url)

    engine = create_engine(database_url)
    with Session(engine) as session:
        user = session.scalar(select(User).where(User.seed_key == "local_user"))

    assert user is not None
    assert user.display_name == "Local User"


def test_seed_creates_starter_companies_with_valid_states(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)

    run_seed(database_url)

    engine = create_engine(database_url)
    with Session(engine) as session:
        companies = session.scalars(select(Company).order_by(Company.slug)).all()

    assert len(companies) == 3
    assert {company.lifecycle_status for company in companies} == {"active", "paused"}

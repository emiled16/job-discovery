from __future__ import annotations

from pathlib import Path
import sys

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from job_discovery_backend.db.models import Company, CompanySource, Job, User  # noqa: E402
from job_discovery_backend.db.seed_data import STARTER_COMPANIES  # noqa: E402
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
        assert session.scalar(select(func.count()).select_from(Company)) == len(STARTER_COMPANIES)
        assert session.scalar(select(func.count()).select_from(CompanySource)) == len(STARTER_COMPANIES)
        assert session.scalar(select(func.count()).select_from(Job)) == 2


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
        sources = session.scalars(select(CompanySource)).all()

    assert len(companies) == len(STARTER_COMPANIES)
    assert len(companies) >= 200
    assert {company.lifecycle_status for company in companies} == {"active"}
    assert {source.source_type for source in sources} == {
        "applytojob",
        "ashby",
        "greenhouse",
        "lever",
        "manual",
        "smartrecruiters",
        "workday",
    }
    assert sum(1 for source in sources if source.is_enabled) == len(STARTER_COMPANIES)
    assert sum(1 for source in sources if source.source_type != "manual") >= 61


def test_seed_matches_existing_company_by_name_to_avoid_duplicate_inserts(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)

    run_seed(database_url)

    engine = create_engine(database_url)
    with Session(engine) as session:
        company = session.scalar(select(Company).where(Company.name == "Stripe"))
        assert company is not None
        company.slug = "stripe-live"
        session.commit()

    run_seed(database_url, apply_migrations=False)

    with Session(engine) as session:
        companies = session.scalars(select(Company).where(Company.name == "Stripe")).all()

    assert len(companies) == 1


def test_user_only_seed_mode_skips_companies_sources_and_jobs(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)

    run_seed(database_url, mode="user-only")

    engine = create_engine(database_url)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(User)) == 1
        assert session.scalar(select(func.count()).select_from(Company)) == 0
        assert session.scalar(select(func.count()).select_from(CompanySource)) == 0
        assert session.scalar(select(func.count()).select_from(Job)) == 0

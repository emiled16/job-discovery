"""Deterministic seed runner for local bootstrap."""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from alembic import command
from sqlalchemy import select
from sqlalchemy.orm import Session

from job_discovery_backend.db.migrate import build_alembic_config
from job_discovery_backend.db.models import Company, CompanySource, Job, User
from job_discovery_backend.db.seed_data import LOCAL_USER, STARTER_COMPANIES, STARTER_JOBS
from job_discovery_backend.db.session import session_scope


@dataclass(frozen=True)
class SeedSummary:
    users_upserted: int
    companies_upserted: int
    company_sources_upserted: int
    jobs_upserted: int


def _upsert_user(session: Session) -> int:
    user = session.scalar(select(User).where(User.seed_key == LOCAL_USER["seed_key"]))
    if user is None:
        user = User(**LOCAL_USER)
        session.add(user)
    else:
        user.display_name = LOCAL_USER["display_name"]
        user.email = LOCAL_USER["email"]
    return 1


def _upsert_companies(session: Session) -> tuple[int, int]:
    companies_upserted = 0
    sources_upserted = 0

    for record in STARTER_COMPANIES:
        company_payload = record["company"]
        source_payload = record["source"]

        company = session.scalar(select(Company).where(Company.slug == company_payload["slug"]))
        if company is None:
            company = Company(**company_payload)
            session.add(company)
            session.flush()
        else:
            company.name = company_payload["name"]
            company.website_url = company_payload["website_url"]
            company.description = company_payload["description"]
            company.lifecycle_status = company_payload["lifecycle_status"]

        source = session.scalar(
            select(CompanySource).where(
                CompanySource.company_id == company.id,
                CompanySource.source_type == source_payload["source_type"],
            )
        )
        if source is None:
            source = CompanySource(company_id=company.id, **source_payload)
            session.add(source)
        else:
            source.external_key = source_payload["external_key"]
            source.base_url = source_payload["base_url"]
            source.configuration = source_payload["configuration"]
            source.is_enabled = source_payload["is_enabled"]

        companies_upserted += 1
        sources_upserted += 1

    return companies_upserted, sources_upserted


def _upsert_jobs(session: Session) -> int:
    jobs_upserted = 0

    for record in STARTER_JOBS:
        company = session.scalar(select(Company).where(Company.slug == record["company_slug"]))
        source = session.scalar(
            select(CompanySource).where(
                CompanySource.company_id == company.id,
                CompanySource.source_type == record["source_type"],
            )
        )
        job = session.scalar(select(Job).where(Job.source_identity == record["source_identity"]))
        payload = {
            "company_id": company.id,
            "source_id": source.id,
            "source_job_key": record["source_job_key"],
            "source_identity": record["source_identity"],
            "title": record["title"],
            "location_text": record["location_text"],
            "work_mode": record["work_mode"],
            "employment_type": record["employment_type"],
            "status": record["status"],
            "posted_at": record["posted_at"],
            "apply_url": record["apply_url"],
            "description_text": record["description_text"],
            "last_seen_at": record["last_seen_at"],
            "missed_sync_count": record["missed_sync_count"],
        }
        if job is None:
            job = Job(id=record["id"], **payload)
            session.add(job)
        else:
            for key, value in payload.items():
                setattr(job, key, value)
        jobs_upserted += 1

    return jobs_upserted


def run_seed(database_url: str | None = None, *, apply_migrations: bool = True) -> SeedSummary:
    if apply_migrations:
        command.upgrade(build_alembic_config(database_url), "head")

    with session_scope(database_url) as session:
        users_upserted = _upsert_user(session)
        companies_upserted, company_sources_upserted = _upsert_companies(session)
        jobs_upserted = _upsert_jobs(session)

    return SeedSummary(
        users_upserted=users_upserted,
        companies_upserted=companies_upserted,
        company_sources_upserted=company_sources_upserted,
        jobs_upserted=jobs_upserted,
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run deterministic local seed data.")
    parser.add_argument(
        "--skip-migrate",
        action="store_true",
        help="Skip running migrations before the seed step.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Override the database URL used for migrations and seed writes.",
    )
    args = parser.parse_args(argv)

    summary = run_seed(args.database_url, apply_migrations=not args.skip_migrate)
    print(
        "Seed complete:"
        f" users={summary.users_upserted}"
        f" companies={summary.companies_upserted}"
        f" company_sources={summary.company_sources_upserted}"
        f" jobs={summary.jobs_upserted}"
    )


if __name__ == "__main__":
    main()

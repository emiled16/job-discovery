"""Alembic migration command helpers."""

from __future__ import annotations

from pathlib import Path
import argparse

from alembic import command
from alembic.config import Config

from job_discovery_backend.config import load_settings


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def build_alembic_config(database_url: str | None = None) -> Config:
    root = project_root()
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.set_main_option(
        "sqlalchemy.url",
        database_url or load_settings().database_url,
    )
    return config


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run database migrations.")
    parser.add_argument(
        "command",
        choices=("upgrade", "downgrade", "current"),
        help="Alembic command to run.",
    )
    parser.add_argument(
        "revision",
        nargs="?",
        default="head",
        help="Target revision for upgrade/downgrade.",
    )
    args = parser.parse_args(argv)

    config = build_alembic_config()

    if args.command == "upgrade":
        command.upgrade(config, args.revision)
        return

    if args.command == "downgrade":
        command.downgrade(config, args.revision)
        return

    command.current(config)


if __name__ == "__main__":
    main()

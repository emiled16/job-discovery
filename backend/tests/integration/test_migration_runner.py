from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from job_discovery_backend.db.migrate import build_alembic_config, project_root  # noqa: E402


def test_build_alembic_config_targets_backend_paths() -> None:
    config = build_alembic_config("sqlite+pysqlite:///:memory:")

    assert config.get_main_option("script_location") == str(project_root() / "alembic")
    assert config.get_main_option("sqlalchemy.url") == "sqlite+pysqlite:///:memory:"

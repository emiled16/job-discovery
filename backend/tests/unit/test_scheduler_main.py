from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from job_discovery_backend.scheduler.main import main  # noqa: E402


def test_scheduler_uses_writable_beat_schedule_path() -> None:
    with patch("job_discovery_backend.scheduler.main.configure_logging") as configure_logging:
        with patch("job_discovery_backend.scheduler.main.celery_app.start") as start:
            main()

    configure_logging.assert_called_once_with("scheduler")
    start.assert_called_once_with(
        [
            "beat",
            "--loglevel=INFO",
            "--schedule=/tmp/celerybeat-schedule",
        ]
    )

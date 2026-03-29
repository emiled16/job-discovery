from job_discovery_backend.config import load_settings
from job_discovery_backend.db.seed import run_seed


def main() -> None:
    settings = load_settings()
    run_seed(
        settings.database_url,
        mode=settings.startup_seed_mode,
    )


if __name__ == "__main__":
    main()

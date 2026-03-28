import uvicorn

from job_discovery_backend.config import load_settings
from job_discovery_backend.observability import configure_logging

def main() -> None:
    configure_logging("api")
    settings = load_settings()
    uvicorn.run(
        "job_discovery_backend.app:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()

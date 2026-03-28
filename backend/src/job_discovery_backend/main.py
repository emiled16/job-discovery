import uvicorn

from job_discovery_backend.config import load_settings

def main() -> None:
    settings = load_settings()
    uvicorn.run(
        "job_discovery_backend.app:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()

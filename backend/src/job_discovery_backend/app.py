from fastapi import FastAPI

from job_discovery_backend.api.routes.health import router as health_router
from job_discovery_backend.config import load_settings


def create_app() -> FastAPI:
    settings = load_settings()
    app = FastAPI(
        title="Job Discovery API",
        version="0.1.0",
    )
    app.state.settings = settings
    app.include_router(health_router)
    return app


app = create_app()

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from job_discovery_backend.api.errors import (
    ApiError,
    api_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from job_discovery_backend.api.middleware import request_id_middleware
from job_discovery_backend.api.routes.health import router as health_router
from job_discovery_backend.config import load_settings


def create_app() -> FastAPI:
    settings = load_settings()
    app = FastAPI(
        title="Job Discovery API",
        version="0.1.0",
    )
    app.state.settings = settings
    app.middleware("http")(request_id_middleware)
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.include_router(health_router)
    return app


app = create_app()

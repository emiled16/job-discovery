from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

REQUEST_ID_HEADER = "X-Request-ID"


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def build_error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    request_id = get_request_id(request)
    payload: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
        },
        "request_id": request_id,
    }
    if details:
        payload["error"]["details"] = details

    response = JSONResponse(status_code=status_code, content=payload)
    if request_id:
        response.headers[REQUEST_ID_HEADER] = request_id
    return response


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return build_error_response(
        request=request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    details = exc.detail if isinstance(exc.detail, list) else None
    code = "not_found" if exc.status_code == 404 else "http_error"
    return build_error_response(
        request=request,
        status_code=exc.status_code,
        code=code,
        message=message,
        details=details,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"] if part != "body"),
            "message": error["msg"],
            "code": error["type"],
        }
        for error in exc.errors()
    ]
    return build_error_response(
        request=request,
        status_code=422,
        code="validation_error",
        message="Request validation failed",
        details=details,
    )


async def unhandled_exception_handler(request: Request, _exc: Exception) -> JSONResponse:
    return build_error_response(
        request=request,
        status_code=500,
        code="internal_server_error",
        message="Internal server error",
    )

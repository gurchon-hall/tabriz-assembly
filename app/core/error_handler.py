"""Global exception handlers for FastAPI application.

Provides consistent error response formatting across the application.
"""

import traceback
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.core.exceptions import AppException

logger = settings.log.get_logger(__name__)


def create_error_response(
    request_id: str,
    error_code: str,
    message: str,
    status_code: int,
    details: dict[str, Any] | None = None,
    path: str | None = None,
) -> dict[str, Any]:
    """Create a standardized error response."""
    return {
        "error": {
            "code": error_code,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now(UTC).isoformat(),
            "request_id": request_id,
            "path": path,
        }
    }


def get_request_id(request: Request) -> str:
    """Get or generate a request ID."""
    return getattr(request.state, "request_id", str(uuid.uuid4()))


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    request_id = get_request_id(request)

    logger.warning(
        f"AppException: {exc.error_code} - {exc.message}",
        extra={
            "request_id": request_id,
            "error_code": exc.error_code,
            "path": request.url.path,
            "details": exc.details,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            request_id=request_id,
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
            path=request.url.path,
        ),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle Starlette/FastAPI HTTP exceptions."""
    request_id = get_request_id(request)

    # Map status codes to error codes
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT",
    }

    error_code = error_code_map.get(exc.status_code, "HTTP_ERROR")

    logger.warning(
        f"HTTPException: {exc.status_code} - {exc.detail}",
        extra={
            "request_id": request_id,
            "status_code": exc.status_code,
            "path": request.url.path,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            request_id=request_id,
            error_code=error_code,
            message=str(exc.detail) if exc.detail else "An error occurred",
            status_code=exc.status_code,
            path=request.url.path,
        ),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors."""
    request_id = get_request_id(request)

    # Format validation errors
    errors: list[dict[str, Any]] = []
    for error in exc.errors():
        errors.append(
            {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    logger.warning(
        f"ValidationError: {len(errors)} validation errors",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "errors": errors,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=create_error_response(
            request_id=request_id,
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"validation_errors": errors},
            path=request.url.path,
        ),
    )


async def pydantic_exception_handler(
    request: Request, exc: PydanticValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    request_id = get_request_id(request)

    errors: list[dict[str, Any]] = []
    for error in exc.errors():
        errors.append(
            {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    logger.warning(
        f"PydanticValidationError: {len(errors)} errors",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "errors": errors,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=create_error_response(
            request_id=request_id,
            error_code="VALIDATION_ERROR",
            message="Data validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"validation_errors": errors},
            path=request.url.path,
        ),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions."""
    request_id = get_request_id(request)

    # Log the full traceback for debugging
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {exc}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "traceback": traceback.format_exc(),
        },
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            request_id=request_id,
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            path=request.url.path,
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI application."""
    app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(PydanticValidationError, pydantic_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_exception_handler)

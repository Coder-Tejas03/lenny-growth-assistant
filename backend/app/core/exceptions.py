"""
Lenny Growth Assistant — Global Exception Handlers

Translates all application exceptions, validation failures, and unhandled errors
into the standard structured error envelope matching Section 13 of docs/implementation-contract.md.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.error import AppException, utc_now

logger = logging.getLogger("lenny_api.exceptions")


def format_error_payload(code: str, message: str, details: Dict[str, Any]) -> Dict[str, Any]:
    """Builds standard error envelope dictionary."""
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "timestamp": utc_now().isoformat(),
        }
    }


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handles domain-specific application exceptions."""
    logger.warning(
        "Application exception on %s %s: code=%s message=%s",
        request.method,
        request.url.path,
        exc.code,
        exc.message,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handles Pydantic input validation failures with structured 422 responses."""
    cleaned_errors = []
    for err in exc.errors():
        loc = " -> ".join(str(item) for item in err.get("loc", []))
        msg = err.get("msg", "Validation error")
        cleaned_errors.append({"field": loc, "issue": msg, "type": err.get("type", "value_error")})

    payload = format_error_payload(
        code="VALIDATION_ERROR",
        message="Request payload failed validation.",
        details={"validation_errors": cleaned_errors},
    )
    logger.info(
        "Validation failed on %s %s: %s",
        request.method,
        request.url.path,
        cleaned_errors,
    )
    return JSONResponse(status_code=422, content=payload)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handles standard Starlette/FastAPI HTTPExceptions."""
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        408: "REQUEST_TIMEOUT",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
    }
    code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
    message = str(exc.detail) if exc.detail else "An HTTP error occurred."

    payload = format_error_payload(
        code=code,
        message=message,
        details={"status_code": exc.status_code},
    )
    return JSONResponse(status_code=exc.status_code, content=payload)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unexpected exceptions to prevent stack trace leakage."""
    logger.exception("Unhandled internal exception on %s %s", request.method, request.url.path)
    payload = format_error_payload(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred. Please try again.",
        details={},
    )
    return JSONResponse(status_code=500, content=payload)


def register_exception_handlers(app: FastAPI) -> None:
    """Registers all custom exception handlers on the FastAPI application."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

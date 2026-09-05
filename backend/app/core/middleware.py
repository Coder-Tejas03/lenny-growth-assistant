"""
Lenny Growth Assistant — Request ID & Structured Logging Middleware

Injects unique request tracking IDs, catches unhandled runtime faults,
and emits structured audit logs without sensitive data leaks.
"""

import logging
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import format_error_payload

logger = logging.getLogger("lenny_api.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that:
    1. Extracts or generates an X-Request-ID for every HTTP request.
    2. Attaches request_id to request.state.
    3. Records request start time and logs latency on completion.
    4. Guarantees structured error envelope for any unhandled exceptions.
    5. Propagates X-Request-ID back in response headers for tracing.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract existing X-Request-ID or generate new UUID4
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        request.state.request_id = request_id

        start_time = time.perf_counter()
        method = request.method
        path = request.url.path

        # Suppress noisy healthcheck logs if desired, or log at DEBUG/INFO
        is_health = path.endswith("/health")

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            log_level = logging.DEBUG if is_health else logging.INFO
            logger.log(
                log_level,
                "HTTP %s %s -> %d (%.2f ms) [req_id=%s]",
                method,
                path,
                response.status_code,
                duration_ms,
                request_id,
            )

            # Set trace header on response
            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception(
                "HTTP %s %s -> UNHANDLED EXCEPTION after %.2f ms [req_id=%s]",
                method,
                path,
                duration_ms,
                request_id,
            )
            # Ensure the client receives a structured 500 error envelope without leaked secrets
            payload = format_error_payload(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected server error occurred. Please try again.",
                details={},
            )
            err_response = JSONResponse(status_code=500, content=payload)
            err_response.headers["X-Request-ID"] = request_id
            return err_response

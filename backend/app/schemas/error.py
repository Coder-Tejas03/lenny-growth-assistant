"""
Lenny Growth Assistant — Structured Error Models & Exception Hierarchy

Defines standard error contracts and exception classes matching Section 13 of docs/implementation-contract.md.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    """Returns timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class ErrorDetail(BaseModel):
    """The structured inner error object."""
    code: str = Field(..., description="Standardized error code string (e.g. VALIDATION_ERROR)")
    message: str = Field(..., description="Human-readable, safe error message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Contextual error details")
    timestamp: datetime = Field(default_factory=utc_now, description="UTC timestamp of the error")


class ErrorResponse(BaseModel):
    """The top-level JSON error envelope required for all non-2xx responses."""
    error: ErrorDetail


class AppException(Exception):
    """Base application exception supporting structured API error responses."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.timestamp = utc_now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
                "timestamp": self.timestamp.isoformat(),
            }
        }


class ValidationError(AppException):
    """Raised when client input fails validation checks."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=400,
            details=details,
        )


class SessionNotFoundError(AppException):
    """Raised when a requested session UUID is not found in the database."""

    def __init__(self, session_id: str) -> None:
        super().__init__(
            code="SESSION_NOT_FOUND",
            message=f"Session '{session_id}' not found.",
            status_code=404,
            details={"session_id": session_id},
        )


class BudgetExceededException(AppException):
    """Raised when cumulative OpenAI API spend has hit the configured budget ceiling."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            code="BUDGET_EXCEEDED",
            message=message,
            status_code=402,
            details=details,
        )


class ProviderUnavailableException(AppException):
    """Raised when a requested LLM provider (Ollama or OpenAI) is unreachable or times out."""

    def __init__(self, provider: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        merged_details = {"provider": provider}
        if details:
            merged_details.update(details)
        super().__init__(
            code="PROVIDER_UNAVAILABLE",
            message=message,
            status_code=503,
            details=merged_details,
        )


class ArtifactNotFoundError(AppException):
    """Raised when a requested artifact UUID is not found in the database."""

    def __init__(self, artifact_id: str) -> None:
        super().__init__(
            code="ARTIFACT_NOT_FOUND",
            message=f"Artifact '{artifact_id}' not found.",
            status_code=404,
            details={"artifact_id": artifact_id},
        )


class DatabaseErrorException(AppException):
    """Raised when a database query or connection failure occurs."""

    def __init__(self, message: str = "A database error occurred.", details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            code="DATABASE_ERROR",
            message=message,
            status_code=500,
            details=details,
        )

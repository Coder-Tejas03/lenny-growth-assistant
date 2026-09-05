"""
Lenny Growth Assistant — Schemas Package

Exports validated data models for errors, sessions, messages, citations, and health probes.
"""

from app.schemas.error import (
    AppException,
    ArtifactNotFoundError,
    BudgetExceededException,
    DatabaseErrorException,
    ErrorDetail,
    ErrorResponse,
    ProviderUnavailableException,
    SessionNotFoundError,
    ValidationError,
)
from app.schemas.health import (
    CorpusHealthStatus,
    DatabaseHealthStatus,
    HealthResponse,
    OllamaProviderHealth,
    OpenAIProviderHealth,
    ProviderHealthStatus,
)
from app.schemas.session import (
    ArtifactResponse,
    CitationResponse,
    CreateSessionRequest,
    MessageResponse,
    SessionDetailResponse,
    SessionResponse,
    SessionSummaryResponse,
    UpdateSessionRequest,
)

from app.schemas.chat import (
    ChatMode,
    ChatProvider,
    ChatRequest,
    SSEEvent,
    format_sse,
    format_sse_done,
)

__all__ = [
    "AppException",
    "ValidationError",
    "SessionNotFoundError",
    "ArtifactNotFoundError",
    "BudgetExceededException",
    "ProviderUnavailableException",
    "DatabaseErrorException",
    "ErrorDetail",
    "ErrorResponse",
    "CreateSessionRequest",
    "UpdateSessionRequest",
    "SessionResponse",
    "SessionSummaryResponse",
    "CitationResponse",
    "MessageResponse",
    "ArtifactResponse",
    "SessionDetailResponse",
    "DatabaseHealthStatus",
    "OpenAIProviderHealth",
    "OllamaProviderHealth",
    "ProviderHealthStatus",
    "CorpusHealthStatus",
    "HealthResponse",
    "ChatMode",
    "ChatProvider",
    "ChatRequest",
    "SSEEvent",
    "format_sse",
    "format_sse_done",
]


"""
Lenny Growth Assistant — Phase 6 Schema & Error Unit Tests

Verifies Pydantic contracts, exception hierarchy, and error envelope formatting.
"""

import uuid
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError as PydanticValidationError

from app.schemas.error import (
    AppException,
    BudgetExceededException,
    DatabaseErrorException,
    ErrorDetail,
    ErrorResponse,
    ProviderUnavailableException,
    SessionNotFoundError,
    ValidationError,
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
from app.schemas.health import (
    CorpusHealthStatus,
    DatabaseHealthStatus,
    HealthResponse,
    OllamaProviderHealth,
    OpenAIProviderHealth,
    ProviderHealthStatus,
)


class TestErrorSchemasAndHierarchy:
    """Tests structured error contracts matching Section 13 of implementation-contract.md."""

    def test_error_envelope_structure(self):
        detail = ErrorDetail(
            code="PROVIDER_UNAVAILABLE",
            message="Ollama service unreachable",
            details={"provider": "ollama", "port": 11434},
        )
        envelope = ErrorResponse(error=detail)
        data = envelope.model_dump()

        assert "error" in data
        assert data["error"]["code"] == "PROVIDER_UNAVAILABLE"
        assert data["error"]["message"] == "Ollama service unreachable"
        assert data["error"]["details"]["provider"] == "ollama"
        assert "timestamp" in data["error"]

    def test_validation_error_exception(self):
        exc = ValidationError("Field 'anonymous_identifier' required.", details={"field": "anonymous_identifier"})
        assert exc.status_code == 400
        assert exc.code == "VALIDATION_ERROR"
        d = exc.to_dict()
        assert d["error"]["code"] == "VALIDATION_ERROR"
        assert d["error"]["details"]["field"] == "anonymous_identifier"

    def test_session_not_found_exception(self):
        fake_id = str(uuid.uuid4())
        exc = SessionNotFoundError(fake_id)
        assert exc.status_code == 404
        assert exc.code == "SESSION_NOT_FOUND"
        assert fake_id in exc.message
        assert exc.details["session_id"] == fake_id

    def test_budget_exceeded_exception(self):
        exc = BudgetExceededException("Budget $4.00 exhausted", details={"spent": 4.02})
        assert exc.status_code == 402
        assert exc.code == "BUDGET_EXCEEDED"
        assert exc.details["spent"] == 4.02

    def test_provider_unavailable_exception(self):
        exc = ProviderUnavailableException("ollama", "Connection refused")
        assert exc.status_code == 503
        assert exc.code == "PROVIDER_UNAVAILABLE"
        assert exc.details["provider"] == "ollama"

    def test_database_error_exception(self):
        exc = DatabaseErrorException("Failed to connect to postgres")
        assert exc.status_code == 500
        assert exc.code == "DATABASE_ERROR"


class TestSessionSchemas:
    """Tests session request/response contracts matching Section 11 of implementation-contract.md."""

    def test_create_session_request_valid(self):
        req = CreateSessionRequest(
            title="Product Market Fit Chat",
            anonymous_identifier="anon_user_abc123",
        )
        assert req.title == "Product Market Fit Chat"
        assert req.anonymous_identifier == "anon_user_abc123"

    def test_create_session_request_defaults(self):
        req = CreateSessionRequest(anonymous_identifier="anon_default")
        assert req.title == "New Conversation"

    def test_create_session_request_empty_identifier_fails(self):
        with pytest.raises(PydanticValidationError):
            CreateSessionRequest(anonymous_identifier="")

    def test_update_session_request(self):
        req = UpdateSessionRequest(title="Updated Title")
        assert req.title == "Updated Title"

    def test_session_detail_graph_schema(self):
        session_id = uuid.uuid4()
        chunk_id = uuid.uuid4()
        msg_id = uuid.uuid4()
        art_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        citation = CitationResponse(
            chunk_id=chunk_id,
            episode_title="Rahul Vohra on PMF",
            guest_name="Rahul Vohra",
            timestamp="14:22",
            source_url="https://lennyspodcast.com/rahul",
            similarity=0.88,
            excerpt="When we surveyed Superhuman users...",
        )

        message = MessageResponse(
            id=msg_id,
            role="assistant",
            content="Superhuman measured PMF using the Sean Ellis engine.",
            provider="openai",
            model="gpt-4o-mini",
            tokens_prompt=500,
            tokens_completion=150,
            cost_usd=0.0001,
            citations=[citation],
            created_at=now,
        )

        artifact = ArtifactResponse(
            id=art_id,
            type="markdown",
            title="PMF Framework",
            content="# PMF Framework\nStep 1...",
            created_at=now,
        )

        detail = SessionDetailResponse(
            id=session_id,
            title="Rahul Vohra on PMF",
            created_at=now,
            updated_at=now,
            messages=[message],
            artifacts=[artifact],
        )

        assert detail.id == session_id
        assert len(detail.messages) == 1
        assert detail.messages[0].citations[0].guest_name == "Rahul Vohra"
        assert len(detail.artifacts) == 1


class TestHealthSchemas:
    """Tests health probe schemas matching Section 11 of implementation-contract.md."""

    def test_health_response_schema(self):
        health = HealthResponse(
            status="healthy",
            database=DatabaseHealthStatus(
                connected=True,
                pgvector_ready=True,
                vector_version="0.8.6",
                uuid_ready=True,
                latency_ms=1.45,
            ),
            providers=ProviderHealthStatus(
                openai=OpenAIProviderHealth(
                    configured=True,
                    budget_remaining_usd=3.95,
                    model="gpt-4o-mini",
                ),
                ollama=OllamaProviderHealth(
                    available=True,
                    model="qwen2.5:1.5b",
                    base_url="http://localhost:11434",
                ),
            ),
            corpus=CorpusHealthStatus(
                indexed_chunks=150,
                indexed_episodes=5,
            ),
        )

        assert health.status == "healthy"
        assert health.database.connected is True
        assert health.database.vector_version == "0.8.6"
        assert health.providers.openai.budget_remaining_usd == 3.95
        assert health.providers.ollama.model == "qwen2.5:1.5b"
        assert health.corpus.indexed_chunks == 150

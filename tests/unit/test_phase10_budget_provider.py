"""
Unit Tests for Phase 10: Provider UX, Ollama Demo, and Budget Controls.

Verifies:
1. Cumulative spend tracking and hard budget ceiling enforcement in OpenAIProvider.
2. Safe budget telemetry in health status schemas without secret exposure.
3. ChatService error handling, rollback, and design.md-compliant fallback suggestions
   when budget is exceeded or provider is unavailable.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.db.models import Message, Session, User
from app.providers.base import BudgetExceededError, ProviderUnavailableError
from app.providers.openai_provider import OpenAIProvider
from app.schemas.chat import ChatMode, ChatRequest
from app.schemas.health import OpenAIProviderHealth
from app.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_openai_provider_cumulative_spend_tracking():
    """Verifies that OpenAIProvider tracks token usage and increments cumulative spend."""
    OpenAIProvider.reset_cumulative_spend()
    assert OpenAIProvider.get_cumulative_spend() == 0.0

    provider = OpenAIProvider(mock_mode=True, budget_limit=4.00)
    messages = [{"role": "user", "content": "How do you evaluate product retention?"}]
    system_prompt = "You are Lenny Assistant."

    tokens = []
    async for token in provider.stream_chat(messages, system_prompt):
        tokens.append(token)

    assert len(tokens) > 0
    spend = OpenAIProvider.get_cumulative_spend()
    assert spend > 0.0

    meta = provider.get_last_metadata()
    assert meta is not None
    assert meta.provider == "openai"
    assert meta.total_tokens > 0
    assert meta.cost_usd > 0.0


@pytest.mark.asyncio
async def test_openai_provider_budget_ceiling_enforcement():
    """Verifies that exceeding the configured budget limit immediately halts execution."""
    OpenAIProvider.reset_cumulative_spend()
    # Set an artificially low budget ceiling that is already exceeded
    tiny_budget = 0.0000001
    provider = OpenAIProvider(mock_mode=True, budget_limit=tiny_budget)

    # First call will consume tokens and exceed tiny budget
    messages = [{"role": "user", "content": "Tell me about product metrics."}]
    async for _ in provider.stream_chat(messages, "System prompt"):
        pass

    assert OpenAIProvider.get_cumulative_spend() > tiny_budget

    # Subsequent call must immediately raise BudgetExceededError without continuing
    with pytest.raises(BudgetExceededError) as exc_info:
        async for _ in provider.stream_chat(messages, "System prompt"):
            pass

    assert exc_info.value.budget_limit == tiny_budget
    assert "budget limit exceeded" in str(exc_info.value).lower()
    OpenAIProvider.reset_cumulative_spend()


def test_openai_provider_health_schema_safety():
    """Verifies that OpenAIProviderHealth reports budget metrics without exposing keys."""
    health = OpenAIProviderHealth(
        configured=True,
        budget_remaining_usd=3.85,
        budget_exceeded=False,
        model="gpt-4o-mini",
    )
    dump = health.model_dump()
    assert dump["configured"] is True
    assert dump["budget_remaining_usd"] == 3.85
    assert dump["budget_exceeded"] is False
    assert dump["model"] == "gpt-4o-mini"
    # Ensure zero private credential fields exist in schema
    assert "api_key" not in dump
    assert "secret" not in dump


@pytest.fixture
def mock_db_session():
    """Mock async SQLAlchemy session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_chat_service_budget_exceeded_sse_and_rollback(mock_db_session):
    """
    Verifies that when OpenAIProvider raises BudgetExceededError:
    1. ChatService catches it and emits a design.md-compliant SSE error event.
    2. Suggests manual fallback to 'ollama'.
    3. Rolls back the database transaction so zero incomplete assistant messages exist.
    """
    session_id = uuid.uuid4()
    mock_session = Session(id=session_id, user_id=uuid.uuid4(), title="Budget Test Session")

    chat_service = ChatService(db=mock_db_session)
    chat_service.session_repo.get_by_id = AsyncMock(return_value=mock_session)

    user_msg = Message(id=uuid.uuid4(), session_id=session_id, role="user", content="What is PMF?")
    chat_service.message_repo.create = AsyncMock(return_value=user_msg)
    chat_service.message_repo.list_by_session = AsyncMock(return_value=[user_msg])

    mock_retriever = AsyncMock()
    mock_retriever.retrieve.return_value = AsyncMock(chunks=[], citations=[])
    chat_service.retriever = mock_retriever

    async def raise_budget_error(*args, **kwargs):
        raise BudgetExceededError(current_spend=4.05, budget_limit=4.00)
        yield

    chat_service.agent_client = AsyncMock()
    chat_service.agent_client.stream_skill = raise_budget_error

    req = ChatRequest(
        session_id=str(session_id),
        message="What is PMF?",
        provider="openai",
        model="gpt-4o-mini",
    )

    events = []
    async for sse_chunk in chat_service.stream_chat(req):
        for line in sse_chunk.splitlines():
            if line.startswith("data: ") and not line.startswith("data: [DONE]"):
                import json
                events.append(json.loads(line[6:].strip()))

    error_events = [e for e in events if e.get("code") == "BUDGET_EXCEEDED"]
    assert len(error_events) == 1
    err = error_events[0]
    assert err["code"] == "BUDGET_EXCEEDED"
    assert "demo's API budget has been reached" in err["message"]
    assert err["details"]["fallback_suggested"] == "ollama"
    assert err["details"]["budget_limit"] == 4.00

    # Verify rollback was called and assistant message was NOT created
    assert mock_db_session.rollback.call_count >= 1
    assert chat_service.message_repo.create.call_count == 1  # only user message created


@pytest.mark.asyncio
async def test_chat_service_provider_unavailable_sse_and_rollback(mock_db_session):
    """
    Verifies that when Ollama raises ProviderUnavailableError:
    1. Emits design.md-compliant PROVIDER_UNAVAILABLE error event.
    2. Suggests manual fallback to 'openai'.
    3. Rolls back so zero incomplete assistant messages exist.
    """
    session_id = uuid.uuid4()
    mock_session = Session(id=session_id, user_id=uuid.uuid4(), title="Provider Test Session")

    chat_service = ChatService(db=mock_db_session)
    chat_service.session_repo.get_by_id = AsyncMock(return_value=mock_session)

    user_msg = Message(id=uuid.uuid4(), session_id=session_id, role="user", content="Explain cohorts")
    chat_service.message_repo.create = AsyncMock(return_value=user_msg)
    chat_service.message_repo.list_by_session = AsyncMock(return_value=[user_msg])

    mock_retriever = AsyncMock()
    mock_retriever.retrieve.return_value = AsyncMock(chunks=[], citations=[])
    chat_service.retriever = mock_retriever

    async def raise_unavailable_error(*args, **kwargs):
        raise ProviderUnavailableError(
            provider="ollama",
            message="Connection refused on port 11434",
            details={"port": 11434},
        )
        yield

    chat_service.agent_client = AsyncMock()
    chat_service.agent_client.stream_skill = raise_unavailable_error

    req = ChatRequest(
        session_id=str(session_id),
        message="Explain cohorts",
        provider="ollama",
        model="qwen2.5:1.5b",
    )

    events = []
    async for sse_chunk in chat_service.stream_chat(req):
        for line in sse_chunk.splitlines():
            if line.startswith("data: ") and not line.startswith("data: [DONE]"):
                import json
                events.append(json.loads(line[6:].strip()))

    error_events = [e for e in events if e.get("code") == "PROVIDER_UNAVAILABLE"]
    assert len(error_events) == 1
    err = error_events[0]
    assert err["code"] == "PROVIDER_UNAVAILABLE"
    assert "isn't available right now" in err["message"]
    assert err["details"]["fallback_suggested"] == "openai"

    assert mock_db_session.rollback.call_count >= 1
    assert chat_service.message_repo.create.call_count == 1

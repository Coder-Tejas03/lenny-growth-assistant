"""
Unit tests for Phase 7 ChatService.

Validates session verification, user message persistence, semantic retrieval integration,
SSE event sequencing, atomic persistence on completion, and rollback on generation error.
"""

from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, List
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent.client import PiAgentClient
from app.agent.models import AgentRequestPayload, StreamEventModel
from app.agent.skills import CANONICAL_ABSTENTION_MESSAGE
from app.db.models import Message, MessageCitation, Session, User
from app.providers.base import BudgetExceededError, ProviderUnavailableError
from app.retrieval.models import Citation, EvidenceChunk, RetrievalResult
from app.retrieval.retriever import TranscriptRetriever
from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService


@pytest.fixture
def mock_db_session():
    """Mock async SQLAlchemy session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_chat_service_nonexistent_session(mock_db_session):
    service = ChatService(db=mock_db_session)
    service.session_repo.get_by_id = AsyncMock(return_value=None)

    req = ChatRequest(
        session_id=uuid.uuid4(),
        message="Hello Lenny",
        mock_mode=True,
    )

    events = [chunk async for chunk in service.stream_chat(req)]
    assert len(events) == 2
    assert "event: error" in events[0]
    assert "SESSION_NOT_FOUND" in events[0]
    assert events[1] == "data: [DONE]\n\n"


@pytest.mark.asyncio
async def test_chat_service_grounded_qa_success(mock_db_session):
    session_id = uuid.uuid4()
    mock_session = Session(id=session_id, user_id=uuid.uuid4(), title="Test Session")
    mock_session.touch = MagicMock()

    service = ChatService(db=mock_db_session)
    service.session_repo.get_by_id = AsyncMock(return_value=mock_session)

    # Mock user message creation
    user_msg_id = uuid.uuid4()
    mock_user_msg = Message(id=user_msg_id, session_id=session_id, role="user", content="What is PMF?")
    service.message_repo.create = AsyncMock(side_effect=[
        mock_user_msg,
        Message(
            id=uuid.uuid4(),
            session_id=session_id,
            role="assistant",
            content="PMF is finding product-market fit.",
            provider="openai",
            model="gpt-4o-mini",
        ),
    ])
    service.message_repo.list_by_session = AsyncMock(return_value=[mock_user_msg])
    service.message_repo.add_citations = AsyncMock()

    # Mock retrieval
    chunk_id = uuid.uuid4()
    mock_evidence = EvidenceChunk(
        chunk_id=chunk_id,
        episode_title="Rahul Vohra on PMF",
        guest_name="Rahul Vohra",
        content="PMF means having high retention.",
        timestamp="12:00",
        source_url="https://example.com",
        similarity=0.85,
    )
    mock_citation = Citation(
        chunk_id=chunk_id,
        episode_title="Rahul Vohra on PMF",
        guest_name="Rahul Vohra",
        timestamp="12:00",
        source_url="https://example.com",
        similarity=0.85,
        excerpt="PMF means having high retention.",
    )
    service.retriever.retrieve = AsyncMock(
        return_value=RetrievalResult(
            query="What is PMF?",
            chunks=[mock_evidence],
            citations=[mock_citation],
            is_sufficient=True,
            query_latency_ms=15.0,
        )
    )


    # Mock Pi Agent Client stream
    async def mock_stream_skill(payload: AgentRequestPayload) -> AsyncGenerator[StreamEventModel, None]:
        yield StreamEventModel(event="status", data={"stage": "generating", "message": "Drafting..."})
        yield StreamEventModel(event="token", data={"delta": "PMF is "})
        yield StreamEventModel(event="token", data={"delta": "finding product-market fit."})
        yield StreamEventModel(
            event="done",
            data={
                "provider": "openai",
                "model": "gpt-4o-mini",
                "tokens": {"prompt": 100, "completion": 8},
                "cost_usd": 0.0001,
            },
        )

    service.agent_client.stream_skill = mock_stream_skill

    req = ChatRequest(
        session_id=session_id,
        message="What is PMF?",
        provider="openai",
        mock_mode=True,
    )

    events = [chunk async for chunk in service.stream_chat(req)]

    # Verify event sequence
    event_names = [e.split("\n")[0].replace("event: ", "").strip() for e in events if e.startswith("event: ")]
    assert event_names[0] == "status"     # retrieving
    assert event_names[1] == "citation"   # citations
    assert event_names[2] == "status"     # generating
    assert event_names[3] == "status"     # skill status
    assert event_names[4] == "token"      # token 1
    assert event_names[5] == "token"      # token 2
    assert event_names[6] == "done"       # done
    assert events[-1] == "data: [DONE]\n\n"

    # Verify DB commit was called (user msg commit + assistant msg commit)
    assert mock_db_session.commit.call_count >= 2
    # Verify citations persisted
    assert service.message_repo.add_citations.call_count == 1
    citations_arg = service.message_repo.add_citations.call_args[0][1]
    assert citations_arg[0]["chunk_id"] == chunk_id
    assert citations_arg[0]["similarity"] == 0.85


@pytest.mark.asyncio
async def test_chat_service_abstention_on_empty_retrieval(mock_db_session):
    session_id = uuid.uuid4()
    mock_session = Session(id=session_id, user_id=uuid.uuid4(), title="Test Session")
    mock_session.touch = MagicMock()

    service = ChatService(db=mock_db_session)
    service.session_repo.get_by_id = AsyncMock(return_value=mock_session)

    user_msg = Message(id=uuid.uuid4(), session_id=session_id, role="user", content="How to bake cake?")
    service.message_repo.create = AsyncMock(side_effect=[
        user_msg,
        Message(
            id=uuid.uuid4(),
            session_id=session_id,
            role="assistant",
            content=CANONICAL_ABSTENTION_MESSAGE,
            provider="openai",
            model="gpt-4o-mini",
        ),
    ])
    service.message_repo.list_by_session = AsyncMock(return_value=[user_msg])
    service.message_repo.add_citations = AsyncMock()

    # Out-of-domain: 0 evidence, abstention True
    service.retriever.retrieve = AsyncMock(
        return_value=RetrievalResult.abstain(query="How to bake cake?")
    )

    async def mock_stream_abstention(payload: AgentRequestPayload) -> AsyncGenerator[StreamEventModel, None]:
        yield StreamEventModel(event="token", data={"delta": CANONICAL_ABSTENTION_MESSAGE})
        yield StreamEventModel(
            event="done",
            data={
                "provider": "openai",
                "model": "gpt-4o-mini",
                "tokens": {"prompt": 10, "completion": 20},
                "cost_usd": 0.0,
            },
        )

    service.agent_client.stream_skill = mock_stream_abstention

    req = ChatRequest(
        session_id=session_id,
        message="How to bake cake?",
        mock_mode=True,
    )

    events = [chunk async for chunk in service.stream_chat(req)]
    assert any("event: token" in e and "sufficient evidence" in e for e in events)
    # Citations must not be emitted or persisted for abstentions
    assert service.message_repo.add_citations.call_count == 0


@pytest.mark.asyncio
async def test_chat_service_rollback_on_generation_failure(mock_db_session):
    """
    Gate requirement: interrupted or failed generation must never leave
    a partially completed assistant message in the database.
    """
    session_id = uuid.uuid4()
    mock_session = Session(id=session_id, user_id=uuid.uuid4(), title="Test Session")

    service = ChatService(db=mock_db_session)
    service.session_repo.get_by_id = AsyncMock(return_value=mock_session)

    user_msg = Message(id=uuid.uuid4(), session_id=session_id, role="user", content="Tell me about pricing")
    # Only user message is created; assistant message creation is never reached
    service.message_repo.create = AsyncMock(return_value=user_msg)
    service.message_repo.list_by_session = AsyncMock(return_value=[user_msg])

    service.retriever.retrieve = AsyncMock(
        return_value=RetrievalResult(
            query="Tell me about pricing",
            chunks=[],
            citations=[],
            is_sufficient=False,
            query_latency_ms=5.0,
        )
    )

    # Simulate provider failure midway through streaming
    async def mock_failing_stream(payload: AgentRequestPayload) -> AsyncGenerator[StreamEventModel, None]:
        yield StreamEventModel(event="token", data={"delta": "Pricing is "})
        raise ProviderUnavailableError("ollama", "Local Ollama daemon at http://localhost:11434 dropped connection.")


    service.agent_client.stream_skill = mock_failing_stream

    req = ChatRequest(
        session_id=session_id,
        message="Tell me about pricing",
        provider="ollama",
    )

    events = [chunk async for chunk in service.stream_chat(req)]

    # Check that error event was emitted
    error_event = [e for e in events if "event: error" in e]
    assert len(error_event) == 1
    assert "PROVIDER_UNAVAILABLE" in error_event[0]
    assert "dropped connection" in error_event[0]

    # Verify rollback was called to discard any pending changes
    assert mock_db_session.rollback.call_count >= 1
    # Verify assistant message was NOT created (create called only once for the user message)
    assert service.message_repo.create.call_count == 1

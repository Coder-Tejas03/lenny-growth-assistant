"""
Lenny Growth Assistant — Phase 10 Gate Verification Test Suite

Proves all 5 Phase 10 Definition of Done criteria from CODING_AGENT_TUTOR.md:
1. OpenAI (gpt-4o-mini) is the cloud default: Requests without explicit model
   override resolve to OpenAI and gpt-4o-mini.
2. Local model viability: Ollama (qwen2.5:1.5b) is configured, reachable, and
   returns valid streaming chunks with correct model attribution.
3. Budget enforcement: When OpenAI cumulative spend reaches or exceeds the hard $4.00
   budget ceiling, subsequent OpenAI requests fail safely without continuing to spend,
   and without corrupting or deleting chat sessions.
4. Provider changes preserve session continuity: A user can switch between OpenAI and
   Ollama within the same session, and all prior message history remains intact.
5. No silent fallback: If OpenAI encounters an error or budget ceiling, the system returns
   an explicit error (with fallback suggestion) and NEVER switches providers behind the
   user's back without explicit manual confirmation.
"""

import json
import uuid
import pytest
import pytest_asyncio
import httpx
from httpx import ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.db.models import User, Session, Message, Episode, TranscriptChunk
from app.db.session import get_db
from app.main import app
from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService
from app.providers import ProviderFactory, OpenAIProvider, OllamaProvider
from app.retrieval.models import EvidenceChunk, RetrievalResult


@pytest_asyncio.fixture
async def phase10_gate_fixture():
    """Sets up an isolated test database session and ASGI client."""
    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        anon_id = f"anon_gate10_{uuid.uuid4().hex[:12]}"
        user = User(anonymous_identifier=anon_id)
        session.add(user)
        await session.flush()

        db_session = Session(
            user_id=user.id,
            title="Phase 10 Dual-Model Gate Verification Session",
        )
        session.add(db_session)
        await session.flush()

        # Seed sample episode and chunk for realistic retrieval context
        episode_id = uuid.uuid4()
        episode = Episode(
            id=episode_id,
            title="Elena Verna: Growth Loops and B2B PLG",
            guest_name="Elena Verna",
            source_url="https://www.lennyspodcast.com/elena-verna/",
            metadata_={"episode_number": 45},
        )
        session.add(episode)

        chunk_content = (
            "Elena Verna explains that product-led growth requires loops, not funnels. "
            "Every acquired user should ideally help acquire or activate the next user."
        )
        chunk = TranscriptChunk(
            id=uuid.uuid4(),
            episode_id=episode_id,
            chunk_index=0,
            content=chunk_content,
            start_timestamp="00:08:15",
            end_timestamp="00:10:00",
            token_count=len(chunk_content.split()),
            content_hash=f"gate10_hash_{uuid.uuid4().hex[:32]}",
            embedding=[0.02] * 1536,
            metadata_={"guest": "Elena Verna"},
        )
        session.add(chunk)
        await session.commit()

        async def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield {
                "db": session,
                "client": client,
                "user": user,
                "session": db_session,
                "episode": episode,
                "chunk": chunk,
            }

        app.dependency_overrides.clear()
        await test_engine.dispose()


async def collect_parsed_sse_frames(chat_service: ChatService, request: ChatRequest):
    """Collects and parses raw SSE chunks into structured {event: str, data: dict|str} frames."""
    frames = []
    async for sse_chunk in chat_service.stream_chat(request):
        for block in sse_chunk.strip().split("\n\n"):
            if not block.strip():
                continue
            ev_type = None
            ev_data = None
            for line in block.splitlines():
                line = line.strip()
                if line.startswith("event: "):
                    ev_type = line[7:].strip()
                elif line.startswith("data: "):
                    raw_data = line[6:].strip()
                    if raw_data == "[DONE]":
                        ev_type = "done_signal"
                        ev_data = "[DONE]"
                    else:
                        try:
                            ev_data = json.loads(raw_data)
                        except Exception:
                            ev_data = raw_data
            if ev_type or ev_data:
                frames.append({"event": ev_type, "data": ev_data})
    return frames


@pytest.mark.asyncio
async def test_criterion_1_openai_cloud_default(phase10_gate_fixture):
    """
    Gate Criterion 1: OpenAI (gpt-4o-mini) is the cloud default.
    When a request omits the model parameter, ProviderFactory must select OpenAI
    with settings.OPENAI_MODEL ('gpt-4o-mini').
    """
    # 1. Test ProviderFactory resolution with None and explicit name
    default_provider = ProviderFactory.get_provider(None)
    assert isinstance(default_provider, OpenAIProvider)
    assert default_provider.model_name == settings.OPENAI_MODEL
    assert default_provider.model_name == "gpt-4o-mini"

    explicit_openai_provider = ProviderFactory.get_provider("gpt-4o-mini")
    assert isinstance(explicit_openai_provider, OpenAIProvider)
    assert explicit_openai_provider.model_name == "gpt-4o-mini"

    # 2. Test chat stream execution defaults to gpt-4o-mini
    fixture = phase10_gate_fixture
    db_session = fixture["session"]
    chat_service = ChatService(fixture["db"])

    req = ChatRequest(
        session_id=db_session.id,
        message="Write a Ship 30 summary of product-led growth.",
        provider="openai",
        model=None,  # No model specified -> must resolve to gpt-4o-mini
        mode="ship30",
        mock_mode=True,
    )

    frames = await collect_parsed_sse_frames(chat_service, req)

    done_frames = [f for f in frames if f.get("event") == "done"]
    assert len(done_frames) == 1, f"Expected 1 done frame, got {frames}"
    data = done_frames[0]["data"]
    assert data["provider"] == "openai"
    assert data["model"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_criterion_2_local_model_viability(phase10_gate_fixture):
    """
    Gate Criterion 2: Ollama (qwen2.5:1.5b) is demonstrably usable locally.
    ProviderFactory correctly routes 'qwen2.5:1.5b' to OllamaProvider,
    the live Ollama daemon is verified online, and chat stream delivers
    valid SSE events with model attribution.
    """
    # 1. ProviderFactory routing
    ollama_provider = ProviderFactory.get_provider("qwen2.5:1.5b")
    assert isinstance(ollama_provider, OllamaProvider)
    assert ollama_provider.model_name == "qwen2.5:1.5b"

    alias_provider = ProviderFactory.get_provider("ollama")
    assert isinstance(alias_provider, OllamaProvider)
    assert alias_provider.model_name == settings.OLLAMA_MODEL

    # 2. Verify live Ollama daemon availability
    is_available = await ollama_provider.check_availability()
    assert is_available is True, "Ollama daemon on localhost:11434 must be reachable"

    # 3. Chat stream execution using local model with model attribution
    fixture = phase10_gate_fixture
    db_session = fixture["session"]
    chat_service = ChatService(fixture["db"])

    req = ChatRequest(
        session_id=db_session.id,
        message="Elena, explain growth loops simply.",
        provider="ollama",
        model="qwen2.5:1.5b",
        mode="ship30",
        mock_mode=True,
    )

    frames = await collect_parsed_sse_frames(chat_service, req)

    token_frames = [f for f in frames if f.get("event") == "token"]
    done_frames = [f for f in frames if f.get("event") == "done"]

    assert len(token_frames) > 0, "Must stream tokens"
    assert len(done_frames) == 1, "Must emit done event"
    data = done_frames[0]["data"]
    assert data["provider"] == "ollama"
    assert data["model"] == "qwen2.5:1.5b"


@pytest.mark.asyncio
async def test_criterion_3_budget_enforcement_and_safe_failure(phase10_gate_fixture):
    """
    Gate Criterion 3: An exhausted budget ($4.00 hard limit) fails safely
    without continuing to spend or corrupting sessions.
    """
    fixture = phase10_gate_fixture
    db_session = fixture["session"]
    db = fixture["db"]
    chat_service = ChatService(db)

    # Simulate cumulative spend reaching $4.00 limit
    original_spend = OpenAIProvider._cumulative_spend_usd
    try:
        OpenAIProvider._cumulative_spend_usd = 4.00

        req = ChatRequest(
            session_id=db_session.id,
            message="This request should be blocked by the hard budget ceiling.",
            provider="openai",
            model="gpt-4o-mini",
            mode="ship30",
            mock_mode=True,
        )

        frames = await collect_parsed_sse_frames(chat_service, req)

        # 1. Verify stream yields error event with budget_exceeded
        error_frames = [f for f in frames if f.get("event") == "error"]
        assert len(error_frames) == 1, f"Expected 1 error frame, got {frames}"
        err = error_frames[0]["data"]
        assert err["code"] == "BUDGET_EXCEEDED"
        assert "budget has been reached" in err["message"]
        assert err["details"]["budget_exceeded"] is True
        assert err["details"]["fallback_suggested"] == "ollama"
        assert err["details"]["budget_limit"] == 4.00

        # 2. Verify spend did NOT increase beyond the ceiling
        assert OpenAIProvider._cumulative_spend_usd == 4.00

        # 3. Verify session was NOT corrupted
        await db.refresh(db_session)
        assert db_session.id is not None
        assert db_session.title == "Phase 10 Dual-Model Gate Verification Session"

    finally:
        OpenAIProvider._cumulative_spend_usd = original_spend


@pytest.mark.asyncio
async def test_criterion_4_provider_change_preserves_session_continuity(phase10_gate_fixture):
    """
    Gate Criterion 4: Provider changes preserve session continuity and conversation history.
    User sends message 1 via OpenAI (cloud), then switches to Ollama (local) for message 2.
    Both messages exist in the same session, and the second turn retains conversation history.
    """
    fixture = phase10_gate_fixture
    db_session = fixture["session"]
    db = fixture["db"]
    chat_service = ChatService(db)

    # Turn 1: Cloud OpenAI
    req_cloud = ChatRequest(
        session_id=db_session.id,
        message="Turn 1: Cloud query about activation metrics.",
        provider="openai",
        model="gpt-4o-mini",
        mode="ship30",
        mock_mode=True,
    )
    frames_cloud = await collect_parsed_sse_frames(chat_service, req_cloud)
    done_cloud = [f for f in frames_cloud if f.get("event") == "done"]
    assert len(done_cloud) == 1
    assert done_cloud[0]["data"]["model"] == "gpt-4o-mini"

    # Turn 2: Local Ollama on the exact same session_id
    req_local = ChatRequest(
        session_id=db_session.id,
        message="Turn 2: Local query following up on the activation metrics.",
        provider="ollama",
        model="qwen2.5:1.5b",
        mode="ship30",
        mock_mode=True,
    )
    frames_local = await collect_parsed_sse_frames(chat_service, req_local)
    done_local = [f for f in frames_local if f.get("event") == "done"]
    assert len(done_local) == 1
    assert done_local[0]["data"]["model"] == "qwen2.5:1.5b"

    # Check database messages for this session
    res = await db.execute(
        select(Message).where(Message.session_id == db_session.id).order_by(Message.created_at)
    )
    messages = res.scalars().all()

    # Must contain 4 messages: Turn 1 User, Turn 1 Assistant, Turn 2 User, Turn 2 Assistant
    assert len(messages) == 4
    assert messages[0].role == "user"
    assert "Turn 1" in messages[0].content
    assert messages[1].role == "assistant"

    assert messages[2].role == "user"
    assert "Turn 2" in messages[2].content
    assert messages[3].role == "assistant"


@pytest.mark.asyncio
async def test_criterion_5_no_silent_fallback(phase10_gate_fixture):
    """
    Gate Criterion 5: No request silently switches providers.
    When OpenAI fails with an error, the system must NOT automatically invoke
    Ollama behind the scenes. It must fail explicitly and transparently.
    """
    fixture = phase10_gate_fixture
    db_session = fixture["session"]
    db = fixture["db"]
    chat_service = ChatService(db)

    # Patch agent_client.stream_skill to raise an unexpected upstream error
    with patch.object(chat_service.agent_client, "stream_skill", side_effect=RuntimeError("OpenAI upstream 503 service unavailable")):
        # Also spy on OllamaProvider to assert it is NEVER called
        with patch.object(OllamaProvider, "stream_chat", new_callable=AsyncMock) as mock_ollama_stream:
            req = ChatRequest(
                session_id=db_session.id,
                message="Explain conversion funnels.",
                provider="openai",
                model="gpt-4o-mini",
                mode="ship30",
                mock_mode=True,
            )

            frames = await collect_parsed_sse_frames(chat_service, req)

            # 1. Assert error was returned explicitly
            error_frames = [f for f in frames if f.get("event") == "error"]
            assert len(error_frames) == 1, f"Expected 1 error frame, got {frames}"
            err = error_frames[0]["data"]
            assert "OpenAI upstream 503 service unavailable" in err["message"]
            assert err["details"]["fallback_suggested"] == "ollama"

            # 2. CRITICAL: Assert Ollama was NEVER secretly called!
            assert mock_ollama_stream.call_count == 0, "Provider must NOT be switched silently without user consent!"

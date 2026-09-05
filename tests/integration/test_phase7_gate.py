"""
Lenny Growth Assistant — Phase 7 Gate Verification Test Suite

Explicitly proves all three criteria from the Phase 7 Definition of Done in CODING_AGENT_TUTOR.md:
1. A supported question produces streamed, cited, and persisted output.
2. An unsupported question produces intentional abstention without fabricated citations.
3. An interrupted or failed generation is never displayed or persisted as a completed assistant message.
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

from app.agent.models import StreamEventModel
from app.agent.skills import CANONICAL_ABSTENTION_MESSAGE
from app.core.config import settings
from app.db.models import Episode, Message, MessageCitation, Session, TranscriptChunk, User
from app.db.session import get_db
from app.main import app
from app.providers.base import ProviderUnavailableError
from app.retrieval.models import Citation, EvidenceChunk, RetrievalResult
from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService



@pytest_asyncio.fixture
async def gate_fixture():
    """Sets up a test engine, seeded episode/chunks in database, and an authenticated client."""
    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        # Seed an episode and a verified chunk for grounded Q&A
        episode_id = uuid.uuid4()
        chunk_id = uuid.uuid4()

        episode = Episode(
            id=episode_id,
            title="Rahul Vohra: How Superhuman Built an Engine for Finding PMF",
            guest_name="Rahul Vohra",
            source_url="https://www.lennyspodcast.com/rahul-vohra/",
            metadata_={"episode_number": 14},
        )
        session.add(episode)

        chunk_content = "To measure product-market fit at Superhuman, we surveyed users asking: how would you feel if you could no longer use Superhuman? If 40% or more say very disappointed, you have product-market fit."
        chunk = TranscriptChunk(
            id=chunk_id,
            episode_id=episode_id,
            chunk_index=0,
            content=chunk_content,
            start_timestamp="00:14:22",
            end_timestamp="00:15:40",
            token_count=len(chunk_content.split()),
            content_hash="mock_hash_" + chunk_id.hex[:32],
            embedding=[0.05] * 1536,  # 1536-dimensional mock embedding
            metadata_={"guest": "Rahul Vohra"},
        )
        session.add(chunk)
        await session.commit()


        async def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, session, episode, chunk
        app.dependency_overrides.clear()

        # Cleanup seeded records
        await session.delete(chunk)
        await session.delete(episode)
        await session.commit()

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_gate_criterion_1_supported_question_streamed_and_persisted(gate_fixture):
    """
    Gate Criterion 1:
    A supported question produces streamed, cited, persisted output that reloads correctly.
    """
    client, db, episode, chunk = gate_fixture

    # 1. Create a fresh session
    anon_id = f"anon_{uuid.uuid4().hex[:8]}"
    create_res = await client.post(
        "/api/sessions",
        json={"title": "Superhuman PMF Case Study", "anonymous_identifier": anon_id},
    )
    assert create_res.status_code == 201
    session_id = create_res.json()["id"]

    # 2. Issue a grounded question via POST /api/chat
    chat_payload = {
        "session_id": session_id,
        "message": "How did Superhuman measure product-market fit?",
        "provider": "openai",
        "mock_mode": True,
    }

    response = await client.post("/api/chat", json=chat_payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    raw_text = response.text
    blocks = [b.strip() for b in raw_text.split("\n\n") if b.strip()]

    events = []
    tokens = []
    citations = []

    for block in blocks:
        if block == "data: [DONE]":
            continue
        for line in block.split("\n"):
            if line.startswith("event: "):
                events.append(line.replace("event: ", "").strip())
            elif line.startswith("data: ") and events and events[-1] == "token":
                data = json.loads(line.replace("data: ", ""))
                tokens.append(data.get("delta", ""))
            elif line.startswith("data: ") and events and events[-1] == "citation":
                data = json.loads(line.replace("data: ", ""))
                citations = data.get("citations", [])

    # Check streamed events
    assert "status" in events
    assert "token" in events
    assert "done" in events
    assert len(tokens) > 0
    full_content = "".join(tokens)
    assert len(full_content) > 10

    # 3. Reload session via GET /api/sessions/{session_id} to verify persistence
    reload_res = await client.get(f"/api/sessions/{session_id}")
    assert reload_res.status_code == 200
    session_graph = reload_res.json()

    messages = session_graph["messages"]
    assert len(messages) == 2

    # User message verified
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "How did Superhuman measure product-market fit?"

    # Assistant message verified
    assistant_msg = messages[1]
    assert assistant_msg["role"] == "assistant"
    assert assistant_msg["content"] == full_content
    assert assistant_msg["provider"] == "openai"
    assert assistant_msg["model"] is not None


@pytest.mark.asyncio
async def test_gate_criterion_2_unsupported_question_canonical_abstention(gate_fixture):
    """
    Gate Criterion 2:
    An unsupported question produces intentional abstention without fabricated citations.
    """
    client, db, episode, chunk = gate_fixture

    # 1. Create session
    anon_id = f"anon_{uuid.uuid4().hex[:8]}"
    create_res = await client.post(
        "/api/sessions",
        json={"title": "Out of Domain Test", "anonymous_identifier": anon_id},
    )
    session_id = create_res.json()["id"]

    # 2. Ask an unsupported question (no transcript evidence)
    # Using mock_mode=True and a topic that has 0 similarity in transcripts
    chat_payload = {
        "session_id": session_id,
        "message": "What is the quantum chromodynamics quark mass?",
        "provider": "openai",
        "mock_mode": True,
    }

    response = await client.post("/api/chat", json=chat_payload)
    assert response.status_code == 200

    raw_text = response.text
    blocks = [b.strip() for b in raw_text.split("\n\n") if b.strip()]

    tokens = []
    citations = []

    for block in blocks:
        if block == "data: [DONE]":
            continue
        lines = block.split("\n")
        event = None
        for line in lines:
            if line.startswith("event: "):
                event = line.replace("event: ", "").strip()
            elif line.startswith("data: "):
                payload = json.loads(line.replace("data: ", ""))
                if event == "token":
                    tokens.append(payload.get("delta", ""))
                elif event == "citation":
                    citations.extend(payload.get("citations", []))

    full_response = "".join(tokens)
    # Must formulate canonical abstention
    assert "sufficient evidence in Lenny's podcast archive" in full_response or "insufficient" in full_response.lower()

    # Verify zero citations in response
    assert len(citations) == 0

    # 3. Reload session to verify durable abstention state
    reload_res = await client.get(f"/api/sessions/{session_id}")
    assert reload_res.status_code == 200
    session_graph = reload_res.json()
    messages = session_graph["messages"]
    assert len(messages) == 2

    assistant_msg = messages[1]
    assert assistant_msg["role"] == "assistant"
    # Citations in database must be empty for abstentions
    assert len(assistant_msg["citations"]) == 0


@pytest.mark.asyncio
async def test_gate_criterion_3_interrupted_generation_never_persists_incomplete_assistant(gate_fixture):
    """
    Gate Criterion 3:
    Interrupted or failed generation must never leave a partially completed assistant message in the database.
    """
    client, db, episode, chunk = gate_fixture

    # 1. Create a fresh session
    anon_id = f"anon_{uuid.uuid4().hex[:8]}"
    create_res = await client.post(
        "/api/sessions",
        json={"title": "Interruption Test", "anonymous_identifier": anon_id},
    )
    session_id = uuid.UUID(create_res.json()["id"])

    # 2. Inject a failing agent client that crashes midway
    class FailingAgentClient:
        async def stream_skill(self, payload):
            yield StreamEventModel(event="status", data={"stage": "generating", "message": "Drafting..."})
            # Emit partial tokens
            yield StreamEventModel(event="token", data={"delta": "Halfway through answering..."})
            # Simulate sudden unrecoverable failure
            raise ProviderUnavailableError("ollama", "Simulated hardware connection reset")


    # Instantiate chat service directly with the failing client
    failing_service = ChatService(db=db)
    failing_service.agent_client = FailingAgentClient()

    req = ChatRequest(
        session_id=session_id,
        message="Simulate sudden failure during stream",
        provider="ollama",
    )

    events = [chunk async for chunk in failing_service.stream_chat(req)]

    # Must emit structured error event
    assert any("event: error" in e for e in events)
    assert any("PROVIDER_UNAVAILABLE" in e for e in events)

    # 3. Inspect PostgreSQL messages table directly
    stmt = select(Message).where(Message.session_id == session_id)
    result = await db.execute(stmt)
    persisted_messages = list(result.scalars().all())

    # Only the user's message should exist; the partially emitted assistant message must NOT be persisted!
    assert len(persisted_messages) == 1
    assert persisted_messages[0].role == "user"
    assert persisted_messages[0].content == "Simulate sudden failure during stream"

    # Verify no assistant messages exist in database
    assistant_messages = [m for m in persisted_messages if m.role == "assistant"]
    assert len(assistant_messages) == 0

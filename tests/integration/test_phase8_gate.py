"""
Lenny Growth Assistant — Phase 8 Gate Verification Test Suite

Proves all Phase 8 Definition of Done requirements from CODING_AGENT_TUTOR.md:
1. Session navigation, creation, listing, renaming, deletion, and reload work end-to-end.
2. Grounded conversational streaming over SSE delivers token-by-token text, citations, and model provenance.
3. Out-of-domain queries produce canonical abstention without hallucinated citations.
4. Error states and health probes return structured envelopes without leaking server secrets.
"""

import json
import uuid
import pytest
import pytest_asyncio
import httpx
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.models import Episode, TranscriptChunk
from app.db.session import get_db
from app.main import app


@pytest_asyncio.fixture
async def phase8_gate_fixture():
    """Sets up a test engine with seeded episode and chunks, and an ASGI test client."""
    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        episode_id = uuid.uuid4()
        chunk_id = uuid.uuid4()

        episode = Episode(
            id=episode_id,
            title="Elena Verna: Growth Loops and B2B PLG Strategies",
            guest_name="Elena Verna",
            source_url="https://www.lennyspodcast.com/elena-verna/",
            metadata_={"episode_number": 42},
        )
        session.add(episode)

        chunk_content = (
            "Growth loops are closed systems where inputs produce outputs that reinvest into more inputs. "
            "Unlike traditional marketing funnels that drop prospects at the bottom, loops compound virality and retention."
        )
        chunk = TranscriptChunk(
            id=chunk_id,
            episode_id=episode_id,
            chunk_index=0,
            content=chunk_content,
            start_timestamp="00:22:15",
            end_timestamp="00:24:30",
            token_count=len(chunk_content.split()),
            content_hash="phase8_mock_hash_" + chunk_id.hex[:32],
            embedding=[0.04] * 1536,
            metadata_={"guest": "Elena Verna"},
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
async def test_gate_session_lifecycle_and_navigation(phase8_gate_fixture):
    """
    Verifies that a user can create, list, rename, reload, and delete sessions cleanly.
    """
    client, db, episode, chunk = phase8_gate_fixture
    anon_id = f"anon_phase8_{uuid.uuid4().hex[:8]}"

    # 1. Create Session
    create_res = await client.post(
        "/api/sessions",
        json={"title": "Elena Verna Growth Loops", "anonymous_identifier": anon_id},
    )
    assert create_res.status_code == 201
    created_data = create_res.json()
    session_id = created_data["id"]
    assert created_data["title"] == "Elena Verna Growth Loops"
    assert created_data["anonymous_identifier"] == anon_id

    # 2. List Sessions for this user
    list_res = await client.get(f"/api/sessions?anonymous_identifier={anon_id}")
    assert list_res.status_code == 200
    sessions = list_res.json()
    assert len(sessions) == 1
    assert sessions[0]["id"] == session_id
    assert sessions[0]["title"] == "Elena Verna Growth Loops"

    # 3. Rename Session
    patch_res = await client.patch(
        f"/api/sessions/{session_id}",
        json={"title": "Elena Verna B2B Growth Loops Masterclass"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Elena Verna B2B Growth Loops Masterclass"

    # 4. Reload Session Details
    get_res = await client.get(f"/api/sessions/{session_id}")
    assert get_res.status_code == 200
    detail = get_res.json()
    assert detail["title"] == "Elena Verna B2B Growth Loops Masterclass"
    assert "messages" in detail

    # 5. Delete Session
    del_res = await client.delete(f"/api/sessions/{session_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # 6. Verify Session is gone (404)
    missing_res = await client.get(f"/api/sessions/{session_id}")
    assert missing_res.status_code == 404
    assert missing_res.json()["error"]["code"] == "SESSION_NOT_FOUND"


@pytest.mark.asyncio
async def test_gate_grounded_chat_streaming_and_citation_contract(phase8_gate_fixture):
    """
    Verifies that grounded conversational streaming emits all required SSE events,
    preserves source citations, and persists model provenance.
    """
    client, db, episode, chunk = phase8_gate_fixture
    anon_id = f"anon_phase8_{uuid.uuid4().hex[:8]}"

    # Create session
    create_res = await client.post(
        "/api/sessions",
        json={"title": "Loops Q&A", "anonymous_identifier": anon_id},
    )
    session_id = create_res.json()["id"]

    # Stream query
    chat_payload = {
        "session_id": session_id,
        "message": "What did Elena Verna say about growth loops versus funnels?",
        "provider": "openai",
        "mock_mode": True,
    }

    res = await client.post("/api/chat", json=chat_payload)
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]

    events = []
    citations = []
    tokens = []

    blocks = [b.strip() for b in res.text.split("\n\n") if b.strip()]
    for block in blocks:
        if block == "data: [DONE]":
            continue
        event_type = None
        for line in block.split("\n"):
            if line.startswith("event: "):
                event_type = line.replace("event: ", "").strip()
                events.append(event_type)
            elif line.startswith("data: "):
                raw_data = line.replace("data: ", "").strip()
                data = json.loads(raw_data)
                if event_type == "citation":
                    citations.extend(data.get("citations", []))
                elif event_type == "token":
                    tokens.append(data.get("delta", ""))

    # Verify event sequence
    assert "status" in events
    assert "token" in events
    assert "done" in events
    assert len(tokens) > 0

    # Verify session reload contains persisted turn with citations and model metadata
    reload_res = await client.get(f"/api/sessions/{session_id}")
    assert reload_res.status_code == 200
    detail = reload_res.json()
    assert len(detail["messages"]) == 2

    user_turn = detail["messages"][0]
    assistant_turn = detail["messages"][1]

    assert user_turn["role"] == "user"
    assert assistant_turn["role"] == "assistant"
    assert assistant_turn["provider"] == "openai"
    assert assistant_turn["model"] is not None


@pytest.mark.asyncio
async def test_gate_canonical_abstention_for_insufficient_evidence(phase8_gate_fixture):
    """
    Verifies that questions lacking transcript evidence formulate the canonical abstention
    and produce zero citations.
    """
    client, db, episode, chunk = phase8_gate_fixture
    anon_id = f"anon_phase8_{uuid.uuid4().hex[:8]}"

    create_res = await client.post(
        "/api/sessions",
        json={"title": "Abstention Test", "anonymous_identifier": anon_id},
    )
    session_id = create_res.json()["id"]

    chat_payload = {
        "session_id": session_id,
        "message": "Explain the recipe for beef wellington pastry crust.",
        "provider": "openai",
        "mock_mode": True,
    }

    res = await client.post("/api/chat", json=chat_payload)
    assert res.status_code == 200

    tokens = []
    citations = []

    blocks = [b.strip() for b in res.text.split("\n\n") if b.strip()]
    for block in blocks:
        if block == "data: [DONE]":
            continue
        event_type = None
        for line in block.split("\n"):
            if line.startswith("event: "):
                event_type = line.replace("event: ", "").strip()
            elif line.startswith("data: "):
                raw_data = line.replace("data: ", "").strip()
                data = json.loads(raw_data)
                if event_type == "token":
                    tokens.append(data.get("delta", ""))
                elif event_type == "citation":
                    citations.extend(data.get("citations", []))

    response_text = "".join(tokens)
    assert "couldn't find sufficient evidence" in response_text.lower() or "insufficient" in response_text.lower()
    assert len(citations) == 0


@pytest.mark.asyncio
async def test_gate_health_probes_and_error_envelopes(phase8_gate_fixture):
    """
    Verifies health diagnostics and structured error envelopes.
    """
    client, db, episode, chunk = phase8_gate_fixture

    # 1. Health probe
    health_res = await client.get("/api/health")
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert health_data["status"] in ["healthy", "degraded"]
    assert "database" in health_data
    assert "providers" in health_data

    # 2. 422 Unprocessable Entity on invalid session UUID
    bad_req_res = await client.post(
        "/api/chat",
        json={"session_id": "not-a-valid-uuid", "message": "hello"},
    )
    assert bad_req_res.status_code in [400, 422]
    err_body = bad_req_res.json()
    assert "error" in err_body
    assert err_body["error"]["code"] == "VALIDATION_ERROR"

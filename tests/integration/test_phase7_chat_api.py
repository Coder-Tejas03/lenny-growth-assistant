"""
Lenny Growth Assistant — Chat API Streaming Integration Tests (Phase 7)

Verifies:
- POST /api/chat and POST /chat streaming SSE with text/event-stream
- Anti-buffering HTTP headers (Cache-Control, X-Accel-Buffering)
- Event sequence parsing over ASGI transport
- End-to-end conversation persistence and reload via GET /api/sessions/{id}
- Structured validation error handling for malformed requests
- Nonexistent session error handling over SSE
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
from app.db.session import get_db
from app.main import app


@pytest_asyncio.fixture
async def client_and_session():
    """Yields an httpx test client alongside direct async database access sharing the connection."""
    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        async def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, session
        app.dependency_overrides.clear()

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_post_chat_stream_headers_and_status(client_and_session):
    client, _ = client_and_session

    # 1. Create a session first
    create_res = await client.post(
        "/api/sessions",
        json={"title": "PMF Discussion", "anonymous_identifier": f"anon_{uuid.uuid4().hex[:8]}"},
    )
    assert create_res.status_code == 201
    session_id = create_res.json()["id"]

    # 2. Call POST /api/chat
    chat_payload = {
        "session_id": session_id,
        "message": "What is product-market fit according to Lenny's guests?",
        "provider": "openai",
        "mock_mode": True,
    }

    response = await client.post("/api/chat", json=chat_payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "no-cache" in response.headers["cache-control"]
    assert response.headers.get("x-accel-buffering") == "no"

    body_text = response.text
    assert "event: status" in body_text
    assert "data: [DONE]" in body_text


@pytest.mark.asyncio
async def test_post_chat_alias_route(client_and_session):
    client, _ = client_and_session

    # Create session
    create_res = await client.post(
        "/api/sessions",
        json={"title": "Alias Test", "anonymous_identifier": f"anon_{uuid.uuid4().hex[:8]}"},
    )
    session_id = create_res.json()["id"]

    # Test alias route POST /chat
    response = await client.post(
        "/chat",
        json={
            "session_id": session_id,
            "message": "How to scale retention?",
            "provider": "openai",
            "mock_mode": True,
        },
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "data: [DONE]" in response.text


@pytest.mark.asyncio
async def test_post_chat_stream_events_parsed(client_and_session):
    client, _ = client_and_session

    create_res = await client.post(
        "/api/sessions",
        json={"title": "Parsing Test", "anonymous_identifier": f"anon_{uuid.uuid4().hex[:8]}"},
    )
    session_id = create_res.json()["id"]

    response = await client.post(
        "/api/chat",
        json={
            "session_id": session_id,
            "message": "Explain activation metrics",
            "provider": "openai",
            "mock_mode": True,
        },
    )
    assert response.status_code == 200

    raw_stream = response.text
    blocks = [b.strip() for b in raw_stream.split("\n\n") if b.strip()]

    events_received = []
    tokens = []

    for block in blocks:
        if block == "data: [DONE]":
            events_received.append("[DONE]")
            continue

        lines = block.split("\n")
        event_name = None
        data_content = None

        for line in lines:
            if line.startswith("event: "):
                event_name = line.replace("event: ", "").strip()
            elif line.startswith("data: "):
                data_content = line.replace("data: ", "").strip()

        if event_name:
            events_received.append(event_name)
            if event_name == "token" and data_content:
                parsed_data = json.loads(data_content)
                tokens.append(parsed_data.get("delta", ""))

    assert "status" in events_received
    assert "token" in events_received
    assert "done" in events_received
    assert "[DONE]" in events_received
    assert len(tokens) > 0


@pytest.mark.asyncio
async def test_post_chat_persists_messages_and_reload(client_and_session):
    client, _ = client_and_session

    create_res = await client.post(
        "/api/sessions",
        json={"title": "Persistence Test", "anonymous_identifier": f"anon_{uuid.uuid4().hex[:8]}"},
    )
    session_id = create_res.json()["id"]

    query_text = "What did Rahul Vohra say about PMF survey?"
    chat_res = await client.post(
        "/api/chat",
        json={
            "session_id": session_id,
            "message": query_text,
            "provider": "openai",
            "mock_mode": True,
        },
    )
    assert chat_res.status_code == 200

    # Reload session via GET /api/sessions/{session_id}
    reload_res = await client.get(f"/api/sessions/{session_id}")
    assert reload_res.status_code == 200
    detail = reload_res.json()

    messages = detail["messages"]
    assert len(messages) == 2

    # 1st message is user
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == query_text

    # 2nd message is assistant
    assert messages[1]["role"] == "assistant"
    assert len(messages[1]["content"]) > 0
    assert messages[1]["provider"] == "openai"
    assert messages[1]["model"] is not None


@pytest.mark.asyncio
async def test_post_chat_invalid_payload(client_and_session):
    client, _ = client_and_session

    # Empty query must fail with structured 400/422 validation envelope
    res = await client.post(
        "/api/chat",
        json={"session_id": str(uuid.uuid4()), "message": "   "},
    )
    assert res.status_code in (400, 422)
    err_json = res.json()
    assert "error" in err_json
    assert err_json["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_post_chat_nonexistent_session_sse_error(client_and_session):
    client, _ = client_and_session

    random_id = str(uuid.uuid4())
    res = await client.post(
        "/api/chat",
        json={"session_id": random_id, "message": "Hello?"},
    )
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]
    assert "SESSION_NOT_FOUND" in res.text

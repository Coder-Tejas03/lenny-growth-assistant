"""
Lenny Growth Assistant — Sessions API Integration Tests (Phase 6 Gate)

Verifies:
- Anonymous user creation and idempotency
- Independent session lifecycle (CRUD)
- Session isolation between distinct anonymous users
- Full graph reload (messages, citations, artifacts)
- Structured 4xx responses for invalid payloads and missing resources
"""

import uuid
import pytest
import pytest_asyncio
import httpx
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.repositories import (
    ArtifactRepository,
    CorpusRepository,
    MessageRepository,
    SessionRepository,
    UserRepository,
)
from app.db.session import get_db
from app.main import app


@pytest_asyncio.fixture
async def client_and_repos():
    """Yields an httpx test client alongside direct repository access sharing the same session."""
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
async def test_create_session_success(client_and_repos):
    client, db = client_and_repos
    anon_id = f"anon_{uuid.uuid4().hex[:8]}"

    payload = {
        "title": "Onboarding & Retention Discussion",
        "anonymous_identifier": anon_id,
    }
    response = await client.post("/api/sessions", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert "id" in data
    assert data["title"] == "Onboarding & Retention Discussion"
    assert data["anonymous_identifier"] == anon_id
    assert "created_at" in data
    assert "updated_at" in data

    # Verify user was created in DB
    user_repo = UserRepository(db)
    user = await user_repo.get_by_anonymous_identifier(anon_id)
    assert user is not None
    assert user.anonymous_identifier == anon_id


@pytest.mark.asyncio
async def test_create_session_idempotent_user(client_and_repos):
    client, _ = client_and_repos
    anon_id = f"anon_shared_{uuid.uuid4().hex[:8]}"

    # Create first session
    res1 = await client.post(
        "/api/sessions",
        json={"title": "Session 1", "anonymous_identifier": anon_id},
    )
    assert res1.status_code == 201

    # Create second session for same anonymous user
    res2 = await client.post(
        "/api/sessions",
        json={"title": "Session 2", "anonymous_identifier": anon_id},
    )
    assert res2.status_code == 201

    # Both sessions should have unique IDs
    assert res1.json()["id"] != res2.json()["id"]
    assert res1.json()["anonymous_identifier"] == anon_id
    assert res2.json()["anonymous_identifier"] == anon_id


@pytest.mark.asyncio
async def test_create_session_default_title(client_and_repos):
    client, _ = client_and_repos
    anon_id = f"anon_default_{uuid.uuid4().hex[:8]}"

    response = await client.post(
        "/api/sessions",
        json={"anonymous_identifier": anon_id},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "New Conversation"


@pytest.mark.asyncio
async def test_create_session_validation_failure_empty_identifier(client_and_repos):
    client, _ = client_and_repos
    response = await client.post(
        "/api/sessions",
        json={"anonymous_identifier": ""},
    )
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "validation_errors" in data["error"]["details"]


@pytest.mark.asyncio
async def test_create_session_validation_failure_missing_body(client_and_repos):
    client, _ = client_and_repos
    response = await client.post("/api/sessions", json={})
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_list_sessions_and_isolation(client_and_repos):
    client, _ = client_and_repos
    user_a = f"user_a_{uuid.uuid4().hex[:8]}"
    user_b = f"user_b_{uuid.uuid4().hex[:8]}"

    # Create 2 sessions for User A
    s1 = await client.post("/api/sessions", json={"title": "A1", "anonymous_identifier": user_a})
    s2 = await client.post("/api/sessions", json={"title": "A2", "anonymous_identifier": user_a})

    # Create 1 session for User B
    s3 = await client.post("/api/sessions", json={"title": "B1", "anonymous_identifier": user_b})

    # Query User A sessions
    res_a = await client.get(f"/api/sessions?anonymous_identifier={user_a}")
    assert res_a.status_code == 200
    list_a = res_a.json()
    assert len(list_a) == 2
    ids_a = {item["id"] for item in list_a}
    assert s1.json()["id"] in ids_a
    assert s2.json()["id"] in ids_a
    assert s3.json()["id"] not in ids_a  # User B's session isolated!

    # Query User B sessions
    res_b = await client.get(f"/api/sessions?anonymous_identifier={user_b}")
    assert res_b.status_code == 200
    list_b = res_b.json()
    assert len(list_b) == 1
    assert list_b[0]["id"] == s3.json()["id"]

    # Query unknown user -> returns empty list
    res_empty = await client.get("/api/sessions?anonymous_identifier=nonexistent_user")
    assert res_empty.status_code == 200
    assert res_empty.json() == []


@pytest.mark.asyncio
async def test_get_session_not_found(client_and_repos):
    client, _ = client_and_repos
    fake_uuid = str(uuid.uuid4())
    response = await client.get(f"/api/sessions/{fake_uuid}")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "SESSION_NOT_FOUND"
    assert fake_uuid in data["error"]["message"]


@pytest.mark.asyncio
async def test_get_session_invalid_uuid(client_and_repos):
    client, _ = client_and_repos
    response = await client.get("/api/sessions/not-a-valid-uuid")
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_get_session_with_full_history(client_and_repos):
    client, db = client_and_repos
    anon_id = f"anon_history_{uuid.uuid4().hex[:8]}"

    # Create session via API
    create_res = await client.post(
        "/api/sessions",
        json={"title": "Superhuman PMF Chat", "anonymous_identifier": anon_id},
    )
    session_id = uuid.UUID(create_res.json()["id"])

    # Populate message, citation, and artifact directly in database
    msg_repo = MessageRepository(db)
    corpus_repo = CorpusRepository(db)
    artifact_repo = ArtifactRepository(db)

    ep = await corpus_repo.create_or_get_episode(
        title="Rahul Vohra on Superhuman",
        guest_name="Rahul Vohra",
        source_url="https://lennyspodcast.com/rahul",
    )
    chunk, _ = await corpus_repo.upsert_chunk(
        episode_id=ep.id,
        chunk_index=0,
        content="Superhuman asked how disappointed users would be if product vanished.",
        token_count=12,
        content_hash=f"hash_{uuid.uuid4().hex[:8]}",
        embedding=[0.05] * 1536,
        start_timestamp="14:22",
    )

    # 1. User Message
    await msg_repo.create(
        session_id=session_id,
        role="user",
        content="How did Rahul Vohra measure PMF?",
    )

    # 2. Assistant Message with Citation
    asst_msg = await msg_repo.create(
        session_id=session_id,
        role="assistant",
        content="Rahul Vohra used the Sean Ellis metric at Superhuman.",
        provider="openai",
        model="gpt-4o-mini",
        tokens_prompt=300,
        tokens_completion=80,
        cost_usd=0.00015,
    )
    await msg_repo.add_citations(
        asst_msg.id,
        [{"chunk_id": chunk.id, "rank": 1, "similarity": 0.91}],
    )

    # 3. Artifact
    await artifact_repo.create(
        session_id=session_id,
        type="markdown",
        title="Superhuman PMF Engine",
        content="# The PMF Engine\n\n40% threshold...",
        message_id=asst_msg.id,
    )
    await db.commit()

    # Query GET /api/sessions/{session_id} via API
    response = await client.get(f"/api/sessions/{session_id}")
    assert response.status_code == 200
    detail = response.json()

    assert detail["id"] == str(session_id)
    assert detail["title"] == "Superhuman PMF Chat"
    assert len(detail["messages"]) == 2

    # User message verification
    assert detail["messages"][0]["role"] == "user"
    assert detail["messages"][0]["content"] == "How did Rahul Vohra measure PMF?"

    # Assistant message and citation verification
    asst_data = detail["messages"][1]
    assert asst_data["role"] == "assistant"
    assert asst_data["provider"] == "openai"
    assert asst_data["model"] == "gpt-4o-mini"
    assert asst_data["cost_usd"] == 0.00015
    assert len(asst_data["citations"]) == 1

    citation = asst_data["citations"][0]
    assert citation["chunk_id"] == str(chunk.id)
    assert citation["episode_title"] == "Rahul Vohra on Superhuman"
    assert citation["guest_name"] == "Rahul Vohra"
    assert citation["timestamp"] == "14:22"
    assert citation["similarity"] == 0.91

    # Artifact verification
    assert len(detail["artifacts"]) == 1
    artifact = detail["artifacts"][0]
    assert artifact["type"] == "markdown"
    assert artifact["title"] == "Superhuman PMF Engine"
    assert "40% threshold" in artifact["content"]


@pytest.mark.asyncio
async def test_update_session_title(client_and_repos):
    client, _ = client_and_repos
    anon_id = f"anon_update_{uuid.uuid4().hex[:8]}"

    create_res = await client.post(
        "/api/sessions",
        json={"title": "Original Title", "anonymous_identifier": anon_id},
    )
    session_id = create_res.json()["id"]

    # Update title
    update_res = await client.patch(
        f"/api/sessions/{session_id}",
        json={"title": "Updated Brand New Title"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Updated Brand New Title"

    # Verify updated title persists on reload
    get_res = await client.get(f"/api/sessions/{session_id}")
    assert get_res.json()["title"] == "Updated Brand New Title"


@pytest.mark.asyncio
async def test_delete_session(client_and_repos):
    client, _ = client_and_repos
    anon_id = f"anon_del_{uuid.uuid4().hex[:8]}"

    create_res = await client.post(
        "/api/sessions",
        json={"title": "To Be Deleted", "anonymous_identifier": anon_id},
    )
    session_id = create_res.json()["id"]

    # Delete session
    del_res = await client.delete(f"/api/sessions/{session_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Subsequent GET returns 404
    get_res = await client.get(f"/api/sessions/{session_id}")
    assert get_res.status_code == 404
    assert get_res.json()["error"]["code"] == "SESSION_NOT_FOUND"

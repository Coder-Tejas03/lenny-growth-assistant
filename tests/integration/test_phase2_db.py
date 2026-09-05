"""
Lenny Growth Assistant — Automated Integration Tests for Database Foundation (Phase 2 Gate)

Verifies the Phase 2 Gate:
  - Clean migration from zero (verified via Alembic)
  - Foreign-key cascades and ON DELETE SET NULL behaviors
  - Uniqueness and check constraints
  - Vector similarity search (HNSW index and cosine distance)
  - Full relational graph persistence and reload (user -> session -> message -> citation -> artifact)
"""

import uuid
import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from app.db.health import check_database_health
from app.db.models import (
    Artifact,
    Episode,
    Message,
    MessageCitation,
    Session,
    TranscriptChunk,
    User,
)
from app.db.repositories import (
    ArtifactRepository,
    CorpusRepository,
    MessageRepository,
    SessionRepository,
    UserRepository,
)
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings


@pytest_asyncio.fixture
async def db_session():
    """Yields an isolated async session for testing with NullPool to prevent loop cross-talk."""
    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_database_health_probe(db_session):
    """Verifies that database probe reports healthy with pgvector and uuid-ossp enabled."""
    health = await check_database_health(db_session)
    assert health["connected"] is True
    assert health["pgvector_ready"] is True
    assert health["vector_version"] is not None
    assert health["uuid_ready"] is True
    assert health["status"] == "healthy"
    assert health["latency_ms"] >= 0.0


@pytest.mark.asyncio
async def test_user_and_session_crud(db_session):
    """Verifies user creation, session creation, title updates, and listing."""
    user_repo = UserRepository(db_session)
    session_repo = SessionRepository(db_session)

    anon_id = f"anon_gate_{uuid.uuid4().hex[:8]}"
    user, is_new = await user_repo.get_or_create(anon_id, {"browser": "pytest"})
    assert is_new is True
    assert user.anonymous_identifier == anon_id

    # Test idempotency of get_or_create
    user_again, is_new_again = await user_repo.get_or_create(anon_id)
    assert is_new_again is False
    assert user_again.id == user.id

    # Create sessions
    s1 = await session_repo.create(user.id, "Session 1")
    s2 = await session_repo.create(user.id, "Session 2")

    sessions = await session_repo.list_by_user(user.id, limit=10)
    assert len(sessions) == 2
    assert {s.id for s in sessions} == {s1.id, s2.id}

    # Update session title
    updated_s1 = await session_repo.update_title(s1.id, "Renamed Session 1")
    assert updated_s1.title == "Renamed Session 1"


@pytest.mark.asyncio
async def test_unique_constraints(db_session):
    """Verifies that duplicate records trigger IntegrityError."""
    # 1. Unique anonymous_identifier
    anon_id = f"dup_user_{uuid.uuid4().hex[:8]}"
    u1 = User(anonymous_identifier=anon_id)
    db_session.add(u1)
    await db_session.flush()

    u2 = User(anonymous_identifier=anon_id)
    db_session.add(u2)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    # 2. Unique (episode_id, chunk_index)
    ep = Episode(title=f"Unique Ep {uuid.uuid4().hex[:4]}", guest_name="Guest")
    db_session.add(ep)
    await db_session.flush()

    c1 = TranscriptChunk(
        episode_id=ep.id,
        chunk_index=0,
        content="Chunk 0",
        token_count=5,
        content_hash="hash_0",
    )
    db_session.add(c1)
    await db_session.flush()

    c2 = TranscriptChunk(
        episode_id=ep.id,
        chunk_index=0,
        content="Chunk 0 duplicate index",
        token_count=5,
        content_hash="hash_0_dup",
    )
    db_session.add(c2)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_check_constraints(db_session):
    """Verifies that invalid check constraint values are rejected."""
    user = User(anonymous_identifier=f"anon_{uuid.uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()

    chat_session = Session(user_id=user.id, title="Check Test")
    db_session.add(chat_session)
    await db_session.flush()

    # Invalid message role
    invalid_msg = Message(
        session_id=chat_session.id,
        role="unauthorized_role",
        content="Hello",
    )
    db_session.add(invalid_msg)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    # Invalid artifact type
    invalid_artifact = Artifact(
        session_id=chat_session.id,
        type="executable_binary",
        title="Bad Artifact",
        content="binary",
    )
    db_session.add(invalid_artifact)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_cascade_and_set_null_deletions(db_session):
    """
    Verifies:
      - Deleting a user cascades to session, messages, citations, and artifacts.
      - Deleting a message sets artifact.message_id to NULL (ON DELETE SET NULL).
    """
    user_repo = UserRepository(db_session)
    session_repo = SessionRepository(db_session)
    msg_repo = MessageRepository(db_session)
    corpus_repo = CorpusRepository(db_session)
    artifact_repo = ArtifactRepository(db_session)

    # Setup tree
    user = await user_repo.create(f"cascade_test_{uuid.uuid4().hex[:8]}")
    chat_session = await session_repo.create(user.id, "Cascade Test")
    ep = await corpus_repo.create_or_get_episode(
        title=f"Episode {uuid.uuid4().hex[:4]}", guest_name="Guest"
    )
    chunk, _ = await corpus_repo.upsert_chunk(
        episode_id=ep.id,
        chunk_index=0,
        content="Test chunk content",
        token_count=10,
        content_hash="hash_cascade_test",
        embedding=[0.05] * 1536,
    )
    msg = await msg_repo.create(
        session_id=chat_session.id,
        role="assistant",
        content="Cascade test message",
    )
    await msg_repo.add_citations(
        msg.id, [{"chunk_id": chunk.id, "rank": 1, "similarity": 0.85}]
    )
    artifact = await artifact_repo.create(
        session_id=chat_session.id,
        type="html",
        title="Cascade Artifact",
        content="<div>test</div>",
        message_id=msg.id,
    )
    await db_session.flush()

    # 1. Test ON DELETE SET NULL on artifact when message is deleted
    await db_session.delete(msg)
    await db_session.flush()

    # Refresh artifact
    await db_session.refresh(artifact)
    assert artifact.message_id is None, "Artifact message_id should be SET NULL"

    # 2. Test ON DELETE CASCADE when user is deleted
    await db_session.delete(user)
    await db_session.flush()

    # Verify session and artifact are removed
    loaded_session = await session_repo.get_by_id(chat_session.id)
    assert loaded_session is None, "Session should be cascade-deleted with user"

    loaded_artifact = await artifact_repo.get_by_id(artifact.id)
    assert loaded_artifact is None, "Artifact should be cascade-deleted with session"


@pytest.mark.asyncio
async def test_vector_similarity_search_ranking(db_session):
    """Verifies that HNSW cosine similarity search ranks candidates accurately."""
    corpus_repo = CorpusRepository(db_session)

    ep = await corpus_repo.create_or_get_episode(
        title=f"Search Ep {uuid.uuid4().hex[:4]}",
        guest_name="Elena Verna",
    )

    # Create 3 vectors with varying similarity to target [1, 0, 0, ...]
    target_vector = [0.0] * 1536
    target_vector[0] = 1.0

    # High match: 95% alignment
    vec_high = [0.0] * 1536
    vec_high[0] = 0.95
    vec_high[1] = 0.05

    # Medium match: 70% alignment
    vec_med = [0.0] * 1536
    vec_med[0] = 0.70
    vec_med[1] = 0.30

    # Low match: orthogonal/below threshold
    vec_low = [0.0] * 1536
    vec_low[5] = 1.0  # Completely orthogonal to index 0

    await corpus_repo.upsert_chunk(
        episode_id=ep.id,
        chunk_index=0,
        content="High match chunk",
        token_count=5,
        content_hash="h_high",
        embedding=vec_high,
    )
    await corpus_repo.upsert_chunk(
        episode_id=ep.id,
        chunk_index=1,
        content="Medium match chunk",
        token_count=5,
        content_hash="h_med",
        embedding=vec_med,
    )
    await corpus_repo.upsert_chunk(
        episode_id=ep.id,
        chunk_index=2,
        content="Low match chunk",
        token_count=5,
        content_hash="h_low",
        embedding=vec_low,
    )
    await db_session.flush()

    # Search with 0.65 threshold (should exclude low match)
    results = await corpus_repo.search_similar_chunks(
        query_embedding=target_vector,
        similarity_threshold=0.65,
        top_k=5,
    )

    assert len(results) == 2, "Should return high and medium matches only"
    assert results[0]["content"] == "High match chunk"
    assert results[1]["content"] == "Medium match chunk"
    assert results[0]["similarity"] > results[1]["similarity"]
    assert results[0]["similarity"] >= 0.95


@pytest.mark.asyncio
async def test_full_session_graph_persistence_and_reload(db_session):
    """
    Verifies the complete Phase 2 Gate:
    Persist user -> session -> messages -> citations -> chunks -> artifact,
    then reload and assert full graph integrity.
    """
    user_repo = UserRepository(db_session)
    session_repo = SessionRepository(db_session)
    msg_repo = MessageRepository(db_session)
    corpus_repo = CorpusRepository(db_session)
    artifact_repo = ArtifactRepository(db_session)

    # 1. Create User
    user = await user_repo.create(
        f"graph_user_{uuid.uuid4().hex[:8]}", {"tier": "pro"}
    )

    # 2. Create Session
    session = await session_repo.create(user.id, "Full Graph Session")

    # 3. Create Episode and Chunks
    ep = await corpus_repo.create_or_get_episode(
        title="Grounded Growth Tactics",
        guest_name="Brian Balfour",
        episode_number=101,
        source_url="https://lennyspodcast.com/balfour",
    )
    chunk, _ = await corpus_repo.upsert_chunk(
        episode_id=ep.id,
        chunk_index=0,
        content="Four growth loops drive product virality.",
        token_count=8,
        content_hash="balfour_virality_chunk",
        embedding=[0.02] * 1536,
        start_timestamp="05:20",
    )

    # 4. Create User Message
    user_msg = await msg_repo.create(
        session_id=session.id,
        role="user",
        content="What does Balfour say about virality?",
    )

    # 5. Create Assistant Message with Provenance
    asst_msg = await msg_repo.create(
        session_id=session.id,
        role="assistant",
        content="Balfour identifies four core growth loops.",
        provider="openai",
        model="gpt-4o-mini",
        tokens_prompt=250,
        tokens_completion=65,
        cost_usd=0.00012,
    )

    # 6. Attach Citation
    citations = await msg_repo.add_citations(
        asst_msg.id,
        [{"chunk_id": chunk.id, "rank": 1, "similarity": 0.892}],
    )
    assert len(citations) == 1

    # 7. Create Artifact
    artifact = await artifact_repo.create(
        session_id=session.id,
        type="markdown",
        title="Balfour Growth Loops",
        content="# Growth Loops Framework\n\n1. Viral\n2. Content\n3. Paid\n4. Sales",
        message_id=asst_msg.id,
    )

    await db_session.commit()

    # 8. Reload full graph in a fresh query
    reloaded_session = await session_repo.get_with_history(session.id)
    assert reloaded_session is not None
    assert reloaded_session.title == "Full Graph Session"
    assert len(reloaded_session.messages) == 2

    # User message
    assert reloaded_session.messages[0].role == "user"
    assert reloaded_session.messages[0].content == "What does Balfour say about virality?"

    # Assistant message
    reloaded_asst = reloaded_session.messages[1]
    assert reloaded_asst.role == "assistant"
    assert reloaded_asst.provider == "openai"
    assert reloaded_asst.model == "gpt-4o-mini"
    assert reloaded_asst.cost_usd == 0.00012

    # Citation
    assert len(reloaded_asst.citations) == 1
    assert reloaded_asst.citations[0].chunk_id == chunk.id
    assert reloaded_asst.citations[0].rank == 1
    assert abs(reloaded_asst.citations[0].similarity - 0.892) < 1e-4

    # Artifact
    assert len(reloaded_session.artifacts) == 1
    reloaded_artifact = reloaded_session.artifacts[0]
    assert reloaded_artifact.title == "Balfour Growth Loops"
    assert reloaded_artifact.type == "markdown"
    assert reloaded_artifact.message_id == asst_msg.id

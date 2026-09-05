"""
Lenny Growth Assistant — Phase 3 Ingestion Pipeline Integration Tests

Tests end-to-end transcript ingestion against PostgreSQL/pgvector:
1. Parsing and storing episode records with metadata.
2. Generating and storing 1536-dimensional chunk embeddings.
3. Strict idempotency: re-ingesting causes 0 duplicates and 0 re-embeddings.
4. Vector similarity queryability of newly ingested chunks via HNSW index.
"""

from pathlib import Path
import pytest
import pytest_asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.models import Episode, TranscriptChunk
from app.db.repositories.corpus_repo import CorpusRepository
from ingestion.embeddings import EmbeddingClient
from ingestion.ingest import IngestionPipeline


SAMPLE_FIXTURE_PATH = Path("tests/fixtures/transcripts/sample_transcript.md")


@pytest_asyncio.fixture
async def test_session():
    """Provides an isolated database session for pipeline integration tests."""
    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )
    async_session = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_pipeline_ingest_sample_file(test_session: AsyncSession):
    """
    Verifies that ingesting a sample transcript creates the episode,
    produces chunks with 1536-d embeddings, and links them properly.
    """
    repo = CorpusRepository(test_session)
    embedding_client = EmbeddingClient(mock_mode=True)
    pipeline = IngestionPipeline(test_session, embedding_client=embedding_client)

    # Clean up prior test run if present to verify genuine first-run insertion
    sample_title = "How to build a high-performing growth team | Adam Fishman (Patreon, Lyft, Imperfect Foods)"
    existing = await repo.get_episode_by_title(sample_title)
    if existing is not None:
        await test_session.delete(existing)
        await test_session.commit()

    # Ingest the sample file
    stats = await pipeline.ingest_file(SAMPLE_FIXTURE_PATH)

    assert stats.episodes_processed == 1
    assert stats.chunks_processed > 0
    assert stats.chunks_created == stats.chunks_processed
    assert stats.chunks_skipped == 0
    assert stats.tokens_embedded > 0

    # Query the stored episode from PostgreSQL
    episode = await repo.get_episode_by_title(
        "How to build a high-performing growth team | Adam Fishman (Patreon, Lyft, Imperfect Foods)"
    )
    assert episode is not None
    assert episode.guest_name == "Adam Fishman"
    assert episode.source_url == "https://www.youtube.com/watch?v=wP8YyWH524A"
    assert episode.metadata_.get("video_id") == "wP8YyWH524A"

    # Query the stored chunks
    stmt = (
        select(TranscriptChunk)
        .where(TranscriptChunk.episode_id == episode.id)
        .order_by(TranscriptChunk.chunk_index.asc())
    )
    result = await test_session.execute(stmt)
    chunks = result.scalars().all()

    assert len(chunks) == stats.chunks_created
    first_chunk = chunks[0]
    assert first_chunk.chunk_index == 0
    assert first_chunk.start_timestamp == "00:00:00"
    assert first_chunk.embedding is not None
    assert len(first_chunk.embedding) == 1536
    assert "[Episode:" in first_chunk.content
    assert "Guest: Adam Fishman" in first_chunk.content


@pytest.mark.asyncio
async def test_pipeline_idempotency_zero_duplicates(test_session: AsyncSession):
    """
    GATE REQUIREMENT: Re-ingesting the exact same file must produce:
    - 0 new episodes
    - 0 new chunks
    - 100% skipped chunks
    - 0 new tokens embedded ($0.00 spend)
    - Zero duplicate rows in PostgreSQL
    """
    embedding_client = EmbeddingClient(mock_mode=True)
    pipeline = IngestionPipeline(test_session, embedding_client=embedding_client)

    # First ingestion (already done in previous test or run here)
    stats1 = await pipeline.ingest_file(SAMPLE_FIXTURE_PATH)

    # Second ingestion of the identical file
    stats2 = await pipeline.ingest_file(SAMPLE_FIXTURE_PATH)

    assert stats2.episodes_processed == 1
    assert stats2.episodes_created == 0, "Episode was duplicated!"
    assert stats2.chunks_created == 0, "Chunks were duplicated!"
    assert stats2.chunks_skipped == stats2.chunks_processed, "Chunks should all be skipped!"
    assert stats2.tokens_embedded == 0, "API tokens were burned on unchanged content!"
    assert stats2.cost_usd == 0.0, "Cost should be exactly $0.00 for duplicate run!"

    # Verify total row count in DB hasn't grown
    count_stmt = select(func.count(Episode.id)).where(
        Episode.title == "How to build a high-performing growth team | Adam Fishman (Patreon, Lyft, Imperfect Foods)"
    )
    count_res = await test_session.execute(count_stmt)
    total_episodes = count_res.scalar_one()
    assert total_episodes == 1, "Expected exactly 1 episode row in PostgreSQL"


@pytest.mark.asyncio
async def test_pipeline_ingested_chunks_searchable_via_hnsw(test_session: AsyncSession):
    """
    Verifies that newly ingested chunks can be queried via HNSW vector search
    with metadata filtering.
    """
    repo = CorpusRepository(test_session)

    # Search for an onboarding query using mock embedding
    query_text = "Why is onboarding such an underappreciated growth lever?"
    query_vector = EmbeddingClient.generate_deterministic_mock_embedding(query_text)

    # Search with guest_name filter
    results = await repo.search_similar_chunks(
        query_embedding=query_vector,
        similarity_threshold=-1.0,  # Match top results regardless of threshold for mock vector test
        top_k=3,
        guest_name="Adam Fishman",
    )

    assert len(results) > 0
    top_result = results[0]
    assert top_result["guest_name"] == "Adam Fishman"
    assert "How to build a high-performing growth team" in top_result["episode_title"]
    assert top_result["timestamp"] is not None
    assert "source_url" in top_result
    assert "content" in top_result

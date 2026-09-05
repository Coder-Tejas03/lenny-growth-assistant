"""
Lenny Growth Assistant — Phase 4 Retrieval Integration Tests

Runs live queries against PostgreSQL/pgvector to test:
1. End-to-end retrieval with HNSW vector index.
2. Relational metadata constraints (guest_name filtering).
3. Out-of-domain question abstention against stored corpus.
4. Citation structure compatibility with database records.
"""

from pathlib import Path
import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.repositories.corpus_repo import CorpusRepository
from app.retrieval.models import CANONICAL_ABSTENTION_MESSAGE
from app.retrieval.retriever import TranscriptRetriever
from ingestion.embeddings import EmbeddingClient
from ingestion.ingest import IngestionPipeline

SAMPLE_FIXTURE_PATH = Path("tests/fixtures/transcripts/sample_transcript.md")


@pytest_asyncio.fixture
async def db_session():
    """Provides an isolated database session with NullPool."""
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool, echo=False)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_corpus(db_session: AsyncSession):
    """Ensures sample transcript is ingested and indexed in PostgreSQL."""
    client = EmbeddingClient(mock_mode=True)
    pipeline = IngestionPipeline(db_session, embedding_client=client)
    await pipeline.ingest_file(SAMPLE_FIXTURE_PATH)
    return True


@pytest.mark.asyncio
async def test_live_retrieval_returns_grounded_chunks(db_session: AsyncSession, seeded_corpus):
    """
    Verifies that querying a known topic from the ingested transcript
    returns EvidenceChunks and Citations with high similarity.
    """
    client = EmbeddingClient(mock_mode=True)
    retriever = TranscriptRetriever(
        db_session,
        embedding_client=client,
        similarity_threshold=-1.0,  # Bounded for deterministic mock test
        top_k=3,
    )

    query = "Why is onboarding such an underappreciated growth lever?"
    result = await retriever.retrieve(query)

    assert result.is_sufficient is True
    assert len(result.chunks) > 0
    assert len(result.citations) == len(result.chunks)

    top_chunk = result.chunks[0]
    assert top_chunk.guest_name is not None
    assert top_chunk.episode_title is not None
    assert top_chunk.similarity > -1.0

    top_citation = result.citations[0]
    assert top_citation.chunk_id == top_chunk.chunk_id
    assert top_citation.guest_name == top_chunk.guest_name
    assert top_chunk.guest_name in top_citation.in_text_reference
    assert top_chunk.episode_title in top_citation.in_text_reference


@pytest.mark.asyncio
async def test_live_retrieval_with_guest_filter(db_session: AsyncSession, seeded_corpus):
    """
    Verifies that relational filters (guest_name) correctly filter
    the HNSW vector search in PostgreSQL.
    """
    client = EmbeddingClient(mock_mode=True)
    retriever = TranscriptRetriever(db_session, embedding_client=client, similarity_threshold=-1.0)

    # Search with matching guest filter
    result = await retriever.retrieve("growth talent competency model", guest_name="Fishman")
    assert result.is_sufficient is True
    assert all(c.guest_name == "Adam Fishman" for c in result.chunks)

    # Search with non-existent guest filter
    result_none = await retriever.retrieve("growth talent competency model", guest_name="NonExistentGuest12345")
    assert result_none.is_sufficient is False
    assert result_none.abstention_message == CANONICAL_ABSTENTION_MESSAGE


@pytest.mark.asyncio
async def test_live_out_of_domain_query_abstains(db_session: AsyncSession, seeded_corpus):
    """
    Verifies that out-of-domain queries naturally abstain when
    meeting the 0.65 similarity threshold against the stored corpus.
    """
    client = EmbeddingClient(mock_mode=True)
    # Use default 0.65 threshold
    retriever = TranscriptRetriever(
        db_session,
        embedding_client=client,
        similarity_threshold=0.65,
    )

    out_of_domain_query = "What are the recommended first-line treatments for acute pediatric otitis media?"
    result = await retriever.retrieve(out_of_domain_query)

    assert result.is_sufficient is False
    assert result.abstention_message == CANONICAL_ABSTENTION_MESSAGE
    assert len(result.chunks) == 0
    assert len(result.citations) == 0

"""
Lenny Growth Assistant — Phase 4 Retriever Service Unit Tests

Tests query embedding, similarity thresholding, diversity filtering,
in-text citation construction, and canonical abstention behavior using mocked repositories.
"""

from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest

from app.retrieval import (
    CANONICAL_ABSTENTION_MESSAGE,
    EvidenceChunk,
    RetrievalResult,
    TranscriptRetriever,
)
from ingestion.embeddings import EmbeddingClient


@pytest.fixture
def mock_session():
    """Mocked SQLAlchemy AsyncSession."""
    return AsyncMock()


@pytest.fixture
def mock_embedding_client():
    """EmbeddingClient configured in mock mode for zero-cost deterministic tests."""
    return EmbeddingClient(mock_mode=True)


@pytest.mark.asyncio
async def test_empty_or_whitespace_query_abstains(mock_session, mock_embedding_client):
    """Verifies that empty or whitespace-only queries immediately abstain."""
    retriever = TranscriptRetriever(mock_session, embedding_client=mock_embedding_client)

    result_empty = await retriever.retrieve("")
    assert result_empty.is_sufficient is False
    assert result_empty.abstention_message == CANONICAL_ABSTENTION_MESSAGE
    assert len(result_empty.chunks) == 0
    assert len(result_empty.citations) == 0

    result_whitespace = await retriever.retrieve("   \n\t  ")
    assert result_whitespace.is_sufficient is False
    assert result_whitespace.abstention_message == CANONICAL_ABSTENTION_MESSAGE


@pytest.mark.asyncio
async def test_below_threshold_triggers_abstention(mock_session, mock_embedding_client):
    """
    GATE REQUIREMENT: If all search results fall below 0.65 similarity,
    the retriever must return an explicit abstention with zero citations.
    """
    retriever = TranscriptRetriever(
        mock_session,
        embedding_client=mock_embedding_client,
        similarity_threshold=0.65,
    )

    # Mock corpus repository returning empty list (no chunks >= 0.65)
    retriever.corpus_repo.search_similar_chunks = AsyncMock(return_value=[])

    result = await retriever.retrieve("What is the recipe for beef wellington?")

    assert result.is_sufficient is False
    assert result.abstention_message == CANONICAL_ABSTENTION_MESSAGE
    assert len(result.chunks) == 0
    assert len(result.citations) == 0
    assert result.format_context_for_prompt() == "No relevant transcript evidence found."


@pytest.mark.asyncio
async def test_successful_retrieval_with_citations(mock_session, mock_embedding_client):
    """
    Verifies that chunks meeting the similarity threshold are properly
    structured into EvidenceChunks and Citations.
    """
    retriever = TranscriptRetriever(
        mock_session,
        embedding_client=mock_embedding_client,
        similarity_threshold=0.65,
        top_k=3,
    )

    chunk_id = uuid.uuid4()
    mock_candidates = [
        {
            "chunk_id": chunk_id,
            "episode_title": "How to Measure Product-Market Fit",
            "guest_name": "Rahul Vohra",
            "content": "[Episode: PMF] At Superhuman we measured PMF by asking how disappointed users would be.",
            "timestamp": "14:22",
            "source_url": "https://example.com/rahul-vohra",
            "similarity": 0.8421,
        }
    ]
    retriever.corpus_repo.search_similar_chunks = AsyncMock(return_value=mock_candidates)

    result = await retriever.retrieve("How did Superhuman measure PMF?")

    assert result.is_sufficient is True
    assert result.abstention_message is None
    assert len(result.chunks) == 1
    assert len(result.citations) == 1

    chunk = result.chunks[0]
    assert chunk.chunk_id == chunk_id
    assert chunk.guest_name == "Rahul Vohra"
    assert chunk.similarity == 0.8421

    citation = result.citations[0]
    assert citation.chunk_id == chunk_id
    assert citation.in_text_reference == "[How to Measure Product-Market Fit: Rahul Vohra, 14:22]"
    assert "Superhuman" in citation.excerpt
    assert result.query_latency_ms >= 0.0


@pytest.mark.asyncio
async def test_source_diversity_filtering(mock_session, mock_embedding_client):
    """
    Verifies source diversity: caps chunks per episode (default 2)
    to prevent a single episode from monopolizing all top_k slots.
    """
    retriever = TranscriptRetriever(
        mock_session,
        embedding_client=mock_embedding_client,
        similarity_threshold=0.65,
        top_k=4,
        max_chunks_per_episode=2,
    )

    # 4 chunks from Episode A, 2 from Episode B
    mock_candidates = [
        {"chunk_id": uuid.uuid4(), "episode_title": "Episode A", "guest_name": "Guest 1", "content": "Text A1", "similarity": 0.90},
        {"chunk_id": uuid.uuid4(), "episode_title": "Episode A", "guest_name": "Guest 1", "content": "Text A2", "similarity": 0.88},
        {"chunk_id": uuid.uuid4(), "episode_title": "Episode A", "guest_name": "Guest 1", "content": "Text A3", "similarity": 0.87},
        {"chunk_id": uuid.uuid4(), "episode_title": "Episode A", "guest_name": "Guest 1", "content": "Text A4", "similarity": 0.86},
        {"chunk_id": uuid.uuid4(), "episode_title": "Episode B", "guest_name": "Guest 2", "content": "Text B1", "similarity": 0.85},
        {"chunk_id": uuid.uuid4(), "episode_title": "Episode B", "guest_name": "Guest 2", "content": "Text B2", "similarity": 0.84},
    ]
    retriever.corpus_repo.search_similar_chunks = AsyncMock(return_value=mock_candidates)

    result = await retriever.retrieve("Growth tactics across companies", top_k=4)

    assert len(result.chunks) == 4
    episode_a_count = sum(1 for c in result.chunks if c.episode_title == "Episode A")
    episode_b_count = sum(1 for c in result.chunks if c.episode_title == "Episode B")

    # Should have capped Episode A at 2, allowing Episode B to fill the remaining slots
    assert episode_a_count == 2
    assert episode_b_count == 2


@pytest.mark.asyncio
async def test_specific_episode_filter_bypasses_diversity_cap(mock_session, mock_embedding_client):
    """
    Verifies that when a user/system explicitly filters by episode_id,
    all top chunks from that single episode are allowed.
    """
    target_ep_id = uuid.uuid4()
    retriever = TranscriptRetriever(
        mock_session,
        embedding_client=mock_embedding_client,
        similarity_threshold=0.65,
        top_k=4,
        max_chunks_per_episode=2,
    )

    mock_candidates = [
        {"chunk_id": uuid.uuid4(), "episode_title": "Target Episode", "guest_name": "Solo Guest", "content": f"Text {i}", "similarity": 0.90 - i * 0.01}
        for i in range(4)
    ]
    retriever.corpus_repo.search_similar_chunks = AsyncMock(return_value=mock_candidates)

    result = await retriever.retrieve("Deep dive into this episode", episode_id=target_ep_id, top_k=4)

    assert len(result.chunks) == 4
    assert all(c.episode_title == "Target Episode" for c in result.chunks)


@pytest.mark.asyncio
async def test_prompt_context_formatting(mock_session, mock_embedding_client):
    """Verifies that format_context_for_prompt produces clean markdown blocks."""
    retriever = TranscriptRetriever(mock_session, embedding_client=mock_embedding_client)

    c1 = EvidenceChunk(
        chunk_id=uuid.uuid4(),
        episode_title="Pricing Strategy",
        guest_name="Madhavan Ramanujam",
        content="Monetization is not something you design at the end.",
        timestamp="08:15",
        source_url="https://example.com/pricing",
        similarity=0.892,
    )
    result = RetrievalResult(query="Pricing", chunks=[c1], citations=[c1.to_citation()])
    context_str = result.format_context_for_prompt()

    assert "--- Evidence Source [1]: [Pricing Strategy: Madhavan Ramanujam, 08:15] ---" in context_str
    assert "Source URL: https://example.com/pricing" in context_str
    assert "Relevance Score: 0.8920" in context_str
    assert "Monetization is not something you design at the end." in context_str


@pytest.mark.asyncio
async def test_database_exception_produces_graceful_abstention(mock_session, mock_embedding_client):
    """Verifies that unhandled database/network errors fail safely without crashing."""
    retriever = TranscriptRetriever(mock_session, embedding_client=mock_embedding_client)
    retriever.corpus_repo.search_similar_chunks = AsyncMock(side_effect=RuntimeError("DB Connection Lost"))

    result = await retriever.retrieve("Any valid query")

    assert result.is_sufficient is False
    assert result.abstention_message == CANONICAL_ABSTENTION_MESSAGE
    assert len(result.chunks) == 0

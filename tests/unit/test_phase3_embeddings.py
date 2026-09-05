"""
Lenny Growth Assistant — Phase 3 Embedding Client Unit Tests

Tests cost calculation, mock mode fallback, 1536-dimensional vector normalization,
batching, and safety budget guardrail enforcement.
"""

import pytest
from ingestion.embeddings import (
    EmbeddingClient,
    EmbeddingBudgetExceededError,
    EMBEDDING_DIMENSIONS,
    COST_PER_MILLION_TOKENS_USD,
)


def test_cost_calculation():
    """Verifies cost calculation under text-embedding-3-small pricing ($0.02 / 1M tokens)."""
    client = EmbeddingClient(mock_mode=True)
    assert client.calculate_cost(1_000_000) == pytest.approx(0.02)
    assert client.calculate_cost(500_000) == pytest.approx(0.01)
    assert client.calculate_cost(10_000) == pytest.approx(0.0002)
    assert client.calculate_cost(0) == 0.0


def test_mock_embedding_dimensions_and_normalization():
    """Verifies that mock embeddings produce 1536 dimensions normalized to unit length."""
    text = "Product-market fit means being in a good market with a product that can satisfy that market."
    vector = EmbeddingClient.generate_deterministic_mock_embedding(text)

    assert len(vector) == EMBEDDING_DIMENSIONS
    assert all(isinstance(x, float) for x in vector)

    # Verify L2 unit norm: sum(x^2) should be approximately 1.0 for cosine similarity
    norm = sum(x * x for x in vector) ** 0.5
    assert norm == pytest.approx(1.0, rel=1e-3)


def test_deterministic_mock_embedding():
    """Verifies that identical text yields identical mock embeddings."""
    text1 = "How to build high-performing growth teams"
    text2 = "How to build high-performing growth teams"
    text3 = "Completely different text snippet"

    v1 = EmbeddingClient.generate_deterministic_mock_embedding(text1)
    v2 = EmbeddingClient.generate_deterministic_mock_embedding(text2)
    v3 = EmbeddingClient.generate_deterministic_mock_embedding(text3)

    assert v1 == v2
    assert v1 != v3


@pytest.mark.asyncio
async def test_get_embeddings_in_mock_mode():
    """Verifies batch embedding retrieval in mock mode."""
    client = EmbeddingClient(mock_mode=True)
    texts = [
        "First chunk discussing activation loops",
        "Second chunk discussing user onboarding dropoff",
        "Third chunk discussing viral loops",
    ]
    embeddings = await client.get_embeddings(texts)

    assert len(embeddings) == 3
    assert len(embeddings[0]) == EMBEDDING_DIMENSIONS
    assert client.total_api_calls == 1
    assert client.total_tokens_embedded > 0
    assert client.total_cost_usd > 0.0


@pytest.mark.asyncio
async def test_budget_exceeded_error():
    """Verifies that exceeding the safety budget ceiling raises an exception."""
    # Set ceiling to $0.000001 with mock_mode=False and dummy key
    client = EmbeddingClient(
        api_key="sk-dummy-test-key",
        budget_ceiling_usd=0.000001,
        mock_mode=False,
    )
    texts = ["Test text that exceeds tiny budget"] * 10
    estimated_tokens = [500] * 10  # 5000 tokens -> $0.0001 which is > $0.000001

    with pytest.raises(EmbeddingBudgetExceededError, match="exceed safety budget"):
        await client.get_embeddings(texts, estimated_tokens=estimated_tokens)

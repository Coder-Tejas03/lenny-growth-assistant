"""
Lenny Growth Assistant — Embedding Client & Cost Telemetry

Generates 1536-dimensional vector embeddings using OpenAI's text-embedding-3-small
model, with request batching, rate-limit retries, cost tracking ($0.02 / 1M tokens),
budget guardrails, and deterministic offline mock capabilities for CI/testing.
"""

import asyncio
import hashlib
import logging
import os
from typing import List, Optional, Tuple
from dotenv import load_dotenv
import httpx

load_dotenv()

logger = logging.getLogger(__name__)

# Constants per implementation contract
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
COST_PER_MILLION_TOKENS_USD = 0.02
MAX_BATCH_SIZE = 100


class EmbeddingBudgetExceededError(Exception):
    """Raised when cumulative embedding spend exceeds the configured safety ceiling."""

    pass


class EmbeddingClient:
    """
    Manages vector embedding generation with cost guardrails and mock fallback.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = EMBEDDING_MODEL,
        budget_ceiling_usd: float = 4.00,
        mock_mode: bool = False,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.budget_ceiling_usd = budget_ceiling_usd
        # Enable mock mode if explicitly requested or if no API key is set
        self.mock_mode = mock_mode or not bool(self.api_key)

        # Telemetry
        self.total_tokens_embedded = 0
        self.total_cost_usd = 0.0
        self.total_api_calls = 0

        if self.mock_mode:
            logger.info("EmbeddingClient initialized in MOCK mode (no API key required).")
        else:
            logger.info(f"EmbeddingClient initialized with model '{self.model}'.")

    def calculate_cost(self, token_count: int) -> float:
        """Calculates USD cost for a given token count under text-embedding-3-small pricing."""
        return (token_count / 1_000_000.0) * COST_PER_MILLION_TOKENS_USD

    @staticmethod
    def generate_deterministic_mock_embedding(text: str, dim: int = EMBEDDING_DIMENSIONS) -> List[float]:
        """
        Generates a normalized, deterministic 1536-dimensional float vector based on SHA-256
        hashing of the input text. Used in mock mode and unit tests.
        """
        seed_hash = hashlib.sha256(text.encode("utf-8")).digest()
        vector: List[float] = []
        for i in range(dim):
            # Deterministic pseudo-float between -1.0 and 1.0
            byte_val = seed_hash[i % len(seed_hash)]
            pseudo_float = ((byte_val + i * 31) % 256 - 128) / 128.0
            vector.append(round(pseudo_float, 6))

        # Normalize vector to unit length (L2 norm) for cosine similarity
        norm = sum(x * x for x in vector) ** 0.5
        if norm > 0:
            vector = [round(x / norm, 6) for x in vector]
        return vector

    async def get_embeddings(
        self,
        texts: List[str],
        estimated_tokens: Optional[List[int]] = None,
    ) -> List[List[float]]:
        """
        Generates embeddings for a list of texts in batches.
        Returns a list of 1536-dimensional float vectors.
        """
        if not texts:
            return []

        # Check mock mode first
        if self.mock_mode:
            tokens_batch = sum(estimated_tokens) if estimated_tokens else len(texts) * 500
            self.total_tokens_embedded += tokens_batch
            self.total_cost_usd += self.calculate_cost(tokens_batch)
            self.total_api_calls += 1
            return [self.generate_deterministic_mock_embedding(t) for t in texts]

        # Live OpenAI API mode
        all_embeddings: List[List[float]] = []

        # Chunk into batches of at most MAX_BATCH_SIZE texts
        for i in range(0, len(texts), MAX_BATCH_SIZE):
            batch = texts[i : i + MAX_BATCH_SIZE]
            batch_tokens = (
                sum(estimated_tokens[i : i + MAX_BATCH_SIZE])
                if estimated_tokens
                else len(batch) * 500
            )

            # Check budget ceiling before spending
            projected_cost = self.total_cost_usd + self.calculate_cost(batch_tokens)
            if projected_cost > self.budget_ceiling_usd:
                raise EmbeddingBudgetExceededError(
                    f"Embedding request would exceed safety budget of ${self.budget_ceiling_usd:.2f}. "
                    f"Current spend: ${self.total_cost_usd:.4f}"
                )

            vectors, actual_tokens = await self._call_openai_embedding_api(batch)
            all_embeddings.extend(vectors)

            # Record telemetry
            self.total_tokens_embedded += actual_tokens
            self.total_cost_usd += self.calculate_cost(actual_tokens)
            self.total_api_calls += 1

        return all_embeddings

    async def _call_openai_embedding_api(
        self, texts: List[str], max_retries: int = 3
    ) -> Tuple[List[List[float]], int]:
        """Calls the OpenAI v1/embeddings REST endpoint with exponential backoff."""
        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": texts,
            "encoding_format": "float",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            delay = 1.0
            for attempt in range(max_retries):
                try:
                    response = await client.post(url, headers=headers, json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        embeddings = [item["embedding"] for item in data["data"]]
                        tokens = data.get("usage", {}).get("total_tokens", len(texts) * 500)
                        return embeddings, tokens

                    if response.status_code == 429:
                        logger.warning(f"OpenAI rate limited (429). Retrying in {delay}s...")
                        await asyncio.sleep(delay)
                        delay *= 2.0
                        continue

                    response.raise_for_status()

                except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                    if attempt == max_retries - 1:
                        raise RuntimeError(f"OpenAI embedding API failed after {max_retries} attempts: {exc}") from exc
                    await asyncio.sleep(delay)
                    delay *= 2.0

        raise RuntimeError("OpenAI embedding API reached unreachable state.")

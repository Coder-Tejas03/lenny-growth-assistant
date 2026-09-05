"""
Lenny Growth Assistant — Core Transcript Retriever Service

Orchestrates query embedding, pgvector HNSW cosine search, similarity thresholding,
source diversity filtering, and canonical abstention per docs/implementation-contract.md.
"""

import logging
import time
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.repositories.corpus_repo import CorpusRepository
from app.retrieval.models import (
    EvidenceChunk,
    RetrievalResult,
)
from ingestion.embeddings import EmbeddingClient

logger = logging.getLogger(__name__)

# Constants per Section 5 of docs/implementation-contract.md
DEFAULT_SIMILARITY_THRESHOLD = settings.RETRIEVAL_SIMILARITY_THRESHOLD  # 0.65
DEFAULT_TOP_K = settings.RETRIEVAL_TOP_K  # 5
MAX_CHUNKS_PER_EPISODE = 2  # Source diversity rule: prevent one episode from dominating


class TranscriptRetriever:
    """
    Service responsible for grounded semantic retrieval against Lenny's Podcast transcripts.
    """

    def __init__(
        self,
        session: AsyncSession,
        embedding_client: Optional[EmbeddingClient] = None,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        top_k: int = DEFAULT_TOP_K,
        max_chunks_per_episode: int = MAX_CHUNKS_PER_EPISODE,
    ):
        self.session = session
        self.embedding_client = embedding_client or EmbeddingClient(
            api_key=settings.OPENAI_API_KEY
        )
        self.similarity_threshold = similarity_threshold
        self.top_k = top_k
        self.max_chunks_per_episode = max_chunks_per_episode
        self.corpus_repo = CorpusRepository(session)

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        guest_name: Optional[str] = None,
        episode_id: Optional[uuid.UUID] = None,
    ) -> RetrievalResult:
        """
        Executes grounded retrieval for a user query:
        1. Validates and cleans query string.
        2. Generates query vector embedding.
        3. Executes pgvector HNSW cosine similarity search.
        4. Applies similarity threshold and source diversity filtering.
        5. Constructs EvidenceChunks and Citations.
        6. Triggers canonical abstention if no chunks meet threshold.
        """
        start_time = time.perf_counter()
        clean_query = query.strip()

        if not clean_query:
            logger.warning("Empty query submitted to TranscriptRetriever.")
            return RetrievalResult.abstain(query=query, latency_ms=0.0)

        effective_top_k = top_k or self.top_k
        effective_threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else self.similarity_threshold
        )

        try:
            # 1. Generate query vector embedding (1536-d)
            query_embeddings = await self.embedding_client.get_embeddings([clean_query])
            if not query_embeddings:
                logger.error("Failed to generate embedding for query.")
                return RetrievalResult.abstain(query=clean_query)

            query_vector = query_embeddings[0]

            # 2. Query pgvector via repository layer
            # Over-fetch slightly (2 * top_k) to allow for source diversity filtering
            fetch_limit = max(effective_top_k * 2, 10)
            raw_candidates = await self.corpus_repo.search_similar_chunks(
                query_embedding=query_vector,
                similarity_threshold=effective_threshold,
                top_k=fetch_limit,
                guest_name=guest_name,
                episode_id=episode_id,
            )

            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # 3. Check for empty results / below-threshold abstention
            if not raw_candidates:
                logger.info(
                    f"Zero chunks met similarity threshold {effective_threshold:.2f} for query: '{clean_query[:50]}...'"
                )
                return RetrievalResult.abstain(query=clean_query, latency_ms=latency_ms)

            # 4. Apply source diversity rule (cap chunks per episode)
            filtered_chunks: List[EvidenceChunk] = []
            episode_chunk_counts: Dict[str, int] = {}

            for row in raw_candidates:
                ep_title = row["episode_title"]
                current_count = episode_chunk_counts.get(ep_title, 0)

                # If single-episode filter is explicitly given, allow all chunks from that episode
                if episode_id is None and current_count >= self.max_chunks_per_episode:
                    continue

                chunk = EvidenceChunk(
                    chunk_id=row["chunk_id"],
                    episode_title=row["episode_title"],
                    guest_name=row["guest_name"],
                    content=row["content"],
                    timestamp=row.get("timestamp"),
                    source_url=row.get("source_url"),
                    similarity=row["similarity"],
                )
                filtered_chunks.append(chunk)
                episode_chunk_counts[ep_title] = current_count + 1

                if len(filtered_chunks) >= effective_top_k:
                    break

            # Fallback: if diversity filtering was too aggressive and produced zero chunks,
            # take top candidates up to top_k directly
            if not filtered_chunks and raw_candidates:
                for row in raw_candidates[:effective_top_k]:
                    filtered_chunks.append(
                        EvidenceChunk(
                            chunk_id=row["chunk_id"],
                            episode_title=row["episode_title"],
                            guest_name=row["guest_name"],
                            content=row["content"],
                            timestamp=row.get("timestamp"),
                            source_url=row.get("source_url"),
                            similarity=row["similarity"],
                        )
                    )

            # 5. Build user-facing citations
            citations = [chunk.to_citation() for chunk in filtered_chunks]

            return RetrievalResult(
                query=clean_query,
                chunks=filtered_chunks,
                citations=citations,
                is_sufficient=True,
                abstention_message=None,
                query_latency_ms=latency_ms,
            )

        except Exception as exc:
            logger.error(f"Error during retrieval for query '{clean_query}': {exc}", exc_info=True)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return RetrievalResult.abstain(query=clean_query, latency_ms=latency_ms)

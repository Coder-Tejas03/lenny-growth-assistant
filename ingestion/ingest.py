"""
Lenny Growth Assistant — Master Corpus Ingestion Pipeline

Coordinates transcript acquisition, parsing, token-aware chunking, OpenAI embeddings,
and idempotent database storage in PostgreSQL via CorpusRepository.
"""

import argparse
import asyncio
from dataclasses import dataclass
import logging
from pathlib import Path
import time
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Episode, TranscriptChunk
from app.db.repositories.corpus_repo import CorpusRepository
from app.db.session import AsyncSessionLocal
from ingestion.chunker import TranscriptChunker, TranscriptChunkData
from ingestion.embeddings import EmbeddingClient
from ingestion.fetcher import clone_transcript_repository, discover_transcript_files
from ingestion.parser import parse_transcript_file

logger = logging.getLogger(__name__)


@dataclass
class IngestionStats:
    """Telemetry report summarizing the result of an ingestion run."""

    episodes_processed: int = 0
    episodes_created: int = 0
    chunks_processed: int = 0
    chunks_created: int = 0
    chunks_skipped: int = 0
    tokens_embedded: int = 0
    cost_usd: float = 0.0
    duration_seconds: float = 0.0


class IngestionPipeline:
    """High-level service orchestrating the idempotent ingestion of podcast transcripts."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_client: Optional[EmbeddingClient] = None,
        chunker: Optional[TranscriptChunker] = None,
    ):
        self.session = session
        self.repo = CorpusRepository(session)
        self.embedding_client = embedding_client or EmbeddingClient()
        self.chunker = chunker or TranscriptChunker()

    async def ingest_file(self, file_path: Path | str) -> IngestionStats:
        """
        Parses and ingests a single transcript file idempotently.
        Skips embedding generation if a chunk with matching (episode_id, chunk_index)
        and identical content_hash already exists.
        """
        stats = IngestionStats()
        start_time = time.perf_counter()

        parsed = parse_transcript_file(file_path)
        stats.episodes_processed = 1

        # 1. Create or get episode record
        existing_episode = await self.repo.get_episode_by_title(parsed.title)
        if existing_episode is None:
            episode = await self.repo.create_or_get_episode(
                title=parsed.title,
                guest_name=parsed.guest_name,
                episode_number=parsed.episode_number,
                source_url=parsed.source_url,
                publication_date=parsed.publication_date,
                metadata=parsed.metadata,
            )
            stats.episodes_created = 1
        else:
            episode = existing_episode

        # 2. Chunk the transcript dialogue
        chunks: List[TranscriptChunkData] = self.chunker.chunk_transcript(
            transcript_text=parsed.transcript_text,
            episode_title=parsed.title,
            guest_name=parsed.guest_name,
        )
        stats.chunks_processed = len(chunks)

        if not chunks:
            await self.session.commit()
            stats.duration_seconds = time.perf_counter() - start_time
            return stats

        # 3. Determine which chunks actually need embedding generation
        chunks_to_embed: List[TranscriptChunkData] = []
        chunks_to_skip: List[TranscriptChunkData] = []

        for chunk_data in chunks:
            existing_chunk = await self.repo.get_chunk_by_episode_and_index(
                episode.id, chunk_data.chunk_index
            )
            if existing_chunk is not None and existing_chunk.content_hash == chunk_data.content_hash:
                chunks_to_skip.append(chunk_data)
            else:
                chunks_to_embed.append(chunk_data)

        stats.chunks_skipped = len(chunks_to_skip)

        # 4. Generate embeddings only for new or modified chunks
        embeddings: List[List[float]] = []
        if chunks_to_embed:
            texts = [c.content for c in chunks_to_embed]
            token_counts = [c.token_count for c in chunks_to_embed]
            embeddings = await self.embedding_client.get_embeddings(
                texts, estimated_tokens=token_counts
            )
            stats.tokens_embedded = sum(token_counts)
            stats.cost_usd = self.embedding_client.calculate_cost(stats.tokens_embedded)

        # 5. Persist chunks in PostgreSQL via CorpusRepository
        for idx, chunk_data in enumerate(chunks_to_embed):
            vector = embeddings[idx] if embeddings else None
            _, is_new = await self.repo.upsert_chunk(
                episode_id=episode.id,
                chunk_index=chunk_data.chunk_index,
                content=chunk_data.content,
                token_count=chunk_data.token_count,
                content_hash=chunk_data.content_hash,
                embedding=vector,
                start_timestamp=chunk_data.start_timestamp,
                end_timestamp=chunk_data.end_timestamp,
                metadata={},
            )
            if is_new:
                stats.chunks_created += 1

        await self.session.commit()
        stats.duration_seconds = time.perf_counter() - start_time
        return stats

    async def ingest_directory(
        self,
        source_dir: Path | str,
        limit: Optional[int] = None,
    ) -> IngestionStats:
        """Discovers and ingests all transcript files in a directory."""
        files = discover_transcript_files(source_dir)
        if limit:
            files = files[:limit]

        total_stats = IngestionStats()
        start_time = time.perf_counter()

        for idx, file_path in enumerate(files, start=1):
            episode_label = file_path.parent.name if file_path.parent.name != "episodes" else file_path.name
            logger.info(f"[{idx}/{len(files)}] Ingesting episode '{episode_label}'...")
            try:
                file_stats = await self.ingest_file(file_path)
                total_stats.episodes_processed += file_stats.episodes_processed
                total_stats.episodes_created += file_stats.episodes_created
                total_stats.chunks_processed += file_stats.chunks_processed
                total_stats.chunks_created += file_stats.chunks_created
                total_stats.chunks_skipped += file_stats.chunks_skipped
                total_stats.tokens_embedded += file_stats.tokens_embedded
                total_stats.cost_usd += file_stats.cost_usd
            except Exception as exc:
                logger.error(f"Error ingesting episode '{episode_label}' ({file_path}): {exc}", exc_info=True)

        total_stats.duration_seconds = time.perf_counter() - start_time
        return total_stats


async def run_pipeline(
    source_dir: Optional[str] = None,
    limit: Optional[int] = None,
    mock_mode: bool = False,
    budget_ceiling: float = 4.00,
) -> IngestionStats:
    """Entrypoint for running ingestion asynchronously."""
    # If no source dir provided, clone or use cached transcripts
    if not source_dir:
        transcripts_path = clone_transcript_repository()
    else:
        transcripts_path = Path(source_dir)

    embedding_client = EmbeddingClient(
        budget_ceiling_usd=budget_ceiling, mock_mode=mock_mode
    )

    async with AsyncSessionLocal() as session:
        pipeline = IngestionPipeline(session, embedding_client=embedding_client)
        stats = await pipeline.ingest_directory(transcripts_path, limit=limit)

    return stats


def main():
    """CLI interface for running the ingestion pipeline."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Ingest Lenny's Podcast transcripts into PostgreSQL/pgvector.")
    parser.add_argument("--source-dir", type=str, default=None, help="Directory containing transcript markdown files")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of episodes to process")
    parser.add_argument("--mock-embeddings", action="store_true", help="Force deterministic mock embeddings (zero cost)")
    parser.add_argument("--budget-ceiling", type=float, default=4.00, help="Safety budget limit in USD")
    args = parser.parse_args()

    logger.info("Starting transcript ingestion pipeline...")
    stats = asyncio.run(
        run_pipeline(
            source_dir=args.source_dir,
            limit=args.limit,
            mock_mode=args.mock_embeddings,
            budget_ceiling=args.budget_ceiling,
        )
    )

    print("\n" + "=" * 60)
    print("LENNY GROWTH ASSISTANT — INGESTION SUMMARY REPORT")
    print("=" * 60)
    print(f"Episodes Processed : {stats.episodes_processed}")
    print(f"Episodes Created   : {stats.episodes_created}")
    print(f"Chunks Processed   : {stats.chunks_processed}")
    print(f"Chunks Created     : {stats.chunks_created}")
    print(f"Chunks Skipped     : {stats.chunks_skipped} (Deduplicated)")
    print(f"Tokens Embedded    : {stats.tokens_embedded:,}")
    print(f"Estimated Cost     : ${stats.cost_usd:.6f} USD")
    print(f"Duration           : {stats.duration_seconds:.2f}s")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

"""
Lenny Growth Assistant — Corpus & Retrieval Repository

Manages podcast episodes, transcript chunks, and pgvector cosine similarity search.
"""

import uuid
from datetime import date
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Episode, TranscriptChunk
from app.db.repositories.base import BaseRepository


class CorpusRepository(BaseRepository[Episode]):
    def __init__(self, session: AsyncSession):
        super().__init__(Episode, session)

    # --- Episode Operations ---

    async def get_episode_by_id(self, episode_id: uuid.UUID) -> Optional[Episode]:
        stmt = select(Episode).where(Episode.id == episode_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_episode_by_title(self, title: str) -> Optional[Episode]:
        stmt = select(Episode).where(Episode.title == title)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_or_get_episode(
        self,
        title: str,
        guest_name: str,
        episode_number: Optional[int] = None,
        source_url: Optional[str] = None,
        publication_date: Optional[date] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Episode:
        existing = await self.get_episode_by_title(title)
        if existing is not None:
            return existing

        episode = Episode(
            title=title,
            guest_name=guest_name,
            episode_number=episode_number,
            source_url=source_url,
            publication_date=publication_date,
            metadata_=metadata or {},
        )
        self.session.add(episode)
        await self.session.flush()
        return episode

    # --- Transcript Chunk Operations ---

    async def get_chunk_by_id(self, chunk_id: uuid.UUID) -> Optional[TranscriptChunk]:
        stmt = select(TranscriptChunk).where(TranscriptChunk.id == chunk_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_chunk_by_episode_and_index(
        self, episode_id: uuid.UUID, chunk_index: int
    ) -> Optional[TranscriptChunk]:
        stmt = select(TranscriptChunk).where(
            TranscriptChunk.episode_id == episode_id,
            TranscriptChunk.chunk_index == chunk_index,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_chunk(
        self,
        episode_id: uuid.UUID,
        chunk_index: int,
        content: str,
        token_count: int,
        content_hash: str,
        embedding: Optional[List[float]] = None,
        start_timestamp: Optional[str] = None,
        end_timestamp: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[TranscriptChunk, bool]:
        """
        Idempotent chunk insertion.
        Returns (chunk, is_new).
        If (episode_id, chunk_index) exists and hash matches, returns existing chunk (saving embedding cost).
        If hash changed, updates chunk content and embedding.
        """
        existing = await self.get_chunk_by_episode_and_index(episode_id, chunk_index)
        if existing is not None:
            if existing.content_hash == content_hash:
                return existing, False
            # Content changed: update
            existing.content = content
            existing.token_count = token_count
            existing.content_hash = content_hash
            if embedding is not None:
                existing.embedding = embedding
            existing.start_timestamp = start_timestamp
            existing.end_timestamp = end_timestamp
            existing.metadata_ = metadata or {}
            await self.session.flush()
            return existing, False

        new_chunk = TranscriptChunk(
            episode_id=episode_id,
            chunk_index=chunk_index,
            content=content,
            token_count=token_count,
            content_hash=content_hash,
            embedding=embedding,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            metadata_=metadata or {},
        )
        self.session.add(new_chunk)
        await self.session.flush()
        return new_chunk, True

    # --- Vector Similarity Search ---

    async def search_similar_chunks(
        self,
        query_embedding: List[float],
        similarity_threshold: float = 0.65,
        top_k: int = 5,
        guest_name: Optional[str] = None,
        episode_id: Optional[uuid.UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executes HNSW-accelerated cosine similarity search:
          similarity = 1 - (embedding <=> query_embedding)
        Filters by similarity threshold and optional relational constraints.
        """
        filters = ["1 - (c.embedding <=> CAST(:query_vector AS vector)) >= :threshold"]
        params: Dict[str, Any] = {
            "query_vector": str(query_embedding),
            "threshold": similarity_threshold,
            "limit": top_k,
        }

        if guest_name:
            filters.append("e.guest_name ILIKE :guest_name")
            params["guest_name"] = f"%{guest_name}%"

        if episode_id:
            filters.append("e.id = :episode_id")
            params["episode_id"] = str(episode_id)

        where_clause = " AND ".join(filters)

        sql = f"""
            SELECT 
                c.id AS chunk_id,
                e.title AS episode_title,
                e.guest_name AS guest_name,
                c.content AS content,
                c.start_timestamp AS timestamp,
                e.source_url AS source_url,
                1 - (c.embedding <=> CAST(:query_vector AS vector)) AS similarity
            FROM transcript_chunks c
            JOIN episodes e ON c.episode_id = e.id
            WHERE {where_clause}
            ORDER BY c.embedding <=> CAST(:query_vector AS vector) ASC
            LIMIT :limit;
        """

        result = await self.session.execute(text(sql), params)
        rows = result.fetchall()

        return [
            {
                "chunk_id": row.chunk_id,
                "episode_title": row.episode_title,
                "guest_name": row.guest_name,
                "content": row.content,
                "timestamp": row.timestamp,
                "source_url": row.source_url,
                "similarity": round(float(row.similarity), 4),
            }
            for row in rows
        ]

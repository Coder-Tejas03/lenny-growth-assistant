"""
Lenny Growth Assistant — Message Repository

Manages conversation messages, model provenance, and citation junction records.
"""

import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models import Message, MessageCitation, TranscriptChunk
from app.db.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    def __init__(self, session: AsyncSession):
        super().__init__(Message, session)

    async def get_by_id(self, message_id: uuid.UUID) -> Optional[Message]:
        stmt = (
            select(Message)
            .where(Message.id == message_id)
            .options(
                selectinload(Message.citations)
                .selectinload(MessageCitation.chunk)
                .selectinload(TranscriptChunk.episode)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_session(self, session_id: uuid.UUID) -> List[Message]:
        stmt = (
            select(Message)
            .where(Message.session_id == session_id)
            .options(
                selectinload(Message.citations)
                .selectinload(MessageCitation.chunk)
                .selectinload(TranscriptChunk.episode)
            )
            .order_by(Message.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        session_id: uuid.UUID,
        role: str,
        content: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        tokens_prompt: Optional[int] = None,
        tokens_completion: Optional[int] = None,
        cost_usd: float = 0.0,
    ) -> Message:
        message = Message(
            session_id=session_id,
            role=role,
            content=content,
            provider=provider,
            model=model,
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            cost_usd=cost_usd,
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def add_citations(
        self, message_id: uuid.UUID, citations_data: List[Dict[str, Any]]
    ) -> List[MessageCitation]:
        """
        Attaches verified transcript citations to an assistant message.
        Each citation dict must have: chunk_id, rank, similarity.
        """
        citations: List[MessageCitation] = []
        for item in citations_data:
            citation = MessageCitation(
                message_id=message_id,
                chunk_id=item["chunk_id"],
                rank=item["rank"],
                similarity=float(item["similarity"]),
            )
            self.session.add(citation)
            citations.append(citation)
        await self.session.flush()
        return citations

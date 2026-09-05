"""
Lenny Growth Assistant — Session Repository

Manages conversation threads and history loading.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models import Message, MessageCitation, Session, TranscriptChunk
from app.db.repositories.base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    def __init__(self, session: AsyncSession):
        super().__init__(Session, session)

    async def get_by_id(self, session_id: uuid.UUID) -> Optional[Session]:
        stmt = select(Session).where(Session.id == session_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_history(self, session_id: uuid.UUID) -> Optional[Session]:
        """Loads a session along with its messages, citations, chunks, episodes, and artifacts."""
        stmt = (
            select(Session)
            .where(Session.id == session_id)
            .options(
                selectinload(Session.messages)
                .selectinload(Message.citations)
                .selectinload(MessageCitation.chunk)
                .selectinload(TranscriptChunk.episode),
                selectinload(Session.artifacts),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self, user_id: uuid.UUID, limit: int = 20, offset: int = 0
    ) -> List[Session]:
        stmt = (
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(Session.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self, user_id: uuid.UUID, title: str = "New Conversation"
    ) -> Session:
        chat_session = Session(
            user_id=user_id,
            title=title,
        )
        self.session.add(chat_session)
        await self.session.flush()
        return chat_session

    async def update_title(self, session_id: uuid.UUID, title: str) -> Optional[Session]:
        s = await self.get_by_id(session_id)
        if s is not None:
            s.title = title
            s.updated_at = datetime.now(timezone.utc)
            await self.session.flush()
        return s

    async def delete(self, session_id: uuid.UUID) -> bool:
        s = await self.get_by_id(session_id)
        if s is not None:
            await self.session.delete(s)
            await self.session.flush()
            return True
        return False

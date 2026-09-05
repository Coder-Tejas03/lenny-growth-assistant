"""
Lenny Growth Assistant — Artifact Repository

Manages persistence and lookup for generated Markdown and HTML artifacts.
"""

import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Artifact
from app.db.repositories.base import BaseRepository


class ArtifactRepository(BaseRepository[Artifact]):
    def __init__(self, session: AsyncSession):
        super().__init__(Artifact, session)

    async def get_by_id(self, artifact_id: uuid.UUID) -> Optional[Artifact]:
        stmt = select(Artifact).where(Artifact.id == artifact_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_session(self, session_id: uuid.UUID) -> List[Artifact]:
        stmt = (
            select(Artifact)
            .where(Artifact.session_id == session_id)
            .order_by(Artifact.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        session_id: uuid.UUID,
        type: str,
        title: str,
        content: str,
        message_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
        id: Optional[uuid.UUID] = None,
    ) -> Artifact:
        artifact = Artifact(
            id=id or uuid.uuid4(),
            session_id=session_id,
            message_id=message_id,
            type=type,
            title=title,
            content=content,
            metadata_=metadata or {},
        )
        self.session.add(artifact)
        await self.session.flush()
        return artifact

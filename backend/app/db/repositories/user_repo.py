"""
Lenny Growth Assistant — User Repository

Handles persistence and lookup for anonymous user identities.
"""

import uuid
from typing import Any, Dict, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User
from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_anonymous_identifier(self, identifier: str) -> Optional[User]:
        stmt = select(User).where(User.anonymous_identifier == identifier)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, identifier: str, metadata: Optional[Dict[str, Any]] = None) -> User:
        user = User(
            anonymous_identifier=identifier,
            metadata_=metadata or {},
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_or_create(
        self, identifier: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[User, bool]:
        """Returns (user, created_flag)."""
        existing = await self.get_by_anonymous_identifier(identifier)
        if existing is not None:
            return existing, False
        new_user = await self.create(identifier, metadata)
        return new_user, True

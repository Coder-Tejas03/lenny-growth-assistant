"""
Lenny Growth Assistant — Base Async Repository

Provides common database session encapsulation and query primitives.
"""

from typing import Generic, Type, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic repository providing shared session handling and model scoping."""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

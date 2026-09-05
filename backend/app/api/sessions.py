"""
Lenny Growth Assistant — Sessions API Router

Implements session lifecycle, message history reload, and anonymous identity resolution
matching Section 11 of docs/implementation-contract.md.
"""

import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.session_repo import SessionRepository
from app.db.repositories.user_repo import UserRepository
from app.db.session import get_db
from app.schemas.error import SessionNotFoundError
from app.schemas.session import (
    ArtifactResponse,
    CitationResponse,
    CreateSessionRequest,
    MessageResponse,
    SessionDetailResponse,
    SessionResponse,
    SessionSummaryResponse,
    UpdateSessionRequest,
)

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
)
async def create_session(
    payload: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """
    Creates an independent conversation session:
    1. Idempotently resolves or creates the anonymous user record.
    2. Inserts a new session record linked to the user.
    3. Commits and returns session metadata.
    """
    user_repo = UserRepository(db)
    session_repo = SessionRepository(db)

    # 1. Resolve or create user
    user, _ = await user_repo.get_or_create(payload.anonymous_identifier)

    # 2. Create session
    title = payload.title or "New Conversation"
    new_session = await session_repo.create(user_id=user.id, title=title)
    await db.commit()

    return SessionResponse(
        id=new_session.id,
        title=new_session.title,
        anonymous_identifier=user.anonymous_identifier,
        created_at=new_session.created_at,
        updated_at=new_session.updated_at,
    )


@router.get(
    "",
    response_model=List[SessionSummaryResponse],
    summary="List sessions for an anonymous user",
)
async def list_sessions(
    anonymous_identifier: str = Query(..., min_length=1, max_length=255, description="Anonymous user ID"),
    limit: int = Query(20, ge=1, le=100, description="Max sessions to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
) -> List[SessionSummaryResponse]:
    """
    Returns a paginated list of sessions owned by the given anonymous user,
    ordered by most recently updated first.
    """
    user_repo = UserRepository(db)
    session_repo = SessionRepository(db)

    user = await user_repo.get_by_anonymous_identifier(anonymous_identifier)
    if user is None:
        # A new visitor has zero existing sessions
        return []

    sessions = await session_repo.list_by_user(user.id, limit=limit, offset=offset)
    return [
        SessionSummaryResponse(
            id=s.id,
            title=s.title,
            updated_at=s.updated_at,
        )
        for s in sessions
    ]


@router.get(
    "/{session_id}",
    response_model=SessionDetailResponse,
    summary="Load full conversation history and artifacts",
)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SessionDetailResponse:
    """
    Loads complete session graph including:
    - Ordered message history
    - Verified transcript citations for each assistant turn
    - Associated Markdown and HTML artifacts
    """
    session_repo = SessionRepository(db)
    session_obj = await session_repo.get_with_history(session_id)

    if session_obj is None:
        raise SessionNotFoundError(str(session_id))

    # Transform messages and citations
    messages_out: List[MessageResponse] = []
    for msg in session_obj.messages:
        citations_out: List[CitationResponse] = []
        for cit in msg.citations:
            # Chunk details if joined
            chunk_content = cit.chunk.content if cit.chunk else ""
            ep_title = cit.chunk.episode.title if cit.chunk and cit.chunk.episode else "Lenny's Podcast"
            guest = cit.chunk.episode.guest_name if cit.chunk and cit.chunk.episode else "Podcast Guest"
            url = cit.chunk.episode.source_url if cit.chunk and cit.chunk.episode else None
            tstamp = cit.chunk.start_timestamp if cit.chunk else None

            citations_out.append(
                CitationResponse(
                    chunk_id=cit.chunk_id,
                    episode_title=ep_title,
                    guest_name=guest,
                    timestamp=tstamp,
                    source_url=url,
                    similarity=cit.similarity,
                    excerpt=chunk_content[:200] if chunk_content else None,
                )
            )

        messages_out.append(
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                provider=msg.provider,
                model=msg.model,
                tokens_prompt=msg.tokens_prompt,
                tokens_completion=msg.tokens_completion,
                cost_usd=float(msg.cost_usd) if msg.cost_usd is not None else 0.0,
                citations=citations_out,
                created_at=msg.created_at,
            )
        )

    # Transform artifacts
    artifacts_out: List[ArtifactResponse] = [
        ArtifactResponse(
            id=art.id,
            type=art.type,
            title=art.title,
            content=art.content,
            created_at=art.created_at,
        )
        for art in session_obj.artifacts
    ]

    return SessionDetailResponse(
        id=session_obj.id,
        title=session_obj.title,
        created_at=session_obj.created_at,
        updated_at=session_obj.updated_at,
        messages=messages_out,
        artifacts=artifacts_out,
    )


@router.patch(
    "/{session_id}",
    response_model=SessionSummaryResponse,
    summary="Update session title",
)
async def update_session_title(
    session_id: uuid.UUID,
    payload: UpdateSessionRequest,
    db: AsyncSession = Depends(get_db),
) -> SessionSummaryResponse:
    """Updates the title of an existing conversation session."""
    session_repo = SessionRepository(db)
    updated = await session_repo.update_title(session_id, payload.title)
    if updated is None:
        raise SessionNotFoundError(str(session_id))

    await db.commit()
    return SessionSummaryResponse(
        id=updated.id,
        title=updated.title,
        updated_at=updated.updated_at,
    )


@router.delete(
    "/{session_id}",
    summary="Delete a session and associated records",
)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Deletes a conversation session, cascading to messages, citations, and artifacts."""
    session_repo = SessionRepository(db)
    deleted = await session_repo.delete(session_id)
    if not deleted:
        raise SessionNotFoundError(str(session_id))

    await db.commit()
    return {"status": "deleted", "session_id": str(session_id)}

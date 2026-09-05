"""
Lenny Growth Assistant — Chat API Router

Exposes POST /api/chat (and alias POST /chat) returning a Server-Sent Events (SSE)
stream of grounded answers, citations, and artifacts per Sections 10 and 11 of docs/implementation-contract.md.
"""

import logging
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService

logger = logging.getLogger("lenny_assistant.api_chat")

router = APIRouter(tags=["Chat"])


@router.post(
    "/api/chat",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    summary="Stream grounded assistant response via SSE",
    description="Initiates grounded question answering, Ship 30 essay, or artifact generation with Server-Sent Events (SSE).",
)
@router.post(
    "/chat",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def chat_stream_endpoint(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    HTTP SSE streaming endpoint:
    1. Accepts validated ChatRequest payload.
    2. Instantiates ChatService with database session.
    3. Returns StreamingResponse with text/event-stream media type.
    4. Sets anti-buffering headers for proxy and client compatibility.
    """
    chat_service = ChatService(db=db)

    # Return standard W3C text/event-stream response
    return StreamingResponse(
        chat_service.stream_chat(payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disables proxy buffering (e.g. Nginx, Cloudflare)
        },
    )

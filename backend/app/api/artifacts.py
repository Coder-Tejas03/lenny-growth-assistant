"""
Lenny Growth Assistant — Artifacts API Router

Exposes REST endpoints for:
- Retrieving an artifact by UUID (GET /api/artifacts/{artifact_id})
- Downloading an artifact file directly (GET /api/artifacts/{artifact_id}/download)
- Listing artifacts for a conversation session (GET /api/artifacts/session/{session_id})
"""

import uuid
from typing import List
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.error import ArtifactNotFoundError
from app.schemas.session import ArtifactResponse
from app.services.artifact_service import ArtifactService

router = APIRouter(prefix="/api/artifacts", tags=["Artifacts"])


@router.get(
    "/{artifact_id}",
    response_model=ArtifactResponse,
    summary="Get single artifact by ID",
)
async def get_artifact(
    artifact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ArtifactResponse:
    """
    Returns an artifact's metadata and sanitized content.
    """
    service = ArtifactService(db)
    artifact = await service.get_artifact(artifact_id)
    if not artifact:
        raise ArtifactNotFoundError(str(artifact_id))

    return ArtifactResponse(
        id=artifact.id,
        type=artifact.type,
        title=artifact.title,
        content=artifact.content,
        created_at=artifact.created_at,
    )


@router.get(
    "/{artifact_id}/download",
    summary="Download an artifact as a file (.md or .html)",
)
async def download_artifact(
    artifact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Returns the artifact content with Content-Disposition: attachment header
    for browser file downloads.
    """
    service = ArtifactService(db)
    artifact = await service.get_artifact(artifact_id)
    if not artifact:
        raise ArtifactNotFoundError(str(artifact_id))

    content, filename, media_type = ArtifactService.format_download(artifact)

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@router.get(
    "/session/{session_id}",
    response_model=List[ArtifactResponse],
    summary="List artifacts for a session",
)
async def list_session_artifacts(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> List[ArtifactResponse]:
    """
    Returns all artifacts created within a specific conversation session.
    """
    service = ArtifactService(db)
    artifacts = await service.list_session_artifacts(session_id)
    return [
        ArtifactResponse(
            id=a.id,
            type=a.type,
            title=a.title,
            content=a.content,
            created_at=a.created_at,
        )
        for a in artifacts
    ]

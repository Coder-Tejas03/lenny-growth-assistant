"""
Lenny Growth Assistant — Session & Conversation Schemas

Pydantic v2 data models for session lifecycle, message history, citations, and artifacts
matching Section 11 of docs/implementation-contract.md.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CreateSessionRequest(BaseModel):
    """Payload for creating a new conversation session."""
    title: Optional[str] = Field(default="New Conversation", max_length=255, description="Initial conversation title")
    anonymous_identifier: str = Field(..., min_length=1, max_length=255, description="Unique anonymous user identifier")


class UpdateSessionRequest(BaseModel):
    """Payload for updating session metadata (e.g. title)."""
    title: str = Field(..., min_length=1, max_length=255, description="Updated conversation title")


class SessionResponse(BaseModel):
    """Summary response when a session is created or updated."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    anonymous_identifier: str
    created_at: datetime
    updated_at: datetime


class SessionSummaryResponse(BaseModel):
    """Lightweight session summary for list views."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    updated_at: datetime


class CitationResponse(BaseModel):
    """Citation linking an assistant response to a specific source transcript chunk."""
    model_config = ConfigDict(from_attributes=True)

    chunk_id: uuid.UUID
    episode_title: str
    guest_name: str
    timestamp: Optional[str] = None
    source_url: Optional[str] = None
    similarity: float
    excerpt: Optional[str] = None


class MessageResponse(BaseModel):
    """A conversational turn in a session."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    provider: Optional[str] = None
    model: Optional[str] = None
    tokens_prompt: Optional[int] = None
    tokens_completion: Optional[int] = None
    cost_usd: float = 0.0
    citations: List[CitationResponse] = Field(default_factory=list)
    created_at: datetime


class ArtifactResponse(BaseModel):
    """A generated Markdown or HTML/CSS artifact linked to a session."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    title: str
    content: str
    created_at: datetime


class SessionDetailResponse(BaseModel):
    """Complete session graph response including message history and artifacts."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = Field(default_factory=list)
    artifacts: List[ArtifactResponse] = Field(default_factory=list)

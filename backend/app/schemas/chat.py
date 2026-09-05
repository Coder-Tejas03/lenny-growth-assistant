"""
Lenny Growth Assistant — Chat & Streaming Schemas

Defines Pydantic v2 validation models for chat requests and Server-Sent Event (SSE)
stream formatting matching Sections 10 and 11 of docs/implementation-contract.md.
"""

from enum import Enum
import json
from typing import Any, Dict, Optional, Union
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatMode(str, Enum):
    """Supported chat execution modes mapping directly to specialized Pi Agent skills."""
    DEFAULT = "default"      # Grounded Q&A skill
    SHIP30 = "ship30"        # Ship 30 for 30 essay writer skill
    ARTIFACT = "artifact"    # Structured artifact generator skill


class ChatProvider(str, Enum):
    """Allowed LLM provider backends."""
    OPENAI = "openai"
    OLLAMA = "ollama"


class ChatRequest(BaseModel):
    """
    Validated request payload initiating grounded response generation via SSE.
    Matches Section 11 of docs/implementation-contract.md.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    session_id: uuid.UUID = Field(
        ...,
        description="UUID of an existing, active conversation session",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="User query, prompt, or content generation instruction",
    )
    provider: str = Field(
        default="openai",
        description="LLM provider backend to use ('openai' or 'ollama')",
    )
    model: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Optional model identifier override (e.g. 'gpt-4o-mini', 'qwen2.5:1.5b')",
    )
    mode: str = Field(
        default="default",
        description="Generation mode: 'default' (Q&A), 'ship30' (essay), or 'artifact' (HTML/MD)",
    )
    mock_mode: bool = Field(
        default=False,
        description="Whether to run in deterministic offline mock mode (for fast/costless testing)",
    )

    @field_validator("message")
    @classmethod
    def validate_non_empty_message(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Message cannot be empty or solely whitespace.")
        return stripped

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        lowered = v.lower().strip()
        valid = [p.value for p in ChatProvider]
        if lowered not in valid:
            raise ValueError(f"Invalid provider '{v}'. Allowed providers are: {', '.join(valid)}.")
        return lowered

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        lowered = v.lower().strip()
        valid = [m.value for m in ChatMode]
        if lowered not in valid:
            raise ValueError(f"Invalid mode '{v}'. Allowed modes are: {', '.join(valid)}.")
        return lowered


class SSEEvent(BaseModel):
    """
    Data model representing a single Server-Sent Event (SSE).
    Formats payloads according to standard W3C text/event-stream specification:
    event: <event_name>
    data: <json_or_text>
    \n\n
    """
    event: str = Field(..., description="Event type (status, token, citation, artifact, done, error)")
    data: Union[Dict[str, Any], str] = Field(..., description="Event payload as dictionary or raw string")

    def encode(self) -> str:
        """Encodes event into an SSE text/event-stream frame ending with double newline."""
        return format_sse(self.event, self.data)


def format_sse(event: str, data: Any) -> str:
    """
    Encodes an event name and arbitrary payload into an SSE wire frame.
    Example:
    format_sse("token", {"delta": "Hello"})
    -> "event: token\\ndata: {\\"delta\\": \\"Hello\\"}\\n\\n"
    """
    if isinstance(data, str):
        payload = data
    else:
        payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def format_sse_done() -> str:
    """Standard terminal SSE delimiter per Section 10 of docs/implementation-contract.md."""
    return "data: [DONE]\n\n"

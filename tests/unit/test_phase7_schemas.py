"""
Unit tests for Phase 7 Chat and SSE schemas.

Validates Pydantic constraints, provider allowlists, mode enforcement,
and SSE wire frame serialization per Sections 10 and 11 of docs/implementation-contract.md.
"""

import json
import uuid
import pytest
from pydantic import ValidationError

from app.schemas.chat import (
    ChatMode,
    ChatProvider,
    ChatRequest,
    SSEEvent,
    format_sse,
    format_sse_done,
)


def test_valid_chat_request_defaults():
    session_id = uuid.uuid4()
    req = ChatRequest(
        session_id=session_id,
        message="What is product-market fit?",
    )
    assert req.session_id == session_id
    assert req.message == "What is product-market fit?"
    assert req.provider == "openai"
    assert req.mode == "default"
    assert req.model is None
    assert req.mock_mode is False


def test_valid_chat_request_custom_fields():
    session_id = uuid.uuid4()
    req = ChatRequest(
        session_id=session_id,
        message="  Write a Ship 30 essay on retention.  ",
        provider="OLLAMA",
        mode="SHIP30",
        model="qwen2.5:1.5b",
        mock_mode=True,
    )
    assert req.message == "Write a Ship 30 essay on retention."
    assert req.provider == "ollama"
    assert req.mode == "ship30"
    assert req.model == "qwen2.5:1.5b"
    assert req.mock_mode is True


def test_chat_request_rejects_empty_message():
    with pytest.raises(ValidationError) as exc:
        ChatRequest(session_id=uuid.uuid4(), message="   ")
    err = str(exc.value)
    assert "at least 1 character" in err or "Message cannot be empty" in err



def test_chat_request_rejects_invalid_provider():
    with pytest.raises(ValidationError) as exc:
        ChatRequest(
            session_id=uuid.uuid4(),
            message="Valid question",
            provider="anthropic",
        )
    assert "Invalid provider 'anthropic'" in str(exc.value)


def test_chat_request_rejects_invalid_mode():
    with pytest.raises(ValidationError) as exc:
        ChatRequest(
            session_id=uuid.uuid4(),
            message="Valid question",
            mode="unsupported_mode",
        )
    assert "Invalid mode 'unsupported_mode'" in str(exc.value)


def test_sse_event_dict_payload_encode():
    event = SSEEvent(
        event="status",
        data={"stage": "retrieving", "message": "Searching transcript archive..."},
    )
    encoded = event.encode()
    expected = (
        "event: status\n"
        'data: {"stage": "retrieving", "message": "Searching transcript archive..."}\n\n'
    )
    assert encoded == expected


def test_sse_event_string_payload_encode():
    event = SSEEvent(
        event="token",
        data="Product-market fit",
    )
    encoded = event.encode()
    expected = "event: token\ndata: Product-market fit\n\n"
    assert encoded == expected


def test_format_sse_helper():
    out = format_sse("citation", {"citations": [{"id": 1}]})
    assert out.startswith("event: citation\ndata: ")
    assert out.endswith("\n\n")
    parsed_body = json.loads(out.split("\ndata: ")[1].strip())
    assert parsed_body == {"citations": [{"id": 1}]}


def test_format_sse_done():
    done_signal = format_sse_done()
    assert done_signal == "data: [DONE]\n\n"

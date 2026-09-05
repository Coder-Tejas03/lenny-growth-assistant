"""
Unit tests for QueryRewriter in app.retrieval.query_rewriter.
Validates multi-turn context extraction, mock heuristics, error handling, and API fallback.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.retrieval.query_rewriter import QueryRewriter


@pytest.mark.asyncio
async def test_rewriter_empty_or_whitespace():
    rewriter = QueryRewriter(mock_mode=True)
    assert await rewriter.rewrite_if_needed("") == ""
    assert await rewriter.rewrite_if_needed("   ") == ""


@pytest.mark.asyncio
async def test_rewriter_turn_1_passthrough():
    rewriter = QueryRewriter(mock_mode=True)
    query = "How do I know if my startup has genuine product-market fit?"
    # No history passed -> passthrough immediately
    res = await rewriter.rewrite_if_needed(query, conversation_history=None)
    assert res == query

    res_empty = await rewriter.rewrite_if_needed(query, conversation_history=[])
    assert res_empty == query


@pytest.mark.asyncio
async def test_rewriter_mock_heuristic():
    rewriter = QueryRewriter(mock_mode=True)
    history = [
        {"role": "user", "content": "How do I know if my startup has genuine product-market fit?"},
        {"role": "assistant", "content": "Look for 40% disappointment and retention curves."},
    ]
    query = "and how do i collect this customer data?"
    rewritten = await rewriter.rewrite_if_needed(query, conversation_history=history)
    assert "product-market fit" in rewritten.lower()


@pytest.mark.asyncio
async def test_rewriter_llm_success():
    rewriter = QueryRewriter(api_key="test-key", mock_mode=False)
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '"how to collect customer survey data for product-market fit"'
    mock_response.choices = [mock_choice]

    with patch.object(rewriter._client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        history = [
            {"role": "user", "content": "How do I know if my startup has genuine product-market fit?"},
            {"role": "assistant", "content": "40% rule from Sean Ellis."},
        ]
        result = await rewriter.rewrite_if_needed("and how do i collect this customer data?", history)
        assert result == "how to collect customer survey data for product-market fit"
        assert mock_create.await_count == 1


@pytest.mark.asyncio
async def test_rewriter_llm_exception_fallback():
    rewriter = QueryRewriter(api_key="test-key", mock_mode=False)

    with patch.object(rewriter._client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = Exception("API timeout")
        history = [
            {"role": "user", "content": "Explain growth loops vs funnels"},
        ]
        raw_query = "why can theu be more challenging in B2B?"
        result = await rewriter.rewrite_if_needed(raw_query, history)
        # Should gracefully fall back to raw query
        assert result == raw_query


def test_strip_task_prefixes():
    res = QueryRewriter.strip_task_prefixes("Create an interactive HTML card comparing PLG vs SLG")
    assert "Product-Led Growth (PLG)" in res
    assert "Sales-Led Growth (SLG)" in res

    res_essay = QueryRewriter.strip_task_prefixes("Write a Ship 30 essay on user retention loops")
    assert res_essay == "user retention loops"


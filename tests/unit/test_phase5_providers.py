"""
Unit Tests for Phase 5 LLM Providers & Provider Factory

Verifies:
1. OpenAIProvider streaming, token calculation, and $4.00 budget ceiling guardrail.
2. OllamaProvider streaming, zero-cost telemetry, and connection failure resilience.
3. ProviderFactory resolution and enforcement of manual visible fallback.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.providers.base import (
    BudgetExceededError,
    LLMProviderInterface,
    LLMResponseMetadata,
    ProviderUnavailableError,
)
from app.providers.openai_provider import OpenAIProvider, PRICING
from app.providers.ollama_provider import OllamaProvider
from app.providers.factory import get_llm_provider


@pytest.fixture(autouse=True)
def reset_spend():
    """Ensure cumulative spend is isolated across test cases."""
    OpenAIProvider.reset_cumulative_spend()
    yield
    OpenAIProvider.reset_cumulative_spend()


@pytest.mark.asyncio
async def test_openai_provider_mock_stream():
    """Asserts mock OpenAI provider yields tokens and emits response metadata."""
    provider = OpenAIProvider(api_key="sk-mock", model="gpt-4o-mini", mock_mode=True)
    assert provider.provider_name == "openai"
    assert provider.model_name == "gpt-4o-mini"

    messages = [{"role": "user", "content": "How do I measure PMF?"}]
    tokens = []
    async for token in provider.stream_chat(messages, system_prompt="You are a helpful assistant."):
        tokens.append(token)

    full_text = "".join(tokens)
    assert len(tokens) > 5
    assert "Mock OpenAI Response" in full_text
    assert "Rahul Vohra" in full_text

    meta = provider.get_last_metadata()
    assert meta is not None
    assert meta.provider == "openai"
    assert meta.model == "gpt-4o-mini"
    assert meta.prompt_tokens > 0
    assert meta.completion_tokens > 0
    assert meta.cost_usd > 0.0
    assert OpenAIProvider.get_cumulative_spend() > 0.0


@pytest.mark.asyncio
async def test_openai_budget_ceiling_enforcement():
    """Asserts that requests halt with BudgetExceededError when spend reaches ceiling."""
    # Set a small budget limit of $0.001
    provider = OpenAIProvider(api_key="sk-mock", budget_limit=0.001, mock_mode=True)

    # Manually simulate prior accumulated spend at or over ceiling
    OpenAIProvider._cumulative_spend_usd = 0.0015

    messages = [{"role": "user", "content": "Will this exceed the budget?"}]
    with pytest.raises(BudgetExceededError) as exc_info:
        async for _ in provider.stream_chat(messages, system_prompt="System prompt"):
            pass

    assert exc_info.value.current_spend == 0.0015
    assert exc_info.value.budget_limit == 0.001
    assert "budget limit exceeded" in str(exc_info.value)


def test_openai_pricing_calculation():
    """Asserts mathematical accuracy of token pricing rates for supported models."""
    provider_mini = OpenAIProvider(model="gpt-4o-mini", mock_mode=True)
    # 10,000 prompt tokens @ $0.15/1M = $0.0015; 5,000 completion tokens @ $0.60/1M = $0.0030 -> total $0.0045
    cost_mini = provider_mini._calculate_cost(10_000, 5_000)
    assert cost_mini == 0.0045

    provider_4o = OpenAIProvider(model="gpt-4o", mock_mode=True)
    # 1,000 prompt tokens @ $2.50/1M = $0.0025; 1,000 completion tokens @ $10.00/1M = $0.0100 -> total $0.0125
    cost_4o = provider_4o._calculate_cost(1_000, 1_000)
    assert cost_4o == 0.0125


@pytest.mark.asyncio
async def test_ollama_provider_mock_stream():
    """Asserts mock Ollama provider yields tokens with zero dollar cost."""
    provider = OllamaProvider(model="qwen2.5:1.5b", mock_mode=True)
    assert provider.provider_name == "ollama"
    assert provider.model_name == "qwen2.5:1.5b"

    messages = [{"role": "user", "content": "What is activation?"}]
    tokens = []
    async for token in provider.stream_chat(messages, system_prompt="System instructions"):
        tokens.append(token)

    full_text = "".join(tokens)
    assert "Mock Ollama qwen2.5:1.5b Response" in full_text

    meta = provider.get_last_metadata()
    assert meta is not None
    assert meta.provider == "ollama"
    assert meta.model == "qwen2.5:1.5b"
    assert meta.cost_usd == 0.0


@pytest.mark.asyncio
async def test_ollama_connection_failure_raises_provider_unavailable():
    """Asserts that network errors when communicating with Ollama raise ProviderUnavailableError."""
    provider = OllamaProvider(base_url="http://localhost:11434", mock_mode=False)

    with patch("httpx.AsyncClient.stream", side_effect=httpx.ConnectError("Connection refused")):
        messages = [{"role": "user", "content": "Hello"}]
        with pytest.raises(ProviderUnavailableError) as exc_info:
            async for _ in provider.stream_chat(messages, system_prompt="Prompt"):
                pass

        assert exc_info.value.provider == "ollama"
        assert "Cannot connect to local Ollama service" in str(exc_info.value)


def test_provider_factory_resolution():
    """Asserts get_llm_provider correctly resolves instances conforming to LLMProviderInterface."""
    openai_inst = get_llm_provider("openai", mock_mode=True)
    assert isinstance(openai_inst, LLMProviderInterface)
    assert openai_inst.provider_name == "openai"
    assert openai_inst.model_name == "gpt-4o-mini"

    ollama_inst = get_llm_provider("ollama", model="qwen2.5:1.5b", mock_mode=True)
    assert isinstance(ollama_inst, LLMProviderInterface)
    assert ollama_inst.provider_name == "ollama"
    assert ollama_inst.model_name == "qwen2.5:1.5b"


def test_provider_factory_rejects_unsupported_provider():
    """Asserts provider factory rejects Anthropic/Claude or unknown names with clear error."""
    with pytest.raises(ValueError) as exc_info:
        get_llm_provider("claude")
    assert "Unsupported LLM provider 'claude'" in str(exc_info.value)
    assert "Anthropic Claude is not configured" in str(exc_info.value)

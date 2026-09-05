"""
Lenny Growth Assistant — OpenAI LLM Provider

Implements the LLMProviderInterface using OpenAI's async client with strict budget
guardrails ($4.00 ceiling), token usage telemetry, and deterministic mock mode.
"""

import asyncio
from typing import AsyncGenerator, Dict, List, Optional
from openai import AsyncOpenAI

from app.core.config import settings
from app.providers.base import (
    BudgetExceededError,
    LLMProviderInterface,
    LLMResponseMetadata,
    ProviderError,
)

# Current OpenAI API Pricing (USD per token)
PRICING = {
    "gpt-4o-mini": {
        "prompt": 0.150 / 1_000_000,       # $0.15 per 1M input tokens
        "completion": 0.600 / 1_000_000,   # $0.60 per 1M output tokens
    },
    "gpt-4o": {
        "prompt": 2.50 / 1_000_000,        # $2.50 per 1M input tokens
        "completion": 10.00 / 1_000_000,    # $10.00 per 1M output tokens
    },
}


class OpenAIProvider(LLMProviderInterface):
    """
    OpenAI Cloud Provider with real-time token tracking and hard budget ceiling.
    """

    # Class-level accumulator across provider instances to ensure cumulative budget enforcement
    _cumulative_spend_usd: float = 0.0

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        budget_limit: Optional[float] = None,
        mock_mode: bool = False,
    ):
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._model = model or settings.OPENAI_MODEL
        self._budget_limit = budget_limit if budget_limit is not None else settings.OPENAI_BUDGET_USD
        self.mock_mode = mock_mode or (not self._api_key or self._api_key.startswith("sk-placeholder"))

        self._client: Optional[AsyncOpenAI] = None
        if not self.mock_mode:
            self._client = AsyncOpenAI(api_key=self._api_key)

        self._last_metadata: Optional[LLMResponseMetadata] = None

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    @classmethod
    def get_cumulative_spend(cls) -> float:
        """Returns the total cumulative USD spend tracked during the process lifetime."""
        return cls._cumulative_spend_usd

    @classmethod
    def record_spend(cls, cost: float) -> None:
        """Accumulates USD cost into cumulative spend."""
        cls._cumulative_spend_usd = round(cls._cumulative_spend_usd + cost, 6)

    @classmethod
    def reset_cumulative_spend(cls) -> None:
        """Resets the cumulative spend counter (useful for test isolation)."""
        cls._cumulative_spend_usd = 0.0


    def get_last_metadata(self) -> Optional[LLMResponseMetadata]:
        return self._last_metadata

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        rates = PRICING.get(self._model, PRICING["gpt-4o-mini"])
        cost = (prompt_tokens * rates["prompt"]) + (completion_tokens * rates["completion"])
        return round(cost, 6)

    def _check_budget(self) -> None:
        """Verifies cumulative spend has not exceeded the hard budget ceiling."""
        if OpenAIProvider._cumulative_spend_usd >= self._budget_limit:
            raise BudgetExceededError(
                current_spend=OpenAIProvider._cumulative_spend_usd,
                budget_limit=self._budget_limit,
            )

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """
        Streams generated tokens while calculating cost and verifying budget ceiling.
        """
        self._check_budget()

        if self.mock_mode:
            async for token in self._stream_mock(messages, system_prompt):
                yield token
            return

        formatted_messages = [{"role": "system", "content": system_prompt}] + messages
        prompt_tokens = 0
        completion_tokens = 0

        try:
            stream = await self._client.chat.completions.create(
                model=self._model,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                stream_options={"include_usage": True},
            )

            async for chunk in stream:
                if chunk.usage:
                    prompt_tokens = chunk.usage.prompt_tokens or 0
                    completion_tokens = chunk.usage.completion_tokens or 0

                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        yield delta.content

            # Calculate cost and update cumulative budget tracker
            cost = self._calculate_cost(prompt_tokens, completion_tokens)
            OpenAIProvider._cumulative_spend_usd += cost

            self._last_metadata = LLMResponseMetadata(
                provider="openai",
                model=self._model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost_usd=cost,
            )

        except BudgetExceededError:
            raise
        except Exception as e:
            raise ProviderError(f"OpenAI streaming request failed: {str(e)}") from e

    async def _stream_mock(
        self, messages: List[Dict[str, str]], system_prompt: str
    ) -> AsyncGenerator[str, None]:
        """Deterministic mock stream for testing and offline development."""
        last_user_message = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "Hello",
        )

        mock_response = (
            f"[Mock OpenAI Response] Grounded insights regarding: {last_user_message}. "
            "According to Lenny's podcast archives, product-market fit requires measuring user retention "
            "and continuous feedback [Episode: Rahul Vohra on PMF, 14:22]."
        )

        tokens = mock_response.split(" ")
        for i, word in enumerate(tokens):
            chunk = word if i == 0 else " " + word
            yield chunk
            await asyncio.sleep(0.005)  # brief simulation of streaming latency

        # Telemetry record for mock execution
        prompt_tokens = len(system_prompt.split()) + sum(len(m["content"].split()) for m in messages)
        completion_tokens = len(tokens)
        cost = self._calculate_cost(prompt_tokens, completion_tokens)
        OpenAIProvider._cumulative_spend_usd += cost

        self._last_metadata = LLMResponseMetadata(
            provider="openai",
            model=self._model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=cost,
        )

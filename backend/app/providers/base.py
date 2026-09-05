"""
Lenny Growth Assistant — LLM Provider Base Interface & Metadata Contracts

Defines the asynchronous LLMProviderInterface Protocol, response metadata models,
and subsystem exceptions for budget and provider availability guardrails.
"""

from dataclasses import dataclass, field
from typing import AsyncGenerator, Dict, List, Optional, Protocol, runtime_checkable


class ProviderError(Exception):
    """Base exception for all LLM provider failures."""
    pass


class BudgetExceededError(ProviderError):
    """Raised when an API request would exceed the configured dollar budget ceiling."""
    def __init__(self, current_spend: float, budget_limit: float):
        super().__init__(
            f"OpenAI budget limit exceeded: current spend ${current_spend:.4f} "
            f"reached or exceeded the ${budget_limit:.2f} ceiling."
        )
        self.current_spend = current_spend
        self.budget_limit = budget_limit


class ProviderUnavailableError(ProviderError):
    """Raised when an LLM provider endpoint is unreachable or returning connection errors."""
    def __init__(self, provider: str, message: str, details: Optional[Dict] = None):
        super().__init__(f"Provider '{provider}' unavailable: {message}")
        self.provider = provider
        self.details = details or {}


@dataclass
class LLMResponseMetadata:
    """Carries token telemetry and cost accounting for a completed generation request."""
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    finish_reason: Optional[str] = "stop"


@runtime_checkable
class LLMProviderInterface(Protocol):
    """
    Formal asynchronous protocol that all LLM providers (OpenAI, Ollama, Mocks)
    must satisfy to be used interchangeably by the agent and API layers.
    """

    @property
    def provider_name(self) -> str:
        """Returns the canonical provider identifier ('openai' or 'ollama')."""
        ...

    @property
    def model_name(self) -> str:
        """Returns the specific model identifier (e.g. 'gpt-4o-mini', 'qwen2.5:1.5b')."""
        ...

    def get_last_metadata(self) -> Optional[LLMResponseMetadata]:
        """Returns the metadata (tokens, cost) from the most recent generation."""
        ...

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """
        Streams generated text tokens as strings.
        
        Args:
            messages: List of conversation turns (role: user/assistant, content: str).
            system_prompt: Guiding system instructions (grounding rules, tone, skills).
            temperature: Sampling temperature (0.0 to 1.0).
            max_tokens: Maximum completion tokens to generate.
            
        Yields:
            Token chunks as strings.
        """
        ...

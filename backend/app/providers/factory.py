"""
Lenny Growth Assistant — LLM Provider Factory

Instantiates and configures concrete LLM providers based on explicit configuration
or request parameters. Strictly enforces manual visible provider selection.
"""

from typing import Optional

from app.core.config import settings
from app.providers.base import LLMProviderInterface
from app.providers.openai_provider import OpenAIProvider
from app.providers.ollama_provider import OllamaProvider


def get_llm_provider(
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
    mock_mode: Optional[bool] = None,
) -> LLMProviderInterface:
    """
    Factory function resolving the requested LLM provider.
    
    Args:
        provider_name: 'openai' or 'ollama'. Defaults to settings.DEFAULT_LLM_PROVIDER.
        model: Optional model override (e.g. 'gpt-4o' or 'qwen2.5:1.5b').
        mock_mode: If True, forces deterministic offline execution.
        
    Returns:
        Configured LLMProviderInterface instance.
        
    Raises:
        ValueError: If an unsupported or invalid provider is requested.
    """
    selected_provider = (provider_name or settings.DEFAULT_LLM_PROVIDER).lower().strip()

    if selected_provider == "openai":
        use_mock = mock_mode if mock_mode is not None else (
            not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("sk-placeholder")
        )
        return OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            model=model or settings.OPENAI_MODEL,
            budget_limit=settings.OPENAI_BUDGET_USD,
            mock_mode=use_mock,
        )

    elif selected_provider == "ollama":
        use_mock = mock_mode if mock_mode is not None else False
        return OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=model or settings.OLLAMA_MODEL,
            mock_mode=use_mock,
        )

    else:
        raise ValueError(
            f"Unsupported LLM provider '{selected_provider}'. "
            f"Allowed providers are strictly 'openai' and 'ollama'. "
            f"Note: Anthropic Claude is not configured for this deployment."
        )


class ProviderFactory:
    """
    Class-based factory providing static lookup and resolution for LLM providers.
    Supports resolving by provider name ('openai', 'ollama') or model identifier ('gpt-4o-mini', 'qwen2.5:1.5b').
    """

    @classmethod
    def get_provider(
        cls,
        model_or_provider: Optional[str] = None,
        mock_mode: Optional[bool] = None,
        model: Optional[str] = None,
    ) -> LLMProviderInterface:
        """Resolve and instantiate the appropriate LLM provider."""
        if model_or_provider is None or model_or_provider == "":
            return get_llm_provider(
                provider_name=settings.DEFAULT_LLM_PROVIDER,
                model=model or settings.OPENAI_MODEL,
                mock_mode=mock_mode,
            )

        identifier = model_or_provider.strip().lower()
        if identifier in ("openai", "gpt-4o", "gpt-4o-mini", "gpt-4"):
            resolved_model = model if model else (model_or_provider if "gpt" in identifier else settings.OPENAI_MODEL)
            return get_llm_provider(
                provider_name="openai",
                model=resolved_model,
                mock_mode=mock_mode,
            )
        elif identifier in ("ollama", "qwen2.5:1.5b", "llama3.1:8b") or ":" in identifier:
            resolved_model = model if model else (model_or_provider if identifier != "ollama" else settings.OLLAMA_MODEL)
            return get_llm_provider(
                provider_name="ollama",
                model=resolved_model,
                mock_mode=mock_mode,
            )
        else:
            return get_llm_provider(
                provider_name=model_or_provider,
                model=model,
                mock_mode=mock_mode,
            )


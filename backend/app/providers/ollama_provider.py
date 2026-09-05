"""
Lenny Growth Assistant — Ollama Local LLM Provider

Implements LLMProviderInterface for local inference via Ollama HTTP API,
targeting qwen2.5:1.5b with resilient error recovery and deterministic mock mode.
"""

import asyncio
import json
from typing import AsyncGenerator, Dict, List, Optional
import httpx

from app.core.config import settings
from app.providers.base import (
    LLMProviderInterface,
    LLMResponseMetadata,
    ProviderUnavailableError,
)


class OllamaProvider(LLMProviderInterface):
    """
    Ollama Local Provider targeting lightweight CPU-friendly models (<=2B params).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        mock_mode: bool = False,
    ):
        self._base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self._model = model or settings.OLLAMA_MODEL
        self.mock_mode = mock_mode
        self._last_metadata: Optional[LLMResponseMetadata] = None

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    def get_last_metadata(self) -> Optional[LLMResponseMetadata]:
        return self._last_metadata

    async def check_availability(self) -> bool:
        """Probes the Ollama endpoint to verify if the local daemon is responding."""
        if self.mock_mode:
            return True
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self._base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """
        Streams generated tokens from local Ollama /api/chat endpoint.
        """
        if self.mock_mode:
            async for token in self._stream_mock(messages, system_prompt):
                yield token
            return

        payload = {
            "model": self._model,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        prompt_tokens = 0
        completion_tokens = 0

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/api/chat",
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        raise ProviderUnavailableError(
                            provider="ollama",
                            message=f"HTTP {response.status_code}: {body.decode(errors='ignore')}",
                            details={"status_code": response.status_code, "base_url": self._base_url},
                        )

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        # Extract telemetry tokens if provided by Ollama in the final chunk
                        if "prompt_eval_count" in chunk:
                            prompt_tokens = chunk.get("prompt_eval_count", 0)
                        if "eval_count" in chunk:
                            completion_tokens = chunk.get("eval_count", 0)

                        message_obj = chunk.get("message", {})
                        content = message_obj.get("content", "")
                        if content:
                            yield content

            self._last_metadata = LLMResponseMetadata(
                provider="ollama",
                model=self._model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost_usd=0.0,  # Local inference costs $0.00
            )

        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            raise ProviderUnavailableError(
                provider="ollama",
                message=f"Cannot connect to local Ollama service at {self._base_url}. Ensure 'ollama serve' is running.",
                details={"error_type": type(e).__name__, "base_url": self._base_url},
            ) from e
        except httpx.TimeoutException as e:
            raise ProviderUnavailableError(
                provider="ollama",
                message=f"Ollama inference timed out after 60s at {self._base_url}.",
                details={"error_type": "Timeout", "base_url": self._base_url},
            ) from e
        except ProviderUnavailableError:
            raise
        except Exception as e:
            raise ProviderUnavailableError(
                provider="ollama",
                message=f"Unexpected error communicating with Ollama: {str(e)}",
            ) from e

    async def _stream_mock(
        self, messages: List[Dict[str, str]], system_prompt: str
    ) -> AsyncGenerator[str, None]:
        """Deterministic mock stream for testing and offline execution."""
        last_user_message = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "Hello",
        )

        mock_response = (
            f"[Mock Ollama qwen2.5:1.5b Response] Grounded synthesis for: {last_user_message}. "
            "Lenny's guests emphasize user interviews and high-velocity shipping cycles."
        )

        tokens = mock_response.split(" ")
        for i, word in enumerate(tokens):
            chunk = word if i == 0 else " " + word
            yield chunk
            await asyncio.sleep(0.005)

        prompt_tokens = len(system_prompt.split()) + sum(len(m["content"].split()) for m in messages)
        completion_tokens = len(tokens)

        self._last_metadata = LLMResponseMetadata(
            provider="ollama",
            model=self._model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=0.0,
        )

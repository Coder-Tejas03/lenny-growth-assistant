"""
Lenny Growth Assistant — Health Check Schemas

Pydantic models for subsystem health probes matching Section 11 of docs/implementation-contract.md.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from app.schemas.error import utc_now


class DatabaseHealthStatus(BaseModel):
    """Database connectivity and pgvector readiness status."""
    connected: bool
    pgvector_ready: bool
    vector_version: Optional[str] = None
    uuid_ready: bool = True
    latency_ms: float = 0.0


class OpenAIProviderHealth(BaseModel):
    """OpenAI cloud provider configuration and budget telemetry."""
    configured: bool
    budget_remaining_usd: float
    budget_exceeded: bool = False
    model: str = "gpt-4o-mini"


class OllamaProviderHealth(BaseModel):
    """Ollama local provider connectivity and model target."""
    available: bool
    model: str = "qwen2.5:1.5b"
    base_url: str = "http://localhost:11434"
    error: Optional[str] = None


class ProviderHealthStatus(BaseModel):
    """Container for provider readiness probes."""
    openai: OpenAIProviderHealth
    ollama: OllamaProviderHealth


class CorpusHealthStatus(BaseModel):
    """Transcript knowledge base indexing metrics."""
    indexed_chunks: int = 0
    indexed_episodes: int = 0


class HealthResponse(BaseModel):
    """Aggregated health status across all application subsystems."""
    status: str = Field(..., description="'healthy', 'degraded', or 'unhealthy'")
    database: DatabaseHealthStatus
    providers: ProviderHealthStatus
    corpus: CorpusHealthStatus
    timestamp: datetime = Field(default_factory=utc_now)

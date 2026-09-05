"""
Lenny Growth Assistant — Health Probe Router

Exposes /api/health and /health probes for database, pgvector, Ollama, OpenAI, and corpus indexing.
Complies with Section 11 of docs/implementation-contract.md.
"""

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.health import check_database_health
from app.db.session import get_db
from app.providers.openai_provider import OpenAIProvider
from app.schemas.health import (
    CorpusHealthStatus,
    DatabaseHealthStatus,
    HealthResponse,
    OllamaProviderHealth,
    OpenAIProviderHealth,
    ProviderHealthStatus,
)

router = APIRouter(tags=["Health"])


async def probe_ollama_service() -> OllamaProviderHealth:
    """Probes the local Ollama server without raising unhandled exceptions."""
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/version")
            if resp.status_code == 200:
                return OllamaProviderHealth(
                    available=True,
                    model=settings.OLLAMA_MODEL,
                    base_url=settings.OLLAMA_BASE_URL,
                    error=None,
                )
            return OllamaProviderHealth(
                available=False,
                model=settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
                error=f"Ollama returned HTTP {resp.status_code}",
            )
    except Exception as exc:
        return OllamaProviderHealth(
            available=False,
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            error=str(exc),
        )


async def get_system_health(db: AsyncSession) -> HealthResponse:
    """Aggregates health across database, providers, and corpus."""
    # 1. Database & pgvector probe
    db_raw = await check_database_health(db)
    db_status = DatabaseHealthStatus(
        connected=db_raw.get("connected", False),
        pgvector_ready=db_raw.get("pgvector_ready", False),
        vector_version=db_raw.get("vector_version"),
        uuid_ready=db_raw.get("uuid_ready", True),
        latency_ms=db_raw.get("latency_ms", 0.0),
    )

    # 2. OpenAI provider status (safe check, never exposes raw key)
    has_real_key = bool(
        settings.OPENAI_API_KEY
        and not settings.OPENAI_API_KEY.startswith("sk-placeholder")
    )
    spent_usd = OpenAIProvider.get_cumulative_spend()
    remaining_usd = max(0.0, round(settings.OPENAI_BUDGET_USD - spent_usd, 4))
    is_budget_exceeded = spent_usd >= settings.OPENAI_BUDGET_USD

    openai_status = OpenAIProviderHealth(
        configured=has_real_key,
        budget_remaining_usd=remaining_usd,
        budget_exceeded=is_budget_exceeded,
        model=settings.OPENAI_MODEL,
    )

    # 3. Ollama local provider probe
    ollama_status = await probe_ollama_service()

    # 4. Indexed corpus counts
    indexed_chunks = 0
    indexed_episodes = 0
    if db_status.connected:
        try:
            chunks_res = await db.execute(text("SELECT COUNT(*) FROM transcript_chunks;"))
            indexed_chunks = chunks_res.scalar() or 0
            ep_res = await db.execute(text("SELECT COUNT(*) FROM episodes;"))
            indexed_episodes = ep_res.scalar() or 0
        except Exception:
            indexed_chunks = 0
            indexed_episodes = 0

    corpus_status = CorpusHealthStatus(
        indexed_chunks=indexed_chunks,
        indexed_episodes=indexed_episodes,
    )

    # 5. Composite health evaluation
    if not db_status.connected:
        overall_status = "unhealthy"
    elif not db_status.pgvector_ready:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return HealthResponse(
        status=overall_status,
        database=db_status,
        providers=ProviderHealthStatus(
            openai=openai_status,
            ollama=ollama_status,
        ),
        corpus=corpus_status,
    )


@router.get("/api/health", response_model=HealthResponse)
async def api_health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Comprehensive health probe matching docs/implementation-contract.md."""
    return await get_system_health(db)


@router.get("/health", response_model=HealthResponse)
async def health_check_alias(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Root health probe alias for container and load-balancer probes."""
    return await get_system_health(db)

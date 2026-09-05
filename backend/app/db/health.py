"""
Lenny Growth Assistant — Database Health Probe

Verifies connectivity, latency, and pgvector extension readiness.
"""

import time
from typing import Any, Dict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def check_database_health(session: AsyncSession) -> Dict[str, Any]:
    """
    Executes a health probe checking:
    1. Active database connectivity (SELECT 1).
    2. pgvector extension installation and version.
    3. uuid-ossp extension installation.
    4. Query round-trip latency in milliseconds.
    """
    start_time = time.perf_counter()
    try:
        # Check basic connectivity
        await session.execute(text("SELECT 1;"))

        # Check vector extension
        result = await session.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector';")
        )
        vector_version = result.scalar_one_or_none()

        # Check uuid-ossp extension
        uuid_result = await session.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'uuid-ossp';")
        )
        uuid_version = uuid_result.scalar_one_or_none()

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "connected": True,
            "pgvector_ready": vector_version is not None,
            "vector_version": vector_version,
            "uuid_ready": uuid_version is not None,
            "latency_ms": latency_ms,
            "status": "healthy" if vector_version else "degraded",
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "connected": False,
            "pgvector_ready": False,
            "vector_version": None,
            "uuid_ready": False,
            "latency_ms": latency_ms,
            "status": "unhealthy",
            "error": str(exc),
        }

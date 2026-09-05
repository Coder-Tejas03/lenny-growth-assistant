"""
Lenny Growth Assistant — Health Endpoint & Middleware Integration Tests

Verifies request ID propagation, structured logging, health probes, and error shielding.
"""

import uuid
import pytest
import pytest_asyncio
import httpx
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.session import get_db
from app.main import app


@pytest_asyncio.fixture
async def client_with_db():
    """Provides an httpx async client with an isolated NullPool database session."""
    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        async def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
        app.dependency_overrides.clear()

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_root_endpoint(client_with_db):
    response = await client_with_db.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Lenny Growth Assistant API"
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_request_id_middleware_generates_uuid(client_with_db):
    response = await client_with_db.get("/")
    assert response.status_code == 200
    req_id = response.headers.get("X-Request-ID")
    assert req_id is not None
    # Verify valid UUID format
    parsed = uuid.UUID(req_id)
    assert str(parsed) == req_id


@pytest.mark.asyncio
async def test_request_id_middleware_preserves_incoming_header(client_with_db):
    custom_id = f"custom-req-{uuid.uuid4()}"
    response = await client_with_db.get("/", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


@pytest.mark.asyncio
async def test_health_check_endpoint(client_with_db):
    response = await client_with_db.get("/api/health")
    assert response.status_code == 200
    data = response.json()

    # Core health envelope structure
    assert "status" in data
    assert data["status"] in ("healthy", "degraded", "unhealthy")

    # Database subsystem
    assert "database" in data
    assert data["database"]["connected"] is True
    assert data["database"]["pgvector_ready"] is True
    assert data["database"]["vector_version"] is not None

    # Provider subsystem
    assert "providers" in data
    assert "openai" in data["providers"]
    assert "ollama" in data["providers"]
    # Never leak secrets
    assert "api_key" not in data["providers"]["openai"]
    assert "budget_remaining_usd" in data["providers"]["openai"]
    assert data["providers"]["openai"]["model"] == "gpt-4o-mini"
    assert "model" in data["providers"]["ollama"]
    assert data["providers"]["ollama"]["model"] == "qwen2.5:1.5b"

    # Corpus subsystem
    assert "corpus" in data
    assert "indexed_chunks" in data["corpus"]


@pytest.mark.asyncio
async def test_health_alias_endpoint(client_with_db):
    response = await client_with_db.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["database"]["connected"] is True
    assert data["status"] in ("healthy", "degraded", "unhealthy")

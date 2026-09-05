"""
Lenny Growth Assistant — Phase 6 Gate Verification Test Suite

Verifies all criteria of the Phase 6 Gate from CODING_AGENT_TUTOR.md:
1. Invalid input gives structured 4xx responses.
2. Database and provider failures are safe (no crash, no leaks).
3. Sessions stay independent (strict tenant/user isolation).
4. Health output distinguishes component state without exposing secrets.
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
from app.schemas.error import (
    BudgetExceededException,
    DatabaseErrorException,
    ProviderUnavailableException,
)


@pytest_asyncio.fixture
async def gate_client():
    """Provides an isolated test client with NullPool database connectivity."""
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


class TestPhase6GateRequirements:
    """Rigorous gate verification for Phase 6 deliverables."""

    @pytest.mark.asyncio
    async def test_gate_criterion_1_structured_4xx_validation_responses(self, gate_client):
        """Verify that invalid inputs consistently return structured 4xx error envelopes."""
        # 1. Missing body
        res1 = await gate_client.post("/api/sessions", json={})
        assert res1.status_code == 422
        data1 = res1.json()
        assert "error" in data1
        assert data1["error"]["code"] == "VALIDATION_ERROR"
        assert "validation_errors" in data1["error"]["details"]
        assert "timestamp" in data1["error"]

        # 2. Malformed non-UUID in session_id path
        res2 = await gate_client.get("/api/sessions/invalid-not-a-uuid")
        assert res2.status_code == 422
        data2 = res2.json()
        assert data2["error"]["code"] == "VALIDATION_ERROR"

        # 3. Missing session returns structured 404
        non_existent_uuid = str(uuid.uuid4())
        res3 = await gate_client.get(f"/api/sessions/{non_existent_uuid}")
        assert res3.status_code == 404
        data3 = res3.json()
        assert data3["error"]["code"] == "SESSION_NOT_FOUND"
        assert data3["error"]["details"]["session_id"] == non_existent_uuid

    @pytest.mark.asyncio
    async def test_gate_criterion_2_safe_failure_handling(self, gate_client):
        """Verify that database and provider errors fail safely without leaking internal code traces."""
        # Test simulated custom provider unavailable error via dynamic test endpoint
        @app.get("/api/test-provider-error")
        async def mock_provider_error():
            raise ProviderUnavailableException("ollama", "Local Ollama daemon is offline.")

        res = await gate_client.get("/api/test-provider-error")
        assert res.status_code == 503
        data = res.json()
        assert data["error"]["code"] == "PROVIDER_UNAVAILABLE"
        assert data["error"]["details"]["provider"] == "ollama"

        # Test simulated budget exceeded error
        @app.get("/api/test-budget-error")
        async def mock_budget_error():
            raise BudgetExceededException("Budget ceiling of $4.00 exceeded.", {"spent": 4.01})

        res_b = await gate_client.get("/api/test-budget-error")
        assert res_b.status_code == 402
        data_b = res_b.json()
        assert data_b["error"]["code"] == "BUDGET_EXCEEDED"
        assert data_b["error"]["details"]["spent"] == 4.01

        # Test simulated unexpected error (catch-all 500)
        @app.get("/api/test-unhandled-error")
        async def mock_unhandled_error():
            raise RuntimeError("Database connection string postgresql://secret_pass@db leaked?")

        res_u = await gate_client.get("/api/test-unhandled-error")
        assert res_u.status_code == 500
        data_u = res_u.json()
        assert data_u["error"]["code"] == "INTERNAL_SERVER_ERROR"
        # Assert secret/trace did NOT leak to client!
        assert "secret_pass" not in data_u["error"]["message"]
        assert "RuntimeError" not in data_u["error"]["message"]

    @pytest.mark.asyncio
    async def test_gate_criterion_3_session_independence_and_isolation(self, gate_client):
        """Verify that sessions are completely independent across distinct users."""
        user_alpha = f"alpha_{uuid.uuid4().hex[:6]}"
        user_beta = f"beta_{uuid.uuid4().hex[:6]}"

        # Create sessions for Alpha
        s_a1 = await gate_client.post("/api/sessions", json={"title": "Alpha 1", "anonymous_identifier": user_alpha})
        s_a2 = await gate_client.post("/api/sessions", json={"title": "Alpha 2", "anonymous_identifier": user_alpha})

        # Create session for Beta
        s_b1 = await gate_client.post("/api/sessions", json={"title": "Beta 1", "anonymous_identifier": user_beta})

        # List Alpha sessions
        list_a = (await gate_client.get(f"/api/sessions?anonymous_identifier={user_alpha}")).json()
        a_ids = {item["id"] for item in list_a}
        assert s_a1.json()["id"] in a_ids
        assert s_a2.json()["id"] in a_ids
        assert s_b1.json()["id"] not in a_ids

        # List Beta sessions
        list_b = (await gate_client.get(f"/api/sessions?anonymous_identifier={user_beta}")).json()
        b_ids = {item["id"] for item in list_b}
        assert s_b1.json()["id"] in b_ids
        assert s_a1.json()["id"] not in b_ids
        assert s_a2.json()["id"] not in b_ids

    @pytest.mark.asyncio
    async def test_gate_criterion_4_health_subsystem_observability_and_zero_secret_leakage(self, gate_client):
        """Verify that health probe distinguishes subsystem states and leaks zero credentials."""
        response = await gate_client.get("/api/health")
        assert response.status_code == 200
        data = response.json()

        # 1. Distinguishes component states
        assert data["database"]["connected"] is True
        assert data["database"]["pgvector_ready"] is True
        assert isinstance(data["database"]["latency_ms"], float)
        assert isinstance(data["corpus"]["indexed_chunks"], int)
        assert data["providers"]["openai"]["model"] == "gpt-4o-mini"
        assert data["providers"]["ollama"]["model"] == "qwen2.5:1.5b"
        assert isinstance(data["providers"]["openai"]["budget_remaining_usd"], float)

        # 2. Zero secret leakage across entire JSON dump
        dump_str = str(data)
        assert "password" not in dump_str.lower()
        assert "api_key" not in dump_str
        assert "secret" not in dump_str.lower()

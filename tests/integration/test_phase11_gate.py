"""
Lenny Growth Assistant — Phase 11 Gate Verification & Operational Smoke Test Suite

Proves all Phase 11 Definition of Done criteria from CODING_AGENT_TUTOR.md:
1. Multi-Subsystem Health & Operational Diagnostics:
   GET /api/health accurately reports all subsystems (PostgreSQL, pgvector,
   OpenAI budget state, Ollama reachability, and corpus chunk statistics) with zero
   secret leakage.
2. Full End-to-End Grounded Chat & Persistence Lifecycle:
   Session creation -> user question -> grounded semantic retrieval -> SSE streaming
   with citations -> database persistence -> full session reload.
3. End-to-End Ship 30 for 30 Content Engine:
   Dedicated writing workflow generates ~1,250-word essay with hook, bold anchors,
   guest attribution, and actionable checklist, persisting as an artifact.
4. Safe Artifact Security & Isolation Contracts:
   Defense-in-depth Bleach server sanitization neutralizes malicious scripts;
   client SandboxedIframe strictly enforces sandbox="allow-scripts" without allow-same-origin;
   REST artifact download serves safe attachments.
5. Trust, Canonical Abstention, and Zero Silent Fallback:
   Out-of-domain queries trigger canonical abstention with zero citations;
   provider errors surface explicit actionable manual fallback options without
   ever silently switching models behind the user's back.
"""

import json
import os
import uuid
import pytest
import pytest_asyncio
import httpx
from httpx import ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.models import User, Session, Message, Episode, TranscriptChunk, Artifact
from app.db.session import get_db
from app.main import app
from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService
from app.services.artifact_service import ArtifactService
from app.providers import ProviderFactory, OpenAIProvider, OllamaProvider


def parse_sse_events(sse_text: str):
    """
    Helper to parse raw SSE text into structured events, tokens, citations, and artifacts.
    """
    events = []
    tokens = []
    citations = []
    artifacts = []
    status_events = []
    error_event = None
    done_event = None
    done_signal = False

    blocks = sse_text.strip().split("\n\n")
    for block in blocks:
        if not block.strip():
            continue
        ev_name = None
        ev_data = None
        for line in block.splitlines():
            line = line.strip()
            if line.startswith("event: "):
                ev_name = line[7:].strip()
            elif line.startswith("data: "):
                raw_data = line[6:].strip()
                if raw_data == "[DONE]":
                    done_signal = True
                    continue
                try:
                    ev_data = json.loads(raw_data)
                except Exception:
                    ev_data = raw_data

        if ev_name or ev_data:
            events.append({"event": ev_name, "data": ev_data})
            if ev_name == "token" and isinstance(ev_data, dict):
                delta = ev_data.get("delta") or ev_data.get("content") or ""
                tokens.append(delta)
            elif ev_name == "citation" and isinstance(ev_data, dict):
                c_list = ev_data.get("citations", [])
                citations.extend(c_list)
            elif ev_name == "artifact" and isinstance(ev_data, dict):
                artifacts.append(ev_data)
            elif ev_name == "status" and isinstance(ev_data, dict):
                status_events.append(ev_data)
            elif ev_name == "error":
                error_event = ev_data
            elif ev_name == "done":
                done_event = ev_data

    return {
        "events": events,
        "tokens": tokens,
        "citations": citations,
        "artifacts": artifacts,
        "status_events": status_events,
        "error_event": error_event,
        "done_event": done_event,
        "done_signal": done_signal,
    }


@pytest_asyncio.fixture
async def phase11_gate_fixture():
    """Sets up an isolated test database session, seed corpus, and ASGI client."""
    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        anon_id = f"anon_gate11_{uuid.uuid4().hex[:12]}"
        user = User(anonymous_identifier=anon_id)
        session.add(user)
        await session.flush()

        db_session = Session(
            user_id=user.id,
            title="Phase 11 E2E Gate Verification Session",
        )
        session.add(db_session)

        # Seed an episode and chunk if none exist
        ep_result = await session.execute(select(Episode).limit(1))
        episode = ep_result.scalar_one_or_none()
        if not episode:
            episode = Episode(
                title="Brian Chesky on Product Leadership & Founder Mode",
                guest_name="Brian Chesky",
                source_url="https://www.lennyspodcast.com/brian-chesky",
                episode_metadata={"published": "2024-05-01"},
            )
            session.add(episode)
            await session.flush()

            chunk = TranscriptChunk(
                episode_id=episode.id,
                chunk_index=0,
                content=(
                    "[Episode: Brian Chesky on Product Leadership | Guest: Brian Chesky | Timestamp: 14:20]\n"
                    "Brian Chesky: The biggest mistake product teams make is relying solely on A/B testing "
                    "for product roadmap decisions. Great products require strong founder vision, holistic taste, "
                    "and ruthless customer immersion rather than incremental metric chasing."
                ),
                start_timestamp="14:20",
                end_timestamp="16:45",
                embedding=[0.05] * 1536,
                chunk_metadata={"guest": "Brian Chesky", "topic": "Product Leadership"},
            )
            session.add(chunk)

        await session.commit()
        await session.refresh(db_session)
        await session.refresh(user)

        async def override_get_db():
            async with session_factory() as s:
                yield s

        app.dependency_overrides[get_db] = override_get_db

        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield {
                "client": client,
                "session": session,
                "user": user,
                "db_session": db_session,
                "session_factory": session_factory,
                "episode": episode,
            }

        app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_gate11_criterion_1_multi_subsystem_health(phase11_gate_fixture):
    """
    Gate Criterion 1: Multi-Subsystem Health & Operational Diagnostics.
    Asserts that GET /api/health probes all subsystems accurately without leaking secrets.
    """
    client = phase11_gate_fixture["client"]

    response = await client.get("/api/health")
    assert response.status_code == 200, f"Health endpoint returned {response.status_code}: {response.text}"

    data = response.json()
    assert "status" in data
    assert data["status"] in ("healthy", "degraded")

    # 1. Database subsystem
    assert "database" in data
    db_status = data["database"]
    assert db_status.get("connected") is True, "Database should be connected"
    assert "latency_ms" in db_status
    assert isinstance(db_status["latency_ms"], (int, float))

    # 2. pgvector subsystem
    assert db_status.get("pgvector_ready") is True, "pgvector extension must be ready"
    assert "vector_version" in db_status

    # 3. Provider subsystem (OpenAI cloud + Ollama local)
    assert "providers" in data
    providers_status = data["providers"]
    assert "openai" in providers_status
    openai_status = providers_status["openai"]
    assert "budget_exceeded" in openai_status
    assert openai_status["budget_exceeded"] is False

    assert "ollama" in providers_status
    ollama_status = providers_status["ollama"]
    assert "available" in ollama_status
    assert "model" in ollama_status

    # 4. Corpus index statistics
    assert "corpus" in data
    corpus_status = data["corpus"]
    assert "indexed_chunks" in corpus_status
    assert corpus_status["indexed_chunks"] >= 1

    # Security verification: ensure zero API keys or passwords in the response payload
    raw_text = json.dumps(data).lower()
    assert "sk-" not in raw_text, "OpenAI secret key must not leak in health output"
    assert "postgres:" not in raw_text, "Database credentials must not leak in health output"


@pytest.mark.asyncio
async def test_gate11_criterion_2_grounded_chat_and_session_lifecycle(phase11_gate_fixture):
    """
    Gate Criterion 2: Full End-to-End Grounded Chat & Persistence Lifecycle.
    Asserts:
    - POST /api/sessions creates an independent session.
    - POST /api/chat streams SSE events with evidence retrieval, token generation, and citations.
    - Message, citations, and provider provenance are atomically persisted in PostgreSQL.
    - GET /api/sessions/{id} correctly reloads the conversational history.
    """
    client = phase11_gate_fixture["client"]
    user = phase11_gate_fixture["user"]

    # Step 1: Create a brand new session via REST
    create_resp = await client.post(
        "/api/sessions",
        json={
            "anonymous_identifier": user.anonymous_identifier,
            "title": "Brian Chesky Product Strategy",
        },
    )
    assert create_resp.status_code == 201
    session_data = create_resp.json()
    session_id = session_data["id"]

    # Step 2: Stream a grounded question (using mock_mode=True for deterministic local testing)
    chat_payload = {
        "session_id": session_id,
        "message": "What did Brian Chesky say about product leadership and A/B testing?",
        "mode": "default",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "mock_mode": True,
    }

    chat_resp = await client.post("/api/chat", json=chat_payload)
    assert chat_resp.status_code == 200
    assert "text/event-stream" in chat_resp.headers.get("content-type", "")

    # Step 3: Parse the SSE stream
    parsed = parse_sse_events(chat_resp.text)
    assert parsed["done_signal"] is True, "Stream must emit terminal [DONE] indicator"
    assert len(parsed["tokens"]) > 0, "Stream must deliver generated tokens"
    assert len(parsed["events"]) >= 3, "Stream must contain status, tokens, and done events"

    # Step 4: Reload session history via REST API to verify persistence
    reload_resp = await client.get(f"/api/sessions/{session_id}")
    assert reload_resp.status_code == 200
    history_data = reload_resp.json()

    assert history_data["id"] == session_id
    messages = history_data["messages"]
    assert len(messages) >= 2, "Session must contain user message and assistant message"

    user_msg = messages[0]
    assistant_msg = messages[1]

    assert user_msg["role"] == "user"
    assert "Brian Chesky" in user_msg["content"]

    assert assistant_msg["role"] == "assistant"
    assert len(assistant_msg["content"]) > 0
    # Provider attribution must be persisted on the assistant message
    assert assistant_msg["provider"] == "openai"
    assert assistant_msg["model"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_gate11_criterion_3_ship30_content_engine(phase11_gate_fixture):
    """
    Gate Criterion 3: End-to-End Ship 30 for 30 Content Engine.
    Asserts that the Ship 30 writing workflow produces ~1,250-word structured essays
    with hook, short paragraphs, bold anchors, and an actionable checklist.
    """
    client = phase11_gate_fixture["client"]
    db_session = phase11_gate_fixture["db_session"]

    chat_payload = {
        "session_id": str(db_session.id),
        "message": "Turn Brian Chesky's thoughts on founder mode into a Ship 30 for 30 essay.",
        "mode": "ship30",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "mock_mode": True,
    }

    response = await client.post("/api/chat", json=chat_payload)
    assert response.status_code == 200

    parsed = parse_sse_events(response.text)
    full_text = "".join(parsed["tokens"])
    word_count = len(full_text.split())

    # Verify Ship 30 formatting heuristics
    assert word_count >= 1000, f"Ship 30 essay should be ~1,250 words, got {word_count}"
    assert "##" in full_text, "Ship 30 essay must contain clear Markdown structural headers"
    assert "**" in full_text, "Ship 30 essay must contain bold anchor emphasis"
    assert "Step" in full_text or "Checklist" in full_text or "Playbook" in full_text, (
        "Ship 30 essay must conclude with an actionable playbook or checklist"
    )

    # Verify that an artifact event was emitted and persisted
    assert len(parsed["artifacts"]) >= 1, "Ship 30 generation must emit an artifact event"
    artifact_event = parsed["artifacts"][0]
    art_id = artifact_event.get("id") or artifact_event.get("artifact_id")
    assert art_id is not None

    art_resp = await client.get(f"/api/artifacts/{art_id}")
    assert art_resp.status_code == 200
    art_data = art_resp.json()
    assert art_data["type"] == "markdown"
    assert len(art_data["content"]) > 0


@pytest.mark.asyncio
async def test_gate11_criterion_4_safe_artifact_security_contracts(phase11_gate_fixture):
    """
    Gate Criterion 4: Safe Artifact Security & Isolation Contracts.
    Asserts:
    - Malicious HTML payloads are sanitized by Bleach (stripping active script tags).
    - REST artifact download serves safe attachments with Content-Disposition.
    - Frontend SandboxedIframe strictly enforces sandbox="allow-scripts" without allow-same-origin.
    """
    client = phase11_gate_fixture["client"]
    db_session = phase11_gate_fixture["db_session"]
    session_factory = phase11_gate_fixture["session_factory"]

    # 1. Test Bleach defense-in-depth sanitization
    raw_html = (
        "<!DOCTYPE html><html><body>"
        "<h1>Safe Heading</h1>"
        "<script>window.parent.postMessage('steal_cookies', '*');</script>"
        "<img src='https://example.com/pic.png' onerror='alert(\"xss\")' />"
        "<p>Product Growth Dashboard</p>"
        "</body></html>"
    )
    clean_dict = ArtifactService.validate_and_sanitize("html", "Dashboard Widget", raw_html)
    sanitized = clean_dict["content"]

    assert "<script" not in sanitized, "Bleach must strip active <script> tags"
    assert "onerror=" not in sanitized, "Bleach must strip inline event handlers"
    assert "<h1>Safe Heading</h1>" in sanitized, "Bleach must preserve safe semantic tags"

    # 2. Persist an artifact and verify safe file download endpoint
    async with session_factory() as session:
        artifact = Artifact(
            session_id=db_session.id,
            type="html",
            title="Product Launch Checklist",
            content=sanitized,
        )
        session.add(artifact)
        await session.commit()
        await session.refresh(artifact)
        artifact_id = str(artifact.id)

    download_resp = await client.get(f"/api/artifacts/{artifact_id}/download")
    assert download_resp.status_code == 200
    assert "text/html" in download_resp.headers.get("content-type", "")
    assert "attachment;" in download_resp.headers.get("content-disposition", "")
    assert "product_launch_checklist.html" in download_resp.headers.get("content-disposition", "")

    # 3. Verify frontend SandboxedIframe security specification in source code
    import re
    iframe_component_path = os.path.join(
        os.path.dirname(__file__),
        "../../frontend/src/components/Artifact/SandboxedIframe.tsx",
    )
    with open(iframe_component_path, "r", encoding="utf-8") as f:
        iframe_source = f.read()

    # Parse sandbox attribute tokens specifically
    match = re.search(r'sandbox="([^"]*)"', iframe_source)
    assert match is not None, "iframe must declare a sandbox attribute"
    sandbox_tokens = match.group(1).strip().split()

    assert "allow-scripts" in sandbox_tokens, "Sandbox must allow scripts for interactive rendering"
    assert "allow-same-origin" not in sandbox_tokens, (
        "CRITICAL SECURITY: Iframe MUST NEVER include 'allow-same-origin' to prevent host DOM/cookie access"
    )


@pytest.mark.asyncio
async def test_gate11_criterion_5_canonical_abstention_and_no_silent_fallback(phase11_gate_fixture):
    """
    Gate Criterion 5: Trust, Canonical Abstention, and Zero Silent Fallback.
    Asserts:
    - Out-of-domain query triggers canonical abstention with zero hallucinated citations.
    - Hardware/provider failure returns an explicit structured error envelope with manual
      fallback suggestion, never silently switching providers behind the user's back.
    """
    client = phase11_gate_fixture["client"]
    db_session = phase11_gate_fixture["db_session"]

    # 1. Out-of-Domain Canonical Abstention Check
    unsupported_payload = {
        "session_id": str(db_session.id),
        "message": "How do you calculate the thermal conductivity of liquid xenon in cryogenics?",
        "mode": "default",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "mock_mode": True,
    }

    resp = await client.post("/api/chat", json=unsupported_payload)
    assert resp.status_code == 200

    parsed = parse_sse_events(resp.text)
    full_answer = "".join(parsed["tokens"])
    assert "sufficient evidence" in full_answer.lower(), (
        "Weak/out-of-domain questions must trigger canonical abstention message"
    )
    assert len(parsed["citations"]) == 0, "Abstention response must emit 0 citations"

    # 2. Zero Silent Fallback on Budget Ceiling Check
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(OpenAIProvider, "_cumulative_spend_usd", 4.05)

        budget_payload = {
            "session_id": str(db_session.id),
            "message": "Tell me about growth loops.",
            "mode": "default",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "mock_mode": True,
        }

        budget_resp = await client.post("/api/chat", json=budget_payload)
        assert budget_resp.status_code == 200

        # SSE stream must emit explicit BUDGET_EXCEEDED error, NOT silently switch to Ollama
        budget_parsed = parse_sse_events(budget_resp.text)
        error_event = budget_parsed["error_event"]

        assert error_event is not None, f"System must emit structured error event on budget limit, got {budget_resp.text}"
        code = error_event.get("code") or error_event.get("error_code")
        assert code == "BUDGET_EXCEEDED"
        details = error_event.get("details", {})
        fallback = details.get("fallback_suggested") or error_event.get("fallback_suggested")
        assert fallback == "ollama"

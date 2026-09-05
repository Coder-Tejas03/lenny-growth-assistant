"""
Lenny Growth Assistant — Phase 9 Artifact Service & API Unit Tests

Verifies:
- Defense-in-depth bleach sanitization of untrusted HTML artifacts (stripping script tags,
  event handlers, javascript: pseudo-protocols while preserving styles and semantic markup).
- Markdown artifact normalization (null bytes, newlines).
- Download header formatting (Content-Disposition, filename slug, media types).
- Artifact REST endpoints: GET /api/artifacts/{id}, download, session listing, and 404 errors.
"""

import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.models import Artifact, Session, User
from app.db.session import get_db
from app.main import app
from app.services.artifact_service import ArtifactService


@pytest_asyncio.fixture
async def client_and_db():
    """Yields an httpx test client alongside direct repository access sharing the same session."""
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
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, session
        app.dependency_overrides.clear()

    await test_engine.dispose()


def test_sanitize_html_strips_active_scripts():
    """Verifies that malicious <script> tags and executable code are stripped."""
    malicious = """
    <div>
        <h1>Safe Header</h1>
        <script>alert('pwned');</script>
        <p>Legitimate content</p>
    </div>
    """
    res = ArtifactService.validate_and_sanitize("html", "Test Widget", malicious)
    assert "<script>" not in res["content"]
    assert "alert('pwned')" not in res["content"]
    assert "<h1>Safe Header</h1>" in res["content"]
    assert "<p>Legitimate content</p>" in res["content"]


def test_sanitize_html_strips_event_handlers():
    """Verifies that inline JS event handlers (onload, onerror, onclick) are stripped."""
    malicious = """
    <img src="https://example.com/pic.png" onerror="alert('xss')" alt="photo" />
    <button onclick="stealCookies()" class="btn">Click me</button>
    """
    res = ArtifactService.validate_and_sanitize("html", "Event Test", malicious)
    assert "onerror=" not in res["content"]
    assert "onclick=" not in res["content"]
    assert 'class="btn"' in res["content"]
    assert 'alt="photo"' in res["content"]


def test_sanitize_html_blocks_javascript_pseudo_protocols():
    """Verifies that href="javascript:..." links are stripped."""
    malicious = '<a href="javascript:alert(document.cookie)">Malicious Link</a>'
    res = ArtifactService.validate_and_sanitize("html", "Link Test", malicious)
    assert "javascript:" not in res["content"]
    assert "Malicious Link" in res["content"]


def test_sanitize_html_preserves_styles_and_semantic_tags():
    """Verifies that CSS in <style> tags and semantic HTML tables/cards are retained."""
    safe_markup = """
    <style>
        .metric-card { background-color: #0f172a; color: #10b981; padding: 1rem; }
    </style>
    <div class="metric-card" id="card-1">
        <h2>PMF Engine</h2>
        <table>
            <thead><tr><th>Metric</th><th>Target</th></tr></thead>
            <tbody><tr><td>Retention</td><td>> 40%</td></tr></tbody>
        </table>
    </div>
    """
    res = ArtifactService.validate_and_sanitize("html", "PMF Dashboard", safe_markup)
    assert ".metric-card" in res["content"]
    assert "<table>" in res["content"]
    assert "PMF Engine" in res["content"]
    assert 'id="card-1"' in res["content"]
    assert res["type"] == "html"
    assert res["title"] == "PMF Dashboard"


def test_sanitize_markdown_normalizes_content():
    """Verifies null byte removal and newline normalization for markdown."""
    raw_md = "# Title\r\n\r\nHello\x00 World!\r\n* Bullet"
    res = ArtifactService.validate_and_sanitize("markdown", "Strategy Guide", raw_md)
    assert "\x00" not in res["content"]
    assert "\r\n" not in res["content"]
    assert "# Title\n\nHello World!\n* Bullet" == res["content"]
    assert res["type"] == "markdown"


def test_validate_and_sanitize_defaults_and_truncation():
    """Verifies fallback type and title handling."""
    res = ArtifactService.validate_and_sanitize("invalid_type", "", "content")
    assert res["type"] == "markdown"
    assert res["title"] == "Generated Artifact"

    long_title = "A" * 300
    res_long = ArtifactService.validate_and_sanitize("html", long_title, "content")
    assert len(res_long["title"]) == 255


def test_format_download_filenames_and_mime():
    """Verifies download filename slugification and MIME media types."""
    html_art = Artifact(
        id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        type="html",
        title="Super Growth Matrix / 2026!",
        content="<html><body>Matrix</body></html>",
    )
    content, filename, media_type = ArtifactService.format_download(html_art)
    assert filename == "super_growth_matrix___2026.html"
    assert media_type == "text/html; charset=utf-8"
    assert content == html_art.content

    md_art = Artifact(
        id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        type="markdown",
        title="Ship 30: Viral Loops",
        content="# Viral Loops Essay",
    )
    content_md, filename_md, media_type_md = ArtifactService.format_download(md_art)
    assert filename_md == "ship_30__viral_loops.md"
    assert media_type_md == "text/markdown; charset=utf-8"


@pytest.mark.asyncio
async def test_get_artifact_api_and_404(client_and_db):
    """Tests GET /api/artifacts/{artifact_id} endpoint and 404 error envelope."""
    client, db_session = client_and_db

    # 1. Create session and artifact in DB
    user = User(anonymous_identifier=f"anon_test_{uuid.uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, title="Artifact Test Session")
    db_session.add(session)
    await db_session.flush()

    service = ArtifactService(db_session)
    artifact = await service.create_artifact(
        session_id=session.id,
        type="html",
        title="Interactive Metric Card",
        content="<div class='card'>Retention: 60%</div>",
    )
    await db_session.commit()

    # 2. Query endpoint using client
    res = await client.get(f"/api/artifacts/{artifact.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(artifact.id)
    assert data["title"] == "Interactive Metric Card"
    assert data["type"] == "html"
    assert "Retention: 60%" in data["content"]

    # 3. Test non-existent artifact produces structured 404
    fake_id = uuid.uuid4()
    res_404 = await client.get(f"/api/artifacts/{fake_id}")
    assert res_404.status_code == 404
    err = res_404.json()
    assert err["error"]["code"] == "ARTIFACT_NOT_FOUND"
    assert str(fake_id) in err["error"]["message"]


@pytest.mark.asyncio
async def test_download_artifact_api(client_and_db):
    """Tests GET /api/artifacts/{artifact_id}/download endpoint headers and content."""
    client, db_session = client_and_db

    user = User(anonymous_identifier=f"anon_dl_{uuid.uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, title="Download Test Session")
    db_session.add(session)
    await db_session.flush()

    service = ArtifactService(db_session)
    artifact = await service.create_artifact(
        session_id=session.id,
        type="markdown",
        title="Product Strategy Playbook",
        content="# Playbook\n\n1. Validate demand\n2. Iterate quickly",
    )
    await db_session.commit()

    res = await client.get(f"/api/artifacts/{artifact.id}/download")
    assert res.status_code == 200
    assert "attachment; filename=\"product_strategy_playbook.md\"" in res.headers.get("content-disposition", "")
    assert "text/markdown" in res.headers.get("content-type", "")
    assert res.text == artifact.content


@pytest.mark.asyncio
async def test_list_session_artifacts_api(client_and_db):
    """Tests GET /api/artifacts/session/{session_id} listing endpoint."""
    client, db_session = client_and_db

    user = User(anonymous_identifier=f"anon_list_{uuid.uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, title="List Test Session")
    db_session.add(session)
    await db_session.flush()

    service = ArtifactService(db_session)
    await service.create_artifact(
        session_id=session.id,
        type="markdown",
        title="Doc 1",
        content="Content 1",
    )
    await service.create_artifact(
        session_id=session.id,
        type="html",
        title="Widget 2",
        content="<div>Widget 2</div>",
    )
    await db_session.commit()

    res = await client.get(f"/api/artifacts/session/{session.id}")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    titles = [a["title"] for a in data]
    assert "Doc 1" in titles
    assert "Widget 2" in titles


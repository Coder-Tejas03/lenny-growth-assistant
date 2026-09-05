"""
Lenny Growth Assistant — Artifact Service

Provides validation, defense-in-depth sanitization via bleach, persistence,
and download packaging for generated Markdown and HTML/CSS artifacts.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid
import bleach
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Artifact
from app.db.repositories.artifact_repo import ArtifactRepository

logger = logging.getLogger("lenny_assistant.artifact_service")

# Safe HTML tags permitted for rich rendered visual artifacts
# Deliberately excludes <script>, <iframe>, <frame>, <object>, <embed>, <base>, <form>
ALLOWED_HTML_TAGS = [
    "html",
    "head",
    "body",
    "style",
    "title",
    "meta",
    "div",
    "span",
    "p",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "th",
    "td",
    "caption",
    "code",
    "pre",
    "blockquote",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "s",
    "small",
    "mark",
    "hr",
    "br",
    "a",
    "img",
    "svg",
    "path",
    "circle",
    "rect",
    "line",
    "polyline",
    "polygon",
    "section",
    "article",
    "nav",
    "aside",
    "header",
    "footer",
    "main",
    "figure",
    "figcaption",
    "details",
    "summary",
    "button",
]

# Safe attributes permitted on HTML tags (omit inline style attribute to avoid NoCssSanitizerWarning; style tags are preserved)
ALLOWED_HTML_ATTRIBUTES = {
    "*": ["class", "id", "title", "aria-hidden", "aria-label", "role"],
    "a": ["href", "target", "rel"],
    "img": ["src", "alt", "width", "height", "loading"],
    "svg": ["viewBox", "width", "height", "fill", "stroke", "stroke-width", "xmlns"],
    "path": ["d", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin"],
    "meta": ["charset", "name", "content"],
}

# Safe URL protocols permitted in href and src attributes (strictly excludes javascript:)
ALLOWED_PROTOCOLS = ["http", "https", "mailto", "data"]


class ArtifactService:
    """
    Manages validation, sanitization, database persistence, and download
    formatting for conversational artifacts.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.artifact_repo = ArtifactRepository(db)

    @classmethod
    def validate_and_sanitize(
        cls,
        type: str,
        title: str,
        content: str,
    ) -> Dict[str, str]:
        """
        Validates artifact parameters and applies backend defense-in-depth
        sanitization to untrusted generated content before persistence.
        """
        # 1. Normalize type
        normalized_type = (type or "markdown").lower().strip()
        if normalized_type not in ("markdown", "html"):
            normalized_type = "markdown"

        # 2. Normalize title
        clean_title = (title or "").strip()
        if not clean_title:
            clean_title = "Generated Artifact"
        if len(clean_title) > 255:
            clean_title = clean_title[:255]

        # 3. Sanitize content
        raw_content = content or ""
        # Strip null bytes
        clean_content = raw_content.replace("\x00", "")

        if normalized_type == "html":
            # 3a. Strip complete script blocks including inner executable code
            clean_content = re.sub(
                r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",
                "",
                clean_content,
                flags=re.IGNORECASE,
            )
            # 3b. Strip active script tags, dangerous tags, and event handlers via bleach
            clean_content = bleach.clean(
                clean_content,
                tags=ALLOWED_HTML_TAGS,
                attributes=ALLOWED_HTML_ATTRIBUTES,
                protocols=ALLOWED_PROTOCOLS,
                strip=True,
            )
        else:
            # Markdown: normalize carriage returns
            clean_content = clean_content.replace("\r\n", "\n").replace("\r", "\n")

        return {
            "type": normalized_type,
            "title": clean_title,
            "content": clean_content,
        }

    async def get_artifact(self, artifact_id: uuid.UUID) -> Optional[Artifact]:
        """Loads a single artifact by its primary UUID."""
        return await self.artifact_repo.get_by_id(artifact_id)

    async def list_session_artifacts(self, session_id: uuid.UUID) -> List[Artifact]:
        """Loads all artifacts associated with a session, ordered by newest first."""
        return await self.artifact_repo.list_by_session(session_id)

    async def create_artifact(
        self,
        session_id: uuid.UUID,
        type: str,
        title: str,
        content: str,
        message_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Artifact:
        """Sanitizes and persists an artifact record to the database."""
        sanitized = self.validate_and_sanitize(type, title, content)
        artifact = await self.artifact_repo.create(
            session_id=session_id,
            message_id=message_id,
            type=sanitized["type"],
            title=sanitized["title"],
            content=sanitized["content"],
            metadata=metadata or {},
        )
        await self.db.flush()
        return artifact

    @staticmethod
    def format_download(artifact: Artifact) -> Tuple[str, str, str]:
        """
        Prepares an artifact for safe client download.
        Returns:
            Tuple of (raw_content_string, filename, content_type)
        """
        # Create safe filename slug from title
        slug = re.sub(r"[^a-zA-Z0-9_\-]", "_", artifact.title.lower()).strip("_")
        if not slug:
            slug = "artifact"
        # Shorten if too long
        slug = slug[:48]

        if artifact.type == "html":
            filename = f"{slug}.html"
            media_type = "text/html; charset=utf-8"
        else:
            filename = f"{slug}.md"
            media_type = "text/markdown; charset=utf-8"

        return artifact.content, filename, media_type

"""
Lenny Growth Assistant — Transcript & Metadata Parser

Extracts structured episode metadata (guest, title, date, URLs, keywords) from
YAML frontmatter and isolates the spoken transcript dialogue.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
import re
from typing import Any, Dict, Optional
import yaml


@dataclass
class ParsedEpisode:
    """Represents normalized metadata and raw transcript content for an episode."""

    title: str
    guest_name: str
    source_url: Optional[str] = None
    publication_date: Optional[date] = None
    episode_number: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    transcript_text: str = ""


class TranscriptParseError(Exception):
    """Raised when a transcript file cannot be parsed or lacks mandatory fields."""

    pass


def _extract_episode_number(title: str, frontmatter: Dict[str, Any]) -> Optional[int]:
    """Attempts to extract an integer episode number from frontmatter or title."""
    if "episode_number" in frontmatter:
        try:
            return int(frontmatter["episode_number"])
        except (ValueError, TypeError):
            pass

    # Match patterns like "#42", "Episode 42", "Ep. 42"
    match = re.search(r"(?:#|Episode\s+|Ep\.\s*)(\d+)", title, re.IGNORECASE)
    if match:
        return int(match.group(1))

    return None


def _parse_publication_date(val: Any) -> Optional[date]:
    """Converts diverse date representations (str, date, datetime) into a datetime.date."""
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        val = val.strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%B %d, %Y", "%b %d, %Y"):
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
    return None


def parse_transcript_content(content: str, filename_hint: str = "") -> ParsedEpisode:
    """
    Parses the raw string content of a transcript file.

    Extracts:
    1. YAML frontmatter delimited by opening and closing '---'.
    2. Episode title, guest, publication date, source URL.
    3. Spoken dialogue body with timestamp anchors intact.
    """
    if not content or not content.strip():
        raise TranscriptParseError("Transcript content is empty.")

    frontmatter: Dict[str, Any] = {}
    body = content

    # Check for YAML frontmatter at the beginning of the content
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if fm_match:
        fm_text = fm_match.group(1)
        body = fm_match.group(2)
        try:
            loaded_yaml = yaml.safe_load(fm_text)
            if isinstance(loaded_yaml, dict):
                frontmatter = loaded_yaml
        except yaml.YAMLError as exc:
            raise TranscriptParseError(f"Failed to parse YAML frontmatter: {exc}") from exc

    # 1. Resolve Title
    title = (
        frontmatter.get("title")
        or frontmatter.get("episode_title")
        or ""
    )
    if not title:
        # Try extracting from the first H1 header in markdown body: "# Episode Title"
        h1_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        if h1_match:
            title = h1_match.group(1).strip()
        elif filename_hint:
            # Derive title from filename (e.g. adam-fishman.md -> Adam Fishman)
            title = Path(filename_hint).stem.replace("-", " ").replace("_", " ").title()
        else:
            title = "Untitled Episode"

    # 2. Resolve Guest Name
    guest_name = (
        frontmatter.get("guest")
        or frontmatter.get("guest_name")
        or ""
    )
    if not guest_name:
        # Try finding guest from title pattern: "... | Guest Name (...)"
        pipe_match = re.search(r"\|\s*([^(\n]+)", title)
        if pipe_match:
            guest_name = pipe_match.group(1).strip()
        else:
            guest_name = "Lenny Rachitsky & Guest"

    # 3. Resolve Source / YouTube URL
    source_url = (
        frontmatter.get("youtube_url")
        or frontmatter.get("source_url")
        or frontmatter.get("url")
        or (f"https://www.youtube.com/watch?v={frontmatter['video_id']}" if "video_id" in frontmatter else None)
    )

    # 4. Resolve Publication Date
    pub_date = _parse_publication_date(
        frontmatter.get("publish_date") or frontmatter.get("date") or frontmatter.get("publication_date")
    )

    # 5. Resolve Episode Number
    episode_num = _extract_episode_number(title, frontmatter)

    # 6. Metadata bag (excluding fields already extracted as top-level columns)
    metadata: Dict[str, Any] = {}
    known_keys = {"title", "episode_title", "guest", "guest_name", "youtube_url", "source_url", "url", "publish_date", "date", "publication_date", "episode_number"}
    for k, v in frontmatter.items():
        if k not in known_keys:
            metadata[k] = v

    # Clean body: strip leading '# Title' and '## Transcript' headers if present
    cleaned_body = body.strip()
    cleaned_body = re.sub(r"^#\s+[^\n]+\n+", "", cleaned_body)
    cleaned_body = re.sub(r"^##\s+Transcript\s*\n+", "", cleaned_body, flags=re.IGNORECASE)
    cleaned_body = cleaned_body.strip()

    return ParsedEpisode(
        title=str(title).strip(),
        guest_name=str(guest_name).strip(),
        source_url=str(source_url).strip() if source_url else None,
        publication_date=pub_date,
        episode_number=episode_num,
        metadata=metadata,
        transcript_text=cleaned_body,
    )


def parse_transcript_file(file_path: Path | str) -> ParsedEpisode:
    """Reads a transcript markdown file from disk and parses it."""
    path = Path(file_path)
    if not path.is_file():
        raise TranscriptParseError(f"Transcript file not found: {path}")

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as exc:
        raise TranscriptParseError(f"Could not read file {path}: {exc}") from exc

    return parse_transcript_content(content, filename_hint=path.name)

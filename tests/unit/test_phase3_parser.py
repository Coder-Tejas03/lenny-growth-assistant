"""
Lenny Growth Assistant — Phase 3 Parser Unit Tests

Tests YAML frontmatter extraction, metadata normalization, date parsing,
dialogue isolation, and transcript file discovery.
"""

from datetime import date
from pathlib import Path
import tempfile
import pytest

from ingestion.parser import (
    ParsedEpisode,
    TranscriptParseError,
    parse_transcript_content,
    parse_transcript_file,
    _extract_episode_number,
    _parse_publication_date,
)
from ingestion.fetcher import discover_transcript_files


SAMPLE_FIXTURE_PATH = Path("tests/fixtures/transcripts/sample_transcript.md")


def test_parse_sample_transcript_file():
    """Verifies parsing of our realistic sample transcript fixture."""
    parsed = parse_transcript_file(SAMPLE_FIXTURE_PATH)

    assert isinstance(parsed, ParsedEpisode)
    assert parsed.guest_name == "Adam Fishman"
    assert "How to build a high-performing growth team" in parsed.title
    assert parsed.publication_date == date(2022, 10, 13)
    assert parsed.source_url == "https://www.youtube.com/watch?v=wP8YyWH524A"
    assert parsed.metadata.get("video_id") == "wP8YyWH524A"
    assert parsed.metadata.get("duration_seconds") == 3946.0
    assert "onboarding" in parsed.metadata.get("keywords", [])

    # Verify transcript text has no YAML frontmatter or H1/H2 headers
    assert "---" not in parsed.transcript_text
    assert "# How to build" not in parsed.transcript_text
    assert "## Transcript" not in parsed.transcript_text
    assert "Onboarding is the only part of your product experience" in parsed.transcript_text
    assert "Adam Fishman (00:00:00):" in parsed.transcript_text


def test_parse_missing_frontmatter_fallback():
    """Verifies graceful fallback when frontmatter is absent."""
    raw_markdown = """# Lenny's Podcast with Shreyas Doshi

Shreyas Doshi (00:01:00):
High-agency people don't wait for permission.
"""
    parsed = parse_transcript_content(raw_markdown, filename_hint="shreyas-doshi.md")
    assert parsed.title == "Lenny's Podcast with Shreyas Doshi"
    assert parsed.guest_name == "Lenny Rachitsky & Guest"
    assert parsed.publication_date is None
    assert "High-agency people don't wait for permission" in parsed.transcript_text


def test_parse_title_with_guest_pipe():
    """Verifies guest extraction from title pipe formatting."""
    content = """---
title: How to Find PMF | Rahul Vohra (Superhuman)
---
Rahul Vohra (00:00:10):
The survey asks how disappointed users would be.
"""
    parsed = parse_transcript_content(content)
    assert parsed.title == "How to Find PMF | Rahul Vohra (Superhuman)"
    assert parsed.guest_name == "Rahul Vohra"
    assert "The survey asks how disappointed" in parsed.transcript_text


def test_parse_date_formats():
    """Verifies date normalizer across common date formats."""
    assert _parse_publication_date("2023-05-12") == date(2023, 5, 12)
    assert _parse_publication_date("May 12, 2023") == date(2023, 5, 12)
    assert _parse_publication_date(date(2023, 5, 12)) == date(2023, 5, 12)
    assert _parse_publication_date("invalid-date-string") is None
    assert _parse_publication_date(None) is None


def test_extract_episode_number():
    """Verifies episode number extraction heuristics."""
    assert _extract_episode_number("Episode 42: Scaling Startups", {}) == 42
    assert _extract_episode_number("Scaling Startups #105", {}) == 105
    assert _extract_episode_number("Scaling Startups", {"episode_number": 88}) == 88
    assert _extract_episode_number("No Number Here", {}) is None


def test_empty_content_raises_error():
    """Verifies that empty transcript strings raise TranscriptParseError."""
    with pytest.raises(TranscriptParseError, match="content is empty"):
        parse_transcript_content("   \n\n  ")


def test_malformed_yaml_raises_error():
    """Verifies that broken YAML syntax raises TranscriptParseError."""
    broken_yaml = """---
title: [unclosed bracket
guest: Broken
---
Body text
"""
    with pytest.raises(TranscriptParseError, match="Failed to parse YAML frontmatter"):
        parse_transcript_content(broken_yaml)


def test_discover_transcript_files():
    """Verifies transcript discovery filters out README and non-transcript markdown."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "README.md").write_text("# Readme")
        (root / "CLAUDE.md").write_text("# Claude instructions")
        
        ep1_dir = root / "episodes" / "adam-fishman"
        ep1_dir.mkdir(parents=True)
        (ep1_dir / "transcript.md").write_text("transcript 1")
        
        ep2_dir = root / "episodes" / "elena-verna"
        ep2_dir.mkdir(parents=True)
        (ep2_dir / "transcript.md").write_text("transcript 2")

        discovered = discover_transcript_files(root)
        filenames = [p.name for p in discovered]
        assert len(discovered) == 2
        assert "transcript.md" in filenames
        assert "README.md" not in filenames
        assert "CLAUDE.md" not in filenames

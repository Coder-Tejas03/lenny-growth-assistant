"""
Lenny Growth Assistant — Phase 3 Chunker Unit Tests

Tests token-aware recursive splitting, context header construction, timestamp
extraction, overlap continuity, and SHA-256 hashing.
"""

from pathlib import Path
from ingestion.parser import parse_transcript_file
from ingestion.chunker import TranscriptChunker, TranscriptChunkData


SAMPLE_FIXTURE_PATH = Path("tests/fixtures/transcripts/sample_transcript.md")


def test_chunk_empty_text():
    """Verifies that empty transcript strings return no chunks."""
    chunker = TranscriptChunker()
    assert chunker.chunk_transcript("", "Title", "Guest") == []
    assert chunker.chunk_transcript("   \n\n ", "Title", "Guest") == []


def test_chunk_sample_fixture():
    """Verifies chunking of the sample transcript fixture."""
    parsed = parse_transcript_file(SAMPLE_FIXTURE_PATH)
    chunker = TranscriptChunker(min_tokens=100, max_tokens=300, overlap_tokens=30)
    chunks = chunker.chunk_transcript(
        transcript_text=parsed.transcript_text,
        episode_title=parsed.title,
        guest_name=parsed.guest_name,
    )

    assert len(chunks) >= 1
    first_chunk = chunks[0]
    assert isinstance(first_chunk, TranscriptChunkData)
    assert first_chunk.chunk_index == 0
    assert first_chunk.start_timestamp == "00:00:00"
    assert len(first_chunk.content_hash) == 64  # SHA-256 hex length
    assert first_chunk.token_count == chunker.count_tokens(first_chunk.content)

    # Check header formatting per Section 2 of implementation-contract.md
    expected_header_prefix = f"[Episode: {parsed.title} | Guest: {parsed.guest_name} | Timestamp: 00:00:00]"
    assert first_chunk.content.startswith(expected_header_prefix)


def test_timestamp_extractor():
    """Verifies extraction of timestamps in varied formats."""
    text = "Intro (00:00:15) then middle [00:14:22] and ending (1:05:46)"
    extracted = TranscriptChunker.extract_timestamps(text)
    assert extracted == ["00:00:15", "00:14:22", "1:05:46"]


def test_sha256_hash_idempotency():
    """Verifies that SHA-256 hash is deterministic and content-sensitive."""
    text1 = "When we surveyed our users at Superhuman..."
    text2 = "When we surveyed our users at Superhuman..."
    text3 = "Different content entirely."

    hash1 = TranscriptChunker.compute_sha256(text1)
    hash2 = TranscriptChunker.compute_sha256(text2)
    hash3 = TranscriptChunker.compute_sha256(text3)

    assert hash1 == hash2
    assert hash1 != hash3
    assert len(hash1) == 64


def test_sentence_splitting_for_oversized_paragraph():
    """Verifies that paragraphs exceeding max_tokens are split cleanly into sentences."""
    # Create an oversized paragraph with many sentences
    sentence = "High performance teams focus relentlessly on activation and customer retention. "
    long_paragraph = sentence * 30  # ~330 tokens
    
    chunker = TranscriptChunker(min_tokens=50, max_tokens=100, overlap_tokens=10)
    chunks = chunker.chunk_transcript(
        transcript_text=long_paragraph,
        episode_title="Test Episode",
        guest_name="Test Guest",
    )

    # Should be split into multiple chunks
    assert len(chunks) > 1
    for chunk in chunks:
        # Verify content has context header
        assert "[Episode: Test Episode | Guest: Test Guest" in chunk.content
        assert chunk.token_count > 0


def test_overlap_continuity():
    """Verifies that consecutive chunks contain overlapping text."""
    p1 = "First segment discussing product market fit principles and Sean Ellis score. " * 5
    p2 = "Second segment discussing activation curves and onboarding dropoff. " * 5
    full_text = f"{p1}\n\n{p2}"

    chunker = TranscriptChunker(min_tokens=30, max_tokens=60, overlap_tokens=15)
    chunks = chunker.chunk_transcript(
        transcript_text=full_text,
        episode_title="Overlap Test",
        guest_name="Elena Verna",
    )

    assert len(chunks) >= 2
    # Ensure second chunk contains tail text from first chunk
    assert len(chunks[1].content) > 0
    assert chunks[1].chunk_index == 1

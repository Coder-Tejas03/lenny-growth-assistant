"""
Lenny Growth Assistant — Token-Aware Recursive Transcript Chunker

Splits transcript dialogue into semantically bounded, overlapping chunks
(500–800 tokens, 100-token overlap) using tiktoken (cl100k_base), extracts timestamp
intervals, prepends citation context headers, and computes SHA-256 content hashes.
"""

from dataclasses import dataclass
import hashlib
import re
from typing import List, Optional, Tuple
import tiktoken

# Encoding used by OpenAI text-embedding-3-small and GPT-4o
DEFAULT_ENCODING = "cl100k_base"
TARGET_MIN_TOKENS = 500
TARGET_MAX_TOKENS = 800
TARGET_OVERLAP_TOKENS = 100


@dataclass
class TranscriptChunkData:
    """A prepared transcript chunk ready for embedding and database insertion."""

    chunk_index: int
    content: str
    token_count: int
    content_hash: str
    start_timestamp: Optional[str] = None
    end_timestamp: Optional[str] = None


class TranscriptChunker:
    """Token-aware recursive text splitter specialized for podcast dialogue."""

    def __init__(
        self,
        min_tokens: int = TARGET_MIN_TOKENS,
        max_tokens: int = TARGET_MAX_TOKENS,
        overlap_tokens: int = TARGET_OVERLAP_TOKENS,
        encoding_name: str = DEFAULT_ENCODING,
    ):
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.tokenizer = tiktoken.get_encoding(encoding_name)

    def count_tokens(self, text: str) -> int:
        """Returns the exact number of tokens in the given text."""
        return len(self.tokenizer.encode(text, disallowed_special=()))

    @staticmethod
    def extract_timestamps(text: str) -> List[str]:
        """
        Extracts timestamp anchors matching (HH:MM:SS) or (MM:SS) or [HH:MM:SS].
        Example: 'Adam Fishman (00:14:22):' -> ['00:14:22']
        """
        pattern = r"[\(\[](\d{1,2}:\d{2}(?::\d{2})?)[\)\]]"
        return re.findall(pattern, text)

    @staticmethod
    def compute_sha256(text: str) -> str:
        """Computes a hexadecimal SHA-256 hash of the content."""
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Splits dialogue on double newlines or speaker turn boundaries."""
        # Split on double newline first
        raw_paragraphs = re.split(r"\n\s*\n", text)
        cleaned: List[str] = []
        for p in raw_paragraphs:
            p_str = p.strip()
            if p_str:
                cleaned.append(p_str)
        return cleaned

    def _split_into_sentences(self, text: str) -> List[str]:
        """Splits text on sentence boundaries."""
        sentences = re.split(r"(?<=[.?!])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def chunk_transcript(
        self,
        transcript_text: str,
        episode_title: str,
        guest_name: str,
    ) -> List[TranscriptChunkData]:
        """
        Recursively chunks transcript text into target token ranges.
        Prepends the citation context header to every chunk.
        """
        if not transcript_text or not transcript_text.strip():
            return []

        paragraphs = self._split_into_paragraphs(transcript_text)
        if not paragraphs:
            return []

        # 1. Group paragraphs into raw text slices based on token count
        raw_slices: List[str] = []
        current_paragraphs: List[str] = []
        current_tokens = 0

        for p in paragraphs:
            p_tokens = self.count_tokens(p)

            # If a single paragraph exceeds max_tokens, split it by sentence
            if p_tokens > self.max_tokens:
                if current_paragraphs:
                    raw_slices.append("\n\n".join(current_paragraphs))
                    current_paragraphs = []
                    current_tokens = 0

                sentences = self._split_into_sentences(p)
                current_sent: List[str] = []
                sent_tokens = 0
                for s in sentences:
                    s_tok = self.count_tokens(s)
                    if sent_tokens + s_tok > self.max_tokens and current_sent:
                        raw_slices.append(" ".join(current_sent))
                        current_sent = [s]
                        sent_tokens = s_tok
                    else:
                        current_sent.append(s)
                        sent_tokens += s_tok

                if current_sent:
                    raw_slices.append(" ".join(current_sent))
                continue

            if current_tokens + p_tokens > self.max_tokens and current_paragraphs:
                raw_slices.append("\n\n".join(current_paragraphs))
                current_paragraphs = [p]
                current_tokens = p_tokens
            else:
                current_paragraphs.append(p)
                current_tokens += p_tokens

        if current_paragraphs:
            raw_slices.append("\n\n".join(current_paragraphs))

        # 2. Add overlap and construct chunks
        chunks: List[TranscriptChunkData] = []
        prev_tail_text = ""

        for idx, raw_content in enumerate(raw_slices):
            # If we have an overlap from previous slice, prepend it
            if prev_tail_text:
                full_body = prev_tail_text + "\n\n" + raw_content
            else:
                full_body = raw_content

            # Extract timestamps present in this chunk body
            timestamps = self.extract_timestamps(full_body)
            start_ts = timestamps[0] if timestamps else None
            end_ts = timestamps[-1] if timestamps and len(timestamps) > 1 else start_ts

            # Prepare citation context header per Section 2 of implementation-contract.md:
            # [Episode: {title} | Guest: {guest} | Timestamp: {start_timestamp}]
            ts_str = start_ts or "00:00:00"
            header = f"[Episode: {episode_title} | Guest: {guest_name} | Timestamp: {ts_str}]\n"
            final_content = header + full_body

            token_count = self.count_tokens(final_content)
            content_hash = self.compute_sha256(final_content)

            chunk = TranscriptChunkData(
                chunk_index=idx,
                content=final_content,
                token_count=token_count,
                content_hash=content_hash,
                start_timestamp=start_ts,
                end_timestamp=end_ts,
            )
            chunks.append(chunk)

            # Compute overlap tail text for the next chunk
            if self.overlap_tokens > 0:
                tokens = self.tokenizer.encode(raw_content, disallowed_special=())
                if len(tokens) > self.overlap_tokens:
                    tail_tokens = tokens[-self.overlap_tokens:]
                    prev_tail_text = self.tokenizer.decode(tail_tokens).strip()
                else:
                    prev_tail_text = raw_content
            else:
                prev_tail_text = ""

        return chunks

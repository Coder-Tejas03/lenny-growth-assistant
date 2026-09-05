"""
Lenny Growth Assistant — Retrieval & Citation Data Contracts

Defines validated Pydantic models for retrieved evidence, citations,
and retrieval outcomes matching Section 7 of docs/implementation-contract.md.
"""

from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

# Canonical abstention message per Section 5 of docs/implementation-contract.md
CANONICAL_ABSTENTION_MESSAGE = (
    "I couldn't find sufficient evidence in Lenny's podcast archive to answer this reliably. "
    "Try asking about a product or growth topic covered in the podcast transcripts."
)


class Citation(BaseModel):
    """
    JSON Citation payload returned to the frontend and persisted with messages.
    Matches Section 7 of docs/implementation-contract.md.
    """

    model_config = ConfigDict(frozen=True)

    chunk_id: uuid.UUID = Field(..., description="Unique UUID of the supporting transcript chunk")
    episode_title: str = Field(..., description="Title of the source podcast episode")
    guest_name: str = Field(..., description="Guest featured in the episode")
    timestamp: Optional[str] = Field(None, description="Start timestamp of the cited passage (e.g. 14:22)")
    source_url: Optional[str] = Field(None, description="Direct URL to episode audio or video")
    similarity: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")
    excerpt: str = Field(..., description="Representative verbatim text snippet from the chunk")

    @property
    def in_text_reference(self) -> str:
        """
        Formats in-text markdown citation anchor:
        [Episode: Guest Name, Timestamp/Topic]
        """
        time_part = f", {self.timestamp}" if self.timestamp else ""
        return f"[{self.episode_title}: {self.guest_name}{time_part}]"


class EvidenceChunk(BaseModel):
    """
    Rich evidence object representing a single retrieved transcript chunk
    prior to or during prompt formulation.
    """

    model_config = ConfigDict(frozen=True)

    chunk_id: uuid.UUID = Field(..., description="Database UUID of the chunk")
    episode_title: str = Field(..., description="Title of the episode")
    guest_name: str = Field(..., description="Guest speaker name")
    content: str = Field(..., description="Full text content of the chunk")
    timestamp: Optional[str] = Field(None, description="Start timestamp of dialogue (e.g. 00:14:22)")
    source_url: Optional[str] = Field(None, description="Web URL to source material")
    similarity: float = Field(..., description="Calculated cosine similarity against user query")

    def to_citation(self, excerpt_len: int = 220) -> Citation:
        """
        Converts the evidence chunk into a user-facing Citation object
        with a clean, truncated excerpt.
        """
        cleaned_text = " ".join(self.content.split())
        # Remove context header if present in stored content
        if cleaned_text.startswith("[Episode:") and "]" in cleaned_text:
            cleaned_text = cleaned_text.split("]", 1)[1].strip()

        if len(cleaned_text) > excerpt_len:
            excerpt = cleaned_text[:excerpt_len].rsplit(" ", 1)[0] + "..."
        else:
            excerpt = cleaned_text

        return Citation(
            chunk_id=self.chunk_id,
            episode_title=self.episode_title,
            guest_name=self.guest_name,
            timestamp=self.timestamp,
            source_url=self.source_url,
            similarity=self.similarity,
            excerpt=excerpt,
        )

    @property
    def formatted_citation_anchor(self) -> str:
        """Helper returning in-text bracket citation."""
        time_part = f", {self.timestamp}" if self.timestamp else ""
        return f"[{self.episode_title}: {self.guest_name}{time_part}]"


class RetrievalResult(BaseModel):
    """
    Comprehensive outcome of a retrieval operation, encapsulating retrieved
    evidence, formatted citations, abstention state, and query latency.
    """

    query: str = Field(..., description="Original user search query")
    chunks: List[EvidenceChunk] = Field(default_factory=list, description="Ranked evidence chunks meeting cutoff")
    citations: List[Citation] = Field(default_factory=list, description="Derived citation objects for display")
    is_sufficient: bool = Field(default=True, description="Whether sufficient grounded evidence was found")
    abstention_message: Optional[str] = Field(
        default=None, description="Canonical abstention text if is_sufficient is False"
    )
    query_latency_ms: float = Field(default=0.0, description="End-to-end retrieval and vector query time in milliseconds")

    @classmethod
    def abstain(cls, query: str, latency_ms: float = 0.0) -> "RetrievalResult":
        """Factory method constructing an explicit abstention result."""
        return cls(
            query=query,
            chunks=[],
            citations=[],
            is_sufficient=False,
            abstention_message=CANONICAL_ABSTENTION_MESSAGE,
            query_latency_ms=latency_ms,
        )

    def format_context_for_prompt(self) -> str:
        """
        Formats all retrieved chunks into a standardized evidence block
        suitable for injection into LLM system or user prompts.
        """
        if not self.is_sufficient or not self.chunks:
            return "No relevant transcript evidence found."

        blocks = []
        for idx, chunk in enumerate(self.chunks, start=1):
            source_tag = chunk.formatted_citation_anchor
            blocks.append(
                f"--- Evidence Source [{idx}]: {source_tag} ---\n"
                f"Source URL: {chunk.source_url or 'N/A'}\n"
                f"Relevance Score: {chunk.similarity:.4f}\n"
                f"Content:\n{chunk.content}"
            )
        return "\n\n".join(blocks)

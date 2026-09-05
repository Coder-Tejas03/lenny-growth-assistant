"""
Lenny Growth Assistant — Phase 9 Ship 30 for 30 Content Engine Tests

Verifies:
- Essay length: approximately 1,250 words (bounds: 1,100 - 1,400 words).
- The Hook: first 2-3 lines contain immediate operational tension/curiosity gap without greetings.
- Short paragraphs: high-cadence reading rhythm (1 to 3 sentences per paragraph).
- Visual architecture: Markdown headers (## and ###).
- Bold anchors: bullet points begin with bold anchor words (**Anchor Word:**).
- In-text citations: [Episode Title: Guest Name, Timestamp or Topic].
- Actionable takeaway: concrete multi-step implementation checklist/framework at conclusion.
- Grounding: incorporates retrieved transcript evidence into essay claims.
- End-to-end streaming through PiAgentClient with mock and direct fallback.
"""

import re
import pytest
from app.agent.client import PiAgentClient
from app.agent.models import AgentRequestPayload, AgentSkill
from app.agent.skills import (
    SHIP30_SYSTEM_PROMPT,
    build_grounded_context_prompt,
    generate_mock_ship30_essay,
)
from app.retrieval.models import EvidenceChunk


def test_ship30_system_prompt_heuristics():
    """Verifies that the system prompt explicitly encodes all Ship 30 heuristics."""
    assert "1,250 words" in SHIP30_SYSTEM_PROMPT
    assert "The Hook" in SHIP30_SYSTEM_PROMPT
    assert "bold anchor words" in SHIP30_SYSTEM_PROMPT
    assert "Actionable Takeaway" in SHIP30_SYSTEM_PROMPT
    assert "[Episode Title: Guest Name, Timestamp or Topic]" in SHIP30_SYSTEM_PROMPT


def test_ship30_essay_word_count():
    """Verifies that the generated Ship 30 essay is approximately 1,250 words."""
    essay = generate_mock_ship30_essay("Product-Led Growth Flywheels")
    words = essay.split()
    word_count = len(words)

    # Must be approximately 1,250 words (within 1,100 to 1,400 words)
    assert 1100 <= word_count <= 1400, f"Word count was {word_count}, expected ~1,250 words"


def test_ship30_essay_hook_structure():
    """Verifies that the essay opens with a strong hook and zero introductory pleasantries."""
    essay = generate_mock_ship30_essay("Viral Loops and User Retention")
    lines = [line.strip() for line in essay.split("\n") if line.strip()]

    # First line is a bold title
    assert lines[0].startswith("# ")

    # Next 2-3 lines are the hook
    hook_paragraphs = lines[1:4]
    hook_text = " ".join(hook_paragraphs)

    # Must not contain filler openings
    forbidden_greetings = ["in this article", "welcome to", "hello", "today we will explore", "let's dive into"]
    for greeting in forbidden_greetings:
        assert greeting not in hook_text.lower()

    # Must contain tension / problem statement
    assert any(term in hook_text.lower() for term in ["bleeding", "trap", "fail", "vaporize", "flawed", "obsess"])


def test_ship30_essay_bold_anchors_and_headers():
    """Verifies presence of section headers and bold anchor words at the start of bullet points."""
    essay = generate_mock_ship30_essay("B2B SaaS Onboarding")

    # Check Markdown headers
    headers = re.findall(r"^#{2,3}\s+(.+)$", essay, re.MULTILINE)
    assert len(headers) >= 5, "Expected at least 5 major section/tactical headers"
    assert any("trap" in h.lower() for h in headers)
    assert any("playbook" in h.lower() or "takeaway" in h.lower() for h in headers)

    # Check bold anchor bullets: * **Anchor Word:** or 1. **Anchor Word:**
    bold_bullet_anchors = re.findall(r"^\*\s+\*\*([^*]+)\*\*\s+", essay, re.MULTILINE)
    assert len(bold_bullet_anchors) >= 4, f"Found only {len(bold_bullet_anchors)} bold bullet anchors"

    numbered_anchors = re.findall(r"^\d+\.\s+\*\*([^*]+)\*\*\s+", essay, re.MULTILINE)
    assert len(numbered_anchors) >= 4, f"Found only {len(numbered_anchors)} numbered anchors"


def test_ship30_essay_in_text_citations():
    """Verifies that the essay includes properly formatted transcript citations."""
    essay = generate_mock_ship30_essay("How to build product-market fit")

    # Match [Episode Title: Guest Name, Timestamp or Topic]
    citations = re.findall(r"\[([^:\]]+):\s*([^,\]]+),\s*([^\]]+)\]", essay)
    assert len(citations) >= 2, f"Found only {len(citations)} citations in essay"

    # Verify citation format contents
    for ep, guest, loc in citations:
        assert len(ep.strip()) > 3
        assert len(guest.strip()) > 2
        assert len(loc.strip()) >= 4


def test_ship30_essay_incorporates_custom_evidence():
    """Verifies that custom retrieved evidence is bound directly into the generated claims."""
    import uuid
    evidence = [
        EvidenceChunk(
            chunk_id=uuid.uuid4(),
            episode_id=uuid.uuid4(),
            episode_title="Superhuman PMF Engine",
            guest_name="Rahul Vohra",
            content="We created a survey asking users how they would feel if they could no longer use Superhuman.",
            timestamp="14:22",
            similarity=0.88,
        ),
        EvidenceChunk(
            chunk_id=uuid.uuid4(),
            episode_id=uuid.uuid4(),
            episode_title="B2B Growth Mechanics",
            guest_name="Elena Verna",
            content="Product-led growth is an organizational model, not just self-serve signups.",
            timestamp="28:10",
            similarity=0.84,
        ),
    ]

    essay = generate_mock_ship30_essay("How to measure product market fit", evidence)
    assert "Rahul Vohra" in essay
    assert "Elena Verna" in essay
    assert "[Superhuman PMF Engine: Rahul Vohra, 14:22]" in essay
    assert "[B2B Growth Mechanics: Elena Verna, 28:10]" in essay


def test_ship30_essay_actionable_conclusion():
    """Verifies that the essay concludes with a concrete multi-step operational checklist."""
    essay = generate_mock_ship30_essay("Pricing and Packaging")

    # Check for the 5-step playbook
    assert "5-Step Monday Morning Playbook" in essay or "Actionable Checklist" in essay
    assert "1. **" in essay
    assert "2. **" in essay
    assert "3. **" in essay
    assert "4. **" in essay
    assert "5. **" in essay


@pytest.mark.asyncio
async def test_pi_agent_client_streams_full_ship30_essay():
    """Verifies that PiAgentClient streams the ~1,250 word essay with status, citations, and done events."""
    import uuid
    client = PiAgentClient()
    payload = AgentRequestPayload(
        skill=AgentSkill.SHIP30_WRITER,
        query="The Ultimate Guide to Product-Led Growth",
        evidence=[
            EvidenceChunk(
                chunk_id=uuid.uuid4(),
                episode_id=uuid.uuid4(),
                episode_title="PLG Principles",
                guest_name="Elena Verna",
                content="Retention is the single input metric that proves product-market fit.",
                timestamp="10:00",
                similarity=0.85,
            )
        ],
        mock_mode=True,
    )

    events = []
    tokens = []
    async for event in client.stream_skill(payload):
        events.append(event.event)
        if event.event == "token":
            tokens.append(event.data.get("delta", ""))

    assert "status" in events
    assert "citation" in events
    assert "token" in events
    assert "done" in events

    full_essay = "".join(tokens)
    words = full_essay.split()
    assert len(words) >= 1100, f"Streamed essay only contained {len(words)} words"
    assert "##" in full_essay
    assert "* **" in full_essay
    assert "1. **" in full_essay

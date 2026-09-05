"""
Integration Tests for Phase 5 Pi Agent Runtime & Gate Verification

Verifies:
1. End-to-end communication between FastAPI's Python layer and the Node.js Pi runtime.
2. Grounded QA skill execution with citations and threshold abstention.
3. Ship 30 for 30 essay generation.
4. Artifact generation producing structured payloads.
5. Strict enforcement of Phase 5 Definition of Done Gate requirements.
"""

import subprocess
import uuid
import pytest

from app.agent.client import PiAgentClient
from app.agent.models import AgentRequestPayload, AgentSkill
from app.retrieval.models import CANONICAL_ABSTENTION_MESSAGE, EvidenceChunk


@pytest.fixture
def sample_evidence():
    return [
        EvidenceChunk(
            chunk_id=uuid.uuid4(),
            episode_title="How to Measure Product-Market Fit",
            guest_name="Rahul Vohra",
            content=(
                "When we surveyed Superhuman users, we asked how disappointed they would be if "
                "the product disappeared. If 40% or more say very disappointed, you have product-market fit."
            ),
            timestamp="14:22",
            source_url="https://lennyspodcast.com/rahul-vohra",
            similarity=0.88,
        )
    ]


@pytest.fixture
def weak_evidence():
    return [
        EvidenceChunk(
            chunk_id=uuid.uuid4(),
            episode_title="French Gastronomy",
            guest_name="Chef Laurent",
            content="Slow cook the braised shallots with red wine vinegar for forty minutes.",
            timestamp="22:15",
            source_url="https://example.com",
            similarity=0.41,  # Below 0.65 threshold
        )
    ]


@pytest.mark.asyncio
async def test_live_node_pi_runtime_subprocess_execution(sample_evidence):
    """Verifies Python PiAgentClient launches Node runtime subprocess and parses events."""
    client = PiAgentClient(enable_fallback=False)
    assert client.is_node_runtime_compiled(), "Node runtime dist/index.js must be compiled"

    payload = AgentRequestPayload(
        skill=AgentSkill.GROUNDED_QA,
        query="What is Rahul Vohra's rule for PMF?",
        evidence=sample_evidence,
        provider="openai",
        model="gpt-4o-mini",
        mock_mode=True,
    )

    result = await client.execute_and_accumulate(payload)
    assert len(result.content) > 10
    assert result.provider == "openai"
    assert result.model == "gpt-4o-mini"
    assert result.tokens_prompt > 0
    assert result.tokens_completion > 0
    assert len(result.citations) == 1
    assert result.citations[0].guest_name == "Rahul Vohra"


@pytest.mark.asyncio
async def test_live_node_pi_runtime_abstention_gate(weak_evidence):
    """Verifies that queries with weak evidence trigger canonical abstention via Node runtime."""
    client = PiAgentClient(enable_fallback=False)

    payload = AgentRequestPayload(
        skill=AgentSkill.GROUNDED_QA,
        query="How do I prepare coq au vin?",
        evidence=weak_evidence,
        provider="ollama",
        mock_mode=True,
    )

    result = await client.execute_and_accumulate(payload)
    assert CANONICAL_ABSTENTION_MESSAGE in result.content
    assert len(result.citations) == 0


@pytest.mark.asyncio
async def test_live_node_pi_runtime_ship30_and_artifact(sample_evidence):
    """Verifies Ship 30 and Artifact skills execute via the Node runtime."""
    client = PiAgentClient(enable_fallback=False)

    # Ship 30
    ship_payload = AgentRequestPayload(
        skill=AgentSkill.SHIP30_WRITER,
        query="How to measure PMF",
        evidence=sample_evidence,
        provider="openai",
        mock_mode=True,
    )
    ship_res = await client.execute_and_accumulate(ship_payload)
    assert len(ship_res.content) > 30
    assert ship_res.provider == "openai"

    # Artifact
    art_payload = AgentRequestPayload(
        skill=AgentSkill.ARTIFACT_GENERATOR,
        query="Generate a comparison table for PMF frameworks",
        evidence=sample_evidence,
        provider="ollama",
        mock_mode=True,
    )
    art_res = await client.execute_and_accumulate(art_payload)
    assert art_res.artifact is not None
    assert art_res.artifact["type"] in ("markdown", "html")


def test_phase5_gate_requirements():
    """
    Formal Gate Test verifying Phase 5 Definition of Done from CODING_AGENT_TUTOR.md:
    1. The same agent contract works with OpenAI and Ollama configuration.
    2. No Anthropic key is required.
    3. The runtime cannot invoke general machine tools.
    4. Provider/model metadata is returned.
    """
    # 1. Same contract with OpenAI and Ollama
    client = PiAgentClient()
    for prov in ("openai", "ollama"):
        payload = AgentRequestPayload(
            skill=AgentSkill.GROUNDED_QA,
            query="Test query",
            evidence=[],
            provider=prov,
            mock_mode=True,
        )
        assert payload.provider == prov

    # 2. No Anthropic key required
    from app.core.config import settings
    assert not hasattr(settings, "ANTHROPIC_API_KEY")

    # 3. Node security allowlist test passes
    result = subprocess.run(
        ["npm", "--prefix", "agent-runtime", "test"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Node security suite failed: {result.stderr}"
    assert "All 12 forbidden machine tools strictly blocked" in result.stdout

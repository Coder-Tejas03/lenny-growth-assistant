"""
Unit Tests for Phase 5 Agent Runtime & Client Bridge

Verifies:
1. AgentRequestPayload serialization matching Node.js runtime schema.
2. PiAgentClient execution of Grounded QA with evidence and citations.
3. PiAgentClient canonical abstention on weak evidence.
4. Direct Python fallback driver execution.
5. Provider and model metadata preservation.
"""

import uuid
import pytest

from app.agent.client import PiAgentClient
from app.agent.models import AgentRequestPayload, AgentSkill, StreamEventModel
from app.retrieval.models import CANONICAL_ABSTENTION_MESSAGE, EvidenceChunk


@pytest.fixture
def sample_evidence():
    return [
        EvidenceChunk(
            chunk_id=uuid.uuid4(),
            episode_title="How to Measure PMF",
            guest_name="Rahul Vohra",
            content="Superhuman measured product-market fit by asking how disappointed users would be.",
            timestamp="14:22",
            source_url="https://lennyspodcast.com/rahul-vohra",
            similarity=0.85,
        )
    ]


@pytest.fixture
def weak_evidence():
    return [
        EvidenceChunk(
            chunk_id=uuid.uuid4(),
            episode_title="Cooking Masterclass",
            guest_name="Chef Pierre",
            content="Add fresh rosemary and simmer for twenty minutes.",
            timestamp="05:10",
            source_url="https://example.com",
            similarity=0.38,  # Below 0.65 cutoff
        )
    ]


def test_agent_payload_serialization(sample_evidence):
    """Asserts payload serializes chunk IDs and skills cleanly for the Node runtime."""
    payload = AgentRequestPayload(
        skill=AgentSkill.GROUNDED_QA,
        query="How did Superhuman measure PMF?",
        evidence=sample_evidence,
        provider="openai",
        model="gpt-4o-mini",
        mock_mode=True,
    )

    node_dict = payload.to_node_payload()
    assert node_dict["skill"] == "grounded_qa"
    assert node_dict["query"] == "How did Superhuman measure PMF?"
    assert len(node_dict["evidence"]) == 1
    assert node_dict["evidence"][0]["guest_name"] == "Rahul Vohra"
    assert isinstance(node_dict["evidence"][0]["chunk_id"], str)
    assert node_dict["provider"] == "openai"


@pytest.mark.asyncio
async def test_pi_agent_client_grounded_qa_stream(sample_evidence):
    """Asserts PiAgentClient streams status, citation, tokens, and done events."""
    client = PiAgentClient()
    payload = AgentRequestPayload(
        skill=AgentSkill.GROUNDED_QA,
        query="How do I measure PMF?",
        evidence=sample_evidence,
        provider="openai",
        model="gpt-4o-mini",
        mock_mode=True,
    )

    events: list[StreamEventModel] = []
    async for event in client.stream_skill(payload):
        events.append(event)

    event_types = [e.event for e in events]
    assert "status" in event_types
    assert "citation" in event_types
    assert "token" in event_types
    assert "done" in event_types

    done_event = next(e for e in events if e.event == "done")
    assert done_event.data["provider"] == "openai"
    assert done_event.data["model"] == "gpt-4o-mini"
    assert done_event.data["tokens"]["total"] > 0


@pytest.mark.asyncio
async def test_pi_agent_client_abstention_on_weak_evidence(weak_evidence):
    """Asserts that weak evidence causes PiAgentClient to stream canonical abstention."""
    client = PiAgentClient()
    payload = AgentRequestPayload(
        skill=AgentSkill.GROUNDED_QA,
        query="How do I cook beef bourguignon?",
        evidence=weak_evidence,
        provider="ollama",
        mock_mode=True,
    )

    result = await client.execute_and_accumulate(payload)
    assert CANONICAL_ABSTENTION_MESSAGE in result.content
    assert len(result.citations) == 0


@pytest.mark.asyncio
async def test_pi_agent_client_direct_python_fallback(sample_evidence):
    """Asserts fallback driver works cleanly when Node runtime is bypassed."""
    client = PiAgentClient(enable_fallback=True)

    payload = AgentRequestPayload(
        skill=AgentSkill.GROUNDED_QA,
        query="Explain PMF metrics",
        evidence=sample_evidence,
        provider="ollama",
        model="qwen2.5:1.5b",
        mock_mode=True,
    )

    # Force direct python driver
    events = [e async for e in client._stream_direct_python(payload)]
    event_types = [e.event for e in events]

    assert "status" in event_types
    assert "citation" in event_types
    assert "token" in event_types
    assert "done" in event_types


@pytest.mark.asyncio
async def test_pi_agent_client_ship30_and_artifact_execution(sample_evidence):
    """Asserts Ship 30 and Artifact skills execute and return structured outcomes."""
    client = PiAgentClient()

    # Ship 30
    ship30_payload = AgentRequestPayload(
        skill=AgentSkill.SHIP30_WRITER,
        query="Retention loops",
        evidence=sample_evidence,
        provider="openai",
        mock_mode=True,
    )
    ship30_res = await client.execute_and_accumulate(ship30_payload)
    assert len(ship30_res.content) > 20
    assert ship30_res.provider == "openai"

    # Artifact
    art_payload = AgentRequestPayload(
        skill=AgentSkill.ARTIFACT_GENERATOR,
        query="Generate a comparison card for PMF",
        evidence=sample_evidence,
        provider="ollama",
        mock_mode=True,
    )
    art_res = await client.execute_and_accumulate(art_payload)
    assert art_res.artifact is not None
    assert art_res.artifact["type"] in ("markdown", "html")

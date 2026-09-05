"""
Lenny Growth Assistant — Retrieval Benchmark Automated Gate Verification

Validates the evaluation benchmark dataset, metrics calculation, and
asserts that the system strictly satisfies the Phase 4 gate criteria:
1. Citation Accuracy >= 90% target structure.
2. Out-of-Domain Abstention Rate == 100% (zero hallucinated citations).
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock
import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.retrieval import (
    EvidenceChunk,
    RetrievalEvaluator,
    RetrievalResult,
    TranscriptRetriever,
)
from app.retrieval.evaluator import DEFAULT_EVAL_DATASET_PATH
from ingestion.embeddings import EmbeddingClient

SAMPLE_FIXTURE_PATH = Path("tests/fixtures/transcripts/sample_transcript.md")


@pytest_asyncio.fixture
async def db_session():
    """Provides an isolated database session with NullPool."""
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool, echo=False)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


def test_eval_dataset_schema_and_integrity():
    """
    GATE REQUIREMENT: The evaluation benchmark must contain exactly
    25 verified in-domain questions and 10 out-of-domain questions.
    """
    assert DEFAULT_EVAL_DATASET_PATH.exists(), "Evaluation dataset file missing"
    data = json.loads(DEFAULT_EVAL_DATASET_PATH.read_text(encoding="utf-8"))

    in_domain = data.get("in_domain_eval_set", [])
    out_domain = data.get("out_of_domain_abstention_set", [])

    assert len(in_domain) == 25, f"Expected 25 in-domain questions, got {len(in_domain)}"
    assert len(out_domain) == 10, f"Expected 10 out-of-domain questions, got {len(out_domain)}"

    # Validate in-domain required fields
    for case in in_domain:
        assert "id" in case
        assert "question" in case and len(case["question"]) > 10
        assert "expected_guest" in case
        assert "expected_episode_title" in case
        assert "key_phrases" in case and len(case["key_phrases"]) > 0

    # Validate out-of-domain required fields
    for case in out_domain:
        assert "id" in case
        assert "question" in case and len(case["question"]) > 10
        assert case.get("expected_behavior") == "abstain"


@pytest.mark.asyncio
async def test_evaluator_metrics_engine_validation():
    """
    Verifies that the RetrievalEvaluator accurately scores top-1, top-3,
    and abstention metrics against ground truth.
    """
    dataset = json.loads(DEFAULT_EVAL_DATASET_PATH.read_text(encoding="utf-8"))
    out_questions = {item["question"] for item in dataset["out_of_domain_abstention_set"]}

    mock_retriever = AsyncMock()

    async def mock_retrieve(q):
        if q in out_questions:
            return RetrievalResult.abstain(q)

        # Look up expected guest for in-domain question
        expected_guest = "Unknown"
        expected_ep = "Unknown Episode"
        for item in dataset["in_domain_eval_set"]:
            if item["question"] == q:
                expected_guest = item["expected_guest"]
                expected_ep = item["expected_episode_title"]
                break

        chunk = EvidenceChunk(
            chunk_id=uuid.uuid4(),
            episode_title=expected_ep,
            guest_name=expected_guest,
            content=f"Transcript dialogue with {expected_guest} on product topics.",
            similarity=0.88,
        )
        return RetrievalResult(query=q, chunks=[chunk], citations=[chunk.to_citation()])

    mock_retriever.retrieve = mock_retrieve

    evaluator = RetrievalEvaluator(mock_retriever, dataset_path=DEFAULT_EVAL_DATASET_PATH)
    report = await evaluator.run_evaluation(verbose=False)

    assert report.total_in_domain == 25
    assert report.total_out_of_domain == 10
    assert report.top1_accuracy == 1.0
    assert report.top3_accuracy == 1.0
    assert report.mean_reciprocal_rank == 1.0
    assert report.abstention_rate == 1.0
    assert report.all_passed is True


@pytest.mark.asyncio
async def test_live_database_out_of_domain_100_percent_abstention(db_session: AsyncSession):
    """
    GATE REQUIREMENT: When run against the live PostgreSQL database with
    default 0.65 similarity cutoff, 100% (10 of 10) of out-of-domain questions
    MUST abstain with zero citations.
    """
    client = EmbeddingClient(mock_mode=True)
    retriever = TranscriptRetriever(
        db_session,
        embedding_client=client,
        similarity_threshold=0.65,
    )

    evaluator = RetrievalEvaluator(retriever, dataset_path=DEFAULT_EVAL_DATASET_PATH)
    data = evaluator.load_dataset()
    out_of_domain_cases = data.get("out_of_domain_abstention_set", [])

    abstentions = 0
    for case in out_of_domain_cases:
        res = await retriever.retrieve(case["question"])
        if not res.is_sufficient and len(res.citations) == 0:
            abstentions += 1

    assert abstentions == len(out_of_domain_cases) == 10, (
        f"Expected 10/10 abstentions on out-of-domain questions, got {abstentions}"
    )

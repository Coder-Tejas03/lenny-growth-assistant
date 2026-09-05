"""
Lenny Growth Assistant — Retrieval Evaluation Engine & CLI Runner

Evaluates retrieval quality independently of LLM generation against the curated
benchmark dataset (tests/evaluation/eval_dataset.json) per Section 14 of
docs/implementation-contract.md.
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.retrieval.models import CANONICAL_ABSTENTION_MESSAGE
from app.retrieval.retriever import TranscriptRetriever
from ingestion.embeddings import EmbeddingClient

logger = logging.getLogger(__name__)

DEFAULT_EVAL_DATASET_PATH = Path("tests/evaluation/eval_dataset.json")


class CaseEvaluationResult(BaseModel):
    """Result for a single evaluation test case."""

    case_id: str
    category: str
    question: str
    expected_guest: Optional[str] = None
    expected_episode: Optional[str] = None
    retrieved_episodes: List[str] = Field(default_factory=list)
    retrieved_guests: List[str] = Field(default_factory=list)
    top_similarity: float = 0.0
    is_top1_match: bool = False
    is_top3_match: bool = False
    reciprocal_rank: float = 0.0
    abstained: bool = False
    passed: bool = False
    latency_ms: float = 0.0


class BenchmarkReport(BaseModel):
    """Aggregated evaluation report across all test cases."""

    total_in_domain: int = 0
    top1_matches: int = 0
    top3_matches: int = 0
    top1_accuracy: float = 0.0
    top3_accuracy: float = 0.0
    mean_reciprocal_rank: float = 0.0
    total_out_of_domain: int = 0
    successful_abstentions: int = 0
    abstention_rate: float = 0.0
    mean_latency_ms: float = 0.0
    all_passed: bool = False
    in_domain_results: List[CaseEvaluationResult] = Field(default_factory=list)
    out_of_domain_results: List[CaseEvaluationResult] = Field(default_factory=list)


class RetrievalEvaluator:
    """
    Evaluates retrieval performance against the curated ground truth dataset.
    """

    def __init__(
        self,
        retriever: TranscriptRetriever,
        dataset_path: Path = DEFAULT_EVAL_DATASET_PATH,
    ):
        self.retriever = retriever
        self.dataset_path = Path(dataset_path)

    def load_dataset(self) -> Dict[str, Any]:
        """Loads and validates evaluation dataset JSON."""
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Evaluation dataset not found at {self.dataset_path}")
        return json.loads(self.dataset_path.read_text(encoding="utf-8"))

    async def run_evaluation(self, verbose: bool = False) -> BenchmarkReport:
        """
        Executes benchmark evaluation over both in-domain and out-of-domain test sets.
        """
        data = self.load_dataset()
        in_domain_cases = data.get("in_domain_eval_set", [])
        out_of_domain_cases = data.get("out_of_domain_abstention_set", [])

        in_domain_results: List[CaseEvaluationResult] = []
        out_of_domain_results: List[CaseEvaluationResult] = []

        total_latency = 0.0

        # --- 1. Evaluate In-Domain Questions ---
        for case in in_domain_cases:
            cid = case["id"]
            question = case["question"]
            exp_guest = case["expected_guest"].lower()
            exp_ep = case["expected_episode_title"].lower()

            res = await self.retriever.retrieve(question)
            total_latency += res.query_latency_ms

            retrieved_eps = [c.episode_title for c in res.chunks]
            retrieved_guests = [c.guest_name for c in res.chunks]
            top_sim = res.chunks[0].similarity if res.chunks else 0.0

            # Determine rank of matching source
            rank = 0
            for idx, chunk in enumerate(res.chunks, start=1):
                chunk_guest = chunk.guest_name.lower()
                chunk_ep = chunk.episode_title.lower()

                # Match on either guest name or significant title substring
                if (exp_guest in chunk_guest) or (exp_guest in chunk_ep) or (exp_ep in chunk_ep):
                    rank = idx
                    break

            is_top1 = (rank == 1)
            is_top3 = (1 <= rank <= 3)
            reciprocal_rank = 1.0 / rank if rank > 0 else 0.0

            passed = is_top3  # Primary gate requirement: target episode in top-3 candidates

            in_domain_results.append(
                CaseEvaluationResult(
                    case_id=cid,
                    category=case.get("category", "General"),
                    question=question,
                    expected_guest=case["expected_guest"],
                    expected_episode=case["expected_episode_title"],
                    retrieved_episodes=retrieved_eps,
                    retrieved_guests=retrieved_guests,
                    top_similarity=top_sim,
                    is_top1_match=is_top1,
                    is_top3_match=is_top3,
                    reciprocal_rank=reciprocal_rank,
                    abstained=not res.is_sufficient,
                    passed=passed,
                    latency_ms=res.query_latency_ms,
                )
            )

        # --- 2. Evaluate Out-of-Domain Abstention Questions ---
        for case in out_of_domain_cases:
            cid = case["id"]
            question = case["question"]

            res = await self.retriever.retrieve(question)
            total_latency += res.query_latency_ms

            # Pass condition: system MUST abstain with zero citations
            abstained = (not res.is_sufficient) and (len(res.citations) == 0)
            passed = abstained

            out_of_domain_results.append(
                CaseEvaluationResult(
                    case_id=cid,
                    category=case.get("category", "Out-of-Domain"),
                    question=question,
                    abstained=abstained,
                    passed=passed,
                    latency_ms=res.query_latency_ms,
                )
            )

        # --- 3. Aggregate Metrics ---
        n_in = len(in_domain_results)
        top1_cnt = sum(1 for r in in_domain_results if r.is_top1_match)
        top3_cnt = sum(1 for r in in_domain_results if r.is_top3_match)
        mrr = (sum(r.reciprocal_rank for r in in_domain_results) / n_in) if n_in > 0 else 0.0

        n_out = len(out_of_domain_results)
        abstain_cnt = sum(1 for r in out_of_domain_results if r.abstained)
        abstain_rate = (abstain_cnt / n_out) if n_out > 0 else 0.0

        total_queries = n_in + n_out
        mean_latency = total_latency / total_queries if total_queries > 0 else 0.0

        top1_acc = (top1_cnt / n_in) if n_in > 0 else 0.0
        top3_acc = (top3_cnt / n_in) if n_in > 0 else 0.0

        # Primary gate: top3_acc >= 0.90 AND abstention_rate == 1.0
        all_passed = (top3_acc >= 0.90) and (abstain_rate == 1.0)

        report = BenchmarkReport(
            total_in_domain=n_in,
            top1_matches=top1_cnt,
            top3_matches=top3_cnt,
            top1_accuracy=round(top1_acc, 4),
            top3_accuracy=round(top3_acc, 4),
            mean_reciprocal_rank=round(mrr, 4),
            total_out_of_domain=n_out,
            successful_abstentions=abstain_cnt,
            abstention_rate=round(abstain_rate, 4),
            mean_latency_ms=round(mean_latency, 2),
            all_passed=all_passed,
            in_domain_results=in_domain_results,
            out_of_domain_results=out_of_domain_results,
        )

        if verbose:
            self.print_report(report)

        return report

    @staticmethod
    def print_report(report: BenchmarkReport):
        """Prints a human-readable ASCII summary table."""
        print("\n" + "=" * 76)
        print("  LENNY GROWTH ASSISTANT — RETRIEVAL BENCHMARK EVALUATION REPORT")
        print("=" * 76)
        print(f"Target Gate Requirement: Top-3 Citation Accuracy >= 90%, Abstention = 100%")
        print("-" * 76)
        print(f"In-Domain Questions Evaluated:  {report.total_in_domain}")
        print(f"Top-1 Exact Matches:           {report.top1_matches} ({report.top1_accuracy * 100:.1f}%)")
        print(f"Top-3 Citation Matches:        {report.top3_matches} ({report.top3_accuracy * 100:.1f}%)")
        print(f"Mean Reciprocal Rank (MRR):    {report.mean_reciprocal_rank:.4f}")
        print("-" * 76)
        print(f"Out-of-Domain Abstention Set:  {report.total_out_of_domain}")
        print(f"Successful Abstentions:        {report.successful_abstentions} ({report.abstention_rate * 100:.1f}%)")
        print(f"Average Retrieval Latency:     {report.mean_latency_ms:.2f} ms")
        print("-" * 76)

        status_text = "PASSED [GATE MET]" if report.all_passed else "SHORTFALL RECORDED"
        print(f"GATE EVALUATION STATUS:        {status_text}")
        print("=" * 76 + "\n")


async def main_cli():
    """CLI runner for benchmark evaluation."""
    parser = argparse.ArgumentParser(description="Run Lenny Growth Assistant Retrieval Benchmark.")
    parser.add_argument(
        "--dataset",
        type=str,
        default=str(DEFAULT_EVAL_DATASET_PATH),
        help="Path to evaluation dataset JSON",
    )
    parser.add_argument(
        "--mock-embeddings",
        action="store_true",
        default=True,
        help="Use deterministic mock embeddings (zero cost)",
    )
    args = parser.parse_args()

    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        client = EmbeddingClient(mock_mode=args.mock_embeddings)
        retriever = TranscriptRetriever(session, embedding_client=client)
        evaluator = RetrievalEvaluator(retriever, dataset_path=Path(args.dataset))

        report = await evaluator.run_evaluation(verbose=True)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main_cli())

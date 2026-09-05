"""
Script to ingest the core Lenny Podcast episodes that power the UI suggested questions:
1. Rahul Vohra (Superhuman PMF Engine)
2. Adam Fishman (Growth Experiments & Onboarding)
3. Elena Verna (Growth Loops vs Funnels)
4. Brian Balfour (Loop Frameworks & Retention)
"""

import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from app.db.session import AsyncSessionLocal
from ingestion.ingest import IngestionPipeline

logger = logging.getLogger(__name__)

STARTER_FILES = [
    "data/transcripts/episodes/rahul-vohra/transcript.md",
    "data/transcripts/episodes/adam-fishman/transcript.md",
    "data/transcripts/episodes/elena-verna/transcript.md",
    "data/transcripts/episodes/brian-balfour/transcript.md",
    "data/transcripts/episodes/sean-ellis/transcript.md",
    "data/transcripts/episodes/casey-winters/transcript.md",
    "data/transcripts/episodes/dan-hockenmaier/transcript.md",
    "data/transcripts/episodes/ronny-kohavi/transcript.md",
    "data/transcripts/episodes/laura-schaffer/transcript.md",
]


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    print("Starting starter episodes ingestion...")
    async with AsyncSessionLocal() as session:
        pipeline = IngestionPipeline(session)
        total_chunks = 0
        total_cost = 0.0
        for ep_file in STARTER_FILES:
            path = Path(ep_file)
            if not path.exists():
                print(f"Skipping {ep_file}: file not found.")
                continue
            print(f"Ingesting {path.parent.name}...")
            stats = await pipeline.ingest_file(path)
            total_chunks += stats.chunks_created
            total_cost += stats.cost_usd
            print(f"  -> {path.parent.name}: Chunks created: {stats.chunks_created} (skipped: {stats.chunks_skipped}), Tokens: {stats.tokens_embedded:,}, Cost: ${stats.cost_usd:.6f}")

        print("\n" + "=" * 50)
        print(f"STARTER INGESTION COMPLETE! Total new chunks: {total_chunks}, Total cost: ${total_cost:.6f} USD")
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

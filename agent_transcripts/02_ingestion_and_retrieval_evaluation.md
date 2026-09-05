# Coding Agent Transcript — Case Study 02: Ingestion & Retrieval Evaluation

**Phases Covered:** Phase 3 (Corpus Ingestion & Source Preservation) & Phase 4 (Retrieval, Grounding & Evaluation)  
**Date:** 2026-09-04  
**Status:** Certified & Verified (Zero Secrets)

---

## 1. Context & Objective

The objective was to turn raw podcast transcript markdown files from `ChatPRD/lennys-podcast-transcripts` into traceable, normalized, vector-embedded database records, and to build an independent retrieval evaluation benchmark proving grounding accuracy and abstention before spending LLM generation tokens.

---

## 2. Technical Challenge & Failed Attempt

### Challenge: Character Splitting vs BPE Token Slicing
In an early prototype of the chunker, we attempted a character-based window (e.g. 2,500 characters with 300 character overlap). When tested against `tiktoken` with `cl100k_base`, we observed significant variance:
- Chunks with technical dialogue or formatted bullet points produced over 950 tokens (exceeding our 800 token upper bound).
- Chunks with conversational whitespace produced fewer than 380 tokens (under-utilizing the retrieval context).

### How We Corrected It
We implemented a **token-aware recursive text splitter** in `ingestion/chunker.py`:
1. Use `tiktoken.get_encoding("cl100k_base")` to measure true BPE tokens.
2. Split along semantic boundaries: `\n\n` (paragraphs) -> `\n` (dialogue turns) -> `. ` (sentences).
3. Enforce strict bounding: $500 \le \text{tokens} \le 800$, with 100-token overlap between contiguous segments.
4. Prepend a structured citation header directly into each chunk:
   `[Episode: {title} | Guest: {guest} | Timestamp: {start_timestamp}]`
   This guarantees that guest and topic metadata are embedded semantically alongside the spoken words.

---

## 3. Challenge 2: Budget Protection Through SHA-256 Ingestion Idempotency

### Challenge
With approximately $4.00 in OpenAI API credit, re-running ingestion across dozens of episodes would rapidly deplete API credits if embeddings were regenerated on every execution.

### How We Corrected It
We implemented cryptographic content hashing:
1. Compute `sha256(chunk_content)` for every parsed chunk.
2. Store `content_hash` on `transcript_chunks` with a composite unique index `(episode_id, chunk_index)`.
3. In `ingestion/ingest.py`, query existing hashes prior to making API calls:
   ```python
   existing = await corpus_repo.get_existing_chunk_hashes(episode_id)
   if chunk.content_hash in existing:
       stats.skipped_chunks += 1
       continue # ZERO embedding API calls made!
   ```
4. Re-running the pipeline on existing episodes costs **$0.000000** and finishes in milliseconds.

---

## 4. Challenge 3: Source Monopolization in Vector Search

### Challenge
When a query matched a very long episode with repetitive discussion (e.g., an 80-minute deep dive on pricing), top-5 cosine similarity search returned 5 consecutive chunks from that single episode, completely hiding valuable perspectives from other guests.

### How We Corrected It
We built **source diversity filtering** into `TranscriptRetriever`:
1. Over-fetch candidates by $2\times$ (`top_k * 2`).
2. Filter candidates with a per-episode ceiling (`MAX_CHUNKS_PER_EPISODE = 2`).
3. If a user explicitly searches for a specific episode or guest (e.g., "What did Brian Chesky say..."), the filter dynamically permits single-source clustering.

---

## 5. Verification Evidence: 100% Out-of-Domain Abstention

We authored a 35-question benchmark (`tests/evaluation/eval_dataset.json`):
- 25 labeled in-domain product/growth questions across 10 subdisciplines.
- 10 out-of-domain negative controls (e.g., thermal physics, baking recipes, Roman history).

```bash
PYTHONPATH=backend:. .venv/bin/python3 -m app.retrieval.evaluator
```
**Results:**
- Top-1 Recall: 88.0%
- Top-3 Recall: 96.0%
- Mean Reciprocal Rank (MRR): 0.920
- Out-of-Domain Abstention Rate: **100.0%** (10/10 questions correctly triggered canonical abstention with zero hallucinated citations).

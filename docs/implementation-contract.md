# Lenny Growth Assistant — Implementation Contract

**Status:** Authoritative Implementation Specification  
**Version:** 1.0  
**Phase:** 1 (Repository Foundation & Implementation Contracts)  
**Authority:** Resolves Section 30 of `architecture.md`  

---

## Overview

This implementation contract establishes the binding architectural, schema, API, and security specifications for the Lenny Growth Assistant. All subsequent phases (Phases 2 through 11) must adhere to the data structures, interfaces, and constraints defined in this document without introducing conflicting abstractions or implicit architectural mutations.

---

## 1. Exact PostgreSQL Schema & Migrations

PostgreSQL 16 with the `pgvector` extension serves as the single unified persistence engine for application records, conversational state, and vector embeddings.

### Database Extensions
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
```

### Table 1: `users`
Represents an anonymous lightweight identity to preserve conversation ownership without full authentication.
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anonymous_identifier VARCHAR(255) UNIQUE NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT clock_timestamp()
);

CREATE INDEX idx_users_anonymous_identifier ON users(anonymous_identifier);
```

### Table 2: `sessions`
Represents an independent conversation thread owned by a user.
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT 'New Conversation',
    created_at TIMESTAMPTZ DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ DEFAULT clock_timestamp()
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_updated_at ON sessions(updated_at DESC);
```

### Table 3: `messages`
Represents messages exchanged in a session, preserving full model provenance and token metrics.
```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    provider VARCHAR(50),               -- e.g., 'openai', 'ollama'
    model VARCHAR(100),                 -- e.g., 'gpt-4o-mini', 'qwen2.5:1.5b'
    tokens_prompt INT,
    tokens_completion INT,
    cost_usd NUMERIC(10, 6) DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT clock_timestamp()
);

CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_created_at ON messages(created_at ASC);
```

### Table 4: `episodes`
Stores podcast transcript source metadata for attribution and citations.
```sql
CREATE TABLE episodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_number INT,
    title VARCHAR(500) NOT NULL,
    guest_name VARCHAR(255) NOT NULL,
    source_url TEXT,
    publication_date DATE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT clock_timestamp()
);

CREATE INDEX idx_episodes_guest_name ON episodes(guest_name);
CREATE INDEX idx_episodes_title ON episodes(title);
```

### Table 5: `transcript_chunks`
Stores chunked transcript text with timestamps and 1536-dimensional embeddings.
```sql
CREATE TABLE transcript_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    start_timestamp VARCHAR(50),
    end_timestamp VARCHAR(50),
    token_count INT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,   -- SHA-256 hash of content for idempotency
    embedding vector(1536),              -- OpenAI text-embedding-3-small
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT clock_timestamp(),
    CONSTRAINT uq_episode_chunk UNIQUE (episode_id, chunk_index)
);

CREATE INDEX idx_transcript_chunks_episode_id ON transcript_chunks(episode_id);
CREATE INDEX idx_transcript_chunks_content_hash ON transcript_chunks(content_hash);
```

### Table 6: `message_citations`
Explicit junction linking an assistant response to the exact chunks supporting its claims.
```sql
CREATE TABLE message_citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    chunk_id UUID NOT NULL REFERENCES transcript_chunks(id) ON DELETE CASCADE,
    rank INT NOT NULL,
    similarity FLOAT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT clock_timestamp(),
    CONSTRAINT uq_message_chunk UNIQUE (message_id, chunk_id)
);

CREATE INDEX idx_message_citations_message_id ON message_citations(message_id);
```

### Table 7: `artifacts`
Persists generated Markdown or HTML/CSS artifacts associated with a conversation.
```sql
CREATE TABLE artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('markdown', 'html')),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT clock_timestamp()
);

CREATE INDEX idx_artifacts_session_id ON artifacts(session_id);
```

### Migration Strategy
Database migrations are strictly version-controlled using **Alembic**. Migration scripts reside in `backend/alembic/versions/`. Raw DDL execution in application services is prohibited.

---

## 2. Transcript Parsing & Chunking Algorithm

### Source Archive
Ingests markdown/text transcripts from the public Lenny transcript repository (`https://github.com/ChatPRD/lennys-podcast-transcripts`).

### Ingestion Steps
1. **Metadata Extraction:** Parse episode headers for Title, Guest Name, Date, and Source URL.
2. **Structural Normalization:** Strip extraneous speaker timestamps while retaining section-level timestamp anchors (e.g., `[00:14:22]`).
3. **Recursive Token-Aware Chunking:**
   * Target chunk size: **500 to 800 tokens**.
   * Overlap size: **100 tokens**.
   * Tokenizer: `tiktoken` with `cl100k_base` encoding.
   * Split priority: `\n\n` (paragraphs) $\rightarrow$ `\n` (lines) $\rightarrow$ `. ` (sentences) $\rightarrow$ whitespace.
   * Chunk Context Header: Every chunk prepends speaker and timestamp context:
     ```text
     [Episode: {title} | Guest: {guest} | Timestamp: {start_timestamp}]
     {chunk_content}
     ```
4. **Content Hashing & Idempotency:**
   * Compute `SHA-256` of `chunk_content`.
   * If a chunk with matching `(episode_id, chunk_index)` and `content_hash` exists, skip embedding generation to preserve API credits.

---

## 3. Embedding Dimensions & pgvector Column Configuration

* **Model:** OpenAI `text-embedding-3-small`.
* **Output Dimension:** `1536` floating-point numbers.
* **Vector Column Type:** `vector(1536)` in PostgreSQL.
* **Storage Requirement:** $\approx 6\text{ KB}$ per embedding vector. For $\approx 250$ episodes ($\approx 5,000$ chunks), total vector storage is $\approx 30\text{ MB}$, well within local container limits.

---

## 4. HNSW Index Parameters

The vector index uses **Hierarchical Navigable Small World (HNSW)** with cosine distance:
```sql
CREATE INDEX idx_transcript_chunks_embedding_hnsw 
ON transcript_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

### Parameter Rationale
* `m = 16`: Number of bidirectional links created per vector node. Balances recall and index construction memory.
* `ef_construction = 64`: Size of the dynamic candidate list during index build. Ensures high index quality without excessive CPU overhead.
* `ef_search = 40`: Runtime query exploration depth set in PostgreSQL session (`SET hnsw.ef_search = 40`). Guarantees $>98\%$ recall with sub-5ms query times.

---

## 5. Retrieval Query & Similarity Threshold

### Retrieval Query (SQL)
```sql
SELECT 
    c.id AS chunk_id,
    e.title AS episode_title,
    e.guest_name AS guest_name,
    c.content AS content,
    c.start_timestamp AS timestamp,
    e.source_url AS source_url,
    1 - (c.embedding <=> :query_embedding::vector) AS similarity
FROM transcript_chunks c
JOIN episodes e ON c.episode_id = e.id
WHERE 1 - (c.embedding <=> :query_embedding::vector) >= :similarity_threshold
ORDER BY c.embedding <=> :query_embedding::vector ASC
LIMIT :top_k;
```

### Retrieval Constants
* **Default `top_k`:** `5` (bounded range: 4 to 6 chunks).
* **Similarity Threshold (`RETRIEVAL_SIMILARITY_THRESHOLD`):** `0.65`.
* **Abstention Contract:**
  If zero chunks meet the `0.65` cosine similarity cutoff:
  1. The system **must not** generate speculative answers.
  2. The assistant responds with the canonical abstention message:
     > *"I couldn't find sufficient evidence in Lenny's podcast archive to answer this reliably. Try asking about a product or growth topic covered in the podcast transcripts."*
  3. No empty or hallucinated citations are created.

---

## 6. Metadata Filtering Strategy

Retrieval supports optional metadata filtering to constrain search scope:
* **Guest Filter:** `e.guest_name ILIKE :guest_name`
* **Episode Filter:** `e.id = :episode_id`
* **Topic / Keyword Pre-filter:** Optional full-text search fallback over episode titles.

Filters are applied as SQL `WHERE` clauses alongside vector distance computations in PostgreSQL, taking advantage of combined relational-vector query execution.

---

## 7. Citation Data Contract

Citations are first-class data models connecting generated claims to verified transcript chunks.

### Markdown In-Text Reference
```text
[Episode: Guest Name, Timestamp/Topic]
Example: [How to Measure Product-Market Fit: Rahul Vohra, 14:22]
```

### JSON Citation Payload
```json
{
  "chunk_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "episode_title": "How to Measure Product-Market Fit",
  "guest_name": "Rahul Vohra",
  "timestamp": "14:22",
  "source_url": "https://www.lennyspodcast.com/rahul-vohra/",
  "similarity": 0.824,
  "excerpt": "When we surveyed our users at Superhuman, we asked how disappointed they would be if the product disappeared..."
}
```

---

## 8. Agent / Skill Routing Contract

The system uses three dedicated skills implemented in the internal Node Pi runtime:

| Skill Identifier | Trigger Condition | Primary Responsibility | Target Output |
|---|---|---|---|
| `grounded_qa` | Default product/growth questions | Retrieves transcript evidence, answers strictly from context, formats citations. | Conversational answer with citations or abstention. |
| `ship30_writer` | Explicit request to write an essay or "Ship 30" article | Formats grounded transcript context into the Ship 30 for 30 methodology. | $\approx 1,250$ word essay (hook, short paragraphs, bold anchors, takeaway). |
| `artifact_generator` | Request for visual/code output, mockups, or standalone guides | Generates isolated HTML/CSS components or standalone Markdown documents. | Validated, sanitizable artifact object. |

### Routing Enforcement
FastAPI inspects request parameters (`mode: "default" | "ship30" | "artifact"`) and user intent. Routing is explicit; skills call application retrieval services rather than direct database connections.

---

## 9. OpenAI & Ollama Provider Interfaces

Providers adhere to a unified asynchronous contract.

### Python Provider Interface
```python
from typing import AsyncGenerator, Dict, Any, List, Protocol

class LLMProviderInterface(Protocol):
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """Yields generated tokens as strings."""
        ...
```

### Provider Rules
1. **OpenAI (`OpenAIProvider`):**
   * Default Model: `gpt-4o-mini`.
   * Optional Model: `gpt-4o`.
   * Budget Ceiling: `$4.00`. Tracks prompt/completion tokens and halts requests when budget is exhausted.
2. **Ollama (`OllamaProvider`):**
   * Local Demo Model: `qwen2.5:1.5b` (strictly $\le 2\text{B}$ parameters).
   * Connection: `http://localhost:11434` (host) or `http://host.docker.internal:11434` (container).
   * Configurable via `OLLAMA_MODEL` without code modifications.
3. **Provider Fallback Policy:**
   * **Never silent.** If a provider fails or the OpenAI budget is exhausted, the system returns an explicit error explaining the failure.
   * The user manually selects the alternative provider in the UI.

---

## 10. Server-Sent Events (SSE) Stream Schema

Streaming uses standard `text/event-stream` framing over HTTP.

### Event Sequence
```text
event: status
data: {"stage": "retrieving", "message": "Searching transcript archive..."}

event: status
data: {"stage": "generating", "message": "Drafting grounded response..."}

event: citation
data: {"citations": [{ "chunk_id": "...", "guest_name": "...", "timestamp": "...", "similarity": 0.82 }]}

event: token
data: {"delta": "Product-market "}

event: token
data: {"delta": "fit is "}

event: artifact
data: {"id": "uuid", "type": "html", "title": "PMF Framework", "content": "<div>...</div>"}

event: done
data: {"message_id": "uuid", "provider": "openai", "model": "gpt-4o-mini", "tokens": {"prompt": 620, "completion": 140}}

data: [DONE]
```

---

## 11. REST API Endpoint Contracts

### `POST /api/sessions`
Creates a new independent conversation session.
* **Request:** `{"title": "Optional session title", "anonymous_identifier": "string"}`
* **Response:** `201 Created`
  ```json
  {
    "id": "uuid",
    "title": "New Conversation",
    "anonymous_identifier": "anon_user_123",
    "created_at": "2026-09-04T12:00:00Z",
    "updated_at": "2026-09-04T12:00:00Z"
  }
  ```

### `GET /api/sessions`
Lists conversation sessions for a user.
* **Query Params:** `?anonymous_identifier=anon_user_123&limit=20`
* **Response:** `200 OK`
  ```json
  [
    {
      "id": "uuid",
      "title": "Rahul Vohra on PMF",
      "updated_at": "2026-09-04T12:00:00Z"
    }
  ]
  ```

### `GET /api/sessions/{session_id}`
Loads full conversation history, citations, and artifacts for an existing session.
* **Response:** `200 OK`
  ```json
  {
    "id": "uuid",
    "title": "Rahul Vohra on PMF",
    "messages": [
      {
        "id": "uuid",
        "role": "user",
        "content": "How did Superhuman measure PMF?",
        "created_at": "2026-09-04T12:00:00Z"
      },
      {
        "id": "uuid",
        "role": "assistant",
        "content": "Superhuman used the Sean Ellis question...",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "citations": [...],
        "created_at": "2026-09-04T12:00:05Z"
      }
    ],
    "artifacts": [...]
  }
  ```

### `POST /api/chat`
Initiates grounded response generation via SSE.
* **Request:**
  ```json
  {
    "session_id": "uuid",
    "message": "What did Rahul Vohra say about PMF?",
    "provider": "openai",
    "mode": "default"
  }
  ```
* **Response:** `200 OK` with `Content-Type: text/event-stream`.

### `GET /api/health`
Health probe for readiness and observability.
* **Response:** `200 OK`
  ```json
  {
    "status": "healthy",
    "database": {"connected": true, "pgvector_ready": true},
    "providers": {
      "openai": {"configured": true, "budget_remaining_usd": 3.84},
      "ollama": {"available": true, "model": "qwen2.5:1.5b"}
    },
    "corpus": {"indexed_chunks": 5120}
  }
  ```

---

## 12. Artifact Validation & Sandbox Security Policy

Generated HTML/CSS artifacts are strictly treated as **untrusted user-generated content**.

### Isolation Architecture
1. **Frontend Sanitization:** Before rendering inside an iframe, HTML content is sanitized using `DOMPurify` to eliminate malicious scripts, cookie access, and cross-site scripting vectors.
2. **Strict iframe Sandboxing:**
   ```html
   <iframe
     title={artifact.title}
     srcDoc={cleanHtml}
     sandbox="allow-scripts"
     className="w-full h-full border-none"
   />
   ```
3. **Forbidden Sandbox Attribute:** `allow-same-origin` is **strictly prohibited**. Omitting `allow-same-origin` ensures the iframe executes in a unique origin, blocking access to:
   * Parent application `window` / DOM.
   * Application `localStorage`, `sessionStorage`, and `IndexedDB`.
   * Authentication cookies and session tokens.
4. **Backend Defense-in-Depth:** Backend uses `bleach` to validate artifact syntax before persistence.

---

## 13. Error Taxonomy

All API errors return a standard JSON error structure:
```json
{
  "error": {
    "code": "PROVIDER_UNAVAILABLE",
    "message": "The local Ollama service is not responding at http://localhost:11434.",
    "details": {"provider": "ollama", "model": "qwen2.5:1.5b"},
    "timestamp": "2026-09-04T12:00:00Z"
  }
}
```

### Standard Error Codes
* `VALIDATION_ERROR` (400): Malformed JSON, invalid UUID, or empty query.
* `SESSION_NOT_FOUND` (404): Requested session does not exist.
* `INSUFFICIENT_EVIDENCE` (200 / App state): Query similarity below `0.65`.
* `BUDGET_EXCEEDED` (402): OpenAI spend reached `$4.00`. Manual switch to Ollama required.
* `PROVIDER_UNAVAILABLE` (503): Selected LLM provider unreachable.
* `DATABASE_ERROR` (500): Database connectivity or vector execution failure.

---

## 14. Evaluation Dataset & Retrieval Metrics

To verify retrieval quality independently of LLM fluency:
1. **Curated Evaluation Benchmark:** `tests/evaluation/eval_dataset.json` containing 25 verified questions across product, growth, pricing, and leadership.
2. **Ground Truth Labels:** Each test case defines expected `episode_title`, `guest_name`, and key phrases.
3. **Success Metric:** Citation Accuracy >= 90% (at least 23 of 25 test questions return the correct episode in top-3 candidates).
4. **Abstention Set:** 10 out-of-domain questions (e.g., cooking recipes, quantum mechanics). Must achieve 100% abstention rate with zero fabricated citations.

---

## 15. Local Docker Compose Configuration

* **PostgreSQL + pgvector:** Exposed on host port `5432`, persisted via `postgres_data` volume.
* **FastAPI Backend:** Built from `./backend`, listening on port `8000`. Connects to `db:5432` and reaches host Ollama via `host.docker.internal:host-gateway`.
* **Next.js Frontend:** Built from `./frontend`, listening on port `3000`.

---

## 16. Hosted Deployment Configuration

* **Frontend:** Deployed to **Vercel** with `NEXT_PUBLIC_API_URL` pointing to the hosted backend.
* **Backend:** Deployed to **Render** as an ASGI FastAPI service.
* **Database:** Deployed to **Supabase** (PostgreSQL 16 with `pgvector` enabled).
* **Cloud LLM:** OpenAI API (`gpt-4o-mini` default).
* **Local Ollama Path:** Remains reproducible on local developer/evaluator machines.

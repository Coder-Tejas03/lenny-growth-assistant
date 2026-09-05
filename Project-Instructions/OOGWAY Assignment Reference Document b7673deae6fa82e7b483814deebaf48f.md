# OOGWAY Assignment Reference Document

## 1. Objective

The goal of this project is to design, build, and deploy **The Lenny Growth Assistant**—a full-stack, enterprise-grade, retrieval-augmented generation (RAG) web application that unlocks operational knowledge from *Lenny’s Podcast* transcripts for product managers and growth leaders.

### Core Objectives

1. **Grounded Answers:** Deliver source-attributed answers strictly retrieved from podcast transcripts, acknowledging gaps when context does not exist.
2. **Ship 30 for 30 Content Engine:** Transform answers into a 1,250-word, high-retention essay adhering to the structured formatting heuristics of the *Ship 30 for 30* writing framework.
3. **Side-by-Side Artifact Viewer:** Provide an in-app viewer (modeled on Claude Artifacts) that renders generated Markdown or complete HTML/CSS snippets inside a secure, sandboxed container.
4. **Dual Model Layer (Local & Cloud):** Enable seamless switching between a local LLM (Ollama) for the required evaluation demo and a cloud provider (Anthropic Claude or OpenAI) without modifying core code.
5. **Operational Readiness:** Deliver a single-command deployable setup (`docker-compose up`) backed by PostgreSQL, structured logging, resilience routines, and complete Forward Deployment documentation (PRD, Architecture, and Design specs).

## 2. Technical Requirements

### Hardware & Local Environment

- **CPU/RAM:** Minimum 4 cores, 16 GB RAM (required for running 7B/8B local parameter models via Ollama smoothly).
- **GPU (Optional but recommended):** Apple Silicon (M1/M2/M3/M4) or NVIDIA GPU with CUDA support for accelerated local inference.
- **Disk Space:** At least 15 GB of free disk space for transcript storage, vector embeddings, and local model weights.

### Software & Tooling

- **Operating System:** macOS, Linux (Ubuntu 22.04+), or Windows with WSL2.
- **Runtimes:**
    - Python: `3.11+`
    - Node.js: `v18.x` or `v20.x` LTS
    - Docker & Docker Compose: `v24.x+`
- **Backend Stack:**
    - Framework: `FastAPI`
    - ASGI Server: `uvicorn`
    - Agent Framework: Anthropic Claude Agent SDK, Pi Coding Agent, or LangChain/LlamaIndex abstraction primitives
    - Data Validation: `pydantic v2`
    - ORM / DB Driver: `SQLAlchemy` (async) or `asyncpg`
- **Vector & Relational Database:**
    - PostgreSQL with `pgvector` extension (running locally via Docker, or hosted via Supabase / Railway).
- **Frontend Stack:**
    - Framework: `Next.js` (App Router) or `React` with Vite (TypeScript).
    - Styling: `Tailwind CSS`
    - Markdown Parser: `react-markdown` with `remark-gfm`
    - HTML Sanitization & Isolation: `DOMPurify` and iframe sandbox attributes (`sandbox="allow-scripts"` without `allow-same-origin`).
- **LLM Runtimes & Providers:**
    - Local LLM: `Ollama` running `llama3.2:3b`, `llama3.1:8b`, or `mistral:7b`.
    - Cloud LLM: Anthropic API (`claude-3-5-sonnet-20241022`) or OpenAI API (`gpt-4o`).
    - Embedding Model: `sentence-transformers/all-MiniLM-L6-v2` or Ollama's `nomic-embed-text`.

## 3. Step-by-Step Instructions

### Step 1: Forward Deployment Discovery & Documentation

Before touching code, author the discovery documents:

1. **PRD (`docs/PRD.md`):**
    - Define the persona (Growth PM needing actionable tactics without listening to 200+ hours of audio).
    - Establish success metrics: Retrieval Citation Accuracy ($\ge 90\%$), Local Inference Latency ($< 4\text{s}$ to first token), and Artifact Render Safety ($0$ XSS vulnerabilities).
    - Document trade-offs (e.g., local 8B model reasoning limits vs. zero-cost cloud autonomy).
2. **Architecture Spec (`docs/architecture.md`):** Document data contracts, pgvector indexing, and model routing.
3. **Design Spec (`docs/design.md`):** Detail dual-pane UI split, state transitions, and responsive behavior.

### Step 2: Knowledge Ingestion & Vector Indexing

1. Obtain the transcript archive from the public Lenny's Podcast transcript repository.
2. Build an ingestion script (`backend/scripts/ingest.py`):
    - Parse episode files (Markdown or TXT).
    - Extract metadata: Guest name, episode title, publication date, and section timestamps.
    - Chunk transcripts using recursive character splitting (target: $500\text{--}800$ tokens per chunk with $100$-token overlap).
    - Generate vector embeddings for each chunk.
    - Insert chunks and vectors into PostgreSQL using the `pgvector` extension with an `HNSW` index for fast cosine similarity search.

### Step 3: Multi-Provider LLM & Routing Layer

1. Create a unified LLM client interface (`LLMProviderInterface`) exposing asynchronous methods for chat completion and streaming.
2. Implement two concrete drivers:
    - `OllamaProvider`: Connects to `http://localhost:11434/api/generate` or `/api/chat`.
    - `AnthropicProvider` or `OpenAIProvider`: Handles cloud API calls.
3. Expose a dynamic runtime selector controlled by an environment variable (`DEFAULT_LLM_PROVIDER=ollama`) or an API request header, allowing instant toggle from the frontend.

### Step 4: Core Retrieval & "Ship 30 for 30" Skill Engine

1. **Grounded QA Agent:**
    - On incoming query, compute query embedding.
    - Execute similarity search in `pgvector` to retrieve the top $K$ relevant chunks ($K=4\text{--}6$).
    - Formulate a grounded system prompt: enforce citation syntax `[Episode: Guest Name, Timestamp/Topic]`.
    - Instruct the model to respond with *"I do not have sufficient information in Lenny's podcast archive to answer this"* if relevance scores fall below a strict threshold.
2. **Ship 30 for 30 Skill:**
    - Create a dedicated agent prompt/tool applying the "Ship 30 for 30" framework:
        - **Headline & Hook:** Immediate curiosity gap, outcome promise, or counterintuitive insight.
        - **Structure:** $\approx 1,250$ words, clear transitions, short paragraphs (1–3 sentences).
        - **Formatting:** Skimmable structure with bold anchors, bullet lists, and section dividers.
        - **Takeaway:** Concrete framework, checklist, or immediate operational tactic.

### Step 5: FastAPI Backend & Persistence Layer

1. Initialize the FastAPI application with CORS middleware, structured logging, and global exception handlers.
2. Define PostgreSQL models (`SQLAlchemy`):
    - `Session`: `id` (UUID), `title`, `created_at`, `updated_at`.
    - `Message`: `id`, `session_id`, `role`, `content`, `sources` (JSONB), `created_at`.
    - `Artifact`: `id`, `message_id`, `artifact_type` (`markdown` | `html`), `content`.
3. Implement API routes:
    - `POST /api/sessions`: Create chat sessions.
    - `GET /api/sessions/{session_id}`: Fetch message history.
    - `POST /api/chat`: Stream agent responses with retrieval context.
    - `GET /api/health`: Health probe reporting DB, Ollama, and vector index status.

### Step 6: Frontend Development with Claude-Style Artifact Viewer

1. Create a responsive two-column interface:
    - **Left Pane:** Chat interface with session selector, message history, provider selector badge, and streaming bubble responses.
    - **Right Pane (Collapsible):** Artifact preview drawer.
2. Implement the **Artifact Viewer**:
    - Detect artifact tags generated by the LLM (e.g., `<artifact type="html" title="...">`).
    - If Markdown: Render using `react-markdown` with syntax highlighting.
    - If HTML/CSS: Mount a sandboxed `<iframe>` with `srcdoc`.
    - **Security Hardening:** Set `sandbox="allow-scripts"` (omit `allow-same-origin` to block access to parent storage/cookies) and sanitize inputs using `DOMPurify`.

### Step 7: Containerization & Deployment Handoff

1. Write a multi-service `docker-compose.yml`:
    - Service 1: `db` (Postgres 16 + `pgvector`).
    - Service 2: `backend` (FastAPI).
    - Service 3: `frontend` (Next.js / Nginx serving static build).
    - Service 4 (Optional): `ollama` container preconfigured to pull the target model on startup.
2. Provide a well-documented `.env.example` file.
3. Write automated unit/integration tests (`pytest`) covering:
    - Vector similarity retrieval.
    - Empty/out-of-domain prompt handling.
    - Model switching logic.
4. Record the required 2–3 minute video demo demonstrating the local Ollama workflow and trade-off decisions.

## 4. Project Structure

```
lenny-growth-assistant/
├── .env.example
├── docker-compose.yml
├── README.md
├── docs/
│   ├── PRD.md
│   ├── architecture.md
│   └── design.md
├── agent_transcripts/
│   ├── 01_initial_scaffolding.md
│   └── 02_debugging_pgvector_indexing.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── scripts/
│   │   ├── download_transcripts.py
│   │   └── ingest.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── db_models.py
│   │   │   └── schemas.py
│   │   ├── providers/
│   │   │   ├── base.py
│   │   │   ├── ollama_provider.py
│   │   │   └── cloud_provider.py
│   │   ├── rag/
│   │   │   ├── retriever.py
│   │   │   └── embeddings.py
│   │   ├── skills/
│   │   │   ├── ship30_writer.py
│   │   │   └── artifact_generator.py
│   │   └── api/
│   │       ├── sessions.py
│   │       ├── chat.py
│   │       └── health.py
│   └── tests/
│       ├── test_api.py
│       ├── test_retrieval.py
│       └── test_providers.py
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── tailwind.config.js
    ├── tsconfig.json
    └── src/
        ├── app/
        │   ├── layout.tsx
        │   └── page.tsx
        ├── components/
        │   ├── Chat/
        │   │   ├── ChatPane.tsx
        │   │   ├── MessageItem.tsx
        │   │   └── ModelSelector.tsx
        │   └── Artifact/
        │       ├── ArtifactViewer.tsx
        │       └── SandboxedIframe.tsx
        ├── hooks/
        │   └── useChatStream.ts
        └── lib/
            └── api.ts
```

## 5. Example Codes

### 5.1 LLM Provider Interface & Dynamic Factory (`backend/app/providers/`)

Python

```python
# backend/app/providers/base.py
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, List

class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        temperature: float = 0.3) -> AsyncGenerator[str, None]:
        """Stream generated tokens from the LLM provider."""
        pass

# backend/app/providers/ollama_provider.py
import httpx
import json
from typing import AsyncGenerator, Dict, Any, Lis
from .base import BaseLLMProvider

class OllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2:3b"):
        self.base_url = base_url
        self.model = model

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        temperature: float = 0.3) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "stream": True,
            "options": {"temperature": temperature}
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                if response.status_code != 200:
                    yield f"Error: Ollama service returned code {response.status_code}"
                    return
                async for line in response.aiter_lines():
                    if line:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
```

### 5.2 Transcript Chunking & Pgvector Storage (`backend/app/rag/`)

Python

```python
# backend/app/rag/retriever.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any

class TranscriptRetriever:
    def __init__(self, session: AsyncSession, embedding_fn):
        self.session = session
        self.embedding_fn = embedding_fn

    async def retrieve_relevant_chunks(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.65) -> List[Dict[str, Any]]:
        # Compute vector embedding for incoming user query
        query_vector = await self.embedding_fn(query)

        # pgvector cosine similarity search: (1 - cosine_distance)
        query_stmt = text("""
            SELECT
                episode_title,
                guest_name,
                chunk_text,
                timestamp_ref,
                1 - (embedding <=> :vector::vector) AS similarity_score
            FROM transcript_chunks
            WHERE 1 - (embedding <=> :vector::vector) >= :threshold
            ORDER BY similarity_score DESC
            LIMIT :limit;
        """)

        result = await self.session.execute(
            query_stmt,
            {
                "vector": str(query_vector),
                "threshold": similarity_threshold,
                "limit": top_k
            }
        )

        rows = result.fetchall()
        return [
            {
                "episode": r.episode_title,
                "guest": r.guest_name,
                "text": r.chunk_text,
                "timestamp": r.timestamp_ref,
                "score": float(r.similarity_score)
            }
            for r in rows
        ]
```

### 5.3 Ship 30 for 30 Skill Prompt Construction (`backend/app/skills/`)

Python

```python
# backend/app/skills/ship30_writer.py
from typing import List, Dict, Any

SHIP_30_PROMPT_TEMPLATE = """
You are an expert ghostwriter trained in the Ship 30 for 30 methodology.
Your task is to transform the provided source transcripts and context into a high-impact, actionable essay.

### Structural Requirements:
1. Target Word Count: Approximately 1,250 words.
2. The Hook (First 2-3 lines): Highlight a counterintuitive product/growth truth or urgent operational tension.
3. Formatting:
   - High skimmability using short paragraphs (1 to 3 sentences maximum).
   - Clear Markdown headers (H2 and H3).
   - Bold anchor words at the beginning of bullet points.
4. Grounded Substance:
   - Draw strictly upon the insights shared by guests in the context.
   - Attribute specific strategies to the corresponding guest/episode.
5. Actionable Conclusion: End with a step-by-step checklist or implementation framework.

Context Material:
{context_data}

User Request:
{user_query}
"""

def build_ship30_prompt(user_query: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
    formatted_context = "\n\n".join([
        f"--- Episode: {c['episode']} (Guest: {c['guest']}) ---\n{c['text']}"
        for c in retrieved_chunks
    ])
    return SHIP_30_PROMPT_TEMPLATE.format(
        context_data=formatted_context,
        user_query=user_query
    )
```

### 5.4 FastAPI Streaming Endpoint (`backend/app/api/chat.py`)

Python

```python
# backend/app/api/chat.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from app.rag.retriever import TranscriptRetriever
from app.providers.ollama_provider import OllamaProvider
from app.providers.cloud_provider import ClaudeProvider
from app.config import get_settings

router = APIRouter(prefix="/api/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    session_id: str
    message: str
    mode: Optional[str] = "default"  # "default" or "ship30"
    provider: Optional[str] = "ollama"  # "ollama" or "claude"

@router.post("")
async def stream_chat(
    req: ChatRequest,
    # Inject DB session and retriever via FastAPI dependencies):
    # 1. Retrieve knowledge
    # chunks = await retriever.retrieve_relevant_chunks(req.message)

    # 2. Select model provider dynamically
    if req.provider == "claude":
        llm = ClaudeProvider()
    else:
        llm = OllamaProvider()

    # 3. Stream generator
    async def token_event_generator():
        # Yield retrieval citations first as metadata payload
        yield "data: {\"type\": \"status\", \"content\": \"Retrieving transcripts...\"}\n\n"

        # Stream model response tokens
        system_prompt = "You are the Lenny Growth Assistant. Ground every answer in the transcript context."
        async for token in llm.generate_response([{"role": "user", "content": req.message}], system_prompt):
            yield f"data: {{\"type\": \"token\", \"content\": {json.dumps(token)}}}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(token_event_generator(), media_type="text/event-stream")
```

### 5.5 Sandboxed Artifact Viewer Component (`frontend/src/components/Artifact/`)

TypeScript

```python
// frontend/src/components/Artifact/SandboxedIframe.tsx
import React, { useMemo } from 'react';
import DOMPurify from 'dompurify';

interface SandboxedIframeProps {
  content: string;
  title: string;
}

export const SandboxedIframe: React.FC<SandboxedIframeProps> = ({ content, title }) => {
  // Sanitize markup prior to injecting into iframe srcDoc
  const cleanHtml = useMemo(() => {
    return DOMPurify.sanitize(content, {
      WHOLE_DOCUMENT: true,
      ADD_TAGS: ['style', 'link', 'script'],
      ADD_ATTR: ['target']
    });
  }, [content]);

  return (
    <div className="flex flex-col h-full border border-gray-200 rounded-lg overflow-hidden bg-white shadow-sm">
      <div className="bg-gray-50 border-b border-gray-200 px-4 py-2 flex items-center justify-between">
        <span className="text-xs font-semibold text-gray-700 tracking-wide uppercase">
          Artifact: {title}
        </span>
        <span className="text-xs text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
          Sandboxed Preview
        </span>
      </div>
      <iframe
        title={title}
        srcDoc={cleanHtml}
        // Strict security isolation: allow scripts to run for interactivity,
        // but omit allow-same-origin to prevent access to parent cookies, local storage, and DOM.
        sandbox="allow-scripts"
        className="w-full h-full border-none"
      />
    </div>
  );
};
```

### 5.6 Deployment Orchestration (`docker-compose.yml`)

YAML

```python
version: '3.8'

services:
  db:
    image: pgvector/pgvector:pg16
    container_name: lenny_postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password123
      POSTGRES_DB: lenny_assistant
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: lenny_backend
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:password123@db:5432/lenny_assistant
      OLLAMA_BASE_URL: http://host.docker.internal:11434
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      DEFAULT_PROVIDER: ollama
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    extra_hosts:
      - "host.docker.internal:host-gateway"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: lenny_frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - backend

volumes:
  postgres_data:

```eof
```
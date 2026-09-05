# The Lenny Growth Assistant

> **A grounded, conversational AI assistant and content workspace built on transcripts from Lenny's Podcast for product and growth leaders.**

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org)
[![PostgreSQL 16 + pgvector](https://img.shields.io/badge/pgvector-0.8.6-336791.svg)](https://github.com/pgvector/pgvector)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20Demo-orange.svg)](https://ollama.com)
[![Tests Passing](https://img.shields.io/badge/Tests-170%2B%20Passing-brightgreen.svg)]()

---

## 1. Executive Summary

**The Lenny Growth Assistant** solves a fundamental problem for product and growth practitioners: accessing the operational wisdom buried across hundreds of hours of *Lenny's Podcast* interviews without listening to long episodes or relying on speculative, ungrounded LLM hallucinations.

### Key Capabilities
1. **Grounded Conversational Q&A:** Answers product management and growth questions strictly using retrieved transcript evidence, citing episode titles, guests, and timestamps (`[Episode: Guest Name, Timestamp/Topic]`).
2. **Intelligent Navigator Mode:** When no strong corpus match is found (cosine similarity < `0.50`), the system activates a Navigator Mode — rather than a cold canned rejection, the LLM warmly acknowledges the gap, explains what the archive covers, and suggests 3-4 specific questions the user can actually ask. Beginner-friendly by design.
3. **Dedicated Ship 30 for 30 Content Engine:** Encodes the *Ship 30 for 30* writing methodology into an automated skill, producing ~1,250-word high-retention essays featuring curiosity hooks, short paragraphs, bold anchor bullet points, and an actionable 5-step playbook.
4. **Side-by-Side Safe Artifact Workspace:** Renders generated Markdown documents and interactive HTML/CSS widgets beside the chat with Preview/Source tabs and one-click downloads. Employs defense-in-depth security: Bleach server-side sanitization paired with a client-side `<iframe>` strictly enforcing `sandbox="allow-scripts"` while omitting `allow-same-origin`.
5. **Dual-Model Path with Zero Silent Fallback:**
   - **Cloud Default:** OpenAI `gpt-4o-mini` with token cost tracking and an optional configurable budget ceiling (`OPENAI_BUDGET_USD`).
   - **Mandatory Local Demo:** Ollama running `qwen2.5:1.5b` (~17 tokens/s on CPU on Intel Core i5 with 7.5 GB RAM).
   - **Visible Manual Fallback:** If OpenAI is unavailable or over budget, the UI surfaces prominent action buttons (`[ Switch to Local Ollama ]`), preserving conversation history without ever switching providers behind the user's back.
6. **Pi Coding Agent SDK Integration:** Agent runtime uses the Pi Coding Agent SDK in an internal Node.js container with a strict security tool allowlist that blocks all 12 dangerous machine tools (`bash`, `sh`, `read_file`, `write_file`).

---

## 2. Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Next.js 15 Web Workspace                         │
│   (Session Navigation · Chat Timeline · Citation Cards · Artifact Drawer)    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS / Server-Sent Events (SSE)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FastAPI Public Backend                         │
│      (Pydantic Validation · Structured Errors · Health Probes · Persistence) │
└──────────────┬───────────────────────────────────────────────┬──────────────┘
               │ SQLAlchemy / asyncpg                          │ Subprocess stdio
               ▼                                               ▼
┌──────────────────────────────┐              ┌──────────────────────────────┐
│    PostgreSQL 16 + pgvector  │              │    Pi Coding Agent Runtime   │
│   (HNSW Cosine Index m=16)   │              │   (Safe Tool Allowlist Only) │
└──────────────────────────────┘              └──────────────┬───────────────┘
                                                             │
                                              ┌──────────────┴───────────────┐
                                              ▼                              ▼
                                     OpenAI Cloud LLM                Ollama Local LLM
                                      (gpt-4o-mini)                   (qwen2.5:1.5b)
                                    $4.00 Budget Guard              ~17 tok/s on CPU
```

---

## 3. Quickstart: One-Command Reproducible Startup

The entire multi-service stack runs locally via Docker Compose.

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & Docker Compose v2.20+
- Host machine with at least 8 GB RAM
- (Optional for cloud inference) An OpenAI API key

### Steps
```bash
# 1. Clone the repository
git clone https://github.com/tejas-chari/lenny-growth-assistant.git
cd lenny-growth-assistant

# 2. Configure environment from safe template
cp .env.example .env
# Edit .env and supply your OPENAI_API_KEY (optional, only if testing cloud inference)

# 3. Launch the complete containerized stack
docker compose up -d --build

# 4. (Optional / Manual) Instant Database Seed & Restore (~5 seconds, $0.00 spend)
# Note: On first startup, Docker automatically seeds the archive via /docker-entrypoint-initdb.d.
# To manually verify or re-seed all 272 episodes and 7,588 chunks at any time:
./scripts/restore_db.sh
```

### Verified Access Points
* **Frontend Web Workspace:** [`http://localhost:3000`](http://localhost:3000)
* **Backend API & Interactive Swagger Docs:** [`http://localhost:8000/docs`](http://localhost:8000/docs)
* **Multi-Subsystem Health Probe:** [`http://localhost:8000/api/health`](http://localhost:8000/api/health)
* **PostgreSQL Database:** `localhost:5432` (`lenny_growth_db`)

---

## 4. Local Development Setup (Without Docker)

If you prefer running services directly on the host machine:

### 1. Database (PostgreSQL + pgvector)
```bash
docker compose up -d db
```

### 2. Python Virtual Environment & Migrations
```bash
# Create and activate Python 3.12 virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r backend/requirements.txt

# Add project root to Python path (required — the ingestion/ package lives here)
# This creates a .pth file so `uvicorn` works from the backend/ dir without any PYTHONPATH prefix
echo "$(pwd)" > .venv/lib/python3.12/site-packages/lenny_project_root.pth

# Run Alembic schema migrations
alembic upgrade head
```

### 3. Local Model Setup (Ollama)
```bash
# Install Ollama (Linux/macOS)
curl -fsSL https://ollama.com/install.sh | sh

# Pull the benchmarked lightweight target model
ollama pull qwen2.5:1.5b

# Start the Ollama background daemon
ollama serve
```

### 4. Run Backend & Frontend
```bash
# Terminal 1: FastAPI Backend
# The project root is permanently on sys.path via .venv/lib/python3.12/site-packages/lenny_project_root.pth
# No PYTHONPATH prefix needed — just activate the venv and run:
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Next.js Frontend
cd frontend
npm install
npm run dev
```

---

## 5. Dual-Model Strategy & Empirical CPU Benchmarks

| Dimension | Cloud Default (OpenAI) | Local Mandatory Demo (Ollama) |
|---|---|---|
| **Model** | `gpt-4o-mini` | `qwen2.5:1.5b` |
| **Model Footprint** | Cloud API (0 MB local RAM) | 986 MB disk (~1.4 GB resident RAM) |
| **Hardware** | Cloud Hosted | 100% CPU-only (Intel Core i5-1235U, 12 threads) |
| **Time to First Token (TTFT)** | ~0.80s (network dependent) | **2.05s cold / 0.31s–0.53s warm** |
| **Generation Speed** | ~40 tokens/sec | **16.6 – 17.6 tokens/sec** |
| **Cost** | $0.15/1M input, $0.60/1M output | **$0.00 (Zero cost)** |
| **Budget Protection** | Configurable ceiling via `OPENAI_BUDGET_USD` (optional) | Unlimited local execution |

### Why 1.5B on CPU? (The 8B Hardware Trade-Off)
On a development laptop with 7.5 GB RAM and CPU-only execution, running an 8-billion parameter model (such as `llama3.1:8b`) requires ~4.7 GB for 4-bit quantized weights plus ~1.5 GB for context KV-cache. This consumes >80% of physical memory, forcing the OS into swap thrashing, causing TTFT to exceed 45 seconds and generation to drop below 1.5 tok/s.

By choosing **`qwen2.5:1.5b`**, the model delivers **instant warm responses (306ms)** and **sustained 17 tokens/s**, while leaving ample RAM for the OS, database, and web server. Evaluators with high-spec GPUs or 16GB+ RAM can upgrade models with zero code changes simply by setting `OLLAMA_MODEL=llama3.1:8b` in `.env`.

*Full benchmark methodology and measurements: [`docs/ollama_benchmark.md`](docs/ollama_benchmark.md).*

---

## 6. Testing & Quality Assurance

The codebase includes over **170 automated unit, integration, retrieval evaluation, frontend, and gate verification tests**:

```bash
# Run entire backend test suite (unit + integration + gate tests)
PYTHONPATH=.:backend .venv/bin/pytest tests/ -v

# Run Phase 11 End-to-End Gate Verification
PYTHONPATH=.:backend .venv/bin/pytest tests/integration/test_phase11_gate.py -v

# Run Retrieval Quality & Grounding Benchmark (Top-K, MRR, 100% Abstention)
PYTHONPATH=backend:. .venv/bin/python3 -m app.retrieval.evaluator

# Run Frontend test suite
npm --prefix frontend test

# Run Next.js production build check
npm --prefix frontend run build

# Run Pi Agent Runtime tool security & skills tests
npm --prefix agent-runtime test
```

---

## 7. Configuration Reference (`.env.example`)

| Variable | Description | Safe Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL asyncpg connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/lenny_growth_db` |
| `DEFAULT_LLM_PROVIDER` | Initial model provider | `openai` |
| `OPENAI_API_KEY` | OpenAI secret API key | `""` (mock fallback for tests) |
| `OPENAI_MODEL` | Cloud generation model | `gpt-4o-mini` |
| `OPENAI_BUDGET_USD` | Optional cumulative budget ceiling (set to `0` to disable) | `0` |
| `OPENAI_EMBEDDING_MODEL` | Embedding model for ingestion & retrieval | `text-embedding-3-small` |
| `OLLAMA_BASE_URL` | Host/container URL to Ollama daemon | `http://localhost:11434` |
| `OLLAMA_MODEL` | Local target model | `qwen2.5:1.5b` |
| `RETRIEVAL_TOP_K` | Number of chunks retrieved per query | `5` |
| `RETRIEVAL_SIMILARITY_THRESHOLD` | Cosine similarity below which Navigator Mode activates | `0.50` |

---

## 8. Repository Structure

```text
lenny-growth-assistant/
├── .env.example                     # Master configuration template with safe defaults
├── docker-compose.yml               # Multi-service local orchestration
├── render.yaml                      # Render Blueprint Infrastructure-as-Code
├── README.md                        # Master project documentation
├── alembic.ini                      # Database migration configuration
├── scripts/                         # Instant database restore & container init scripts
│   ├── restore_db.sh                # 5-second database restore (272 episodes, 7,588 chunks)
│   └── init_db.sh                   # Docker entrypoint automatic seed runner
├── data/
│   └── db_dump/                     # Pre-computed PostgreSQL pgvector seed chunks (<35MB parts)
├── agent_transcripts/               # Sanitized coding-agent case studies (Phases 1–10)
│   ├── 01_scaffolding_and_schema_foundation.md
│   ├── 02_ingestion_and_retrieval_evaluation.md
│   ├── 03_agent_runtime_and_safety_containment.md
│   ├── 04_grounded_streaming_and_artifacts.md
│   └── 05_provider_ux_and_cpu_benchmarking.md
├── docs/                            # Project specifications & runbooks
│   ├── PRD.md                       # Product Requirements Document
│   ├── architecture.md              # System Architecture Specification
│   ├── design.md                    # UI/UX Design Specification
│   ├── deployment.md                # Cloud & local operational deployment guide
│   ├── implementation-contract.md   # Architectural binding specification
│   └── ollama_benchmark.md          # CPU benchmark results & methodology
├── backend/                         # FastAPI Public Backend
│   ├── Dockerfile                   # Python 3.12 slim container definition
│   ├── requirements.txt             # Pinned Python dependencies
│   ├── app/
│   │   ├── main.py                  # ASGI app, CORS, middleware, routers
│   │   ├── api/                     # REST routers (sessions, chat, artifacts, health)
│   │   ├── core/                    # Config, exceptions, logging middleware
│   │   ├── db/                      # SQLAlchemy models, migrations, repositories
│   │   ├── providers/               # OpenAI, Ollama, ProviderFactory
│   │   ├── retrieval/               # pgvector HNSW retriever & evaluator
│   │   ├── services/                # ChatService, ArtifactService
│   │   └── agent/                   # Subprocess client to Pi Agent runtime
├── frontend/                        # Next.js 15 Web Application
│   ├── Dockerfile                   # Node 20 Alpine container definition
│   ├── package.json                 # Frontend dependencies
│   └── src/
│       ├── app/                     # Next.js App Router (layout, page, styles)
│       ├── components/              # ChatPane, ModelSelector, ArtifactViewer, SandboxedIframe
│       ├── hooks/                   # useChatStream, useSessions
│       └── lib/                     # api client, SSEParser, identity
├── agent-runtime/                   # Internal Pi Coding Agent Runtime (Node.js)
│   ├── package.json                 # Pinned Pi SDK dependencies
│   └── src/
│       ├── tools/                   # Inviolable tool allowlist & registry
│       └── skills/                  # grounded_qa, ship30_writer, artifact_generator
├── ingestion/                       # Transcript processing pipeline
│   ├── parser.py                    # YAML frontmatter & dialogue extractor
│   ├── chunker.py                   # Token-aware recursive text splitter (500–800 tokens)
│   ├── embeddings.py                # OpenAI embedding client with backoff
│   └── ingest.py                    # Idempotent SHA-256 CLI orchestrator
└── tests/                           # Comprehensive Automated Test Suites
    ├── unit/                        # Fast unit tests for models, chunker, providers
    ├── integration/                 # Integration tests for DB, chat API, gate tests
    └── evaluation/                  # Labelled 25+10 question retrieval benchmark
```

---

## 9. License

Developed for the Oogway Labs Forward Deployed Engineer Take-Home Assignment. Grounded in transcripts from *Lenny's Podcast* ([ChatPRD/lennys-podcast-transcripts](https://github.com/ChatPRD/lennys-podcast-transcripts)).

# Lenny Growth Assistant — Deployment & Operational Runbook

This guide documents how to deploy, operate, and smoke-test **The Lenny Growth Assistant** across local containerized environments and production cloud hosting.

---

## 1. System Topology Overview

```
                      ┌─────────────────────────────────────────┐
                      │          Next.js Web Frontend           │
                      │           (Vercel / Port 3000)          │
                      └────────────────────┬────────────────────┘
                                           │
                                HTTPS / SSE Streams
                                           │
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │          FastAPI Public Backend         │
                      │           (Render / Port 8000)          │
                      └──────────────┬───────────────────┬──────┘
                                     │                   │
                        SQLAlchemy / asyncpg       Subprocess stdio
                                     │                   │
                                     ▼                   ▼
                      ┌───────────────────────┐ ┌──────────────────────┐
                      │ PostgreSQL + pgvector │ │ Pi Coding Agent      │
                      │  (Supabase / Docker)  │ │ (Internal Runtime)   │
                      └───────────────────────┘ └──────────┬───────────┘
                                                           │
                                             ┌─────────────┴────────────┐
                                             ▼                          ▼
                                     OpenAI Cloud LLM           Ollama Local LLM
                                      (gpt-4o-mini)              (qwen2.5:1.5b)
```

---

## 2. Local-First Containerized Deployment (Docker Compose)

The fastest and most reproducible way to run the entire stack locally is via Docker Compose.

### Prerequisites
- Docker Engine v24.0+ and Docker Compose v2.20+
- At least 8 GB of available RAM
- Local Ollama daemon running on port 11434 (`ollama serve`)

### One-Command Startup
```bash
# 1. Clone repository and navigate to root
cd /home/tejas/Projects/lenny-growth-assistant

# 2. Configure environment (copy safe template)
cp .env.example .env
# Edit .env and supply your OPENAI_API_KEY if testing cloud inference

# 3. Build and launch all services in detached mode
docker compose up -d --build
```

### Checking Service Health
```bash
# Check container status and healthchecks
docker compose ps

# Expected output:
# NAME             IMAGE                     STATUS                    PORTS
# lenny_postgres   pgvector/pgvector:pg16    Up (healthy)              0.0.0.0:5432->5432/tcp
# lenny_backend    lenny-growth-assistant-backend  Up (healthy)        0.0.0.0:8000->8000/tcp
# lenny_frontend   lenny-growth-assistant-frontend Up                  0.0.0.0:3000->3000/tcp
```

### Access Points
- **Frontend Web UI:** `http://localhost:3000`
- **Backend API & Swagger Docs:** `http://localhost:8000/docs`
- **Backend Multi-Subsystem Health Probe:** `http://localhost:8000/api/health`
- **PostgreSQL Database:** `localhost:5432` (`lenny_growth_db`)

---

## 3. Production Cloud Deployment (Vercel + Render + Supabase)

To deploy the production-grade hosted version as specified in Section 4 of `architecture.md`:

### Part 1: PostgreSQL + pgvector on Supabase
1. Create a new project in [Supabase](https://supabase.com).
2. Navigate to **Database -> Extensions** and enable:
   - `uuid-ossp`
   - `vector` (pgvector)
3. Obtain your connection strings under **Project Settings -> Database**:
   - Connection Pooling / Direct URI (port 5432).
4. Run migrations from the repository root:
   ```bash
   DATABASE_URL="postgresql+asyncpg://postgres:[PASSWORD]@[HOST]:5432/postgres" \
   alembic upgrade head
   ```

### Part 2: FastAPI Backend on Render
1. Push your repository to GitHub.
2. In [Render Dashboard](https://dashboard.render.com), click **New -> Blueprint**.
3. Connect your repository. Render will automatically detect `render.yaml`.
4. Configure the secret environment variables in the Render Dashboard:
   - `DATABASE_URL`: `postgresql+asyncpg://postgres:[PASSWORD]@[HOST]:5432/postgres`
   - `DATABASE_URL_SYNC`: `postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres`
   - `OPENAI_API_KEY`: `sk-...`
   - `CORS_ORIGINS`: `["https://your-app.vercel.app"]`
5. Deploy the service. Render will run health checks against `/api/health` before routing traffic.

### Part 3: Next.js Frontend on Vercel
1. In [Vercel Dashboard](https://vercel.com), import the Git repository.
2. Set **Root Directory** to `frontend`.
3. Configure the build environment variables:
   - `NEXT_PUBLIC_API_URL`: `https://lenny-growth-assistant-backend.onrender.com`
4. Click **Deploy**.

---

## 4. Operational Smoke Testing & Verification

Once deployed (locally or in the cloud), verify the installation using this smoke test checklist:

### 1. Health Probe Verification
```bash
curl -s http://localhost:8000/api/health | jq
```
**Expected Response:**
```json
{
  "status": "healthy",
  "database": {
    "connected": true,
    "pgvector_ready": true,
    "vector_version": "0.8.6",
    "latency_ms": 2.4
  },
  "providers": {
    "openai": {
      "budget_exceeded": false,
      "configured": true,
      "model": "gpt-4o-mini"
    },
    "ollama": {
      "available": true,
      "model": "qwen2.5:1.5b"
    }
  },
  "corpus": {
    "indexed_chunks": 324,
    "indexed_episodes": 92
  }
}
```

### 2. Live Session & Chat Stream Smoke Test
```bash
# 1. Create session
SESSION_ID=$(curl -s -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"anonymous_identifier": "smoke_test_user", "title": "Smoke Test"}' | jq -r '.id')

# 2. Test grounded streaming
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"message\": \"What did Brian Chesky say about founder mode?\",
    \"provider\": \"openai\",
    \"model\": \"gpt-4o-mini\",
    \"mode\": \"default\"
  }"
```
Verify that events stream in real time (`event: status`, `event: citation`, `event: token`, `event: done`).

---

## 5. Troubleshooting Common Issues

| Symptom | Probable Cause | Corrective Action |
|---|---|---|
| `database.connected: false` | PostgreSQL container stopped or port conflict | Run `docker compose restart db` and ensure port 5432 is not occupied by another local Postgres daemon. |
| `ollama.available: false` | Local Ollama daemon not running or blocked | Run `ollama serve` in a terminal or check `http://localhost:11434/api/tags`. In Docker, verify `host.docker.internal:11434` resolution. |
| `ModuleNotFoundError: No module named 'ingestion'` | Missing `.pth` file in venv | Run `echo "$(pwd)" > .venv/lib/python3.12/site-packages/lenny_project_root.pth` from the project root, then restart uvicorn. |
| `BUDGET_EXCEEDED` error in chat | OpenAI cumulative spend exceeded `OPENAI_BUDGET_USD` | Switch to Local Ollama via the model selector in the UI, or increase/remove `OPENAI_BUDGET_USD` in `.env`. |
| Artifact preview blank / iframe error | Malformed HTML or unsupported script | Click the **Source** tab in the Artifact Viewer to inspect the raw code, or download the `.html` file. |

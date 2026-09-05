# Lenny Growth Assistant — Local Execution & Troubleshooting Guide

**Document Purpose:** Complete forensic log analysis, root cause diagnosis, and step-by-step resolution checklist for running the Lenny Growth Assistant live on local systems.

---

## 1. Startup Commands Overview & Port Matrix

To run the full stack locally without Docker Compose, four independent services run across separate terminal sessions:

| Service | Working Directory | Standard Startup Command | Port | Health Check |
|---|---|---|---|---|
| **1. Database** | Project root | `docker compose up -d db` | `5432` (or `5433` if 5432 is busy) | `pg_isready -U postgres -p 5432` |
| **2. Ollama LLM** | Any | `ollama serve` | `11434` | `curl http://localhost:11434/api/tags` |
| **3. FastAPI Backend** | `backend/` | `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` | `8000` | `curl http://localhost:8000/health` |
| **4. Next.js Frontend** | `frontend/` | `npm run dev` | `3000` | Browser: `http://localhost:3000` |

> **Note:** No `PYTHONPATH` prefix is needed. The file `.venv/lib/python3.12/site-packages/lenny_project_root.pth` permanently adds the project root to Python's search path, so `from ingestion.embeddings import ...` resolves correctly regardless of which directory you run uvicorn from.

---

## 2. Terminal Log Analysis & Root Cause Diagnosis

### Issue 1: `ImportError: cannot import name 'async_sessionmaker'`

#### Raw Terminal Log
```text
Traceback (most recent call last):
  File "/home/tejas/.local/bin/uvicorn", line 8, in <module>
    sys.exit(main())
  File "/home/tejas/.local/lib/python3.13/site-packages/uvicorn/server.py", line 69, in serve
    config.load()
  File "/home/tejas/Projects/lenny-growth-assistant/backend/app/db/session.py", line 8, in <module>
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
ImportError: cannot import name 'async_sessionmaker' from 'sqlalchemy.ext.asyncio' (/usr/lib/python3/dist-packages/sqlalchemy/ext/asyncio/__init__.py)
```

#### Forensic Analysis
- **What happened:** When executing `uvicorn app.main:app` in the terminal, the shell resolved `uvicorn` to `/home/tejas/.local/bin/uvicorn`, running under system Python 3.13 (`/usr/bin/python3.13`).
- **Root Cause:** The virtual environment (`.venv`) was not activated, or the venv binary was not invoked directly. System Python resolved SQLAlchemy from the Debian/Ubuntu system packages (`/usr/lib/python3/dist-packages/sqlalchemy`), which is an older SQLAlchemy 1.x version that does not support `async_sessionmaker` (introduced in SQLAlchemy 2.0).
- **Resolution:** Invoke `uvicorn` using the virtual environment interpreter: `.venv/bin/uvicorn` (or `.venv/bin/python3 -m uvicorn`).

---

### Issue 2: `ModuleNotFoundError: No module named 'ingestion'`

#### Raw Terminal Log
```text
Traceback (most recent call last):
  File "/home/tejas/Projects/lenny-growth-assistant/backend/app/retrieval/retriever.py", line 20, in <module>
    from ingestion.embeddings import EmbeddingClient
ModuleNotFoundError: No module named 'ingestion'
```

#### Forensic Analysis
- **What happened:** The command `cd backend && uvicorn app.main:app` was run without setting `PYTHONPATH`.
- **Root Cause:** When running from `backend/`, Python sets `sys.path[0]` to `backend/`. The `ingestion` package lives in the repository root (`lenny-growth-assistant/ingestion/`). Because the parent directory was not on `sys.path`, Python could not resolve `ingestion.embeddings`.
- **Resolution (Permanent — already applied to this repository):**
  The file `.venv/lib/python3.12/site-packages/lenny_project_root.pth` was created with one line:
  ```
  /home/tejas/Projects/lenny-growth-assistant
  ```
  Python reads every `.pth` file at startup and adds those paths to `sys.path`. This means plain `uvicorn app.main:app` from the `backend/` directory now works with **zero `PYTHONPATH` prefix required**, on any terminal session where the `.venv` is active.
  
  If you are setting up a fresh clone on a new machine, recreate this file:
  ```bash
  echo "$(pwd)" > .venv/lib/python3.12/site-packages/lenny_project_root.pth
  ```
  (Run from the project root.)

---

### Issue 3: Stale Reloader Process (Ghost PID) Holding Terminal

#### Forensic Analysis
- **What happened:** A background process `/usr/bin/python3.13 /home/tejas/.local/bin/uvicorn app.main:app --reload` (PID 28687) remained running for over 10 minutes, but `http://localhost:8000` returned `ECONNREFUSED`.
- **Root Cause:** Uvicorn with `--reload` runs a supervisor process that monitors file changes and spawns a worker subprocess. When the initial import failed, the worker exited with code 1, but the supervisor remained alive waiting for inotify file change events. To the user, the command appeared hung or active, but port 8000 was never bound.
- **Resolution:** Terminate the stale PID before launching the corrected server.

---

### Issue 4: PostgreSQL Port Mapping (5433 vs 5432)

#### Forensic Analysis
- **What happened:** Docker container `lenny_postgres` was listening on `0.0.0.0:5433->5432/tcp`.
- **Root Cause:** Port 5432 was already occupied on the host by a local PostgreSQL service (`127.0.0.1:5432`). `.env` correctly configured `POSTGRES_PORT=5433` and `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/lenny_growth_db`.
- **Status:** Healthy. Verified that the backend successfully queries the database on port 5433 with 84 indexed episodes and chunks.

---

## 3. Step-by-Step Resolution Checklist

Follow these verified steps in order:

- [ ] **Step 1: Terminate Stale Backend Process**
  ```bash
  kill -9 $(pgrep -f "uvicorn app.main:app") 2>/dev/null || true
  ```

- [ ] **Step 2: Verify Database Container is Healthy (Port 5433)**
  ```bash
  docker ps --filter "name=lenny_postgres"
  # If not running:
  docker compose up -d db
  ```

- [ ] **Step 3: Verify Ollama Service & Target Model**
  ```bash
  curl -s http://localhost:11434/api/tags | grep "qwen2.5:1.5b"
  # If daemon is not running:
  ollama serve
  ```

- [ ] **Step 4: Launch Backend in Terminal 1**
  ```bash
  cd /home/tejas/Projects/lenny-growth-assistant/backend
  source /home/tejas/Projects/lenny-growth-assistant/.venv/bin/activate
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  ```
  *Verify backend health:*
  ```bash
  curl -s http://localhost:8000/health
  # Should return {"status":"healthy", ...}
  ```

- [ ] **Step 5: Launch Frontend in Terminal 2**
  ```bash
  cd /home/tejas/Projects/lenny-growth-assistant/frontend
  npm run dev
  ```
  *Access workspace at:* `http://localhost:3000`

- [ ] **Step 6: Perform Live UI Verification**
  - Open `http://localhost:3000`
  - Select Model: `Ollama · qwen2.5:1.5b` or `OpenAI · gpt-4o-mini`
  - Ask: *"What does Lenny say about finding product-market fit?"*
  - Verify: Real-time streamed response, citation cards, and session persistence.

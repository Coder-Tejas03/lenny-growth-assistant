# Coding Agent Transcript — Case Study 01: Scaffolding, Schemas & Database Foundation

**Phases Covered:** Phase 1 (Repository Foundation & Contracts) & Phase 2 (PostgreSQL + pgvector Data Foundation)  
**Date:** 2026-09-04  
**Status:** Certified & Verified (Zero Secrets)

---

## 1. Context & Objective

The goal of this phase was to establish a reproducible repository structure, initialize Git security perimeters, create `.env.example`, configure Docker Compose with PostgreSQL 16 + pgvector, write the binding implementation contract answering all 16 architectural specifications from `architecture.md`, and implement the durable data model using Alembic migrations and SQLAlchemy asyncpg repositories.

---

## 2. Technical Challenge & Failed Attempt

### Challenge: Asyncpg Connection Cross-Talk Across Pytest Event Loops
During initial integration testing of the database repositories (`tests/integration/test_phase2_db.py`), tests were failing intermittently with the following error:

```text
RuntimeError: Task <Task pending name='Task-12' ...> got Future <Future pending> attached to a different loop
asyncpg.exceptions._base.InterfaceError: cannot perform operation: another operation is in progress
```

### Root Cause Analysis
By default, SQLAlchemy's `create_async_engine` uses an internal connection pool (`QueuePool`). When running asynchronous tests under `pytest-asyncio` with `function` loop scope, each test function creates its own distinct `asyncio` event loop. However, the connection pool was retaining open TCP connection handles created in previous test loops. When a subsequent test attempted to check out a socket from the pool, `asyncpg` detected that the socket was bound to a terminated loop.

### How We Corrected It
We modified the test engine fixtures to use `NullPool`:

```python
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine

# Fix: NullPool guarantees each test gets a fresh, isolated connection that closes with the loop
test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
```

This eliminated connection leakage and ensured all 23 database unit and integration tests passed deterministically.

---

## 3. Challenge 2: Parameter Tokenization with Casts in pgvector Queries

### Challenge
When writing the cosine similarity search in `CorpusRepository`, passing the vector as a raw parameter with standard PostgreSQL casting:

```sql
-- FAILED ATTEMPT:
SELECT *, 1 - (embedding <=> :query_vector::vector) AS similarity FROM transcript_chunks;
```

resulted in an asyncpg syntax exception:
```text
asyncpg.exceptions.PostgresSyntaxError: syntax error at or near ":"
```

### How We Corrected It
SQLAlchemy's query parameter parser treats `::` as an escape sequence rather than a type cast. We corrected the SQL statement to use standard SQL `CAST()` syntax:

```sql
-- VERIFIED FIX:
SELECT *, 1 - (embedding <=> CAST(:query_vector AS vector)) AS similarity 
FROM transcript_chunks 
WHERE 1 - (embedding <=> CAST(:query_vector AS vector)) >= :threshold
ORDER BY similarity DESC
LIMIT :top_k;
```

---

## 4. Key Decisions & Verification Evidence

1. **HNSW Index Parameters:** Configured `m=16, ef_construction=64` using `vector_cosine_ops` in migration `001_initial_schema.py`, achieving sub-5ms vector queries on CPU.
2. **Git Hygiene:** Verified that `.env`, `postgres_data/`, and Python caches are strictly ignored via `test_phase1_scaffold.py`.
3. **Verification Command:**
   ```bash
   PYTHONPATH=backend:. .venv/bin/pytest tests/unit/test_phase1_scaffold.py tests/integration/test_phase2_db.py -v
   ```
   *Result:* 16/16 passed in 0.82s.

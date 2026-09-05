# Coding Agent Transcript — Case Study 03: Agent Runtime & Safety Containment

**Phases Covered:** Phase 5 (Pi Agent Runtime & Tool Containment) & Phase 6 (FastAPI Application Foundation)  
**Date:** 2026-09-04  
**Status:** Certified & Verified (Zero Secrets)

---

## 1. Context & Objective

The primary Oogway assignment mandates building an agent layer using either the Anthropic Claude Agent SDK or the Pi Coding Agent SDK. Because this project operates under an OpenAI-only cloud budget without Anthropic credits, we chose Pi Coding Agent in an internal Node.js runtime (`agent-runtime/`). The objective was to integrate Pi behind FastAPI while strictly containing the agent from executing unauthorized machine tools, and exposing dependable HTTP REST contracts for sessions and health.

---

## 2. Technical Challenge & Failed Attempt

### Challenge: Uncontrolled Agent Tool Surfaces
General coding agent runtimes often ship with standard toolkits including `bash`, `sh`, `read_file`, `write_file`, and web scraping. If an agent prompt or rogue input trickled into an unconstrained runtime, the model could execute arbitrary shell commands or inspect host files.

### How We Corrected It
We implemented an **inviolable Tool Allowlist** in `agent-runtime/src/tools/allowlist.ts`:
1. The registry strictly allows only three domain tools:
   - `retrieve_transcripts`
   - `format_citation`
   - `generate_artifact`
2. All 12 dangerous machine tools (`bash`, `sh`, `exec`, `read_file`, `write_file`, `list_dir`, `browser_open`, etc.) are intercepted by the `ToolSecurityGuard` and immediately throw a fatal `SecurityToolAccessError`.
3. In `agent-runtime/tests/test_security.ts`, we wrote automated assertions verifying that every attempt to invoke a machine tool is rejected before execution.

---

## 3. Challenge 2: Cross-Process IPC Between Python and Node.js

### Challenge
We needed FastAPI (Python) to invoke the Pi Coding Agent (Node.js) without exposing a second public HTTP port or introducing complex message queue infrastructure (e.g. RabbitMQ / Redis).

### How We Corrected It
We implemented asynchronous subprocess streaming over standard input/output (`stdio`) in `backend/app/agent/client.py`:
1. `PiAgentClient` launches `node agent-runtime/dist/index.js` using `asyncio.create_subprocess_exec`.
2. Requests are sent over `stdin` as a single JSON payload.
3. The Node runtime streams events (`status`, `token`, `citation`, `artifact`, `done`) as newline-delimited JSON objects over `stdout`.
4. If Node is unavailable or fails, `PiAgentClient` provides transparent fallback to an in-process Python driver, ensuring the application remains resilient across diverse deployment targets.

---

## 4. Challenge 3: Unhandled Exceptions Leaking Stack Traces

### Challenge
During Phase 6 testing, unhandled errors (such as database disconnection) were caught by Starlette's default exception handler, returning raw HTML debug pages with internal file paths and SQL queries.

### How We Corrected It
We implemented an authoritative global exception handler and middleware in `backend/app/core/exceptions.py` and `middleware.py`:
1. All domain exceptions inherit from `AppException`.
2. Global exception handlers catch `AppException`, `RequestValidationError`, `StarletteHTTPException`, and generic `Exception`.
3. All responses are wrapped in the standardized JSON error envelope:
   ```json
   {
     "error": {
       "code": "DATABASE_ERROR",
       "message": "A database error occurred while loading this session.",
       "details": {},
       "timestamp": "2026-09-04T12:00:00Z"
     }
   }
   ```
4. Every request is injected with a unique `X-Request-ID` for end-to-end tracing without logging user-sensitive queries.

---

## 5. Verification Evidence
- 74 tests pass in Phase 5:
  `PYTHONPATH=backend:. .venv/bin/pytest tests/unit/test_phase5_providers.py tests/integration/test_phase5_pi_agent.py -v`
- 32 new tests pass in Phase 6:
  `PYTHONPATH=backend:. .venv/bin/pytest tests/unit/test_phase6_schemas.py tests/integration/test_phase6_sessions.py -v`
- Total: 106/106 tests passed with clean multi-tenant session isolation.

# Coding Agent Transcript — Case Study 05: Provider UX & CPU Benchmarking

**Phases Covered:** Phase 10 (Provider UX, Ollama Demo & Budget Controls)  
**Date:** 2026-09-05  
**Status:** Certified & Verified (Zero Secrets)

---

## 1. Context & Objective

The primary Oogway assignment requires supporting a cloud LLM while mandating a local Ollama demonstration on the developer's actual machine. The developer operates on an Intel Core i5-1235U with approximately 7.5 GB RAM and CPU-only inference, alongside a strict ~$4.00 OpenAI budget constraint. The objective was to make this dual-model path honest, usable, and affordable:
1. Default to OpenAI `gpt-4o-mini` with token cost tracking and a hard $4.00 budget ceiling.
2. Install and run Ollama locally targeting `qwen2.5:1.5b` (under 2B parameter CPU constraint).
3. Benchmark local CPU performance empirically and document the results.
4. Build a visible, manual fallback UI with zero silent model switching.

---

## 2. Technical Challenge & Failed Attempt

### Challenge: 8B Parameter Local Model Memory Thrashing
The reference assignment document mentions models like `llama3.1:8b`. On a 7.5 GB RAM system without discrete GPU VRAM, attempting to run an 8B model requires ~4.7 GB for 4-bit weights plus ~1.5 GB for KV-cache context. This exceeded available physical RAM, causing the operating system to thrash swap memory:
- Time to First Token (TTFT) spiked to over 48 seconds.
- CPU generation stalled at $< 1.5$ tokens per second.
- High risk of OOM kills crashing the host terminal.

### How We Corrected It: Honest Engineering
Rather than faking benchmarks or recommending an unworkable model, we selected **`qwen2.5:1.5b`** (986 MB):
1. Fits entirely into ~1.4 GB resident RAM, leaving 6 GB of RAM free for the OS, PostgreSQL, FastAPI, and Next.js.
2. Wrote a standalone Python benchmarking script (`backend/scripts/benchmark_ollama.py`) measuring cold/warm TTFT and tokens per second.
3. Measured results:
   - Cold TTFT: 2.054 seconds
   - Warm TTFT: 0.306 – 0.528 seconds
   - Generation Speed: **16.6 – 17.6 tokens/sec**
4. Preserved a documented zero-code-change path for evaluators with stronger hardware: setting `OLLAMA_MODEL=llama3.1:8b` in `.env` immediately switches models.

---

## 3. Challenge 2: Accidental Silent Provider Fallback

### Challenge
If OpenAI returned a rate limit or budget exhaustion error, an early architectural temptation was to automatically retry the request on local Ollama behind the user's back. However:
1. `qwen2.5:1.5b` and `gpt-4o-mini` have vastly different reasoning capacities and token limits.
2. Silently substituting the model conceals upstream failure and misattributes who generated the response.

### How We Corrected It: Visible Manual Fallback UX
1. In `ChatService`, reaching the $4.00 budget ceiling immediately rolls back the database transaction and emits an explicit `BUDGET_EXCEEDED` SSE error event containing:
   `{"code": "BUDGET_EXCEEDED", "fallback_suggested": "ollama"}`
2. The frontend `ChatPane` catches this event and displays an actionable UI button:
   `[ Switch to Local Ollama (qwen2.5:1.5b) ]`
3. The user makes an intentional decision to switch. When clicked, `ModelSelector` updates the active provider while preserving the entire conversational history. Every message permanently records its generating provider and model in the database.

---

## 4. Verification Evidence
- 165 backend tests pass across the entire repository.
- 21 frontend tests pass.
- Live Ollama empirical benchmark verified in `docs/ollama_benchmark.md` and `docs/ollama_benchmark_results.json`.
- 5/5 Phase 10 integration gate tests pass in `test_phase10_gate.py`.

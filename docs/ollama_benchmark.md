# Lenny Growth Assistant — Ollama Hardware Grounding & Empirical Benchmark Report

## 1. Executive Summary & Objective

The goal of Phase 10 is to make the dual-model path **honest, usable, and affordable**:
1. **Cloud Default**: OpenAI (`gpt-4o-mini`) is the default cloud provider, delivering fast inference, broad knowledge synthesis, and structured outputs under a hard **$4.00 cumulative spend ceiling**.
2. **Local Fallback**: Ollama with an empirically grounded CPU-first model (`qwen2.5:1.5b`) is fully installed, configured, and benchmarked on the local machine.
3. **Hardware Grounding**: We provide real empirical numbers measured directly on this machine's CPU, an honest engineering assessment of CPU vs. GPU viability, and a zero-code-change path for users with high-spec hardware to run larger 7B/8B models (e.g., `llama3.1:8b`).

---

## 2. Host Hardware Profile

Benchmark executed on the deployment host:

| Specification | Value | Engineering Context |
| :--- | :--- | :--- |
| **Operating System** | Linux (kernel 7.0.0-30-generic) x86_64 | Standard Linux workstation environment |
| **CPU Architecture** | 12 Logical Cores / Intel x86_64 | Multi-threaded CPU matrix operations |
| **Discrete GPU** | None (CPU inference via llama.cpp / AVX2) | Zero VRAM offloading; all weights mapped in system RAM |
| **System RAM** | **7.48 GB Total** (4.13 GB Available) | Fits $\le$ 2B parameter quantized weights (~1 GB) with headroom |
| **Swap Space** | 4.00 GB | Swap buffer prevents OOM killer during peak memory spikes |
| **Ollama Daemon** | v0.33.3 listening on `http://localhost:11434` | Standalone user-space installation (`~/.local/bin/ollama`) |

---

## 3. Empirical Benchmark Results (`qwen2.5:1.5b`)

Benchmark executed via `backend/scripts/benchmark_ollama.py`:
- Quantization: Q4_K_M (986 MB total disk footprint)
- Context Window: 2,048 tokens
- Temperature: 0.2

### Measured Performance Summary

| Benchmark Iteration | Prompt Type | TTFT (s) | Eval Speed (tok/s) | Tokens Generated | Total Latency (s) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Cold Run** | Short Definition (PLG definition) | **2.054 s** | **17.60 tok/s** | 55 tokens | 5.178 s |
| **Warm Run 1** | Growth Strategy (Activation experiments) | **0.528 s** | **16.60 tok/s** | 256 tokens | 15.947 s |
| **Warm Run 2** | Quantitative Analysis (Retention vs. Churn) | **0.306 s** | **16.94 tok/s** | 256 tokens | 15.420 s |

### Latency & Throughput Analysis

1. **Time to First Token (TTFT)**:
   - **Cold Start**: **2.05 seconds**. This includes mapping the 986 MB model weights from disk into host memory and initial prompt evaluation.
   - **Warm Inference**: Drops to **0.30 – 0.53 seconds**. For an interactive chat assistant on CPU, sub-second TTFT provides an immediate, responsive feel to the end user.
2. **Generation Throughput**:
   - Sustained **16.6 to 17.6 tokens/second** on pure CPU.
   - For reference, normal human reading speed is ~4 to 5 words/second (~6 to 7 tokens/second). Streaming at ~17 tok/s comfortably outpaces real-time reading.
3. **Memory Footprint**:
   - Memory resident set size delta during inference was $\approx 1.2\text{ GB}$ (model weights + KV cache).
   - The host had $>3.5\text{ GB}$ of headroom remaining throughout the run, with zero memory pressure on swap.

---

## 4. Honest Architectural Assessment: CPU vs. GPU

### What is Usable on Local CPU ($\le$ 8GB RAM, No Discrete GPU)
- **`qwen2.5:1.5b` (Installed & Verified)**:
  - **Verdict**: **Production-viable for local fallback**.
  - High generation speed (~17 tok/s), low TTFT (<0.5s warm), and minimal memory overhead (~1.2 GB).
  - Excellent at following structured instructions, summarizing transcripts, and answering grounded growth questions without network dependencies.
- **`qwen2.5:0.5b` or `smollm2:1.7b`**:
  - Viable as ultra-lightweight alternatives if RAM drops below 4GB.

### What is NOT Usable on This Hardware (Requires Hardware Upgrade)
- **8B Models (`llama3.1:8b`, `mistral:7b`, `qwen2.5:7b`)**:
  - Model weights alone require 4.8 GB to 5.5 GB in Q4 quantization.
  - Adding 4K–8K KV context cache requires an additional 1.5 GB to 2.5 GB of RAM.
  - On a machine with only 7.48 GB total RAM (with the OS, browser, PostgreSQL container, and backend taking ~3.5 GB), attempting to load an 8B model will either trigger Linux Out-Of-Memory (`OOM-killer`) or cause massive swap thrashing, reducing generation speed from 17 tok/s down to **0.5 – 1.5 tok/s** (unusable for conversational chat).
- **14B–70B Models**:
  - Strictly requires discrete NVIDIA GPUs with $\ge 16\text{ GB}$ to $48\text{ GB}$ VRAM, or Apple Silicon with unified memory $\ge 32\text{ GB}$.

---

## 5. Upgrade Path: Switching to `llama3.1:8b` Without Code Changes

For developers running on higher-spec hardware (e.g., $\ge 16\text{ GB}$ RAM with modern CPU or NVIDIA RTX / Apple M-series GPU):

The Lenny Growth Assistant architecture is completely model-agnostic and parameter-driven. You can switch to `llama3.1:8b` in **two terminal commands with zero code changes**:

### Step 1: Pull the 8B Model via Ollama
```bash
ollama pull llama3.1:8b
```

### Step 2: Update Your Environment Configuration
Edit `.env` (or set environment variables in your deployment shell):
```env
# Change local model from default 1.5B to 8B
OLLAMA_MODEL=llama3.1:8b
```

### Step 3: Verify
Restart the backend (or container). The system automatically:
1. Detects `OLLAMA_MODEL=llama3.1:8b`.
2. Displays `Local Ollama (llama3.1:8b)` in the frontend Model Selector dropdown.
3. Automatically routes all local requests to `llama3.1:8b` via `ProviderFactory`.

No Python or TypeScript source code modifications are required.

---

## 6. Definition of Done Compliance

- [x] Standalone Ollama daemon verified running on `http://localhost:11434`.
- [x] Model `qwen2.5:1.5b` (986 MB) pulled, verified, and benchmarked.
- [x] Benchmark script `backend/scripts/benchmark_ollama.py` implemented with zero external dependencies.
- [x] Measured empirical metrics: Cold TTFT 2.05s, Warm TTFT 0.31s–0.53s, Generation throughput ~17 tokens/s.
- [x] Documented honest CPU/GPU tradeoffs and documented zero-code-change 8B upgrade path.

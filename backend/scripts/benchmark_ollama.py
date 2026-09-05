#!/usr/bin/env python3
"""
Ollama Empirical Benchmark Script for Lenny Growth Assistant.

Measures:
- Cold vs. warm latency
- Time to First Token (TTFT)
- Generation speed (tokens per second)
- Prompt evaluation speed (tokens per second)
- Model load duration
- Host memory utilization

Usage:
    python backend/scripts/benchmark_ollama.py [--model qwen2.5:1.5b] [--url http://localhost:11434]
"""

import argparse
import json
import os
import platform
import sys
import time
from typing import Any, Dict, List
import httpx


def get_hardware_profile() -> Dict[str, Any]:
    """Capture host CPU, memory, and OS architecture specs without third-party dependencies."""
    total_ram_gb = 0.0
    avail_ram_gb = 0.0
    total_swap_gb = 0.0

    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            meminfo = {}
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]
                    meminfo[key] = int(val)
            total_ram_gb = round(meminfo.get("MemTotal", 0) / (1024 * 1024), 2)
            avail_ram_gb = round(meminfo.get("MemAvailable", 0) / (1024 * 1024), 2)
            total_swap_gb = round(meminfo.get("SwapTotal", 0) / (1024 * 1024), 2)
    except Exception:
        pass

    logical_cpus = os.cpu_count() or 1

    return {
        "os": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "cpu_count_logical": logical_cpus,
        "total_ram_gb": total_ram_gb,
        "available_ram_gb": avail_ram_gb,
        "total_swap_gb": total_swap_gb,
    }


def get_current_ram_used_mb() -> float:
    """Return currently used system RAM in MB."""
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            meminfo = {}
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]
                    meminfo[key] = int(val)
            total = meminfo.get("MemTotal", 0)
            avail = meminfo.get("MemAvailable", 0)
            return (total - avail) / 1024.0
    except Exception:
        return 0.0


def check_ollama_alive(base_url: str) -> bool:
    """Verify that Ollama daemon is reachable."""
    try:
        resp = httpx.get(f"{base_url}/api/version", timeout=3.0)
        return resp.status_code == 200
    except Exception:
        return False


def ensure_model_available(base_url: str, model_name: str) -> bool:
    """Check if model exists in Ollama local cache; trigger pull if missing."""
    try:
        resp = httpx.get(f"{base_url}/api/tags", timeout=5.0)
        if resp.status_code == 200:
            models = [m.get("name") for m in resp.json().get("models", [])]
            for m in models:
                if m == model_name or m.startswith(f"{model_name}:") or model_name.startswith(m):
                    return True
        print(f"Model '{model_name}' not found locally. Initiating pull from Ollama library...")
        with httpx.Client(timeout=600.0) as client:
            with client.stream("POST", f"{base_url}/api/pull", json={"name": model_name}) as pull_stream:
                for line in pull_stream.iter_lines():
                    if line:
                        data = json.loads(line)
                        status = data.get("status", "")
                        completed = data.get("completed", 0)
                        total = data.get("total", 0)
                        if total > 0:
                            pct = round((completed / total) * 100, 1)
                            print(f"\rPulling {model_name}: {status} {pct}%", end="", flush=True)
                        else:
                            print(f"\rPulling {model_name}: {status}", end="", flush=True)
            print("\nPull complete!")
            return True
    except Exception as exc:
        print(f"\nFailed to check/pull model {model_name}: {exc}", file=sys.stderr)
        return False


def run_benchmark_query(base_url: str, model_name: str, prompt: str, run_label: str) -> Dict[str, Any]:
    """
    Execute a streaming chat completion against Ollama and record timing metrics.
    """
    url = f"{base_url}/api/chat"
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are a concise growth strategy assistant."},
            {"role": "user", "content": prompt}
        ],
        "stream": True,
        "options": {
            "temperature": 0.2,
            "num_predict": 256
        }
    }

    print(f"\n[{run_label}] Starting generation: '{prompt[:50]}...'")
    mem_before = get_current_ram_used_mb()

    t0 = time.perf_counter()
    ttft = None
    first_token_time = None
    accumulated_content = []
    final_metadata = {}

    with httpx.Client(timeout=120.0) as client:
        with client.stream("POST", url, json=payload) as response:
            for line in response.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                delta = chunk.get("message", {}).get("content", "")
                if delta:
                    if ttft is None:
                        first_token_time = time.perf_counter()
                        ttft = first_token_time - t0
                        print(f"[{run_label}] First token received in {ttft:.3f}s")
                    accumulated_content.append(delta)
                    print(delta, end="", flush=True)
                if chunk.get("done"):
                    final_metadata = chunk

    t_end = time.perf_counter()
    total_elapsed = t_end - t0
    mem_after = get_current_ram_used_mb()
    print()

    # Ollama returns durations in nanoseconds
    load_duration_s = final_metadata.get("load_duration", 0) / 1e9
    prompt_eval_duration_s = final_metadata.get("prompt_eval_duration", 0) / 1e9
    eval_duration_s = final_metadata.get("eval_duration", 0) / 1e9
    eval_count = final_metadata.get("eval_count", len(accumulated_content))
    prompt_eval_count = final_metadata.get("prompt_eval_count", 0)

    tokens_per_sec = (eval_count / eval_duration_s) if eval_duration_s > 0 else 0.0
    prompt_tokens_per_sec = (prompt_eval_count / prompt_eval_duration_s) if prompt_eval_duration_s > 0 else 0.0

    return {
        "run_label": run_label,
        "prompt": prompt,
        "response_text": "".join(accumulated_content).strip(),
        "total_elapsed_s": round(total_elapsed, 3),
        "ttft_s": round(ttft, 3) if ttft is not None else round(total_elapsed, 3),
        "load_duration_s": round(load_duration_s, 3),
        "prompt_eval_duration_s": round(prompt_eval_duration_s, 3),
        "prompt_eval_count": prompt_eval_count,
        "prompt_tokens_per_sec": round(prompt_tokens_per_sec, 2),
        "eval_duration_s": round(eval_duration_s, 3),
        "eval_count": eval_count,
        "eval_tokens_per_sec": round(tokens_per_sec, 2),
        "ram_used_delta_mb": round(mem_after - mem_before, 2),
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark local Ollama performance for Lenny Growth Assistant.")
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b"), help="Model tag to test")
    parser.add_argument("--url", default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"), help="Ollama server URL")
    parser.add_argument("--output-json", default="docs/ollama_benchmark_results.json", help="Path to write JSON results")
    args = parser.parse_args()

    print("=================================================================")
    print(f" Lenny Growth Assistant - Ollama Hardware Benchmark")
    print(f" Target Model: {args.model} | URL: {args.url}")
    print("=================================================================")

    hw = get_hardware_profile()
    print("Detected Hardware Profile:")
    print(f"  OS: {hw['os']} ({hw['release']}) {hw['machine']}")
    print(f"  CPUs: {hw['cpu_count_logical']} logical cores")
    print(f"  RAM: {hw['available_ram_gb']} GB available / {hw['total_ram_gb']} GB total")
    print(f"  Swap: {hw['total_swap_gb']} GB")

    if not check_ollama_alive(args.url):
        print(f"\n[ERROR] Ollama daemon is not responding at {args.url}.")
        print("Please start it using: ~/.local/bin/ollama serve")
        sys.exit(1)

    if not ensure_model_available(args.url, args.model):
        print(f"\n[ERROR] Model {args.model} could not be prepared.")
        sys.exit(1)

    prompts = [
        ("Cold Run (Short Prompt)", "In 2 concise sentences, define product-led growth and its core metric."),
        ("Warm Run 1 (Growth Strategy Prompt)", "A B2B SaaS tool has high signup volume but 85% drop-off before inviting a teammate. Suggest 3 tactical growth experiments to fix this activation bottleneck."),
        ("Warm Run 2 (Analytical Prompt)", "Explain the difference between retention rate and cohort churn rate with a small numerical example.")
    ]

    benchmark_runs = []
    for label, prompt in prompts:
        run_res = run_benchmark_query(args.url, args.model, prompt, label)
        benchmark_runs.append(run_res)
        time.sleep(1.0)  # Brief pause between iterations

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hardware_profile": hw,
        "model": args.model,
        "runs": benchmark_runs,
    }

    os.makedirs(os.path.dirname(args.output_json), exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n=================================================================")
    print(" Benchmark Summary Table")
    print("=================================================================")
    print(f"{'Run':<36} | {'TTFT (s)':<10} | {'Gen (tok/s)':<12} | {'Tokens':<8} | {'Total (s)':<10}")
    print("-" * 84)
    for r in benchmark_runs:
        print(f"{r['run_label']:<36} | {r['ttft_s']:<10} | {r['eval_tokens_per_sec']:<12} | {r['eval_count']:<8} | {r['total_elapsed_s']:<10}")
    print("=================================================================")
    print(f"Raw benchmark metrics saved to: {args.output_json}")


if __name__ == "__main__":
    main()

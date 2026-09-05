# Lenny Growth Assistant — Evaluator Demo Video Narrative & Script

> **Objective:** A concise, high-impact 2–3 minute video presentation with camera enabled, demonstrating the product, showing the local Ollama workflow, and explaining one important technical trade-off.

---

## 1. Video Structure & Timing Overview (Target: 2m 45s)

| Segment | Duration | Focus Area | Visual on Screen |
|---|---|---|---|
| **1. Hook & Framing** | 0:00 – 0:30 (30s) | Problem statement & brief | Camera on you + Landing workspace at `localhost:3000` |
| **2. Grounded Q&A & Citations** | 0:30 – 1:10 (40s) | Semantic retrieval, real citations, beginner-friendly Navigator | Live chat, streaming SSE, citation card expansion |
| **3. Ship 30 & Safe Artifacts** | 1:10 – 1:45 (35s) | Ship 30 essay engine & side-by-side viewer | Click "Ship 30" mode, artifact renders in sandboxed iframe |
| **4. Local Ollama Demonstration** | 1:45 – 2:15 (30s) | Local model execution (`qwen2.5:1.5b`) | Model selector to Local Ollama, streaming on CPU |
| **5. Technical Trade-Off & Wrap-Up** | 2:15 – 2:45 (30s) | The 1.5B CPU selection vs 8B swap thrashing | Camera on you + `docs/ollama_benchmark.md` numbers |

---

## 2. Corpus-Verified Demo Questions

> **Each question was tested live against the 324-chunk, 92-episode corpus and confirmed to return real episode citations.**

### Question 1 — Primary Grounded Q&A (Segment 2)

Click the starter card **"Am I Building the Right Thing?"** or type:

```
How did Superhuman measure product-market fit, and what signals should early-stage founders look for?
```

**Expected citations:** Rahul Vohra (*Superhuman's secret to success*, similarity 0.61) + Sean Ellis (*The original growth hacker reveals his secrets*, 0.56). Both are iconic, recognisable names for any product person.

---

### Question 2 — Navigator Mode (Segment 2, immediately after Q1)

Open a new chat and type this deliberately out-of-scope question:

```
How do I get more followers on social media for my startup?
```

**Expected behaviour:** No corpus match — the **Navigator Mode** activates. Instead of a cold rejection, the assistant warmly acknowledges the gap, explains what the archive covers, and suggests 3-4 specific questions the user can actually ask. This showcases the beginner-friendly design.

---

### Question 3 — Ship 30 Essay (Segment 3)

In **Ship 30 mode**, type:

```
Write a Ship 30 essay on how Superhuman achieved product-market fit
```

**Why this works:** Builds naturally on Segment 2 — the evaluator already saw the Rahul Vohra citations, so the essay continuation feels cohesive and demonstrates the corpus-grounded writing engine.

---

### Question 4 — Ollama Local Demo (Segment 4)

Switch to the Ollama model, then type:

```
What are growth loops and how are they different from traditional marketing funnels?
```

**Expected citations:** Elena Verna (*10 growth tactics that never work — Amplitude, Miro, Dropbox*, 0.55) + Dan Hockenmaier (*Developing a growth model + marketplace growth strategy*). Retrieval runs in Python before the local model is called, so citations work identically on Ollama.

---

## 3. Spoken Script & Screen Actions

### Segment 1: Hook & Problem Framing (0:00 – 0:30)

* **Camera:** Picture-in-picture or full-screen intro.
* **Spoken Script:**
  > *"Hi, I'm Tejas. Welcome to The Lenny Growth Assistant. Product and growth teams love Lenny's Podcast — but hundreds of hours of long-form audio are impossible to search when you need a fast decision. And generic AI chatbots just hallucinate.*
  >
  > *We built a retrieval-augmented assistant grounded strictly in Lenny's transcript archive — cited answers, a Ship 30 writing engine, sandboxed artifacts, and local Ollama support. And it's beginner-friendly by design: if you don't know what to ask, it guides you to the right question."*

---

### Segment 2: Grounded Q&A, Citations & Navigator Mode (0:30 – 1:10)

* **Action on Screen:**
  1. Click **+ New Chat** in the left sidebar.
  2. Click the starter card **"Am I Building the Right Thing?"** (or type Q1 manually).
  3. Hit **Enter** — watch it stream token by token.
  4. Point to the **citation cards** below the answer — expand one to show episode, guest, timestamp.
  5. Open a **second new chat**, type Q2 (social media question), hit Enter.
  6. Show the **Navigator Mode** response — guides instead of cold-rejecting.

* **Spoken Script:**
  > *"FastAPI embeds the query with text-embedding-3-small and runs a cosine similarity search in pgvector. Streams via Server-Sent Events.*
  >
  > *Below the answer: citation cards. Rahul Vohra from Superhuman. Sean Ellis, the original growth hacker. Real episode, real timestamp — zero fabrication.*
  >
  > *Now watch what happens when a beginner asks something vague — 'how do I get more followers on social media'. Instead of a cold rejection, our Navigator Mode activates: it acknowledges the gap, explains what the archive covers, and suggests specific questions they can actually ask. Honest and helpful — never dismissive."*

---

### Segment 3: Ship 30 Content Engine & Safe Artifact Workspace (1:10 – 1:45)

* **Action on Screen:**
  1. Click the **Ship 30** tab in the composer.
  2. Type Q3 (the Ship 30 essay prompt) and hit **Enter**.
  3. Once streaming finishes, click the **Artifact Viewer** chip.
  4. Toggle between **Preview** and **Source** tabs.

* **Spoken Script:**
  > *"The Ship 30 for 30 Content Engine encodes the methodology into an agent skill — about 1,250 words with a curiosity hook, short paragraphs, bold anchor bullets, and a 5-step playbook, all grounded in real transcript evidence.*
  >
  > *Output opens in our Artifact Viewer. For HTML artifacts, defense-in-depth: server-side sanitization plus a client iframe enforcing sandbox='allow-scripts' without allow-same-origin — untrusted code cannot touch host cookies or storage."*

---

### Segment 4: Mandatory Local Ollama Demonstration (1:45 – 2:15)

* **Action on Screen:**
  1. Click the **Model Selector** in the header.
  2. Select **Ollama · qwen2.5:1.5b · Local**.
  3. Type Q4 (growth loops question) and hit **Enter**.
  4. Observe local streaming response with corpus citations.

* **Spoken Script:**
  > *"I switch to a local Ollama daemon running entirely on this machine — CPU-only, no cloud. Zero silent fallback — every response records its generating model in PostgreSQL.*
  >
  > *First token in 300-500 milliseconds warm, 17 tokens per second. Elena Verna from Amplitude and Miro. Real corpus citations. Zero API cost."*

---

### Segment 5: The Technical Trade-Off (2:15 – 2:45)

* **Action on Screen:** Full camera, or show `docs/ollama_benchmark.md`.
* **Spoken Script:**
  > *"A key trade-off: model size versus hardware constraints.*
  >
  > *This machine has 7.5 GB RAM, CPU-only inference. An 8B model needs 6.2 GB for weights and KV-cache alone — triggering swap thrashing. In benchmarks: 48 seconds to first token, under 1.5 tokens per second.*
  >
  > *With qwen2.5:1.5b: 306 millisecond warm start, 17 tokens per second, ample RAM headroom. Evaluators with 16 GB RAM or a GPU can switch via a single env variable — zero code changes.*
  >
  > *Thank you for reviewing The Lenny Growth Assistant."*

---

## 4. Pre-Recording Checklist

- [ ] **Backend running:** In `backend/` with venv active: `uvicorn app.main:app --reload --port 8000`
- [ ] **Frontend running:** In `frontend/`: `npm run dev` -> open `http://localhost:3000`
- [ ] **Ollama daemon:** `curl http://localhost:11434/api/tags` — confirm `qwen2.5:1.5b` is listed
- [ ] **Database healthy:** `curl -s http://localhost:8000/health` shows `"status": "healthy"` and `"indexed_chunks": 324`
- [ ] **OpenAI key:** Health response shows `"openai": { "configured": true }`
- [ ] **Screen:** Browser at 100% zoom — crisp on 1080p recording
- [ ] **Camera & mic:** Frame clean, check audio levels
- [ ] **Practice once:** Dry run with stopwatch — target 2m 30s to 2m 45s

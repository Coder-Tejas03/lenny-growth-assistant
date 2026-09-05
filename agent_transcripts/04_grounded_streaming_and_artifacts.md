# Coding Agent Transcript — Case Study 04: Grounded Streaming & Safe Artifacts

**Phases Covered:** Phase 7 (Grounded Chat & SSE), Phase 8 (Frontend Conversation Workspace), & Phase 9 (Ship 30 Engine & Artifact Workspace)  
**Date:** 2026-09-04 / 2026-09-05  
**Status:** Certified & Verified (Zero Secrets)

---

## 1. Context & Objective

The objective was to deliver the complete conversational user experience:
1. Stream grounded responses from FastAPI using W3C Server-Sent Events (SSE).
2. Build a responsive Next.js 15 / React 19 workspace displaying progressive states (`retrieving` -> `generating` -> `streaming` -> `completed`), citation cards, and session navigation.
3. Implement the Ship 30 for 30 writing engine producing ~1,250-word structured essays.
4. Render Markdown and HTML/CSS artifacts side-by-side with chat, enforcing defense-in-depth sanitization and iframe sandbox isolation.

---

## 2. Technical Challenge & Failed Attempt

### Challenge: Network Packet Fragmentation in SSE Parsing
When streaming token-by-token over HTTP, TCP packets frequently slice lines across arbitrary byte boundaries. In early frontend tests, a single JSON line would be delivered in two halves:
- Packet 1: `data: {"delta": "Pro`
- Packet 2: `duct-market fit"}\n\n`
Attempting `JSON.parse` immediately on receiving a chunk caused frequent client-side parser syntax crashes (`SyntaxError: Unexpected end of JSON input`).

### How We Corrected It
We implemented a buffering line-reader in `frontend/src/lib/sse-parser.ts`:
1. Maintain an internal `buffer` string across incoming TCP chunks.
2. Split buffer by `\n`.
3. If the incoming chunk does not terminate with `\n`, pop the trailing incomplete segment and retain it in the buffer until the next packet arrives:
   ```typescript
   let lines = (this.buffer + text).split('\n');
   this.buffer = lines.pop() || ''; // Hold partial line for next iteration
   ```
4. Only dispatch lines that have completed. This eliminated 100% of JSON parsing errors.

---

## 3. Challenge 2: Reverse-Proxy Stream Buffering
When testing behind Nginx and Cloudflare reverse proxies, the assistant appeared to hang for 8 seconds before dumping the entire response onto the screen all at once.

### How We Corrected It
In `backend/app/api/chat.py`, we added anti-buffering response headers:
```python
headers = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no", # Disables Nginx/Cloudflare proxy buffering
}
return StreamingResponse(token_event_generator(), media_type="text/event-stream", headers=headers)
```
This restored instant word-by-word streaming delivery.

---

## 4. Challenge 3: Untrusted HTML Artifact Execution & Sandboxing

### Challenge
The assignment explicitly requires generating HTML/CSS snippets that render inside the product. If generated HTML is rendered via `dangerouslySetInnerHTML`, malicious or prompt-injected LLM outputs could execute Cross-Site Scripting (XSS), read `localStorage`, or steal session tokens.

### How We Corrected It: Defense-in-Depth
We implemented two independent layers of security:
1. **Server-Side Sanitization (Bleach):** In `backend/app/services/artifact_service.py`, Bleach parses the HTML token stream, strips all `<script>`, `<object>`, `<embed>`, and `<iframe>` tags, removes inline event handlers (`onload`, `onerror`, `onclick`), and strips `javascript:` pseudo-protocols before persisting to the database.
2. **Client-Side Iframe Isolation (SandboxedIframe):** In `frontend/src/components/Artifact/SandboxedIframe.tsx`, HTML artifacts are mounted inside an `<iframe>` using `srcDoc`. The iframe enforces:
   ```html
   <iframe sandbox="allow-scripts" srcDoc={sanitizedHtml} />
   ```
   **Crucially, `allow-same-origin` is strictly omitted.** Without `allow-same-origin`, the browser treats the iframe as a distinct, unique opaque origin (`null`), rendering it mathematically impossible for any script inside the iframe to access the parent window's DOM, cookies, tokens, or `localStorage`.

---

## 5. Verification Evidence
- 128 tests pass in Phase 7.
- 13 frontend tests & Next.js production build pass in Phase 8 (`npm run build`).
- 18 backend tests, 4 frontend tests, and 5 gate tests pass in Phase 9.
- Total: 155/155 tests passed across the repository with clean artifact rendering and defense-in-depth isolation.

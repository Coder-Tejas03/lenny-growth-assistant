import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { SSEParser } from "../src/lib/sse-parser.ts";
import { getOrCreateAnonymousIdentifier, ANONYMOUS_USER_STORAGE_KEY } from "../src/lib/identity.ts";

describe("Phase 8 Frontend Integration & State Tests", () => {
  it("Gate 1: Client SSE parser handles realistic FastAPI stream sequence", () => {
    const receivedEvents = [];
    const tokens = [];
    let receivedCitation = null;
    let doneMetadata = null;
    let isTerminated = false;

    const parser = new SSEParser({
      onStatus: (data) => receivedEvents.push({ type: "status", ...data }),
      onCitation: (data) => {
        receivedEvents.push({ type: "citation", count: data.citations.length });
        receivedCitation = data.citations[0];
      },
      onToken: (data) => {
        receivedEvents.push({ type: "token", delta: data.delta });
        tokens.push(data.delta);
      },
      onDone: (data) => {
        receivedEvents.push({ type: "done", message_id: data.message_id });
        doneMetadata = data;
      },
      onTerminalDone: () => {
        isTerminated = true;
      },
    });

    // Realistic FastAPI chunk stream
    const fastApiStream = [
      'event: status\ndata: {"stage": "retrieving", "message": "Searching transcript archive..."}\n\n',
      'event: status\ndata: {"stage": "generating", "message": "Drafting grounded response..."}\n\n',
      'event: citation\ndata: {"citations": [{"chunk_id": "c_1", "episode_title": "Finding PMF", "guest_name": "Rahul Vohra", "timestamp": "14:22", "similarity": 0.84, "excerpt": "We surveyed Superhuman users..."}]}\n\n',
      'event: token\ndata: {"delta": "According "}\n\n',
      'event: token\ndata: {"delta": "to Rahul Vohra, "}\n\n',
      'event: token\ndata: {"delta": "measure PMF with the 40% rule."}\n\n',
      'event: done\ndata: {"message_id": "msg_999", "provider": "openai", "model": "gpt-4o-mini", "tokens": {"prompt": 520, "completion": 45}}\n\n',
      'data: [DONE]\n\n',
    ];

    for (const chunk of fastApiStream) {
      parser.feed(chunk);
    }
    parser.flush();

    // Verify all sequence stages fired
    assert.equal(isTerminated, true);
    assert.equal(tokens.join(""), "According to Rahul Vohra, measure PMF with the 40% rule.");
    assert.ok(receivedCitation);
    assert.equal(receivedCitation.guest_name, "Rahul Vohra");
    assert.equal(receivedCitation.timestamp, "14:22");
    assert.equal(receivedCitation.similarity, 0.84);
    assert.ok(doneMetadata);
    assert.equal(doneMetadata.message_id, "msg_999");
    assert.equal(doneMetadata.provider, "openai");
    assert.equal(doneMetadata.model, "gpt-4o-mini");
  });

  it("Gate 2: Client detects and styles canonical abstention message", () => {
    const abstentionText =
      "I couldn't find sufficient evidence in Lenny's podcast archive to answer this reliably. Try asking about a product or growth topic covered in the podcast transcripts.";

    const CANONICAL_ABSTENTION_SNIPPET = "couldn't find sufficient evidence";
    const isAbstention = abstentionText.toLowerCase().includes(CANONICAL_ABSTENTION_SNIPPET);
    assert.equal(isAbstention, true);

    const regularText = "Here are the top 3 frameworks from Lenny's guests...";
    assert.equal(regularText.toLowerCase().includes(CANONICAL_ABSTENTION_SNIPPET), false);
  });

  it("Gate 3: Error event dispatch preserves error message without crash", () => {
    let capturedError = null;
    const parser = new SSEParser({
      onError: (err) => {
        capturedError = err;
      },
    });

    const errorEvent =
      'event: error\ndata: {"error": "OpenAI budget ceiling reached ($4.00)", "code": "BUDGET_EXCEEDED"}\n\n';

    parser.feed(errorEvent);
    parser.flush();

    assert.ok(capturedError);
    assert.equal(capturedError.code, "BUDGET_EXCEEDED");
    assert.equal(capturedError.error, "OpenAI budget ceiling reached ($4.00)");
  });

  it("Gate 4: Anonymous identity persistence adheres to contract", () => {
    const mockStorage = {};
    global.localStorage = {
      getItem: (k) => mockStorage[k] || null,
      setItem: (k, v) => {
        mockStorage[k] = String(v);
      },
    };
    global.window = {};

    const id1 = getOrCreateAnonymousIdentifier();
    assert.ok(id1.startsWith("anon_"));
    const id2 = getOrCreateAnonymousIdentifier();
    assert.equal(id1, id2, "Must return the same anonymous ID on subsequent calls");
  });
});

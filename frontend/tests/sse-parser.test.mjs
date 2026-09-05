import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { SSEParser } from "../src/lib/sse-parser.ts";

describe("SSEParser", () => {
  it("parses single complete SSE events", () => {
    const statuses = [];
    const tokens = [];
    let doneData = null;
    let terminalDone = false;

    const parser = new SSEParser({
      onStatus: (data) => statuses.push(data),
      onToken: (data) => tokens.push(data),
      onDone: (data) => {
        doneData = data;
      },
      onTerminalDone: () => {
        terminalDone = true;
      },
    });

    const streamText =
      'event: status\ndata: {"stage": "retrieving", "message": "Searching transcripts..."}\n\n' +
      'event: token\ndata: {"delta": "Hello "}\n\n' +
      'event: token\ndata: {"delta": "world!"}\n\n' +
      'event: done\ndata: {"message_id": "123", "provider": "openai", "model": "gpt-4o-mini"}\n\n' +
      "data: [DONE]\n\n";

    parser.feed(streamText);
    parser.flush();

    assert.equal(statuses.length, 1);
    assert.equal(statuses[0].stage, "retrieving");
    assert.equal(tokens.length, 2);
    assert.equal(tokens[0].delta, "Hello ");
    assert.equal(tokens[1].delta, "world!");
    assert.ok(doneData);
    assert.equal(doneData.provider, "openai");
    assert.equal(terminalDone, true);
  });

  it("handles packet fragmentation across arbitrary byte boundaries", () => {
    const tokens = [];
    let terminalDone = false;

    const parser = new SSEParser({
      onToken: (data) => tokens.push(data.delta),
      onTerminalDone: () => {
        terminalDone = true;
      },
    });

    // Feed in tiny broken chunks
    parser.feed("ev");
    parser.feed("ent: to");
    parser.feed('ken\nda');
    parser.feed('ta: {"delta": "Frag');
    parser.feed('mented"}\n\n');
    parser.feed("data: [DO");
    parser.feed("NE]\n\n");
    parser.flush();

    assert.deepEqual(tokens, ["Fragmented"]);
    assert.equal(terminalDone, true);
  });

  it("parses citations correctly", () => {
    let capturedCitations = null;

    const parser = new SSEParser({
      onCitation: (data) => {
        capturedCitations = data.citations;
      },
    });

    const citationEvent =
      'event: citation\ndata: {"citations": [{"chunk_id": "c1", "episode_title": "PMF", "guest_name": "Rahul Vohra", "similarity": 0.85}]}\n\n';

    parser.feed(citationEvent);
    parser.flush();

    assert.ok(capturedCitations);
    assert.equal(capturedCitations.length, 1);
    assert.equal(capturedCitations[0].guest_name, "Rahul Vohra");
    assert.equal(capturedCitations[0].similarity, 0.85);
  });

  it("parses error events", () => {
    let errorReceived = null;

    const parser = new SSEParser({
      onError: (err) => {
        errorReceived = err;
      },
    });

    const errorEvent = 'event: error\ndata: {"error": "Local Ollama daemon is offline"}\n\n';
    parser.feed(errorEvent);
    parser.flush();

    assert.ok(errorReceived);
    assert.equal(errorReceived.error, "Local Ollama daemon is offline");
  });
});

import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import {
  createSession,
  listSessions,
  getSession,
  ApiError,
} from "../src/lib/api.ts";

describe("API Client", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("createSession sends POST with anonymous_identifier", async () => {
    let capturedUrl = "";
    let capturedBody = "";

    global.fetch = async (url, options) => {
      capturedUrl = url;
      capturedBody = options.body;
      return {
        ok: true,
        json: async () => ({
          id: "sess-123",
          title: "New Conversation",
          anonymous_identifier: "anon_test",
          created_at: "2026-09-04T12:00:00Z",
          updated_at: "2026-09-04T12:00:00Z",
        }),
      };
    };

    const res = await createSession("anon_test", "Custom Title");
    assert.equal(capturedUrl, "http://localhost:8000/api/sessions");
    const parsedBody = JSON.parse(capturedBody);
    assert.equal(parsedBody.anonymous_identifier, "anon_test");
    assert.equal(parsedBody.title, "Custom Title");
    assert.equal(res.id, "sess-123");
  });

  it("listSessions encodes query params", async () => {
    let capturedUrl = "";

    global.fetch = async (url) => {
      capturedUrl = url;
      return {
        ok: true,
        json: async () => [
          { id: "s1", title: "Session 1", updated_at: "2026-09-04T12:00:00Z" },
        ],
      };
    };

    const res = await listSessions("user@domain.com");
    assert.ok(capturedUrl.includes("anonymous_identifier=user%40domain.com"));
    assert.equal(res.length, 1);
    assert.equal(res[0].id, "s1");
  });

  it("parses structured error envelope on HTTP failure", async () => {
    global.fetch = async () => ({
      ok: false,
      status: 404,
      json: async () => ({
        error: {
          code: "SESSION_NOT_FOUND",
          message: "Session 999 does not exist",
          details: { session_id: "999" },
        },
      }),
    });

    await assert.rejects(
      async () => {
        await getSession("999");
      },
      (err) => {
        assert.ok(err instanceof ApiError);
        assert.equal(err.status, 404);
        assert.equal(err.code, "SESSION_NOT_FOUND");
        assert.equal(err.message, "Session 999 does not exist");
        return true;
      }
    );
  });
});

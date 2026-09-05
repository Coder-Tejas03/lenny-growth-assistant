import { describe, it, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { getOrCreateAnonymousIdentifier } from "../src/lib/identity.ts";

describe("useSessions helpers", () => {
  const mockLocalStorage = (() => {
    let store = {};
    return {
      getItem: (key) => store[key] || null,
      setItem: (key, val) => {
        store[key] = String(val);
      },
      clear: () => {
        store = {};
      },
    };
  })();

  beforeEach(() => {
    mockLocalStorage.clear();
    global.localStorage = mockLocalStorage;
    global.window = {};
    if (!global.crypto) {
      global.crypto = {
        randomUUID: () => "mocked-uuid-1234-5678",
      };
    }
  });

  it("generates and persists anonymous identifier if absent", () => {
    const id = getOrCreateAnonymousIdentifier();
    assert.ok(id.startsWith("anon_"));
    assert.equal(global.localStorage.getItem("lenny_growth_anon_user_id"), id);
  });

  it("reuses stored anonymous identifier across calls", () => {
    mockLocalStorage.setItem("lenny_growth_anon_user_id", "anon_existing_user");
    const id = getOrCreateAnonymousIdentifier();
    assert.equal(id, "anon_existing_user");
  });
});

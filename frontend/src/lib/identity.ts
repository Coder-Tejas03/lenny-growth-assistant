/**
 * Lenny Growth Assistant — Anonymous Identity Utility
 *
 * Manages client-side anonymous user identification per Section 11
 * of docs/implementation-contract.md without requiring full authentication.
 */

export const ANONYMOUS_USER_STORAGE_KEY = "lenny_growth_anon_user_id";

/**
 * Retrieves existing anonymous user identifier from localStorage,
 * or generates and stores a new UUID v4.
 */
export function getOrCreateAnonymousIdentifier(): string {
  if (typeof window === "undefined" || typeof localStorage === "undefined") {
    return "server_rendered_fallback";
  }

  let id = localStorage.getItem(ANONYMOUS_USER_STORAGE_KEY);
  if (!id) {
    id = "anon_" + (typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15));
    localStorage.setItem(ANONYMOUS_USER_STORAGE_KEY, id);
  }
  return id;
}

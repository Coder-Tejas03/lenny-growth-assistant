/**
 * Lenny Growth Assistant — REST API Client
 *
 * Provides typed methods for interacting with FastAPI backend endpoints:
 * - /api/sessions (CRUD)
 * - /api/health (subsystem readiness)
 *
 * Adheres to structured error envelope parsing per Section 13 of docs/implementation-contract.md.
 */

import type {
  CreateSessionPayload,
  SessionDetail,
  SessionResponse,
  SessionSummary,
  UpdateSessionPayload,
} from "../types/session";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  code: string;
  status: number;
  details?: Record<string, unknown>;

  constructor(message: string, status: number, code: string = "API_ERROR", details?: Record<string, unknown>) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorCode = `HTTP_${res.status}`;
    let errorMessage = `Request failed with status ${res.status}`;
    let details: Record<string, unknown> | undefined;

    try {
      const data = await res.json();
      if (data?.error) {
        errorCode = data.error.code || errorCode;
        errorMessage = data.error.message || errorMessage;
        details = data.error.details;
      }
    } catch {
      // Body not JSON
    }

    throw new ApiError(errorMessage, res.status, errorCode, details);
  }

  return res.json() as Promise<T>;
}

/**
 * Creates a new conversation session for an anonymous user.
 */
export async function createSession(
  anonymousIdentifier: string,
  title?: string
): Promise<SessionResponse> {
  const payload: CreateSessionPayload = {
    anonymous_identifier: anonymousIdentifier,
    title: title || "New Conversation",
  };

  const res = await fetch(`${API_BASE}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  return handleResponse<SessionResponse>(res);
}

/**
 * Lists sessions belonging to the given anonymous user identifier.
 */
export async function listSessions(
  anonymousIdentifier: string,
  limit: number = 50,
  offset: number = 0
): Promise<SessionSummary[]> {
  const url = `${API_BASE}/api/sessions?anonymous_identifier=${encodeURIComponent(
    anonymousIdentifier
  )}&limit=${limit}&offset=${offset}`;

  const res = await fetch(url, {
    method: "GET",
    headers: { Accept: "application/json" },
  });

  return handleResponse<SessionSummary[]>(res);
}

/**
 * Retrieves full conversation history, citations, and artifacts for a session.
 */
export async function getSession(sessionId: string): Promise<SessionDetail> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });

  return handleResponse<SessionDetail>(res);
}

/**
 * Updates an existing session's title.
 */
export async function updateSessionTitle(
  sessionId: string,
  title: string
): Promise<SessionSummary> {
  const payload: UpdateSessionPayload = { title };
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  return handleResponse<SessionSummary>(res);
}

/**
 * Deletes a session and its associated records.
 */
export async function deleteSession(
  sessionId: string
): Promise<{ status: string; session_id: string }> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    method: "DELETE",
    headers: { Accept: "application/json" },
  });

  return handleResponse<{ status: string; session_id: string }>(res);
}

/**
 * Health probe checking database, provider, and vector status.
 */
export async function getHealth(): Promise<{
  status: string;
  database: Record<string, unknown>;
  providers: Record<string, unknown>;
  corpus: Record<string, unknown>;
}> {
  const res = await fetch(`${API_BASE}/api/health`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });

  return handleResponse(res);
}

/**
 * Lenny Growth Assistant — Chat & Streaming Types
 *
 * Matches backend/app/schemas/chat.py and Section 10 of docs/implementation-contract.md.
 */

import { Citation } from "./citation";
import { Artifact } from "./session";

export type ChatMode = "default" | "ship30" | "artifact";
export type ChatProvider = "openai" | "ollama";

export interface ChatRequestPayload {
  session_id: string;
  message: string;
  provider: ChatProvider;
  model?: string;
  mode?: ChatMode;
  mock_mode?: boolean;
}

export type StreamStage = "retrieving" | "generating" | "persisting";

export interface SSEStatusData {
  stage: StreamStage;
  message: string;
}

export interface SSECitationData {
  citations: Citation[];
}

export interface SSETokenData {
  delta: string;
}

export interface SSEDoneData {
  message_id: string;
  provider: string;
  model: string;
  tokens?: {
    prompt?: number;
    completion?: number;
  };
  cost_usd?: number;
}

export interface SSEErrorData {
  error?: string;
  message?: string;
  code?: string;
  details?: Record<string, unknown>;
}

export type StreamStatus =
  | "idle"
  | "connecting"
  | "retrieving"
  | "generating"
  | "streaming"
  | "completed"
  | "error";

/**
 * Lenny Growth Assistant — Session & Persistence Types
 *
 * Matches backend/app/schemas/session.py and Section 11 of docs/implementation-contract.md.
 */

import { Citation } from "./citation";

export type MessageRole = "user" | "assistant" | "system";

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  provider?: string | null;
  model?: string | null;
  tokens_prompt?: number | null;
  tokens_completion?: number | null;
  cost_usd?: number;
  citations?: Citation[];
  created_at: string;
}

export interface Artifact {
  id: string;
  type: "markdown" | "html";
  title: string;
  content: string;
  created_at: string;
}

export interface SessionSummary {
  id: string;
  title: string;
  updated_at: string;
}

export interface SessionResponse {
  id: string;
  title: string;
  anonymous_identifier: string;
  created_at: string;
  updated_at: string;
}

export interface SessionDetail {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: Message[];
  artifacts: Artifact[];
}

export interface CreateSessionPayload {
  title?: string;
  anonymous_identifier: string;
}

export interface UpdateSessionPayload {
  title: string;
}

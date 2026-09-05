/**
 * Lenny Growth Assistant — Agent Runtime Type Definitions
 *
 * Defines strongly typed contracts for skills, tools, providers, citations,
 * and normalized Server-Sent Event (SSE) stream payloads matching Section 10
 * of docs/implementation-contract.md.
 */

export type AgentSkill = "grounded_qa" | "ship30_writer" | "artifact_generator";

export type LLMProviderType = "openai" | "ollama";

export interface EvidenceChunk {
  chunk_id: string;
  episode_title: string;
  guest_name: string;
  content: string;
  timestamp?: string;
  source_url?: string;
  similarity: number;
}

export interface Citation {
  chunk_id: string;
  episode_title: string;
  guest_name: string;
  timestamp?: string;
  source_url?: string;
  similarity: number;
  excerpt?: string;
}

export interface ArtifactPayload {
  id: string;
  type: "markdown" | "html";
  title: string;
  content: string;
  metadata?: Record<string, unknown>;
}

export interface TokenUsage {
  prompt: number;
  completion: number;
  total: number;
}

export interface AgentExecutionMetadata {
  provider: LLMProviderType;
  model: string;
  tokens: TokenUsage;
  cost_usd: number;
  finish_reason?: string;
}

export interface AgentRequest {
  skill: AgentSkill;
  query: string;
  evidence: EvidenceChunk[];
  conversation_history?: Array<{ role: "user" | "assistant" | "system"; content: string }>;
  provider: LLMProviderType;
  model?: string;
  mock_mode?: boolean;
}

export interface AgentResponse {
  content: string;
  citations: Citation[];
  artifact?: ArtifactPayload;
  metadata: AgentExecutionMetadata;
}

/**
 * Normalized Server-Sent Events (SSE) stream event types emitted to FastAPI.
 */
export type StreamEventType =
  | "status"
  | "token"
  | "citation"
  | "artifact"
  | "done"
  | "error";

export interface StreamEvent<T = unknown> {
  event: StreamEventType;
  data: T;
}

export interface StatusEventData {
  stage: "retrieving" | "generating" | "synthesizing" | "formatting";
  message: string;
}

export interface TokenEventData {
  delta: string;
}

export interface CitationEventData {
  citations: Citation[];
}

export interface ArtifactEventData {
  id: string;
  type: "markdown" | "html";
  title: string;
  content: string;
}

export interface DoneEventData {
  message_id?: string;
  provider: LLMProviderType;
  model: string;
  tokens: TokenUsage;
  cost_usd: number;
}

export interface ErrorEventData {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

/**
 * Safe Tool Interface — allowlisted application tools only.
 */
export interface ToolParameterSchema {
  type: string;
  description?: string;
  properties?: Record<string, unknown>;
  required?: string[];
}

export interface ToolDefinition {
  name: string;
  description: string;
  parameters: ToolParameterSchema;
  execute: (args: Record<string, unknown>) => Promise<unknown>;
}

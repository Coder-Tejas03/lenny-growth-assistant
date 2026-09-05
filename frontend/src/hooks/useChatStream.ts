/**
 * Lenny Growth Assistant — SSE Chat Streaming Hook
 *
 * Coordinates real-time response generation with FastAPI:
 * - Submits POST /api/chat with ChatRequest payload
 * - Consumes W3C Server-Sent Events stream using parseSSEStream
 * - Tracks progressive stages: retrieving -> generating -> streaming -> completed
 * - Accumulates token-by-token content and transcript citations
 * - Handles graceful aborts and structured error events
 */

import { useCallback, useRef, useState } from "react";
import { parseSSEStream } from "../lib/sse-parser";
import {
  ChatMode,
  ChatProvider,
  ChatRequestPayload,
  SSEErrorData,
  StreamStage,
  StreamStatus,
} from "../types/chat";
import { Citation } from "../types/citation";
import { Artifact, Message } from "../types/session";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface UseChatStreamProps {
  sessionId: string | null;
  onMessageCompleted?: (message: Message) => void;
  onArtifactCreated?: (artifact: Artifact) => void;
}

export function useChatStream({
  sessionId,
  onMessageCompleted,
  onArtifactCreated,
}: UseChatStreamProps) {
  const [status, setStatus] = useState<StreamStatus>("idle");
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [streamingContent, setStreamingContent] = useState<string>("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [errorInfo, setErrorInfo] = useState<SSEErrorData | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  // Accumulated message metadata from the 'done' event
  const doneMetaRef = useRef<{
    message_id?: string;
    provider?: string;
    model?: string;
    cost_usd?: number;
    tokens?: { prompt?: number; completion?: number };
  }>({});

  const abortStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setStatus("idle");
    setStatusMessage("");
  }, []);

  const sendMessage = useCallback(
    async (
      userQuery: string,
      options: {
        provider?: ChatProvider;
        model?: string;
        mode?: ChatMode;
        mock_mode?: boolean;
        sessionId?: string;
      } = {}
    ) => {
      const effectiveSessionId = options.sessionId || sessionId;
      if (!effectiveSessionId) {
        setError("No active session selected.");
        return;
      }

      // Abort any ongoing stream
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      const controller = new AbortController();
      abortControllerRef.current = controller;

      // Reset state
      setStatus("connecting");
      setStatusMessage("Connecting to Lenny Assistant...");
      setStreamingContent("");
      setCitations([]);
      setError(null);
      setErrorInfo(null);
      doneMetaRef.current = {};

      const payload: ChatRequestPayload = {
        session_id: effectiveSessionId,
        message: userQuery,
        provider: options.provider || "openai",
        model: options.model,
        mode: options.mode || "default",
        mock_mode: options.mock_mode || false,
      };

      let liveContent = "";
      let liveCitations: Citation[] = [];

      try {
        const res = await fetch(`${API_BASE}/api/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
          },
          body: JSON.stringify(payload),
          signal: controller.signal,
        });

        if (!res.ok) {
          let errorText = `Request failed with status ${res.status}`;
          try {
            const errJson = await res.json();
            if (errJson?.error?.message) {
              errorText = errJson.error.message;
            }
          } catch {
            // body is not JSON
          }
          throw new Error(errorText);
        }

        if (!res.body) {
          throw new Error("Response body is not a readable stream.");
        }

        const reader = res.body.getReader();

        await parseSSEStream(
          reader,
          {
            onStatus: (data) => {
              if (data.stage === "retrieving") {
                setStatus("retrieving");
                setStatusMessage(data.message || "Searching transcript archive...");
              } else if (data.stage === "generating") {
                setStatus("generating");
                setStatusMessage(data.message || "Drafting grounded response...");
              } else if (data.stage === "persisting") {
                setStatusMessage(data.message || "Finalizing response...");
              }
            },
            onCitation: (data) => {
              if (data.citations && Array.isArray(data.citations)) {
                liveCitations = data.citations;
                setCitations(data.citations);
              }
            },
            onToken: (data) => {
              liveContent += data.delta;
              setStreamingContent(liveContent);
              setStatus("streaming");
            },
            onArtifact: (artifact) => {
              onArtifactCreated?.(artifact);
            },
            onDone: (doneData) => {
              doneMetaRef.current = {
                message_id: doneData.message_id,
                provider: doneData.provider,
                model: doneData.model,
                cost_usd: doneData.cost_usd,
                tokens: doneData.tokens,
              };
            },
            onError: (errData) => {
              const msg =
                errData.message ||
                errData.error ||
                (typeof errData === "string" ? errData : "An error occurred.");
              setError(msg);
              setErrorInfo(errData);
              setStatus("error");
            },
            onTerminalDone: () => {
              setStatus("completed");
              setStatusMessage("");

              // Build completed assistant message
              const completedMessage: Message = {
                id: doneMetaRef.current.message_id || ("msg_" + crypto.randomUUID()),
                role: "assistant",
                content: liveContent,
                provider: doneMetaRef.current.provider || payload.provider,
                model: doneMetaRef.current.model || payload.model || "default",
                citations: liveCitations,
                tokens_prompt: doneMetaRef.current.tokens?.prompt,
                tokens_completion: doneMetaRef.current.tokens?.completion,
                cost_usd: doneMetaRef.current.cost_usd || 0,
                created_at: new Date().toISOString(),
              };

              onMessageCompleted?.(completedMessage);
            },
          },
          controller.signal
        );
      } catch (err: any) {
        if (err.name === "AbortError") {
          setStatus("idle");
          setStatusMessage("");
        } else {
          setError(err.message || "An unexpected streaming error occurred.");
          setStatus("error");
        }
      } finally {
        abortControllerRef.current = null;
      }
    },
    [sessionId, onArtifactCreated, onMessageCompleted]
  );

  return {
    status,
    statusMessage,
    streamingContent,
    citations,
    error,
    errorInfo,
    isStreaming: status === "retrieving" || status === "generating" || status === "streaming",
    sendMessage,
    abortStream,
  };
}

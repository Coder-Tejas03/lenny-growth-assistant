/**
 * Lenny Growth Assistant — Chat Pane Component
 *
 * Editorial Signal Desk Conversation Canvas:
 * - Centered reading column (680–760px)
 * - Smart auto-scroll that respects manual reading
 * - Compact editorial empty state with curated inquiries
 * - Real-time streaming turn with discrete progress indicator
 * - Resilient error handling with manual provider fallback
 * - Embedded Query Desk Composer
 */

"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { Sparkles, AlertCircle, Loader2, Cpu, Cloud, FileText } from "lucide-react";
import { Artifact, Message } from "../../types/session";
import { ChatMode, ChatProvider, SSEErrorData, StreamStatus } from "../../types/chat";
import { Citation } from "../../types/citation";
import { MessageItem } from "./MessageItem";
import { Composer } from "./Composer";
import { CitationCard } from "./CitationCard";
import { EmptyState } from "../Common/EmptyState";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ChatPaneProps {
  messages: Message[];
  streamingContent: string;
  streamingStatus: StreamStatus;
  streamingStatusMessage: string;
  citations: Citation[];
  error: string | null;
  errorInfo?: SSEErrorData | null;
  activeProvider: ChatProvider;
  activeModel?: string;
  onSendMessage: (query: string, mode: ChatMode, suggestedTitle?: string) => void;
  onAbortStream: () => void;
  onSelectModel?: (provider: ChatProvider, model: string) => void;
  isLoadingHistory?: boolean;
  artifacts?: Artifact[];
  onViewArtifact?: (artifact: Artifact) => void;
  activeArtifactId?: string | null;
}

export function ChatPane({
  messages,
  streamingContent,
  streamingStatus,
  streamingStatusMessage,
  citations,
  error,
  errorInfo,
  activeProvider,
  activeModel,
  onSendMessage,
  onAbortStream,
  onSelectModel,
  isLoadingHistory = false,
  artifacts = [],
  onViewArtifact,
  activeArtifactId,
}: ChatPaneProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [userScrolledUp, setUserScrolledUp] = useState(false);

  const isStreaming =
    streamingStatus === "connecting" ||
    streamingStatus === "retrieving" ||
    streamingStatus === "generating" ||
    streamingStatus === "streaming";

  // Check scroll position so auto-scroll does not interrupt manual reading
  const handleScroll = useCallback(() => {
    if (!scrollContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    const distanceToBottom = scrollHeight - scrollTop - clientHeight;
    setUserScrolledUp(distanceToBottom > 140);
  }, []);

  // Smart auto-scroll: only scrolls to bottom if user has not scrolled up
  useEffect(() => {
    if (!userScrolledUp && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "auto" });
    }
  }, [messages, streamingContent, streamingStatus, userScrolledUp]);

  // Reset user scroll state when a new query is submitted
  const handleSend = (query: string, mode: ChatMode, suggestedTitle?: string) => {
    setUserScrolledUp(false);
    onSendMessage(query, mode, suggestedTitle);
  };

  return (
    <main
      aria-label="Conversation Workspace"
      className="flex-1 flex flex-col h-full overflow-hidden bg-canvas relative select-text"
    >
      {/* 1. Scrollable Message Timeline */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-4 py-6 space-y-4"
      >
        {isLoadingHistory ? (
          <div className="flex items-center justify-center h-48 text-content-muted gap-2 text-xs">
            <Loader2 className="w-4 h-4 animate-spin text-signal" />
            <span>Loading conversation archive...</span>
          </div>
        ) : messages.length === 0 && !isStreaming ? (
          /* Empty State */
          <EmptyState onSelectPrompt={handleSend} />
        ) : (
          /* Rendered Conversation Timeline */
          <div className="max-w-[740px] mx-auto space-y-5">
            {/* Session Deliverables Banner */}
            {artifacts.length > 0 && (
              <div className="flex items-center justify-between px-3.5 py-2.5 rounded-xl bg-surface border border-artifact/40 text-xs text-content shadow-xs animate-fade-in">
                <div className="flex items-center gap-2 min-w-0">
                  <Sparkles className="w-4 h-4 text-artifact shrink-0" />
                  <span className="truncate">
                    This research session generated <strong>{artifacts.length}</strong> deliverable{artifacts.length > 1 ? "s" : ""}.
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => onViewArtifact?.(artifacts[artifacts.length - 1])}
                  className="px-2.5 py-1 rounded-lg bg-artifact hover:opacity-90 text-white text-[11px] font-semibold transition-opacity shrink-0 shadow-xs ml-2"
                >
                  Open Deliverable
                </button>
              </div>
            )}

            {/* Historical Messages */}
            {messages.map((msg, idx) => {
              const isLastAssistant =
                msg.role === "assistant" &&
                (idx === messages.length - 1 ||
                  (idx === messages.length - 2 &&
                    messages[messages.length - 1].role === "user"));
              const matchedArtifact =
                isLastAssistant && artifacts.length > 0
                  ? artifacts[artifacts.length - 1]
                  : undefined;

              return (
                <MessageItem
                  key={msg.id}
                  message={msg}
                  artifact={matchedArtifact}
                  onViewArtifact={onViewArtifact}
                />
              );
            })}

            {/* Live Streaming Assistant Turn */}
            {isStreaming && (
              <div className="flex items-start gap-3.5 py-3 w-full animate-fade-in">
                <div className="w-7 h-7 rounded-lg bg-surface-raised border border-border-strong flex items-center justify-center shrink-0 text-signal font-serif font-bold text-xs shadow-xs mt-0.5">
                  L
                </div>

                <div className="flex-1 space-y-3 min-w-0">
                  {/* Status Indicator */}
                  {(streamingStatus === "retrieving" ||
                    streamingStatus === "generating" ||
                    streamingStatus === "connecting") && (
                    <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md bg-surface-raised border border-border text-[11px] font-mono text-content-muted">
                      <span className="w-1.5 h-1.5 rounded-full bg-signal animate-pulse" />
                      <span>{streamingStatusMessage || (streamingStatus === "retrieving" ? "Retrieving transcript evidence..." : "Drafting grounded response...")}</span>
                    </div>
                  )}

                  {/* Progressive Token Stream */}
                  {streamingContent && (
                    <div className="prose-editorial text-xs sm:text-sm break-words leading-relaxed">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {streamingContent}
                      </ReactMarkdown>
                    </div>
                  )}

                  {/* Discovered Citations During Stream */}
                  {citations.length > 0 && (
                    <div className="pt-2 border-t border-border space-y-2">
                      <div className="text-[10px] font-mono uppercase tracking-wider text-content-subtle">
                        Discovered Sources ({citations.length})
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {citations.map((cit, idx) => (
                          <CitationCard
                            key={cit.chunk_id || `live-cit-${idx}`}
                            citation={cit}
                            index={idx}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Error Banner with Manual Fallback Controls */}
            {error && (
              <div
                className={`p-4 rounded-xl border text-xs shadow-xs animate-fade-in ${
                  errorInfo?.code === "BUDGET_EXCEEDED" || error.toLowerCase().includes("budget")
                    ? "bg-amber-950/20 border-amber-600/40 text-amber-900 dark:text-amber-200"
                    : "bg-danger/10 border-danger/30 text-danger"
                }`}
              >
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <div className="space-y-1.5 flex-1">
                    <div className="font-semibold">
                      {errorInfo?.code === "BUDGET_EXCEEDED"
                        ? "API Budget Ceiling Reached ($4.00)"
                        : errorInfo?.code === "PROVIDER_UNAVAILABLE"
                        ? "Model Provider Unavailable"
                        : "Request Error"}
                    </div>
                    <div className="text-[11px] leading-relaxed opacity-90">
                      {error}
                    </div>

                    {/* Manual Fallback Action Buttons */}
                    {(errorInfo?.code === "BUDGET_EXCEEDED" ||
                      errorInfo?.code === "PROVIDER_UNAVAILABLE" ||
                      error.toLowerCase().includes("budget") ||
                      error.toLowerCase().includes("available")) && (
                      <div className="pt-2">
                        {activeProvider === "openai" ? (
                          <button
                            type="button"
                            onClick={() => onSelectModel?.("ollama", "qwen2.5:1.5b")}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-raised border border-border text-content text-xs font-semibold hover:bg-surface-hover transition-all shadow-xs"
                          >
                            <Cpu className="w-3.5 h-3.5 text-signal" />
                            <span>Switch to Local Ollama (qwen2.5:1.5b)</span>
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={() => onSelectModel?.("openai", "gpt-4o-mini")}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-raised border border-border text-content text-xs font-semibold hover:bg-surface-hover transition-all shadow-xs"
                          >
                            <Cloud className="w-3.5 h-3.5 text-evidence" />
                            <span>Switch to Cloud OpenAI (gpt-4o-mini)</span>
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* 2. Query Desk Composer */}
      <Composer
        onSendMessage={handleSend}
        onAbortStream={onAbortStream}
        isStreaming={isStreaming}
      />
    </main>
  );
}

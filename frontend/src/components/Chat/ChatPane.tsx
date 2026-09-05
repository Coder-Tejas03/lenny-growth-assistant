/**
 * Lenny Growth Assistant — Chat Pane Component
 *
 * Integrates:
 * - Conversation timeline with auto-scrolling
 * - Empty state with curated starter questions
 * - Live streaming assistant turn with transient status indicators
 * - Error alerts
 * - Embedded Composer
 */

"use client";

import React, { useEffect, useRef } from "react";
import { Sparkles, Compass, AlertCircle, Loader2, Cpu, Cloud } from "lucide-react";
import { Artifact, Message } from "../../types/session";
import { ChatMode, ChatProvider, SSEErrorData, StreamStatus } from "../../types/chat";
import { Citation } from "../../types/citation";
import { MessageItem } from "./MessageItem";
import { Composer } from "./Composer";
import { CitationCard } from "./CitationCard";
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
  onSendMessage: (query: string, mode: ChatMode) => void;
  onAbortStream: () => void;
  onSelectModel?: (provider: ChatProvider, model: string) => void;
  isLoadingHistory?: boolean;
  artifacts?: Artifact[];
  onViewArtifact?: (artifact: Artifact) => void;
  activeArtifactId?: string | null;
}

const STARTER_PROMPTS = [
  {
    title: "🚀 Am I Building the Right Thing?",
    prompt: "How do I know if my startup has genuine product-market fit? What signals should I look for?",
  },
  {
    title: "📈 How Do Great Products Grow?",
    prompt: "What are growth loops and how are they different from traditional marketing funnels?",
  },
  {
    title: "🔁 Why Do Users Leave?",
    prompt: "What are the most important retention metrics for a B2B SaaS product and how do I improve them?",
  },
  {
    title: "🧪 Running Experiments",
    prompt: "How should an early-stage startup think about running growth experiments and measuring success?",
  },
];

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
  const bottomRef = useRef<HTMLDivElement>(null);
  const isStreaming =
    streamingStatus === "connecting" ||
    streamingStatus === "retrieving" ||
    streamingStatus === "generating" ||
    streamingStatus === "streaming";

  // Auto-scroll to bottom on new messages or streaming tokens
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent, streamingStatus]);

  return (
    <main
      aria-label="Conversation Workspace"
      className="flex-1 flex flex-col h-full overflow-hidden bg-surface-950 relative"
    >
      {/* 1. Scrollable Message Timeline */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {isLoadingHistory ? (
          <div className="flex items-center justify-center h-48 text-slate-400 gap-2 text-xs">
            <Loader2 className="w-4 h-4 animate-spin text-brand-400" />
            <span>Loading conversation history...</span>
          </div>
        ) : messages.length === 0 && !isStreaming ? (
          /* Empty State */
          <div className="max-w-2xl mx-auto py-12 px-4 text-center space-y-6">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-brand-600 to-brand-400 mx-auto flex items-center justify-center shadow-xl shadow-brand-500/20">
              <Sparkles className="w-6 h-6 text-white" />
            </div>

            <div className="space-y-2">
              <h2 className="text-lg font-bold text-white tracking-tight">
                Ask Lenny&apos;s Podcast Archive
              </h2>
              <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
                Answers are grounded strictly in retrieved podcast transcripts with verified
                citations back to guests and timestamps.
              </p>
            </div>

            <div className="space-y-2 pt-2">
              <div className="flex items-center justify-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                <Compass className="w-3.5 h-3.5 text-brand-400" />
                <span>Suggested Questions</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
                {STARTER_PROMPTS.map((starter) => (
                  <button
                    key={starter.title}
                    type="button"
                    onClick={() => onSendMessage(starter.prompt, "default")}
                    className="p-3 rounded-xl bg-surface-900/60 hover:bg-surface-800/80 border border-surface-700 hover:border-brand-500/50 transition-all text-left group"
                  >
                    <div className="text-xs font-semibold text-slate-200 group-hover:text-brand-300 transition-colors">
                      {starter.title}
                    </div>
                    <div className="text-[11px] text-slate-400 mt-1 leading-snug line-clamp-2">
                      {starter.prompt}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          /* Rendered Message List */
          <div className="max-w-3xl mx-auto space-y-4">
            {/* Session Artifacts Notification Banner */}
            {artifacts.length > 0 && (
              <div className="flex items-center justify-between px-3.5 py-2.5 rounded-xl bg-gradient-to-r from-brand-950/70 to-surface-900 border border-brand-500/40 text-xs text-brand-200 shadow-md">
                <div className="flex items-center gap-2 min-w-0">
                  <Sparkles className="w-4 h-4 text-brand-400 shrink-0" />
                  <span className="truncate">
                    This conversation includes <strong>{artifacts.length}</strong> safe deliverable{artifacts.length > 1 ? "s" : ""}.
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => onViewArtifact?.(artifacts[artifacts.length - 1])}
                  className="px-2.5 py-1 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-[11px] font-semibold transition-colors shrink-0 shadow-sm ml-2"
                >
                  Open Deliverable
                </button>
              </div>
            )}
            {messages.map((msg, idx) => {
              // Connect artifact to the latest assistant message or matching index
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

            {/* Live Streaming Turn */}
            {isStreaming && (
              <div className="flex items-start gap-3 py-3 w-full animate-fade-in">
                <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-brand-700 to-brand-500 flex items-center justify-center shrink-0 text-white shadow-md shadow-brand-500/20 mt-1">
                  <Sparkles className="w-3.5 h-3.5 animate-pulse" />
                </div>

                <div className="flex-1 space-y-3">
                  {/* Status pill during retrieval / generation */}
                  {(streamingStatus === "retrieving" ||
                    streamingStatus === "generating" ||
                    streamingStatus === "connecting") && (
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-900 border border-brand-500/40 text-xs text-brand-300 animate-pulse">
                      <Loader2 className="w-3 h-3 animate-spin text-brand-400" />
                      <span>{streamingStatusMessage || "Retrieving transcript evidence..."}</span>
                    </div>
                  )}

                  {/* Token content accumulation */}
                  {streamingContent && (
                    <div className="prose-custom text-xs break-words">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {streamingContent}
                      </ReactMarkdown>
                    </div>
                  )}

                  {/* Real-time citations discovered */}
                  {citations.length > 0 && (
                    <div className="pt-2 border-t border-surface-800/80 space-y-2">
                      <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
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

            {/* Error Banner with Proactive Manual Fallback */}
            {error && (
              <div
                className={`p-4 rounded-xl border text-xs shadow-lg animate-fade-in ${
                  errorInfo?.code === "BUDGET_EXCEEDED" || error.toLowerCase().includes("budget")
                    ? "bg-amber-950/40 border-amber-800/80 text-amber-200"
                    : "bg-red-950/50 border-red-800/80 text-red-200"
                }`}
              >
                <div className="flex items-start gap-3">
                  <AlertCircle
                    className={`w-4 h-4 shrink-0 mt-0.5 ${
                      errorInfo?.code === "BUDGET_EXCEEDED" || error.toLowerCase().includes("budget")
                        ? "text-amber-400"
                        : "text-red-400"
                    }`}
                  />
                  <div className="space-y-1.5 flex-1">
                    <div
                      className={`font-semibold ${
                        errorInfo?.code === "BUDGET_EXCEEDED" || error.toLowerCase().includes("budget")
                          ? "text-amber-300"
                          : "text-red-300"
                      }`}
                    >
                      {errorInfo?.code === "BUDGET_EXCEEDED"
                        ? "API Budget Ceiling Reached ($4.00)"
                        : errorInfo?.code === "PROVIDER_UNAVAILABLE"
                        ? "Model Provider Unavailable"
                        : "Request Error"}
                    </div>
                    <div className="text-[11px] leading-relaxed opacity-90">
                      {error}
                    </div>

                    {/* Manual Fallback Action Button */}
                    {(errorInfo?.code === "BUDGET_EXCEEDED" ||
                      errorInfo?.code === "PROVIDER_UNAVAILABLE" ||
                      error.toLowerCase().includes("budget") ||
                      error.toLowerCase().includes("available")) && (
                      <div className="pt-2">
                        {activeProvider === "openai" ? (
                          <button
                            type="button"
                            onClick={() => onSelectModel?.("ollama", "qwen2.5:1.5b")}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-purple-900/80 hover:bg-purple-800 text-purple-200 border border-purple-700/80 text-xs font-semibold transition-all shadow-sm group"
                          >
                            <Cpu className="w-3.5 h-3.5 text-purple-400" />
                            <span>Switch to Local Ollama (qwen2.5:1.5b)</span>
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={() => onSelectModel?.("openai", "gpt-4o-mini")}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-900/80 hover:bg-emerald-800 text-emerald-200 border border-emerald-700/80 text-xs font-semibold transition-all shadow-sm group"
                          >
                            <Cloud className="w-3.5 h-3.5 text-emerald-400" />
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

      {/* 2. Chat Composer */}
      <Composer
        onSendMessage={onSendMessage}
        onAbortStream={onAbortStream}
        isStreaming={isStreaming}
      />
    </main>
  );
}

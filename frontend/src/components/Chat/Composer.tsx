/**
 * Lenny Growth Assistant — Chat Composer Component
 *
 * Editorial Query Desk:
 * - Multiline auto-expanding textarea
 * - Enter to send / Shift+Enter for newline
 * - Segmented mode selector rail (Grounded Q&A, Ship 30 Essay, Artifact)
 * - Restrained tactile send button / Stop action during generation
 * - Mobile safe-area padding
 */

"use client";

import React, { useRef, useState, useEffect } from "react";
import { ArrowUp, Square, BookOpen, Code2, MessageSquare } from "lucide-react";
import { ChatMode } from "../../types/chat";

interface ComposerProps {
  onSendMessage: (query: string, mode: ChatMode) => void;
  onAbortStream: () => void;
  isStreaming: boolean;
  disabled?: boolean;
}

const CHAT_MODES: { mode: ChatMode; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { mode: "default", label: "Grounded Q&A", icon: MessageSquare },
  { mode: "ship30", label: "Ship 30 Essay", icon: BookOpen },
  { mode: "artifact", label: "Artifact", icon: Code2 },
];

export function Composer({
  onSendMessage,
  onAbortStream,
  isStreaming,
  disabled = false,
}: ComposerProps) {
  const [query, setQuery] = useState("");
  const [selectedMode, setSelectedMode] = useState<ChatMode>("default");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea based on input height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        220
      )}px`;
    }
  }, [query]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || isStreaming || disabled) return;

    onSendMessage(trimmed, selectedMode);
    setQuery("");

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-border bg-surface/90 backdrop-blur px-3 sm:px-4 pt-3 pb-3 sm:pb-4 shrink-0 select-none">
      <div className="max-w-[740px] mx-auto space-y-2">
        {/* Compact Segmented Mode Selector Rail */}
        <div className="flex items-center gap-2 overflow-x-auto pb-0.5">
          <div className="inline-flex items-center p-0.5 rounded-lg bg-surface-raised border border-border">
            {CHAT_MODES.map((item) => {
              const Icon = item.icon;
              const isSelected = selectedMode === item.mode;
              return (
                <button
                  key={item.mode}
                  type="button"
                  onClick={() => setSelectedMode(item.mode)}
                  disabled={isStreaming}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                    isSelected
                      ? "bg-surface text-content shadow-xs font-semibold border border-border"
                      : "text-content-muted hover:text-content border border-transparent"
                  } ${isStreaming ? "opacity-50 cursor-not-allowed" : "cursor-pointer"} focus-visible:outline focus-visible:outline-2 focus-visible:outline-signal`}
                >
                  <Icon className={`w-3 h-3 ${isSelected ? "text-signal" : "text-content-subtle"}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Input Box Form */}
        <form
          onSubmit={handleSubmit}
          className="relative rounded-xl bg-surface-raised border border-border focus-within:border-signal focus-within:ring-1 focus-within:ring-signal/30 shadow-xs transition-all"
        >
          <textarea
            ref={textareaRef}
            rows={1}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={
              selectedMode === "ship30"
                ? "What topic should I turn into a Ship 30 for 30 essay?"
                : selectedMode === "artifact"
                ? "Request a component, checklist, or guide deliverable..."
                : "Ask a product or growth question from Lenny's transcripts..."
            }
            className="w-full resize-none bg-transparent px-3.5 pt-3 pb-10 text-xs sm:text-sm text-content placeholder-content-subtle outline-none leading-relaxed select-text"
          />

          <div className="absolute right-2.5 bottom-2 flex items-center gap-2">
            <span className="hidden sm:inline-block text-[10px] text-content-subtle font-mono">
              Enter ↵ to send · Shift+Enter newline
            </span>

            {isStreaming ? (
              <button
                type="button"
                onClick={onAbortStream}
                aria-label="Stop generating response"
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-danger/10 hover:bg-danger/20 border border-danger/30 text-danger text-xs font-medium shadow-xs transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-danger"
              >
                <Square className="w-2.5 h-2.5 fill-current" />
                <span className="text-[11px] font-mono">Stop</span>
              </button>
            ) : (
              <button
                type="submit"
                disabled={!query.trim() || disabled}
                aria-label="Send message"
                className="w-7 h-7 rounded-lg bg-signal hover:opacity-90 disabled:opacity-30 disabled:hover:opacity-30 text-white flex items-center justify-center shadow-xs transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-signal"
              >
                <ArrowUp className="w-4 h-4" />
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}

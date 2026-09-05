/**
 * Lenny Growth Assistant — Chat Composer Component
 *
 * Provides:
 * - Multiline auto-expanding prompt input
 * - Enter to submit / Shift+Enter for new line
 * - Skill / Mode selector (Default Q&A, Ship 30 Essay, Artifact Generator)
 * - Stop / Cancel button when streaming
 * - Accessibility keyboard controls
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

  // Auto-resize textarea based on input
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        200
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
    <div className="border-t border-surface-700 bg-surface-950/80 backdrop-blur-md p-3 sm:p-4">
      <div className="max-w-3xl mx-auto space-y-2">
        {/* Mode Selector Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
          {CHAT_MODES.map((item) => {
            const Icon = item.icon;
            const isSelected = selectedMode === item.mode;
            return (
              <button
                key={item.mode}
                type="button"
                onClick={() => setSelectedMode(item.mode)}
                disabled={isStreaming}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all ${
                  isSelected
                    ? "bg-brand-600/30 text-brand-300 border border-brand-500/50"
                    : "text-slate-400 hover:text-slate-200 hover:bg-surface-800/60 border border-transparent"
                } ${isStreaming ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
              >
                <Icon className="w-3 h-3" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>

        {/* Input Box Form */}
        <form
          onSubmit={handleSubmit}
          className="relative rounded-xl bg-surface-900 border border-surface-700 focus-within:border-brand-500/60 shadow-lg transition-all"
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
                ? "Request a component or guide artifact..."
                : "Ask a product or growth question from Lenny's transcripts..."
            }
            className="w-full resize-none bg-transparent px-3.5 pt-3 pb-10 text-xs sm:text-sm text-slate-100 placeholder-slate-500 outline-none leading-relaxed"
          />

          <div className="absolute right-2.5 bottom-2.5 flex items-center gap-2">
            <span className="hidden sm:inline-block text-[10px] text-slate-500 font-mono">
              Enter ↵ to send
            </span>

            {isStreaming ? (
              <button
                type="button"
                onClick={onAbortStream}
                aria-label="Stop generating response"
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-red-950/80 hover:bg-red-900 border border-red-800 text-red-300 text-xs font-medium shadow transition-all"
              >
                <Square className="w-3 h-3 fill-current" />
                <span className="text-[11px]">Stop</span>
              </button>
            ) : (
              <button
                type="submit"
                disabled={!query.trim() || disabled}
                aria-label="Send message"
                className="w-7 h-7 rounded-lg bg-brand-600 hover:bg-brand-500 disabled:opacity-40 disabled:hover:bg-brand-600 text-white flex items-center justify-center shadow-md shadow-brand-600/30 transition-all"
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

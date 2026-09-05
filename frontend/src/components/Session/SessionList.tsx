/**
 * Lenny Growth Assistant — Session List Sidebar Component
 *
 * Provides:
 * - "+ New Chat" primary action
 * - Chronological conversation history list
 * - Active session selection
 * - Inline rename & delete delegation
 * - Anonymous user session ownership metadata
 */

"use client";

import React from "react";
import { Plus, User, AlertCircle, RefreshCw, MessageSquareDashed } from "lucide-react";
import { SessionSummary } from "../../types/session";
import { SessionItem } from "./SessionItem";

interface SessionListProps {
  sessions: SessionSummary[];
  activeSessionId: string | null;
  isLoading: boolean;
  error: string | null;
  anonymousId: string;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onRenameSession: (id: string, newTitle: string) => void;
  onDeleteSession: (id: string) => void;
  onRetry: () => void;
  className?: string;
}

export function SessionList({
  sessions,
  activeSessionId,
  isLoading,
  error,
  anonymousId,
  onSelectSession,
  onNewChat,
  onRenameSession,
  onDeleteSession,
  onRetry,
  className = "",
}: SessionListProps) {
  return (
    <aside
      aria-label="Conversation History"
      className={`w-64 bg-surface-950 border-r border-surface-700 flex flex-col h-full select-none ${className}`}
    >
      {/* 1. New Chat Header Action */}
      <div className="p-3 border-b border-surface-800">
        <button
          type="button"
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md shadow-brand-600/20 transition-all active:scale-[0.98]"
        >
          <Plus className="w-4 h-4" />
          <span>New Chat</span>
        </button>
      </div>

      {/* 2. Conversations Timeline */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        <div className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          Recent Conversations
        </div>

        {error && (
          <div className="p-2.5 rounded-lg bg-red-950/40 border border-red-800/50 text-xs text-red-300 flex flex-col gap-1.5">
            <div className="flex items-center gap-1.5 font-medium">
              <AlertCircle className="w-3.5 h-3.5 shrink-0 text-red-400" />
              <span>Failed to load</span>
            </div>
            <button
              type="button"
              onClick={onRetry}
              className="flex items-center gap-1 text-[11px] text-red-200 underline hover:text-white"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Retry</span>
            </button>
          </div>
        )}

        {isLoading && sessions.length === 0 ? (
          <div className="p-2 space-y-2">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="h-8 rounded-lg bg-surface-800/50 animate-pulse-subtle"
              />
            ))}
          </div>
        ) : sessions.length === 0 && !error ? (
          <div className="py-8 px-4 text-center text-slate-500 flex flex-col items-center gap-2">
            <MessageSquareDashed className="w-6 h-6 text-slate-600" />
            <p className="text-xs">No conversations yet.</p>
            <p className="text-[11px] text-slate-600">Start a new chat to begin.</p>
          </div>
        ) : (
          sessions.map((session) => (
            <SessionItem
              key={session.id}
              session={session}
              isActive={session.id === activeSessionId}
              onSelect={onSelectSession}
              onRename={onRenameSession}
              onDelete={onDeleteSession}
            />
          ))
        )}
      </div>

      {/* 3. Footer: Minimal Anonymous User Indicator */}
      <div className="p-3 border-t border-surface-800/80 bg-surface-950/90 text-slate-400 flex items-center justify-between">
        <div className="flex items-center gap-2 overflow-hidden">
          <div className="w-6 h-6 rounded-full bg-surface-800 flex items-center justify-center text-slate-300 shrink-0">
            <User className="w-3.5 h-3.5" />
          </div>
          <div className="overflow-hidden">
            <div className="text-[11px] font-medium text-slate-300 truncate">
              {anonymousId ? anonymousId.slice(0, 16) + "..." : "Guest User"}
            </div>
            <div className="text-[10px] text-slate-500">Persistent Local ID</div>
          </div>
        </div>
      </div>
    </aside>
  );
}

/**
 * Lenny Growth Assistant — Session List Sidebar Component
 *
 * Research Library Navigation:
 * - Refined "+ New Chat" primary research action
 * - Chronological conversation history list with robust truncation
 * - Accessible semantic active selection
 * - Inline rename & delete delegation
 * - Anonymous user session ownership footer
 */

"use client";

import React from "react";
import { Plus, User, AlertCircle, RefreshCw, BookOpen, X } from "lucide-react";
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
  onCloseMobile?: () => void;
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
  onCloseMobile,
}: SessionListProps) {
  return (
    <aside
      aria-label="Conversation History"
      className={`w-64 sm:w-72 bg-surface border-r border-border flex flex-col h-full select-none ${className}`}
    >
      {/* 1. Library Header & New Chat Action */}
      <div className="p-3 border-b border-border space-y-2">
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-content font-serif">
            <BookOpen className="w-3.5 h-3.5 text-signal" />
            <span>Library</span>
          </div>

          {onCloseMobile && (
            <button
              type="button"
              onClick={onCloseMobile}
              aria-label="Close conversation library"
              className="md:hidden p-1 rounded-md text-content-muted hover:text-content hover:bg-surface-hover transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        <button
          type="button"
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-surface-raised hover:bg-surface-hover hover:border-signal/40 border border-border text-content text-xs font-semibold shadow-xs transition-all active:scale-[0.99] focus-visible:outline focus-visible:outline-2 focus-visible:outline-signal cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5 text-signal" />
          <span>New Chat</span>
        </button>
      </div>

      {/* 2. Conversations Timeline */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        <div className="px-2 py-1.5 text-[11px] font-medium tracking-wide text-content-subtle">
          Recent Conversations
        </div>

        {error && (
          <div className="p-2.5 rounded-lg bg-danger/10 border border-danger/30 text-xs text-danger flex flex-col gap-1.5">
            <div className="flex items-center gap-1.5 font-medium">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>Failed to load conversations</span>
            </div>
            <button
              type="button"
              onClick={onRetry}
              className="flex items-center gap-1 text-[11px] underline hover:opacity-80 font-medium"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Retry</span>
            </button>
          </div>
        )}

        {isLoading && sessions.length === 0 ? (
          <div className="p-2 space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                className="h-8 rounded-lg bg-surface-hover animate-pulse-subtle"
              />
            ))}
          </div>
        ) : sessions.length === 0 && !error ? (
          <div className="py-10 px-4 text-center text-content-muted flex flex-col items-center gap-2">
            <BookOpen className="w-5 h-5 text-content-subtle" />
            <p className="text-xs font-medium text-content">No conversations yet</p>
            <p className="text-[11px] text-content-muted">Start a new chat to begin exploring.</p>
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

      {/* 3. Footer: Discreet Anonymous User Provenance */}
      <div className="p-3 border-t border-border bg-surface text-content-muted flex items-center justify-between">
        <div className="flex items-center gap-2 overflow-hidden">
          <div className="w-6 h-6 rounded-md bg-surface-raised border border-border flex items-center justify-center text-content-muted shrink-0">
            <User className="w-3.5 h-3.5" />
          </div>
          <div className="overflow-hidden">
            <div className="text-[11px] font-medium text-content truncate">
              {anonymousId ? anonymousId.slice(0, 16) + "..." : "Guest User"}
            </div>
            <div className="text-[10px] text-content-subtle font-mono">Persistent Local ID</div>
          </div>
        </div>
      </div>
    </aside>
  );
}

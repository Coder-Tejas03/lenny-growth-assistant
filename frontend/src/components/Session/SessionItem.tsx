/**
 * Lenny Growth Assistant — Session Item Component
 *
 * Renders an individual conversation thread in the session library:
 * - Semantic button interaction (no clickable divs)
 * - Subtle active indicator rail and surface shift (not color alone)
 * - Inline title editing with Enter/Esc keyboard support
 * - Accessible options menu with Rename and Delete actions
 */

"use client";

import React, { useState, useRef, useEffect } from "react";
import { MessageSquare, MoreVertical, Pencil, Trash2, Check, X } from "lucide-react";
import { SessionSummary } from "../../types/session";

interface SessionItemProps {
  session: SessionSummary;
  isActive: boolean;
  onSelect: (id: string) => void;
  onRename: (id: string, newTitle: string) => void;
  onDelete: (id: string) => void;
}

export function SessionItem({
  session,
  isActive,
  onSelect,
  onRename,
  onDelete,
}: SessionItemProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(session.title);
  const [showMenu, setShowMenu] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  // Close menu on click outside or escape key
  useEffect(() => {
    if (!showMenu) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setShowMenu(false);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [showMenu]);

  const handleSaveRename = (e?: React.FormEvent) => {
    e?.preventDefault();
    const trimmed = editTitle.trim();
    if (trimmed && trimmed !== session.title) {
      onRename(session.id, trimmed);
    } else {
      setEditTitle(session.title);
    }
    setIsEditing(false);
    setShowMenu(false);
  };

  const handleCancelRename = () => {
    setEditTitle(session.title);
    setIsEditing(false);
    setShowMenu(false);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete(session.id);
    setShowMenu(false);
  };

  if (isEditing) {
    return (
      <form
        onSubmit={handleSaveRename}
        className="flex items-center gap-1 p-1.5 rounded-lg bg-surface-raised border border-signal shadow-xs"
      >
        <input
          ref={inputRef}
          type="text"
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") handleCancelRename();
          }}
          className="flex-1 bg-transparent px-2 py-1 text-xs text-content outline-none"
        />
        <button
          type="submit"
          aria-label="Save title"
          className="p-1 text-signal hover:text-signal/80 rounded hover:bg-surface-hover"
        >
          <Check className="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          onClick={handleCancelRename}
          aria-label="Cancel editing"
          className="p-1 text-content-muted hover:text-content rounded hover:bg-surface-hover"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </form>
    );
  }

  return (
    <div
      className={`group relative flex items-center justify-between rounded-lg text-xs font-medium transition-all ${
        isActive
          ? "bg-surface-raised border-l-[3px] border-l-signal border-t border-r border-b border-border text-content font-semibold shadow-xs"
          : "text-content-muted hover:bg-surface-hover hover:text-content border border-transparent"
      }`}
    >
      <button
        type="button"
        onClick={() => onSelect(session.id)}
        aria-current={isActive ? "page" : undefined}
        className="flex-1 flex items-center gap-2.5 text-left py-2 px-2.5 min-w-0 focus-visible:outline focus-visible:outline-2 focus-visible:outline-signal rounded-l-lg"
      >
        <MessageSquare
          className={`w-3.5 h-3.5 shrink-0 transition-colors ${
            isActive ? "text-signal" : "text-content-subtle group-hover:text-content-muted"
          }`}
        />
        <span className="truncate leading-relaxed" title={session.title}>
          {session.title}
        </span>
      </button>

      <div className="relative pr-1.5 shrink-0" ref={menuRef}>
        <button
          type="button"
          aria-label={`Options for ${session.title}`}
          aria-expanded={showMenu}
          onClick={(e) => {
            e.stopPropagation();
            setShowMenu(!showMenu);
          }}
          className={`p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity text-content-muted hover:text-content hover:bg-surface-hover focus-visible:opacity-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-signal ${
            showMenu ? "opacity-100 bg-surface-hover" : ""
          }`}
        >
          <MoreVertical className="w-3.5 h-3.5" />
        </button>

        {showMenu && (
          <>
            <div
              className="fixed inset-0 z-20"
              onClick={(e) => {
                e.stopPropagation();
                setShowMenu(false);
              }}
              aria-hidden="true"
            />
            <div className="absolute right-0 mt-1 w-32 rounded-lg bg-surface-raised border border-border shadow-lg z-30 p-1 animate-slide-up">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setIsEditing(true);
                }}
                className="w-full flex items-center gap-2 px-2.5 py-1.5 text-left text-xs text-content hover:bg-surface-hover rounded"
              >
                <Pencil className="w-3 h-3 text-content-muted" />
                <span>Rename</span>
              </button>
              <button
                type="button"
                onClick={handleDelete}
                className="w-full flex items-center gap-2 px-2.5 py-1.5 text-left text-xs text-danger hover:bg-danger/10 rounded"
              >
                <Trash2 className="w-3 h-3 text-danger" />
                <span>Delete</span>
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

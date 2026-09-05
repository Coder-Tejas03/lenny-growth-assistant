/**
 * Lenny Growth Assistant — Session Item Component
 *
 * Renders an individual conversation thread in the sidebar:
 * - Active session visual distinction
 * - Inline title editing with Enter/Esc handling
 * - Delete action with confirmation
 * - Accessible keyboard navigation
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

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

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
        className="flex items-center gap-1 p-1.5 rounded-lg bg-surface-800 border border-brand-500/50"
      >
        <input
          ref={inputRef}
          type="text"
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") handleCancelRename();
          }}
          className="flex-1 bg-transparent px-2 py-1 text-xs text-white outline-none"
        />
        <button
          type="submit"
          aria-label="Save title"
          className="p-1 text-brand-400 hover:text-brand-300 rounded hover:bg-surface-700"
        >
          <Check className="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          onClick={handleCancelRename}
          aria-label="Cancel editing"
          className="p-1 text-slate-400 hover:text-slate-300 rounded hover:bg-surface-700"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </form>
    );
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect(session.id)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect(session.id);
        }
      }}
      className={`group relative flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all cursor-pointer ${
        isActive
          ? "bg-surface-800 border border-surface-600 text-white font-semibold shadow-sm"
          : "text-slate-400 hover:bg-surface-900 hover:text-slate-200 border border-transparent"
      }`}
    >
      <div className="flex items-center gap-2.5 overflow-hidden">
        <MessageSquare
          className={`w-3.5 h-3.5 shrink-0 ${
            isActive ? "text-brand-400" : "text-slate-500 group-hover:text-slate-400"
          }`}
        />
        <span className="truncate" title={session.title}>
          {session.title}
        </span>
      </div>

      <div className="relative">
        <button
          type="button"
          aria-label="Session options"
          onClick={(e) => {
            e.stopPropagation();
            setShowMenu(!showMenu);
          }}
          className={`p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity text-slate-400 hover:text-white hover:bg-surface-700 ${
            showMenu ? "opacity-100" : ""
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
            <div className="absolute right-0 mt-1 w-32 rounded-lg bg-surface-900 border border-surface-700 shadow-xl z-30 p-1">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setIsEditing(true);
                }}
                className="w-full flex items-center gap-2 px-2 py-1.5 text-left text-xs text-slate-300 hover:text-white hover:bg-surface-800 rounded"
              >
                <Pencil className="w-3 h-3" />
                <span>Rename</span>
              </button>
              <button
                type="button"
                onClick={handleDelete}
                className="w-full flex items-center gap-2 px-2 py-1.5 text-left text-xs text-red-400 hover:text-red-300 hover:bg-red-950/40 rounded"
              >
                <Trash2 className="w-3 h-3" />
                <span>Delete</span>
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

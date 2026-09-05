/**
 * Lenny Growth Assistant — Message Item Component
 *
 * Renders individual conversational turns:
 * - User query bubble
 * - Assistant response with Markdown typography (ReactMarkdown + remarkGfm)
 * - Canonical abstention banner for insufficient evidence queries
 * - Provider & Model attribution provenance badge
 * - Collapsible citation cards section
 */

"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  User,
  Sparkles,
  Copy,
  Check,
  Cpu,
  Cloud,
  FileText,
  AlertTriangle,
} from "lucide-react";
import { Artifact, Message } from "../../types/session";
import { CitationCard } from "./CitationCard";

interface MessageItemProps {
  message: Message;
  artifact?: Artifact | null;
  onViewArtifact?: (artifact: Artifact) => void;
}

const CANONICAL_ABSTENTION_SNIPPET = "couldn't find sufficient evidence";

export function MessageItem({
  message,
  artifact,
  onViewArtifact,
}: MessageItemProps) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";

  const isAbstention =
    !isUser &&
    message.content.toLowerCase().includes(CANONICAL_ABSTENTION_SNIPPET);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isUser) {
    return (
      <div className="flex justify-end gap-3 max-w-3xl ml-auto py-2">
        <div className="flex flex-col items-end gap-1 max-w-[85%]">
          <div className="rounded-2xl rounded-tr-sm bg-brand-600 px-4 py-2.5 text-xs text-white shadow-md leading-relaxed whitespace-pre-wrap break-words">
            {message.content}
          </div>
          <span className="text-[10px] text-slate-500 font-mono pr-1">
            {new Date(message.created_at).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>
        <div className="w-7 h-7 rounded-full bg-brand-900 border border-brand-700 flex items-center justify-center shrink-0 text-brand-300">
          <User className="w-3.5 h-3.5" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 max-w-3xl mr-auto py-3 w-full">
      {/* Assistant Avatar */}
      <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-brand-700 to-brand-500 flex items-center justify-center shrink-0 text-white shadow-md shadow-brand-500/20 mt-1">
        <Sparkles className="w-3.5 h-3.5" />
      </div>

      <div className="flex-1 overflow-hidden space-y-3">
        {/* Attribution Badge & Actions */}
        <div className="flex items-center justify-between text-[11px] text-slate-400">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-200">Lenny Assistant</span>

            {message.provider && (
              <span
                className={`inline-flex items-center gap-1 px-1.5 py-0.2 rounded text-[10px] font-mono ${
                  message.provider === "ollama"
                    ? "bg-purple-950 text-purple-300 border border-purple-800"
                    : "bg-emerald-950 text-emerald-300 border border-emerald-800"
                }`}
              >
                {message.provider === "ollama" ? (
                  <Cpu className="w-2.5 h-2.5 text-purple-400" />
                ) : (
                  <Cloud className="w-2.5 h-2.5 text-emerald-400" />
                )}
                <span>{message.model || message.provider}</span>
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleCopy}
              aria-label="Copy response"
              className="p-1 rounded text-slate-400 hover:text-white hover:bg-surface-800 transition-colors flex items-center gap-1 text-[11px]"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-brand-400" />
                  <span className="text-brand-400 text-[10px]">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span className="text-[10px]">Copy</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Insufficient Evidence Info Banner — shown only if the grounded abstention string is present */}
        {isAbstention && (
          <div className="p-3 rounded-lg bg-blue-950/40 border border-blue-800/60 text-blue-200 text-xs flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-blue-300">Corpus Search Guidance</div>
              <div className="text-[11px] text-blue-200/90 leading-relaxed mt-0.5">
                No direct match found in the transcript archive — see the suggestions above to find related insights.
              </div>
            </div>
          </div>
        )}

        {/* Message Content (Markdown) */}
        <div className="prose-custom text-xs break-words">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Associated Artifact Workspace Chip */}
        {artifact && (
          <div className="pt-2">
            <button
              type="button"
              onClick={() => onViewArtifact?.(artifact)}
              className="inline-flex items-center gap-2.5 px-3 py-2 rounded-lg bg-surface-900 border border-brand-500/50 hover:border-brand-400 text-slate-200 hover:text-white transition-all shadow-md group text-xs text-left w-full sm:w-auto"
            >
              <div className="p-1.5 rounded-md bg-brand-900/60 border border-brand-700/60 text-brand-300 group-hover:text-brand-200 shrink-0">
                <Sparkles className="w-3.5 h-3.5" />
              </div>
              <div className="min-w-0">
                <div className="font-semibold text-brand-300 group-hover:text-brand-200 flex items-center gap-1.5">
                  <span>Open Artifact Workspace</span>
                  <span className="text-[10px] font-mono px-1 py-0.2 rounded bg-surface-800 text-slate-300 uppercase border border-surface-700">
                    {artifact.type}
                  </span>
                </div>
                <div className="text-[11px] text-slate-400 truncate max-w-xs sm:max-w-md">
                  {artifact.title || "Generated Deliverable"}
                </div>
              </div>
            </button>
          </div>
        )}

        {/* Verified Citations Section */}
        {message.citations && message.citations.length > 0 && (
          <div className="pt-2 border-t border-surface-800/80 space-y-2">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              <FileText className="w-3 h-3 text-brand-400" />
              <span>Supporting Sources ({message.citations.length})</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {message.citations.map((cit, idx) => (
                <CitationCard
                  key={cit.chunk_id || `cit-${idx}`}
                  citation={cit}
                  index={idx}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

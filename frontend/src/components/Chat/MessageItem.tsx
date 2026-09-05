/**
 * Lenny Growth Assistant — Message Item Component
 *
 * Editorial turn presentation:
 * - User query: compact, right-aligned editorial block with timestamp
 * - Assistant response: editorial reading room layout with rich prose typography
 * - Canonical abstention banner for insufficient evidence queries
 * - Provider & Model attribution provenance badge (OpenAI / Ollama)
 * - Discoverable copy-to-clipboard action
 * - Supporting transcript citations list
 */

"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Sparkles,
  Copy,
  Check,
  Cpu,
  Cloud,
  FileText,
  Compass,
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
      <div className="flex justify-end gap-3 max-w-full py-2">
        <div className="flex flex-col items-end gap-1.5 max-w-[85%] sm:max-w-[78%]">
          <div className="rounded-2xl rounded-tr-xs bg-surface-raised border border-border px-4 py-3 text-xs sm:text-sm text-content shadow-xs leading-relaxed whitespace-pre-wrap break-words">
            {message.content}
          </div>
          <span className="text-[10px] text-content-subtle font-mono pr-1">
            {new Date(message.created_at).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3.5 max-w-full py-3 w-full group">
      {/* Editorial Assistant Monogram Avatar */}
      <div className="w-7 h-7 rounded-lg bg-surface-raised border border-border-strong flex items-center justify-center shrink-0 text-signal font-serif font-bold text-xs shadow-xs mt-0.5 select-none">
        L
      </div>

      <div className="flex-1 overflow-hidden space-y-3 min-w-0">
        {/* Header Attribution & Provenance Actions */}
        <div className="flex items-center justify-between text-[11px] text-content-muted">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-content font-serif tracking-tight">
              Lenny Assistant
            </span>

            {message.provider && (
              <span
                className={`inline-flex items-center gap-1 px-1.5 py-0.2 rounded text-[10px] font-mono ${
                  message.provider === "ollama"
                    ? "bg-purple-950/20 text-purple-700 dark:text-purple-300 border border-purple-300 dark:border-purple-800"
                    : "bg-emerald-950/20 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800"
                }`}
              >
                {message.provider === "ollama" ? (
                  <Cpu className="w-2.5 h-2.5" />
                ) : (
                  <Cloud className="w-2.5 h-2.5" />
                )}
                <span>{message.model || message.provider}</span>
              </span>
            )}
          </div>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={handleCopy}
              aria-label="Copy response text"
              className="p-1 rounded text-content-muted hover:text-content hover:bg-surface-hover transition-colors flex items-center gap-1 text-[11px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-signal"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-signal" />
                  <span className="text-signal text-[10px] font-mono">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span className="text-[10px] font-mono hidden sm:inline">Copy</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Insufficient Evidence / Navigator Banner */}
        {isAbstention && (
          <div className="p-3.5 rounded-xl bg-evidence/10 border border-evidence/30 text-content text-xs flex items-start gap-3 shadow-xs">
            <Compass className="w-4 h-4 text-evidence shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <div className="font-semibold text-evidence">Corpus Boundary Notice</div>
              <div className="text-[11px] text-content-muted leading-relaxed">
                The archive does not contain sufficient direct transcript evidence for this query. Review the recommendations below for topics thoroughly covered in the podcast.
              </div>
            </div>
          </div>
        )}

        {/* Message Content (Prose Typography) */}
        <div className="prose-editorial text-xs sm:text-sm break-words leading-relaxed">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Associated Deliverable Workspace Chip */}
        {artifact && (
          <div className="pt-2">
            <button
              type="button"
              onClick={() => onViewArtifact?.(artifact)}
              className="inline-flex items-center gap-3 px-3.5 py-2 rounded-xl bg-surface border border-artifact/50 hover:border-artifact hover:bg-surface-raised text-content transition-all shadow-xs group text-xs text-left w-full sm:w-auto focus-visible:outline focus-visible:outline-2 focus-visible:outline-signal"
            >
              <div className="p-1.5 rounded-lg bg-artifact/10 border border-artifact/30 text-artifact shrink-0">
                <Sparkles className="w-3.5 h-3.5" />
              </div>
              <div className="min-w-0">
                <div className="font-semibold text-artifact flex items-center gap-1.5">
                  <span>Open Deliverable Workspace</span>
                  <span className="text-[10px] font-mono px-1 py-0.2 rounded bg-surface-raised text-content-muted uppercase border border-border">
                    {artifact.type}
                  </span>
                </div>
                <div className="text-[11px] text-content-muted truncate max-w-xs sm:max-w-md">
                  {artifact.title || "Generated Deliverable"}
                </div>
              </div>
            </button>
          </div>
        )}

        {/* Verified Transcript Citations Section */}
        {message.citations && message.citations.length > 0 && (
          <div className="pt-3 border-t border-border space-y-2.5">
            <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider text-content-subtle">
              <FileText className="w-3 h-3 text-evidence" />
              <span>
                {isAbstention
                  ? `Related Topics Explored (${message.citations.length})`
                  : `Supporting Sources (${message.citations.length})`}
              </span>
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

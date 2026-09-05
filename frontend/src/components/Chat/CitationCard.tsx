/**
 * Lenny Growth Assistant — Citation Card Component
 *
 * Displays verified podcast transcript evidence supporting an assistant response:
 * - Episode Title & Guest Name
 * - Timestamp / Topic location anchor
 * - Cosine similarity relevance badge
 * - Expandable source excerpt
 * - External link to episode where available
 *
 * Matches Section 7 of docs/implementation-contract.md and Section 6 of design.md.
 */

"use client";

import React, { useState } from "react";
import { ExternalLink, Mic, Clock, ChevronDown, Award } from "lucide-react";
import { Citation } from "../../types/citation";

interface CitationCardProps {
  citation: Citation;
  index: number;
}

export function CitationCard({ citation, index }: CitationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Format similarity as a percentage
  const similarityPct = Math.round(citation.similarity * 100);

  return (
    <div className="rounded-lg border border-surface-700 bg-surface-900/80 hover:bg-surface-800/80 transition-all text-xs overflow-hidden">
      <div
        className="p-2.5 flex items-start justify-between gap-2 cursor-pointer select-none"
        onClick={() => setIsExpanded(!isExpanded)}
        role="button"
        tabIndex={0}
        aria-expanded={isExpanded}
        aria-label={`Citation ${index + 1}: ${citation.guest_name} on ${citation.episode_title}`}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setIsExpanded(!isExpanded);
          }
        }}
      >
        <div className="flex items-start gap-2 overflow-hidden">
          <div className="mt-0.5 w-5 h-5 rounded bg-surface-800 border border-surface-700 flex items-center justify-center shrink-0 text-brand-400 font-mono text-[10px] font-bold">
            {index + 1}
          </div>

          <div className="overflow-hidden">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="font-semibold text-slate-200 truncate">
                {citation.guest_name}
              </span>
              {citation.timestamp && (
                <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.2 rounded bg-surface-800 text-slate-400 font-mono">
                  <Clock className="w-2.5 h-2.5 text-slate-500" />
                  {citation.timestamp}
                </span>
              )}
            </div>

            <div className="text-[11px] text-slate-400 truncate" title={citation.episode_title}>
              {citation.episode_title}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <span
            title={`Cosine similarity: ${citation.similarity.toFixed(3)}`}
            className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-medium ${
              similarityPct >= 75
                ? "bg-emerald-950/80 text-emerald-300 border border-emerald-800/50"
                : "bg-surface-800 text-slate-300 border border-surface-700"
            }`}
          >
            <Award className="w-2.5 h-2.5 text-brand-400" />
            {similarityPct}%
          </span>

          <ChevronDown
            className={`w-3.5 h-3.5 text-slate-400 transition-transform ${
              isExpanded ? "rotate-180" : ""
            }`}
          />
        </div>
      </div>

      {isExpanded && (
        <div className="px-3 pb-3 pt-1 border-t border-surface-800 text-slate-300 text-[11px] space-y-2 animate-fadeIn">
          {citation.excerpt && (
            <blockquote className="border-l-2 border-brand-500/60 pl-2.5 italic text-slate-300/90 leading-relaxed bg-surface-950/40 py-1 rounded-r">
              &ldquo;{citation.excerpt}&rdquo;
            </blockquote>
          )}

          <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1">
            <div className="flex items-center gap-1 font-mono">
              <Mic className="w-3 h-3 text-slate-500" />
              <span>Lenny&apos;s Podcast Archive</span>
            </div>

            {citation.source_url && (
              <a
                href={citation.source_url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="inline-flex items-center gap-1 text-brand-400 hover:text-brand-300 underline underline-offset-2"
              >
                <span>Listen / Source</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

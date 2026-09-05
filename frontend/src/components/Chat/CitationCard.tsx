/**
 * Lenny Growth Assistant — Citation Card Component
 *
 * Grounded Podcast Transcript Evidence:
 * - Numbered source badge linking claim to evidence
 * - Guest name, Episode title, and Timestamp/topic anchor
 * - Cosine similarity relevance score badge
 * - Accessible semantic button disclosure for excerpt expansion
 * - External link to episode audio/transcript where available
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

  // Format similarity as an integer percentage
  const similarityPct = Math.round(citation.similarity * 100);

  return (
    <div className="rounded-xl border border-border bg-surface hover:bg-surface-raised transition-all text-xs overflow-hidden shadow-xs">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
        aria-label={`Citation ${index + 1}: ${citation.guest_name} on ${citation.episode_title}`}
        className="w-full p-3 flex items-start justify-between gap-2.5 text-left select-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-signal"
      >
        <div className="flex items-start gap-2.5 overflow-hidden">
          <div className="mt-0.5 w-5 h-5 rounded-md bg-surface-raised border border-border flex items-center justify-center shrink-0 text-evidence font-mono text-[10px] font-bold">
            {index + 1}
          </div>

          <div className="overflow-hidden space-y-0.5">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="font-semibold text-content truncate font-serif">
                {citation.guest_name}
              </span>
              {citation.timestamp && (
                <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.2 rounded bg-surface-hover text-content-muted font-mono">
                  <Clock className="w-2.5 h-2.5" />
                  {citation.timestamp}
                </span>
              )}
            </div>

            <div className="text-[11px] text-content-muted truncate" title={citation.episode_title}>
              {citation.episode_title}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0 pt-0.5">
          <span
            title={`Cosine similarity: ${citation.similarity.toFixed(3)}`}
            className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-medium ${
              similarityPct >= 75
                ? "bg-evidence/15 text-evidence border border-evidence/30"
                : "bg-surface-hover text-content-muted border border-border"
            }`}
          >
            <Award className="w-2.5 h-2.5" />
            {similarityPct}%
          </span>

          <ChevronDown
            className={`w-3.5 h-3.5 text-content-subtle transition-transform duration-150 ${
              isExpanded ? "rotate-180" : ""
            }`}
          />
        </div>
      </button>

      {isExpanded && (
        <div className="px-3.5 pb-3 pt-1 border-t border-border text-content text-[11px] space-y-2.5 animate-fade-in bg-surface-raised/40">
          {citation.excerpt && (
            <blockquote className="border-l-2 border-evidence pl-3 italic text-content-muted leading-relaxed bg-surface/70 py-1.5 pr-2 rounded-r">
              &ldquo;{citation.excerpt}&rdquo;
            </blockquote>
          )}

          <div className="flex items-center justify-between text-[10px] text-content-subtle pt-1 font-mono">
            <div className="flex items-center gap-1">
              <Mic className="w-3 h-3 text-content-subtle" />
              <span>Lenny&apos;s Podcast Archive</span>
            </div>

            {citation.source_url && (
              <a
                href={citation.source_url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="inline-flex items-center gap-1 text-evidence hover:opacity-80 underline underline-offset-2"
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

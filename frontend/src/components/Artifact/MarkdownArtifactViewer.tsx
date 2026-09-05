/**
 * Lenny Growth Assistant — Markdown Artifact Viewer Component
 *
 * Editorial Deliverable Document Presentation:
 * - Rich typography for long-form reading (Ship 30 essays, playbooks, frameworks)
 * - Warm paper sheet on desk appearance in both light and dark modes
 * - Tables and syntax highlighting via remark-gfm
 */

"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownArtifactViewerProps {
  content: string;
  className?: string;
}

export function MarkdownArtifactViewer({
  content,
  className = "",
}: MarkdownArtifactViewerProps) {
  return (
    <div
      className={`h-full w-full overflow-y-auto p-4 sm:p-6 bg-canvas ${className}`}
    >
      <div className="max-w-3xl mx-auto bg-surface rounded-xl border border-border p-6 sm:p-10 shadow-xs prose-editorial text-xs sm:text-sm leading-relaxed space-y-4">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ children }) => (
              <h1 className="text-xl sm:text-2xl font-serif font-bold tracking-tight text-content pb-3 border-b border-border mb-5 mt-2">
                {children}
              </h1>
            ),
            h2: ({ children }) => (
              <h2 className="text-base sm:text-lg font-serif font-bold text-signal mt-7 mb-3 pt-3 border-t border-border">
                {children}
              </h2>
            ),
            h3: ({ children }) => (
              <h3 className="text-sm sm:text-base font-serif font-semibold text-content mt-5 mb-2">
                {children}
              </h3>
            ),
            p: ({ children }) => (
              <p className="text-content text-xs sm:text-sm leading-relaxed mb-4">
                {children}
              </p>
            ),
            ul: ({ children }) => (
              <ul className="list-disc pl-5 space-y-2 text-content text-xs sm:text-sm my-3">
                {children}
              </ul>
            ),
            ol: ({ children }) => (
              <ol className="list-decimal pl-5 space-y-2 text-content text-xs sm:text-sm my-3">
                {children}
              </ol>
            ),
            li: ({ children }) => (
              <li className="text-content text-xs sm:text-sm leading-relaxed">
                {children}
              </li>
            ),
            blockquote: ({ children }) => (
              <blockquote className="border-l-3 border-signal pl-4 py-2 italic bg-surface-hover/60 rounded-r text-content-muted text-xs sm:text-sm my-4">
                {children}
              </blockquote>
            ),
            code: ({ children, className }) => {
              const isInline = !className;
              return isInline ? (
                <code className="px-1.5 py-0.5 rounded bg-surface-raised font-mono text-[11px] text-evidence border border-border">
                  {children}
                </code>
              ) : (
                <pre className="p-4 rounded-xl bg-surface-raised font-mono text-xs text-content overflow-x-auto border border-border my-4 shadow-xs">
                  <code>{children}</code>
                </pre>
              );
            },
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
}

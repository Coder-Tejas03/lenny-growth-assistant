/**
 * Lenny Growth Assistant — Markdown Artifact Viewer Component
 *
 * Renders long-form markdown artifacts (such as Ship 30 essays or frameworks):
 * - Rich typography with custom styled headers, blockquotes, and bold anchors
 * - Tables and code formatting via remark-gfm
 * - Visual reading layout optimized for deep editorial content
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
      className={`h-full w-full overflow-y-auto p-6 bg-surface-900/90 text-slate-100 rounded-lg border border-surface-800 ${className}`}
    >
      <div className="max-w-3xl mx-auto prose-custom text-sm leading-relaxed space-y-4">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ children }) => (
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white pb-3 border-b border-surface-700/80 mb-4 mt-2">
                {children}
              </h1>
            ),
            h2: ({ children }) => (
              <h2 className="text-base sm:text-lg font-bold text-brand-300 mt-6 mb-3 pt-2 border-t border-surface-800/60">
                {children}
              </h2>
            ),
            h3: ({ children }) => (
              <h3 className="text-sm sm:text-base font-semibold text-slate-200 mt-4 mb-2">
                {children}
              </h3>
            ),
            p: ({ children }) => (
              <p className="text-slate-300 text-xs sm:text-sm leading-relaxed mb-3">
                {children}
              </p>
            ),
            ul: ({ children }) => (
              <ul className="list-disc pl-5 space-y-2 text-slate-300 text-xs sm:text-sm my-3">
                {children}
              </ul>
            ),
            ol: ({ children }) => (
              <ol className="list-decimal pl-5 space-y-2 text-slate-300 text-xs sm:text-sm my-3">
                {children}
              </ol>
            ),
            li: ({ children }) => (
              <li className="text-slate-300 text-xs sm:text-sm leading-relaxed">
                {children}
              </li>
            ),
            blockquote: ({ children }) => (
              <blockquote className="border-l-4 border-brand-500 pl-4 py-1 italic bg-surface-800/40 rounded-r text-slate-300 text-xs sm:text-sm my-4">
                {children}
              </blockquote>
            ),
            code: ({ children, className }) => {
              const isInline = !className;
              return isInline ? (
                <code className="px-1.5 py-0.5 rounded bg-surface-800 font-mono text-[11px] text-brand-300 border border-surface-700/50">
                  {children}
                </code>
              ) : (
                <pre className="p-3 rounded-lg bg-surface-950 font-mono text-xs text-slate-200 overflow-x-auto border border-surface-800 my-3">
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

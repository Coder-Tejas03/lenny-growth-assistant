/**
 * Lenny Growth Assistant — Safe Artifact Workspace Component
 *
 * Editorial Deliverable Desk:
 * - Document-on-a-desk reading environment
 * - Quiter masthead with title, type, and security provenance
 * - Dual-view tabs: Rendered Preview vs. Raw Source Code
 * - One-click Copy to clipboard with success feedback
 * - File download as .html or .md
 * - Close button to return to single-pane conversation
 */

"use client";

import React, { useState } from "react";
import {
  Code,
  Eye,
  Copy,
  Check,
  Download,
  X,
  Shield,
  FileCode,
  FileText,
} from "lucide-react";
import { Artifact } from "../../types/session";
import { SandboxedIframe } from "./SandboxedIframe";
import { MarkdownArtifactViewer } from "./MarkdownArtifactViewer";

interface ArtifactViewerProps {
  artifact: Artifact;
  onClose: () => void;
  className?: string;
}

export function ArtifactViewer({
  artifact,
  onClose,
  className = "",
}: ArtifactViewerProps) {
  const [viewMode, setViewMode] = useState<"preview" | "source">("preview");
  const [copied, setCopied] = useState(false);

  const isHtml = artifact.type === "html";

  const handleCopy = () => {
    navigator.clipboard.writeText(artifact.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const extension = isHtml ? "html" : "md";
    const mimeType = isHtml ? "text/html; charset=utf-8" : "text/markdown; charset=utf-8";
    const slug = (artifact.title || "artifact")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
    const filename = `${slug || "artifact"}.${extension}`;

    const blob = new Blob([artifact.content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div
      className={`flex flex-col h-full bg-surface border-l border-border shadow-lg relative select-none ${className}`}
    >
      {/* Top Masthead Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-surface-raised shrink-0">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="p-1.5 rounded-md bg-surface border border-border text-artifact shrink-0">
            {isHtml ? (
              <FileCode className="w-4 h-4" />
            ) : (
              <FileText className="w-4 h-4" />
            )}
          </div>
          <div className="min-w-0">
            <h2 className="text-xs sm:text-sm font-semibold text-content font-serif truncate">
              {artifact.title || "Generated Deliverable"}
            </h2>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="inline-block text-[10px] font-mono px-1.5 py-0.2 rounded border uppercase font-medium bg-surface text-content-muted border-border">
                {artifact.type}
              </span>
              <span className="flex items-center gap-1 text-[10px] text-signal font-mono">
                <Shield className="w-2.5 h-2.5" />
                <span>Isolated Sandbox</span>
              </span>
            </div>
          </div>
        </div>

        {/* View Mode Switcher & Actions */}
        <div className="flex items-center gap-1 sm:gap-1.5 shrink-0">
          {/* Preview / Source Switcher */}
          <div className="flex items-center bg-surface rounded-lg p-0.5 border border-border">
            <button
              type="button"
              onClick={() => setViewMode("preview")}
              className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition-all ${
                viewMode === "preview"
                  ? "bg-surface-raised text-content shadow-xs font-semibold border border-border"
                  : "text-content-muted hover:text-content"
              } focus-visible:outline focus-visible:outline-2 focus-visible:outline-signal`}
            >
              <Eye className="w-3 h-3" />
              <span>Preview</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode("source")}
              className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition-all ${
                viewMode === "source"
                  ? "bg-surface-raised text-content shadow-xs font-semibold border border-border"
                  : "text-content-muted hover:text-content"
              } focus-visible:outline focus-visible:outline-2 focus-visible:outline-signal`}
            >
              <Code className="w-3 h-3" />
              <span>Source</span>
            </button>
          </div>

          {/* Copy Button */}
          <button
            type="button"
            onClick={handleCopy}
            title="Copy content"
            aria-label="Copy artifact content"
            className="p-1.5 rounded-lg text-content-muted hover:text-content hover:bg-surface-hover transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-signal"
          >
            {copied ? (
              <Check className="w-4 h-4 text-signal" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>

          {/* Download Button */}
          <button
            type="button"
            onClick={handleDownload}
            title={`Download as .${isHtml ? "html" : "md"}`}
            aria-label={`Download as .${isHtml ? "html" : "md"}`}
            className="p-1.5 rounded-lg text-content-muted hover:text-content hover:bg-surface-hover transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-signal"
          >
            <Download className="w-4 h-4" />
          </button>

          {/* Close Button */}
          <button
            type="button"
            onClick={onClose}
            title="Close workspace"
            aria-label="Close artifact workspace"
            className="p-1.5 rounded-lg text-content-muted hover:text-danger hover:bg-danger/10 transition-colors ml-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-danger"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Document Body */}
      <div className="flex-1 overflow-hidden p-3 sm:p-4 bg-canvas select-text">
        {viewMode === "preview" ? (
          isHtml ? (
            <SandboxedIframe
              content={artifact.content}
              title={artifact.title || "Artifact Preview"}
            />
          ) : (
            <MarkdownArtifactViewer content={artifact.content} />
          )
        ) : (
          <div className="h-full w-full overflow-auto rounded-xl border border-border bg-surface-raised p-4 font-mono text-xs text-content shadow-xs">
            <pre className="whitespace-pre-wrap break-all leading-relaxed">
              <code>{artifact.content}</code>
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

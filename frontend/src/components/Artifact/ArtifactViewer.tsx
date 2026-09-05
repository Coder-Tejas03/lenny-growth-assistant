/**
 * Lenny Growth Assistant — Safe Artifact Workspace Component
 *
 * Provides a dedicated container for generated deliverables:
 * - Header with artifact title, format badge, and sandbox indicator
 * - Dual-view tabs: Rendered Preview vs. Raw Source Code
 * - One-click Copy to clipboard with success feedback
 * - File download as .html or .md
 * - Close button to return to single-pane chat view
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
      className={`flex flex-col h-full bg-surface-950 border-l border-surface-800 shadow-2xl relative select-none ${className}`}
    >
      {/* Top Header Bar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-800 bg-surface-900/90 backdrop-blur shrink-0">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="p-1.5 rounded-md bg-brand-900/50 border border-brand-700/60 text-brand-400 shrink-0">
            {isHtml ? (
              <FileCode className="w-4 h-4" />
            ) : (
              <FileText className="w-4 h-4" />
            )}
          </div>
          <div className="min-w-0">
            <h2 className="text-xs sm:text-sm font-semibold text-slate-100 truncate">
              {artifact.title || "Generated Artifact"}
            </h2>
            <div className="flex items-center gap-2 mt-0.5">
              <span
                className={`inline-block text-[10px] font-mono px-1.5 py-0.2 rounded border uppercase font-medium ${
                  isHtml
                    ? "bg-amber-950/60 text-amber-300 border-amber-800/60"
                    : "bg-blue-950/60 text-blue-300 border-blue-800/60"
                }`}
              >
                {artifact.type}
              </span>
              <span className="flex items-center gap-1 text-[10px] text-emerald-400 font-mono">
                <Shield className="w-2.5 h-2.5" />
                <span>Isolated Sandbox</span>
              </span>
            </div>
          </div>
        </div>

        {/* View Mode Switcher & Actions */}
        <div className="flex items-center gap-1.5 shrink-0">
          {/* Preview / Source Switcher */}
          <div className="flex items-center bg-surface-800 rounded-lg p-0.5 border border-surface-700/60">
            <button
              type="button"
              onClick={() => setViewMode("preview")}
              className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                viewMode === "preview"
                  ? "bg-brand-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Eye className="w-3 h-3" />
              <span>Preview</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode("source")}
              className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                viewMode === "source"
                  ? "bg-brand-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
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
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-800 transition-colors"
          >
            {copied ? (
              <Check className="w-4 h-4 text-emerald-400" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>

          {/* Download Button */}
          <button
            type="button"
            onClick={handleDownload}
            title={`Download as .${isHtml ? "html" : "md"}`}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-800 transition-colors"
          >
            <Download className="w-4 h-4" />
          </button>

          {/* Close Button */}
          <button
            type="button"
            onClick={onClose}
            title="Close artifact workspace"
            className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-surface-800 transition-colors ml-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Workspace Body */}
      <div className="flex-1 overflow-hidden p-3 bg-surface-950 select-text">
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
          <div className="h-full w-full overflow-auto rounded-lg border border-surface-800 bg-surface-900 p-4 font-mono text-xs text-slate-200">
            <pre className="whitespace-pre-wrap break-all leading-relaxed">
              <code>{artifact.content}</code>
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

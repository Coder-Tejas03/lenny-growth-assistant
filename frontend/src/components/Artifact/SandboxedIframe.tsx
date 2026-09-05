/**
 * Lenny Growth Assistant — Sandboxed Iframe Component
 *
 * Renders HTML artifacts inside a strictly sandboxed iframe:
 * - Defense-in-depth sanitization with DOMPurify on the client
 * - sandbox="allow-scripts" strictly omitting "allow-same-origin"
 *   Ensures the iframe runs in an opaque origin (null) and cannot
 *   access parent DOM, cookies, session storage, or local storage.
 * - Displays an isolated security provenance badge.
 */

"use client";

import React, { useEffect, useState } from "react";
import DOMPurify from "dompurify";
import { ShieldCheck, Lock } from "lucide-react";

interface SandboxedIframeProps {
  content: string;
  title: string;
  className?: string;
}

export function SandboxedIframe({
  content,
  title,
  className = "",
}: SandboxedIframeProps) {
  const [sanitizedHtml, setSanitizedHtml] = useState<string>(content);

  useEffect(() => {
    // Client-side defense-in-depth sanitization
    if (typeof window !== "undefined") {
      const clean = DOMPurify.sanitize(content, {
        WHOLE_DOCUMENT: true,
        ADD_TAGS: ["style", "link"],
        ADD_ATTR: ["target"],
      });
      setSanitizedHtml(clean);
    }
  }, [content]);

  return (
    <div className={`flex flex-col h-full w-full bg-white relative rounded-xl overflow-hidden border border-border shadow-xs ${className}`}>
      {/* Sandbox Isolation Header Indicator */}
      <div className="flex items-center justify-between px-3.5 py-2 bg-surface-raised border-b border-border text-[11px] text-content-muted select-none">
        <div className="flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-signal" />
          <span className="font-semibold text-content font-serif">Sandboxed Preview</span>
          <span className="text-[10px] text-content-subtle font-mono hidden sm:inline">
            (Isolated Origin)
          </span>
        </div>
        <div className="flex items-center gap-1 text-[10px] text-signal font-mono bg-signal/10 border border-signal/30 px-1.5 py-0.5 rounded">
          <Lock className="w-2.5 h-2.5" />
          <span>No Parent DOM Access</span>
        </div>
      </div>

      {/* Sandboxed iframe container */}
      <div className="flex-1 w-full h-full relative bg-white">
        <iframe
          title={title}
          // CRITICAL SECURITY REQUIREMENT:
          // sandbox="allow-scripts" executes interactive charts/scripts,
          // but strictly OMITS "allow-same-origin" so origin is "null".
          sandbox="allow-scripts"
          srcDoc={sanitizedHtml}
          className="w-full h-full border-none"
          loading="lazy"
        />
      </div>
    </div>
  );
}

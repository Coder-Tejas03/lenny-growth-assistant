/**
 * Lenny Growth Assistant — Application Header Component
 *
 * Editorial Signal Desk Masthead:
 * - Restrained editorial monogram & archive identity
 * - Real-time backend system connectivity probe with tooltip
 * - Explicit model / provider selector
 * - Deliverable / Artifact toggle when artifact exists
 * - Theme toggle (Dark / Light)
 * - Accessible mobile navigation drawer toggle
 */

"use client";

import React, { useEffect, useState } from "react";
import { Menu, Sparkles, X } from "lucide-react";
import { ModelSelector } from "../Chat/ModelSelector";
import { ThemeToggle } from "../Common/ThemeToggle";
import { ChatProvider } from "../../types/chat";
import { getHealth } from "../../lib/api";

interface HeaderProps {
  selectedProvider: ChatProvider;
  selectedModel?: string;
  onSelectModel: (provider: ChatProvider, model: string) => void;
  onToggleSidebar?: () => void;
  isStreaming?: boolean;
  hasArtifact?: boolean;
  isArtifactOpen?: boolean;
  onToggleArtifact?: () => void;
}

export function Header({
  selectedProvider,
  selectedModel,
  onSelectModel,
  onToggleSidebar,
  isStreaming = false,
  hasArtifact = false,
  isArtifactOpen = false,
  onToggleArtifact,
}: HeaderProps) {
  const [backendHealth, setBackendHealth] = useState<"healthy" | "degraded" | "offline">("healthy");
  const [healthTooltip, setHealthTooltip] = useState<string>("Backend healthy");

  useEffect(() => {
    let isMounted = true;

    async function checkHealth() {
      try {
        const health = await getHealth();
        if (isMounted) {
          if (health.status === "healthy") {
            setBackendHealth("healthy");
            setHealthTooltip("PostgreSQL + pgvector operational");
          } else {
            setBackendHealth("degraded");
            setHealthTooltip("One or more subsystems degraded");
          }
        }
      } catch {
        if (isMounted) {
          setBackendHealth("offline");
          setHealthTooltip("FastAPI backend unreachable");
        }
      }
    }

    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Poll every 30s
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header className="h-14 border-b border-border bg-surface/95 backdrop-blur px-3 sm:px-5 flex items-center justify-between z-10 shrink-0 select-none">
      {/* Brand & Identity Area */}
      <div className="flex items-center gap-3 min-w-0">
        {onToggleSidebar && (
          <button
            type="button"
            onClick={onToggleSidebar}
            aria-label="Toggle sessions library"
            className="md:hidden p-2 rounded-lg text-content-muted hover:text-content hover:bg-surface-hover transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-signal"
          >
            <Menu className="w-4 h-4" />
          </button>
        )}

        <div className="flex items-center gap-2.5 min-w-0">
          {/* Restrained Editorial Signal Monogram */}
          <div className="w-8 h-8 rounded-lg bg-surface-raised border border-border-strong flex items-center justify-center text-signal font-serif font-bold text-base shadow-xs shrink-0">
            L
          </div>

          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="text-xs sm:text-sm font-semibold tracking-tight text-content truncate font-serif">
                Lenny Growth Assistant
              </h1>
              <span className="hidden xl:inline-block px-1.5 py-0.2 rounded text-[10px] bg-surface-hover border border-border text-content-muted font-mono">
                Archive RAG
              </span>
            </div>
            <p className="hidden sm:block text-[11px] text-content-muted truncate leading-tight">
              Grounded in Lenny&apos;s Podcast transcript archive
            </p>
          </div>
        </div>
      </div>

      {/* Controls & Actions Area */}
      <div className="flex items-center gap-2 sm:gap-2.5 shrink-0">
        {/* Compact Health Probe Status */}
        <div
          title={healthTooltip}
          className="hidden lg:flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] border border-border bg-surface-raised/80 text-content-muted font-mono"
        >
          <span
            className={`w-2 h-2 rounded-full ${
              backendHealth === "healthy"
                ? "bg-emerald-500"
                : backendHealth === "degraded"
                ? "bg-amber-500"
                : "bg-red-500"
            }`}
          />
          <span className="capitalize">{backendHealth === "healthy" ? "Operational" : backendHealth}</span>
        </div>

        {/* Artifact Workspace Toggle Button */}
        {hasArtifact && onToggleArtifact && (
          <button
            type="button"
            onClick={onToggleArtifact}
            aria-label="Toggle deliverable workspace"
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium border transition-all ${
              isArtifactOpen
                ? "bg-artifact text-white border-artifact shadow-xs"
                : "bg-surface-raised border-border text-content hover:bg-surface-hover"
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-300" />
            <span className="font-semibold">Deliverable</span>
          </button>
        )}

        {/* Model Selector */}
        <ModelSelector
          selectedProvider={selectedProvider}
          selectedModel={selectedModel}
          onSelect={onSelectModel}
          disabled={isStreaming}
        />

        {/* Dual-Theme Toggle */}
        <ThemeToggle />
      </div>
    </header>
  );
}

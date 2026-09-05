/**
 * Lenny Growth Assistant — Application Header Component
 *
 * Displays:
 * - Brand identity and grounding subtitle
 * - Real-time backend connectivity status badge
 * - Visible model/provider toggle
 * - Mobile navigation menu toggle
 */

"use client";

import React, { useEffect, useState } from "react";
import { Sparkles, Menu, Activity, ShieldCheck, AlertCircle } from "lucide-react";
import { ModelSelector } from "../Chat/ModelSelector";
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
            setHealthTooltip("Database & Vector store operational");
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
    <header className="h-14 border-b border-surface-700 bg-surface-950/80 backdrop-blur-md px-4 flex items-center justify-between z-10 shrink-0">
      <div className="flex items-center gap-3">
        {onToggleSidebar && (
          <button
            type="button"
            onClick={onToggleSidebar}
            aria-label="Toggle Sessions Sidebar"
            className="md:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-800 transition-colors"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-brand-600 to-brand-400 flex items-center justify-center shadow-lg shadow-brand-500/20">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-bold text-white tracking-tight">
                Lenny Growth Assistant
              </h1>
              <span className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] rounded bg-brand-950 border border-brand-800 text-brand-300 font-mono">
                RAG v1.0
              </span>
            </div>
            <p className="hidden sm:block text-[11px] text-slate-400">
              Grounded in Lenny&apos;s Podcast transcript archive
            </p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Backend health status badge */}
        <div
          title={healthTooltip}
          className="hidden lg:flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] border border-surface-700 bg-surface-900/60 text-slate-300"
        >
          {backendHealth === "healthy" ? (
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          ) : backendHealth === "degraded" ? (
            <Activity className="w-3.5 h-3.5 text-amber-400" />
          ) : (
            <AlertCircle className="w-3.5 h-3.5 text-red-400" />
          )}
          <span className="capitalize">{backendHealth}</span>
        </div>

        {/* Artifact Workspace Toggle Button */}
        {hasArtifact && onToggleArtifact && (
          <button
            type="button"
            onClick={onToggleArtifact}
            aria-label="Toggle Artifact Workspace"
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium border transition-all ${
              isArtifactOpen
                ? "bg-brand-600 border-brand-500 text-white shadow-sm shadow-brand-500/20"
                : "bg-surface-900 border-surface-700 text-slate-300 hover:text-white hover:bg-surface-800"
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-brand-300" />
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
      </div>
    </header>
  );
}

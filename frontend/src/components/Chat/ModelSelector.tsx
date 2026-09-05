/**
 * Lenny Growth Assistant — Model / Provider Selector Component
 *
 * Editorial Signal Desk Inference Selector:
 * - Clear distinction between Cloud (OpenAI) and Local (Ollama)
 * - Zero silent fallback: selected provider and model are always explicit
 * - Hardware upgrade path (7B / 8B via OLLAMA_MODEL) documented
 * - Accessible popover with keyboard Escape-to-close handling
 */

"use client";

import React, { useEffect, useRef, useState } from "react";
import { Cloud, Cpu, ChevronDown } from "lucide-react";
import { ChatProvider } from "../../types/chat";

interface ModelOption {
  provider: ChatProvider;
  model: string;
  name: string;
  badge: string;
  isLocal: boolean;
  description: string;
}

const MODEL_OPTIONS: ModelOption[] = [
  {
    provider: "openai",
    model: "gpt-4o-mini",
    name: "OpenAI GPT-4o mini",
    badge: "Cloud Default",
    isLocal: false,
    description: "Fast, cost-disciplined cloud model for development & production",
  },
  {
    provider: "ollama",
    model: "qwen2.5:1.5b",
    name: "Ollama Qwen 2.5",
    badge: "1.5B Local Demo",
    isLocal: true,
    description: "On-device CPU model for private evaluation & offline demo",
  },
];

interface ModelSelectorProps {
  selectedProvider: ChatProvider;
  selectedModel?: string;
  onSelect: (provider: ChatProvider, model: string) => void;
  disabled?: boolean;
}

export function ModelSelector({
  selectedProvider,
  selectedModel,
  onSelect,
  disabled = false,
}: ModelSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const activeOption =
    MODEL_OPTIONS.find(
      (opt) =>
        opt.provider === selectedProvider &&
        (!selectedModel || opt.model === selectedModel)
    ) ||
    MODEL_OPTIONS.find((opt) => opt.provider === selectedProvider) ||
    MODEL_OPTIONS[0];

  const displayName =
    selectedModel && selectedModel !== activeOption.model
      ? `${activeOption.provider === "ollama" ? "Ollama" : "OpenAI"} ${selectedModel}`
      : activeOption.name;

  // Handle Escape key and outside clicks
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsOpen(false);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  const handleSelect = (option: ModelOption) => {
    onSelect(option.provider, option.model);
    setIsOpen(false);
  };

  return (
    <div className="relative inline-block text-left" ref={containerRef}>
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label="Select AI Model Provider"
        className={`flex items-center gap-2 px-2.5 sm:px-3 py-1.5 rounded-lg border text-xs font-medium transition-all shadow-xs ${
          activeOption.isLocal
            ? "bg-purple-950/10 dark:bg-purple-950/30 border-purple-300 dark:border-purple-800 text-purple-800 dark:text-purple-200 hover:bg-purple-950/20"
            : "bg-surface-raised border-border text-content hover:bg-surface-hover"
        } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"} focus-visible:outline focus-visible:outline-2 focus-visible:outline-signal`}
      >
        {activeOption.isLocal ? (
          <Cpu className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400 shrink-0" />
        ) : (
          <Cloud className="w-3.5 h-3.5 text-evidence shrink-0" />
        )}
        <span className="font-semibold truncate max-w-[120px] sm:max-w-[160px]">
          {displayName}
        </span>
        <span
          className={`px-1.5 py-0.2 rounded text-[10px] font-mono uppercase tracking-wider ${
            activeOption.isLocal
              ? "bg-purple-200 dark:bg-purple-900 text-purple-900 dark:text-purple-200"
              : "bg-surface-hover text-content-muted"
          }`}
        >
          {activeOption.isLocal ? "Local" : "Cloud"}
        </span>
        <ChevronDown className={`w-3.5 h-3.5 text-content-subtle transition-transform ${isOpen ? "rotate-180" : ""}`} />
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-20"
            onClick={() => setIsOpen(false)}
            aria-hidden="true"
          />
          <div
            role="listbox"
            className="absolute right-0 mt-2 w-72 sm:w-80 rounded-xl bg-surface-raised border border-border shadow-xl z-30 overflow-hidden animate-slide-up"
          >
            <div className="p-2.5 border-b border-border text-[11px] font-mono uppercase tracking-wider text-content-subtle">
              Select Inference Provider
            </div>
            <div className="p-1.5 space-y-1">
              {MODEL_OPTIONS.map((opt) => {
                const isSelected =
                  opt.provider === selectedProvider &&
                  (!selectedModel || opt.model === selectedModel);

                return (
                  <button
                    key={`${opt.provider}-${opt.model}`}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => handleSelect(opt)}
                    className={`w-full text-left p-2.5 rounded-lg flex flex-col gap-1 transition-all border ${
                      isSelected
                        ? "bg-surface border-signal/60 text-content shadow-xs"
                        : "border-transparent hover:bg-surface-hover text-content-muted hover:text-content"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {opt.isLocal ? (
                          <Cpu className="w-4 h-4 text-purple-500" />
                        ) : (
                          <Cloud className="w-4 h-4 text-evidence" />
                        )}
                        <span className="text-xs font-semibold text-content">{opt.name}</span>
                      </div>
                      <span
                        className={`text-[10px] font-mono px-1.5 py-0.2 rounded font-medium ${
                          opt.isLocal
                            ? "bg-purple-950/20 text-purple-700 dark:text-purple-300 border border-purple-300 dark:border-purple-800"
                            : "bg-surface-hover text-content-muted border border-border"
                        }`}
                      >
                        {opt.badge}
                      </span>
                    </div>
                    <p className="text-[11px] text-content-muted leading-relaxed">
                      {opt.description}
                    </p>
                  </button>
                );
              })}
            </div>

            {/* Hardware Upgrade Disclosure Section */}
            <div className="p-2.5 bg-surface border-t border-border text-[10px] text-content-muted space-y-1.5">
              <div className="flex items-center justify-between font-medium text-content">
                <span>Hardware Upgrade Path</span>
                <span className="text-[9px] px-1.5 py-0.2 rounded bg-surface-raised text-content-muted border border-border font-mono">
                  7B / 8B
                </span>
              </div>
              <p className="text-content-subtle leading-normal">
                Swap to larger local models (e.g. llama3.1:8b) via OLLAMA_MODEL in .env on machines with ≥16GB RAM.
              </p>
              <div className="text-[10px] text-signal pt-0.5 font-medium">
                Provider selection is explicit. Never switches silently.
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

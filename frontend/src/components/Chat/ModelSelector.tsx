/**
 * Lenny Growth Assistant — Model / Provider Selector Component
 *
 * Provides a visible control to toggle between Cloud (OpenAI) and Local (Ollama)
 * per Section 9 of design.md and Section 9 of docs/implementation-contract.md.
 * Ensures zero silent fallback: selected provider and model are always explicit.
 */

"use client";

import React from "react";
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
  const [isOpen, setIsOpen] = React.useState(false);

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

  const handleSelect = (option: ModelOption) => {
    onSelect(option.provider, option.model);
    setIsOpen(false);
  };

  return (
    <div className="relative inline-block text-left">
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label="Select AI Model Provider"
        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
          activeOption.isLocal
            ? "bg-purple-950/40 border-purple-800/60 text-purple-200 hover:bg-purple-900/50"
            : "bg-emerald-950/40 border-emerald-800/60 text-emerald-200 hover:bg-emerald-900/50"
        } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
      >
        {activeOption.isLocal ? (
          <Cpu className="w-3.5 h-3.5 text-purple-400" />
        ) : (
          <Cloud className="w-3.5 h-3.5 text-emerald-400" />
        )}
        <span className="font-semibold">{displayName}</span>
        <span
          className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${
            activeOption.isLocal
              ? "bg-purple-900/80 text-purple-300"
              : "bg-emerald-900/80 text-emerald-300"
          }`}
        >
          {activeOption.isLocal ? "Local" : "Cloud"}
        </span>
        <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isOpen ? "rotate-180" : ""}`} />
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
            className="absolute right-0 mt-2 w-72 rounded-xl bg-surface-900 border border-surface-700 shadow-2xl z-30 overflow-hidden animate-slide-up"
          >
            <div className="p-2 border-b border-surface-800 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Select Inference Provider
            </div>
            <div className="p-1 space-y-1">
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
                    className={`w-full text-left p-2.5 rounded-lg flex flex-col gap-1 transition-colors ${
                      isSelected
                        ? "bg-surface-800 text-white"
                        : "hover:bg-surface-800/60 text-slate-300"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {opt.isLocal ? (
                          <Cpu className="w-4 h-4 text-purple-400" />
                        ) : (
                          <Cloud className="w-4 h-4 text-emerald-400" />
                        )}
                        <span className="text-xs font-semibold">{opt.name}</span>
                      </div>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                          opt.isLocal
                            ? "bg-purple-900/50 text-purple-300 border border-purple-700/50"
                            : "bg-emerald-900/50 text-emerald-300 border border-emerald-700/50"
                        }`}
                      >
                        {opt.badge}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-tight">
                      {opt.description}
                    </p>
                  </button>
                );
              })}
            </div>
            <div className="p-2.5 bg-surface-950/70 border-t border-surface-800 text-[10px] text-slate-400 space-y-1">
              <div className="flex items-center justify-between text-slate-300 font-medium">
                <span>Hardware Upgrade Path</span>
                <span className="text-[9px] px-1.5 py-0.2 rounded bg-surface-800 text-purple-300 border border-purple-800/50 font-mono">
                  7B / 8B
                </span>
              </div>
              <p className="text-slate-500 leading-tight">
                Swap to larger local models (e.g. llama3.1:8b) via OLLAMA_MODEL in .env on machines with ≥16GB RAM.
              </p>
              <div className="text-[10px] text-brand-400/90 pt-0.5 font-medium">
                Provider selection is explicit. Never switches silently.
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

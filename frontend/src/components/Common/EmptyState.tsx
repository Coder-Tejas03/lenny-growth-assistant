/**
 * Lenny Growth Assistant — Empty State Component
 *
 * Editorial prompt invitation:
 * - Restrained archive signal mark
 * - "Ask the archive" display headline
 * - Grounded retrieval premise explanation
 * - Curated index of research starter questions
 */

"use client";

import React from "react";
import { Target, TrendingUp, Repeat, FlaskConical, ArrowUpRight } from "lucide-react";
import { ChatMode } from "../../types/chat";

interface EmptyStateProps {
  onSelectPrompt: (prompt: string, mode: ChatMode, suggestedTitle?: string) => void;
}

interface StarterItem {
  category: string;
  title: string;
  prompt: string;
  icon: React.ComponentType<{ className?: string }>;
}

export const STARTER_QUESTIONS: StarterItem[] = [
  {
    category: "Product-Market Fit",
    title: "Recognizing Genuine PMF",
    prompt: "How do I know if my startup has genuine product-market fit? What signals should I look for?",
    icon: Target,
  },
  {
    category: "Distribution & Growth",
    title: "Loops vs. Traditional Funnels",
    prompt: "What are growth loops and how are they different from traditional marketing funnels?",
    icon: TrendingUp,
  },
  {
    category: "Engagement & Retention",
    title: "Driving Retention & Reducing Churn",
    prompt: "What are the most effective strategies for driving user retention and reducing churn according to Lenny's guests?",
    icon: Repeat,
  },
  {
    category: "Execution",
    title: "Early Growth Experiments",
    prompt: "How should an early-stage startup think about running growth experiments and measuring success?",
    icon: FlaskConical,
  },
];

export function EmptyState({ onSelectPrompt }: EmptyStateProps) {
  return (
    <div className="max-w-2xl mx-auto py-12 px-4 text-center space-y-8 animate-fade-in">
      {/* Brand Signal Mark */}
      <div className="space-y-3">
        <div className="w-10 h-10 rounded-xl bg-surface-raised border border-border-strong mx-auto flex items-center justify-center text-signal font-serif font-bold text-lg shadow-xs">
          L
        </div>

        <div className="space-y-2">
          <h2 className="text-2xl sm:text-3xl font-serif font-normal text-content tracking-tight">
            Ask the archive
          </h2>
          <p className="text-xs sm:text-sm text-content-muted max-w-md mx-auto leading-relaxed">
            Every response is grounded strictly in transcript evidence with verified citations back to guests, episodes, and timestamps.
          </p>
        </div>
      </div>

      {/* Curated Prompt Index */}
      <div className="space-y-3 pt-2 text-left">
        <div className="flex items-center justify-between px-1">
          <span className="text-[11px] font-medium tracking-wide uppercase text-content-subtle font-mono">
            Curated Inquiries
          </span>
          <span className="text-[11px] text-content-subtle">
            Select to begin research
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {STARTER_QUESTIONS.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.title}
                type="button"
                onClick={() => onSelectPrompt(item.prompt, "default", item.title)}
                className="group p-3.5 rounded-xl bg-surface border border-border hover:border-signal/50 hover:bg-surface-raised transition-all text-left flex flex-col justify-between shadow-xs active:scale-[0.99] focus-visible:outline focus-visible:outline-2 focus-visible:outline-signal"
              >
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-content-subtle group-hover:text-signal transition-colors">
                    <div className="flex items-center gap-1.5 text-[10px] font-mono font-medium uppercase tracking-wider">
                      <Icon className="w-3 h-3" />
                      <span>{item.category}</span>
                    </div>
                    <ArrowUpRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>

                  <div className="text-xs font-semibold text-content group-hover:text-signal transition-colors">
                    {item.title}
                  </div>
                </div>

                <div className="text-[11px] text-content-muted mt-2 leading-snug line-clamp-2">
                  {item.prompt}
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

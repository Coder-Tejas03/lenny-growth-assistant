/**
 * Lenny Growth Assistant — Ship 30 for 30 Writing Skill
 *
 * Encodes the Ship 30 for 30 methodology into a dedicated content generation engine.
 * Generates an approximately 1,250-word, high-retention essay grounded in Lenny's
 * podcast transcripts with strong hook, short paragraphs, bold anchors, and actionable takeaways.
 */

import { randomUUID } from "node:crypto";
import { ArtifactPayload, Citation, EvidenceChunk, StreamEvent } from "../types.js";
import { NodeLLMProvider } from "../providers/index.js";

export const SHIP30_SYSTEM_PROMPT = `
You are an expert executive ghostwriter trained in the Ship 30 for 30 methodology.
Your task is to transform the user's topic and provided podcast evidence into a high-impact, actionable essay.

### Core Structural Heuristics:
1. Target Length: Approximately 1,250 words of punchy, high-retention writing.
2. The Headline & Hook (First 2-3 lines):
   - Open with an immediate curiosity gap, counterintuitive product/growth truth, or sharp operational tension.
   - Do NOT start with greeting or introductory filler ("In this article...", "Welcome to...").
3. Rhythm and Paragraphing:
   - High skimmability using short paragraphs (1 to 3 sentences maximum).
   - Use one-line "accordion" sentences to control reading cadence.
4. Visual Architecture:
   - Clear Markdown headers (## for major sections, ### for tactical sub-points).
   - Use bullet points with **bold anchor words** at the start of each bullet.
5. Grounded Substance:
   - Draw strictly upon the insights shared by guests in the context.
   - Attribute specific frameworks or lessons to the guest and episode using:
     [Episode Title: Guest Name, Timestamp or Topic]
6. Actionable Conclusion:
   - End with a concrete 3-to-5-step implementation checklist, rubric, or diagnostic test that the reader can execute today.
`.trim();

export interface Ship30Request {
  query: string;
  evidence: EvidenceChunk[];
  conversationHistory?: Array<{ role: "user" | "assistant" | "system"; content: string }>;
  provider: NodeLLMProvider;
}

export async function* runShip30Writer(
  req: Ship30Request
): AsyncGenerator<StreamEvent, { content: string; citations: Citation[]; artifact?: ArtifactPayload }> {
  yield {
    event: "status",
    data: { stage: "retrieving", message: "Curating evidence for Ship 30 essay..." },
  };

  const citations: Citation[] = req.evidence.map((e) => ({
    chunk_id: e.chunk_id,
    episode_title: e.episode_title,
    guest_name: e.guest_name,
    timestamp: e.timestamp || "Discussion",
    source_url: e.source_url,
    similarity: e.similarity,
    excerpt: e.content.slice(0, 160) + "...",
  }));

  if (citations.length > 0) {
    yield {
      event: "citation",
      data: { citations },
    };
  }

  yield {
    event: "status",
    data: { stage: "generating", message: "Drafting 1,250-word Ship 30 essay with hook and bold anchors..." },
  };

  const contextBlock = req.evidence.length > 0
    ? req.evidence
        .map(
          (e, idx) =>
            `--- Source [${idx + 1}]: ${e.episode_title} (${e.guest_name}) ---\n${e.content}`
        )
        .join("\n\n")
    : "Note: Synthesize based on core product/growth principles from Lenny's transcripts.";

  const prompt = `${SHIP30_SYSTEM_PROMPT}\n\n## Source Transcript Material:\n${contextBlock}`;

  const messages = [
    ...(req.conversationHistory || []),
    {
      role: "user" as const,
      content: `Write a complete Ship 30 for 30 style essay on: "${req.query}". Ensure high skimmability, bold anchors, and ~1,250 words.`,
    },
  ];

  let fullContent = "";
  for await (const token of req.provider.stream(
    [{ role: "system", content: prompt }, ...messages],
    { temperature: 0.35, maxTokens: 2500 }
  )) {
    fullContent += token;
    yield {
      event: "token",
      data: { delta: token },
    };
  }

  const artId = randomUUID();
  const cleanTitle = req.query.replace(/^[#\s]+/, "").slice(0, 50).trim();
  const title = `Ship 30: ${cleanTitle || "Growth Strategy"}`;
  const artifact: ArtifactPayload = {
    id: artId,
    type: "markdown",
    title,
    content: fullContent,
    metadata: { generated_at: new Date().toISOString() },
  };

  yield {
    event: "artifact",
    data: artifact,
  };

  return {
    content: fullContent,
    citations,
    artifact,
  };
}

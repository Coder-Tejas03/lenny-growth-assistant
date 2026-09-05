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
import { NAVIGATOR_SYSTEM_PROMPT } from "./grounded_qa.js";

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

  // 1. Boundary check: filter to sufficient evidence (similarity >= 0.45)
  const sufficientEvidence = req.evidence.filter((e) => e.similarity >= 0.45);

  if (sufficientEvidence.length === 0) {
    yield {
      event: "status",
      data: { stage: "generating", message: "Finding related topics to guide you..." },
    };

    const navigatorMessages = [
      ...(req.conversationHistory || []),
      {
        role: "user" as const,
        content: `The user requested a Ship 30 essay on: "${req.query}"\n\nNo matching podcast transcript evidence was found in Lenny's archive. Please explain warmly that Ship 30 essays must be grounded in Lenny's podcast transcripts, describe what topics the archive covers, and suggest 3-4 specific product/growth essay topics they could request instead (e.g., The 40% PMF Test, Compounding Growth Loops vs. Traditional Funnels, Why Most Retention Tactics Fail). Do NOT output an ungrounded essay.`,
      },
    ];

    let fullContent = "";
    try {
      for await (const token of req.provider.stream(
        [{ role: "system", content: NAVIGATOR_SYSTEM_PROMPT }, ...navigatorMessages],
        { temperature: 0.4, maxTokens: 450 }
      )) {
        fullContent += token;
        yield {
          event: "token",
          data: { delta: token },
        };
      }
    } catch (_err) {
      const fallback =
        "I don't have information on that topic in Lenny's podcast archive to write a grounded Ship 30 essay. " +
        "Here are some great product and growth topics you can explore:\n\n" +
        "- **The 40% Product-Market Fit Test** (Sean Ellis)\n" +
        "- **Compounding Growth Loops vs. Traditional Funnels** (Elena Verna)\n" +
        "- **Why Most Retention Tactics Fail** (Casey Winters & Brian Balfour)\n" +
        "- **Rapid Growth Experimentation Cadence** (Albert Cheng)\n\n" +
        "Feel free to request an essay on any of these topics!";
      yield { event: "token", data: { delta: fallback } };
      fullContent = fallback;
    }

    return {
      content: fullContent,
      citations: [],
    };
  }

  const citations: Citation[] = sufficientEvidence.map((e) => ({
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

  const contextBlock = sufficientEvidence
    .map(
      (e, idx) =>
        `--- Source [${idx + 1}]: ${e.episode_title} (${e.guest_name}) ---\n${e.content}`
    )
    .join("\n\n");


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

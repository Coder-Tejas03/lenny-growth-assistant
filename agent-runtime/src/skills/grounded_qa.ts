/**
 * Lenny Growth Assistant — Grounded QA Skill
 *
 * Implements strict corpus-grounded answering over retrieved Lenny podcast evidence.
 * Synthesizes inline citations and enforces the canonical abstention response when
 * evidence is insufficient. When evidence is absent, uses an LLM "navigator" to
 * proactively guide users to questions the corpus CAN answer.
 */

import { Citation, EvidenceChunk, StreamEvent } from "../types.js";
import { NodeLLMProvider } from "../providers/index.js";

export const CANONICAL_ABSTENTION_MESSAGE =
  "I couldn't find sufficient evidence in Lenny's podcast archive to answer this reliably. " +
  "Try asking about a product or growth topic covered in the podcast transcripts.";

export const GROUNDED_QA_SYSTEM_PROMPT = `
You are the Lenny Growth Assistant, a specialized advisor grounded strictly in Lenny Rachitsky's podcast archive.

### Core Grounding Instructions:
1. Answer the user's question using ONLY the retrieved transcript excerpts provided below.
2. For every key point, recommendation, or insight, cite the source using the strict format:
   [Episode Title: Guest Name, Timestamp or Topic]
   Example: [How to Measure Product-Market Fit: Rahul Vohra, 14:22]
3. If the provided excerpts do not contain enough evidence to answer the question, state:
   "${CANONICAL_ABSTENTION_MESSAGE}"
4. Do NOT speculate, hallucinate episodes, or use outside knowledge as if it came from Lenny's podcast.
5. Maintain a professional, actionable, and encouraging tone suited for product managers and founders.
`.trim();

/**
 * Navigator prompt — used when no corpus evidence is found.
 * Guides the user toward questions the corpus CAN answer, without fabricating content.
 */
export const NAVIGATOR_SYSTEM_PROMPT = `
You are the Lenny Growth Assistant, an AI guide to Lenny Rachitsky's podcast archive — one of the most valuable resources for founders and product builders.

The user asked a question, but the semantic search did not find strong matches in the podcast transcript corpus right now. Your job is to be genuinely helpful despite this.

### Your Response Rules:
1. NEVER fabricate podcast quotes, episode titles, or guest claims.
2. Briefly and warmly acknowledge that you don't have a direct answer for their specific question in the archive.
3. Explain what Lenny's podcast archive covers: product-market fit, growth loops, retention, go-to-market, experimentation, building growth teams, user onboarding, and startup strategy — all from practitioners who've done it.
4. Suggest 3-4 specific, concrete questions the user COULD ask that are answerable from the archive. Make these feel natural and relevant to what the user was trying to learn.
5. Keep your tone warm, encouraging, and beginner-friendly — NOT technical or dismissive.
6. If the user's question is about entrepreneurship or startups in general, acknowledge that and bridge to what Lenny covers.
7. End with an open invitation to explore.

Format your response in clean markdown with a short intro, then a bullet list of suggested questions. Keep it under 220 words. Be conversational, not robotic.
`.trim();

export interface GroundedQARequest {
  query: string;
  evidence: EvidenceChunk[];
  conversationHistory?: Array<{ role: "user" | "assistant" | "system"; content: string }>;
  provider: NodeLLMProvider;
}

export async function* runGroundedQA(
  req: GroundedQARequest
): AsyncGenerator<StreamEvent, { content: string; citations: Citation[] }> {
  // 1. Emit status event
  yield {
    event: "status",
    data: { stage: "retrieving", message: "Evaluating retrieved transcript evidence..." },
  };

  // 2. Threshold check: filter to sufficient evidence
  const sufficientEvidence = req.evidence.filter((e) => e.similarity >= 0.50);

  if (sufficientEvidence.length === 0) {
    // ── INTELLIGENT NAVIGATOR MODE ─────────────────────────────────────────
    // Instead of a cold canned abstention, use the LLM to guide the user
    yield {
      event: "status",
      data: { stage: "generating", message: "Finding related topics to guide you..." },
    };

    const navigatorMessages = [
      ...(req.conversationHistory || []),
      {
        role: "user" as const,
        content: `The user asked: "${req.query}"\n\nNo matching podcast transcript evidence was found. Please guide them helpfully toward what the archive covers.`,
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
      // Hard fallback if LLM itself fails
      const fallback =
        "I don't have a specific match for that in Lenny's podcast archive right now. " +
        "Here are some great starting questions:\n\n" +
        "- **How do I know if my startup has product-market fit?**\n" +
        "- **What growth loops work best for early-stage B2B products?**\n" +
        "- **How should I think about user retention vs acquisition?**\n" +
        "- **What does a good onboarding experience look like?**\n\n" +
        "Feel free to ask any of these or rephrase your question!";
      yield { event: "token", data: { delta: fallback } };
      fullContent = fallback;
    }

    return {
      content: fullContent,
      citations: [],
    };
    // ── END NAVIGATOR MODE ─────────────────────────────────────────────────
  }

  // 3. Format citations and emit citation event early
  const citations: Citation[] = sufficientEvidence.map((e) => ({
    chunk_id: e.chunk_id,
    episode_title: e.episode_title,
    guest_name: e.guest_name,
    timestamp: e.timestamp || "Discussion",
    source_url: e.source_url,
    similarity: e.similarity,
    excerpt: e.content.slice(0, 160) + "...",
  }));

  yield {
    event: "citation",
    data: { citations },
  };

  yield {
    event: "status",
    data: { stage: "generating", message: "Synthesizing grounded response..." },
  };

  // 4. Build grounded prompt context
  const contextBlock = sufficientEvidence
    .map(
      (e, idx) =>
        `### Evidence [${idx + 1}] (Episode: "${e.episode_title}", Guest: "${e.guest_name}", Timestamp: "${e.timestamp || "N/A"}", Relevance: ${(e.similarity * 100).toFixed(1)}%)\n${e.content}`
    )
    .join("\n\n");

  const prompt = `${GROUNDED_QA_SYSTEM_PROMPT}\n\n## Retrieved Evidence:\n${contextBlock}`;

  const messages = [
    ...(req.conversationHistory || []),
    { role: "user" as const, content: req.query },
  ];

  // 5. Stream LLM tokens
  let fullContent = "";
  for await (const token of req.provider.stream(
    [{ role: "system", content: prompt }, ...messages],
    { temperature: 0.2, maxTokens: 1500 }
  )) {
    fullContent += token;
    yield {
      event: "token",
      data: { delta: token },
    };
  }

  return {
    content: fullContent,
    citations,
  };
}

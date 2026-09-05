/**
 * Lenny Growth Assistant — Artifact Generator Skill
 *
 * Generates structured Markdown documents or self-contained HTML/CSS components
 * for side-by-side viewing in the application's Artifact Viewer.
 */

import { randomUUID } from "node:crypto";
import { ArtifactPayload, Citation, EvidenceChunk, StreamEvent } from "../types.js";
import { NodeLLMProvider } from "../providers/index.js";
import { NAVIGATOR_SYSTEM_PROMPT } from "./grounded_qa.js";

export const ARTIFACT_SYSTEM_PROMPT = `
You are an expert product systems designer and technical documentation specialist.
Your task is to generate a standalone visual or structural artifact (Markdown guide, rubric, framework, or self-contained HTML/CSS widget) based on the user's request.

### Output Standards:
1. Determine the appropriate artifact type:
   - "markdown": Comprehensive guides, frameworks, roadmaps, PRD templates, or checklists.
   - "html": Visual components, comparison cards, interactive dashboards, or flowcharts.
2. For HTML artifacts:
   - Output clean, valid, modern semantic HTML5 and CSS.
   - Use self-contained CSS inside <style> tags with high-contrast, modern aesthetics (Tailwind-inspired color palette).
   - Do NOT include external script tags or attempts to reach the parent window.
3. First provide a brief introductory paragraph in chat.
4. Then output the artifact block wrapped inside the exact XML tags:
   <artifact type="markdown|html" title="Your Descriptive Title">
   ...content...
   </artifact>
`.trim();

export interface ArtifactRequest {
  query: string;
  evidence: EvidenceChunk[];
  conversationHistory?: Array<{ role: "user" | "assistant" | "system"; content: string }>;
  provider: NodeLLMProvider;
}

export async function* runArtifactGenerator(
  req: ArtifactRequest
): AsyncGenerator<StreamEvent, { content: string; artifact?: ArtifactPayload; citations: Citation[] }> {
  yield {
    event: "status",
    data: { stage: "retrieving", message: "Reviewing specifications for artifact generation..." },
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
        content: `The user requested an artifact for: "${req.query}"\n\nNo matching podcast transcript evidence was found in Lenny's archive. Please explain warmly that you can only generate artifacts grounded in Lenny's archive, describe what topics the archive covers, and suggest 3-4 specific product/growth artifacts they could generate instead (e.g., A Product-Market Fit Survey Rubric, An Onboarding Growth Loop Diagram, A B2B SaaS Churn Diagnostic Matrix). Do NOT output an <artifact> block.`,
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
        "I don't have information on that topic in Lenny's podcast archive to generate an artifact. " +
        "Here are some great product and growth artifacts I can generate for you:\n\n" +
        "- **A Product-Market Fit Survey Rubric** (based on Sean Ellis & Superhuman)\n" +
        "- **A Product-Led vs. Sales-Led Comparison Card** (based on Elena Verna)\n" +
        "- **A Retention Cohort Diagnostic Matrix** (based on Casey Winters & Brian Balfour)\n" +
        "- **An Early-Stage Experimentation Roadmap** (based on Albert Cheng)\n\n" +
        "Feel free to ask for any of these artifacts!";
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

  yield {
    event: "status",
    data: { stage: "generating", message: "Designing structured artifact and component styles..." },
  };

  const contextBlock = sufficientEvidence
    .map((e) => `[Source: ${e.episode_title} / ${e.guest_name}]\n${e.content}`)
    .join("\n\n");


  const prompt = `${ARTIFACT_SYSTEM_PROMPT}\n\n## Context Material:\n${contextBlock}`;

  const messages = [
    ...(req.conversationHistory || []),
    {
      role: "user" as const,
      content: `Generate an artifact for: "${req.query}". Provide a brief explanation followed by the <artifact type="..." title="..."> block.`,
    },
  ];

  let fullContent = "";
  for await (const token of req.provider.stream(
    [{ role: "system", content: prompt }, ...messages],
    { temperature: 0.3, maxTokens: 2500 }
  )) {
    fullContent += token;
    yield {
      event: "token",
      data: { delta: token },
    };
  }

  // Parse generated artifact tags: <artifact type="html|markdown" title="...">...</artifact>
  let artifact: ArtifactPayload | undefined;
  const artifactRegex = /<artifact\s+type="(markdown|html)"\s+title="([^"]+)">([\s\S]*?)<\/artifact>/i;
  const match = fullContent.match(artifactRegex);

  if (match) {
    const type = match[1].toLowerCase() as "markdown" | "html";
    const title = match[2].trim();
    const content = match[3].trim();
    const id = randomUUID();

    artifact = {
      id,
      type,
      title,
      content,
      metadata: { generated_at: new Date().toISOString() },
    };

    yield {
      event: "artifact",
      data: artifact,
    };
  } else {
    // Fallback if model omitted tags
    const isHtml = req.query.toLowerCase().includes("html") || req.query.toLowerCase().includes("card") || fullContent.includes("<div");
    artifact = {
      id: randomUUID(),
      type: isHtml ? "html" : "markdown",
      title: "Generated Artifact",
      content: fullContent,
      metadata: { fallback: true, generated_at: new Date().toISOString() },
    };
    yield {
      event: "artifact",
      data: artifact,
    };
  }

  return {
    content: fullContent,
    artifact,
    citations,
  };
}

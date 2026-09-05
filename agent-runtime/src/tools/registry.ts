/**
 * Lenny Growth Assistant — Safe Tool Registry
 *
 * Enforces the allowlist upon tool registration and invocation. Only explicitly
 * permitted application tools can be registered or executed.
 */

import { ToolDefinition, Citation, ArtifactPayload, EvidenceChunk } from "../types.js";
import { validateToolAllowed, SecurityToolAccessError } from "./allowlist.js";

export class ToolRegistry {
  private tools: Map<string, ToolDefinition> = new Map();

  /**
   * Registers an application tool. Throws SecurityToolAccessError if the tool
   * is not on the allowlist.
   */
  public register(tool: ToolDefinition): void {
    validateToolAllowed(tool.name);
    this.tools.set(tool.name, tool);
  }

  public get(name: string): ToolDefinition | undefined {
    return this.tools.get(name);
  }

  public list(): ToolDefinition[] {
    return Array.from(this.tools.values());
  }

  public async execute(name: string, args: Record<string, unknown>): Promise<unknown> {
    validateToolAllowed(name);
    const tool = this.tools.get(name);
    if (!tool) {
      throw new Error(`Tool '${name}' is allowed but not registered in this runtime instance.`);
    }
    return await tool.execute(args);
  }
}

/**
 * Built-in Allowlisted Application Tools
 */

export const retrieveTranscriptsTool: ToolDefinition = {
  name: "retrieve_transcripts",
  description: "Retrieves evidence chunks from Lenny's podcast transcript archive.",
  parameters: {
    type: "object",
    properties: {
      query: { type: "string", description: "Search query or growth topic" },
      guest_filter: { type: "string", description: "Optional guest name filter" },
    },
    required: ["query"],
  },
  execute: async (args: Record<string, unknown>): Promise<unknown> => {
    // Application tool returning evidence metadata structure
    return {
      query: args.query,
      results: [] as EvidenceChunk[],
      note: "Retrieved via application retrieval service",
    };
  },
};

export const formatCitationTool: ToolDefinition = {
  name: "format_citation",
  description: "Formats a citation into the standard Lenny Assistant format [Episode: Guest, Timestamp].",
  parameters: {
    type: "object",
    properties: {
      episode_title: { type: "string" },
      guest_name: { type: "string" },
      timestamp: { type: "string" },
    },
    required: ["episode_title", "guest_name"],
  },
  execute: async (args: Record<string, unknown>): Promise<string> => {
    const episode = args.episode_title as string;
    const guest = args.guest_name as string;
    const ts = (args.timestamp as string) || "Discussion";
    return `[${episode}: ${guest}, ${ts}]`;
  },
};

export const generateArtifactTool: ToolDefinition = {
  name: "generate_artifact",
  description: "Generates a structured Markdown or sandboxed HTML artifact for side-by-side display.",
  parameters: {
    type: "object",
    properties: {
      type: { type: "string", enum: ["markdown", "html"] },
      title: { type: "string" },
      content: { type: "string" },
    },
    required: ["type", "title", "content"],
  },
  execute: async (args: Record<string, unknown>): Promise<ArtifactPayload> => {
    const type = (args.type as "markdown" | "html") || "markdown";
    const title = (args.title as string) || "Untitled Artifact";
    const content = (args.content as string) || "";
    const id = `art_${Date.now().toString(36)}_${Math.random().toString(36).substring(2, 8)}`;

    return {
      id,
      type,
      title,
      content,
      metadata: { generated_at: new Date().toISOString() },
    };
  },
};

/**
 * Creates and initializes a safe ToolRegistry pre-populated with allowed tools.
 */
export function createSafeToolRegistry(): ToolRegistry {
  const registry = new ToolRegistry();
  registry.register(retrieveTranscriptsTool);
  registry.register(formatCitationTool);
  registry.register(generateArtifactTool);
  return registry;
}

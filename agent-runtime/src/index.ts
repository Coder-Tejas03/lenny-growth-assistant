/**
 * Lenny Growth Assistant — Internal Pi Agent Runtime Master Entry Point
 *
 * Coordinates agent skill execution (grounded_qa, ship30_writer, artifact_generator),
 * safe tool registry access, provider abstraction, and normalized event streaming
 * via stdio for FastAPI.
 */

import {
  AgentRequest,
  AgentResponse,
  DoneEventData,
  StreamEvent,
} from "./types.js";
import { getNodeProvider } from "./providers/index.js";
import { runGroundedQA } from "./skills/grounded_qa.js";
import { runShip30Writer } from "./skills/ship30_writer.js";
import { runArtifactGenerator } from "./skills/artifact_generator.js";
import { createSafeToolRegistry } from "./tools/registry.js";

export { createSafeToolRegistry } from "./tools/registry.js";
export * from "./types.js";
export * from "./tools/allowlist.js";
export * from "./skills/grounded_qa.js";
export * from "./skills/ship30_writer.js";
export * from "./skills/artifact_generator.js";

/**
 * Executes the requested agent skill and yields normalized streaming events.
 */
export async function* executeSkillStream(
  req: AgentRequest
): AsyncGenerator<StreamEvent, AgentResponse> {
  const provider = getNodeProvider(req.provider, req.model, req.mock_mode);
  let result: { content: string; citations: any[]; artifact?: any };

  switch (req.skill) {
    case "grounded_qa": {
      const gen = runGroundedQA({
        query: req.query,
        evidence: req.evidence || [],
        conversationHistory: req.conversation_history,
        provider,
      });
      while (true) {
        const next = await gen.next();
        if (next.done) {
          result = next.value;
          break;
        }
        yield next.value;
      }
      break;
    }

    case "ship30_writer": {
      const gen = runShip30Writer({
        query: req.query,
        evidence: req.evidence || [],
        conversationHistory: req.conversation_history,
        provider,
      });
      while (true) {
        const next = await gen.next();
        if (next.done) {
          result = next.value;
          break;
        }
        yield next.value;
      }
      break;
    }

    case "artifact_generator": {
      const gen = runArtifactGenerator({
        query: req.query,
        evidence: req.evidence || [],
        conversationHistory: req.conversation_history,
        provider,
      });
      while (true) {
        const next = await gen.next();
        if (next.done) {
          result = next.value;
          break;
        }
        yield next.value;
      }
      break;
    }

    default:
      throw new Error(`Unknown skill '${(req as any).skill}'`);
  }

  // Calculate execution metrics
  const wordCount = result.content.split(/\s+/).length;
  const promptWords = (req.query + (req.evidence || []).map((e) => e.content).join(" ")).split(/\s+/).length;
  const promptTokens = promptWords;
  const completionTokens = wordCount;
  const costUsd = req.provider === "openai" ? (promptTokens * 0.15 + completionTokens * 0.60) / 1_000_000 : 0.0;

  const doneData: DoneEventData = {
    provider: req.provider,
    model: provider.model,
    tokens: {
      prompt: promptTokens,
      completion: completionTokens,
      total: promptTokens + completionTokens,
    },
    cost_usd: Math.round(costUsd * 1000000) / 1000000,
  };

  yield {
    event: "done",
    data: doneData,
  };

  return {
    content: result.content,
    citations: result.citations,
    artifact: result.artifact,
    metadata: {
      provider: req.provider,
      model: provider.model,
      tokens: doneData.tokens,
      cost_usd: doneData.cost_usd,
    },
  };
}

/**
 * Standard I/O CLI runner: Reads a single JSON request line from stdin
 * and streams newline-delimited JSON events to stdout.
 */
async function runCLI(): Promise<void> {
  const chunks: Buffer[] = [];
  process.stdin.on("data", (chunk) => chunks.push(chunk));
  process.stdin.on("end", async () => {
    try {
      const raw = Buffer.concat(chunks).toString("utf-8").trim();
      if (!raw) return;

      const request = JSON.parse(raw) as AgentRequest;
      for await (const event of executeSkillStream(request)) {
        process.stdout.write(JSON.stringify(event) + "\n");
      }
    } catch (err: any) {
      const errorEvent: StreamEvent = {
        event: "error",
        data: { code: "AGENT_RUNTIME_ERROR", message: err.message, stack: err.stack },
      };
      process.stdout.write(JSON.stringify(errorEvent) + "\n");
      process.exit(1);
    }
  });
}

// Auto-run CLI if invoked directly from command line
if (import.meta.url === `file://${process.argv[1]}`) {
  runCLI();
}

/**
 * Lenny Growth Assistant — W3C Server-Sent Events (SSE) Parser
 *
 * Implements standard SSE stream parsing:
 * - Buffers fragmented chunks across network packets
 * - Parses 'event' and 'data' lines
 * - Dispatches typed events (status, citation, token, artifact, done, error)
 * - Handles terminal [DONE] signal
 *
 * Adheres to Section 10 of docs/implementation-contract.md.
 */

import type {
  SSEErrorData,
  SSEStatusData,
  SSETokenData,
  SSEDoneData,
  SSECitationData,
} from "../types/chat";
import type { Artifact } from "../types/session";

export interface SSEParserCallbacks {
  onStatus?: (data: SSEStatusData) => void;
  onCitation?: (data: SSECitationData) => void;
  onToken?: (data: SSETokenData) => void;
  onArtifact?: (data: Artifact) => void;
  onDone?: (data: SSEDoneData) => void;
  onError?: (data: SSEErrorData) => void;
  onTerminalDone?: () => void;
}

export class SSEParser {
  private buffer: string = "";
  private currentEvent: string = "message";
  private currentData: string[] = [];
  private callbacks: SSEParserCallbacks;

  constructor(callbacks: SSEParserCallbacks) {
    this.callbacks = callbacks;
  }

  /**
   * Ingests a new text chunk, buffers incomplete lines, and dispatches complete events.
   */
  public feed(chunk: string): void {
    this.buffer += chunk;

    // Normalize \r\n to \n
    const lines = this.buffer.split(/\r\n|\r|\n/);

    // Keep the last segment in buffer as it may be an incomplete line
    this.buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line === "") {
        // Empty line indicates event boundary
        this.dispatchCurrentEvent();
      } else if (line.startsWith(":")) {
        // Comment line per SSE specification, ignore
        continue;
      } else if (line.startsWith("event:")) {
        this.currentEvent = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        const dataValue = line.slice(5).trim();
        this.currentData.push(dataValue);
      }
    }
  }

  /**
   * Flushes any remaining content in the buffer (e.g. at stream end).
   */
  public flush(): void {
    if (this.buffer.trim().length > 0) {
      const remainingLine = this.buffer.trim();
      if (remainingLine.startsWith("data:")) {
        this.currentData.push(remainingLine.slice(5).trim());
      }
      this.buffer = "";
    }
    this.dispatchCurrentEvent();
  }

  private dispatchCurrentEvent(): void {
    if (this.currentData.length === 0) {
      this.currentEvent = "message";
      return;
    }

    const rawData = this.currentData.join("\n");
    const eventName = this.currentEvent;

    // Reset accumulator state
    this.currentData = [];
    this.currentEvent = "message";

    // Check for standard terminal delimiter [DONE]
    if (rawData === "[DONE]") {
      this.callbacks.onTerminalDone?.();
      return;
    }

    let parsedJson: any;
    try {
      parsedJson = JSON.parse(rawData);
    } catch {
      // If data is raw text
      parsedJson = rawData;
    }

    switch (eventName) {
      case "status":
        this.callbacks.onStatus?.(parsedJson as SSEStatusData);
        break;
      case "citation":
        this.callbacks.onCitation?.(parsedJson as SSECitationData);
        break;
      case "token":
        this.callbacks.onToken?.(parsedJson as SSETokenData);
        break;
      case "artifact":
        this.callbacks.onArtifact?.(parsedJson as Artifact);
        break;
      case "done":
        this.callbacks.onDone?.(parsedJson as SSEDoneData);
        break;
      case "error":
        this.callbacks.onError?.(
          typeof parsedJson === "string" ? { error: parsedJson } : (parsedJson as SSEErrorData)
        );
        break;
      default:
        // Generic or unhandled event
        break;
    }
  }
}

/**
 * Consumes a browser ReadableStreamDefaultReader<Uint8Array> and decodes SSE events.
 */
export async function parseSSEStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  callbacks: SSEParserCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const decoder = new TextDecoder("utf-8");
  const parser = new SSEParser(callbacks);

  try {
    while (true) {
      if (signal?.aborted) {
        throw new DOMException("Stream aborted by user", "AbortError");
      }

      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      if (value) {
        const text = decoder.decode(value, { stream: true });
        parser.feed(text);
      }
    }

    parser.flush();
  } finally {
    reader.releaseLock();
  }
}

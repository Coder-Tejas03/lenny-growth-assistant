/**
 * Lenny Growth Assistant — Tool Allowlist & Security Perimeter
 *
 * Strictly restricts the internal Pi Agent runtime to allowlisted application
 * tools only. Forbids and intercepts any general filesystem, shell execution,
 * or arbitrary web browsing tools.
 */

export const ALLOWED_TOOL_NAMES = [
  "retrieve_transcripts",
  "format_citation",
  "generate_artifact",
] as const;

export type AllowedToolName = (typeof ALLOWED_TOOL_NAMES)[number];

export const FORBIDDEN_TOOL_NAMES = [
  "read_file",
  "write_file",
  "list_dir",
  "edit_file",
  "bash",
  "sh",
  "exec",
  "terminal",
  "browser",
  "web_search",
  "fetch",
  "curl",
] as const;

export class SecurityToolAccessError extends Error {
  public readonly toolName: string;
  public readonly reason: string;

  constructor(toolName: string, reason: string) {
    super(
      `[SECURITY ERROR] Tool '${toolName}' is blocked: ${reason}. ` +
        `The Lenny Growth Assistant runtime strictly permits only: ${ALLOWED_TOOL_NAMES.join(", ")}.`
    );
    this.name = "SecurityToolAccessError";
    this.toolName = toolName;
    this.reason = reason;
  }
}

/**
 * Checks if a given tool name is explicitly allowlisted.
 */
export function isToolAllowed(toolName: string): toolName is AllowedToolName {
  return (ALLOWED_TOOL_NAMES as readonly string[]).includes(toolName);
}

/**
 * Validates tool access against the allowlist and security boundary.
 * Throws SecurityToolAccessError if the tool is forbidden or unapproved.
 */
export function validateToolAllowed(toolName: string): void {
  const normalized = toolName.trim().toLowerCase();

  // Check against explicit forbidden machine tools
  if ((FORBIDDEN_TOOL_NAMES as readonly string[]).includes(normalized)) {
    throw new SecurityToolAccessError(
      toolName,
      "General machine access (filesystem, shell, or browsing) is strictly forbidden"
    );
  }

  // Check if tool is in the allowlist
  if (!isToolAllowed(normalized)) {
    throw new SecurityToolAccessError(
      toolName,
      "Tool is not registered on the application allowlist"
    );
  }
}

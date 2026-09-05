/**
 * Automated Security & Tool Allowlist Verification Test
 *
 * Verifies that:
 * 1. Allowlisted application tools register and execute safely.
 * 2. General machine tools (shell, filesystem, browser) are strictly blocked with SecurityToolAccessError.
 * 3. Arbitrary unapproved tools cannot be registered.
 */

import assert from "node:assert";
import {
  ALLOWED_TOOL_NAMES,
  FORBIDDEN_TOOL_NAMES,
  SecurityToolAccessError,
  validateToolAllowed,
} from "../dist/tools/allowlist.js";
import {
  createSafeToolRegistry,
  ToolRegistry,
  formatCitationTool,
} from "../dist/tools/registry.js";

async function runSecurityTests(): Promise<void> {
  console.log("▶ Running Pi Agent Runtime Security & Tool Allowlist Tests...");

  // 1. Verify safe registry initialization with allowlisted tools
  const registry = createSafeToolRegistry();
  const tools = registry.list();
  assert.strictEqual(tools.length, 3, "Safe registry must contain exactly 3 allowlisted tools");

  const toolNames = tools.map((t) => t.name);
  for (const name of ALLOWED_TOOL_NAMES) {
    assert.ok(toolNames.includes(name), `Allowlisted tool '${name}' must be registered`);
  }
  console.log("  ✔ All allowlisted tools present in safe registry");

  // 2. Verify format_citation tool execution
  const citationResult = await registry.execute("format_citation", {
    episode_title: "Measuring Product-Market Fit",
    guest_name: "Rahul Vohra",
    timestamp: "14:22",
  });
  assert.strictEqual(
    citationResult,
    "[Measuring Product-Market Fit: Rahul Vohra, 14:22]",
    "Citation formatting must match required in-text syntax"
  );
  console.log("  ✔ Application tool execution verified");

  // 3. Verify that all forbidden machine tools are blocked
  for (const forbidden of FORBIDDEN_TOOL_NAMES) {
    assert.throws(
      () => validateToolAllowed(forbidden),
      (err: Error) => {
        return (
          err instanceof SecurityToolAccessError &&
          err.toolName === forbidden &&
          err.message.includes("blocked")
        );
      },
      `Forbidden tool '${forbidden}' must throw SecurityToolAccessError`
    );

    // Also assert that registry rejects registration of forbidden tool
    assert.throws(
      () =>
        registry.register({
          name: forbidden,
          description: "Dangerous tool",
          parameters: { type: "object" },
          execute: async () => {},
        }),
      (err: Error) => err instanceof SecurityToolAccessError,
      `Registry must reject registration of forbidden tool '${forbidden}'`
    );
  }
  console.log(`  ✔ All ${FORBIDDEN_TOOL_NAMES.length} forbidden machine tools strictly blocked`);

  // 4. Verify unapproved arbitrary tool rejection
  assert.throws(
    () => validateToolAllowed("arbitrary_external_action"),
    (err: Error) => err instanceof SecurityToolAccessError,
    "Arbitrary unapproved tools must throw SecurityToolAccessError"
  );
  console.log("  ✔ Arbitrary unapproved tool rejected");

  console.log("🎉 ALL AGENT RUNTIME SECURITY TESTS PASSED!");
}

runSecurityTests().catch((err) => {
  console.error("❌ Security test failure:", err);
  process.exit(1);
});

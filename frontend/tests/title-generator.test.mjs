import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { generateChatTitle } from "../src/lib/title-generator.ts";

describe("Title Generator Utility", () => {
  it("passes curated starter title through directly", () => {
    const title = generateChatTitle(
      "How do I know if my startup has genuine product-market fit? What signals should I look for?",
      "Recognizing Genuine PMF"
    );
    assert.equal(title, "Recognizing Genuine PMF");
  });

  it("strips conversational filler and applies title casing", () => {
    const title = generateChatTitle(
      "How do I know if my startup has genuine product-market fit? What signals should I look for?"
    );
    assert.ok(title.includes("Product-Market Fit") || title.includes("Startup"));
    assert.ok(!title.toLowerCase().startsWith("how do i"));
  });

  it("preserves known industry acronyms (PMF, SaaS, B2B, OKRs)", () => {
    const t1 = generateChatTitle("what are the best ways to measure pmf in b2b saas?");
    assert.ok(t1.includes("PMF"));
    assert.ok(t1.includes("B2B"));
    assert.ok(t1.includes("SaaS"));

    const t2 = generateChatTitle("how to set quarterly okrs for growth teams");
    assert.ok(t2.includes("OKRs"));
  });

  it("handles loops vs traditional marketing funnels query cleanly", () => {
    const title = generateChatTitle(
      "What are growth loops and how are they different from traditional marketing funnels?"
    );
    assert.ok(title.includes("Growth Loops"));
    assert.ok(title.length <= 40);
  });

  it("clamps long queries gracefully without cutting mid-word", () => {
    const longQuery =
      "What are the most effective strategies for driving user retention and reducing churn according to Lenny's guests?";
    const title = generateChatTitle(longQuery);
    assert.ok(title.length <= 40);
    assert.ok(!title.endsWith("-"));
  });

  it("returns default title for empty or whitespace query", () => {
    assert.equal(generateChatTitle(""), "New Conversation");
    assert.equal(generateChatTitle("   "), "New Conversation");
  });
});

/**
 * Automated Tests for Agent Skills & Streaming Normalization
 *
 * Verifies:
 * 1. Grounded QA skill with evidence and canonical abstention on weak evidence.
 * 2. Ship 30 for 30 writer skill formatting.
 * 3. Artifact generator skill creating structured Markdown/HTML payloads.
 * 4. Master execution stream emitting normalized events (status, citation, token, artifact, done).
 */

import assert from "node:assert";
import { executeSkillStream, CANONICAL_ABSTENTION_MESSAGE } from "../dist/index.js";

const sampleEvidence: any[] = [
  {
    chunk_id: "chk-001",
    episode_title: "How to Measure Product-Market Fit",
    guest_name: "Rahul Vohra",
    content: "When we surveyed Superhuman users, we asked how disappointed they would be if the product disappeared.",
    timestamp: "14:22",
    similarity: 0.88,
  },
];

async function runSkillTests(): Promise<void> {
  console.log("▶ Running Pi Agent Runtime Skills & Streaming Tests...");

  // 1. Test Grounded QA with sufficient evidence
  console.log("  • Testing Grounded QA (sufficient evidence)...");
  const qaEvents: any[] = [];
  const qaGen = executeSkillStream({
    skill: "grounded_qa",
    query: "How did Superhuman measure PMF?",
    evidence: sampleEvidence,
    provider: "openai",
    model: "gpt-4o-mini",
    mock_mode: true,
  });

  for await (const ev of qaGen) {
    qaEvents.push(ev);
  }

  const eventTypes = qaEvents.map((e) => e.event);
  assert.ok(eventTypes.includes("status"), "Must emit status event");
  assert.ok(eventTypes.includes("citation"), "Must emit citation event");
  assert.ok(eventTypes.includes("token"), "Must emit token event");
  assert.ok(eventTypes.includes("done"), "Must emit done event");

  const citationEv = qaEvents.find((e) => e.event === "citation");
  assert.ok(citationEv && (citationEv.data as any).citations.length === 1);
  assert.strictEqual((citationEv.data as any).citations[0].guest_name, "Rahul Vohra");

  const doneEv = qaEvents.find((e) => e.event === "done");
  assert.ok(doneEv && (doneEv.data as any).provider === "openai");
  assert.ok((doneEv.data as any).tokens.total > 0);
  console.log("  ✔ Grounded QA with citations verified");

  // 2. Test Grounded QA with weak evidence (< 0.65 threshold) -> Abstention
  console.log("  • Testing Grounded QA (weak evidence -> abstention)...");
  const weakEvidence: any[] = [
    {
      chunk_id: "chk-weak",
      episode_title: "Cooking Tips",
      guest_name: "Chef",
      content: "Add a pinch of salt to boiling pasta water.",
      similarity: 0.42, // Below 0.65
    },
  ];

  const abstentionEvents: any[] = [];
  for await (const ev of executeSkillStream({
    skill: "grounded_qa",
    query: "How do I make beef bourguignon?",
    evidence: weakEvidence,
    provider: "ollama",
    mock_mode: true,
  })) {
    abstentionEvents.push(ev);
  }

  // Citations must be empty or omitted
  const weakCitationEv = abstentionEvents.find((e) => e.event === "citation");
  assert.ok(!weakCitationEv || (weakCitationEv.data as any).citations.length === 0);

  const tokenDeltas = abstentionEvents
    .filter((e) => e.event === "token")
    .map((e) => (e.data as any).delta)
    .join("");
  assert.ok(tokenDeltas.includes("sufficient evidence"), "Response must contain canonical abstention message");
  console.log("  ✔ Grounded QA threshold abstention verified");

  // 3. Test Ship 30 Writer
  console.log("  • Testing Ship 30 for 30 Writing skill...");
  const ship30Events: any[] = [];
  for await (const ev of executeSkillStream({
    skill: "ship30_writer",
    query: "Retention loops in B2B SaaS",
    evidence: sampleEvidence,
    provider: "openai",
    mock_mode: true,
  })) {
    ship30Events.push(ev);
  }

  assert.ok(ship30Events.some((e) => e.event === "status"));
  assert.ok(ship30Events.some((e) => e.event === "token"));
  assert.ok(ship30Events.some((e) => e.event === "done"));
  console.log("  ✔ Ship 30 Writer verified");

  // 3b. Test Ship 30 Writer with weak/empty evidence -> Abstention & zero artifacts
  console.log("  • Testing Ship 30 Writer (weak evidence -> abstention)...");
  const ship30AbstainEvents: any[] = [];
  for await (const ev of executeSkillStream({
    skill: "ship30_writer",
    query: "How to bake sourdough bread",
    evidence: weakEvidence,
    provider: "openai",
    mock_mode: true,
  })) {
    ship30AbstainEvents.push(ev);
  }
  assert.ok(!ship30AbstainEvents.some((e) => e.event === "artifact"), "Must NOT emit artifact on weak evidence");
  console.log("  ✔ Ship 30 Writer boundary abstention verified");

  // 4. Test Artifact Generator
  console.log("  • Testing Artifact Generator skill...");
  const artifactEvents: any[] = [];
  for await (const ev of executeSkillStream({
    skill: "artifact_generator",
    query: "Generate an HTML comparison card for PLG vs SLG",
    evidence: sampleEvidence,
    provider: "ollama",
    mock_mode: true,
  })) {
    artifactEvents.push(ev);
  }

  assert.ok(artifactEvents.some((e) => e.event === "artifact"));
  const artEvent = artifactEvents.find((e) => e.event === "artifact");
  assert.ok(artEvent && (artEvent.data as any).type === "html");
  assert.ok(typeof (artEvent.data as any).id === "string" && (artEvent.data as any).id.length > 0);
  console.log("  ✔ Artifact Generator verified");

  // 4b. Test Artifact Generator with weak/empty evidence -> Abstention & zero artifacts
  console.log("  • Testing Artifact Generator (weak evidence -> abstention)...");
  const artifactAbstainEvents: any[] = [];
  for await (const ev of executeSkillStream({
    skill: "artifact_generator",
    query: "How to bake sourdough bread",
    evidence: weakEvidence,
    provider: "openai",
    mock_mode: true,
  })) {
    artifactAbstainEvents.push(ev);
  }
  assert.ok(!artifactAbstainEvents.some((e) => e.event === "artifact"), "Must NOT emit artifact on weak evidence");
  console.log("  ✔ Artifact Generator boundary abstention verified");

  console.log("🎉 ALL AGENT SKILLS & STREAMING TESTS PASSED!");
}

runSkillTests().catch((err) => {
  console.error("❌ Skills test failure:", err);
  process.exit(1);
});

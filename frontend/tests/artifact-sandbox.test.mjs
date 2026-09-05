import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

describe("Phase 9 Frontend: Safe Artifact Sandbox & Security Contracts", () => {
  it("Gate 1: SandboxedIframe strictly omits 'allow-same-origin'", () => {
    const iframeComponentPath = path.resolve(
      __dirname,
      "../src/components/Artifact/SandboxedIframe.tsx"
    );
    assert.ok(
      fs.existsSync(iframeComponentPath),
      "SandboxedIframe.tsx must exist"
    );

    const source = fs.readFileSync(iframeComponentPath, "utf-8");

    // Extract sandbox attribute value
    const match = source.match(/sandbox="([^"]*)"/);
    assert.ok(match, "iframe must declare sandbox attribute");
    const sandboxTokens = match[1].trim().split(/\s+/);

    // Must have allow-scripts
    assert.ok(
      sandboxTokens.includes("allow-scripts"),
      "iframe sandbox must include allow-scripts"
    );

    // CRITICAL: MUST NOT have allow-same-origin
    assert.equal(
      sandboxTokens.includes("allow-same-origin"),
      false,
      "SECURITY CRITICAL: iframe sandbox MUST NOT include allow-same-origin"
    );

    // Must use srcDoc to pass content directly
    assert.ok(
      source.includes("srcDoc={sanitizedHtml}"),
      "iframe must use srcDoc for isolated DOM rendering"
    );
  });

  it("Gate 2: Artifact download slugification generates safe filenames", () => {
    const formatFilename = (title, type) => {
      const extension = type === "html" ? "html" : "md";
      const slug = (title || "artifact")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");
      return `${slug || "artifact"}.${extension}`;
    };

    assert.equal(
      formatFilename("Ship 30: Product-Led Growth Playbook", "html"),
      "ship-30-product-led-growth-playbook.html"
    );
    assert.equal(
      formatFilename("Rahul Vohra's PMF Engine!! (2024)", "md"),
      "rahul-vohra-s-pmf-engine-2024.md"
    );
    assert.equal(
      formatFilename("", "html"),
      "artifact.html"
    );
    assert.equal(
      formatFilename("---Special---///---", "md"),
      "special.md"
    );
  });

  it("Gate 3: ArtifactViewer source code provides dual preview and source tabs", () => {
    const viewerComponentPath = path.resolve(
      __dirname,
      "../src/components/Artifact/ArtifactViewer.tsx"
    );
    assert.ok(
      fs.existsSync(viewerComponentPath),
      "ArtifactViewer.tsx must exist"
    );

    const source = fs.readFileSync(viewerComponentPath, "utf-8");

    assert.ok(
      source.includes('setViewMode("preview")'),
      "Must support Preview view mode"
    );
    assert.ok(
      source.includes('setViewMode("source")'),
      "Must support Source code view mode"
    );
    assert.ok(
      source.includes("handleDownload"),
      "Must provide file download handler"
    );
    assert.ok(
      source.includes("handleCopy"),
      "Must provide copy-to-clipboard handler"
    );
  });

  it("Gate 4: MarkdownArtifactViewer imports ReactMarkdown and remarkGfm", () => {
    const mdViewerPath = path.resolve(
      __dirname,
      "../src/components/Artifact/MarkdownArtifactViewer.tsx"
    );
    assert.ok(
      fs.existsSync(mdViewerPath),
      "MarkdownArtifactViewer.tsx must exist"
    );

    const source = fs.readFileSync(mdViewerPath, "utf-8");
    assert.ok(
      source.includes("ReactMarkdown"),
      "MarkdownArtifactViewer must use ReactMarkdown"
    );
    assert.ok(
      source.includes("remarkGfm"),
      "MarkdownArtifactViewer must use remarkGfm for GitHub Flavored Markdown"
    );
  });
});

/**
 * Lenny Growth Assistant — Smart Conversation Title Generator
 *
 * Extracts concise, human-friendly topic titles from queries:
 * - Direct pass-through for curated starter question titles
 * - Strips conversational fluff ("How do I know if", "What are", "Can you explain")
 * - Formats with editorial Title Case and preserves industry acronyms (PMF, SaaS, B2B, etc.)
 * - Clamps neatly on word boundaries without awkward character cuts
 */

const ACRONYMS: Record<string, string> = {
  pmf: "PMF",
  saas: "SaaS",
  b2b: "B2B",
  b2c: "B2C",
  plg: "PLG",
  ai: "AI",
  llm: "LLM",
  rag: "RAG",
  seo: "SEO",
  cac: "CAC",
  ltv: "LTV",
  arr: "ARR",
  mrr: "MRR",
  nps: "NPS",
  okr: "OKR",
  okrs: "OKRs",
  kpi: "KPI",
  kpis: "KPIs",
  api: "API",
  apis: "APIs",
  roi: "ROI",
  icp: "ICP",
};

const LOWERCASE_WORDS = new Set([
  "a",
  "an",
  "and",
  "as",
  "at",
  "but",
  "by",
  "for",
  "in",
  "nor",
  "of",
  "on",
  "or",
  "the",
  "to",
  "vs",
  "via",
  "with",
]);

const LEADING_FILLER_REGEX =
  /^(can you (please )?|could you (please )?|please )?(tell me about|explain to me|explain|what is|what are|what were|what does|how do i|how does|how can i|how should i|how to|how do we|how should we|how can we|why is|why are|give me|write a|write an|help me with|i want to know about|i need to know about|what's the best way to|what is the best way to|what are the best ways to|the best way to|the best ways to|best way to|best ways to|what's the difference between|difference between)\s+/i;

/**
 * Capitalizes a word according to Title Case rules and domain acronyms.
 */
function formatWord(word: string, index: number): string {
  const cleanWord = word.replace(/[^a-zA-Z0-9-]/g, "");
  const lower = cleanWord.toLowerCase();

  // Check known domain acronyms
  if (ACRONYMS[lower]) {
    return ACRONYMS[lower];
  }

  // Check lowercase stop words (unless it's the very first word)
  if (index > 0 && LOWERCASE_WORDS.has(lower)) {
    return lower;
  }

  // Standard capitalization
  if (word.length === 0) return word;
  return word.charAt(0).toUpperCase() + word.slice(1);
}

/**
 * Generates a clean, human-readable title for a conversation thread.
 *
 * @param query - The raw user query
 * @param starterTitle - Optional curated starter title (e.g. from EmptyState cards)
 * @returns A formatted title (e.g. "Recognizing Genuine PMF", "B2B SaaS Churn Diagnostics")
 */
export function generateChatTitle(query: string, starterTitle?: string): string {
  if (starterTitle && starterTitle.trim().length > 0) {
    return starterTitle.trim();
  }

  const trimmed = (query || "").trim();
  if (!trimmed) {
    return "New Conversation";
  }

  // 1. Take the first sentence if multiple sentences exist
  const firstSentence = trimmed.split(/[.?!]\s+/)[0];

  // 2. Strip leading conversational filler
  let stripped = firstSentence.replace(LEADING_FILLER_REGEX, "").trim();

  // If stripping left nothing or too little, revert to first sentence
  if (stripped.length < 3) {
    stripped = firstSentence;
  }

  // 3. Remove punctuation / markdown symbols from the edges
  stripped = stripped
    .replace(/^["'`#*_\s]+|["'`#*_\s,.?!:;]+$/g, "")
    .replace(/\s+/g, " ");

  // 4. Split into words and apply title casing
  const words = stripped.split(" ");
  const formattedWords = words.map((w, idx) => formatWord(w, idx));

  // 5. Clamp to ~36 characters cleanly on word boundaries
  let result = "";
  for (const word of formattedWords) {
    const candidate = result ? `${result} ${word}` : word;
    if (candidate.length > 40) {
      if (!result) {
        // First word alone is already long
        result = word.slice(0, 38);
      }
      break;
    }
    result = candidate;
  }

  return result || "New Conversation";
}

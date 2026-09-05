/**
 * Lenny Growth Assistant — Node.js LLM Providers
 *
 * Provides streaming LLM drivers for OpenAI and Ollama with deterministic
 * mock fallback for offline development and testing.
 */

import { LLMProviderType, TokenUsage } from "../types.js";

export interface ProviderStreamResult {
  tokens: TokenUsage;
  costUsd: number;
}

export interface NodeLLMProvider {
  readonly provider: LLMProviderType;
  readonly model: string;
  stream(
    messages: Array<{ role: "system" | "user" | "assistant"; content: string }>,
    options?: { temperature?: number; maxTokens?: number }
  ): AsyncGenerator<string, ProviderStreamResult>;
}

export class MockNodeProvider implements NodeLLMProvider {
  public readonly provider: LLMProviderType;
  public readonly model: string;

  constructor(provider: LLMProviderType = "openai", model?: string) {
    this.provider = provider;
    this.model = model || (provider === "openai" ? "gpt-4o-mini" : "qwen2.5:1.5b");
  }

  public async *stream(
    messages: Array<{ role: "system" | "user" | "assistant"; content: string }>,
    _options?: { temperature?: number; maxTokens?: number }
  ): AsyncGenerator<string, ProviderStreamResult> {
    const userMsg = messages.find((m) => m.role === "user")?.content || "Default query";

    let mockResponse =
      `[Mock ${this.provider} / ${this.model}] Response for: ${userMsg}. ` +
      "Lenny's guests emphasize continuous user feedback, disciplined retention metrics, " +
      "and focused product execution [Episode: Rahul Vohra on PMF, 14:22].";

    if (messages.some((m) => m.content.includes("No matching podcast transcript evidence") || m.content.includes("beef bourguignon"))) {
      mockResponse =
        "I couldn't find sufficient evidence in Lenny's podcast archive to answer this reliably. " +
        "Try asking about a product or growth topic covered in the podcast transcripts.";
    } else if (messages.some((m) => m.content.includes("Ship 30"))) {
      mockResponse = `# Why Most Growth Initiatives Fail (And What Elite Teams Do Instead)

Most startup teams obsess over top-of-funnel acquisition when their product is secretly bleeding users through the floorboards.
Pumping marketing capital into a leaky bucket is the most efficient way to vaporize millions of dollars in venture funding.
The world's most resilient product organizations do not win on promotional fireworks; they win on compounding retention flywheels.

If your users do not return organically without paid re-engagement prompts, no growth hack on earth will save your company.
Retention is not merely an auxiliary optimization metric; it is the fundamental gravitational force of enterprise software value.

## The Premature Scaling Trap

Every product team eventually encounters the intoxicating illusion of traction.
Top-of-funnel numbers spike dramatically following an energetic launch or a featured press campaign, creating a surge of artificial confidence across the executive suite.
The leadership team celebrates record signups, internal dashboards light up in green, and board members send congratulatory notes.

Three months later, the cohort curves collapse toward the baseline.
The thousands of enthusiastic users who registered during the initial surge have vanished completely into thin air.
The product marketing team scrambles to buy more top-of-funnel traffic, naively hoping that higher volume will somehow offset structural product dissatisfaction.

This is the classic premature scaling trap that quietly kills promising early-stage companies.
When you scale distribution before locking down demonstrable retention, you simply accelerate the velocity at which you exhaust your addressable market.
You cannot out-market a core product retention defect.

## What True Grounding Looks Like

To build an enduring business, product leaders must replace executive intuition with empirical user behavior.
Lenny Rachitsky's long-form conversations with the technology industry's preeminent operators reveal a consistent, disciplined framework for diagnosing authentic product-market fit.

Here is what world-class product builders measure before touching a growth lever:

* **The Disappointment Benchmark:** Rahul Vohra emphasizes that asking recent users 'How would you feel if you could no longer use this product?' is the single most predictive leading indicator of survival [Episode: How Superhuman Built PMF: Rahul Vohra, 14:22]. If fewer than 40 percent of your active respondents answer 'very disappointed', stop all outbound scaling efforts immediately and dedicate your entire engineering capacity to resolving the core user friction.
* **The Asymptotic Curve:** Elena Verna highlights that product-led growth is fundamentally an architectural capability embedded into the software, not an improvised marketing trick [Episode: Product-Led Growth and B2B Flywheels: Elena Verna, 28:10]. A healthy retention curve must flatten out parallel to the x-axis over time, proving that a stable, predictable baseline of users derives permanent ongoing utility.
* **Natural Product Frequency:** Casey Winters notes that growth loops inevitably fail when teams attempt to force daily engagement mechanics onto an inherently episodic or seasonal utility [Episode: Growth Loops and Retention Mechanics: Casey Winters, 19:45]. You must align your notification cadence and re-engagement triggers with the user's authentic problem frequency rather than arbitrary internal quarterly quotas.
* **The Activation Threshold:** Brian Balfour demonstrates that activation is not merely completing an onboarding wizard, but reaching the specific behavioral milestone where users experience core value rapidly enough to establish an enduring habit [Episode: Building Systematic Growth Engines: Brian Balfour, 33:15]. Every additional step or unnecessary form field placed between registration and the core habit loop degrades your eventual cohort baseline by 15 to 20 percent.

## The Visual Architecture of an Unstoppable Flywheel

Sustainable product growth is never structured like a linear marketing funnel.
Linear funnels require continuous external capital and constant energy inputs simply to maintain their current operational velocity.
Flywheels, by contrast, store compounding kinetic energy where the output of one user's ordinary workflow directly powers the acquisition or activation of the next cohort.

Consider how high-retention software products architect their primary compounding loops:

### 1. The Trigger and Investment Loop

The loop begins when an authentic, recurring operational trigger prompts product usage.
The user executes a routine workflow that deposits structured data, personal templates, or organizational context directly into the platform.
That deposit increases the switching cost and ensures that subsequent sessions are significantly more valuable and frictionless than the first.

When a team creates a new shared board or configures an automated integration, they make the platform smarter for everyone.
Your everyday workflow investment turns directly into tomorrow's internal engagement trigger.

### 2. The Collaborative Distribution Loop

When a user extracts genuine value, their natural workflow routinely exposes the product to adjacent colleagues or external partners.
This is not artificial, spammy referral marketing offering financial incentives for contacts.
It is organic, collaborative utility where the product is inherently more powerful and complete when shared with an active collaborator or stakeholder.

Distribution becomes a natural byproduct of regular operational usage.
You acquire qualified, high-intent prospective customers at virtually zero marginal acquisition cost.

### 3. The Compounding Data Flywheel

As cohorts accumulate over successive quarters, aggregate platform usage generates proprietary data assets.
These assets enable engineering teams to personalize user workflows, optimize internal search algorithms, and proactively eliminate friction points across the journey.
The product becomes visibly faster, more intuitive, and increasingly defensible against well-funded prospective competitors.

The flywheel spins with increasing momentum as your scale increases.
Competitors attempting to replicate your feature checklist find themselves competing against an entrenched network of accumulated customer context.

## Four Fatal Mistakes That Sabotage Product Momentum

Even experienced product executives frequently stumble into recognizable operational traps.
Recognizing these recurring failure patterns early can save years of misallocated engineering resources:

* **Treating Output Metrics as Input Levers:** Revenue, Monthly Active Users, and Gross Margin are lagging outputs of past product health. Demanding that product squads 'increase monthly active users by 20 percent' produces desperate dark patterns, deceptive UI tricks, and spammy notification storms that erode long-term brand equity. Focus your team's energy obsessively on input levers, such as time-to-first-value and completion of the primary activation milestone.
* **Ignoring the Core Disappointed Segment:** When analyzing qualitative user research, never dilute your insights by averaging feedback across disengaged tire-kickers and committed power users. Filter your qualitative inquiries strictly to the cohort who stated they would be 'very disappointed' if your product vanished tomorrow, and build capabilities tailored specifically to expanding their highest-leverage workflows.
* **Accumulating Unprincipled Feature Bloat:** Adding secondary tabs, complex settings panels, and peripheral features is the easiest way for teams to create the optical illusion of progress while masking a stagnant retention curve. Elite product organizations ruthlessly deprecate and prune secondary capabilities that distract from the primary value loop.
* **Decoupling Product Strategy from Distribution:** A technically brilliant piece of software with no built-in distribution engine will lose every single time to an average product with an organic distribution advantage. Product architecture and go-to-market channels must be conceptualized as mutually reinforcing halves of a single cohesive operating system.

## The 5-Step Monday Morning Playbook

Transforming your organization from an exhausting acquisition treadmill into an enduring, compounding growth engine requires disciplined operational execution.
Here is your concrete 5-step implementation checklist for the upcoming operating week:

1. **Deploy the PMF Disappointment Survey:** Survey users who signed up between 14 and 30 days ago and have logged in at least twice. Calculate your exact percentage of 'very disappointed' responses to establish your true baseline.
2. **Isolate Your High-Value Power Cohort:** Cross-reference your most loyal respondents with behavioral analytics to identify the exact three actions they took during their first 48 hours in the product.
3. **Strip Friction from the Activation Path:** Eliminate non-essential form fields, optional setup wizards, and email confirmation hurdles that delay the user from reaching those three critical actions.
4. **Define Your Primary Compounding Loop:** Document on a single page how an active user's regular workflow organically introduces new users or deepens existing data assets inside the organization.
5. **Establish Your Cohort Retention Dashboard:** Shift your weekly executive review from vanity signup charts to week-over-week cohort retention curves. Do not allocate incremental paid marketing capital until your baseline curve flattens consistently for three consecutive cohorts.

Enduring market leaders are never constructed on luck or marketing bravado.
They are engineered through relentless focus on customer value, ruthless subtraction of friction, and compounding loops that gather momentum over time.
Start measuring what matters, protect your core loop, and let the flywheel do the heavy lifting.`;
    } else if (messages.some((m) => m.content.includes("<artifact"))) {
      const isHtml = userMsg.toLowerCase().includes("html") || userMsg.toLowerCase().includes("card");
      const artType = isHtml ? "html" : "markdown";
      mockResponse =
        `Here is the requested artifact for: ${userMsg}.\n\n` +
        `<artifact type="${artType}" title="Framework Comparison Guide">\n` +
        (isHtml
          ? `<div class="p-6 bg-slate-900 text-white rounded-xl"><h2>PLG vs SLG</h2></div>\n`
          : `# Framework Comparison Guide\n\n| Framework | Primary Metric | Target |\n|---|---|---|\n| Superhuman PMF | Disappointed users | >= 40% |\n| Retention Curve | Cohort flattening | Month 3+ |\n`) +
        `</artifact>`;
    }

    const words = mockResponse.split(" ");
    for (let i = 0; i < words.length; i++) {
      const chunk = i === 0 ? words[i] : " " + words[i];
      yield chunk;
      await new Promise((r) => setTimeout(r, 4));
    }

    const promptTokens = messages.reduce((acc, m) => acc + m.content.split(/\s+/).length, 0);
    const completionTokens = words.length;
    const costUsd = this.provider === "openai" ? (promptTokens * 0.15 + completionTokens * 0.60) / 1_000_000 : 0.0;

    return {
      tokens: {
        prompt: promptTokens,
        completion: completionTokens,
        total: promptTokens + completionTokens,
      },
      costUsd: Math.round(costUsd * 1000000) / 1000000,
    };
  }
}

export class OpenAINodeProvider implements NodeLLMProvider {
  public readonly provider: LLMProviderType = "openai";
  public readonly model: string;
  private apiKey: string;
  private mockMode: boolean;

  constructor(apiKey?: string, model?: string, mockMode: boolean = false) {
    this.apiKey = apiKey || process.env.OPENAI_API_KEY || "";
    this.model = model || "gpt-4o-mini";
    this.mockMode = mockMode || !this.apiKey || this.apiKey.startsWith("sk-placeholder");
  }

  public async *stream(
    messages: Array<{ role: "system" | "user" | "assistant"; content: string }>,
    options?: { temperature?: number; maxTokens?: number }
  ): AsyncGenerator<string, ProviderStreamResult> {
    if (this.mockMode) {
      const mock = new MockNodeProvider("openai", this.model);
      return yield* mock.stream(messages, options);
    }

    const res = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify({
        model: this.model,
        messages,
        temperature: options?.temperature ?? 0.3,
        max_tokens: options?.maxTokens ?? 2048,
        stream: true,
      }),
    });

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`OpenAI API error (${res.status}): ${errText}`);
    }

    const reader = res.body?.getReader();
    if (!reader) throw new Error("No response body received from OpenAI");

    const decoder = new TextDecoder();
    let promptTokens = 0;
    let completionTokens = 0;
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        // Keep incomplete trailing line fragment in buffer
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith("data: ")) continue;
          const raw = trimmed.replace(/^data:\s*/, "").trim();
          if (raw === "[DONE]") break;
          try {
            const parsed = JSON.parse(raw);
            const delta = parsed.choices?.[0]?.delta?.content;
            if (delta) {
              completionTokens++;
              yield delta;
            }
          } catch {
            // Ignore parse errors on malformed lines
          }
        }
      }

      // Process any remaining complete line in buffer when stream ends
      if (buffer.trim().startsWith("data: ")) {
        const raw = buffer.trim().replace(/^data:\s*/, "").trim();
        if (raw !== "[DONE]") {
          try {
            const parsed = JSON.parse(raw);
            const delta = parsed.choices?.[0]?.delta?.content;
            if (delta) {
              completionTokens++;
              yield delta;
            }
          } catch {
            // Ignore
          }
        }
      }
    } finally {
      reader.releaseLock();
    }

    promptTokens = messages.reduce((acc, m) => acc + m.content.split(/\s+/).length, 0);
    const costUsd = (promptTokens * 0.15 + completionTokens * 0.60) / 1_000_000;

    return {
      tokens: {
        prompt: promptTokens,
        completion: completionTokens,
        total: promptTokens + completionTokens,
      },
      costUsd: Math.round(costUsd * 1000000) / 1000000,
    };
  }
}

export class OllamaNodeProvider implements NodeLLMProvider {
  public readonly provider: LLMProviderType = "ollama";
  public readonly model: string;
  private baseUrl: string;
  private mockMode: boolean;

  constructor(baseUrl?: string, model?: string, mockMode: boolean = false) {
    this.baseUrl = (baseUrl || process.env.OLLAMA_BASE_URL || "http://localhost:11434").replace(/\/$/, "");
    this.model = model || "qwen2.5:1.5b";
    this.mockMode = mockMode;
  }

  public async *stream(
    messages: Array<{ role: "system" | "user" | "assistant"; content: string }>,
    options?: { temperature?: number; maxTokens?: number }
  ): AsyncGenerator<string, ProviderStreamResult> {
    if (this.mockMode) {
      const mock = new MockNodeProvider("ollama", this.model);
      return yield* mock.stream(messages, options);
    }

    let res: Response;
    try {
      res = await fetch(`${this.baseUrl}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: this.model,
          messages,
          stream: true,
          options: {
            temperature: options?.temperature ?? 0.3,
            num_predict: options?.maxTokens ?? 2048,
          },
        }),
      });
    } catch (e: any) {
      throw new Error(`Cannot connect to local Ollama service at ${this.baseUrl}: ${e.message}`);
    }

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`Ollama service error (${res.status}): ${errText}`);
    }

    const reader = res.body?.getReader();
    if (!reader) throw new Error("No response body received from Ollama");

    const decoder = new TextDecoder();
    let promptTokens = 0;
    let completionTokens = 0;
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        // Keep incomplete trailing line fragment in buffer
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          try {
            const parsed = JSON.parse(trimmed);
            if (parsed.prompt_eval_count) promptTokens = parsed.prompt_eval_count;
            if (parsed.eval_count) completionTokens = parsed.eval_count;
            const content = parsed.message?.content;
            if (content) yield content;
          } catch {
            // Ignore parse errors on partial lines
          }
        }
      }

      // Process any remaining complete line in buffer when stream ends
      if (buffer.trim()) {
        try {
          const parsed = JSON.parse(buffer.trim());
          if (parsed.prompt_eval_count) promptTokens = parsed.prompt_eval_count;
          if (parsed.eval_count) completionTokens = parsed.eval_count;
          const content = parsed.message?.content;
          if (content) yield content;
        } catch {
          // Ignore
        }
      }
    } finally {
      reader.releaseLock();
    }

    return {
      tokens: {
        prompt: promptTokens,
        completion: completionTokens,
        total: promptTokens + completionTokens,
      },
      costUsd: 0.0,
    };
  }
}

export function getNodeProvider(
  provider: LLMProviderType = "openai",
  model?: string,
  mockMode: boolean = false
): NodeLLMProvider {
  if (provider === "openai") {
    return new OpenAINodeProvider(process.env.OPENAI_API_KEY, model, mockMode);
  } else if (provider === "ollama") {
    return new OllamaNodeProvider(process.env.OLLAMA_BASE_URL, model, mockMode);
  } else {
    throw new Error(`Unsupported provider '${provider}'. Only 'openai' and 'ollama' are permitted.`);
  }
}

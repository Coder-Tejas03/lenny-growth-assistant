# Lenny Growth Assistant — Product & UI/UX Design Specification

**Status:** Implementation Baseline  
**Version:** 1.1  
**Last Updated:** 2026-09-04

---

## 1. Purpose

This document defines the product-facing design system and interaction model for **The Lenny Growth Assistant**.

The goal is to make a technically sophisticated RAG/agent system feel like a simple, focused productivity tool for product managers and growth leaders.

The interface should allow users to:

1. Ask grounded product and growth questions.
2. Continue conversations without losing session context.
3. Understand where answers came from.
4. Generate Ship 30 for 30-style written content.
5. Generate Markdown or HTML/CSS artifacts.
6. Inspect generated artifacts beside the conversation.
7. Understand which model/provider is currently being used without needing to understand the underlying infrastructure.

The design prioritizes **clarity, trust, low cognitive load, and usefulness over visual novelty**.

---

# 2. Design Principles

## 2.1 Conversation first

The primary interaction is the user's question.

The UI should feel like a focused expert workspace rather than a dashboard full of controls.

The user should be able to open the application and immediately understand:

> "Ask a product/growth question and get a grounded answer from Lenny's Podcast."

---

## 2.2 Evidence should be visible, not hidden

Because the core product promise is grounded answers, citations are part of the product experience rather than backend metadata.

Answers should make it easy to distinguish:

```text
Answer
↓
Supporting transcript sources
```

Citations should identify the relevant episode, guest, and timestamp/topic where available.

The interface should never imply that an answer is authoritative merely because an LLM generated it.

---

## 2.3 Progressive disclosure

The user should not be forced to understand:

- embeddings
- vector search
- retrieval scores
- model APIs
- agent routing
- infrastructure

These concepts remain available through secondary UI such as source details, model information, or status indicators.

The default interface stays simple.

---

## 2.4 Artifacts are outputs, not messages

When the assistant generates an artifact, the artifact should receive its own visual workspace.

Do not dump large HTML/CSS/Markdown blocks into the chat.

Instead:

```text
Conversation                Artifact
──────────────             ──────────────
User request               Generated output
Assistant explanation  →   Live preview
                           Metadata/actions
```

This follows the assignment's requirement for a Claude Artifacts-style side-by-side experience.

---

## 2.5 Trust through explicit system states

The interface should clearly communicate when the system is:

- retrieving knowledge
- generating
- streaming
- switching models
- creating an artifact
- unable to find sufficient evidence
- experiencing an error

Avoid ambiguous states such as an empty screen or an indefinitely spinning loader.

---

# 3. Information Architecture

The application consists of four primary areas:

```text
┌──────────────────────────────────────────────────────────────┐
│ Header                                                       │
├───────────────┬──────────────────────────────┬───────────────┤
│               │                              │               │
│ Session       │       Conversation           │   Artifact    │
│ Navigation    │                              │   Viewer      │
│               │                              │               │
│               │                              │               │
│               │                              │               │
└───────────────┴──────────────────────────────┴───────────────┘
```

### Primary regions

**1. Header**

Contains:

- application identity
- current provider/model indicator
- optional settings/status affordances

**2. Session Navigation**

Contains:

- New Chat
- previous sessions
- active session indicator

**3. Chat Pane**

Contains:

- conversation history
- user messages
- assistant responses
- citations
- streaming state
- composer

**4. Artifact Pane**

Contains:

- artifact title/type
- preview
- optional source/code view
- artifact actions
- collapse/expand control

---

# 4. Primary User Flow

## 4.1 Starting a conversation

Initial state:

```text
┌──────────────────────────────────────┐
│       Lenny Growth Assistant         │
│                                      │
│  Ask a product or growth question.   │
│                                      │
│  ┌────────────────────────────────┐  │
│  │ What should I ask?             │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

The empty state should provide a concise explanation and optionally a few example prompts.

Examples:

- "How should I prioritize growth experiments?"
- "What do Lenny's guests say about finding product-market fit?"
- "What are the best ways to improve activation?"

Examples are prompts, not hardcoded product flows.

---

## 4.2 Sending a question

Sequence:

```text
User enters question
        ↓
Submit
        ↓
Retrieving transcripts...
        ↓
Evidence found
        ↓
Generating answer...
        ↓
Streaming response
        ↓
Sources displayed
```

The composer should remain visually stable during generation.

The user should have a clear indication that the request is being processed.

---

# 5. Chat Interface

## 5.1 Message hierarchy

User messages should be visually distinct from assistant messages without relying exclusively on color.

Assistant responses should prioritize:

1. readable typography
2. paragraph spacing
3. Markdown hierarchy
4. citations
5. optional follow-up actions

Avoid large decorative message bubbles that consume excessive horizontal space.

---

## 5.2 Assistant response

A typical response should look conceptually like:

```text
Assistant

The strongest recurring pattern across the relevant
episodes is ...

[explanation]

Sources
────────────────────────
Lenny's Podcast · Guest Name
Episode / timestamp

Lenny's Podcast · Guest Name
Episode / timestamp
```

Sources should remain visually subordinate to the answer while still being easy to inspect.

---

# 6. Citation Experience

Citations are a core trust mechanism.

The UI should support the backend citation format:

```text
[Episode: Guest Name, Timestamp/Topic]
```

The frontend may render this as a compact source card/chip rather than displaying the raw syntax.

Example:

```text
Sources

┌────────────────────────────────────┐
│ Lenny's Podcast                    │
│ Guest Name · 42:15                 │
│ Product discovery                  │
└────────────────────────────────────┘
```

Where a timestamp or topic is unavailable, display the available episode/guest information rather than fabricating a timestamp.

---

# 7. Insufficient-Evidence State

This is one of the most important trust states.

If retrieval does not produce sufficiently relevant transcript evidence, the interface should not display a confident generated answer.

Instead:

```text
I couldn't find sufficient information in
Lenny's podcast archive to answer this reliably.

Try asking about a product or growth topic
covered in the podcast transcripts.
```

This state should feel intentional rather than like an application error.

Do not show:

- fabricated citations
- empty source sections
- generic LLM knowledge presented as Lenny's view

---

# 8. Retrieval / Generation Status

The streaming experience should communicate progress without exposing implementation details unnecessarily.

Recommended states:

```text
Retrieving transcripts…
Generating answer…
```

During streaming:

```text
Generating answer…

The strongest pattern...
██████████████████
```

The final response replaces the transient generation state.

The UI should not expose raw embedding operations such as:

```text
Generating vector...
Running HNSW query...
```

Those are engineering details rather than useful user-facing information.

---

# 9. Model / Provider Selector

The assignment requires switching between a local Ollama model and a cloud provider. This implementation uses OpenAI as the only cloud provider because no Anthropic API credit is available.

The selected provider should therefore be visible.

Example:

```text
Model
[ Ollama · qwen2.5:1.5b · Local ▾ ]
```

or:

```text
Model
[ OpenAI · GPT-4o mini · Cloud ▾ ]
```

The selector should communicate:

- provider
- model
- local/cloud distinction where useful

The default is **OpenAI · GPT-4o mini · Cloud**. The local choice exists to demonstrate the required Ollama path on the constrained CPU-only machine; it is not presented as equivalent in quality to the cloud model. A user with stronger hardware may configure a 7B/8B Ollama model without changing application code.

### Switching behaviour

When the user changes provider:

1. update the selected configuration
2. show the new provider visibly
3. use the new provider for subsequent requests
4. do not destroy the current session
5. do not modify conversation history
6. label each newly generated message with the provider/model that produced it

The application should not imply that switching providers changes previously generated messages.

Provider fallback is intentionally manual and visible. If OpenAI is unavailable or its configured budget is exhausted, or if Ollama is unavailable, the UI keeps the selected provider, explains the failure, and lets the user choose the other provider. It must never silently send the request to a different provider.

---

# 10. Session Navigation

Users must be able to start a new chat and maintain independent session context.

The session navigation should therefore provide:

```text
+ New Chat

Recent
──────────────
Activation strategy
Growth experiments
Product discovery
```

Session titles may be generated from the first user message or assigned automatically.

The active session must be clearly indicated.

Selecting another session should load its persisted message history.

---

# 11. Composer Design

The composer is the primary input control.

It should include:

- multiline text input
- send action
- disabled/loading state
- keyboard shortcut where appropriate

During generation:

```text
[ Stop generating ]
```

may replace the send action if cancellation is implemented.

The input should not unexpectedly clear if an API or model error occurs.

---

# 12. Ship 30 for 30 Experience

Ship 30 for 30 is a distinct content-generation capability and should feel intentionally different from normal Q&A.

The user can request:

> "Turn this into a Ship 30 for 30 essay."

The assistant should generate approximately 1,250 words following the required framework:

- strong hook
- clear narrative progression
- short paragraphs
- headings
- bullets
- selective bold emphasis
- specific actionable takeaway
- transcript-grounded claims

The assignment explicitly requires this to be implemented as a dedicated skill/tool rather than merely relying on an unstructured one-off prompt.

---

# 13. Ship 30 Output Presentation

A generated essay should be rendered as a readable document rather than a raw text blob.

Recommended presentation:

```text
┌────────────────────────────────────────────┐
│ Ship 30 for 30                             │
│                                            │
│ A strong headline                          │
│                                            │
│ Hook...                                    │
│                                            │
│ ## The problem                             │
│                                            │
│ ...                                        │
│                                            │
│ ## What to do                              │
│                                            │
│ • **Step 1:** ...                          │
│ • **Step 2:** ...                          │
│                                            │
│ ## Takeaway                                │
│                                            │
└────────────────────────────────────────────┘
```

The formatting should optimize for reading and reuse.

---

# 14. Artifact Viewer

The Artifact Viewer is a first-class product area.

It should open when the assistant generates a supported artifact.

Supported artifact types:

```text
Markdown
HTML/CSS
```

The viewer should display:

- artifact title
- artifact type
- rendered content
- preview/code toggle where useful
- close/collapse action
- optional copy/download action

---

# 15. Artifact Viewer Layout

Desktop:

```text
┌────────────────────────────┬─────────────────────────────┐
│                            │                             │
│       Chat                 │        Artifact              │
│                            │                             │
│                            │     ┌───────────────────┐   │
│                            │     │                   │   │
│                            │     │     Preview       │   │
│                            │     │                   │   │
│                            │     └───────────────────┘   │
│                            │                             │
└────────────────────────────┴─────────────────────────────┘
```

The artifact pane should be collapsible so the user can return to a full-width conversation.

---

# 16. HTML Artifact Security UX

Generated HTML is untrusted.

The UI should make the isolation boundary understandable without overwhelming the user.

A small indicator such as:

```text
Sandboxed Preview
```

is sufficient.

The implementation should use the security model required by the assignment:

- sanitize generated content with DOMPurify
- render HTML/CSS inside an iframe
- use `sandbox="allow-scripts"`
- deliberately omit `allow-same-origin`

This prevents generated content from receiving normal same-origin access to the host application's cookies, storage, and DOM.

The viewer must never inject generated HTML directly into the application's primary DOM.

---

# 17. Artifact States

The viewer should support explicit states.

### Closed

No artifact pane visible.

### Opening

Artifact exists and the pane is transitioning into view.

### Generating

```text
Creating artifact…
```

### Ready

Rendered artifact visible.

### Rendering error

```text
We couldn't render this artifact.

You can view the generated source instead.
```

### Empty

No artifact has been generated for the current conversation.

---

# 18. Responsive Behaviour

The desktop design uses a two-pane workspace.

On smaller screens, the panes should not be squeezed into unusable widths.

### Desktop

```text
Chat  |  Artifact
```

### Tablet

```text
Chat  |  Artifact
```

with adjustable/collapsible artifact width.

### Mobile

Use a single primary pane:

```text
Chat
```

The Artifact Viewer becomes a full-screen or modal/drawer experience:

```text
Chat
 ↓
View Artifact
 ↓
Full-screen Artifact
```

The user should be able to return to the conversation without losing state.

---

# 19. Responsive Priorities

When screen space decreases, preserve functionality in this order:

1. conversation
2. composer
3. assistant response
4. citations
5. artifact preview
6. secondary controls

The session sidebar may collapse before the main conversation becomes constrained.

The artifact pane should collapse rather than force horizontal scrolling across the entire application.

---

# 20. Accessibility

Accessibility is a product requirement, not a final polish step.

## Keyboard navigation

All interactive controls must be keyboard accessible:

- new chat
- session selection
- provider selector
- send
- artifact controls
- close/collapse controls

Focus states must remain visible.

---

## Semantic structure

Use appropriate semantic HTML:

```text
header
nav
main
section
button
textarea
```

Do not implement interactive controls using non-semantic clickable `<div>` elements.

---

## Screen readers

Important state changes should be communicated through appropriate ARIA/live-region mechanisms.

For example:

```text
"Retrieving transcripts"
"Assistant response complete"
"Artifact generated"
```

Streaming text should not cause excessive screen-reader announcements for every token.

---

## Color

Do not rely on color alone to communicate:

- active session
- provider
- error
- loading
- citation state

Use labels, icons, text, or structural differences as supporting signals.

---

## Contrast

Text and controls must maintain sufficient contrast against their backgrounds.

Muted metadata should remain readable rather than becoming decorative low-contrast text.

---

# 21. Error UX

Errors should be actionable and human-readable.

### Model unavailable

```text
The selected model isn't available right now.

Try switching providers or check the local
Ollama service.
```

If the selected cloud provider's configured budget has been reached, use:

```text
Cloud generation is temporarily unavailable because
this demo's API budget has been reached.

Choose the local Ollama model to continue, or update
the configured budget before retrying.
```

### Database/service error

```text
We couldn't load this conversation right now.

Please try again.
```

### Retrieval failure

```text
I couldn't retrieve the transcript knowledge
needed for this answer.
```

### Artifact rendering failure

```text
The artifact was generated, but its preview
couldn't be rendered.

View source
```

Never expose stack traces, API keys, internal URLs, or raw exception messages to users.

---

# 22. Loading and Empty States

Every major asynchronous region should have an intentional state.

| Component | Empty | Loading | Error | Success |
|---|---|---|---|---|
| Sessions | New Chat prompt | Loading sessions | Retry | Session list |
| Chat | Welcome prompt | Generating | Retry message | Conversation |
| Retrieval | Hidden | Retrieving | Explain failure | Sources |
| Artifact | Closed | Generating | Source fallback | Preview |
| Provider | OpenAI cloud default / Ollama local demo | Switching | Explain unavailable or budget reached | Active provider + model |

The application should never rely on blank space to represent an asynchronous state.

---

# 23. Visual Language

The visual language should communicate:

```text
Calm
Focused
Professional
Editorial
Technical without feeling technical
```

Avoid:

- excessive gradients
- heavy glassmorphism
- excessive animation
- oversized decorative illustrations
- dashboard-like density
- excessive badges
- unnecessary shadows

The interface is fundamentally a **knowledge workspace**.

---

# 24. Typography

Typography should prioritize long-form readability because the product produces:

- detailed answers
- citations
- approximately 1,250-word essays
- Markdown artifacts

Recommended hierarchy:

```text
Application title
    ↓
Page / artifact title
    ↓
H2
    ↓
H3
    ↓
Body
    ↓
Metadata / citation
```

Body text should use comfortable line height and avoid excessively wide reading columns.

---

# 25. Motion

Animation should communicate state rather than decorate the interface.

Appropriate uses:

- artifact pane opening
- session transitions
- streaming cursor
- subtle loading indicators
- provider switching feedback

Avoid:

- long entrance animations
- continuous decorative motion
- animation that delays interaction

Respect reduced-motion preferences.

---

# 26. Design Decisions

## Decision 1 — Two-pane workspace

**Chosen:** Chat + collapsible Artifact Viewer.

**Reason:** This directly supports the assignment's artifact requirement while keeping the conversation as the primary workflow.

---

## Decision 2 — Persistent session navigation

**Chosen:** Lightweight session sidebar/navigation.

**Reason:** The assignment explicitly requires independent chat sessions and persisted conversation context.

---

## Decision 3 — Visible provider state

**Chosen:** Provider/model indicator in the interface.

**Reason:** The assignment requires model switching and explicitly asks that the selected provider be visible either in UI or configuration.

---

## Decision 4 — Sources directly below answers

**Chosen:** Compact source presentation attached to assistant responses.

**Reason:** Grounding is a core product promise. Sources should be available at the point where the claim is consumed.

---

## Decision 5 — Artifact pane instead of raw code

**Chosen:** Render generated artifacts in a dedicated viewer.

**Reason:** This is explicitly required by the assignment and creates a significantly more useful product experience than displaying generated HTML/CSS as chat text.

---

## Decision 6 — Mobile artifact drawer

**Chosen:** Convert the desktop side pane into a full-screen/drawer experience on mobile.

**Reason:** Preserves artifact usability without compromising the primary chat workflow.

---

# 27. Interaction Contract

The frontend should behave according to the following high-level state machine:

```text
                    ┌───────────────┐
                    │   New Session │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │     Idle      │
                    └───────┬───────┘
                            │ submit
                            ▼
                    ┌───────────────┐
                    │   Retrieving  │
                    └───────┬───────┘
                            │
                  ┌─────────┴─────────┐
                  │                   │
                  ▼                   ▼
             No evidence          Evidence
                  │                   │
                  ▼                   ▼
             Insufficient        Generating
                                     │
                                     ▼
                                  Streaming
                                     │
                                     ▼
                                  Complete
                                     │
                    ┌────────────────┴───────────────┐
                    │                                │
                    ▼                                ▼
              Normal answer                    Artifact created
                                                     │
                                                     ▼
                                              Artifact Viewer
```

Errors can transition from any asynchronous state into a recoverable error state.

---

# 28. Frontend Component Boundaries

The UI should be decomposed around responsibilities rather than individual visual elements.

Suggested structure:

```text
components/
├── chat/
│   ├── ChatPane
│   ├── MessageList
│   ├── MessageItem
│   ├── CitationList
│   └── Composer
│
├── sessions/
│   ├── SessionSidebar
│   └── SessionItem
│
├── model/
│   └── ModelSelector
│
├── artifact/
│   ├── ArtifactViewer
│   ├── ArtifactHeader
│   ├── ArtifactPreview
│   └── SandboxedIframe
│
└── common/
    ├── LoadingState
    ├── ErrorState
    └── EmptyState
```

Components should remain primarily presentational.

Server communication and streaming state should live in dedicated hooks/services rather than being duplicated across visual components.

---

# 29. Frontend Data States

The frontend should distinguish at least:

```text
session:
  loading | loaded | error

chat:
  idle | retrieving | generating | complete | error

artifact:
  closed | generating | ready | rendering-error

provider:
  local | cloud | switching | unavailable
```

These states should be represented explicitly rather than inferred from scattered booleans.

Avoid combinations such as:

```text
isLoading = true
isGenerating = false
hasArtifact = true
error = null
...
```

when a clearer finite-state representation is possible.

---

# 30. Manual UI Test Plan

Before delivery, manually verify:

### Conversation

- [ ] New chat creates an independent session.
- [ ] Existing session reloads correctly.
- [ ] Follow-up questions preserve context.
- [ ] Messages stream correctly.
- [ ] Long responses remain readable.

### Grounding

- [ ] Valid questions show sources.
- [ ] Sources identify episode/guest.
- [ ] Unsupported questions produce an insufficient-evidence state.
- [ ] No fabricated source is displayed.

### Model switching

- [ ] OpenAI `gpt-4o-mini` is visible as the cloud default.
- [ ] Ollama `qwen2.5:1.5b` is visible as the local demo model.
- [ ] Switching provider preserves session context.
- [ ] Unavailable provider produces a clear error.
- [ ] Reaching the configured OpenAI budget produces a clear error and does not silently change providers.
- [ ] Each response identifies the provider/model that generated it.
- [ ] A configured 7B/8B Ollama model is represented accurately if an evaluator uses stronger hardware.

### Ship 30

- [ ] Dedicated generation flow works.
- [ ] Output is approximately 1,250 words.
- [ ] Hook is visible.
- [ ] Formatting is skimmable.
- [ ] Takeaway is actionable.
- [ ] Claims remain grounded.

### Artifacts

- [ ] Markdown renders correctly.
- [ ] HTML/CSS renders correctly.
- [ ] Artifact opens beside chat.
- [ ] Artifact pane can be collapsed.
- [ ] Mobile artifact experience works.
- [ ] Generated scripts cannot access parent application state.
- [ ] Rendering failures have a source fallback.

### Accessibility

- [ ] Entire interface is keyboard navigable.
- [ ] Focus states are visible.
- [ ] Controls have accessible names.
- [ ] Loading/error states are understandable.
- [ ] Reduced-motion preferences are respected.

---

# 31. Design Success Criteria

The design is successful if an evaluator can:

1. Open the application and immediately understand what it does.
2. Ask a product/growth question without configuration.
3. See a grounded answer with understandable sources.
4. Recognize when the system does not have sufficient evidence.
5. Switch between local Ollama and cloud inference.
6. Start and revisit independent conversations.
7. Generate a Ship 30 for 30 essay.
8. Generate and inspect a Markdown/HTML artifact.
9. Understand artifact rendering as isolated/untrusted content.
10. Use the application comfortably on desktop and mobile.
11. Navigate the core workflow using only a keyboard.

The interface should make the sophistication of the underlying system **feel simple rather than exposing its complexity**.

---

# 32. Relationship to Architecture

This document defines **how the product behaves and feels**.

`architecture.md` defines **how the system is technically constructed**.

`design.md` should therefore avoid duplicating:

- database schemas
- SQL queries
- vector index configuration
- provider implementation details
- deployment infrastructure

Those belong in `architecture.md` and the subsequent implementation-level design documentation.

The three documents form a deliberate chain:

```text
PRD
 ↓
What are we building and why?
 ↓
Architecture
 ↓
How is the system structured?
 ↓
Design
 ↓
How does the user experience that system?
 ↓
Implementation
 ↓
How is it actually built?
```

This separation should be preserved throughout implementation.

# Lenny Growth Assistant — Production UI/UX Redesign Implementation Prompt

## Role

You are implementing a careful production-grade redesign of the existing **Lenny Growth Assistant** frontend.

Your objective is to make the product feel beautiful, distinctive, calm, intuitive, comfortable, and premium while preserving every existing product capability and backend contract.

The visual direction is called **Editorial Signal Desk**: an editorial reading room combined with a precise research console. It must not resemble a generic ChatGPT clone, a dashboard template, or a typical AI-generated SaaS interface.

## Non-negotiable operating rules

1. Read `README.md`, `Project-Instructions/prd.md`, `Project-Instructions/architecture.md`, `Project-Instructions/design.md`, `docs/implementation-contract.md`, and the current frontend source before editing.
2. Treat those documents as the existing product and engineering contract. They describe behavior that must remain intact; they are not permission to simplify, remove, or reinterpret functionality.
3. Make frontend presentation changes only unless a backend change is genuinely unavoidable. Do not change database schemas, API routes, request payloads, SSE event names, provider behavior, retrieval thresholds, artifact security, or persistence behavior.
4. Run the existing frontend tests and production build before making changes. Run them again after each coherent implementation batch and at the end.
5. Do not replace working behavior with mock data, placeholder handlers, fake loading states, or hard-coded demo conversations.
6. Do not silently remove controls because they look visually noisy. Reorganize them using progressive disclosure while keeping the same capability available.
7. Do not add a new UI framework or component library unless the repository already requires it. Prefer the existing React, Tailwind, Lucide, React Markdown, and DOMPurify stack.
8. Keep changes small enough to review. Explain the visual and behavioral intent before each batch of edits.
9. Do not claim completion from a successful build alone. Verify the rendered desktop and mobile experience manually.

## Existing functionality that must remain exactly intact

Preserve all of the following:

- Anonymous persistent local identity.
- Creating a new independent conversation.
- Loading and switching between persisted sessions.
- Renaming and deleting sessions.
- Optimistic user-message rendering.
- SSE streaming and the stages: connecting, retrieving, generating, streaming, completed, and error.
- Stop/cancel generation behavior.
- Grounded Q&A mode.
- Insufficient-evidence / Navigator Mode behavior.
- Expandable transcript citations with episode, guest, timestamp, excerpt, similarity, and source link where available.
- Explicit OpenAI cloud and Ollama local provider selection.
- No silent provider fallback.
- Provider/model attribution on generated assistant messages.
- Ship 30 for 30 generation mode.
- Artifact generation mode.
- Markdown artifact preview.
- Sandboxed HTML artifact preview.
- Preview/source switching.
- Copy and download actions.
- Artifact pane opening beside chat on desktop.
- Full-screen artifact experience on mobile.
- HTML isolation: preserve `sandbox="allow-scripts"`, omit `allow-same-origin`, and retain DOMPurify sanitization.
- Existing keyboard shortcuts and accessible names.

## Target visual experience

### Design thesis

The application should feel like a trusted research instrument for thinking, not like a chatbot waiting for a prompt.

Use these qualities:

- Editorial.
- Calm.
- Focused.
- Tactile but not decorative.
- Premium but not luxurious or flashy.
- Technical through precision, not through neon, gradients, or excessive badges.
- Spacious enough for long answers and essays.
- Clear enough that a first-time user immediately understands what to do.

Avoid:

- Generic centered chatbot welcome screens.
- Purple/blue AI gradients.
- Excessive green branding.
- Rounded cards around every piece of content.
- Excessive glassmorphism.
- Transparent panels that reduce contrast.
- Oversized decorative illustrations.
- Dashboard charts or fake analytics.
- Large glowing blobs.
- Excessive shadows.
- Tiny low-contrast text.
- Decorative animations that delay or distract from work.

## Files to inspect and update

The primary implementation surface is the frontend. Update these existing files as needed:

```text
frontend/src/app/layout.tsx
frontend/src/app/globals.css
frontend/tailwind.config.js
frontend/src/app/page.tsx
frontend/src/components/Layout/Header.tsx
frontend/src/components/Session/SessionList.tsx
frontend/src/components/Session/SessionItem.tsx
frontend/src/components/Chat/ChatPane.tsx
frontend/src/components/Chat/Composer.tsx
frontend/src/components/Chat/MessageItem.tsx
frontend/src/components/Chat/CitationCard.tsx
frontend/src/components/Chat/ModelSelector.tsx
frontend/src/components/Artifact/ArtifactViewer.tsx
frontend/src/components/Artifact/MarkdownArtifactViewer.tsx
frontend/src/components/Artifact/SandboxedIframe.tsx
```

You may add small presentational components under the existing component folders when that makes responsibilities clearer, for example:

```text
frontend/src/components/Common/ThemeToggle.tsx
frontend/src/components/Common/StatusIndicator.tsx
frontend/src/components/Common/EmptyState.tsx
frontend/src/components/Chat/SourceList.tsx
frontend/src/components/Artifact/ArtifactHeader.tsx
```

Do not duplicate streaming, session, API, or artifact state logic in these components. Keep network/state behavior in the existing hooks and page orchestration.

## Theme system

Implement a real dual-theme system.

### Theme behavior

- Support `system`, `dark`, and `light` preferences if this can be done without unnecessary complexity; at minimum support dark and light.
- Persist the user's choice in `localStorage`.
- Avoid a visible flash of the wrong theme where practical.
- Add a clearly accessible theme toggle in the application chrome.
- The theme must update all surfaces, text, borders, controls, inputs, menus, source cards, artifact chrome, and focus states.
- Do not use the current permanently forced `<html className="dark">` behavior.
- Ensure the theme toggle has an accessible name and keyboard support.

### Color direction

Use semantic CSS variables rather than scattering literal colors throughout JSX.

Dark theme:

```text
Canvas:          deep ink / blue-black, approximately #111417–#15191B
Raised surface:  charcoal with a subtle warm undertone
Text:            warm parchment, never harsh pure white for body copy
Muted text:      readable blue-gray / stone
Signal accent:   restrained sage-chartreuse, used for active state and confirmation
Evidence:        desaturated blue or slate-blue
Artifact:        oxidized copper / clay accent
Danger:          muted brick red
Border:          low-contrast warm graphite hairlines
```

Light theme:

```text
Canvas:          warm smoke / linen, approximately #E9E7E1–#F0EEE8
Raised surface:  soft stone / parchment, never pure white as the primary canvas
Text:            deep graphite, never pure black for normal text
Muted text:      warm slate with sufficient contrast
Signal accent:   deep sage / olive green
Evidence:        muted navy / blue-gray
Artifact:        deep copper / terracotta
Danger:          restrained dark red
Border:          warm gray hairlines
```

Do not make the light theme a white version of the dark theme. It should feel intentionally designed for comfortable reading.

Use separate semantic tokens for:

```text
--color-canvas
--color-surface
--color-surface-raised
--color-surface-hover
--color-surface-active
--color-text
--color-text-muted
--color-text-subtle
--color-border
--color-border-strong
--color-signal
--color-evidence
--color-artifact
--color-danger
--color-focus
```

Check contrast in both themes. Never communicate a state with color alone.

## Typography

Typography is a major part of the redesign because the application renders detailed answers, sources, essays, and documents.

- Use an editorial serif for major display headings and artifact titles.
- Use a highly readable humanist or neutral sans-serif for controls, navigation, metadata, and most body text.
- Use monospace only for technical provenance such as model names, timestamps, or source metadata.
- Do not use monospace for the main interface.
- Establish a clear type scale with fewer arbitrary `text-[10px]` and `text-[11px]` labels.
- Increase body copy size and line height for assistant responses and artifacts.
- Keep reading columns comfortably narrow, approximately 680–760px for long-form content.
- Use optical hierarchy, spacing, weight, and alignment—not badges everywhere—to distinguish content.
- Avoid all-caps except for small, purposeful section labels.
- Ensure typography remains comfortable at mobile widths and at browser zoom.

If using a new font, load it deliberately through the existing Next.js setup or a documented CSS strategy. Do not create a dependency or network requirement without verifying the production build.

## Iconography

- Continue using Lucide or another single coherent line-icon family.
- Use icons as semantic support, never as decoration without a label or tooltip.
- Keep stroke weight and optical size consistent.
- Do not mix emoji, filled icons, random icon libraries, and Lucide in the same control system.
- Replace emoji-heavy starter-card titles with a restrained icon plus proper text hierarchy.
- Use larger touch targets on mobile: minimum 44×44px for primary interactive controls.
- Preserve visible focus rings in both themes.

## Layout and information architecture

Preserve the four existing product areas, but make their hierarchy feel intentional:

```text
Application chrome
├── Session library
├── Conversation / reading canvas
└── Contextual artifact workspace
```

### Desktop layout

- Keep a persistent session library on the left.
- Make the sidebar approximately 248–288px wide, with a visually quiet background distinct from the main canvas.
- Keep the conversation as the visual center of gravity.
- Use a centered reading column rather than stretching text across the entire viewport.
- When an artifact is active, show the artifact pane on the right with a clear divider and adjustable-feeling proportions.
- Do not let the artifact pane crush the conversation below a usable width.
- Prefer hairline separators and tonal changes over heavy borders.
- Keep the top application chrome compact and calm.

### Empty conversation state

Replace the current oversized generic welcome treatment with a compact editorial prompt area:

- A small distinctive Lenny mark or signal icon.
- A direct invitation such as “Ask the archive.”
- One short explanation that answers are grounded in transcript evidence.
- Suggested questions presented as a curated index or two-column set of prompts, not four identical heavy cards.
- Make the suggested questions feel useful and scannable.
- Preserve their existing click behavior and prompts exactly.

### Session library

Update `SessionList.tsx` and `SessionItem.tsx`:

- Rename the visual concept from a generic sidebar to a “Library” or “Conversations” area only if that does not break existing meaning.
- Keep “New Chat” prominent, but make it feel like a primary writing/research action rather than a bright full-width SaaS button.
- Use a subtle active rail, background shift, or inset rule for the selected session. Do not rely on color alone.
- Show titles with comfortable line height and robust truncation.
- Keep rename and delete in the existing options menu.
- Ensure menus are not clipped by scroll containers.
- Make the anonymous local identity footer discreet but readable.
- Preserve loading, empty, error, retry, rename, and delete states.
- On mobile, the library should feel like a proper sheet/drawer with a clear close affordance and no accidental background interaction.

### Header

Update `Header.tsx`:

- Create a distinctive but restrained brand mark; do not use the current generic gradient sparkle treatment as the primary identity.
- Keep the product name and grounded-archive descriptor.
- Remove or visually subordinate implementation-centric labels such as “RAG v1.0” unless they are required for the demo.
- Keep backend health visible, but make it a compact status indicator with an understandable label and tooltip.
- Keep the provider/model selector visible and explicit.
- Keep the artifact toggle visible when an artifact exists.
- Add the theme toggle without overcrowding the header.
- Ensure the header remains usable on narrow mobile widths by collapsing secondary labels while retaining accessible names.

## Conversation experience

Update `ChatPane.tsx`, `MessageItem.tsx`, and `Composer.tsx`.

### Conversation canvas

- Use a calm scrollable canvas with a subtle bottom fade or scroll affordance only when useful.
- Do not force smooth scrolling on every streaming token if it causes motion sickness or prevents manual reading. Auto-scroll only when the user is already near the bottom.
- Keep the conversation column centered and readable.
- Preserve the current message order and persisted history.
- Add intentional loading, retrieval, generation, streaming, error, and empty states.

### User messages

- Keep user messages visually distinct without relying only on color.
- Use a compact tinted block or aligned editorial note rather than a large saturated green bubble.
- Preserve timestamp display.
- Keep the user message readable on both themes and mobile.

### Assistant messages

- Present assistant answers as editorial content on the canvas rather than large decorative chat bubbles.
- Use stronger heading hierarchy, comfortable paragraph spacing, readable lists, blockquotes, tables, and code blocks.
- Keep “Lenny Assistant” and provider/model attribution visible but subordinate.
- Make copy action discoverable on hover/focus and still keyboard accessible.
- Preserve Markdown rendering exactly.
- Keep insufficient-evidence responses intentional and trustworthy, using a distinct information treatment rather than a generic red error box.

### Streaming states

Represent progress with an elegant inline status treatment:

```text
Retrieving transcript evidence
Generating grounded response
Streaming response
```

- Show meaningful human-facing status text.
- Do not expose embeddings, vector indexes, or internal implementation language.
- Use a small signal animation or progress indicator, not a large spinner everywhere.
- Preserve the Stop action during generation.
- Respect `prefers-reduced-motion`.

### Composer

Update the bottom composer into a refined “query desk”:

- Keep the multiline textarea, Enter-to-send behavior, Shift+Enter newline behavior, and stop behavior.
- Keep the three modes: Grounded Q&A, Ship 30 Essay, and Artifact.
- Make mode selection feel like a compact segmented control or mode rail rather than generic pills.
- Keep the composer anchored and easy to find without covering content.
- Use a comfortable minimum height and generous internal padding.
- Use an obvious but restrained send button.
- Make the empty, focused, disabled, streaming, and error states visually distinct.
- Never clear text unexpectedly after an API or provider error. If the current behavior clears it before the request, evaluate whether the UX can preserve the draft without changing API behavior.
- On mobile, keep the composer above the safe-area inset and prevent the keyboard from hiding the send/stop action.

## Sources and citations

Update `CitationCard.tsx` and, if useful, extract a `SourceList` presentational component.

Citations are a core product promise, not secondary debug metadata.

- Use a numbered evidence treatment with a clear relationship to the assistant claim.
- Show guest, episode, timestamp/topic, and excerpt when present.
- Never fabricate missing timestamp/topic information.
- Keep similarity/relevance available through progressive disclosure; do not make it the dominant visual element.
- Preserve expandable excerpts and external source links.
- Make the expandable control a real button or an accessible disclosure pattern rather than relying on a clickable `<div>`.
- Ensure source cards work with keyboard and touch.
- Use evidence blue/slate styling consistently in both themes.
- Keep “Supporting Sources” visually subordinate to the answer but easy to inspect.
- On mobile, source cards may become a vertical list or bottom sheet, but all information and actions must remain available.

## Provider and model selector

Update `ModelSelector.tsx` without changing provider behavior.

- Keep OpenAI `gpt-4o-mini` as the visible cloud default.
- Keep Ollama `qwen2.5:1.5b` as the visible local demo option.
- Make the cloud/local distinction understandable without requiring infrastructure knowledge.
- Use a polished menu/popover with strong focus management and escape-to-close behavior.
- Show the active model clearly in compact form in the header.
- Keep descriptions and hardware-upgrade information available through progressive disclosure.
- Do not imply that switching providers changes previous messages.
- Do not silently switch providers after an error.
- Preserve the disabled state while streaming.

## Artifact workspace

Update `ArtifactViewer.tsx`, `MarkdownArtifactViewer.tsx`, and `SandboxedIframe.tsx`.

### Desktop

- Treat the artifact as a first-class contextual workspace, not a second chat pane.
- Use a quieter artifact header with title, type, security state, preview/source tabs, copy, download, and close actions.
- Make the preview feel like a document on a desk: warm, readable, and spatially distinct from the conversation.
- Avoid putting every action inside a pill or badge.
- Keep the artifact pane collapsible/closable.

### Markdown

- Improve long-form reading typography substantially.
- Use a comfortable reading measure, clear title/deck/heading hierarchy, readable lists, tables, quotes, and code.
- Use a subtle page/sheet surface within the larger artifact workspace.
- Ensure the light theme is warm and paper-like without becoming white glare.

### HTML

- Preserve the current security model exactly.
- Keep DOMPurify sanitization.
- Keep `sandbox="allow-scripts"`.
- Do not add `allow-same-origin`.
- Never inject generated HTML into the parent application DOM.
- Present the isolation state in plain language, such as “Sandboxed preview,” without overwhelming the user with security jargon.
- Preserve rendering-error and source-fallback behavior.

### Mobile

- Use a full-screen artifact view or a deliberate bottom/side sheet with a clear back/close action.
- Preserve artifact state when returning to the conversation.
- Keep preview/source, copy, and download actions available without horizontal overflow.

## Motion, blur, and glass treatment

Use motion to explain state and spatial relationships.

Allowed motion:

- Subtle artifact-pane open/close transition.
- Mobile library and artifact drawer transitions.
- Source disclosure expansion.
- Provider menu opening.
- Short streaming cursor/signal animation.
- Small status transitions.

Rules:

- Use short, interruptible transitions generally between 120ms and 240ms.
- Avoid animation that delays interaction.
- Avoid continuous decorative motion.
- Respect `prefers-reduced-motion: reduce` by disabling non-essential transitions and animated effects.
- Do not use blur as a substitute for hierarchy.
- Use translucent/glass surfaces only for floating controls or overlays, with an opaque-enough fallback and verified contrast.
- Never use heavy glassmorphism across the entire application.
- Avoid scroll-linked effects that consume performance or make reading unstable.
- If using a scroll fade, keep it subtle and ensure it does not obscure text or controls.

## Responsive behavior

Design and test these widths:

```text
Desktop: 1440px and 1280px
Tablet:  1024px and 768px
Mobile:  390px and 360px
```

### Desktop

- Persistent session library.
- Centered conversation reading column.
- Optional artifact pane to the right.
- Header controls remain visible and balanced.

### Tablet

- Keep the main conversation usable.
- Collapse or narrow the session library before constraining the conversation.
- Keep artifact preview available if it can maintain a usable width; otherwise provide a clear collapse/open action.

### Mobile

- Single primary conversation pane.
- Session library becomes a full-height sheet/drawer.
- Artifact becomes a full-screen or deliberate sheet experience.
- No horizontal page scrolling.
- Composer remains accessible above the device safe area.
- Mode selector can scroll horizontally inside its own region without moving the page.
- Header secondary labels collapse gracefully.
- Preserve citations, provider switching, artifact actions, error messages, and stop generation.
- Do not merely shrink the desktop layout.

## Accessibility requirements

- Use semantic `header`, `nav`, `main`, `section`, `button`, `textarea`, and disclosure elements appropriately.
- Replace interactive clickable `<div>` elements with semantic controls where practical, especially session items and citation disclosure.
- Every icon-only button needs an accessible name.
- Maintain visible `:focus-visible` indicators in both themes.
- Do not rely on color alone for active, provider, loading, citation, or error states.
- Ensure keyboard navigation through session selection, menus, provider selection, theme toggle, mode selection, composer, citations, artifact actions, and drawers.
- Manage focus when opening and closing mobile drawers and menus.
- Support Escape to close transient menus/drawers where appropriate.
- Use live regions for meaningful state changes such as retrieving, response complete, artifact generated, and recoverable errors.
- Do not announce every streamed token to screen readers.
- Verify text contrast for muted metadata and disabled controls.
- Respect reduced motion.
- Preserve usable hit areas on touch devices.

## Implementation sequence

Implement in small verified batches:

### Batch 1 — Baseline and token foundation

- Run existing tests/build.
- Establish semantic theme tokens in `globals.css`.
- Update Tailwind mappings if needed.
- Remove permanent dark-only assumptions from `layout.tsx`.
- Add theme preference state/toggle without disturbing application state.
- Verify both themes render without layout regressions.

### Batch 2 — Global shell and navigation

- Redesign `Header.tsx`.
- Redesign `SessionList.tsx` and `SessionItem.tsx`.
- Preserve all session actions and loading/error states.
- Verify desktop sidebar and mobile drawer.

### Batch 3 — Empty state and conversation canvas

- Redesign `ChatPane.tsx` empty state, message canvas, loading state, and streaming treatment.
- Preserve starter prompts and submission behavior.
- Verify auto-scroll does not fight manual reading.

### Batch 4 — Message, source, and composer system

- Redesign `MessageItem.tsx`, `CitationCard.tsx`, and `Composer.tsx`.
- Preserve Markdown, citations, copy, modes, keyboard shortcuts, and Stop behavior.
- Verify insufficient-evidence and provider-error states.

### Batch 5 — Provider and artifact workspace

- Redesign `ModelSelector.tsx`.
- Redesign `ArtifactViewer.tsx` and Markdown presentation.
- Preserve sandbox security and all artifact actions.
- Verify desktop split view and mobile full-screen artifact view.

### Batch 6 — Responsive/accessibility polish

- Test all target viewport sizes.
- Test keyboard-only navigation.
- Test reduced-motion mode.
- Test both themes with long responses, long session titles, expanded citations, errors, and artifacts.

## Verification requirements

Run and record:

```bash
npm --prefix frontend test
npm --prefix frontend run build
```

Also perform manual verification of:

- New chat creation.
- Session switching, renaming, and deletion.
- Long conversation reading.
- Suggested prompt submission.
- Grounded answer streaming.
- Retrieval/generation status states.
- Stop generation.
- Insufficient-evidence state.
- Citation expansion, excerpt display, timestamp display, and source link.
- OpenAI/Ollama switching.
- Provider attribution on generated messages.
- Provider unavailable and budget error states.
- Ship 30 mode.
- Artifact mode.
- Markdown preview/source switching.
- HTML preview/source switching.
- Copy and download actions.
- Sandboxed HTML isolation remains unchanged.
- Artifact close/reopen behavior.
- Mobile session drawer.
- Mobile artifact view.
- Light theme comfort and contrast.
- Dark theme contrast.
- Theme persistence after reload.
- Keyboard-only navigation.
- Visible focus states.
- Reduced-motion behavior.
- No horizontal overflow at 360px width.

## Definition of done

The redesign is complete only when:

1. The interface no longer feels like a generic AI-generated application.
2. The Editorial Signal Desk visual language is coherent across every frontend surface.
3. Light mode is warm, comfortable, and never a blank white canvas.
4. Dark mode is calm and readable without excessive neon or gradients.
5. Typography supports long answers and 1,250-word artifacts.
6. The user understands the product purpose immediately.
7. Grounding and sources are more trustworthy and easier to inspect.
8. Provider state is explicit without becoming infrastructure-heavy.
9. Artifacts feel like first-class outputs.
10. Desktop and mobile both feel intentionally designed.
11. Motion, blur, glass, icons, and scroll behavior are restrained and purposeful.
12. Existing functionality and security behavior remain intact.
13. Tests and production build pass.
14. Manual verification has been completed at desktop, tablet, and mobile widths.

Before declaring completion, provide a concise summary of changed files, preserved behaviors, tests run, manual viewport checks, accessibility checks, and any remaining limitations. Do not begin unrelated feature work after this redesign.

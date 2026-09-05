# Product Requirements Document
## Lenny Growth Assistant

**Status:** Implementation Baseline  
**Version:** 1.0  
**Purpose:** Product definition and acceptance baseline for the Oogway Labs take-home assignment

---

## 1. Product Overview

### 1.1 Description

Lenny Growth Assistant is a conversational AI assistant grounded in Lenny Rachitsky's podcast transcripts.

It enables a user to ask questions about product, growth, startups, leadership, and related topics discussed across Lenny's podcast episodes. The assistant retrieves relevant transcript evidence, answers using that evidence, and provides citations back to the originating episode and timestamp.

The assistant also supports a dedicated **Ship30-style writing workflow**, allowing users to transform ideas and source material into structured writing artifacts that can be previewed and downloaded.

The product must demonstrate that the system can combine **retrieval, grounded generation, persistent conversations, agent capabilities, and artifact generation** into a coherent product rather than functioning as a simple chatbot.

---

### 1.2 Forward Deployment Discovery Brief

**Primary user and job:** A product or growth practitioner needs to turn relevant Lenny's Podcast evidence into an answer, a decision input, or reusable written material without locating and listening to long episodes.

**Success measures:**

- **Citation accuracy:** at least 90% of a small, labelled retrieval-evaluation set cites the correct episode and supporting passage.
- **Local-demo responsiveness:** on the actual CPU-only machine, a warm Ollama request reaches its first token within four seconds for the selected 1.5B model, or the measured result and constraint are disclosed in the demo.
- **Artifact safety:** no successful test can use a generated HTML artifact to access the host application's DOM, cookies, or local storage.
- **Budget discipline:** all development and evaluation OpenAI use stays within the approximately US$4 available credit, with request/model/token telemetry available for review.

**Operating assumptions and constraints:**

- OpenAI is the only paid cloud-model provider: there are no Anthropic API credits or keys.
- `gpt-4o-mini` is the default cloud generation model to keep the implementation and demo within the available credit; `gpt-4o` remains a configuration-only option for a deliberately limited final quality check.
- OpenAI `text-embedding-3-small` is the default embedding model. Embeddings are created at ingestion time, then reused by retrieval.
- The local machine is CPU-only and cannot run a large model comfortably. The mandatory Ollama demonstration uses `qwen2.5:1.5b` (or another benchmarked model no larger than 2B parameters).
- A user with more capable hardware may select a 7B/8B Ollama model through configuration without code changes.

**Scope choices and trade-offs:** The first version uses PostgreSQL + pgvector, a single FastAPI application boundary, and a small internal Pi Coding Agent runtime rather than a separate vector store, Anthropic gateway, or large-model hosting. This keeps the system reproducible and affordable while preserving explicit provider and skill boundaries. The trade-off is that the local demonstration prioritizes feasibility over the quality of a larger local model; cloud OpenAI is the normal quality path.

**Risks:** weak retrieval can cause unsupported answers, an exhausted OpenAI budget can block cloud generation, Ollama may be unavailable or slow, and generated HTML can be unsafe. The product addresses these through evidence thresholds and abstention, budget/usage logging, visible manual provider switching, graceful errors, sanitization, and iframe isolation.

---

# 2. Problem

Lenny's podcast archive contains a large body of product and growth knowledge distributed across hundreds of long-form conversations.

A user looking for a specific insight currently has to:

- know which episode contains the relevant discussion,
- locate the relevant section,
- interpret the surrounding context,
- and manually turn the insight into something actionable.

A conversational interface can reduce this friction, but only if its answers remain grounded in the underlying source material.

### Core problem

> **How might we make Lenny's accumulated product and growth knowledge searchable, conversational, attributable, and actionable without sacrificing trust in the source material?**

---

# 3. Why This Product

The value of the product is not simply generating plausible answers.

The assistant must be able to:

1. Find relevant evidence from the transcript corpus.
2. Use that evidence when answering.
3. Show the user where the information came from.
4. Maintain context across follow-up questions.
5. Turn knowledge into useful written output when requested.

The product therefore treats **grounding and traceability as first-class requirements**, rather than relying on an LLM's pretrained knowledge of Lenny or his guests.

---

# 4. Target User

### Primary user

A product/growth practitioner who wants to quickly learn from Lenny's podcast archive and apply those insights to a practical problem.

Typical users include:

- Product managers
- Founders
- Growth practitioners
- Startup operators
- Product designers
- Candidates/researchers studying product and growth thinking

### User characteristics

The user should not need to understand:

- embeddings,
- vector databases,
- RAG,
- agents,
- or model providers.

The complexity of the underlying system must remain invisible to the user.

---

# 5. Product Objectives

### Objective 1 — Grounded knowledge access

Allow users to ask natural-language questions and receive useful answers grounded in the provided Lenny transcript corpus.

### Objective 2 — Trustworthy retrieval

Every grounded answer should make its supporting source material discoverable through citations.

### Objective 3 — Conversational continuity

Allow users to ask follow-up questions without repeatedly restating the original context.

### Objective 4 — Actionable output

Allow users to move from learning to creation through the Ship30-style writing workflow.

### Objective 5 — Production-quality AI experience

Demonstrate reliable streaming, persistence, graceful failure handling, reproducible setup, and a deployable application.

---

# 6. Core User Experience

The primary experience is a conversational workspace.

A user should be able to:

```text
Ask a question
      ↓
Receive a streamed answer
      ↓
Inspect supporting sources
      ↓
Ask a follow-up
      ↓
Request a writing artifact
      ↓
Preview / download the result
```

The interface should make the distinction between:

- the assistant's response,
- supporting evidence,
- and generated artifacts

clear to the user.

---

# 7. Functional Requirements

## FR-01 — Transcript Knowledge Base

The system shall ingest the provided Lenny podcast transcript corpus.

Transcript data shall retain sufficient metadata to identify the originating episode and relevant timestamp/context.

The system shall create searchable representations of transcript content for retrieval.

---

## FR-02 — Grounded Question Answering

The user shall be able to ask questions about the transcript corpus using natural language.

For knowledge-based questions, the assistant shall retrieve relevant transcript content before generating the answer.

Answers should prioritize information supported by retrieved evidence rather than unsupported model knowledge.

If sufficient evidence cannot be found, the assistant should communicate that limitation instead of confidently fabricating an answer.

---

## FR-03 — Source Citations

Grounded responses shall provide citations identifying the source of the supporting information.

At minimum, citations should expose:

- episode,
- relevant timestamp or transcript location,
- and enough context for the user to understand the source.

Citations should be associated with the relevant answer content rather than presented as an unrelated source dump.

---

## FR-04 — Multi-turn Conversations

The assistant shall support conversational follow-ups.

Example:

> User: What does Lenny say about product-market fit?

> Assistant: ...

> User: How would you apply that to an early-stage SaaS company?

The second question should be interpreted using the conversation context.

Conversations shall persist so that users can return to previous sessions.

---

## FR-05 — Session Persistence

The system shall persist relevant conversation state, including:

- sessions,
- a minimal anonymous user record and user metadata (for example, a generated browser/user identifier, creation time, and non-sensitive preferences),
- user messages,
- assistant responses,
- and generated artifacts where applicable.

A user shall be able to view and continue previous conversations.

---

## FR-06 — Ship30 Writing Workflow

The assistant shall support a dedicated writing capability inspired by the Ship30-style workflow described in the assignment.

The user shall be able to request transformation of ideas or retrieved knowledge into a structured piece of writing.

The writing workflow should maintain grounding when the requested content is based on the Lenny corpus.

The system should make the generated output clearly distinguishable from source material.

---

## FR-07 — Artifact Generation

The system shall support generation of a useful visual/content artifact from an appropriate user request.

The assignment requires an artifact capability capable of producing HTML/CSS-based output.

Artifacts shall be:

- previewable inside the application,
- persisted appropriately,
- and downloadable.

Generated HTML shall be rendered in a sandboxed context to reduce the risk of generated markup affecting the host application.

---

## FR-08 — Streaming

Assistant responses shall stream progressively to the user rather than appearing only after the entire generation process completes.

The UI shall communicate relevant generation states such as:

- retrieving,
- generating,
- completed,
- or failed.

---

## FR-09 — Agent Skills

The system shall expose distinct capabilities/skills for different classes of work rather than treating every request as an undifferentiated prompt.

The agent layer shall use the **Pi Coding Agent SDK**, satisfying the assignment's permitted agent-framework choice while allowing the runtime to use OpenAI cloud models and Ollama without Anthropic API usage. FastAPI remains the public backend API and durable session authority.

At minimum, the product shall support the capabilities required by the assignment for:

- grounded transcript Q&A,
- and Ship30-style writing/artifact generation.

The skill architecture should allow additional capabilities to be introduced without restructuring the entire application.

---

## FR-10 — Error Handling

The system shall gracefully handle failures including:

- unavailable model provider,
- retrieval failure,
- malformed generation,
- empty or insufficient retrieval results,
- database failure,
- and artifact-generation failure.

Failures should result in useful user-facing feedback rather than raw stack traces.

---

# 8. Retrieval & Grounding Requirements

Retrieval quality is a core product requirement because the usefulness of the assistant depends on finding the correct portions of the transcript corpus.

The system shall:

- chunk transcript content into searchable units,
- generate embeddings,
- retrieve semantically relevant chunks,
- preserve source metadata,
- and provide retrieved evidence to the answer-generation process.

The implementation shall use PostgreSQL with `pgvector` as the vector-search layer, consistent with the provided technical guidance. fileciteturn0file1

The retrieval layer should be independently testable so that retrieval quality can be evaluated separately from LLM generation.

---

# 9. Trust & Grounding Behaviour

The assistant must prefer:

> **"I couldn't find sufficient evidence in the provided transcripts."**

over:

> **an unsupported but plausible answer.**

The system should not imply that information came from a Lenny transcript when it did not.

When retrieved evidence is insufficient, the assistant should either:

1. explain that the corpus does not provide enough evidence, or
2. clearly distinguish general model knowledge from transcript-grounded information if such behaviour is intentionally supported.

---

# 10. Non-Functional Requirements

## NFR-01 — Reproducibility

A developer should be able to set up the project using the documented setup process without manually reconstructing the environment.

The project shall provide the required environment configuration and startup instructions.

---

## NFR-02 — Local Development

The system shall support local development with the required Ollama-based model path. The mandatory demonstration configuration shall use a benchmarked 1.5B–2B-parameter model (initial target: `qwen2.5:1.5b`) suitable for the CPU-only development machine.

The normal cloud configuration shall use OpenAI only: `gpt-4o-mini` for generation and `text-embedding-3-small` for embeddings. `gpt-4o` may be selected for a deliberately limited quality check, but is not the default under the available credit budget.

The implementation should remain lightweight enough to operate within the available development environment and should record model, token, and request-cost metadata needed to manage the approximately US$4 API-credit limit.

The model provider should be replaceable so that the local model does not become a hard architectural dependency.

---

## NFR-03 — Deployment

The application shall have a deployable production/demo configuration.

The architecture should support:

- hosted frontend,
- hosted backend,
- hosted PostgreSQL/pgvector,
- and a configurable LLM provider.

The mandatory Ollama demonstration path should remain reproducible locally.

Provider failure behaviour is explicit rather than silent: if the selected provider is unavailable or the OpenAI budget is exhausted, the request fails gracefully and the user may deliberately select the other configured provider. The system must not automatically pass a request to a different provider without making that change visible.

---

## NFR-04 — Maintainability

The codebase shall have clear boundaries between:

- API/application logic,
- retrieval,
- persistence,
- agent orchestration,
- model providers,
- and frontend presentation.

Implementation details shall be documented sufficiently for another engineer to understand and operate the system.

---

## NFR-05 — Security

The system shall:

- avoid exposing secrets to the frontend,
- validate externally supplied data,
- safely render generated artifacts,
- isolate generated HTML from the host application,
- and avoid executing arbitrary generated code on the host.

---

## NFR-06 — Observability & Debuggability

Failures in retrieval, model calls, persistence, and artifact generation should be diagnosable through appropriate logs and structured error information.

The system should make it possible to determine where a failed request broke down.

---

# 11. Success Criteria

The product is successful when a reviewer can:

### Knowledge

Ask a meaningful question about Lenny's content and receive a **relevant, grounded answer with useful citations**.

### Retrieval

Ask questions requiring information from different parts of the corpus and observe that the system retrieves the appropriate evidence rather than merely generating plausible answers.

### Conversation

Ask follow-up questions and receive contextually appropriate responses.

### Writing

Request a Ship30-style output and receive a coherent, useful piece of writing based on the conversation/source material.

### Artifacts

Generate an artifact, preview it safely in the application, and download it.

### Reliability

Encountering an unavailable model, weak retrieval result, or other expected failure should produce a graceful response rather than breaking the application.

### Setup

Another developer should be able to follow the repository documentation and reproduce the application locally.

### Deployment

The evaluator should be able to access a deployed version of the application and understand how the deployed system relates to the local development configuration.

---

# 12. Scope

## In Scope

- Lenny podcast transcript ingestion
- Semantic transcript retrieval
- Grounded conversational Q&A
- Source citations
- Multi-turn conversations
- Persistent sessions
- Ship30-style writing
- Artifact generation
- Artifact preview/download
- Agent Skills
- Pi Coding Agent SDK runtime configured for OpenAI and Ollama
- Streaming responses
- Ollama-based local execution
- PostgreSQL + pgvector persistence
- Automated tests
- Local reproducible setup
- Deployment
- Technical documentation
- Demo/handoff material

These capabilities correspond to the core product and engineering requirements specified by Oogway. fileciteturn0file0 fileciteturn0file1

---

# 13. Explicitly Out of Scope

Unless required to satisfy an assignment requirement, the following are intentionally not part of the first version:

- Full user authentication/authorization system
- Multi-tenant architecture
- Mobile-native applications
- Real-time collaboration
- Training or fine-tuning a foundation model
- Building a custom vector database
- Autonomous web research outside the provided knowledge corpus
- Complex enterprise observability infrastructure
- Large-scale distributed inference
- Production-scale Kubernetes infrastructure

The goal is to demonstrate a **complete, production-minded vertical slice**, not to introduce infrastructure whose complexity is unjustified by the assignment's workload.

---

# 14. Product Constraints

The implementation must respect the following constraints from the assignment:

1. The provided transcript corpus is the primary knowledge source.
2. The application must demonstrate grounded retrieval.
3. The application must use Ollama for the required local-model demonstration.
4. The system must use Pi Coding Agent SDK as its agent layer, with OpenAI as the only cloud provider and Ollama as the local provider.
5. The application must provide the required writing and artifact experiences.
6. The project must be reproducible and deployable.
7. The implementation must include appropriate documentation, testing, and demonstration material. fileciteturn0file0

---

# 15. Requirement Traceability

| Oogway requirement | Product requirement |
|---|---|
| Lenny transcript corpus | FR-01 |
| Grounded Q&A | FR-02 |
| Citations | FR-03 |
| Multi-turn chat | FR-04 |
| Persistence | FR-05 |
| Ship30-style writing | FR-06 |
| HTML/CSS artifacts | FR-07 |
| Streaming | FR-08 |
| Agent Skills | FR-09 |
| Error handling | FR-10 |
| PostgreSQL + pgvector | FR-01 / Retrieval |
| Ollama | NFR-02 |
| Cloud LLM with no Anthropic credits | NFR-02 / NFR-03 |
| Claude Agent SDK or Pi Coding Agent | FR-09 |
| Deployment | NFR-03 |
| Tests/documentation | NFR-01 / NFR-04 |
| Demo/handoff | Success Criteria |

---

# 16. Product Definition in One Sentence

> **Lenny Growth Assistant is a grounded conversational interface over Lenny Rachitsky's podcast knowledge that helps product and growth practitioners discover evidence-backed insights, explore them conversationally, and turn those insights into actionable written artifacts.**

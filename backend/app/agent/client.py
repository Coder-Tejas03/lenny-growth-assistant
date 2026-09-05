"""
Lenny Growth Assistant — Pi Agent Runtime Client & Bridge

Asynchronously executes the internal Node.js Pi Coding Agent runtime via stdio
subprocess streaming. Yields normalized Server-Sent Event (SSE) models back to
the FastAPI event loop, with transparent local Python fallback for offline resilience.
"""

import asyncio
import json
import logging
from pathlib import Path
import re
from typing import AsyncGenerator, Dict, List, Optional
import uuid

from app.agent.models import (
    AgentExecutionResult,
    AgentRequestPayload,
    AgentSkill,
    StreamEventModel,
)
from app.core.config import settings
from app.agent.skills import (
    ARTIFACT_SYSTEM_PROMPT,
    CANONICAL_ABSTENTION_MESSAGE,
    GROUNDED_QA_SYSTEM_PROMPT,
    NAVIGATOR_SYSTEM_PROMPT,
    SHIP30_SYSTEM_PROMPT,
    build_grounded_context_prompt,
    generate_mock_ship30_essay,
)
from app.providers.factory import get_llm_provider
from app.retrieval.models import Citation, EvidenceChunk

logger = logging.getLogger("lenny_assistant.agent_client")

# Locate agent-runtime relative to project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_NODE_RUNTIME = PROJECT_ROOT / "agent-runtime" / "dist" / "index.js"


class AgentRuntimeError(Exception):
    """Raised when the agent runtime fails during execution."""
    pass


class PiAgentClient:
    """
    Bridge client connecting FastAPI to the internal Node.js Pi Agent Runtime.
    """

    def __init__(
        self,
        node_runtime_path: Optional[Path] = None,
        enable_fallback: bool = True,
    ):
        self.node_runtime_path = node_runtime_path or DEFAULT_NODE_RUNTIME
        self.enable_fallback = enable_fallback

    def is_node_runtime_compiled(self) -> bool:
        """Checks if the compiled dist/index.js exists on disk."""
        return self.node_runtime_path.exists() and self.node_runtime_path.is_file()

    async def stream_skill(
        self, payload: AgentRequestPayload
    ) -> AsyncGenerator[StreamEventModel, None]:
        """
        Executes an agent skill and streams normalized StreamEventModels.
        Prefers the Node.js Pi Agent Runtime subprocess; falls back to direct
        Python provider execution if Node or the compiled runtime is missing.
        """
        if self.is_node_runtime_compiled():
            try:
                async for event in self._stream_node_subprocess(payload):
                    yield event
                return
            except Exception as e:
                logger.warning(
                    f"Node Pi runtime execution failed ({e}). Falling back to direct Python driver: {e}"
                )
                if not self.enable_fallback:
                    raise AgentRuntimeError(f"Node Pi Agent runtime failed: {e}") from e

        # Fallback to direct Python driver
        async for event in self._stream_direct_python(payload):
            yield event

    async def _stream_node_subprocess(
        self, payload: AgentRequestPayload
    ) -> AsyncGenerator[StreamEventModel, None]:
        """Executes the Node.js Pi runtime via stdin/stdout JSON streaming."""
        proc = await asyncio.create_subprocess_exec(
            "node",
            str(self.node_runtime_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        input_data = json.dumps(payload.to_node_payload()).encode("utf-8")
        if proc.stdin:
            proc.stdin.write(input_data)
            await proc.stdin.drain()
            proc.stdin.close()

        assert proc.stdout is not None
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            raw = line.decode("utf-8").strip()
            if not raw:
                continue

            try:
                parsed = json.loads(raw)
                yield StreamEventModel(event=parsed["event"], data=parsed["data"])
            except json.JSONDecodeError:
                logger.warning(f"Ignored unparseable agent stdout line: {raw}")

        return_code = await proc.wait()
        if return_code != 0:
            assert proc.stderr is not None
            stderr_out = (await proc.stderr.read()).decode("utf-8", errors="ignore")
            raise AgentRuntimeError(
                f"Node Pi Agent runtime exited with code {return_code}: {stderr_out}"
            )

    async def _stream_direct_python(
        self, payload: AgentRequestPayload
    ) -> AsyncGenerator[StreamEventModel, None]:
        """Direct Python execution of the skill in case Node runtime is bypassed."""
        provider = get_llm_provider(
            provider_name=payload.provider,
            model=payload.model,
            mock_mode=payload.mock_mode,
        )

        # 1. Grounded QA Skill
        if payload.skill == AgentSkill.GROUNDED_QA:
            yield StreamEventModel(
                event="status",
                data={"stage": "retrieving", "message": "Evaluating retrieved transcript evidence..."},
            )

            # Grounded threshold check based on configured RETRIEVAL_SIMILARITY_THRESHOLD
            sufficient_evidence = [
                e for e in payload.evidence if e.similarity >= settings.RETRIEVAL_SIMILARITY_THRESHOLD
            ]
            if not sufficient_evidence:
                # ── INTELLIGENT NAVIGATOR MODE ────────────────────────────────────
                # Instead of a cold canned message, use the LLM to guide the user
                # toward questions the corpus CAN answer.
                yield StreamEventModel(
                    event="status",
                    data={"stage": "generating", "message": "Finding related topics to guide you..."},
                )
                navigator_messages = [
                    *[{"role": m["role"], "content": m["content"]} for m in (payload.conversation_history or [])],
                    {
                        "role": "user",
                        "content": f'The user asked: "{payload.query}"\n\nNo matching podcast transcript evidence was found. Please guide them helpfully toward what the archive covers.',
                    },
                ]
                nav_content = ""
                try:
                    async for token in provider.stream_chat(
                        navigator_messages, system_prompt=NAVIGATOR_SYSTEM_PROMPT
                    ):
                        nav_content += token
                        yield StreamEventModel(event="token", data={"delta": token})
                except Exception:
                    # Hard fallback if LLM itself fails
                    fallback = (
                        "I don't have a specific match in the archive for that right now. "
                        "Try asking about product-market fit, growth loops, retention, "
                        "go-to-market strategy, or startup team building — those are well "
                        "covered in Lenny's podcast. I'm here to help you explore!"
                    )
                    nav_content = fallback
                    yield StreamEventModel(event="token", data={"delta": fallback})

                nav_meta = provider.get_last_metadata()
                yield StreamEventModel(
                    event="done",
                    data={
                        "provider": provider.provider_name,
                        "model": provider.model_name,
                        "tokens": {
                            "prompt": nav_meta.prompt_tokens if nav_meta else 10,
                            "completion": nav_meta.completion_tokens if nav_meta else len(nav_content.split()),
                            "total": nav_meta.total_tokens if nav_meta else 10 + len(nav_content.split()),
                        },
                        "cost_usd": nav_meta.cost_usd if nav_meta else 0.0,
                    },
                )
                return
                # ── END NAVIGATOR MODE ────────────────────────────────────────────

            citations = [e.to_citation() for e in sufficient_evidence]
            yield StreamEventModel(
                event="citation",
                data={"citations": [c.model_dump(mode="json") for c in citations]},
            )

            yield StreamEventModel(
                event="status",
                data={"stage": "generating", "message": "Synthesizing grounded response..."},
            )

            prompt = build_grounded_context_prompt(GROUNDED_QA_SYSTEM_PROMPT, sufficient_evidence)
            messages = [{"role": "user", "content": payload.query}]

            async for token in provider.stream_chat(messages, system_prompt=prompt):
                yield StreamEventModel(event="token", data={"delta": token})

            meta = provider.get_last_metadata()
            yield StreamEventModel(
                event="done",
                data={
                    "provider": provider.provider_name,
                    "model": provider.model_name,
                    "tokens": {
                        "prompt": meta.prompt_tokens if meta else 0,
                        "completion": meta.completion_tokens if meta else 0,
                        "total": meta.total_tokens if meta else 0,
                    },
                    "cost_usd": meta.cost_usd if meta else 0.0,
                },
            )

        # 2. Ship 30 Writer Skill
        elif payload.skill == AgentSkill.SHIP30_WRITER:
            if not payload.evidence:
                yield StreamEventModel(
                    event="status",
                    data={"stage": "generating", "message": "Finding related topics to guide you..."},
                )
                messages = [
                    {
                        "role": "user",
                        "content": f'The user requested a Ship 30 essay on: "{payload.query}"\n\nNo matching podcast transcript evidence was found in Lenny\'s archive. Please explain warmly that Ship 30 essays must be grounded in Lenny\'s podcast transcripts, describe what topics the archive covers, and suggest 3-4 specific product/growth essay topics they could request instead. Do NOT output an ungrounded essay.',
                    }
                ]
                async for token in provider.stream_chat(messages, system_prompt=NAVIGATOR_SYSTEM_PROMPT):
                    yield StreamEventModel(event="token", data={"delta": token})

                meta = provider.get_last_metadata()
                yield StreamEventModel(
                    event="done",
                    data={
                        "provider": provider.provider_name,
                        "model": provider.model_name,
                        "tokens": {
                            "prompt": meta.prompt_tokens if meta else 0,
                            "completion": meta.completion_tokens if meta else 0,
                            "total": meta.total_tokens if meta else 0,
                        },
                        "cost_usd": meta.cost_usd if meta else 0.0,
                    },
                )
                return

            yield StreamEventModel(
                event="status",
                data={"stage": "retrieving", "message": "Curating evidence for Ship 30 essay..."},
            )

            citations = [e.to_citation() for e in payload.evidence]
            if citations:
                yield StreamEventModel(
                    event="citation",
                    data={"citations": [c.model_dump(mode="json") for c in citations]},
                )

            yield StreamEventModel(
                event="status",
                data={"stage": "generating", "message": "Drafting 1,250-word Ship 30 essay with hook and bold anchors..."},
            )

            if payload.mock_mode:
                essay_text = generate_mock_ship30_essay(payload.query, payload.evidence)
                tokens = essay_text.split(" ")
                for i, word in enumerate(tokens):
                    chunk = word if i == 0 else " " + word
                    yield StreamEventModel(event="token", data={"delta": chunk})
                    await asyncio.sleep(0.001)

                art_id = str(uuid.uuid4())
                topic_title = payload.query.strip().rstrip("?.!")
                yield StreamEventModel(
                    event="artifact",
                    data={
                        "id": art_id,
                        "type": "markdown",
                        "title": f"Ship 30: {topic_title or 'Growth Strategy'}",
                        "content": essay_text,
                    },
                )

                yield StreamEventModel(
                    event="done",
                    data={
                        "provider": provider.provider_name,
                        "model": provider.model_name,
                        "tokens": {
                            "prompt": 250,
                            "completion": len(tokens),
                            "total": 250 + len(tokens),
                        },
                        "cost_usd": 0.0,
                    },
                )
                return

            prompt = build_grounded_context_prompt(SHIP30_SYSTEM_PROMPT, payload.evidence)
            messages = [
                {
                    "role": "user",
                    "content": f"Write a complete Ship 30 for 30 style essay on: '{payload.query}'. Ensure ~1,250 words and bold anchors.",
                }
            ]

            full_essay = ""
            async for token in provider.stream_chat(messages, system_prompt=prompt):
                full_essay += token
                yield StreamEventModel(event="token", data={"delta": token})

            art_id = str(uuid.uuid4())
            topic_title = payload.query.strip().rstrip("?.!")
            yield StreamEventModel(
                event="artifact",
                data={
                    "id": art_id,
                    "type": "markdown",
                    "title": f"Ship 30: {topic_title or 'Growth Strategy'}",
                    "content": full_essay,
                },
            )

            meta = provider.get_last_metadata()
            yield StreamEventModel(
                event="done",
                data={
                    "provider": provider.provider_name,
                    "model": provider.model_name,
                    "tokens": {
                        "prompt": meta.prompt_tokens if meta else 0,
                        "completion": meta.completion_tokens if meta else 0,
                        "total": meta.total_tokens if meta else 0,
                    },
                    "cost_usd": meta.cost_usd if meta else 0.0,
                },
            )

        # 3. Artifact Generator Skill
        elif payload.skill == AgentSkill.ARTIFACT_GENERATOR:
            if not payload.evidence:
                yield StreamEventModel(
                    event="status",
                    data={"stage": "generating", "message": "Finding related topics to guide you..."},
                )
                messages = [
                    {
                        "role": "user",
                        "content": f'The user requested an artifact for: "{payload.query}"\n\nNo matching podcast transcript evidence was found in Lenny\'s archive. Please explain warmly that you can only generate artifacts grounded in Lenny\'s archive, describe what topics the archive covers, and suggest 3-4 specific product/growth artifacts they could generate instead. Do NOT output an <artifact> block.',
                    }
                ]
                async for token in provider.stream_chat(messages, system_prompt=NAVIGATOR_SYSTEM_PROMPT):
                    yield StreamEventModel(event="token", data={"delta": token})

                meta = provider.get_last_metadata()
                yield StreamEventModel(
                    event="done",
                    data={
                        "provider": provider.provider_name,
                        "model": provider.model_name,
                        "tokens": {
                            "prompt": meta.prompt_tokens if meta else 0,
                            "completion": meta.completion_tokens if meta else 0,
                            "total": meta.total_tokens if meta else 0,
                        },
                        "cost_usd": meta.cost_usd if meta else 0.0,
                    },
                )
                return

            yield StreamEventModel(
                event="status",
                data={"stage": "generating", "message": "Designing structured artifact and component styles..."},
            )

            prompt = build_grounded_context_prompt(ARTIFACT_SYSTEM_PROMPT, payload.evidence)
            messages = [
                {
                    "role": "user",
                    "content": f"Generate an artifact for: '{payload.query}'. Wrap in <artifact type='...' title='...'> block.",
                }
            ]

            full_text = ""
            async for token in provider.stream_chat(messages, system_prompt=prompt):
                full_text += token
                yield StreamEventModel(event="token", data={"delta": token})

            # Tag parsing
            artifact_match = re.search(
                r'<artifact\s+type="(markdown|html)"\s+title="([^"]+)">([\s\S]*?)</artifact>',
                full_text,
                re.IGNORECASE,
            )

            if artifact_match:
                art_type = artifact_match.group(1).lower()
                art_title = artifact_match.group(2).strip()
                art_content = artifact_match.group(3).strip()
                art_id = str(uuid.uuid4())

                yield StreamEventModel(
                    event="artifact",
                    data={
                        "id": art_id,
                        "type": art_type,
                        "title": art_title,
                        "content": art_content,
                    },
                )

            meta = provider.get_last_metadata()
            yield StreamEventModel(
                event="done",
                data={
                    "provider": provider.provider_name,
                    "model": provider.model_name,
                    "tokens": {
                        "prompt": meta.prompt_tokens if meta else 0,
                        "completion": meta.completion_tokens if meta else 0,
                        "total": meta.total_tokens if meta else 0,
                    },
                    "cost_usd": meta.cost_usd if meta else 0.0,
                },
            )

    async def execute_and_accumulate(
        self, payload: AgentRequestPayload
    ) -> AgentExecutionResult:
        """Convenience method that runs the stream to completion and returns the final assembled result."""
        content_tokens: List[str] = []
        citations: List[Citation] = []
        artifact_data: Optional[Dict[str, Any]] = None
        done_data: Dict[str, Any] = {}

        async for event in self.stream_skill(payload):
            if event.event == "token":
                content_tokens.append(event.data.get("delta", ""))
            elif event.event == "citation":
                raw_cits = event.data.get("citations", [])
                for rc in raw_cits:
                    try:
                        citations.append(Citation(**rc))
                    except Exception:
                        pass
            elif event.event == "artifact":
                artifact_data = event.data
            elif event.event == "done":
                done_data = event.data

        full_content = "".join(content_tokens)
        tokens_info = done_data.get("tokens", {})

        return AgentExecutionResult(
            content=full_content,
            citations=citations,
            artifact=artifact_data,
            provider=done_data.get("provider") or payload.provider,
            model=done_data.get("model") or payload.model or ("gpt-4o-mini" if payload.provider == "openai" else "qwen2.5:1.5b"),
            tokens_prompt=tokens_info.get("prompt", 0),
            tokens_completion=tokens_info.get("completion", 0),
            cost_usd=done_data.get("cost_usd", 0.0),
        )

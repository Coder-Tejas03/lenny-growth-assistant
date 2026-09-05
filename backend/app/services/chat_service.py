"""
Lenny Growth Assistant — Grounded Chat Service Orchestrator

Coordinates session context loading, semantic transcript retrieval, specialized
Pi agent skill execution, real-time Server-Sent Event (SSE) streaming, and atomic
database persistence of assistant messages, citations, and artifacts.
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession


from app.agent.client import AgentRuntimeError, PiAgentClient
from app.agent.models import AgentRequestPayload, AgentSkill
from app.agent.skills import CANONICAL_ABSTENTION_MESSAGE
from app.core.config import settings
from app.db.models import Session
from app.db.repositories.artifact_repo import ArtifactRepository
from app.db.repositories.message_repo import MessageRepository
from app.db.repositories.session_repo import SessionRepository
from app.services.artifact_service import ArtifactService
from app.providers.base import BudgetExceededError, ProviderUnavailableError
from app.providers.openai_provider import OpenAIProvider
from app.retrieval.models import Citation, EvidenceChunk
from app.retrieval.retriever import TranscriptRetriever
from app.schemas.chat import ChatMode, ChatRequest, format_sse, format_sse_done
from app.schemas.error import (
    BudgetExceededException,
    ProviderUnavailableException,
    SessionNotFoundError,
)

logger = logging.getLogger("lenny_assistant.chat_service")


class ChatService:
    """
    Core orchestrator managing grounded chat generation and SSE event streaming.
    """

    def __init__(
        self,
        db: AsyncSession,
        retriever: Optional[TranscriptRetriever] = None,
        agent_client: Optional[PiAgentClient] = None,
    ):
        self.db = db
        self.session_repo = SessionRepository(db)
        self.message_repo = MessageRepository(db)
        self.artifact_repo = ArtifactRepository(db)
        self.retriever = retriever or TranscriptRetriever(db)
        self.agent_client = agent_client or PiAgentClient()

    async def stream_chat(
        self, request: ChatRequest
    ) -> AsyncGenerator[str, None]:
        """
        Main entry point for grounded chat streaming:
        1. Validates session existence.
        2. Persists user message to PostgreSQL.
        3. Loads multi-turn conversation history.
        4. Retrieves evidence chunks from transcript corpus.
        5. Streams SSE events (status, citation, token, artifact).
        6. Atomically commits assistant message, citations, and artifacts upon completion.
        7. Yields done event with model provenance and terminal [DONE] marker.
        8. Guarantees failed or aborted generations are rolled back and not persisted as complete.
        """
        # 1. Validate session existence
        session = await self.session_repo.get_by_id(request.session_id)
        if not session:
            logger.warning(f"Chat request submitted for nonexistent session: {request.session_id}")
            yield format_sse(
                "error",
                {
                    "code": "SESSION_NOT_FOUND",
                    "message": f"Session '{request.session_id}' does not exist.",
                },
            )
            yield format_sse_done()
            return

        # 2. Persist incoming user message immediately
        try:
            user_msg = await self.message_repo.create(
                session_id=session.id,
                role="user",
                content=request.message,
            )
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to persist user message: {e}", exc_info=True)
            yield format_sse(
                "error",
                {"code": "DATABASE_ERROR", "message": "Failed to save message to session."},
            )
            yield format_sse_done()
            return

        # 3. Load prior conversation history for multi-turn context
        history_records = await self.message_repo.list_by_session(session.id)
        conversation_history: List[Dict[str, str]] = []
        for msg in history_records:
            if msg.id != user_msg.id:  # Exclude the current message we just added
                conversation_history.append({"role": msg.role, "content": msg.content})

        # 4. Map mode to specialized AgentSkill
        if request.mode == ChatMode.SHIP30.value:
            skill = AgentSkill.SHIP30_WRITER
        elif request.mode == ChatMode.ARTIFACT.value:
            skill = AgentSkill.ARTIFACT_GENERATOR
        else:
            skill = AgentSkill.GROUNDED_QA

        # Buffers for atomic database persistence on success
        accumulated_tokens: List[str] = []
        retrieved_evidence: List[EvidenceChunk] = []
        emitted_citations: List[Dict[str, Any]] = []
        produced_artifact: Optional[Dict[str, Any]] = None
        generation_metadata: Dict[str, Any] = {
            "provider": request.provider,
            "model": request.model or ("gpt-4o-mini" if request.provider == "openai" else "qwen2.5:1.5b"),
            "tokens_prompt": 0,
            "tokens_completion": 0,
            "cost_usd": 0.0,
        }

        try:
            # 4b. Enforce budget ceiling before initiating generation
            if request.provider == "openai":
                current_spend = OpenAIProvider.get_cumulative_spend()
                if current_spend >= settings.OPENAI_BUDGET_USD:
                    raise BudgetExceededError(
                        current_spend=current_spend,
                        budget_limit=settings.OPENAI_BUDGET_USD,
                    )

            # 5. Emit initial status event
            yield format_sse(
                "status",
                {"stage": "retrieving", "message": "Searching transcript archive..."},
            )

            # 6. Execute grounded retrieval
            retrieval_result = await self.retriever.retrieve(
                query=request.message,
                top_k=settings.RETRIEVAL_TOP_K,
                similarity_threshold=settings.RETRIEVAL_SIMILARITY_THRESHOLD,
            )

            retrieved_evidence = retrieval_result.chunks

            # If evidence found, prepare citations and notify client
            if retrieval_result.citations:
                for c in retrieval_result.citations:
                    emitted_citations.append(c.model_dump(mode="json"))
                yield format_sse("citation", {"citations": emitted_citations})

            yield format_sse(
                "status",
                {"stage": "generating", "message": "Drafting grounded response..."},
            )

            # 7. Construct Agent payload
            payload = AgentRequestPayload(
                skill=skill,
                query=request.message,
                evidence=retrieved_evidence,
                conversation_history=conversation_history,
                provider=request.provider,
                model=request.model,
                mock_mode=request.mock_mode,
            )

            # 8. Stream from Pi Agent runtime
            async for event in self.agent_client.stream_skill(payload):
                if event.event == "token":
                    delta = event.data.get("delta", "")
                    accumulated_tokens.append(delta)
                    yield format_sse("token", event.data)

                elif event.event == "citation":
                    # If skill produced/refined citations (e.g. In mock/python fallback)
                    if not emitted_citations:
                        c_list = event.data.get("citations", [])
                        emitted_citations = c_list
                        yield format_sse("citation", event.data)

                elif event.event == "artifact":
                    produced_artifact = event.data
                    yield format_sse("artifact", event.data)

                elif event.event == "status":
                    yield format_sse("status", event.data)

                elif event.event == "done":
                    # Capture generation metadata
                    done_info = event.data
                    generation_metadata["provider"] = done_info.get("provider") or request.provider
                    generation_metadata["model"] = done_info.get("model") or generation_metadata["model"]
                    tokens = done_info.get("tokens", {})
                    generation_metadata["tokens_prompt"] = tokens.get("prompt", 0)
                    generation_metadata["tokens_completion"] = tokens.get("completion", len(accumulated_tokens))
                    generation_metadata["cost_usd"] = done_info.get("cost_usd", 0.0)

            # 9. Atomic Database Persistence on clean completion
            full_response_text = "".join(accumulated_tokens)
            if not full_response_text.strip():
                # Safety fallback if model generated nothing
                full_response_text = CANONICAL_ABSTENTION_MESSAGE

            # Persist assistant message
            assistant_msg = await self.message_repo.create(
                session_id=session.id,
                role="assistant",
                content=full_response_text,
                provider=generation_metadata["provider"],
                model=generation_metadata["model"],
                tokens_prompt=generation_metadata["tokens_prompt"],
                tokens_completion=generation_metadata["tokens_completion"],
                cost_usd=generation_metadata["cost_usd"],
            )

            # Persist citations junction records
            if emitted_citations:
                citations_to_persist = []
                for rank, cit in enumerate(emitted_citations, start=1):
                    chunk_id = cit.get("chunk_id")
                    if chunk_id:
                        citations_to_persist.append(
                            {
                                "chunk_id": uuid.UUID(str(chunk_id)),
                                "rank": rank,
                                "similarity": float(cit.get("similarity", 0.0)),
                            }
                        )
                if citations_to_persist:
                    await self.message_repo.add_citations(assistant_msg.id, citations_to_persist)

            # Persist artifact if produced
            if produced_artifact:
                clean_art = ArtifactService.validate_and_sanitize(
                    type=produced_artifact.get("type", "markdown"),
                    title=produced_artifact.get("title", "Generated Artifact"),
                    content=produced_artifact.get("content", ""),
                )
                raw_art_id = produced_artifact.get("id")
                art_uuid = None
                if raw_art_id:
                    try:
                        art_uuid = uuid.UUID(str(raw_art_id))
                    except (ValueError, TypeError):
                        art_uuid = uuid.uuid4()
                else:
                    art_uuid = uuid.uuid4()

                await self.artifact_repo.create(
                    id=art_uuid,
                    session_id=session.id,
                    message_id=assistant_msg.id,
                    type=clean_art["type"],
                    title=clean_art["title"],
                    content=clean_art["content"],
                    metadata=produced_artifact.get("metadata", {}),
                )

            # Update session updated_at
            session.updated_at = datetime.now(timezone.utc)
            await self.db.commit()


            # 10. Emit final done event with durable message_id and metadata
            if generation_metadata["provider"] == "openai" and generation_metadata.get("cost_usd", 0.0) > 0:
                OpenAIProvider.record_spend(generation_metadata["cost_usd"])

            done_payload = {
                "message_id": str(assistant_msg.id),
                "provider": generation_metadata["provider"],
                "model": generation_metadata["model"],
                "tokens": {
                    "prompt": generation_metadata["tokens_prompt"],
                    "completion": generation_metadata["tokens_completion"],
                },
                "cost_usd": generation_metadata["cost_usd"],
            }
            yield format_sse("done", done_payload)
            yield format_sse_done()

        except BudgetExceededError as e:
            await self.db.rollback()
            logger.warning(f"OpenAI budget exceeded during generation: {e}")
            yield format_sse(
                "error",
                {
                    "code": "BUDGET_EXCEEDED",
                    "message": "Cloud generation is temporarily unavailable because this demo's API budget has been reached. Choose the local Ollama model to continue, or update the configured budget before retrying.",
                    "details": {
                        "provider": "openai",
                        "fallback_suggested": "ollama",
                        "budget_limit": e.budget_limit,
                        "budget_exceeded": True,
                    },
                },
            )
            yield format_sse_done()

        except ProviderUnavailableError as e:
            await self.db.rollback()
            logger.warning(f"LLM provider unavailable: {e}")
            yield format_sse(
                "error",
                {
                    "code": "PROVIDER_UNAVAILABLE",
                    "message": "The selected model isn't available right now. Try switching providers or check the local Ollama service.",
                    "details": {
                        "provider": request.provider,
                        "fallback_suggested": "ollama" if request.provider == "openai" else "openai",
                        "error": str(e),
                    },
                },
            )
            yield format_sse_done()

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Unexpected failure during chat generation: {e}", exc_info=True)
            yield format_sse(
                "error",
                {
                    "code": "GENERATION_ERROR",
                    "message": f"Generation error: {str(e)}",
                    "details": {
                        "provider": request.provider,
                        "fallback_suggested": "ollama" if request.provider == "openai" else "openai",
                        "error": str(e),
                    },
                },
            )
            yield format_sse_done()

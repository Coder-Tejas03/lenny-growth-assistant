"""
Lenny Growth Assistant — Conversational Query Rewriter

Reformulates conversational follow-up questions (with pronouns, anaphora, typos,
or ellipsis) into standalone semantic search queries using conversation context.
Complies with FR-04 (Multi-turn Conversations) of docs/PRD.md.
"""

import logging
import re
from typing import Dict, List, Optional
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

REWRITE_SYSTEM_PROMPT = """You are a search query reformulator for Lenny Rachitsky's podcast transcript archive.
Given the recent conversation history and a user's follow-up question, rewrite the follow-up into a single, standalone search query that preserves all relevant context, entities, topics, and frameworks.
Fix any obvious typos (e.g., 'theu' -> 'they', 'plaform' -> 'platform').
If the follow-up question is already fully standalone and self-contained, return it unchanged.
Do NOT answer the question. Do NOT add preamble. Return ONLY the standalone search query."""


class QueryRewriter:
    """
    Contextual query reformulator for multi-turn RAG retrieval.
    """

    TASK_PATTERNS = [
        r"^(?:please\s+)?(?:create|generate|make|build|write|draft|show\s+me)\s+(?:an?\s+)?(?:interactive\s+)?(?:html|css|markdown|ui|comparison)?\s*(?:card|artifact|widget|table|diagram|checklist|rubric|dashboard|guide|essay|ship\s*30\s*(?:for\s*30)?\s*(?:essay)?|post)\s+(?:on|about|comparing|for|of)\s+",
        r"^(?:write\s+a\s+ship\s*30\s*(?:for\s*30)?\s*essay\s+(?:on|about)\s+)",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        mock_mode: bool = False,
    ):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model
        self.mock_mode = mock_mode or (not self.api_key or self.api_key.startswith("sk-placeholder"))
        self._client: Optional[AsyncOpenAI] = None

        if not self.mock_mode:
            self._client = AsyncOpenAI(api_key=self.api_key)

    @classmethod
    def strip_task_prefixes(cls, query: str) -> str:
        """
        Strips UI/task instruction noise (e.g. 'Create an interactive HTML card comparing...',
        'Write a Ship 30 essay on...') and expands acronyms like PLG / SLG for dense vector search.
        """
        cleaned = query.strip()
        for p in cls.TASK_PATTERNS:
            cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE).strip()

        # Expand high-value domain acronyms when isolated
        if re.search(r"\bplg\b", cleaned, re.IGNORECASE) and not re.search(r"product-led", cleaned, re.IGNORECASE):
            cleaned = re.sub(r"\bplg\b", "Product-Led Growth (PLG)", cleaned, flags=re.IGNORECASE)
        if re.search(r"\bslg\b", cleaned, re.IGNORECASE) and not re.search(r"sales-led", cleaned, re.IGNORECASE):
            cleaned = re.sub(r"\bslg\b", "Sales-Led Growth (SLG)", cleaned, flags=re.IGNORECASE)

        return cleaned or query.strip()

    async def rewrite_if_needed(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Rewrites conversational follow-up questions into standalone search queries.
        Strips task/UI noise and returns the cleaned query if conversation history is empty.
        """
        clean_query = query.strip()
        if not clean_query:
            return clean_query

        # Strip task/formatting prefixes for semantic retrieval
        cleaned_for_search = self.strip_task_prefixes(clean_query)

        if not conversation_history:
            # Turn 1: No conversational history needed, return stripped query
            return cleaned_for_search

        if self.mock_mode or not self._client:
            return self._mock_rewrite(cleaned_for_search, conversation_history)

        # Extract the last 2-4 conversation turns for immediate context
        recent_turns = conversation_history[-4:]
        history_text = "\n".join(
            f"{turn.get('role', 'user').capitalize()}: {turn.get('content', '')}"
            for turn in recent_turns
        )

        user_prompt = (
            f"Conversation History:\n{history_text}\n\n"
            f"Follow-up Question: {clean_query}\n\n"
            f"Standalone Search Query:"
        )

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                max_tokens=60,
                timeout=2.5,
            )
            rewritten = response.choices[0].message.content.strip()
            # Clean up quotation marks if present
            if rewritten.startswith('"') and rewritten.endswith('"'):
                rewritten = rewritten[1:-1].strip()

            if rewritten:
                logger.info(
                    f"Multi-turn query rewritten: '{clean_query}' -> '{rewritten}'"
                )
                return rewritten
            return clean_query

        except Exception as e:
            logger.warning(
                f"Query rewriting failed or timed out ({e}). Falling back to original query."
            )
            return clean_query

    @staticmethod
    def _mock_rewrite(query: str, conversation_history: List[Dict[str, str]]) -> str:
        """Heuristic mock rewrite for test suites and offline mode."""
        combined_history = " ".join(turn.get("content", "") for turn in conversation_history).lower()
        query_lower = query.lower()
        if any(pronoun in query_lower for pronoun in ["it", "this", "they", "them", "theu", "these"]):
            if "product-market fit" in combined_history or "pmf" in combined_history:
                return f"{query} for product-market fit"
            if "growth loop" in combined_history:
                return f"{query.replace('theu', 'growth loops').replace('they', 'growth loops')}"
        return query


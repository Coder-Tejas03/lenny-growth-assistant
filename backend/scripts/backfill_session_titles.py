"""
Lenny Growth Assistant — Session Titles Backfill & Cleanup Script

Renames existing untitled "New Conversation" sessions based on the user's first query,
and prunes redundant empty 0-message ghost sessions.
"""

import asyncio
import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Load root .env
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(env_path)

from sqlalchemy import select, func, delete
from app.db.session import AsyncSessionLocal
from app.db.models import Session, Message, User

STARTERS = {
    "how do i know if my startup has genuine product-market fit? what signals should i look for?": "Recognizing Genuine PMF",
    "what are growth loops and how are they different from traditional marketing funnels?": "Loops vs. Traditional Funnels",
    "what are the most effective strategies for driving user retention and reducing churn according to lenny's guests?": "Driving Retention & Reducing Churn",
    "how should an early-stage startup think about running growth experiments and measuring success?": "Early Growth Experiments",
}

ACRONYMS = {
    "pmf": "PMF",
    "saas": "SaaS",
    "b2b": "B2B",
    "b2c": "B2C",
    "plg": "PLG",
    "ai": "AI",
    "llm": "LLM",
    "rag": "RAG",
    "seo": "SEO",
    "cac": "CAC",
    "ltv": "LTV",
    "arr": "ARR",
    "mrr": "MRR",
    "okr": "OKR",
    "okrs": "OKRs",
    "kpi": "KPI",
    "kpis": "KPIs",
    "api": "API",
    "apis": "APIs",
}

LOWERCASE_WORDS = {
    "a", "an", "and", "as", "at", "but", "by", "for", "in", "nor", "of", "on", "or", "the", "to", "vs", "via", "with"
}

FILLER_REGEX = re.compile(
    r"^(can you (please )?|could you (please )?|please )?(tell me about|explain to me|explain|what is|what are|what were|what does|how do i|how does|how can i|how should i|how to|how do we|how should we|how can we|why is|why are|give me|write a|write an|help me with|i want to know about|i need to know about|what's the best way to|what is the best way to|what are the best ways to|the best way to|the best ways to|best way to|best ways to|what's the difference between|difference between)\s+",
    re.IGNORECASE,
)


def generate_title_from_query(query: str) -> str:
    cleaned_lower = query.strip().lower()
    if cleaned_lower in STARTERS:
        return STARTERS[cleaned_lower]

    # First sentence
    first_sentence = re.split(r"[.?!]\s+", query.strip())[0]

    # Strip filler
    stripped = FILLER_REGEX.sub("", first_sentence).strip()
    if len(stripped) < 3:
        stripped = first_sentence

    # Remove outer punctuation
    stripped = re.sub(r'^["\'`#*_\s]+|["\'`#*_\s,.?!:;]+$', "", stripped)

    words = stripped.split()
    formatted = []
    for i, w in enumerate(words):
        clean_w = re.sub(r"[^a-zA-Z0-9-]", "", w)
        low = clean_w.lower()
        if low in ACRONYMS:
            formatted.append(ACRONYMS[low])
        elif i > 0 and low in LOWERCASE_WORDS:
            formatted.append(low)
        else:
            formatted.append(w.capitalize())

    # Clamp on word boundary to max ~38 chars
    result = ""
    for w in formatted:
        candidate = f"{result} {w}" if result else w
        if len(candidate) > 40:
            if not result:
                result = w[:38]
            break
        result = candidate

    return result or "Product & Growth Inquiry"


async def backfill():
    async with AsyncSessionLocal() as db:
        # Fetch all sessions
        stmt = select(Session).order_by(Session.created_at.asc())
        res = await db.execute(stmt)
        all_sessions = list(res.scalars().all())

        renamed_count = 0
        pruned_empty_count = 0
        user_empty_sessions = {}

        for session in all_sessions:
            # Check messages
            msg_stmt = (
                select(Message)
                .where(Message.session_id == session.id)
                .order_by(Message.created_at.asc())
            )
            msg_res = await db.execute(msg_stmt)
            messages = list(msg_res.scalars().all())

            first_user_msg = next((m for m in messages if m.role == "user"), None)

            if first_user_msg:
                if session.title in ("New Conversation", "", None):
                    new_title = generate_title_from_query(first_user_msg.content)
                    print(f"Renaming [{session.id}]: \"{session.title}\" -> \"{new_title}\"")
                    session.title = new_title
                    renamed_count += 1
            else:
                # 0 messages session
                user_id = session.user_id
                if user_id not in user_empty_sessions:
                    user_empty_sessions[user_id] = [session]
                else:
                    user_empty_sessions[user_id].append(session)

        # Prune redundant empty sessions per user (leave at most 1 empty session)
        for user_id, empty_list in user_empty_sessions.items():
            if len(empty_list) > 1:
                # Keep the newest one, delete older empty ones
                to_delete = empty_list[:-1]
                for empty_s in to_delete:
                    print(f"Pruning empty ghost session [{empty_s.id}]")
                    await db.delete(empty_s)
                    pruned_empty_count += 1

        await db.commit()
        print(f"\nCompleted backfill: {renamed_count} sessions renamed, {pruned_empty_count} redundant empty sessions pruned.")


if __name__ == "__main__":
    asyncio.run(backfill())

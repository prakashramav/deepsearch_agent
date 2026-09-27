"""
Phase 1 linear chain: question → Tavily search → LLM summarize.

This module is intentionally kept simple — a single async function that can
be driven by a background task.  Later phases will replace / extend this with
the full LangGraph state machine.
"""
from __future__ import annotations

import logging
from typing import Optional

from tavily import TavilyClient

from app.config import get_settings
from app.agents.gemini import get_gemini_client, generate_text

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Tool clients (instantiated lazily) ───────────────────────────────────────

def _get_tavily() -> TavilyClient:
    if not settings.tavily_api_key:
        raise RuntimeError("TAVILY_API_KEY is not set in .env")
    return TavilyClient(api_key=settings.tavily_api_key)


def _get_anthropic() -> Any:
    return get_gemini_client()


def _get_gemini_client() -> Any:
    return _get_anthropic()


# ── Phase 1: linear chain ─────────────────────────────────────────────────────

async def run_linear_chain(question: str) -> tuple[str, list[dict]]:
    """
    1. Search Tavily for the question.
    2. Send the top results to Claude for a structured summary.

    Returns (summary_markdown, sources_list).
    """
    import asyncio

    # Step 1 — web search (blocking SDK call, run in thread pool)
    logger.info("Phase 1 | Tavily search for: %s", question[:80])
    tavily = _get_tavily()

    loop = asyncio.get_event_loop()
    search_response = await loop.run_in_executor(
        None,
        lambda: tavily.search(
            query=question,
            search_depth="advanced",
            max_results=7,
            include_answer=True,
        ),
    )

    results = search_response.get("results", [])
    tavily_answer = search_response.get("answer", "")

    # Build a compact context string for the LLM
    context_lines = []
    if tavily_answer:
        context_lines.append(f"**Quick answer from search engine:**\n{tavily_answer}\n")

    for i, r in enumerate(results, 1):
        context_lines.append(
            f"[Source {i}] {r.get('title', 'Untitled')}\n"
            f"URL: {r.get('url', '')}\n"
            f"Snippet: {r.get('content', '')[:600]}\n"
        )

    context = "\n---\n".join(context_lines)

    # Step 2 — LLM summarisation
    logger.info("Phase 1 | LLM summarisation via Gemini")
    client = _get_gemini_client()

    system_prompt = (
        "You are an expert research analyst. Given a research question and web "
        "search results, produce a clear, well-structured Markdown summary. "
        "Include key facts, figures and insights. Cite sources inline as [1], [2] etc. "
        "End with a ## References section listing each source URL."
    )

    user_message = (
        f"## Research question\n{question}\n\n"
        f"## Search results\n{context}\n\n"
        "Please synthesise these results into a comprehensive Markdown summary."
    )

    summary = await generate_text(
        client=client,
        prompt=user_message,
        system_prompt=system_prompt,
        max_tokens=4096,
    )

    sources = [
        {
            "url": r.get("url", ""),
            "title": r.get("title", ""),
            "snippet": r.get("content", "")[:300],
            "score": r.get("score"),
        }
        for r in results
    ]

    return summary, sources

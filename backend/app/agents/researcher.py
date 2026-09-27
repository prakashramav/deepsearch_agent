"""
Phase 3 — Parallel Researcher Agent

Fans out concurrent Tavily web searches across all decomposed sub-questions
from the Planner. Collects, deduplicates by URL, scores, and structures sources.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional
from urllib.parse import urlparse

from tavily import TavilyClient

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_tavily() -> TavilyClient:
    if not settings.tavily_api_key:
        raise RuntimeError("TAVILY_API_KEY is not set in .env")
    return TavilyClient(api_key=settings.tavily_api_key)


def _normalize_url(url: str) -> str:
    """Strip trailing slashes, fragments, and common query trackers for deduplication."""
    parsed = urlparse(url)
    clean_netloc = parsed.netloc.lower()
    clean_path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{clean_netloc}{clean_path}"


async def search_sub_question(
    sub_q: dict[str, Any] | str,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """
    Search Tavily for a single sub-question.
    Returns a list of normalized source dictionaries tagged with sub_question context.
    """
    if isinstance(sub_q, str):
        query_text = sub_q
        focus_area = ""
    else:
        query_text = sub_q.get("question", "")
        focus_area = sub_q.get("focus_area", "")

    if not query_text.strip():
        return []

    tavily = _get_tavily()
    loop = asyncio.get_event_loop()

    logger.info("Researcher searching sub-question: %.80s", query_text)

    try:
        response = await loop.run_in_executor(
            None,
            lambda: tavily.search(
                query=query_text,
                search_depth="advanced",
                max_results=max_results,
                include_answer=True,
            ),
        )
    except Exception as exc:
        logger.warning("Search failed for sub-question '%s': %s", query_text[:50], exc)
        return []

    results = response.get("results", [])
    sources: list[dict[str, Any]] = []

    for item in results:
        url = item.get("url", "").strip()
        if not url:
            continue
        sources.append(
            {
                "url": url,
                "title": item.get("title") or "Untitled Source",
                "snippet": item.get("content", "")[:600],
                "score": float(item.get("score") or 0.0),
                "sub_question": query_text,
                "focus_area": focus_area,
            }
        )

    return sources


async def run_parallel_research(
    sub_questions: list[dict[str, Any]] | list[str],
    max_concurrency: int = 4,
    max_results_per_subq: int = 5,
) -> list[dict[str, Any]]:
    """
    Fan out research across all sub-questions concurrently using an asyncio Semaphore.
    Deduplicates results by canonical URL (keeping the highest relevance score).
    """
    if not sub_questions:
        logger.warning("run_parallel_research called with empty sub_questions list")
        return []

    semaphore = asyncio.Semaphore(max_concurrency)

    async def _bounded_search(sq: dict[str, Any] | str) -> list[dict[str, Any]]:
        async with semaphore:
            try:
                return await search_sub_question(sq, max_results=max_results_per_subq)
            except Exception as exc:
                logger.error("Unexpected error searching sub-question %s: %s", sq, exc)
                return []

    # Fan out in parallel
    tasks = [_bounded_search(sq) for sq in sub_questions]
    search_results_groups = await asyncio.gather(*tasks, return_exceptions=False)

    # Deduplicate by normalized URL
    seen_urls: dict[str, dict[str, Any]] = {}

    for group in search_results_groups:
        for source in group:
            norm_url = _normalize_url(source["url"])
            if norm_url not in seen_urls:
                seen_urls[norm_url] = source
            else:
                # If seen before, keep the one with higher relevance score
                existing = seen_urls[norm_url]
                if (source.get("score") or 0) > (existing.get("score") or 0):
                    seen_urls[norm_url] = source

    deduped_sources = list(seen_urls.values())

    # Sort descending by relevance score
    deduped_sources.sort(key=lambda s: s.get("score") or 0.0, reverse=True)

    logger.info(
        "Parallel research complete: %d unique sources collected across %d sub-questions",
        len(deduped_sources),
        len(sub_questions),
    )
    return deduped_sources

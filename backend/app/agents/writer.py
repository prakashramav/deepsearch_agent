"""
Phase 6 — Writer Agent

Drafts the complete, publication-grade research report in structured Markdown,
integrating the Analyst's insights, fact-checked claims, comparison tables, and citations.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import get_settings
from app.agents.gemini import get_gemini_client, generate_text

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_anthropic() -> Any:
    return get_gemini_client()


def _get_gemini_client() -> Any:
    return _get_anthropic()


_SYSTEM_PROMPT = """You are an executive research report writer and technical author.
Draft a comprehensive, authoritative, publication-quality research report in GitHub-flavored Markdown.

Structure requirements:
1. # <Compelling & Descriptive Report Title>
2. ## Executive Summary: A high-impact synthesis of the core findings.
3. Dedicated deep-dive sections addressing each core focus area / sub-question.
4. Comparative Analysis: Include at least one rich Markdown comparison table (e.g. comparing key players, technologies, or pricing tiers).
5. Fact-Checked Key Metrics: Highlight verified statistics and address any contested data points.
6. Strategic Implications & Forward Outlook.
7. In-text citation requirement: Every factual assertion MUST cite its source as [1], [2], etc., matching the provided numbered source list.
"""


async def draft_report(
    question: str,
    plan: dict[str, Any] | None,
    analysis: str,
    verified_claims: list[dict[str, Any]],
    sources: list[dict[str, Any]],
) -> str:
    """
    Draft the comprehensive research report in Markdown.
    """
    if not sources:
        return f"# Research Report: {question}\n\nNo source data was available to draft this report."

    # Build numbered source reference list for the prompt
    source_items = []
    for i, s in enumerate(sources, 1):
        source_items.append(
            f"[{i}] {s.get('title', 'Untitled')}\n"
            f"    URL: {s.get('url', '')}\n"
            f"    Excerpt: {s.get('snippet', '')[:350]}"
        )
    sources_text = "\n".join(source_items)

    claims_summary = "\n".join(
        f"- {c.get('claim_text')} (Source: {c.get('source_url')})"
        for c in verified_claims[:10]
    )

    sub_questions_text = ""
    if plan and plan.get("sub_questions"):
        sub_questions_text = "\n".join(
            f"- {sq.get('focus_area', 'Topic')}: {sq.get('question')}"
            for sq in plan["sub_questions"]
        )

    user_prompt = (
        f"## Original Research Question\n{question}\n\n"
        f"## Planned Research Scope\n{sub_questions_text}\n\n"
        f"## Strategic Analyst Findings\n{analysis}\n\n"
        f"## Verified Claims\n{claims_summary}\n\n"
        f"## Source Catalog ({len(sources)} available sources):\n{sources_text}\n\n"
        "Draft the complete, in-depth Markdown research report with inline citations [1], [2], etc."
    )

    client = _get_gemini_client()

    try:
        logger.info("Writer drafting report for: %.60s", question)
        return await generate_text(
            client=client,
            prompt=user_prompt,
            system_prompt=_SYSTEM_PROMPT,
            max_tokens=4096,
        )
    except Exception as exc:
        logger.warning("Writer LLM failed: %s, generating structured fallback report", exc)
        return _fallback_report(question, analysis, sources)


def _fallback_report(question: str, analysis: str, sources: list[dict[str, Any]]) -> str:
    """Generates structured report if LLM drafting fails."""
    sections = [
        f"# Research Report: {question}\n",
        "## Executive Summary",
        f"This report presents research findings on **{question}**.",
        "\n## Strategic Analysis",
        analysis,
        "\n## References",
    ]
    for i, s in enumerate(sources, 1):
        sections.append(f"{i}. [{s.get('title')}]({s.get('url')})")
    return "\n".join(sections)

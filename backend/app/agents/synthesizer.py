"""
Phase 3 Synthesis — Synthesizes research findings from parallel sources into a cohesive cited report.
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


async def synthesize_report(
    question: str,
    plan: dict[str, Any] | None,
    sources: list[dict[str, Any]],
) -> str:
    """
    Synthesize research findings into a comprehensive cited Markdown report
    based on the research plan and deduplicated parallel sources.
    """
    if not sources:
        return f"# Research Report: {question}\n\nNo sources could be retrieved for this research topic."

    loop = asyncio.get_event_loop()
    client = _get_anthropic()

    # Format context with numbered source citations
    context_lines = []
    for i, s in enumerate(sources, 1):
        sub_q_tag = f" (Focus: {s.get('focus_area')})" if s.get("focus_area") else ""
        context_lines.append(
            f"[{i}] {s.get('title', 'Untitled')}{sub_q_tag}\n"
            f"URL: {s.get('url', '')}\n"
            f"Snippet: {s.get('snippet', '')}\n"
        )

    context = "\n---\n".join(context_lines)

    strategy_note = ""
    if plan and plan.get("research_strategy"):
        strategy_note = f"\nStrategy employed: {plan.get('research_strategy')}\n"

    system_prompt = (
        "You are an expert lead research analyst. Synthesize the provided multi-angle web research "
        "findings into an authoritative, in-depth Markdown research report.\n\n"
        "Guidelines:\n"
        "- Structure with clear headings, executive summary, analytical comparison, and key takeaways.\n"
        "- Extract hard figures, data points, and technical specifications where available.\n"
        "- Cite sources inline as [1], [2], etc., matching the exact source numbers provided.\n"
        "- End with a comprehensive '## References' section listing each cited URL and title.\n"
    )

    user_message = (
        f"## Main Research Question\n{question}\n{strategy_note}\n"
        f"## Collected Sources ({len(sources)} unique sources)\n\n"
        f"{context}\n\n"
        "Please generate the complete, cited research report now."
    )

    try:
        return await generate_text(
            client=client,
            prompt=user_message,
            system_prompt=system_prompt,
            max_tokens=4096,
        )
    except Exception as exc:
        logger.exception("Synthesizer failed: %s", exc)
        # Fallback summary
        fallback_lines = [
            f"# Research Report: {question}\n",
            "*(Synthesizer encountered an issue; displaying compiled raw findings)*\n",
        ]
        for i, s in enumerate(sources, 1):
            fallback_lines.append(f"### [{i}] {s.get('title')}\n- **URL**: {s.get('url')}\n- {s.get('snippet')}\n")
        return "\n".join(fallback_lines)

"""
Phase 6 — Analyst Agent

Synthesizes findings, identifies overarching market/technology trends,
constructs comparative frameworks, and evaluates trade-offs and conflicts.
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


_SYSTEM_PROMPT = """You are a senior strategic research analyst.
Your job is to transform raw factual claims and source data into deep analytical insights, structured comparisons, and trend evaluations.

Your analysis must:
1. Identify 3–5 macro trends and driving forces.
2. Formulate a structured comparative assessment (e.g. comparing major players, technologies, or approaches across pricing, market share, and technical specifications).
3. Directly evaluate any conflicting or contested data points, explaining why different sources report diverging numbers.
4. Provide forward-looking strategic implications.

Format your output in clean Markdown with clear headings and bullet points."""


async def analyze_research(
    question: str,
    plan: dict[str, Any] | None,
    verified_claims: list[dict[str, Any]],
    sources: list[dict[str, Any]],
) -> str:
    """
    Produce an analytical synthesis of verified claims and source findings.
    """
    if not verified_claims and not sources:
        return "Insufficient research data available for in-depth analysis."

    # Format claims by verification status
    claims_lines = []
    for i, c in enumerate(verified_claims, 1):
        status = "VERIFIED" if c.get("verified") else ("CONFLICT" if c.get("conflict_flag") else "UNVERIFIED")
        notes = f" ({c.get('verification_notes')})" if c.get("verification_notes") else ""
        claims_lines.append(f"- [{status}] Claim {i}: {c.get('claim_text')}{notes}")
    claims_text = "\n".join(claims_lines)

    strategy = plan.get("research_strategy", "") if plan else ""
    domain = plan.get("domain", "General Research") if plan else "General Research"

    user_prompt = (
        f"Research Question: {question}\n"
        f"Domain: {domain}\n"
        f"Strategy: {strategy}\n\n"
        f"Verified Claims & Fact-Check Audit:\n{claims_text}\n\n"
        f"Number of Unique Sources Analyzed: {len(sources)}\n\n"
        "Generate a rigorous strategic analysis."
    )

    client = _get_gemini_client()

    try:
        logger.info("Analyst generating strategic analysis for: %.60s", question)
        return await generate_text(
            client=client,
            prompt=user_prompt,
            system_prompt=_SYSTEM_PROMPT,
            max_tokens=2500,
        )
    except Exception as exc:
        logger.warning("Analyst failed: %s, using fallback synthesis", exc)
        return _fallback_analysis(question, verified_claims)


def _fallback_analysis(question: str, claims: list[dict[str, Any]]) -> str:
    """Fallback rule-based analysis if LLM fails."""
    lines = [
        f"### Strategic Analysis Summary for: {question}",
        "\n#### Key Verified Findings:",
    ]
    verified = [c for c in claims if c.get("verified")]
    conflicts = [c for c in claims if c.get("conflict_flag")]

    for c in verified[:5]:
        lines.append(f"- **Confirmed**: {c.get('claim_text')}")

    if conflicts:
        lines.append("\n#### Contested Points / Divergent Data:")
        for c in conflicts[:3]:
            lines.append(f"- **Discrepancy**: {c.get('claim_text')} — {c.get('verification_notes')}")

    return "\n".join(lines)

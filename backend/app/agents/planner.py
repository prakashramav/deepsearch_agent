"""
Phase 2 — Planner Agent

Given a research question, uses Claude to decompose it into 3–6 concrete
sub-questions with focus areas. Returns structured JSON so the rest of the
pipeline knows exactly what to research.

This module is independently testable: feed it a fixed question, assert on
the shape of the output dict — no LLM variability in unit tests (mock the
client).
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import TypedDict

from app.config import get_settings
from app.agents.gemini import get_gemini_client, generate_text

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Output schema ─────────────────────────────────────────────────────────────

class SubQuestion(TypedDict):
    id: int
    question: str
    focus_area: str


class ResearchPlan(TypedDict):
    sub_questions: list[SubQuestion]
    research_strategy: str
    estimated_sources_needed: int
    domain: str


# ── Planner prompt ────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are an expert research strategist. Your job is to
decompose a complex research question into 3–6 focused sub-questions that,
when answered together, will comprehensively address the original question.

Each sub-question should:
- Be specific and answerable via web search
- Cover a distinct angle (e.g., market data, technical specs, competitive
  landscape, trends, regulatory factors, key players)
- Not overlap significantly with the others

Respond ONLY with valid JSON matching exactly this schema — no prose, no
markdown fences:
{
  "sub_questions": [
    {"id": 1, "question": "<specific sub-question>", "focus_area": "<e.g. Market Size & Players>"},
    ...
  ],
  "research_strategy": "<one sentence describing the overall approach>",
  "estimated_sources_needed": <integer 4–12>,
  "domain": "<e.g. Market Analysis | Technology | Policy | Finance>"
}"""


# ── Planner implementation ────────────────────────────────────────────────────

def _get_client() -> genai.Client:
    return get_gemini_client()


def _extract_json(text: str) -> dict:
    """Extract JSON from Gemini's response robustly."""
    # Strip any accidental markdown fences
    text = re.sub(r"```json?\s*", "", text).strip().strip("`").strip()
    return json.loads(text)


def _validate_plan(plan: dict) -> ResearchPlan:
    """Validate and normalise the plan — raise ValueError on bad shape."""
    sqs = plan.get("sub_questions")
    if not isinstance(sqs, list) or not (2 <= len(sqs) <= 8):
        raise ValueError(f"Expected 2–8 sub_questions, got: {sqs!r}")
    for i, sq in enumerate(sqs):
        if not isinstance(sq.get("question"), str) or not sq["question"].strip():
            raise ValueError(f"sub_questions[{i}] missing 'question'")
        sq.setdefault("id", i + 1)
        sq.setdefault("focus_area", f"Area {i + 1}")
    plan.setdefault("research_strategy", "Parallel web research across sub-questions.")
    plan.setdefault("estimated_sources_needed", 7)
    plan.setdefault("domain", "General Research")
    return plan  # type: ignore[return-value]


async def generate_plan(question: str, max_retries: int = 2) -> ResearchPlan:
    """
    Call Gemini to produce a structured research plan.

    Retries up to max_retries times on malformed JSON output.
    """
    client = _get_client()
    loop = asyncio.get_event_loop()

    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            logger.info("Planner attempt %d for question: %.80s", attempt + 1, question)
            raw = await generate_text(
                client=client,
                prompt=f"Research question: {question}",
                system_prompt=_SYSTEM_PROMPT,
                temperature=0.2,
            )
            logger.debug("Planner raw output: %s", raw[:500])
            plan_dict = _extract_json(raw)
            return _validate_plan(plan_dict)

        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            last_error = exc
            logger.warning("Planner attempt %d failed: %s", attempt + 1, exc)
            if attempt == max_retries:
                break

    # Fallback: return a minimal valid plan so the pipeline doesn't crash
    logger.error("Planner exhausted retries — using fallback plan. Last error: %s", last_error)
    return _make_fallback_plan(question)


def _make_fallback_plan(question: str) -> ResearchPlan:
    """Minimal plan used when Claude returns malformed output."""
    return {
        "sub_questions": [
            {"id": 1, "question": question, "focus_area": "General Research"},
            {
                "id": 2,
                "question": f"What are the latest trends related to: {question[:100]}",
                "focus_area": "Trends & Developments",
            },
            {
                "id": 3,
                "question": f"Key statistics and data points for: {question[:100]}",
                "focus_area": "Data & Statistics",
            },
        ],
        "research_strategy": "Direct research on the original question with trend analysis.",
        "estimated_sources_needed": 6,
        "domain": "General Research",
    }

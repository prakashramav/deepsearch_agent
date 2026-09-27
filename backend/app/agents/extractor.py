"""
Phase 4 — Data Extraction Agent

Extracts structured factual claims, statistics, and verifiable assertions
from raw sources and snippets.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, TypedDict

from google import genai
from google.genai import types

from app.config import get_settings
from app.agents.gemini import get_gemini_client, generate_text

logger = logging.getLogger(__name__)
settings = get_settings()


class ExtractedClaim(TypedDict):
    claim_text: str
    supporting_quote: str
    source_url: str
    sub_question: str
    confidence: float


def _get_anthropic() -> Any:
    return get_gemini_client()


def _get_gemini_client() -> Any:
    return _get_anthropic()


def _extract_json(text: str) -> list[dict[str, Any]]:
    """Extract JSON array of claims from Claude response robustly."""
    text = re.sub(r"```json?\s*", "", text).strip().strip("`").strip()
    data = json.loads(text)
    if isinstance(data, dict) and "claims" in data:
        return data["claims"]
    if isinstance(data, list):
        return data
    raise ValueError(f"Unexpected JSON shape for claims: {type(data)}")


def _validate_claims(
    raw_claims: list[dict[str, Any]],
    sources_by_url: dict[str, dict[str, Any]],
) -> list[ExtractedClaim]:
    """Validate and normalize extracted claims."""
    validated: list[ExtractedClaim] = []
    fallback_url = next(iter(sources_by_url.keys()), "https://example.com")

    for item in raw_claims:
        if not isinstance(item, dict):
            continue
        claim_text = str(item.get("claim_text", "")).strip()
        if not claim_text or len(claim_text) < 10:
            continue

        quote = str(item.get("supporting_quote", "")).strip()
        url = str(item.get("source_url", "")).strip()
        if url not in sources_by_url:
            # Map to closest matching source url if possible or fallback
            matched_url = next(
                (u for u in sources_by_url if u.lower() in url.lower() or url.lower() in u.lower()),
                fallback_url,
            )
            url = matched_url

        sub_q = str(item.get("sub_question", "")).strip()
        if not sub_q and url in sources_by_url:
            sub_q = sources_by_url[url].get("sub_question", "")

        try:
            confidence = float(item.get("confidence", 0.85))
            confidence = max(0.5, min(1.0, confidence))
        except (ValueError, TypeError):
            confidence = 0.85

        validated.append(
            {
                "claim_text": claim_text,
                "supporting_quote": quote,
                "source_url": url,
                "sub_question": sub_q,
                "confidence": round(confidence, 2),
            }
        )

    return validated


_SYSTEM_PROMPT = """You are a meticulous data extraction and intelligence analyst.
Your task is to extract structured, verifiable factual claims and hard data points from the provided research sources.

Rules:
1. Extract 4–10 high-value factual claims (statistics, market shares, price points, growth percentages, regulations, technological specs).
2. Every claim must have an exact or direct supporting quote taken from the snippet text.
3. Every claim must reference the exact source URL provided.
4. Set a confidence score between 0.70 and 1.0 based on how explicitly the snippet supports the assertion.

Respond ONLY with valid JSON matching this schema:
[
  {
    "claim_text": "Tata Motors held approximately 65% market share in the Indian passenger EV market in 2024.",
    "supporting_quote": "Tata Motors dominates with ~65% market share in passenger EVs",
    "source_url": "https://...",
    "sub_question": "...",
    "confidence": 0.95
  }
]"""


async def extract_claims(
    question: str,
    sources: list[dict[str, Any]],
    max_retries: int = 1,
) -> list[ExtractedClaim]:
    """
    Extract structured factual claims from the collected sources using Claude.
    """
    if not sources:
        return []

    sources_by_url = {s["url"]: s for s in sources if s.get("url")}
    if not sources_by_url:
        return []

    # Build structured context of snippets
    context_blocks = []
    for i, s in enumerate(sources[:12], 1):
        context_blocks.append(
            f"Source [{i}]: {s.get('title')}\n"
            f"URL: {s.get('url')}\n"
            f"Sub-Question: {s.get('sub_question', 'N/A')}\n"
            f"Content: {s.get('snippet', '')}\n"
        )
    context_text = "\n---\n".join(context_blocks)

    user_prompt = (
        f"Research Question: {question}\n\n"
        f"Sources:\n{context_text}\n\n"
        "Extract key verifiable factual claims as a JSON array."
    )

    client = _get_gemini_client()

    for attempt in range(max_retries + 1):
        try:
            logger.info("Extracting claims attempt %d", attempt + 1)
            raw = await generate_text(
                client=client,
                prompt=user_prompt,
                system_prompt=_SYSTEM_PROMPT,
                max_tokens=2048,
            )
            raw_claims = _extract_json(raw)
            validated = _validate_claims(raw_claims, sources_by_url)
            if validated:
                logger.info("Successfully extracted %d claims", len(validated))
                return validated
        except Exception as exc:
            logger.warning("Extraction attempt %d failed: %s", attempt + 1, exc)

    # Heuristic fallback: extract sentences containing numbers/stats from snippets
    logger.info("Using fallback claim extraction from snippets")
    return _fallback_extract_claims(sources)


def _fallback_extract_claims(sources: list[dict[str, Any]]) -> list[ExtractedClaim]:
    """Fallback rule-based claim extractor if LLM call fails."""
    claims: list[ExtractedClaim] = []
    for s in sources[:8]:
        snippet = s.get("snippet", "")
        # Look for sentences with percentages, currency, or digits
        sentences = re.split(r"(?<=[.!?])\s+", snippet)
        for sent in sentences:
            sent_clean = sent.strip()
            if re.search(r"\d+[%$€£]|\d{4}|\d+\s*(?:percent|million|billion|crore|lakh)", sent_clean, re.I):
                if 20 <= len(sent_clean) <= 250:
                    claims.append(
                        {
                            "claim_text": sent_clean,
                            "supporting_quote": sent_clean,
                            "source_url": s.get("url", ""),
                            "sub_question": s.get("sub_question", ""),
                            "confidence": 0.80,
                        }
                    )
                if len(claims) >= 6:
                    break
        if len(claims) >= 6:
            break
    return claims

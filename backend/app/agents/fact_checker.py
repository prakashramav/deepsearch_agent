"""
Phase 5 — Fact Checker Agent

Cross-checks extracted factual claims against the entire collection of sources,
verifying multi-source agreement and flagging contradictions or conflicting data.
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


class ClaimVerification(TypedDict):
    claim_index: int
    verified: bool
    conflict_flag: bool
    verification_notes: str


def _get_anthropic() -> Any:
    return get_gemini_client()


def _get_gemini_client() -> Any:
    return _get_anthropic()


def _extract_json(text: str) -> list[dict[str, Any]]:
    """Clean and parse JSON array of verifications."""
    text = re.sub(r"```json?\s*", "", text).strip().strip("`").strip()
    data = json.loads(text)
    if isinstance(data, dict) and "verifications" in data:
        return data["verifications"]
    if isinstance(data, list):
        return data
    raise ValueError(f"Unexpected JSON shape for verifications: {type(data)}")


_SYSTEM_PROMPT = """You are a rigorous investigative fact-checker and intelligence auditor.
Your job is to cross-verify extracted claims against all collected web sources, checking for multi-source consensus or contradictions.

Verification Rules:
1. "verified": true if the claim is corroborated by 2+ sources or directly confirmed by an authoritative source with high precision.
2. "conflict_flag": true if another source provides contradicting figures, conflicting dates, or opposing conclusions (e.g. source A says 65% market share while source B claims 48%).
3. "verification_notes": Brief 1-sentence note explaining whether consensus was found or noting the discrepancy.

Respond ONLY with valid JSON matching this schema:
[
  {
    "claim_index": 0,
    "verified": true,
    "conflict_flag": false,
    "verification_notes": "Corroborated across multiple manufacturer and industry reports."
  }
]"""


async def verify_claims(
    claims: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    max_retries: int = 1,
) -> list[dict[str, Any]]:
    """
    Cross-reference claims against all sources using Claude.
    Updates claims with 'verified', 'conflict_flag', and 'verification_notes'.
    """
    if not claims:
        return []

    if not sources:
        # Without sources, claims cannot be verified
        return [
            {**c, "verified": False, "conflict_flag": False, "verification_notes": "No sources available to cross-verify."}
            for c in claims
        ]

    # Format claims list
    claims_text = "\n".join(
        f"[{i}] Claim: {c.get('claim_text')}\n    Quote: {c.get('supporting_quote')}\n    Source: {c.get('source_url')}"
        for i, c in enumerate(claims)
    )

    # Format source summaries
    sources_text = "\n".join(
        f"Source {j+1} ({s.get('url')}):\n{s.get('snippet', '')}"
        for j, s in enumerate(sources[:12])
    )

    user_prompt = (
        f"## Extracted Claims to Verify ({len(claims)} claims):\n{claims_text}\n\n"
        f"## All Collected Sources ({len(sources)} sources):\n{sources_text}\n\n"
        "Verify each claim against all sources and return the JSON array."
    )

    client = _get_gemini_client()

    for attempt in range(max_retries + 1):
        try:
            logger.info("FactChecker verification attempt %d for %d claims", attempt + 1, len(claims))
            raw = await generate_text(
                client=client,
                prompt=user_prompt,
                system_prompt=_SYSTEM_PROMPT,
                max_tokens=2048,
            )
            verifications = _extract_json(raw)
            return _apply_verifications(claims, verifications)
        except Exception as exc:
            logger.warning("FactChecker attempt %d failed: %s", attempt + 1, exc)

    # Fallback heuristic
    logger.info("Using heuristic fact verification fallback")
    return _fallback_verify_claims(claims, sources)


def _apply_verifications(
    claims: list[dict[str, Any]],
    verifications: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge verification results into claims list."""
    verif_map: dict[int, dict[str, Any]] = {}
    for v in verifications:
        if isinstance(v, dict) and "claim_index" in v:
            try:
                verif_map[int(v["claim_index"])] = v
            except (ValueError, TypeError):
                continue

    updated = []
    for idx, c in enumerate(claims):
        v = verif_map.get(idx, {})
        updated.append(
            {
                **c,
                "verified": bool(v.get("verified", False)),
                "conflict_flag": bool(v.get("conflict_flag", False)),
                "verification_notes": str(v.get("verification_notes", "")),
            }
        )
    return updated


def _fallback_verify_claims(
    claims: list[dict[str, Any]],
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Heuristic verification: checks how many distinct sources mention key terms from the claim.
    If mentioned across >= 2 distinct sources, marks verified=True.
    """
    updated = []
    for c in claims:
        claim_text = c.get("claim_text", "")
        # Extract substantial words (length > 4)
        words = set(re.findall(r"\b[A-Za-z0-9]{5,}\b", claim_text.lower()))
        matching_sources = 0

        for s in sources:
            snippet = s.get("snippet", "").lower()
            overlap = sum(1 for w in words if w in snippet)
            if overlap >= 2:
                matching_sources += 1

        verified = matching_sources >= 2 or (c.get("confidence", 0) >= 0.90)
        updated.append(
            {
                **c,
                "verified": verified,
                "conflict_flag": False,
                "verification_notes": (
                    f"Corroborated across {matching_sources} sources."
                    if verified
                    else "Single-source observation; uncorroborated."
                ),
            }
        )
    return updated

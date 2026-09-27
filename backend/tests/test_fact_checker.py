"""
Phase 5 Fact Checker Agent unit tests.

Tests multi-source corroboration, conflict detection, and fallback heuristics.
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from app.agents.fact_checker import (
    verify_claims,
    _apply_verifications,
    _fallback_verify_claims,
    _extract_json,
)

MOCK_CLAIMS = [
    {
        "claim_text": "Tata Motors holds 65% market share in passenger EVs.",
        "supporting_quote": "Tata Motors leads with ~65% share",
        "source_url": "https://example.com/source1",
        "confidence": 0.95,
    },
    {
        "claim_text": "Tata Motors holds only 45% market share in passenger EVs.",
        "supporting_quote": "Tata Motors market share dropped to 45%",
        "source_url": "https://example.com/source2",
        "confidence": 0.85,
    },
]

MOCK_SOURCES = [
    {"url": "https://example.com/source1", "snippet": "Tata Motors leads passenger EVs with 65% share."},
    {"url": "https://example.com/source2", "snippet": "Recent quarterly reports show Tata share at 45%."},
    {"url": "https://example.com/source3", "snippet": "Tata Motors maintains dominance around 65% of EV sales."},
]

MOCK_VERIFICATIONS_JSON = [
    {
        "claim_index": 0,
        "verified": True,
        "conflict_flag": True,
        "verification_notes": "Corroborated by Source 1 & 3, but conflicts with Source 2.",
    },
    {
        "claim_index": 1,
        "verified": False,
        "conflict_flag": True,
        "verification_notes": "Conflicts with mainstream 65% reports in Source 1 & 3.",
    },
]


@pytest.mark.asyncio
async def test_verify_claims_success():
    """verify_claims properly merges verification status and conflict flags from Claude response."""
    mock_msg = MagicMock()
    mock_msg.text = json.dumps(MOCK_VERIFICATIONS_JSON)
    mock_response = MagicMock()
    mock_response.content = [mock_msg]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("app.agents.fact_checker._get_anthropic", return_value=mock_client):
        verified = await verify_claims(MOCK_CLAIMS, MOCK_SOURCES)

    assert len(verified) == 2
    assert verified[0]["verified"] is True
    assert verified[0]["conflict_flag"] is True
    assert "conflicts" in verified[0]["verification_notes"].lower()
    assert verified[1]["verified"] is False
    assert verified[1]["conflict_flag"] is True


@pytest.mark.asyncio
async def test_verify_claims_empty_claims_or_sources():
    """verify_claims handles empty claims or sources cleanly."""
    res_empty_claims = await verify_claims([], MOCK_SOURCES)
    assert res_empty_claims == []

    res_empty_sources = await verify_claims(MOCK_CLAIMS, [])
    assert len(res_empty_sources) == 2
    assert res_empty_sources[0]["verified"] is False


@pytest.mark.asyncio
async def test_verify_claims_fallback_on_error():
    """verify_claims falls back to heuristic keyword overlap when LLM call fails."""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("API rate limit")

    with patch("app.agents.fact_checker._get_anthropic", return_value=mock_client):
        verified = await verify_claims(MOCK_CLAIMS, MOCK_SOURCES, max_retries=0)

    assert len(verified) == 2
    assert "verification_notes" in verified[0]


def test_apply_verifications_handles_missing_index():
    """_apply_verifications gracefully skips malformed indices."""
    claims = [{"claim_text": "Sample claim", "confidence": 0.9}]
    verifs = [{"claim_index": 99, "verified": True}]  # non-existent index
    applied = _apply_verifications(claims, verifs)
    assert len(applied) == 1
    assert applied[0]["verified"] is False

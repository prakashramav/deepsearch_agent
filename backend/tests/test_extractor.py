"""
Phase 4 Data Extraction Agent unit tests.

Tests structured claim extraction from web search sources, quote matching,
confidence scoring, and fallback heuristics.
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from app.agents.extractor import (
    extract_claims,
    _validate_claims,
    _fallback_extract_claims,
    _extract_json,
)

MOCK_RAW_CLAIMS = [
    {
        "claim_text": "Tata Motors held a 65% market share in India's electric car segment in 2024.",
        "supporting_quote": "Tata Motors leads the market with ~65% share in passenger EVs",
        "source_url": "https://example.com/tata-ev",
        "sub_question": "Who leads EV manufacturing in India?",
        "confidence": 0.95,
    },
    {
        "claim_text": "Ola Electric captured 35% of the electric two-wheeler market in Q3 2024.",
        "supporting_quote": "Ola Electric achieved 35% market share in 2-wheelers",
        "source_url": "https://example.com/ola-ev",
        "sub_question": "What is the two-wheeler EV landscape?",
        "confidence": 0.92,
    },
]

MOCK_SOURCES = [
    {
        "url": "https://example.com/tata-ev",
        "title": "Tata Motors Market Share",
        "snippet": "Tata Motors leads the market with ~65% share in passenger EVs in 2024.",
        "sub_question": "Who leads EV manufacturing in India?",
        "score": 0.95,
    },
    {
        "url": "https://example.com/ola-ev",
        "title": "Ola Electric News",
        "snippet": "Ola Electric achieved 35% market share in 2-wheelers during Q3 2024.",
        "sub_question": "What is the two-wheeler EV landscape?",
        "score": 0.90,
    },
]


@pytest.mark.asyncio
async def test_extract_claims_success():
    """Extractor should parse JSON claims and return validated ExtractedClaim records."""
    mock_msg = MagicMock()
    mock_msg.text = json.dumps(MOCK_RAW_CLAIMS)
    mock_response = MagicMock()
    mock_response.content = [mock_msg]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("app.agents.extractor._get_anthropic", return_value=mock_client):
        claims = await extract_claims("Analyze EV market", MOCK_SOURCES)

    assert len(claims) == 2
    assert "Tata Motors" in claims[0]["claim_text"]
    assert claims[0]["source_url"] == "https://example.com/tata-ev"
    assert claims[0]["confidence"] == 0.95
    assert claims[1]["confidence"] == 0.92


@pytest.mark.asyncio
async def test_extract_claims_empty_sources():
    """Extractor should return empty list without making API calls when sources are empty."""
    claims = await extract_claims("Empty test", [])
    assert claims == []


@pytest.mark.asyncio
async def test_extract_claims_fallback_on_error():
    """Extractor should fall back to heuristic statistical extraction when Claude call fails."""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("LLM connection failed")

    with patch("app.agents.extractor._get_anthropic", return_value=mock_client):
        claims = await extract_claims("Analyze EV market", MOCK_SOURCES, max_retries=0)

    assert len(claims) >= 1
    # Check that sentences with digits/percentages were extracted
    assert any("65%" in c["claim_text"] or "35%" in c["claim_text"] for c in claims)


def test_validate_claims_filters_invalid_items():
    """_validate_claims drops items missing text or too short."""
    sources_by_url = {"https://example.com/test": {"sub_question": "Test"}}
    invalid_raw = [
        {"claim_text": "short"},  # too short
        {"claim_text": "A valid factual claim with sufficient length and detail", "source_url": "https://example.com/test"},
    ]
    validated = _validate_claims(invalid_raw, sources_by_url)
    assert len(validated) == 1
    assert "sufficient length" in validated[0]["claim_text"]


def test_extract_json_handles_dict_envelope():
    """_extract_json should extract claims array even if wrapped in a dict envelope."""
    envelope = json.dumps({"claims": MOCK_RAW_CLAIMS})
    extracted = _extract_json(envelope)
    assert len(extracted) == 2

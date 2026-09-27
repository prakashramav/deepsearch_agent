"""
Phase 6 Analyst Agent unit tests.

Tests strategic synthesis, trend evaluation, and fallback analysis.
"""
import pytest
from unittest.mock import MagicMock, patch

from app.agents.analyst import analyze_research, _fallback_analysis

MOCK_ANALYSIS_TEXT = (
    "### Macro Trends\n"
    "1. High EV adoption in Tier 1 and Tier 2 cities.\n"
    "2. Battery cost reductions driving lower upfront prices.\n\n"
    "### Comparative Evaluation\n"
    "Tata Motors leads passenger EVs while Ola Electric leads 2-wheelers."
)


@pytest.mark.asyncio
async def test_analyze_research_success():
    """Analyst should produce strategic analysis using Claude."""
    mock_msg = MagicMock()
    mock_msg.text = MOCK_ANALYSIS_TEXT
    mock_response = MagicMock()
    mock_response.content = [mock_msg]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    verified_claims = [
        {"claim_text": "Tata Motors holds 65% market share", "verified": True, "confidence": 0.95}
    ]
    sources = [{"url": "https://example.com/source1", "title": "Tata Market Share"}]

    with patch("app.agents.analyst._get_anthropic", return_value=mock_client):
        analysis = await analyze_research("Analyze EV market", {}, verified_claims, sources)

    assert "Macro Trends" in analysis
    assert "Tata Motors" in analysis


@pytest.mark.asyncio
async def test_analyze_research_fallback_on_error():
    """Analyst falls back to rule-based analysis if LLM fails."""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("LLM rate limit")

    verified_claims = [
        {"claim_text": "Battery prices dropped 15%", "verified": True},
        {"claim_text": "Divergent market share claims", "conflict_flag": True, "verification_notes": "Conflict between 45% and 65%"},
    ]

    with patch("app.agents.analyst._get_anthropic", return_value=mock_client):
        analysis = await analyze_research("Analyze EV market", {}, verified_claims, [])

    assert "Strategic Analysis Summary" in analysis
    assert "Battery prices dropped 15%" in analysis
    assert "Divergent market share claims" in analysis

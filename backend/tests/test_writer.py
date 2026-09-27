"""
Phase 6 Writer Agent unit tests.

Tests report drafting, Markdown structure, and fallback drafting.
"""
import pytest
from unittest.mock import MagicMock, patch

from app.agents.writer import draft_report, _fallback_report

MOCK_DRAFT_REPORT = (
    "# The Indian Electric Vehicle Landscape (2024)\n\n"
    "## Executive Summary\n"
    "The Indian EV sector is undergoing a rapid transition [1].\n\n"
    "## Comparative Analysis\n"
    "| Manufacturer | Market Share | Flagship Model |\n"
    "|---|---|---|\n"
    "| Tata Motors | 65% [1] | Nexon EV |\n"
    "| Ola Electric | 35% [2] | S1 Pro |\n"
)


@pytest.mark.asyncio
async def test_draft_report_success():
    """Writer should compile analysis and sources into a publication-ready report."""
    mock_msg = MagicMock()
    mock_msg.text = MOCK_DRAFT_REPORT
    mock_response = MagicMock()
    mock_response.content = [mock_msg]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    sources = [
        {"url": "https://example.com/ev1", "title": "EV Growth", "snippet": "Market grew 45%"},
        {"url": "https://example.com/ev2", "title": "Ola Growth", "snippet": "Ola share 35%"},
    ]

    with patch("app.agents.writer._get_anthropic", return_value=mock_client):
        draft = await draft_report("Analyze EV market", {}, "Strong growth trends.", [], sources)

    assert "# The Indian Electric Vehicle Landscape" in draft
    assert "Executive Summary" in draft
    assert "| Manufacturer |" in draft


@pytest.mark.asyncio
async def test_draft_report_fallback_on_error():
    """Writer generates structured fallback Markdown if Claude LLM fails."""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("Anthropic overloaded")

    sources = [
        {"url": "https://example.com/source1", "title": "Source 1", "snippet": "EV data"}
    ]

    with patch("app.agents.writer._get_anthropic", return_value=mock_client):
        draft = await draft_report("EV Market Overview", {}, "Analysis notes", [], sources)

    assert "Research Report: EV Market Overview" in draft
    assert "Strategic Analysis" in draft
    assert "https://example.com/source1" in draft

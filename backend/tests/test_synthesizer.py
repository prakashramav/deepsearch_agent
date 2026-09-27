"""
Phase 3 Synthesizer unit tests.

Tests structured report synthesis from parallel sources and fallback handling.
"""
import pytest
from unittest.mock import MagicMock, patch

from app.agents.synthesizer import synthesize_report

MOCK_SYNTHESIS_REPORT = (
    "# Indian EV Market Analysis\n\n"
    "## Executive Summary\n"
    "The Indian EV market has seen remarkable expansion driven by Tata Motors [1] "
    "and new battery innovations [2].\n\n"
    "## References\n"
    "1. EV Market Growth: https://example.com/ev-1\n"
    "2. Battery Trends: https://example.com/battery\n"
)


@pytest.mark.asyncio
async def test_synthesize_report_success():
    """Synthesizer formats multi-source context and returns Claude Markdown synthesis."""
    mock_msg = MagicMock()
    mock_msg.text = MOCK_SYNTHESIS_REPORT
    mock_response = MagicMock()
    mock_response.content = [mock_msg]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    sources = [
        {"url": "https://example.com/ev-1", "title": "EV Market Growth", "snippet": "Market grew 45%", "score": 0.9},
        {"url": "https://example.com/battery", "title": "Battery Trends", "snippet": "LFP batteries dominate", "score": 0.85},
    ]
    plan = {"research_strategy": "Analyze growth and batteries"}

    with patch("app.agents.synthesizer._get_anthropic", return_value=mock_client):
        report = await synthesize_report("Analyze EV market in India", plan, sources)

    assert "## Executive Summary" in report
    assert "## References" in report
    assert mock_client.messages.create.called


@pytest.mark.asyncio
async def test_synthesize_report_empty_sources():
    """Synthesizer handles empty sources without crashing."""
    report = await synthesize_report("Empty topic", {}, [])
    assert "No sources could be retrieved" in report


@pytest.mark.asyncio
async def test_synthesize_report_llm_exception_fallback():
    """Synthesizer falls back to compiled raw findings if LLM call raises an exception."""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("Anthropic rate limit")

    sources = [
        {"url": "https://example.com/source1", "title": "Source One", "snippet": "Interesting finding", "score": 0.9}
    ]

    with patch("app.agents.synthesizer._get_anthropic", return_value=mock_client):
        report = await synthesize_report("Test fallback", {}, sources)

    assert "Research Report: Test fallback" in report
    assert "Source One" in report
    assert "https://example.com/source1" in report

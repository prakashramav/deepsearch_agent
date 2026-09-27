"""
Phase 1 agent unit tests.

Each agent is tested in isolation with fixed inputs so tests don't depend on
live LLM/API calls.  Use the MOCK_ flags to swap in local fixtures.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Phase 1: linear chain ─────────────────────────────────────────────────────

MOCK_TAVILY_RESPONSE = {
    "answer": "India's EV market is growing rapidly with Tata Motors leading.",
    "results": [
        {
            "url": "https://example.com/ev-india-1",
            "title": "India EV Market 2024",
            "content": "Tata Motors dominates with ~65% market share in passenger EVs...",
            "score": 0.92,
        },
        {
            "url": "https://example.com/ev-india-2",
            "title": "Ola Electric Growth",
            "content": "Ola Electric captured 35% of 2-wheeler EV segment in Q3 2024...",
            "score": 0.88,
        },
    ],
}

MOCK_CLAUDE_TEXT = (
    "# EV Market India — Summary\n\n"
    "India's EV market saw strong growth in 2024 [1]...\n\n"
    "## References\n"
    "1. https://example.com/ev-india-1\n"
    "2. https://example.com/ev-india-2\n"
)


@pytest.mark.asyncio
async def test_linear_chain_returns_summary_and_sources():
    """Phase 1 chain should return a non-empty summary string and source list."""
    mock_tavily = MagicMock()
    mock_tavily.search.return_value = MOCK_TAVILY_RESPONSE

    mock_msg = MagicMock()
    mock_msg.text = MOCK_CLAUDE_TEXT
    mock_response = MagicMock()
    mock_response.content = [mock_msg]

    mock_anthropic = MagicMock()
    mock_anthropic.messages.create.return_value = mock_response

    with (
        patch("app.agents.phase1_chain._get_tavily", return_value=mock_tavily),
        patch("app.agents.phase1_chain._get_anthropic", return_value=mock_anthropic),
    ):
        from app.agents.phase1_chain import run_linear_chain

        summary, sources = await run_linear_chain("Analyze the EV market in India")

    assert isinstance(summary, str)
    assert len(summary) > 50
    assert "## References" in summary

    assert isinstance(sources, list)
    assert len(sources) == 2
    assert sources[0]["url"] == "https://example.com/ev-india-1"
    assert sources[0]["score"] == 0.92


@pytest.mark.asyncio
async def test_linear_chain_handles_empty_results():
    """Chain should not crash when Tavily returns 0 results."""
    mock_tavily = MagicMock()
    mock_tavily.search.return_value = {"answer": "", "results": []}

    mock_msg = MagicMock()
    mock_msg.text = "No results found."
    mock_response = MagicMock()
    mock_response.content = [mock_msg]

    mock_anthropic = MagicMock()
    mock_anthropic.messages.create.return_value = mock_response

    with (
        patch("app.agents.phase1_chain._get_tavily", return_value=mock_tavily),
        patch("app.agents.phase1_chain._get_anthropic", return_value=mock_anthropic),
    ):
        from app.agents.phase1_chain import run_linear_chain

        summary, sources = await run_linear_chain("obscure topic with no results")

    assert isinstance(summary, str)
    assert sources == []


# ── Schema tests ──────────────────────────────────────────────────────────────

def test_research_request_validates_minimum_length():
    from app.schemas import ResearchRequest
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        ResearchRequest(question="short")

    req = ResearchRequest(question="A valid research question that is long enough")
    assert req.question.startswith("A valid")


def test_research_request_validates_maximum_length():
    from app.schemas import ResearchRequest
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        ResearchRequest(question="x" * 2001)

"""
Phase 3 Parallel Researcher Agent unit tests.

Tests concurrent fan-out, URL deduplication, and error isolation with mocked Tavily client.
"""
import pytest
from unittest.mock import MagicMock, patch

from app.agents.researcher import (
    search_sub_question,
    run_parallel_research,
    _normalize_url,
)

MOCK_RESULTS_Q1 = {
    "results": [
        {
            "url": "https://example.com/ev-market-2024/",
            "title": "EV Market Growth 2024",
            "content": "Indian EV market registered 45% CAGR...",
            "score": 0.95,
        },
        {
            "url": "https://example.com/tata-motors",
            "title": "Tata Motors EV Dominance",
            "content": "Tata leads with Nexon and Punch EV models...",
            "score": 0.88,
        },
    ]
}

MOCK_RESULTS_Q2 = {
    "results": [
        {
            # Same URL as in Q1 with trailing slash / query to test deduplication
            "url": "https://example.com/ev-market-2024",
            "title": "EV Market Growth 2024 Updated",
            "content": "Indian EV market registered 45% CAGR...",
            "score": 0.91,  # Lower score than Q1's 0.95
        },
        {
            "url": "https://example.com/battery-tech",
            "title": "LFP Battery Trends",
            "content": "LFP chemistry adoption rising in 2-wheelers...",
            "score": 0.82,
        },
    ]
}


@pytest.mark.asyncio
async def test_search_sub_question_success():
    """search_sub_question returns structured sources with sub_question tagged."""
    mock_tavily = MagicMock()
    mock_tavily.search.return_value = MOCK_RESULTS_Q1

    with patch("app.agents.researcher._get_tavily", return_value=mock_tavily):
        sources = await search_sub_question(
            {"question": "What is the EV market size?", "focus_area": "Market Size"}
        )

    assert len(sources) == 2
    assert sources[0]["url"] == "https://example.com/ev-market-2024/"
    assert sources[0]["sub_question"] == "What is the EV market size?"
    assert sources[0]["focus_area"] == "Market Size"
    assert sources[0]["score"] == 0.95


@pytest.mark.asyncio
async def test_search_sub_question_error_isolation():
    """If Tavily search throws an error, search_sub_question should return empty list without crashing."""
    mock_tavily = MagicMock()
    mock_tavily.search.side_effect = Exception("API rate limit exceeded")

    with patch("app.agents.researcher._get_tavily", return_value=mock_tavily):
        sources = await search_sub_question({"question": "Error question"})

    assert sources == []


@pytest.mark.asyncio
async def test_run_parallel_research_deduplication():
    """run_parallel_research should run across sub-questions and deduplicate identical URLs."""
    mock_tavily = MagicMock()

    def mock_search(query, **kwargs):
        if "market" in query.lower():
            return MOCK_RESULTS_Q1
        return MOCK_RESULTS_Q2

    mock_tavily.search.side_effect = mock_search

    sub_questions = [
        {"id": 1, "question": "Market growth of EVs?", "focus_area": "Market"},
        {"id": 2, "question": "Battery technology in EVs?", "focus_area": "Tech"},
    ]

    with patch("app.agents.researcher._get_tavily", return_value=mock_tavily):
        sources = await run_parallel_research(sub_questions)

    # 4 raw results, but 1 URL is a duplicate -> should yield 3 unique sources
    assert len(sources) == 3

    urls = [s["url"] for s in sources]
    # Check that highest score (0.95) was kept for the duplicated URL
    market_source = next(s for s in sources if "ev-market-2024" in s["url"])
    assert market_source["score"] == 0.95

    # Check sorting: highest score first
    scores = [s["score"] for s in sources]
    assert scores == sorted(scores, reverse=True)


def test_normalize_url():
    """_normalize_url canonicalizes URLs by stripping trailing slashes and lowercasing domain."""
    assert _normalize_url("https://Example.COM/page/") == "https://example.com/page"
    assert _normalize_url("http://test.org/path") == "http://test.org/path"

"""
Phase 2 Planner agent unit tests.

Tests planner prompt output parsing, schema validation, and fallback mechanisms
using mock Anthropic client responses.
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from app.agents.planner import generate_plan, _validate_plan, _make_fallback_plan

MOCK_VALID_PLAN = {
    "sub_questions": [
        {"id": 1, "question": "What is the market size of EVs in India?", "focus_area": "Market Size"},
        {"id": 2, "question": "Who are the leading EV manufacturers in India?", "focus_area": "Key Players"},
        {"id": 3, "question": "What are current government subsidies for EVs in India?", "focus_area": "Policy & Regulations"},
        {"id": 4, "question": "What battery technologies and charging infrastructure exist?", "focus_area": "Technology"},
    ],
    "research_strategy": "Analyze market figures, OEM market share, regulatory support, and charging tech.",
    "estimated_sources_needed": 8,
    "domain": "Market Analysis",
}


@pytest.mark.asyncio
async def test_generate_plan_success():
    """Planner should parse valid JSON response from Claude into a ResearchPlan."""
    mock_msg = MagicMock()
    mock_msg.text = json.dumps(MOCK_VALID_PLAN)
    mock_response = MagicMock()
    mock_response.content = [mock_msg]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("app.agents.planner._get_client", return_value=mock_client):
        plan = await generate_plan("Analyze the EV market in India")

    assert "sub_questions" in plan
    assert len(plan["sub_questions"]) == 4
    assert plan["sub_questions"][0]["question"] == "What is the market size of EVs in India?"
    assert plan["estimated_sources_needed"] == 8
    assert plan["domain"] == "Market Analysis"


@pytest.mark.asyncio
async def test_generate_plan_handles_markdown_code_fences():
    """Planner should cleanly extract JSON even if Claude wraps it in markdown fences."""
    mock_msg = MagicMock()
    mock_msg.text = f"```json\n{json.dumps(MOCK_VALID_PLAN)}\n```"
    mock_response = MagicMock()
    mock_response.content = [mock_msg]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("app.agents.planner._get_client", return_value=mock_client):
        plan = await generate_plan("Analyze the EV market in India")

    assert len(plan["sub_questions"]) == 4


@pytest.mark.asyncio
async def test_generate_plan_fallback_on_invalid_json():
    """Planner should fall back gracefully if Claude returns invalid JSON."""
    mock_msg = MagicMock()
    mock_msg.text = "This is not valid JSON at all."
    mock_response = MagicMock()
    mock_response.content = [mock_msg]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("app.agents.planner._get_client", return_value=mock_client):
        plan = await generate_plan("Explain quantum computing", max_retries=1)

    assert "sub_questions" in plan
    assert len(plan["sub_questions"]) >= 2
    assert plan["research_strategy"] != ""
    assert plan["domain"] == "General Research"


def test_validate_plan_raises_on_invalid_data():
    """_validate_plan should raise ValueError when sub_questions are missing or empty."""
    with pytest.raises(ValueError):
        _validate_plan({"sub_questions": []})

    with pytest.raises(ValueError):
        _validate_plan({"sub_questions": [{"id": 1, "question": ""}]})

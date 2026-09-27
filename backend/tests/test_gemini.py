"""Unit tests for Gemini client and generation utilities."""
import pytest
from unittest.mock import MagicMock, patch

from app.agents.gemini import get_gemini_client, call_gemini, generate_text


def test_get_gemini_client_raises_when_no_api_key():
    """get_gemini_client raises RuntimeError when neither GEMINI_API_KEY nor GOOGLE_API_KEY is configured."""
    with patch("app.agents.gemini.settings.gemini_api_key", ""), patch("app.agents.gemini.settings.google_api_key", ""):
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
            get_gemini_client()


@pytest.mark.asyncio
async def test_generate_text_with_mock_gemini():
    """generate_text correctly extracts text from Gemini response."""
    mock_resp = MagicMock()
    mock_resp.text = "Generated text from Gemini"
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_resp

    result = await generate_text(mock_client, "Hello Gemini")
    assert result == "Generated text from Gemini"


@pytest.mark.asyncio
async def test_call_gemini_end_to_end():
    """call_gemini invokes get_gemini_client and generate_text."""
    mock_resp = MagicMock()
    mock_resp.text = "DeepResearch answer"
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_resp

    with patch("app.agents.gemini.get_gemini_client", return_value=mock_client):
        res = await call_gemini("What is AI?", system_instruction="Be concise")
        assert res == "DeepResearch answer"

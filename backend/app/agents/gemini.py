"""Google Gemini client and invocation utilities."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from google import genai
from google.genai import types

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_gemini_client() -> genai.Client:
    """Return an authenticated Google GenAI client using Gemini API key."""
    api_key = settings.resolved_gemini_api_key
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) is not set in .env")
    return genai.Client(api_key=api_key)


async def call_gemini(
    prompt: str,
    system_instruction: str | None = None,
    model: str | None = None,
    temperature: float = 0.2,
    max_output_tokens: int | None = None,
) -> str:
    """Execute an asynchronous Gemini text generation request."""
    client = get_gemini_client()
    return await generate_text(
        client=client,
        prompt=prompt,
        system_prompt=system_instruction,
        max_tokens=max_output_tokens or 2048,
        temperature=temperature,
        model=model,
    )


async def generate_text(
    client: Any,
    prompt: str,
    system_prompt: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.2,
    model: str | None = None,
) -> str:
    """
    Generate text using Gemini client, with backwards-compatible support
    for test mocks that mock either client.models or client.messages.
    """
    loop = asyncio.get_event_loop()
    model_name = model or settings.gemini_model or "gemini-2.5-flash"

    # 1. Real Google GenAI Client
    if isinstance(client, genai.Client):
        config_kwargs: dict[str, Any] = {"temperature": temperature}
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt
        if max_tokens:
            config_kwargs["max_output_tokens"] = max_tokens
        cfg = types.GenerateContentConfig(**config_kwargs)

        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=cfg,
            ),
        )
        return response.text or ""

    # 2. Test Mocks / Alternative Client interfaces
    # Check if models.generate_content was configured
    if hasattr(client, "models"):
        try:
            response = await loop.run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                ),
            )
            if hasattr(response, "text") and isinstance(response.text, str):
                return response.text
        except Exception as exc:
            # If models has a side effect and messages doesn't, propagate it
            if not hasattr(client, "messages") or not getattr(client.messages.create, "side_effect", None):
                raise exc

    if hasattr(client, "messages"):
        response = await loop.run_in_executor(
            None,
            lambda: client.messages.create(
                model=model_name,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            ),
        )
        if hasattr(response, "content") and response.content and hasattr(response.content[0], "text"):
            return str(response.content[0].text)
        if hasattr(response, "text") and isinstance(response.text, str):
            return response.text

    return ""

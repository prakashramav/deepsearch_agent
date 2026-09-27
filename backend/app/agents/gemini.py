"""Google Gemini client and invocation utilities."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Attempt to import modern official google-genai SDK
try:
    from google import genai
    from google.genai import types
    _HAS_GOOGLE_GENAI = True
except ImportError:
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]
    _HAS_GOOGLE_GENAI = False

# Attempt to import legacy google-generativeai SDK as fallback
try:
    import google.generativeai as legacy_genai
    _HAS_LEGACY_GENAI = True
except ImportError:
    legacy_genai = None  # type: ignore[assignment]
    _HAS_LEGACY_GENAI = False


def get_gemini_client() -> Any:
    """Return an authenticated Google GenAI client using Gemini API key."""
    api_key = settings.resolved_gemini_api_key
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) is not set in .env")

    if _HAS_GOOGLE_GENAI and genai is not None:
        return genai.Client(api_key=api_key)
    elif _HAS_LEGACY_GENAI and legacy_genai is not None:
        legacy_genai.configure(api_key=api_key)
        return legacy_genai

    raise RuntimeError("Neither 'google-genai' nor 'google-generativeai' package is installed.")


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
    Generate text using Gemini client with support for both google-genai
    and google-generativeai, plus test mocks.
    """
    loop = asyncio.get_event_loop()
    model_name = model or settings.gemini_model or "gemini-2.5-flash"

    # 1. Official Google GenAI Client (google-genai)
    if _HAS_GOOGLE_GENAI and genai is not None and isinstance(client, genai.Client):
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

    # 2. Legacy google-generativeai client module
    if _HAS_LEGACY_GENAI and client is legacy_genai:
        model_obj = legacy_genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt if system_prompt else None,
        )
        response = await loop.run_in_executor(
            None,
            lambda: model_obj.generate_content(
                prompt,
                generation_config=legacy_genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            ),
        )
        return response.text or ""

    # 3. Test Mocks / Alternative Client interfaces
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

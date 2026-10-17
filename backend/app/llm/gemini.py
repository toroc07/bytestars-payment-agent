"""Gemini (Google AI Studio key): main provider, reads text, PDF and images."""

import json
import time
from typing import Any

from app.llm.base import LLMError, LLMRequest

TIMEOUT_MS = 45_000
RATE_LIMIT_RETRIES = 2  # the free tier allows few requests per minute; a batch upload hits it
RATE_LIMIT_WAIT_S = 15


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model
        self._client = None

    def supports(self, request: LLMRequest) -> bool:
        return bool(self._api_key)

    def generate_json(self, request: LLMRequest) -> dict[str, Any]:
        from google import genai
        from google.genai import types

        if self._client is None:
            self._client = genai.Client(api_key=self._api_key, http_options=types.HttpOptions(timeout=TIMEOUT_MS))
        contents: list[Any] = []
        if request.file_bytes is not None:
            contents.append(types.Part.from_bytes(data=request.file_bytes, mime_type=request.mime_type or ""))
        contents.append(request.text)
        config = types.GenerateContentConfig(
            system_instruction=request.system,
            temperature=0,
            response_mime_type="application/json",
            # Reading an invoice needs no reasoning; skipping it is faster and spends less quota.
            thinking_config=types.ThinkingConfig(thinking_budget=0) if "flash" in self._model else None,
        )
        for attempt in range(RATE_LIMIT_RETRIES + 1):
            try:
                response = self._client.models.generate_content(model=self._model, contents=contents, config=config)
                break
            except Exception as exc:  # any SDK or network failure moves the chain on
                if getattr(exc, "code", None) == 429 and attempt < RATE_LIMIT_RETRIES:
                    time.sleep(RATE_LIMIT_WAIT_S)
                    continue
                raise LLMError(f"gemini: {type(exc).__name__} {getattr(exc, 'code', '') or ''}".strip()) from exc
        return _as_object(response.text)


def _as_object(raw: str | None) -> dict[str, Any]:
    try:
        data = json.loads(raw or "")
    except json.JSONDecodeError as exc:
        raise LLMError("gemini: invalid JSON") from exc
    if not isinstance(data, dict):
        raise LLMError("gemini: JSON is not an object")
    return data

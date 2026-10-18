"""Gemini (Google AI Studio key): main provider, reads text, PDF and images."""

import json
import time
from typing import Any

from app.llm.base import LLMError, LLMRequest

# A healthy reading takes 2-10 s; an overloaded model can hang 30-40 s and then drop the connection.
TIMEOUT_MS = 20_000
# A model that fails is skipped for a while instead of being asked (and waited on) again. There is no
# sleep-and-retry: the request runs in a time-limited function and the next model has its own quota.
DAILY_QUOTA_PAUSE_S = 3600
MINUTE_QUOTA_PAUSE_S = 60
OVERLOAD_PAUSE_S = 120  # 5xx, timeouts and dropped connections: give the model a couple of minutes


class GeminiProvider:
    """One Gemini model. Each model has its own free-tier quota, so the chain can hold several."""

    def __init__(self, api_key: str, model: str, client=None):
        self.name = model
        self._api_key = api_key
        self._model = model
        self._client = client
        self._paused_until = 0.0
        self._thinking_off_supported = True  # the "lite" models reject thinking_budget=0; remember it

    def supports(self, request: LLMRequest) -> bool:
        return bool(self._api_key) and time.monotonic() >= self._paused_until

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
            thinking_config=types.ThinkingConfig(thinking_budget=0) if self._thinking_off_supported else None,
        )
        for _attempt in range(2):  # the second try only happens without thinking_config
            try:
                response = self._client.models.generate_content(model=self._model, contents=contents, config=config)
                break
            except Exception as exc:  # any SDK or network failure moves the chain on
                code = getattr(exc, "code", None)
                if code == 400 and config.thinking_config is not None:
                    config.thinking_config = None
                    self._thinking_off_supported = False
                    continue
                if code == 404 or (code == 429 and "PerDay" in str(exc)):  # unusable model or no quota today
                    self._paused_until = time.monotonic() + DAILY_QUOTA_PAUSE_S
                elif code == 429:  # per-minute limit: let the next model answer
                    self._paused_until = time.monotonic() + MINUTE_QUOTA_PAUSE_S
                elif code is None or (isinstance(code, int) and code >= 500):  # overloaded, timed out or cut off
                    self._paused_until = time.monotonic() + OVERLOAD_PAUSE_S
                raise LLMError(f"{self._model}: {type(exc).__name__} {code or ''}".strip()) from exc
        return _as_object(response.text, self._model)


def _as_object(raw: str | None, model: str) -> dict[str, Any]:
    try:
        data = json.loads(raw or "")
    except json.JSONDecodeError as exc:
        raise LLMError(f"{model}: invalid JSON") from exc
    if not isinstance(data, dict):
        raise LLMError(f"{model}: JSON is not an object")
    return data

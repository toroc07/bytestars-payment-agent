"""Groq and OpenRouter through their OpenAI-compatible endpoint. Backup providers when Gemini cannot answer.

Groq reads text only. OpenRouter can also read images when its model accepts them (OPENROUTER_MODEL); PDFs
reach it as text (a PDF with a text layer is always sent as text) and scanned PDFs are left to Gemini.
"""

import base64
import json
import re
import time
from typing import Any

import httpx

from app.llm.base import LLMError, LLMRequest

TIMEOUT_S = 30.0
RATE_LIMIT_PAUSE_S = 60  # free models allow few requests per minute: skip instead of waiting
DAILY_LIMIT_PAUSE_S = 3600
OVERLOAD_PAUSE_S = 120
JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


class OpenAICompatProvider:
    def __init__(self, name: str, api_key: str, base_url: str, model: str, vision: bool = False):
        self.name = name
        self._api_key = api_key
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._model = model
        self._vision = vision
        self._paused_until = 0.0
        self._json_mode = True  # some free models reject response_format; remember it

    def supports(self, request: LLMRequest) -> bool:
        if not self._api_key or time.monotonic() < self._paused_until:
            return False
        if not request.has_file:
            return True
        return self._vision and (request.mime_type or "").startswith("image/")

    def _user_content(self, request: LLMRequest) -> Any:
        if not request.has_file:
            return request.text
        data = base64.b64encode(request.file_bytes or b"").decode("ascii")
        return [
            {"type": "text", "text": request.text},
            {"type": "image_url", "image_url": {"url": f"data:{request.mime_type};base64,{data}"}},
        ]

    def generate_json(self, request: LLMRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": self._user_content(request)},
            ],
        }
        for _attempt in range(2):  # the second try only happens without response_format
            if self._json_mode:
                payload["response_format"] = {"type": "json_object"}
            else:
                payload.pop("response_format", None)
            try:
                response = httpx.post(self._url, json=payload, timeout=TIMEOUT_S,
                                      headers={"Authorization": f"Bearer {self._api_key}",
                                               "X-Title": "ByteStars Payment Agent"})
            except httpx.HTTPError as exc:  # timeout or dropped connection
                self._paused_until = time.monotonic() + OVERLOAD_PAUSE_S
                raise LLMError(f"{self.name}: {type(exc).__name__}") from exc
            if response.status_code == 400 and self._json_mode:
                self._json_mode = False
                continue
            if response.status_code == 429:
                daily = "per-day" in response.text.lower() or "daily" in response.text.lower()
                self._paused_until = time.monotonic() + (DAILY_LIMIT_PAUSE_S if daily else RATE_LIMIT_PAUSE_S)
            elif response.status_code >= 500 or response.status_code in (401, 402, 403, 404):
                # Server trouble, bad key, no credit or unknown model: try again later, not on every invoice.
                self._paused_until = time.monotonic() + OVERLOAD_PAUSE_S
            if response.status_code != 200:
                raise LLMError(f"{self.name}: HTTP {response.status_code}")
            return _as_object(response, self.name)
        raise LLMError(f"{self.name}: could not get JSON")


def _as_object(response: httpx.Response, name: str) -> dict[str, Any]:
    """The reply as a JSON object, also when the model wraps it in text or a ```json fence."""
    try:
        content = response.json()["choices"][0]["message"]["content"] or ""
        match = JSON_OBJECT.search(content)
        data = json.loads(match.group(0) if match else content)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise LLMError(f"{name}: invalid JSON") from exc
    if not isinstance(data, dict):
        raise LLMError(f"{name}: JSON is not an object")
    return data


def groq(api_key: str, model: str) -> OpenAICompatProvider:
    """One Groq model (text only): fast backup for chats, emails and PDFs with text."""
    return OpenAICompatProvider(f"groq ({model})", api_key, "https://api.groq.com/openai/v1", model)


def openrouter(api_key: str, model: str) -> OpenAICompatProvider:
    """One OpenRouter model; it reads images too (free models with vision, e.g. google/gemma-4-31b-it:free)."""
    return OpenAICompatProvider(f"openrouter ({model})", api_key, "https://openrouter.ai/api/v1", model, vision=True)

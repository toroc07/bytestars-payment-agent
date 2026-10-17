"""Groq and OpenRouter through their OpenAI-compatible endpoint. Backup providers, text only."""

import json
from typing import Any

import httpx

from app.llm.base import LLMError, LLMRequest

TIMEOUT_S = 45.0


class OpenAICompatProvider:
    def __init__(self, name: str, api_key: str, base_url: str, model: str):
        self.name = name
        self._api_key = api_key
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._model = model

    def supports(self, request: LLMRequest) -> bool:
        return bool(self._api_key) and not request.has_file

    def generate_json(self, request: LLMRequest) -> dict[str, Any]:
        payload = {
            "model": self._model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.text},
            ],
        }
        try:
            response = httpx.post(
                self._url, json=payload, timeout=TIMEOUT_S,
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            data = json.loads(content)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMError(f"{self.name}: {type(exc).__name__}") from exc
        if not isinstance(data, dict):
            raise LLMError(f"{self.name}: JSON is not an object")
        return data


def groq(api_key: str) -> OpenAICompatProvider:
    return OpenAICompatProvider("groq", api_key, "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile")


def openrouter(api_key: str) -> OpenAICompatProvider:
    return OpenAICompatProvider(
        "openrouter", api_key, "https://openrouter.ai/api/v1", "meta-llama/llama-3.3-70b-instruct:free"
    )

"""OpenRouter backup: reads images too, survives models without JSON mode, skips itself when rate-limited."""

import json

import httpx
import pytest

from app.llm import openai_compat
from app.llm.base import LLMError, LLMRequest
from app.llm.openai_compat import openrouter

IMAGE = LLMRequest(system="s", text="<documento>…</documento>", file_bytes=b"\x89PNG fake", mime_type="image/png")


def reply(status: int, content: str = "", text: str = "") -> httpx.Response:
    body = {"choices": [{"message": {"content": content}}]} if status == 200 else {"error": {"message": text}}
    return httpx.Response(status, json=body, request=httpx.Request("POST", "https://openrouter.ai"))


def test_reads_images_but_leaves_scanned_pdfs_to_gemini():
    provider = openrouter("key", "google/gemma-4-31b-it:free")
    assert provider.supports(IMAGE)
    assert not provider.supports(LLMRequest(system="s", text="t", file_bytes=b"%PDF", mime_type="application/pdf"))
    assert not openrouter("", "m").supports(IMAGE)


def test_sends_the_image_and_retries_without_json_mode(monkeypatch):
    calls = []

    def fake_post(url, json, timeout, headers):
        calls.append(json)
        if "response_format" in json:
            return reply(400, text="response_format not supported")
        return reply(200, content='Aquí está:\n```json\n{"invoice_number": "MIC-430", "amount": "10043.60"}\n```')

    monkeypatch.setattr(openai_compat.httpx, "post", fake_post)
    data = openrouter("key", "m").generate_json(IMAGE)
    assert data == {"invoice_number": "MIC-430", "amount": "10043.60"}
    image_part = calls[0]["messages"][1]["content"][1]
    assert image_part["image_url"]["url"].startswith("data:image/png;base64,")
    assert len(calls) == 2 and "response_format" not in calls[1]


def test_rate_limited_model_is_skipped(monkeypatch):
    monkeypatch.setattr(openai_compat.httpx, "post", lambda *a, **k: reply(429, text="Rate limit exceeded: free-models-per-day"))
    provider = openrouter("key", "m")
    with pytest.raises(LLMError):
        provider.generate_json(IMAGE)
    assert provider.supports(IMAGE) is False


def test_backup_answers_when_every_gemini_model_fails(monkeypatch):
    from app.llm import LLMChain
    from tests.agent.fakes import FakeProvider

    monkeypatch.setattr(openai_compat.httpx, "post", lambda *a, **k: reply(200, content=json.dumps({"amount": "1.00"})))
    chain = LLMChain([FakeProvider("gemini-3.8-flash", answer=None), FakeProvider("gemini-3.5-flash", answer=None),
                      openrouter("key", "google/gemma-4-31b-it:free")])
    data, source = chain.generate_json(IMAGE)
    assert data == {"amount": "1.00"} and source == "openrouter (google/gemma-4-31b-it:free)"

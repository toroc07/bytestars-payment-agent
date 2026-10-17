"""Shared test setup: no test may call a real LLM provider, even if a developer has API keys in .env."""

import pytest

from app.agent import pipeline
from app.llm import LLMChain


@pytest.fixture(autouse=True)
def offline_llm(monkeypatch):
    monkeypatch.setattr(pipeline, "get_llm", lambda: LLMChain([], cache=None))

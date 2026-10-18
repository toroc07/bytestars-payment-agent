"""LLM providers (docs/ARCHITECTURE.md §3). The LLM only reads invoices and writes text; it never decides."""

from functools import lru_cache

from app.config import settings
from app.llm.base import LLMError, LLMRequest, LLMUnavailable, Provider
from app.llm.chain import JsonCache, LLMChain, default_cache_folder
from app.llm.gemini import GeminiProvider
from app.llm.openai_compat import groq, openrouter

__all__ = ["JsonCache", "LLMChain", "LLMError", "LLMRequest", "LLMUnavailable", "Provider", "get_llm"]


@lru_cache(maxsize=1)
def get_llm() -> LLMChain:
    """Chain built from the environment: LLM_PROVIDER_ORDER, the API keys and LLM_CACHE.

    GEMINI_MODEL, GROQ_MODEL and OPENROUTER_MODEL may list several models separated by commas; each one is tried in order.
    """
    gemini_models = [m.strip() for m in settings.GEMINI_MODEL.split(",") if m.strip()]
    openrouter_models = [m.strip() for m in settings.OPENROUTER_MODEL.split(",") if m.strip()]
    groq_models = [m.strip() for m in settings.GROQ_MODEL.split(",") if m.strip()]
    factories = {
        "gemini": lambda: [GeminiProvider(settings.GEMINI_API_KEY, model) for model in gemini_models],
        "groq": lambda: [groq(settings.GROQ_API_KEY, model) for model in groq_models],
        "openrouter": lambda: [openrouter(settings.OPENROUTER_API_KEY, model) for model in openrouter_models],
    }
    order = [name.strip().lower() for name in settings.LLM_PROVIDER_ORDER.split(",")]
    providers = [p for name in order if name in factories for p in factories[name]()]
    cache = JsonCache(default_cache_folder()) if settings.LLM_CACHE else None
    return LLMChain(providers, cache)

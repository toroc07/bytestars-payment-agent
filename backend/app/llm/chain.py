"""Provider chain with fallback and a content-hash cache (docs/ARCHITECTURE.md §3, step 3)."""

import hashlib
import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Any

from app.llm.base import LLMError, LLMRequest, LLMUnavailable, Provider

log = logging.getLogger(__name__)


class JsonCache:
    """Answers by hash of the whole request: the same invoice never spends quota twice.

    Lookup order: this process's memory, the durable store (the database, shared by every serverless
    instance and kept across demo resets) and a folder in the system temp dir.
    """

    def __init__(self, folder: Path | None = None, store=None):
        self._memory: dict[str, dict[str, Any]] = {}
        self._folder = folder
        self._store = store  # durable, shared by every instance (the database); any object with get/put

    @staticmethod
    def key(request: LLMRequest) -> str:
        digest = hashlib.sha256()
        for part in (request.system, request.text, request.mime_type or ""):
            digest.update(part.encode("utf-8"))
            digest.update(b"\0")
        digest.update(request.file_bytes or b"")
        return digest.hexdigest()

    def get(self, key: str) -> dict[str, Any] | None:
        if key in self._memory:
            return self._memory[key]
        if self._store is not None:
            try:
                if (data := self._store.get(key)) is not None:
                    self._memory[key] = data
                    return data
            except Exception:  # noqa: BLE001 - the cache is an optimization; a broken store is a miss
                log.warning("LLM cache store read failed")
        if self._folder:
            try:
                data = json.loads((self._folder / f"{key}.json").read_text(encoding="utf-8"))
                self._memory[key] = data
                return data
            except (OSError, ValueError):
                return None
        return None

    def put(self, key: str, value: dict[str, Any]) -> None:
        self._memory[key] = value
        if self._store is not None:
            try:
                self._store.put(key, value)
            except Exception:  # noqa: BLE001 - never fail the request because of the cache
                log.warning("LLM cache store write failed")
        if self._folder:
            try:
                self._folder.mkdir(parents=True, exist_ok=True)
                (self._folder / f"{key}.json").write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            except OSError:
                pass  # the cache is an optimization; never fail the request because of it


class LLMChain:
    def __init__(self, providers: list[Provider], cache: JsonCache | None = None):
        self.providers = providers
        self.cache = cache

    def with_store(self, store) -> "LLMChain":
        """Same providers, with a durable store (e.g. the database) behind this chain's cache."""
        folder = self.cache._folder if self.cache else None
        cache = JsonCache(folder, store)
        if self.cache:
            cache._memory = self.cache._memory  # keep what this process already read
        return LLMChain(self.providers, cache)

    @property
    def available(self) -> list[str]:
        probe = LLMRequest(system="", text="")
        return [p.name for p in self.providers if p.supports(probe)]

    def generate_json(self, request: LLMRequest) -> tuple[dict[str, Any], str]:
        """Returns (json, provider name). Raises LLMUnavailable if nothing answered."""
        key = JsonCache.key(request) if self.cache else ""
        if self.cache and (hit := self.cache.get(key)) is not None:
            return hit, "cache"
        errors = []
        for provider in self.providers:
            if not provider.supports(request):
                continue
            started = time.monotonic()
            try:
                data = provider.generate_json(request)
            except LLMError as exc:  # never log the invoice content, only who failed and how long it took
                log.warning("LLM provider failed after %.1f s: %s", time.monotonic() - started, exc)
                errors.append(str(exc))
                continue
            log.warning("LLM provider %s answered in %.1f s", provider.name, time.monotonic() - started)
            if self.cache:
                self.cache.put(key, data)
            return data, provider.name
        raise LLMUnavailable("; ".join(errors) or "no hay proveedor de LLM configurado para esta entrada")


def default_cache_folder() -> Path:
    return Path(tempfile.gettempdir()) / "bytestars-llm-cache"

"""Common shape of an LLM call. Providers only turn a request into JSON; they never decide anything."""

from dataclasses import dataclass
from typing import Any, Protocol


class LLMError(Exception):
    """A provider failed (no key, quota, network, invalid JSON). The chain moves on to the next one."""


class LLMUnavailable(LLMError):
    """Every provider failed or none could take the request."""


@dataclass(frozen=True)
class LLMRequest:
    system: str
    text: str
    file_bytes: bytes | None = None
    mime_type: str | None = None  # set with file_bytes: application/pdf, image/png, image/jpeg

    @property
    def has_file(self) -> bool:
        return self.file_bytes is not None


class Provider(Protocol):
    name: str

    def supports(self, request: LLMRequest) -> bool:
        """False when the provider cannot take this input (e.g. text-only model and an image)."""
        ...

    def generate_json(self, request: LLMRequest) -> dict[str, Any]: ...

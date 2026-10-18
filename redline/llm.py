"""Model backends.

Redline talks to a model through one tiny interface (:class:`ChatModel`), so the
rest of the code never cares which open-weight model is loaded. The default
backend is a local Ollama server running an open model such as Gemma.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

DEFAULT_MODEL = "gemma3:4b"
DEFAULT_HOST = "http://localhost:11434"

INSTALL_HELP = (
    "Could not reach the local model.\n"
    f"  Redline talks to Ollama at {DEFAULT_HOST} by default.\n"
    "  1. Install Ollama:  https://ollama.com/download\n"
    "  2. Start it:        ollama serve\n"
    f"  3. Pull a model:    ollama pull {DEFAULT_MODEL}\n"
    "  Or run the built-in checks only:  redline contract.txt --offline"
)


class ModelError(RuntimeError):
    """The model backend is unreachable or returned something unusable."""


class ChatModel(Protocol):
    """The one method Redline needs from any model."""

    def complete(self, system: str, user: str, *, json_mode: bool = True) -> str:
        ...  # pragma: no cover - protocol definition


@dataclass
class OllamaModel:
    """A local open-weight model served by Ollama."""

    model: str = DEFAULT_MODEL
    host: str = DEFAULT_HOST
    temperature: float = 0.1
    timeout: int = 600

    def complete(self, system: str, user: str, *, json_mode: bool = True) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "options": {"temperature": self.temperature},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            payload["format"] = "json"
        request = urllib.request.Request(
            f"{self.host.rstrip('/')}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ModelError(f"{INSTALL_HELP}\n  ({exc})") from exc

        content = (body.get("message") or {}).get("content")
        if not content:
            raise ModelError(f"the model returned no content: {body!r}")
        return content

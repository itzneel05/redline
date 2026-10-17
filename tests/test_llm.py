from __future__ import annotations

import json
import urllib.error

import pytest

from redline import llm


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


def test_complete_posts_chat_and_returns_content(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse(json.dumps({"message": {"content": "hello"}}).encode())

    monkeypatch.setattr(llm.urllib.request, "urlopen", fake_urlopen)
    model = llm.OllamaModel(model="gemma3:4b", host="http://localhost:11434")

    assert model.complete("sys", "usr") == "hello"
    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["body"]["format"] == "json"
    assert captured["body"]["stream"] is False
    assert captured["body"]["model"] == "gemma3:4b"
    assert captured["body"]["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "usr"},
    ]


def test_complete_strips_trailing_slash_from_host(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        return FakeResponse(b'{"message": {"content": "ok"}}')

    monkeypatch.setattr(llm.urllib.request, "urlopen", fake_urlopen)
    llm.OllamaModel(host="http://localhost:11434/").complete("s", "u")
    assert captured["url"] == "http://localhost:11434/api/chat"


def test_complete_raises_model_error_when_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout=None):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(llm.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(llm.ModelError) as excinfo:
        llm.OllamaModel().complete("s", "u")
    assert "ollama" in str(excinfo.value).lower()


def test_complete_raises_when_content_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        llm.urllib.request,
        "urlopen",
        lambda request, timeout=None: FakeResponse(b"{}"),
    )
    with pytest.raises(llm.ModelError):
        llm.OllamaModel().complete("s", "u")

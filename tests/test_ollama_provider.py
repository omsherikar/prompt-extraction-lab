"""Tests for OllamaProvider — fully offline (no real network).

The HTTP layer is mocked by replacing ``urllib.request.urlopen`` with a fake that records
the ``Request`` it received and returns a canned JSON response. We then inspect the captured
request (URL, headers, body) to assert host resolution, auth handling, and body shape.
"""

from __future__ import annotations

import json
import urllib.error

import pytest

from src.providers.ollama_provider import OllamaProvider

CANNED = {"message": {"role": "assistant", "content": "CANNED REPLY"}}


class _FakeResponse:
    """Minimal context-manager response object mimicking urlopen's return value."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._payload


class _Capture:
    """Records the most recent Request passed to the fake urlopen."""

    def __init__(self) -> None:
        self.request = None

    def urlopen(self, request, *args, **kwargs):
        self.request = request
        return _FakeResponse(json.dumps(CANNED).encode())


@pytest.fixture
def capture(monkeypatch: pytest.MonkeyPatch) -> _Capture:
    cap = _Capture()
    monkeypatch.setattr("urllib.request.urlopen", cap.urlopen)
    return cap


def test_cloud_path_uses_ollama_com_and_bearer_auth(
    capture: _Capture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OLLAMA_API_KEY", "secret-key-123")
    provider = OllamaProvider("llama3.1", temperature=0.0)

    out = provider.complete("SYSTEM", "USER")

    assert out == "CANNED REPLY"
    req = capture.request
    assert req.full_url == "https://ollama.com/api/chat"
    assert req.get_header("Authorization") == "Bearer secret-key-123"


def test_local_path_uses_localhost_and_no_auth(
    capture: _Capture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    provider = OllamaProvider("llama3.1")

    out = provider.complete("SYSTEM", "USER")

    assert out == "CANNED REPLY"
    req = capture.request
    assert req.full_url == "http://localhost:11434/api/chat"
    # urllib normalizes header names to title-case; there must be no Authorization header.
    assert req.get_header("Authorization") is None


def test_body_contains_model_messages_in_order_and_temperature(
    capture: _Capture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    provider = OllamaProvider("my-model", temperature=0.7)

    provider.complete("SYS PROMPT", "USER MSG")

    body = json.loads(capture.request.data.decode())
    assert body["model"] == "my-model"
    assert body["stream"] is False
    assert body["messages"] == [
        {"role": "system", "content": "SYS PROMPT"},
        {"role": "user", "content": "USER MSG"},
    ]
    assert body["options"]["temperature"] == 0.7


def test_explicit_host_overrides_env_default(
    capture: _Capture, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Even with a cloud key set, an explicit host wins.
    monkeypatch.setenv("OLLAMA_API_KEY", "secret-key-123")
    provider = OllamaProvider("llama3.1", host="http://example.test:9999/")

    provider.complete("SYSTEM", "USER")

    # Trailing slash on host is stripped.
    assert capture.request.full_url == "http://example.test:9999/api/chat"


def test_local_host_from_env_var(
    capture: _Capture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.setenv("OLLAMA_HOST", "http://remote-box:11434")
    provider = OllamaProvider("llama3.1")

    provider.complete("SYSTEM", "USER")

    assert capture.request.full_url == "http://remote-box:11434/api/chat"
    assert capture.request.get_header("Authorization") is None


def test_http_error_raises_clear_error_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_API_KEY", "secret-key-123")

    def boom(request, *args, **kwargs):
        raise urllib.error.HTTPError(
            url=request.full_url, code=500, msg="Server Error", hdrs=None, fp=None
        )

    monkeypatch.setattr("urllib.request.urlopen", boom)
    provider = OllamaProvider("llama3.1")

    with pytest.raises(RuntimeError) as excinfo:
        provider.complete("SYSTEM", "USER")

    message = str(excinfo.value)
    assert "secret-key-123" not in message  # never leak the key
    assert "ollama.com" in message  # host is reported
    assert "500" in message  # status is reported


def test_url_error_raises_clear_error_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_API_KEY", "secret-key-123")

    def boom(request, *args, **kwargs):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    provider = OllamaProvider("llama3.1")

    with pytest.raises(RuntimeError) as excinfo:
        provider.complete("SYSTEM", "USER")

    message = str(excinfo.value)
    assert "secret-key-123" not in message
    assert "ollama.com" in message


def test_timeout_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # A stalled request must not hang forever: a timeout surfaces as a clear RuntimeError.
    def boom(request, *args, **kwargs):
        raise TimeoutError("read timed out")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    provider = OllamaProvider("llama3.1", host="http://localhost:11434", timeout=5.0)

    with pytest.raises(RuntimeError) as excinfo:
        provider.complete("SYSTEM", "USER")

    assert "timed out" in str(excinfo.value)


def test_error_body_is_surfaced_clearly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Ollama returns model/runtime problems as {"error": ...}; surface it, not a KeyError.
    payload = {"error": 'model "gpt-oss:120b-cloud" not found, try pulling it first'}

    def fake(request, *args, **kwargs):
        return _FakeResponse(json.dumps(payload).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake)
    provider = OllamaProvider("gpt-oss:120b-cloud", host="http://localhost:11434")

    with pytest.raises(RuntimeError) as excinfo:
        provider.complete("SYSTEM", "USER")

    assert "not found" in str(excinfo.value)


def test_unexpected_response_shape_raises_runtimeerror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A body with neither "error" nor message/content yields a clear RuntimeError, not KeyError.
    def fake(request, *args, **kwargs):
        return _FakeResponse(json.dumps({"unexpected": "shape"}).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake)
    provider = OllamaProvider("llama3.1", host="http://localhost:11434")

    with pytest.raises(RuntimeError) as excinfo:
        provider.complete("SYSTEM", "USER")

    assert "unexpected" in str(excinfo.value).lower()

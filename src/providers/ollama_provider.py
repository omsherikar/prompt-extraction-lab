"""Ollama backend (local + cloud).

Talks to the Ollama ``/api/chat`` endpoint, which is identical for the hosted service
(Ollama Cloud) and a self-hosted server. The only differences are the host and whether an
``Authorization: Bearer`` header is sent.

Host resolution (in __init__):
  1. An explicit ``host=`` argument always wins.
  2. Otherwise, if ``OLLAMA_API_KEY`` is set in the environment, default to Ollama Cloud
     (``https://ollama.com``) and send the bearer token.
  3. Otherwise, use a local server (``OLLAMA_HOST`` or ``http://localhost:11434``) with no
     auth.

The API key is read from the environment only; it is never hardcoded, logged, or included
in error messages. Pure stdlib (``json``, ``os``, ``urllib``) — no extra dependency.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from src.providers.base import Provider

CLOUD_HOST = "https://ollama.com"
DEFAULT_LOCAL_HOST = "http://localhost:11434"


class OllamaProvider(Provider):
    """Wraps the Ollama ``/api/chat`` endpoint (cloud or local server)."""

    def __init__(
        self,
        model_id: str,
        temperature: float = 0.0,
        host: str | None = None,
        max_tokens: int = 2048,
    ) -> None:
        super().__init__(model_id, temperature)
        self.max_tokens = max_tokens
        # Read the key from the environment only (may be None for a local server).
        self._api_key = os.environ.get("OLLAMA_API_KEY")

        if host is not None:
            resolved = host
        elif self._api_key:
            resolved = CLOUD_HOST
        else:
            resolved = os.environ.get("OLLAMA_HOST", DEFAULT_LOCAL_HOST)
        self.host = resolved.rstrip("/")

    def complete(self, system_prompt: str, user_message: str) -> str:
        url = f"{self.host}/api/chat"
        body = {
            "model": self.model_id,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        request = urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST"
        )

        try:
            with urllib.request.urlopen(request) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # Report host + status; never include the api key.
            raise RuntimeError(
                f"Ollama request to {self.host} failed with HTTP {exc.code}: {exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Ollama request to {self.host} failed: {exc.reason}"
            ) from exc

        return data["message"]["content"]

"""Anthropic backend (primary).

Implements the Anthropic Messages API. The system prompt goes in the top-level `system`
field; the attack (or benign) query goes in as the user message. The API key is read from
the environment (ANTHROPIC_API_KEY) by the SDK; never hardcode or log it.

Note: `temperature` (and `top_p`/`top_k`) are rejected with a 400 on Opus 4.7/4.8 and
Fable 5, but accepted on Haiku 4.5 / Sonnet 4.6. So temperature is sent only when it is
not None; for a newer model, leave temperature null in config. `thinking`/`effort` are
omitted entirely for cross-model safety.
"""

from __future__ import annotations

import anthropic

from src.providers.base import Provider


class AnthropicProvider(Provider):
    """Wraps the Anthropic Messages API."""

    def __init__(
        self, model_id: str, temperature: float | None = 0.0, max_tokens: int = 2048
    ) -> None:
        super().__init__(model_id, temperature if temperature is not None else 0.0)
        # None means "do not send temperature" (newer models reject the parameter).
        self._temperature = temperature
        self.max_tokens = max_tokens
        self._client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    def complete(self, system_prompt: str, user_message: str) -> str:
        kwargs: dict = {
            "model": self.model_id,
            "max_tokens": self.max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }
        if self._temperature is not None:
            kwargs["temperature"] = self._temperature

        response = self._client.messages.create(**kwargs)
        # A refusal (stop_reason == "refusal") is a meaningful "did not leak" result; we
        # capture whatever text is present rather than raising, so it scores like any
        # other response. Concatenate text blocks; non-text blocks are ignored.
        return "".join(block.text for block in response.content if block.type == "text")

"""Anthropic backend (primary).

Phase 0: implement against the Anthropic Messages API. The system prompt goes in the
top-level `system` field; the attack query goes in as the user message. Read the API key
from the environment (ANTHROPIC_API_KEY) via python-dotenv; never hardcode or log it.
"""

from __future__ import annotations

from src.providers.base import Provider


class AnthropicProvider(Provider):
    """Wraps the Anthropic Messages API."""

    def __init__(self, model_id: str, temperature: float = 0.0, max_tokens: int = 2048) -> None:
        super().__init__(model_id, temperature)
        self.max_tokens = max_tokens
        # Phase 0: construct the anthropic client here (reads ANTHROPIC_API_KEY from env).

    def complete(self, system_prompt: str, user_message: str) -> str:
        # Phase 0: call messages.create(model=self.model_id, system=system_prompt,
        # messages=[{"role": "user", "content": user_message}], temperature=self.temperature,
        # max_tokens=self.max_tokens) and return the concatenated text content.
        raise NotImplementedError("Phase 0: implement Anthropic Messages call")

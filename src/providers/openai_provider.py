"""OpenAI backend (optional).

Only needed to strengthen the cross-model claim. Requires the [openai] extra and
OPENAI_API_KEY. Mirrors AnthropicProvider: system prompt in the system message, attack
query as the user message.
"""

from __future__ import annotations

from src.providers.base import Provider


class OpenAIProvider(Provider):
    """Wraps the OpenAI Chat Completions API. Optional."""

    def __init__(self, model_id: str, temperature: float = 0.0, max_tokens: int = 2048) -> None:
        super().__init__(model_id, temperature)
        self.max_tokens = max_tokens
        # Optional: construct the openai client here (reads OPENAI_API_KEY from env).

    def complete(self, system_prompt: str, user_message: str) -> str:
        # Optional: call chat.completions.create with a system message + user message and
        # return the assistant text.
        raise NotImplementedError("Optional backend: implement OpenAI call if enabled in config")

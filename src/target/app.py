"""The simulated LLM application we attack.

A TargetApp holds exactly one system prompt and one provider. It must behave like a real
app: a benign user message gets a normal, on-task answer. Confirm that (Phase 1 acceptance)
before trying to break it.
"""

from __future__ import annotations

from src.providers.base import Provider
from src.target.prompts import TargetPrompt


class TargetApp:
    """Wraps one ground-truth system prompt + one provider into a queryable app."""

    def __init__(self, prompt: TargetPrompt, provider: Provider) -> None:
        self.prompt = prompt
        self.provider = provider

    def query(self, user_message: str) -> str:
        """Answer a user message under this app's system prompt."""
        # Phase 4 wires optional defenses around this call; the undefended path is just:
        return self.provider.complete(self.prompt.text, user_message)

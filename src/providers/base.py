"""The Provider interface.

Intentionally minimal: one method. Model id and temperature are fixed at construction.
Keeping this narrow is what makes adding a second backend trivial, which is what supports
the "extractability varies across models" claim in the post.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Provider(ABC):
    """A model backend. Constructed with a model id and a sampling temperature."""

    def __init__(self, model_id: str, temperature: float = 0.0) -> None:
        self.model_id = model_id
        self.temperature = temperature

    @abstractmethod
    def complete(self, system_prompt: str, user_message: str) -> str:
        """Send one (system, user) pair and return the model's text response.

        The system prompt is the secret we are studying; the user message is the attack
        query (or a benign message). Implementations must put the system prompt in the
        backend's dedicated system field, not concatenated into the user turn.
        """
        raise NotImplementedError

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"{type(self).__name__}(model_id={self.model_id!r}, temperature={self.temperature})"

# tests/test_provider_factory.py
"""Tests for `build_provider` dispatch (src/experiment/run.py).

Fully OFFLINE: no network, no API key. `build_provider` maps a ModelSpec to a Provider by
dispatching on `spec.provider`. Construction is lazy and side-effect free — neither the
Ollama nor the Anthropic provider performs network I/O or requires a key at __init__ time —
so these assertions hold with the environment stripped of every key.
"""

from __future__ import annotations

import pytest

from src.experiment.config import ModelSpec
from src.experiment.run import build_provider
from src.providers.anthropic_provider import AnthropicProvider
from src.providers.ollama_provider import OllamaProvider


def test_ollama_spec_builds_ollama_provider() -> None:
    """An ollama spec yields an OllamaProvider with the right model_id, no key/network."""
    provider = build_provider(ModelSpec("ollama", "gpt-oss:120b-cloud", 0.0))

    assert isinstance(provider, OllamaProvider)
    assert provider.model_id == "gpt-oss:120b-cloud"


def test_anthropic_spec_builds_anthropic_provider() -> None:
    """An anthropic spec yields an AnthropicProvider; construction needs no key at init."""
    provider = build_provider(ModelSpec("anthropic", "claude-haiku-4-5-20251001", 0.0))

    assert isinstance(provider, AnthropicProvider)
    assert provider.model_id == "claude-haiku-4-5-20251001"


def test_unknown_provider_raises_systemexit() -> None:
    """An unrecognized provider fails loudly with SystemExit (no silent fallback)."""
    with pytest.raises(SystemExit):
        build_provider(ModelSpec("bogus", "x", 0.0))

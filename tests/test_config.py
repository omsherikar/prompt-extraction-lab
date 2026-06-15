# tests/test_config.py
"""Tests for Phase 0 config loading + validation (src/experiment/config.py).

These tests are TDD: they describe the required behavior of `load_config` before its
implementation exists. They are fast and deterministic — no network, no API calls, and
the real config.yaml is read-only (never mutated). Malformed-config cases write to the
`tmp_path` fixture so the repo's config.yaml is never touched.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from src.experiment.config import (
    ExperimentConfig,
    ModelSpec,
    NormalizationConfig,
    load_config,
)

# Repo root is two levels up from this file (tests/ -> repo root).
REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_CONFIG = REPO_ROOT / "config.yaml"


def test_load_real_config_scalars() -> None:
    """load_config('config.yaml') parses the real config's scalar fields exactly.

    Requirement: seed=1729, query_budget=20, repeats=3, output_filter_threshold == 0.5,
    returned as a fully-typed ExperimentConfig.
    """
    cfg = load_config(str(REAL_CONFIG))

    assert isinstance(cfg, ExperimentConfig)
    assert cfg.seed == 1729
    assert cfg.query_budget == 20
    assert cfg.repeats == 3
    assert cfg.output_filter_threshold == 0.5


def test_load_real_config_models_parsed_into_modelspec() -> None:
    """The first models entry is parsed into a ModelSpec with the expected provider/model.

    Requirement: models is a list of ModelSpec; models[0] is the Ollama primary
    (provider='ollama', model_id='gpt-oss:120b-cloud', temperature=0.0).
    """
    cfg = load_config(str(REAL_CONFIG))

    assert isinstance(cfg.models, list)
    assert len(cfg.models) >= 1
    first = cfg.models[0]
    assert isinstance(first, ModelSpec)
    assert first.provider == "ollama"
    assert first.model_id == "gpt-oss:120b-cloud"
    assert first.temperature == 0.0


def test_load_real_config_normalization_flags_all_true() -> None:
    """The normalization map is threaded into a NormalizationConfig with all flags True.

    Requirement: lowercase / collapse_whitespace / strip all True in the real config.
    """
    cfg = load_config(str(REAL_CONFIG))

    assert isinstance(cfg.normalization, NormalizationConfig)
    assert cfg.normalization.lowercase is True
    assert cfg.normalization.collapse_whitespace is True
    assert cfg.normalization.strip is True


def test_load_real_config_prompt_types_and_defenses() -> None:
    """prompt_types and defenses are read as the configured lists.

    Requirement: prompt_types == [direct, role, in_context] and defenses include the
    three configured strategies.
    """
    cfg = load_config(str(REAL_CONFIG))

    assert cfg.prompt_types == ["direct", "role", "in_context"]
    assert cfg.defenses == ["none", "instructional", "output_filter"]


def test_load_real_config_nested_output_dirs_threaded() -> None:
    """The nested `output:` map is flattened into results_dir / transcripts_dir.

    Requirement: output.results_dir -> cfg.results_dir == 'data/results' and
    output.transcripts_dir -> cfg.transcripts_dir == 'data/transcripts'.
    """
    cfg = load_config(str(REAL_CONFIG))

    assert cfg.results_dir == "data/results"
    assert cfg.transcripts_dir == "data/transcripts"


def _write_yaml(tmp_path: Path, body: str) -> Path:
    """Helper: write a config body to an isolated temp file and return its path."""
    bad = tmp_path / "config.yaml"
    bad.write_text(body, encoding="utf-8")
    return bad


def test_missing_required_key_raises_valueerror_naming_key(tmp_path: Path) -> None:
    """A config missing a required key (`seed`) raises ValueError naming that key.

    Requirement: validation fails loudly and early; the error message names the missing
    key so the failure is actionable. Uses tmp_path; the real config.yaml is untouched.
    """
    body = (
        # `seed` intentionally omitted.
        "models:\n"
        "  - provider: anthropic\n"
        "    model_id: claude-haiku-4-5-20251001\n"
        "    temperature: 0.0\n"
        "query_budget: 20\n"
        "repeats: 3\n"
        "normalization:\n"
        "  lowercase: true\n"
        "  collapse_whitespace: true\n"
        "  strip: true\n"
        "prompt_types: [direct, role, in_context]\n"
        "defenses: [none, instructional, output_filter]\n"
        "output_filter_threshold: 0.5\n"
        "output:\n"
        "  results_dir: data/results\n"
        "  transcripts_dir: data/transcripts\n"
    )
    bad_path = _write_yaml(tmp_path, body)

    with pytest.raises(ValueError) as excinfo:
        load_config(str(bad_path))

    assert "seed" in str(excinfo.value), (
        "ValueError message must name the missing 'seed' key; "
        f"got: {excinfo.value!r}"
    )


def test_real_config_is_not_mutated_by_loading() -> None:
    """Loading the real config.yaml must not modify it on disk (read-only contract)."""
    before = REAL_CONFIG.read_bytes()
    load_config(str(REAL_CONFIG))
    after = REAL_CONFIG.read_bytes()

    assert before == after


def test_import_requires_no_api_key_and_no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing src.experiment.config needs no API key and performs no network I/O.

    Requirement: config loading is a pure local concern. With all provider API keys
    stripped from the environment and the socket layer disabled, a fresh import of the
    module (and a load of the real config) must still succeed.
    """
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)

    # Make any attempt to open a network socket fail loudly during this test.
    import socket

    def _no_network(*args: object, **kwargs: object) -> None:  # pragma: no cover - guard
        raise AssertionError("network access attempted during config import/load")

    monkeypatch.setattr(socket, "socket", _no_network)

    # Force a fresh import to prove import-time has no key/network requirement.
    monkeypatch.delitem(sys.modules, "src.experiment.config", raising=False)
    import importlib

    module = importlib.import_module("src.experiment.config")

    # And a real load still works without keys or network.
    cfg = module.load_config(str(REAL_CONFIG))
    assert isinstance(cfg, module.ExperimentConfig)

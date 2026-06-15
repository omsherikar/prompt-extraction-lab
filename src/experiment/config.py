"""Load and validate config.yaml.

A run must be reproducible from (config.yaml + seed), so config is the single source of truth
for models, budgets, normalization, defenses, and the seed. Bad config fails loudly and early.

Phase 0/5: implement loading + validation. The dataclasses below document the schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import yaml


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model_id: str
    temperature: float = 0.0


@dataclass(frozen=True)
class NormalizationConfig:
    lowercase: bool = True
    collapse_whitespace: bool = True
    strip: bool = True


@dataclass(frozen=True)
class ExperimentConfig:
    seed: int
    models: list[ModelSpec]
    query_budget: int
    repeats: int
    normalization: NormalizationConfig
    prompt_types: list[str]
    defenses: list[str]
    output_filter_threshold: float
    results_dir: str
    transcripts_dir: str
    extra: dict = field(default_factory=dict)


def _require(d: dict, key: str) -> object:
    """Return d[key] or raise a clear ValueError naming the missing key."""
    if not isinstance(d, dict) or key not in d:
        raise ValueError(f"config.yaml missing required key: {key!r}")
    return d[key]


def load_config(path: str = "config.yaml") -> ExperimentConfig:
    """Parse and validate config.yaml into an ExperimentConfig. Fails loudly on bad config."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        raise ValueError("config.yaml must be a mapping at the top level")

    seed = _require(raw, "seed")
    if not isinstance(seed, int):
        raise ValueError("config key 'seed' must be an int")

    models_raw = _require(raw, "models")
    if not isinstance(models_raw, list) or not models_raw:
        raise ValueError("config key 'models' must be a non-empty list")
    models = [
        ModelSpec(
            provider=str(_require(m, "provider")),
            model_id=str(_require(m, "model_id")),
            temperature=float(m.get("temperature", 0.0)),
        )
        for m in models_raw
    ]

    norm_raw = _require(raw, "normalization")
    normalization = NormalizationConfig(
        lowercase=bool(norm_raw.get("lowercase", True)),
        collapse_whitespace=bool(norm_raw.get("collapse_whitespace", True)),
        strip=bool(norm_raw.get("strip", True)),
    )

    output_raw = _require(raw, "output")

    reserved = {
        "seed", "models", "query_budget", "repeats", "normalization",
        "prompt_types", "defenses", "output_filter_threshold", "output",
    }
    return ExperimentConfig(
        seed=seed,
        models=models,
        query_budget=int(_require(raw, "query_budget")),
        repeats=int(_require(raw, "repeats")),
        normalization=normalization,
        prompt_types=list(_require(raw, "prompt_types")),
        defenses=list(_require(raw, "defenses")),
        output_filter_threshold=float(_require(raw, "output_filter_threshold")),
        results_dir=str(_require(output_raw, "results_dir")),
        transcripts_dir=str(_require(output_raw, "transcripts_dir")),
        extra={k: v for k, v in raw.items() if k not in reserved},
    )

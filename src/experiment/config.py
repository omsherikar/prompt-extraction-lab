"""Load and validate config.yaml.

A run must be reproducible from (config.yaml + seed), so config is the single source of truth
for models, budgets, normalization, defenses, and the seed. Bad config fails loudly and early.

Phase 0/5: implement loading + validation. The dataclasses below document the schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field


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


def load_config(path: str = "config.yaml") -> ExperimentConfig:
    """Parse and validate config.yaml into an ExperimentConfig."""
    # Phase 0/5: read YAML, validate required keys and types, build the dataclasses, fail loudly
    # on anything missing or malformed.
    raise NotImplementedError("Phase 0/5: implement config loading + validation")

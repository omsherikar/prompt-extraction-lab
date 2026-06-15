"""Tests for the full-matrix orchestration `run_full` (src/experiment/run.py).

Fully OFFLINE: no network, no API key. A `LeakingFakeProvider` returns its system prompt
verbatim — simulating a total leak — so the defense pipeline can be exercised end to end
without a real model. `run_full` is called with that fake factory injected; the real
AnthropicProvider is never constructed, so importing the module needs no key.

What these tests pin:
  - the matrix is fully enumerated (models x prompts x attacks x defenses x repeats) and
    `query_count` matches the row count;
  - every per-response row carries the documented 10 keys;
  - results.json and results.csv are written under the temp results_dir, and the CSV
    re-reads to the same rows/header;
  - the defense pipeline is wired and scored at the right target: against a leaking
    provider, `none` leaks (exact True, rouge_l ~1.0) while the matching `output_filter`
    rows are redacted (secret no longer present -> exact False, rouge_l ~0). This proves
    output_filter is scored POST-filter (on what the attacker receives);
  - the group records exist and carry self_agreement / mean_rouge_l in [0, 1].

NOTE: the "evasion slips past the filter" demonstration (P4-A2) needs a *real* model that
actually transforms its output (spaced chars / base64); a verbatim-leaking fake cannot
evade an overlap filter. This offline test verifies the redaction *plumbing* (filter wired,
scored post-filter), not real evasion.
"""

from __future__ import annotations

import csv
import json

from src.attacks.queries import ATTACKS
from src.experiment.config import (
    ExperimentConfig,
    ModelSpec,
    NormalizationConfig,
)
from src.experiment.run import run_full
from src.providers.base import Provider
from src.target.prompts import PROMPTS

# The documented per-response row schema. Exactly these 10 keys, no more, no less.
REQUIRED_ROW_KEYS = {
    "model_id",
    "prompt_id",
    "prompt_type",
    "attack_id",
    "family",
    "defense",
    "repeat",
    "exact",
    "rouge_l",
    "token_f1",
}


class LeakingFakeProvider(Provider):
    """Offline provider that returns the system prompt verbatim (a total leak).

    Constructed via the Provider ABC's (model_id, temperature). No network: `complete`
    simply echoes the system prompt it was given, which is the worst case for leakage and
    lets the defenses be measured against a known-leaking baseline.
    """

    def complete(self, system_prompt: str, user_message: str) -> str:
        return system_prompt


def fake_factory(spec: ModelSpec) -> LeakingFakeProvider:
    """Map a ModelSpec to a leaking fake provider. No real provider is ever built."""
    return LeakingFakeProvider(spec.model_id, spec.temperature)


def _make_config(tmp_path) -> ExperimentConfig:
    """A small, fully-specified config writing under tmp_path (real dirs untouched)."""
    return ExperimentConfig(
        seed=1729,
        models=[ModelSpec("anthropic", "fake-model", 0.0)],
        query_budget=20,
        repeats=2,
        normalization=NormalizationConfig(),
        prompt_types=["direct", "role", "in_context"],
        defenses=["none", "instructional", "output_filter"],
        output_filter_threshold=0.5,
        results_dir=str(tmp_path / "results"),
        transcripts_dir=str(tmp_path / "transcripts"),
    )


def _selected_prompts(cfg: ExperimentConfig):
    return [p for p in PROMPTS.values() if p.type in cfg.prompt_types]


def test_writes_results_json_and_csv(tmp_path) -> None:
    cfg = _make_config(tmp_path)

    run_full(cfg, provider_factory=fake_factory)

    results_dir = tmp_path / "results"
    assert (results_dir / "results.json").is_file()
    assert (results_dir / "results.csv").is_file()


def test_row_count_matches_full_matrix_and_query_count(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    prompts = _selected_prompts(cfg)

    results = run_full(cfg, provider_factory=fake_factory)

    expected = len(prompts) * len(ATTACKS) * len(cfg.defenses) * cfg.repeats
    assert len(results["responses"]) == expected
    assert results["query_count"] == expected
    assert results["seed"] == cfg.seed


def test_every_row_has_the_ten_required_keys(tmp_path) -> None:
    cfg = _make_config(tmp_path)

    results = run_full(cfg, provider_factory=fake_factory)

    for row in results["responses"]:
        assert set(row) == REQUIRED_ROW_KEYS, f"unexpected row keys: {set(row)}"


def test_csv_round_trips_to_same_rows_and_header(tmp_path) -> None:
    cfg = _make_config(tmp_path)

    results = run_full(cfg, provider_factory=fake_factory)

    csv_path = tmp_path / "results" / "results.csv"
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        header = reader.fieldnames

    assert set(header) == REQUIRED_ROW_KEYS
    assert len(rows) == len(results["responses"])

    # The JSON file holds the same payload as the returned dict.
    with (tmp_path / "results" / "results.json").open(encoding="utf-8") as f:
        on_disk = json.load(f)
    assert on_disk["query_count"] == results["query_count"]
    assert len(on_disk["responses"]) == len(results["responses"])


def test_output_filter_redacts_what_none_leaks(tmp_path) -> None:
    """Against a verbatim-leaking provider, `none` leaks and `output_filter` redacts.

    Proves the filter is wired AND scored on the POST-filter response (what the attacker
    receives): the redaction marker contains none of the secret, so exact flips to False
    and rouge_l collapses toward 0 — even though the model leaked the whole prompt.
    """
    cfg = _make_config(tmp_path)
    prompts = _selected_prompts(cfg)

    results = run_full(cfg, provider_factory=fake_factory)
    rows = results["responses"]

    prompt_id = prompts[0].id
    attack_id = ATTACKS[0].id

    none_rows = [
        r
        for r in rows
        if r["prompt_id"] == prompt_id
        and r["attack_id"] == attack_id
        and r["defense"] == "none"
    ]
    filtered_rows = [
        r
        for r in rows
        if r["prompt_id"] == prompt_id
        and r["attack_id"] == attack_id
        and r["defense"] == "output_filter"
    ]

    assert len(none_rows) == cfg.repeats
    assert len(filtered_rows) == cfg.repeats

    # Undefended: the verbatim leak scores as a (near-)perfect recovery against the secret.
    for r in none_rows:
        assert r["exact"] is True
        assert r["rouge_l"] > 0.99

    # output_filter: the response the attacker receives is the redaction marker, which
    # contains none of the secret, so it no longer counts as a leak.
    for r in filtered_rows:
        assert r["exact"] is False
        assert r["rouge_l"] < 0.1

    # NOTE: the "evasion slips past the filter" demonstration (P4-A2) requires a real model
    # that transforms its output (spaced chars / base64); a verbatim-leaking fake cannot
    # evade an overlap filter. This test verifies the redaction plumbing, not real evasion.


def test_groups_present_and_bounded(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    prompts = _selected_prompts(cfg)

    results = run_full(cfg, provider_factory=fake_factory)
    groups = results["groups"]

    assert groups
    # One group per (model, prompt, attack, defense).
    expected_groups = len(prompts) * len(ATTACKS) * len(cfg.defenses)
    assert len(groups) == expected_groups

    for g in groups:
        assert 0.0 <= g["self_agreement"] <= 1.0
        assert 0.0 <= g["mean_rouge_l"] <= 1.0
        assert g["n"] == cfg.repeats

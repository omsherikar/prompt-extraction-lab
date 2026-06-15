"""Tests for the results aggregation (Phase 5, TDD, written first).

Fully OFFLINE: a small SYNTHETIC results.json is written to tmp_path; the real
data/results/results.json is never read and no network is touched. The synthetic data is
chosen so that one cell of `by_defense` can be hand-averaged, the row counts of `by_attack`
and `by_prompt_type` are known, and the `groups` form a clearly POSITIVELY correlated
(self_agreement, mean_rouge_l) cloud so the reused Pearson correlation is > 0.

What these tests pin:
  - the four summaries are produced and returned under the documented keys;
  - `by_defense` has one row per distinct defense, and a HAND-COMPUTED mean rouge_l for the
    "none" defense matches (bool->numeric mean of `exact` is the leak rate; rouge_l mean is
    the plain average);
  - `by_attack` (grouped by attack_id+family) and `by_prompt_type` have the expected number
    of rows;
  - `self_agreement_correlation` reuses the verifier: correlation is in [-1, 1] and strictly
    > 0 for the positively-correlated synthetic groups, and `pairs` has the right length.
"""

from __future__ import annotations

import json

import pytest

from src.experiment.aggregate import aggregate

# --- synthetic fixture -------------------------------------------------------
#
# Five responses spanning:
#   - 2 attack_ids: "a1" (family "f1") and "a2" (family "f2")
#   - 2 prompt_types: "direct" and "role"
#   - 2 defenses: "none" and "output_filter"
#
# rouge_l values are chosen so the "none" defense mean is easy to hand-average:
#   defense "none" rows have rouge_l: 0.9, 0.7, 0.2  -> mean = 1.8 / 3 = 0.6
#   defense "output_filter" rows have rouge_l: 0.0, 0.1
#
# exact is a mix of true/false so the bool->numeric mean is exercised.
_RESPONSES = [
    {"model_id": "m", "prompt_id": "p1", "prompt_type": "direct", "attack_id": "a1",
     "family": "f1", "defense": "none", "repeat": 0, "exact": True,
     "rouge_l": 0.9, "token_f1": 0.9},
    {"model_id": "m", "prompt_id": "p1", "prompt_type": "direct", "attack_id": "a1",
     "family": "f1", "defense": "none", "repeat": 1, "exact": False,
     "rouge_l": 0.7, "token_f1": 0.7},
    {"model_id": "m", "prompt_id": "p2", "prompt_type": "role", "attack_id": "a2",
     "family": "f2", "defense": "none", "repeat": 0, "exact": False,
     "rouge_l": 0.2, "token_f1": 0.2},
    {"model_id": "m", "prompt_id": "p1", "prompt_type": "direct", "attack_id": "a1",
     "family": "f1", "defense": "output_filter", "repeat": 0, "exact": False,
     "rouge_l": 0.0, "token_f1": 0.0},
    {"model_id": "m", "prompt_id": "p2", "prompt_type": "role", "attack_id": "a2",
     "family": "f2", "defense": "output_filter", "repeat": 1, "exact": False,
     "rouge_l": 0.1, "token_f1": 0.1},
]

# Three groups whose (self_agreement, mean_rouge_l) pairs are clearly POSITIVELY correlated.
_GROUPS = [
    {"model_id": "m", "prompt_id": "p1", "attack_id": "a1", "defense": "none",
     "self_agreement": 0.2, "mean_rouge_l": 0.1, "n": 2},
    {"model_id": "m", "prompt_id": "p2", "attack_id": "a2", "defense": "none",
     "self_agreement": 0.5, "mean_rouge_l": 0.5, "n": 2},
    {"model_id": "m", "prompt_id": "p1", "attack_id": "a1", "defense": "output_filter",
     "self_agreement": 0.9, "mean_rouge_l": 0.95, "n": 2},
]


def _write_results(tmp_path) -> str:
    """Write the synthetic results.json under tmp_path and return its path."""
    payload = {
        "seed": 1729,
        "query_count": len(_RESPONSES),
        "responses": _RESPONSES,
        "groups": _GROUPS,
    }
    path = tmp_path / "results.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


# --- tests -------------------------------------------------------------------


def test_returns_four_summaries(tmp_path) -> None:
    out = aggregate(_write_results(tmp_path))

    assert set(out) == {
        "by_attack",
        "by_prompt_type",
        "by_defense",
        "self_agreement_correlation",
    }


def test_by_defense_one_row_per_defense_with_hand_computed_mean(tmp_path) -> None:
    out = aggregate(_write_results(tmp_path))
    by_defense = out["by_defense"].reset_index()

    # One row per distinct defense: {"none", "output_filter"}.
    assert set(by_defense["defense"]) == {"none", "output_filter"}
    assert len(by_defense) == 2

    # HAND-COMPUTED: defense "none" rouge_l rows are 0.9, 0.7, 0.2 -> mean = 0.6.
    none_row = by_defense[by_defense["defense"] == "none"].iloc[0]
    assert none_row["rouge_l"] == pytest.approx(0.6)

    # bool->numeric mean of `exact` for "none" is the leak rate: one True of three -> 1/3.
    assert none_row["exact"] == pytest.approx(1 / 3)


def test_by_attack_row_count(tmp_path) -> None:
    out = aggregate(_write_results(tmp_path))
    by_attack = out["by_attack"].reset_index()

    # Grouped by (attack_id, family): two groups -> ("a1","f1") and ("a2","f2").
    assert len(by_attack) == 2
    assert set(by_attack["attack_id"]) == {"a1", "a2"}
    assert set(by_attack["family"]) == {"f1", "f2"}


def test_by_prompt_type_row_count(tmp_path) -> None:
    out = aggregate(_write_results(tmp_path))
    by_prompt_type = out["by_prompt_type"].reset_index()

    # Two distinct prompt_types: "direct", "role".
    assert len(by_prompt_type) == 2
    assert set(by_prompt_type["prompt_type"]) == {"direct", "role"}


def test_empty_responses_does_not_crash(tmp_path) -> None:
    # A degenerate zero-row run (e.g. a config matching no prompts) must not crash on the
    # missing `exact` column; aggregate returns empty leakage tables and still correlates
    # whatever groups exist.
    payload = {"seed": 1, "query_count": 0, "responses": [], "groups": _GROUPS}
    path = tmp_path / "results.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    out = aggregate(str(path))

    assert out["by_attack"].empty
    assert out["by_prompt_type"].empty
    assert out["by_defense"].empty
    assert len(out["self_agreement_correlation"]["pairs"]) == len(_GROUPS)


def test_self_agreement_correlation_is_positive_and_bounded(tmp_path) -> None:
    out = aggregate(_write_results(tmp_path))
    corr = out["self_agreement_correlation"]

    # Reuses the verifier's Pearson r: positively-correlated synthetic groups -> > 0.
    assert -1.0 <= corr["correlation"] <= 1.0
    assert corr["correlation"] > 0.0

    # `pairs` carries one (self_agreement, mean_rouge_l) tuple per group.
    assert len(corr["pairs"]) == len(_GROUPS)
    assert corr["pairs"][0] == (0.2, 0.1)

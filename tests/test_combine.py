"""Tests for the cross-model results combiner (src/experiment/combine.py).

Pure, offline: writes tiny per-model results.json files to tmp_path and checks the merge
concatenates responses/groups, re-derives query_count and the model set, and reports
completeness honestly (one partial source -> the combined file is flagged incomplete).
"""

from __future__ import annotations

import json

from src.experiment.combine import combine_results


def _write(tmp_path, name: str, payload: dict) -> str:
    p = tmp_path / name
    p.write_text(json.dumps(payload), encoding="utf-8")
    return str(p)


def _results(model_id: str, n: int, *, seed: int = 1729, complete: bool = True) -> dict:
    return {
        "seed": seed,
        "query_count": n,
        "responses": [{"model_id": model_id, "rouge_l": 0.0} for _ in range(n)],
        "groups": [{"model_id": model_id, "self_agreement": 1.0} for _ in range(n // 2)],
        "complete": complete,
        "error": None,
    }


def test_concatenates_responses_groups_and_models(tmp_path) -> None:
    a = _write(tmp_path, "a.json", _results("model-a", 4))
    b = _write(tmp_path, "b.json", _results("model-b", 6))

    combined = combine_results([a, b])

    assert combined["query_count"] == 10
    assert len(combined["responses"]) == 10
    assert len(combined["groups"]) == 2 + 3
    assert combined["models"] == ["model-a", "model-b"]
    assert combined["seed"] == 1729
    assert combined["complete"] is True
    assert combined["error"] is None


def test_partial_source_makes_combined_incomplete(tmp_path) -> None:
    a = _write(tmp_path, "a.json", _results("model-a", 4, complete=True))
    b = _write(tmp_path, "b.json", _results("model-b", 2, complete=False))

    combined = combine_results([a, b])

    # One unfinished source must not be silently presented as a whole run.
    assert combined["complete"] is False
    assert "b.json" in combined["error"]
    # but the rows that DID complete are still merged.
    assert combined["query_count"] == 6


def test_distinct_seeds_are_preserved_as_a_list(tmp_path) -> None:
    a = _write(tmp_path, "a.json", _results("model-a", 2, seed=1))
    b = _write(tmp_path, "b.json", _results("model-b", 2, seed=2))

    combined = combine_results([a, b])

    assert combined["seed"] == [1, 2]

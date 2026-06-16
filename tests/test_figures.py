"""Tests for figure generation (Phase 6, TDD, written first).

Fully OFFLINE and headless: a small SYNTHETIC results.json is written to tmp_path, figures are
rendered into a tmp dir, and the real data/results/results.json is never read and no network is
touched. matplotlib must run under the Agg backend (no display) — these tests would hang or fail
on a display-less CI otherwise, so we assert the backend is Agg.

The synthetic fixture deliberately spans:
  - >= 2 attack_ids ("a1", "a2") so the heatmap has multiple rows;
  - >= 2 prompt_types ("direct", "role") so the heatmap has multiple columns;
  - >= 2 defenses ("none", "instructional", "output_filter") so the grouped bars have groups;
  - >= 2 families ("f1", "f2") so the bars have multiple x positions;
  - 2 model_ids ("m1", "m2") so the multi-model scatter coloring is exercised;
  - a few groups with a positively-correlated (self_agreement, mean_rouge_l) cloud.

What these tests pin:
  - generate_figures returns the list of the 3 expected absolute file paths;
  - each PNG exists and is non-empty (size > 0);
  - no exception is raised and the run happened under the Agg backend;
  - a degenerate empty-`responses` results.json does not crash (and writes no figures).
"""

from __future__ import annotations

import json
import os

import pytest

from src.viz.figures import generate_figures

# --- synthetic fixture -------------------------------------------------------

_RESPONSES = [
    {"model_id": "m1", "prompt_id": "p1", "prompt_type": "direct", "attack_id": "a1",
     "family": "f1", "defense": "none", "repeat": 0, "exact": True,
     "rouge_l": 0.9, "token_f1": 0.9},
    {"model_id": "m1", "prompt_id": "p1", "prompt_type": "direct", "attack_id": "a1",
     "family": "f1", "defense": "instructional", "repeat": 0, "exact": False,
     "rouge_l": 0.4, "token_f1": 0.4},
    {"model_id": "m2", "prompt_id": "p1", "prompt_type": "role", "attack_id": "a2",
     "family": "f2", "defense": "output_filter", "repeat": 0, "exact": False,
     "rouge_l": 0.1, "token_f1": 0.1},
    {"model_id": "m2", "prompt_id": "p2", "prompt_type": "role", "attack_id": "a2",
     "family": "f2", "defense": "none", "repeat": 1, "exact": False,
     "rouge_l": 0.3, "token_f1": 0.3},
    {"model_id": "m1", "prompt_id": "p2", "prompt_type": "direct", "attack_id": "a2",
     "family": "f2", "defense": "instructional", "repeat": 0, "exact": False,
     "rouge_l": 0.2, "token_f1": 0.2},
    {"model_id": "m2", "prompt_id": "p1", "prompt_type": "role", "attack_id": "a1",
     "family": "f1", "defense": "output_filter", "repeat": 1, "exact": True,
     "rouge_l": 0.8, "token_f1": 0.8},
]

# Groups with a positively-correlated (self_agreement, mean_rouge_l) cloud across two models.
_GROUPS = [
    {"model_id": "m1", "prompt_id": "p1", "attack_id": "a1", "defense": "none",
     "self_agreement": 0.2, "mean_rouge_l": 0.1, "n": 2},
    {"model_id": "m1", "prompt_id": "p2", "attack_id": "a2", "defense": "none",
     "self_agreement": 0.5, "mean_rouge_l": 0.5, "n": 2},
    {"model_id": "m2", "prompt_id": "p1", "attack_id": "a1", "defense": "output_filter",
     "self_agreement": 0.9, "mean_rouge_l": 0.95, "n": 2},
    {"model_id": "m2", "prompt_id": "p2", "attack_id": "a2", "defense": "instructional",
     "self_agreement": 0.7, "mean_rouge_l": 0.6, "n": 2},
]


def _write_results(tmp_path, responses=_RESPONSES) -> str:
    """Write a synthetic results.json under tmp_path and return its path."""
    payload = {
        "seed": 1729,
        "query_count": len(responses),
        "responses": responses,
        "groups": _GROUPS,
        "complete": True,
        "error": None,
    }
    path = tmp_path / "results.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


# --- tests -------------------------------------------------------------------


def test_returns_three_existing_nonempty_pngs(tmp_path) -> None:
    out_dir = tmp_path / "figs"
    paths = generate_figures(_write_results(tmp_path), str(out_dir))

    # Returns the list of the 3 expected files, named as documented.
    assert isinstance(paths, list)
    assert len(paths) == 3
    expected = {
        str(out_dir / "heatmap.png"),
        str(out_dir / "defense_bars.png"),
        str(out_dir / "self_agreement_scatter.png"),
    }
    assert set(paths) == expected

    # Each PNG exists and is non-empty.
    for p in paths:
        assert os.path.exists(p), p
        assert os.path.getsize(p) > 0, p


def test_creates_out_dir_if_missing(tmp_path) -> None:
    # out_dir does not exist yet; generate_figures must create it.
    out_dir = tmp_path / "nested" / "figs"
    assert not out_dir.exists()
    paths = generate_figures(_write_results(tmp_path), str(out_dir))
    assert out_dir.exists()
    assert len(paths) == 3


def test_runs_under_agg_backend(tmp_path) -> None:
    # Headless requirement: rendering must use the non-interactive Agg backend, so the suite
    # never tries to open a display.
    generate_figures(_write_results(tmp_path), str(tmp_path / "figs"))

    import matplotlib

    assert matplotlib.get_backend().lower() == "agg"


def test_empty_responses_does_not_crash(tmp_path) -> None:
    # A degenerate zero-row run must not crash; mirror aggregate's empty guard. We expect no
    # figures to be written (an empty list), not a partial/garbage render.
    out_dir = tmp_path / "figs"
    paths = generate_figures(_write_results(tmp_path, responses=[]), str(out_dir))

    assert paths == []
    # No figures were written.
    if out_dir.exists():
        assert list(out_dir.glob("*.png")) == []


def test_two_model_heatmap_and_bars_facet_render(tmp_path) -> None:
    # The synthetic fixture spans two model_ids ("m1", "m2"). The heatmap and defense bars must
    # FACET per model (one panel per model) rather than averaging the two models into one chart.
    # Pin the user-visible contract here: both PNGs still render and are non-empty (faceted).
    out_dir = tmp_path / "figs"
    paths = generate_figures(_write_results(tmp_path), str(out_dir))

    for name in ("heatmap.png", "defense_bars.png"):
        p = str(out_dir / name)
        assert p in paths
        assert os.path.exists(p), p
        assert os.path.getsize(p) > 0, p


def test_single_model_heatmap_and_bars_render(tmp_path) -> None:
    # The model-aware logic must also work for ONE model: a single labeled panel. Restrict the
    # responses to "m1" so the heatmap and bars see a single model_id and render one panel each.
    single_model_responses = [r for r in _RESPONSES if r["model_id"] == "m1"]
    out_dir = tmp_path / "figs"
    paths = generate_figures(
        _write_results(tmp_path, responses=single_model_responses), str(out_dir)
    )

    for name in ("heatmap.png", "defense_bars.png"):
        p = str(out_dir / name)
        assert p in paths
        assert os.path.exists(p), p
        assert os.path.getsize(p) > 0, p


def test_two_model_scatter_renders(tmp_path) -> None:
    # The per-model scatter: the synthetic fixture spans two model_ids ("m1", "m2"), each with
    # >= 2 groups and >= 2 distinct self_agreement x-values, so each model gets its own fit line
    # and its own Pearson r in the legend. This must render without error and write a non-empty
    # scatter PNG (offline, Agg).
    out_dir = tmp_path / "figs"
    paths = generate_figures(_write_results(tmp_path), str(out_dir))

    scatter = str(out_dir / "self_agreement_scatter.png")
    assert scatter in paths
    assert os.path.exists(scatter)
    assert os.path.getsize(scatter) > 0


def test_single_model_scatter_renders(tmp_path) -> None:
    # The per-model logic must also work for ONE model: one colored cloud, one line, that model's
    # r in its legend label. Use only the "m1" groups so the scatter sees a single model_id.
    out_dir = tmp_path / "figs"
    single_model_groups = [
        {"model_id": "m1", "prompt_id": "p1", "attack_id": "a1", "defense": "none",
         "self_agreement": 0.2, "mean_rouge_l": 0.1, "n": 2},
        {"model_id": "m1", "prompt_id": "p2", "attack_id": "a2", "defense": "none",
         "self_agreement": 0.6, "mean_rouge_l": 0.7, "n": 2},
        {"model_id": "m1", "prompt_id": "p3", "attack_id": "a1", "defense": "instructional",
         "self_agreement": 0.4, "mean_rouge_l": 0.5, "n": 2},
    ]
    payload = {
        "seed": 1729,
        "query_count": len(_RESPONSES),
        "responses": _RESPONSES,
        "groups": single_model_groups,
        "complete": True,
        "error": None,
    }
    path = tmp_path / "results.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    paths = generate_figures(str(path), str(out_dir))
    scatter = str(out_dir / "self_agreement_scatter.png")
    assert scatter in paths
    assert os.path.exists(scatter)
    assert os.path.getsize(scatter) > 0


def test_light_theme_renders_three_nonempty_pngs(tmp_path) -> None:
    # The "light" theme must render the same 3 figures, offline and headless, into existing,
    # non-empty PNGs (only the palette/colormap/glow differ from the default "dark" look).
    out_dir = tmp_path / "figs-light"
    paths = generate_figures(_write_results(tmp_path), str(out_dir), theme="light")

    assert len(paths) == 3
    expected = {
        str(out_dir / "heatmap.png"),
        str(out_dir / "defense_bars.png"),
        str(out_dir / "self_agreement_scatter.png"),
    }
    assert set(paths) == expected
    for p in paths:
        assert os.path.exists(p), p
        assert os.path.getsize(p) > 0, p


def test_unknown_theme_raises_value_error(tmp_path) -> None:
    # An unrecognized theme name must fail loudly with a ValueError naming the valid themes,
    # rather than silently rendering with some default.
    with pytest.raises(ValueError, match="unknown theme"):
        generate_figures(_write_results(tmp_path), str(tmp_path / "figs"), theme="bogus")

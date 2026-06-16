"""Generate the post's figures into blog/figures/.

Phase 6: export, regenerable from data/results/results.json with one command so re-running the
study updates the post's visuals:
  - Heatmap: attack technique (rows) x prompt type (columns), cell = Rouge-L recall.
  - Grouped bars: leakage by defense (none / instructional / filter) per attack family.
  - Scatter: self-agreement vs true ground-truth score, one point per attack-run group, grouped
    by model with a per-model fitted line and per-model correlation (the regime flip across
    models is the point). The figure that proves the no-ground-truth idea.
  - Side-by-side text panel: one real extraction and one confabulation with their scores (may be
    a table in the post rather than a chart).

Honest charts: zero-based bars, labeled units, stated sample sizes; if n is small, say so.
"""

from __future__ import annotations

# Headless backend: select Agg BEFORE importing pyplot so figure generation never needs a
# display (tests and `make figures` run with no display). Order matters.
import matplotlib

matplotlib.use("Agg")

import json
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.scoring.verifier import agreement_vs_truth_correlation

# Fixed ordering for defenses so the grouped bars read consistently across runs.
_DEFENSE_ORDER = ["none", "instructional", "output_filter"]


def generate_figures(
    results_path: str = "data/results/results.json", out_dir: str = "blog/figures"
) -> list[str]:
    """Render all figures from results into out_dir; return the written file paths.

    Loads a results.json (written by ``run_full``) and renders the post's three figures as PNGs:
    a Rouge-L heatmap (attack x prompt_type), grouped defense bars (mean Rouge-L by attack
    family x defense), and the self-agreement vs ground-truth scatter (one point per group,
    grouped by model with a per-model fitted line and the reused per-model Pearson r in the
    legend).

    The heatmap and bars aggregate across whatever models are present; the scatter groups points
    by ``model_id`` so each model gets its own cloud, fit line and r (this is the cross-model
    regime figure). Degenerate empty-``responses`` runs write nothing and return ``[]`` (mirrors
    aggregate's empty guard). Pure render of one JSON file: no network.

    NOTE: the real-vs-confabulation side-by-side text panel (PRD P6-R4) needs the raw response
    TEXT, which run_full does not persist; it is intentionally out of scope here.
    """
    with open(results_path, encoding="utf-8") as f:
        results = json.load(f)

    responses = pd.DataFrame(results["responses"])
    if responses.empty:
        # Degenerate zero-row run (e.g. a config matching no prompts): nothing to plot. Write no
        # files and return [] rather than rendering empty/garbage axes or crashing on a missing
        # column. Mirrors aggregate's empty guard.
        return []

    os.makedirs(out_dir, exist_ok=True)
    groups = results.get("groups", [])

    paths = [
        _heatmap(responses, out_dir),
        _defense_bars(responses, out_dir),
        _self_agreement_scatter(groups, out_dir),
    ]
    return paths


def _models_in(responses: pd.DataFrame) -> list[str]:
    """Sorted set of distinct model_ids present, so figures can be faceted per model."""
    return sorted(responses["model_id"].unique())


def _draw_heatmap_panel(ax, model_rows, title, attack_ids, prompt_types, show_y):
    """Draw ONE model's Rouge-L heatmap (attack_id x prompt_type) onto ``ax``; return the image.

    The pivot is reindexed to the shared ``attack_ids``/``prompt_types`` so every panel has the
    same rows/cols and they align; that lets non-leftmost panels hide the (long) row labels via
    ``show_y=False`` instead of repeating them in the middle of the figure. Cells are mean
    Rouge-L over that model's rows (across defenses); a missing combo is a NaN (blank) cell. The
    color scale is pinned to [0, 1] by the caller so panels are comparable.
    """
    pivot = pd.pivot_table(
        model_rows, values="rouge_l", index="attack_id", columns="prompt_type", aggfunc="mean"
    ).reindex(index=attack_ids, columns=prompt_types)
    im = ax.imshow(pivot.values, aspect="auto", cmap="viridis", vmin=0.0, vmax=1.0)

    ax.set_xticks(range(len(prompt_types)))
    ax.set_xticklabels(prompt_types, rotation=30, ha="right")
    ax.set_yticks(range(len(attack_ids)))
    if show_y:
        ax.set_yticklabels(attack_ids)
        ax.set_ylabel("Attack technique (attack_id)")
    else:
        # Shared rows: only the leftmost panel labels them (avoids mid-figure overlap).
        ax.tick_params(labelleft=False)
    ax.set_xlabel("Prompt type")
    ax.set_title(title)

    # Annotate each cell with its mean value; contrasting text color by cell darkness.
    # A NaN cell (no rows for that combo) is left blank.
    for i in range(len(attack_ids)):
        for j in range(len(prompt_types)):
            val = pivot.values[i, j]
            if pd.isna(val):
                continue
            ax.text(
                j, i, f"{val:.2f}", ha="center", va="center",
                color="white" if val < 0.5 else "black", fontsize=8,
            )
    return im


def _heatmap(responses: pd.DataFrame, out_dir: str) -> str:
    """Heatmap of MEAN Rouge-L recall: rows = attack_id, columns = prompt_type, faceted by model.

    Cells are mean Rouge-L over the matching rows (across defenses). With a SINGLE model the figure
    is one labeled panel; with MULTIPLE models it FACETS into one panel per model side by side
    (same [0, 1] color scale, one shared colorbar) so a resistant and a leaky model are never
    blended into a meaningless mean and each panel is identifiable by its model id.
    """
    models = _models_in(responses)
    n = len(models)

    # Shared rows/cols across panels so they align and only the leftmost panel needs row labels.
    attack_ids = sorted(responses["attack_id"].unique())
    prompt_types = sorted(responses["prompt_type"].unique())

    # Width scales with the number of model panels; height with the number of attack rows.
    panel_w = max(6, 1.2 * len(prompt_types) + 3)
    fig, axes = plt.subplots(
        1, n, figsize=(panel_w * n, max(4, 0.5 * len(attack_ids))),
        squeeze=False, constrained_layout=True,
    )
    axes = axes[0]

    im = None
    for i, (ax, model) in enumerate(zip(axes, models, strict=True)):
        im = _draw_heatmap_panel(
            ax, responses[responses["model_id"] == model], model,
            attack_ids, prompt_types, show_y=(i == 0),
        )

    # One shared colorbar for the whole figure (same scale across panels). The empty-responses
    # guard upstream means there is always >= 1 model, so the loop ran and `im` is set.
    assert im is not None
    cbar = fig.colorbar(im, ax=list(axes))
    cbar.set_label("Mean Rouge-L recall (0-1)")
    fig.suptitle(
        "Leakage (mean Rouge-L recall) by attack technique x prompt type, per model"
    )

    path = os.path.join(out_dir, "heatmap.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _draw_defense_bars_panel(ax, model_rows, title, families, show_y):
    """Draw ONE model's grouped defense bars (x = family, grouped by defense) onto ``ax``.

    Reindexed to the shared ``families`` so panels align; only the leftmost panel labels the
    y-axis (``show_y``). Bars start at zero (honest [0, 1] scale). Defenses are drawn in the
    canonical none/instructional/output_filter order; a family x defense combo with no rows is
    NaN, drawn as a zero-height bar.
    """
    pivot = pd.pivot_table(
        model_rows, values="rouge_l", index="family", columns="defense", aggfunc="mean"
    ).reindex(index=families)
    # Keep canonical defense order for whatever defenses are present.
    defenses = [d for d in _DEFENSE_ORDER if d in pivot.columns]
    defenses += [d for d in pivot.columns if d not in defenses]
    pivot = pivot[defenses]

    n_def = len(defenses)
    x = np.arange(len(families))
    width = 0.8 / max(n_def, 1)

    for k, defense in enumerate(defenses):
        offsets = x + (k - (n_def - 1) / 2) * width
        heights = pivot[defense].to_numpy()
        ax.bar(offsets, np.nan_to_num(heights, nan=0.0), width=width, label=defense)

    ax.set_xticks(x)
    ax.set_xticklabels(families, rotation=20, ha="right")
    ax.set_xlabel("Attack family")
    # Honest scale: zero-based, full [0, 1] range so bar heights are not exaggerated.
    ax.set_ylim(0.0, 1.0)
    if show_y:
        ax.set_ylabel("Mean Rouge-L recall (0-1)")
    else:
        ax.tick_params(labelleft=False)
    ax.set_title(title)
    ax.legend(title="Defense")


def _defense_bars(responses: pd.DataFrame, out_dir: str) -> str:
    """Grouped bars: x = attack family, grouped by defense, y = MEAN Rouge-L recall, per model.

    Bars start at zero (honest scale). With a SINGLE model the figure is one labeled panel; with
    MULTIPLE models it FACETS into one panel per model side by side, so the leakage-by-defense
    story is read per model (not averaged) and each panel is identifiable by its model id.
    """
    models = _models_in(responses)
    n = len(models)

    # Shared family order across panels so they align and only the leftmost panel labels the axis.
    families = sorted(responses["family"].unique())
    panel_w = max(7, 1.6 * len(families) + 2)
    fig, axes = plt.subplots(
        1, n, figsize=(panel_w * n, 5), squeeze=False, constrained_layout=True
    )
    axes = axes[0]

    for i, (ax, model) in enumerate(zip(axes, models, strict=True)):
        _draw_defense_bars_panel(
            ax, responses[responses["model_id"] == model], model, families, show_y=(i == 0)
        )

    fig.suptitle(
        "Leakage by defense per attack family (mean Rouge-L recall), per model"
    )

    path = os.path.join(out_dir, "defense_bars.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _self_agreement_scatter(groups: list[dict], out_dir: str) -> str:
    """Scatter: x = self_agreement, y = mean_rouge_l, one point per group, colored by model.

    PER-MODEL figure. Each model gets its own cloud (in its color), its own dashed least-squares
    fit line (numpy.polyfit over THAT model's points), and its own Pearson r — reusing the
    verifier's ``agreement_vs_truth_correlation`` per model so the figure and the aggregate tables
    use the identical correlation. The per-model r and n are reported in that model's legend label.

    There is deliberately NO single global fit line and NO global r in the title: with models that
    have opposite relationships (one consistent refusal r<0, one consistent extraction r>0), a
    blended global r represents neither model and hides the regime flip this figure exists to show.
    The total number of groups plotted is still annotated honestly on the figure.
    """
    # Use only groups with finite numeric scores so a malformed/NaN group can't KeyError or
    # poison the polyfit and the correlation. Filter BEFORE grouping by model. (Each group is one
    # (model, prompt, attack, defense).)
    pts = [
        (g.get("self_agreement"), g.get("mean_rouge_l"), g.get("model_id", "model"))
        for g in groups
    ]
    pts = [
        (a, t, m)
        for a, t, m in pts
        if isinstance(a, (int, float))
        and isinstance(t, (int, float))
        and np.isfinite(a)
        and np.isfinite(t)
    ]
    total = len(pts)

    fig, ax = plt.subplots(figsize=(7, 6))

    # Color points by model so several models stay visually distinct (one model: one color).
    models = sorted({m for _, _, m in pts})
    cmap = plt.get_cmap("tab10")
    color_for = {m: cmap(i % 10) for i, m in enumerate(models)}
    for m in models:
        model_agreements = [a for a, _, mid in pts if mid == m]
        model_truths = [t for _, t, mid in pts if mid == m]
        k = len(model_agreements)
        # Reuse the verifier's Pearson r PER MODEL so the figure and aggregate tables agree.
        r = agreement_vs_truth_correlation(model_agreements, model_truths)
        ax.scatter(
            model_agreements, model_truths, color=color_for[m],
            label=f"{m}  (r={r:+.2f}, n={k})", alpha=0.8, edgecolors="none",
        )
        # Per-model dashed least-squares fit, same color. Needs >= 2 points with >= 2 distinct
        # x-values to be a meaningful line; otherwise scatter the points but skip the line.
        if k >= 2 and len(set(model_agreements)) >= 2:
            slope, intercept = np.polyfit(model_agreements, model_truths, 1)
            xline = np.linspace(min(model_agreements), max(model_agreements), 100)
            ax.plot(xline, slope * xline + intercept, color=color_for[m],
                    linestyle="--", linewidth=1.5)

    ax.set_xlabel("Self-agreement (pairwise Rouge-L among repeats, no ground truth)")
    ax.set_ylabel("Mean Rouge-L recall vs true prompt (ground truth)")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    # Neutral title: no global r. The per-model r lives in the legend, where the regime flip
    # (opposite signs across models) is the point — a single blended r would represent neither.
    ax.set_title("Self-agreement vs. true extraction quality\nper-model Pearson r in legend")
    # Note the total sample size (groups actually plotted) honestly on the figure.
    ax.text(
        0.02, 0.98, f"n = {total} groups", transform=ax.transAxes,
        ha="left", va="top", fontsize=9,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.7},
    )
    ax.legend(title="Model", loc="lower right")
    fig.tight_layout()

    path = os.path.join(out_dir, "self_agreement_scatter.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


if __name__ == "__main__":
    generate_figures()

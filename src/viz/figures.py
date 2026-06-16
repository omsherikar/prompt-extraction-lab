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

Theming: a small two-theme system (``"dark"`` / ``"light"``) selects the palette, rcParams,
heatmap colormap, NaN-cell color, annotation text color and path-effect glow. The structure of
every figure — what is plotted, how it is aggregated, faceting per model, leftmost-only row
labels, per-model fit lines + per-model Pearson r in the legend, and every guard — is identical
across themes; only colors change. The chosen theme is scoped to ``generate_figures`` via
``plt.rc_context`` so it never leaks into other code or tests.
"""

from __future__ import annotations

# Headless backend: select Agg BEFORE importing pyplot so figure generation never needs a
# display (tests and `make figures` run with no display). Order matters.
import matplotlib

matplotlib.use("Agg")

import json
import os
from dataclasses import dataclass, field

import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.scoring.verifier import agreement_vs_truth_correlation

# Fixed ordering for defenses so the grouped bars read consistently across runs.
_DEFENSE_ORDER = ["none", "instructional", "output_filter"]


# --- theme system ------------------------------------------------------------
# A ``Theme`` bundles everything the figures need to style themselves: the rcParams dict plus the
# handful of colors / colormap names referenced directly in code (NaN cells, annotation text, the
# path-effect glow). The figure/panel helpers take a ``Theme`` (or its fields) and never reference
# a module-level color constant, so adding a theme is purely a matter of adding a ``Theme`` to the
# ``_THEMES`` registry. The chosen theme is scoped to ``generate_figures`` via ``plt.rc_context``.


@dataclass(frozen=True)
class Theme:
    """A figure color/style theme. ``rc`` is applied via rc_context; the rest are used in code."""

    bg: str  # figure/panel/savefig background
    panel: str  # subtle panel tint (legend bg, NaN-ish separation)
    fg: str  # body text / labels
    fg_bright: str  # brighter text for titles / annotations
    spine: str  # spines / outlines
    tick: str  # ticks
    grid: str  # grid behind the data
    accents: list[str]  # 3 accent colors (defenses; models in the scatter)
    cmap: str  # seaborn colormap NAME for the heatmap
    nan_cell: str  # color for NaN heatmap cells
    cell_text: str  # heatmap annotation text color
    glow_fg: str  # path-effect stroke color (usually == bg)
    rc: dict = field(default_factory=dict)  # rcParams applied via plt.rc_context


def _make_rc(*, bg, panel, fg, fg_bright, spine, tick, grid) -> dict:
    """Build an rcParams dict from a theme's palette (shared structure across themes)."""
    return {
        "figure.facecolor": bg,
        "axes.facecolor": bg,
        "savefig.facecolor": bg,
        "savefig.edgecolor": bg,
        "text.color": fg,
        "axes.labelcolor": fg,
        "axes.titlecolor": fg_bright,
        "axes.edgecolor": spine,
        "axes.linewidth": 0.8,
        "xtick.color": tick,
        "ytick.color": tick,
        "xtick.labelcolor": fg,
        "ytick.labelcolor": fg,
        "grid.color": grid,
        "grid.alpha": 0.4,
        "grid.linewidth": 0.8,
        "axes.grid": True,
        "axes.axisbelow": True,  # grid behind the data
        "axes.titleweight": "bold",
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "font.size": 10,
        "legend.framealpha": 0.85,
        "legend.edgecolor": spine,
        "legend.facecolor": panel,
        "legend.labelcolor": fg,
        "figure.titlesize": 14,
        "figure.titleweight": "bold",
    }


# --- dark "techie dashboard" theme -------------------------------------------
# A cohesive near-black Grafana/terminal aesthetic (unchanged from the original look). Accent
# palette: teal / coral-pink / lime — used for the three defenses and, teal-vs-coral, for the two
# models in the scatter.
_DARK = Theme(
    bg="#0d1117",  # near-black figure/panel background (and saved PNG)
    panel="#161b22",  # subtle panel tint (used where a touch of separation helps)
    fg="#c9d1d9",  # light-gray body text / labels
    fg_bright="#e6edf3",  # brighter text for titles / annotations
    spine="#30363d",  # subtle spines
    tick="#8b949e",  # muted ticks
    grid="#21262d",  # faint grid behind the data
    accents=["#2dd4bf", "#f472b6", "#a3e635"],  # teal / coral-pink / lime
    cmap="mako",  # dark, perceptually-uniform colormap for the heatmap
    nan_cell="#161b22",  # NaN cells get the subtle panel tint, not white
    cell_text="#e6edf3",  # fixed light annotation text on the heatmap
    glow_fg="#0d1117",  # path-effect stroke == bg
    rc=_make_rc(
        bg="#0d1117", panel="#161b22", fg="#c9d1d9", fg_bright="#e6edf3",
        spine="#30363d", tick="#8b949e", grid="#21262d",
    ),
)

# --- light "research-paper / docs" theme -------------------------------------
# A clean, modern, professional light look (Stripe / Vercel docs / research-paper vibe). Accents
# chosen for good contrast on white: indigo / rose / emerald.
_LIGHT = Theme(
    bg="#ffffff",  # white figure/panel background (and saved PNG)
    panel="#f0f1f3",  # subtle light panel tint (legend bg / NaN cells)
    fg="#1f2328",  # dark body text / labels
    fg_bright="#0d1117",  # near-black text for titles / annotations
    spine="#d0d7de",  # light-gray spines
    tick="#57606a",  # muted gray ticks
    grid="#eaeef2",  # very faint grid behind the data
    accents=["#4f46e5", "#db2777", "#059669"],  # indigo / rose / emerald
    cmap="crest",  # light->teal: stays light at the low end (where most data sits), so the
    # heatmap reads light and dark annotation text stays legible. "rocket" goes near-black at the
    # low end, which dominated this low-valued data and looked dark — not the clean light look.
    nan_cell="#f0f1f3",  # NaN cells get the light panel tint
    cell_text="#0d1117",  # dark annotation text on the heatmap
    glow_fg="#ffffff",  # white stroke so dark annotations read on lighter cells
    rc=_make_rc(
        bg="#ffffff", panel="#f0f1f3", fg="#1f2328", fg_bright="#0d1117",
        spine="#d0d7de", tick="#57606a", grid="#eaeef2",
    ),
)

# Theme registry — add a Theme here to make it selectable via the ``theme`` parameter.
_THEMES = {"dark": _DARK, "light": _LIGHT}


def _despine(ax, spine: str) -> None:
    """Hide the top + right spines and tint the remaining ones with the theme's spine color."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(spine)


def _glow(foreground: str, linewidth: float = 2.5, alpha: float = 0.6):
    """A tasteful path-effect stroke so marks/labels read on busy cells (stroke = theme glow)."""
    return [path_effects.withStroke(linewidth=linewidth, foreground=foreground, alpha=alpha)]


def generate_figures(
    results_path: str = "data/results/results.json",
    out_dir: str = "blog/figures",
    theme: str = "dark",
) -> list[str]:
    """Render all figures from results into out_dir; return the written file paths.

    Loads a results.json (written by ``run_full``) and renders the post's three figures as PNGs:
    a Rouge-L heatmap (attack x prompt_type), grouped defense bars (mean Rouge-L by attack
    family x defense), and the self-agreement vs ground-truth scatter (one point per group,
    grouped by model with a per-model fitted line and the reused per-model Pearson r in the
    legend).

    ``theme`` selects the look: ``"dark"`` (the near-black dashboard) or ``"light"`` (a clean
    docs/research-paper style). Only colors/colormap/glow change — the structure, aggregations,
    faceting and guards are identical across themes. The theme is scoped to this call via
    ``plt.rc_context`` so it never leaks into other code or tests.

    The heatmap and bars aggregate across whatever models are present; the scatter groups points
    by ``model_id`` so each model gets its own cloud, fit line and r (this is the cross-model
    regime figure). Degenerate empty-``responses`` runs write nothing and return ``[]`` (mirrors
    aggregate's empty guard). Pure render of one JSON file: no network.

    NOTE: the real-vs-confabulation side-by-side text panel (PRD P6-R4) needs the raw response
    TEXT, which run_full does not persist; it is intentionally out of scope here.
    """
    if theme not in _THEMES:
        raise ValueError(f"unknown theme {theme!r}; expected one of {sorted(_THEMES)}")
    t = _THEMES[theme]

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

    # Scope the chosen theme to figure generation only: every figure built inside this block
    # inherits ``t.rc``, and the rcParams are restored on exit so the styling never leaks into
    # other code or tests.
    with plt.rc_context(t.rc):
        paths = [
            _heatmap(responses, out_dir, t),
            _defense_bars(responses, out_dir, t),
            _self_agreement_scatter(groups, out_dir, t),
        ]
    return paths


def _models_in(responses: pd.DataFrame) -> list[str]:
    """Sorted set of distinct model_ids present, so figures can be faceted per model."""
    return sorted(responses["model_id"].unique())


def _draw_heatmap_panel(ax, model_rows, title, attack_ids, prompt_types, show_y, t: Theme):
    """Draw ONE model's Rouge-L heatmap (attack_id x prompt_type) onto ``ax``; return the image.

    The pivot is reindexed to the shared ``attack_ids``/``prompt_types`` so every panel has the
    same rows/cols and they align; that lets non-leftmost panels hide the (long) row labels via
    ``show_y=False`` instead of repeating them in the middle of the figure. Cells are mean
    Rouge-L over that model's rows (across defenses); a missing combo is a NaN (blank) cell. The
    color scale is pinned to [0, 1] by the caller so panels are comparable.
    """
    import seaborn as sns  # lazy: only needed for the perceptually-uniform theme colormap.

    pivot = pd.pivot_table(
        model_rows, values="rouge_l", index="attack_id", columns="prompt_type", aggfunc="mean"
    ).reindex(index=attack_ids, columns=prompt_types)
    cmap = sns.color_palette(t.cmap, as_cmap=True)
    cmap.set_bad(t.nan_cell)  # NaN (no rows) cells get the subtle theme tint, not white.
    im = ax.imshow(pivot.values, aspect="auto", cmap=cmap, vmin=0.0, vmax=1.0)

    ax.grid(False)  # a grid over image cells just adds noise.
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
    _despine(ax, t.spine)

    # Annotate each cell with its mean value. Text is the theme's annotation color with a glow
    # stroke so it stays legible on both ends of the colormap. A NaN cell is left blank.
    for i in range(len(attack_ids)):
        for j in range(len(prompt_types)):
            val = pivot.values[i, j]
            if pd.isna(val):
                continue
            ax.text(
                j, i, f"{val:.2f}", ha="center", va="center",
                color=t.cell_text, fontsize=8, fontweight="bold",
                path_effects=_glow(t.glow_fg, linewidth=2.0, alpha=0.7),
            )
    return im


def _heatmap(responses: pd.DataFrame, out_dir: str, t: Theme) -> str:
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
            attack_ids, prompt_types, show_y=(i == 0), t=t,
        )

    # One shared colorbar for the whole figure (same scale across panels). The empty-responses
    # guard upstream means there is always >= 1 model, so the loop ran and `im` is set.
    assert im is not None
    cbar = fig.colorbar(im, ax=list(axes))
    cbar.set_label("Mean Rouge-L recall (0-1)", color=t.fg)
    cbar.ax.yaxis.set_tick_params(color=t.tick, labelcolor=t.fg)
    if cbar.outline is not None:
        cbar.outline.set_edgecolor(t.spine)
    fig.suptitle(
        "Leakage (mean Rouge-L recall) by attack technique x prompt type, per model"
    )

    path = os.path.join(out_dir, "heatmap.png")
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


def _draw_defense_bars_panel(ax, model_rows, title, families, show_y, t: Theme):
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
        color = t.accents[k % len(t.accents)]  # per-defense accent.
        drawn = np.nan_to_num(heights, nan=0.0)
        ax.bar(offsets, drawn, width=width, label=defense, color=color,
               edgecolor=t.bg, linewidth=0.5)
        # Small value labels above each (non-NaN) bar, with a subtle theme glow.
        for xo, h, raw in zip(offsets, drawn, heights, strict=True):
            if pd.isna(raw):
                continue
            ax.text(
                xo, h + 0.02, f"{h:.2f}", ha="center", va="bottom",
                color=t.fg_bright, fontsize=7,
                path_effects=_glow(t.glow_fg, linewidth=2.0, alpha=0.6),
            )

    ax.set_xticks(x)
    ax.set_xticklabels(families, rotation=20, ha="right")
    ax.set_xlabel("Attack family")
    # Honest scale: zero-based, full [0, 1] range so bar heights are not exaggerated.
    ax.set_ylim(0.0, 1.0)
    if show_y:
        ax.set_ylabel("Mean Rouge-L recall (0-1)")
    else:
        ax.tick_params(labelleft=False)
    # Faint horizontal grid only, behind the bars.
    ax.grid(axis="y", color=t.grid, alpha=0.4)
    ax.grid(axis="x", visible=False)
    ax.set_axisbelow(True)
    ax.set_title(title)
    _despine(ax, t.spine)
    ax.legend(title="Defense", facecolor=t.panel, edgecolor=t.spine,
              framealpha=0.85, labelcolor=t.fg)


def _defense_bars(responses: pd.DataFrame, out_dir: str, t: Theme) -> str:
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
            ax, responses[responses["model_id"] == model], model, families,
            show_y=(i == 0), t=t,
        )

    fig.suptitle(
        "Leakage by defense per attack family (mean Rouge-L recall), per model"
    )

    path = os.path.join(out_dir, "defense_bars.png")
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


def _self_agreement_scatter(groups: list[dict], out_dir: str, t: Theme) -> str:
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
        (a, t_, m)
        for a, t_, m in pts
        if isinstance(a, (int, float))
        and isinstance(t_, (int, float))
        and np.isfinite(a)
        and np.isfinite(t_)
    ]
    total = len(pts)

    fig, ax = plt.subplots(figsize=(7, 6))

    # Color points by model so several models stay visually distinct (one model: one color).
    # Accent palette cycles by index for any model count.
    models = sorted({m for _, _, m in pts})
    color_for = {m: t.accents[i % len(t.accents)] for i, m in enumerate(models)}
    for m in models:
        model_agreements = [a for a, _, mid in pts if mid == m]
        model_truths = [tr for _, tr, mid in pts if mid == m]
        k = len(model_agreements)
        # Reuse the verifier's Pearson r PER MODEL so the figure and aggregate tables agree.
        r = agreement_vs_truth_correlation(model_agreements, model_truths)
        ax.scatter(
            model_agreements, model_truths, color=color_for[m],
            label=f"{m}  (r={r:+.2f}, n={k})", alpha=0.85, edgecolors=t.bg, linewidths=0.4,
            s=55, zorder=3,
        )
        # Per-model dashed least-squares fit, same color, with a subtle glow. Needs >= 2 points
        # with >= 2 distinct x-values to be a meaningful line; otherwise skip the line.
        if k >= 2 and len(set(model_agreements)) >= 2:
            slope, intercept = np.polyfit(model_agreements, model_truths, 1)
            xline = np.linspace(min(model_agreements), max(model_agreements), 100)
            ax.plot(xline, slope * xline + intercept, color=color_for[m],
                    linestyle="--", linewidth=1.8, zorder=2,
                    path_effects=_glow(t.glow_fg, linewidth=3.5, alpha=0.6))

    ax.set_xlabel("Self-agreement (pairwise Rouge-L among repeats, no ground truth)")
    ax.set_ylabel("Mean Rouge-L recall vs true prompt (ground truth)")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    # Neutral title: no global r. The per-model r lives in the legend, where the regime flip
    # (opposite signs across models) is the point — a single blended r would represent neither.
    ax.set_title("Self-agreement vs. true extraction quality\nper-model Pearson r in legend")
    ax.grid(color=t.grid, alpha=0.4)
    ax.set_axisbelow(True)
    _despine(ax, t.spine)
    # Note the total sample size (groups actually plotted) honestly on the figure.
    ax.text(
        0.02, 0.98, f"n = {total} groups", transform=ax.transAxes,
        ha="left", va="top", fontsize=9, color=t.fg_bright,
        bbox={"boxstyle": "round", "facecolor": t.panel, "edgecolor": t.spine, "alpha": 0.85},
    )
    legend = ax.legend(
        title="Model", loc="lower right", facecolor=t.panel, edgecolor=t.spine,
        framealpha=0.85, labelcolor=t.fg,
    )
    legend.get_title().set_color(t.fg_bright)
    fig.tight_layout()

    path = os.path.join(out_dir, "self_agreement_scatter.png")
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


if __name__ == "__main__":
    generate_figures(theme="dark", out_dir="blog/figures")
    generate_figures(theme="light", out_dir="blog/figures/light")

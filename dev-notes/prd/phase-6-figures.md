# PRD — Phase 6: Figures

- **Status:** Not started
- **Owner agent:** data-viz-analyst
- **Depends on:** Phase 5
- **Source:** [`../PLAN.md`](../PLAN.md) § Phase 6
- **Supports thesis claims:** presents 1, 2, 3, 4

## 1. Objective

The three or four visuals that carry the article, regenerable from `results.json` with one
command so re-running the study updates the post's figures.

## 2. Background and context

The figures are how the reader feels the result. The heatmap shows what leaks and what resists;
the defense bars show how little defenses help; the scatter is the figure that proves the no-
ground-truth verifier idea. They must be honest: zero-based bars, labeled units, stated sample
sizes, and visible variance.

## 3. Scope

**In scope**
- Heatmap, grouped defense bars, self-agreement scatter, and a real-vs-confabulation side-by-side
  panel (may be a table in the post).
- One command that regenerates all figures into `blog/figures/`.

**Out of scope**
- The prose around the figures (Phase 7).

## 4. Requirements

- **P6-R1** Heatmap: attack technique (rows) x prompt type (columns), cell value = Rouge-L recall.
- **P6-R2** Grouped bars: leakage by defense (`none` / `instructional` / `output_filter`) per
  attack family, bars zero-based.
- **P6-R3** Scatter: self-agreement score (x) vs true ground-truth score (y), one point per
  attack-run group, with a fitted line and the reported correlation in the caption or on-figure.
- **P6-R4** Side-by-side panel: one real extraction and one confabulation with their scores;
  produced as a figure or as a committed table for the post.
- **P6-R5** `generate_figures(results_path, out_dir)` reads `data/results/results.json` and writes
  all figures to `blog/figures/` in one command.
- **P6-R6** Figures state sample sizes; if n is small, the figure says so. No smoothing or
  cherry-picking.

## 5. Deliverables

| File | Work |
|------|------|
| `src/viz/figures.py` | Implement all figures (P6-R1 to P6-R6) |
| `blog/figures/*` | Generated output committed for the post |

## 6. Acceptance criteria

- **P6-A1** Figures regenerate from `results.json` with one command (`make figures`), so re-running
  the study updates the post's visuals (PLAN.md Phase 6 acceptance).
- **P6-A2** All four visuals are produced and readable; axes labeled, bars zero-based, correlation
  reported on the scatter.

## 7. Test plan

- Manual/visual: run `make figures` against a real `results.json` and inspect each figure for
  honest axes, labels, and sample-size annotation.
- Smoke: `generate_figures` over a small synthetic `results.json` writes the expected file set
  without error.

## 8. Risks and open questions

- Small n is likely; annotate it rather than hiding it. A weak self-agreement correlation must be
  shown weak, not dressed up.
- Choose a figure format (PNG plus optionally SVG) and a consistent style so the post reads as one
  set.

## 9. Definition of done

- [ ] P6-R1 through P6-R6 implemented.
- [ ] P6-A1, P6-A2 pass.
- [ ] data-viz-analyst confirms axes/labels/sample-size honesty on every figure.

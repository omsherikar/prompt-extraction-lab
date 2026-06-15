"""Generate the post's figures into blog/figures/.

Phase 6: export, regenerable from data/results/results.json with one command so re-running the
study updates the post's visuals:
  - Heatmap: attack technique (rows) x prompt type (columns), cell = Rouge-L recall.
  - Grouped bars: leakage by defense (none / instructional / filter) per attack family.
  - Scatter: self-agreement vs true ground-truth score, one point per attack-run group, with a
    fitted line and the reported correlation. The figure that proves the no-ground-truth idea.
  - Side-by-side text panel: one real extraction and one confabulation with their scores (may be
    a table in the post rather than a chart).

Honest charts: zero-based bars, labeled units, stated sample sizes; if n is small, say so.
"""

from __future__ import annotations


def generate_figures(results_path: str = "data/results/results.json", out_dir: str = "blog/figures") -> None:
    """Render all figures from results into out_dir."""
    # Phase 6: build each figure with matplotlib and save to out_dir.
    raise NotImplementedError("Phase 6: implement figure generation")


if __name__ == "__main__":
    generate_figures()

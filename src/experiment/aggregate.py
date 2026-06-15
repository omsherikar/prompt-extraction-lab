"""Turn raw results into the summary tables the post reports.

Phase 5: load data/results/results.json into pandas and produce:
  - leakage rate (exact and Rouge-L) by attack technique
  - leakage by prompt type (direct vs role vs in-context)
  - leakage by defense (none vs instructional vs filter)
  - self-agreement vs ground-truth correlation (from the Phase 3 verifier)

A single command prints these tables.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from src.scoring.verifier import agreement_vs_truth_correlation

if TYPE_CHECKING:
    import pandas as pd


def aggregate(results_path: str = "data/results/results.json") -> dict:
    """Load results and print/return the four summary tables.

    Reads ``results_path`` (written by ``run_full``), builds a DataFrame from ``responses``,
    and returns a dict of four summaries (also printed with headers):

      - ``"by_attack"``: mean ``exact`` (leak rate) and mean ``rouge_l`` grouped by
        ``(attack_id, family)``;
      - ``"by_prompt_type"``: the same two means grouped by ``prompt_type``;
      - ``"by_defense"``: the same two means grouped by ``defense``;
      - ``"self_agreement_correlation"``: a dict ``{"correlation", "pairs"}`` where
        ``correlation`` is the verifier's Pearson r between each group's ``self_agreement``
        and its ``mean_rouge_l`` (the no-ground-truth validation step), and ``pairs`` is the
        parallel list of ``(self_agreement, mean_rouge_l)`` tuples it was computed from.

    Pure read of one JSON file: no network.
    """
    import pandas as pd

    with open(results_path, encoding="utf-8") as f:
        results = json.load(f)

    responses = pd.DataFrame(results["responses"])
    # `exact` is a bool column; mean of a bool column is the leak RATE (fraction True).
    responses["exact"] = responses["exact"].astype(float)

    by_attack = _mean_leak(responses, ["attack_id", "family"])
    by_prompt_type = _mean_leak(responses, "prompt_type")
    by_defense = _mean_leak(responses, "defense")

    groups = results["groups"]
    agreements = [g["self_agreement"] for g in groups]
    truths = [g["mean_rouge_l"] for g in groups]
    correlation = agreement_vs_truth_correlation(agreements, truths)
    self_agreement_correlation = {
        "correlation": correlation,
        "pairs": list(zip(agreements, truths, strict=True)),
    }

    _print_table("Leakage by attack technique (attack_id, family)", by_attack)
    _print_table("Leakage by prompt type", by_prompt_type)
    _print_table("Leakage by defense", by_defense)
    print("\n=== Self-agreement vs ground-truth correlation ===")
    print(f"Pearson r (self_agreement vs mean_rouge_l): {correlation:.4f}")
    print(f"  over {len(groups)} groups")

    return {
        "by_attack": by_attack,
        "by_prompt_type": by_prompt_type,
        "by_defense": by_defense,
        "self_agreement_correlation": self_agreement_correlation,
    }


def _mean_leak(responses: pd.DataFrame, by) -> pd.DataFrame:  # noqa: ANN001 - str | list[str]
    """Group ``responses`` by ``by`` and take the mean of ``exact`` and ``rouge_l``."""
    return responses.groupby(by)[["exact", "rouge_l"]].mean()


def _print_table(header: str, table: pd.DataFrame) -> None:
    """Print a summary table under a clear header."""
    print(f"\n=== {header} ===")
    print(table.to_string())


if __name__ == "__main__":
    aggregate()

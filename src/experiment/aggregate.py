"""Turn raw results into the summary tables the post reports.

Phase 5: load data/results/results.json into pandas and produce:
  - leakage rate (exact and Rouge-L) by attack technique
  - leakage by prompt type (direct vs role vs in-context)
  - leakage by defense (none vs instructional vs filter)
  - self-agreement vs ground-truth correlation (from the Phase 3 verifier)

A single command prints these tables.
"""

from __future__ import annotations


def aggregate(results_path: str = "data/results/results.json") -> None:
    """Load results and print the summary tables."""
    # Phase 5: pandas group-bys for each table above; print them.
    raise NotImplementedError("Phase 5: implement aggregation")


if __name__ == "__main__":
    aggregate()

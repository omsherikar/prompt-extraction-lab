"""Combine several per-model ``results.json`` files into one cross-model results file.

Each ``run_full`` writes the results for one model to its own ``results_dir``. The figures facet
on ``model_id`` (which is present in both ``responses`` and ``groups``), so a cross-model file is
simply the concatenation of every source's ``responses`` and ``groups``, with ``query_count``
re-derived. Keeping this as a small, tested utility makes the cross-model figure reproducible from
the per-model runs rather than an ad-hoc merge.

    python3 -m src.experiment.combine \
        data/results/results.json \
        data/results/run-qwen/results.json \
        data/results/run-minimax/results.json \
        data/results/run-gemma/results.json \
        -o data/results/results.combined.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def combine_results(paths: list[str]) -> dict:
    """Merge per-model results dicts into one combined results dict.

    Concatenates ``responses`` and ``groups`` across all inputs and re-derives ``query_count``.
    ``seed`` is the shared seed when every source agrees (the symmetric-matrix case), else the
    sorted list of distinct seeds. ``complete`` is True only when every source was complete; if
    any source was partial it is False and ``error`` names the offending files, so a combined
    file built from an unfinished run is never silently presented as whole. Adds a ``models`` key
    listing the distinct model_ids, purely for at-a-glance inspection (figures ignore it).
    """
    responses: list[dict] = []
    groups: list[dict] = []
    seeds: set = set()
    incomplete: list[str] = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        responses.extend(d.get("responses", []))
        groups.extend(d.get("groups", []))
        seeds.add(d.get("seed"))
        if not d.get("complete", False):
            incomplete.append(p)

    known_seeds = sorted(s for s in seeds if s is not None)
    seed: object = known_seeds[0] if len(known_seeds) == 1 else known_seeds

    return {
        "seed": seed,
        "query_count": len(responses),
        "responses": responses,
        "groups": groups,
        "complete": not incomplete,
        "error": None if not incomplete else f"incomplete sources: {incomplete}",
        "models": sorted({r["model_id"] for r in responses}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Combine per-model results.json files into one cross-model file."
    )
    parser.add_argument("inputs", nargs="+", help="paths to per-model results.json files")
    parser.add_argument(
        "-o",
        "--output",
        default="data/results/results.combined.json",
        help="path to write the combined results.json",
    )
    args = parser.parse_args()

    combined = combine_results(args.inputs)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2)
    flag = "" if combined["complete"] else "  (WARNING: includes incomplete sources)"
    print(
        f"[combine] {len(combined['responses'])} responses from "
        f"{combined['models']} -> {out}{flag}"
    )


if __name__ == "__main__":
    main()

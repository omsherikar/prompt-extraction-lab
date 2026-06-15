"""Orchestrate the experiment.

Phase 0 acceptance: `python -m src.experiment.run --smoke` sends one hardcoded system prompt
and one user message to one model and prints the response. Nothing else.

Phase 5: the full path loops over models x prompts x attacks x defenses x repeats, scores every
response via the verifier, and writes data/results/results.json and a flat results.csv, recording
query counts so success can be reported as a function of budget. Reproducible from config + seed.
"""

from __future__ import annotations

import argparse


def run_smoke() -> None:
    """One prompt, one query, one model; print the response. Phase 0 acceptance."""
    # Phase 0: load .env, construct the first configured provider, build a TargetApp with one
    # prompt, call app.query("<benign message>"), and print the response.
    raise NotImplementedError("Phase 0: implement the smoke path")


def run_full() -> None:
    """Run the full matrix and write results. Phase 5."""
    # Phase 5: load config, loop the matrix, score via the verifier, write results.json + csv.
    raise NotImplementedError("Phase 5: implement the full run")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the prompt-extraction experiment.")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="One prompt, one query, one model; print the response (Phase 0 acceptance).",
    )
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    if args.smoke:
        run_smoke()
    else:
        run_full()


if __name__ == "__main__":
    main()

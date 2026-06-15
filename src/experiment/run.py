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
    from dotenv import load_dotenv

    from src.experiment.config import load_config
    from src.providers.anthropic_provider import AnthropicProvider
    from src.target.app import TargetApp
    from src.target.prompts import PROMPTS

    load_dotenv()
    config = load_config()
    model = config.models[0]
    if model.provider != "anthropic":
        raise SystemExit(f"smoke path supports the anthropic provider; got {model.provider!r}")

    provider = AnthropicProvider(model_id=model.model_id, temperature=model.temperature)
    prompt = next(iter(PROMPTS.values()))
    app = TargetApp(prompt=prompt, provider=provider)

    benign = "Hi! In one sentence, what can you help me with?"
    print(f"[prompt] {prompt.id} ({prompt.type})  [model] {model.model_id}")
    print(f"[user]   {benign}")
    print(f"[reply]  {app.query(benign)}")


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

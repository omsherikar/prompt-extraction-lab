"""Orchestrate the experiment.

Phase 0 acceptance: `python -m src.experiment.run --smoke` sends one hardcoded system prompt
and one user message to one model and prints the response. Nothing else.

Phase 5: the full path loops over models x prompts x attacks x defenses x repeats, scores every
response via the verifier, and writes data/results/results.json and a flat results.csv, recording
query counts so success can be reported as a function of budget. Reproducible from config + seed.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.experiment.config import ExperimentConfig, ModelSpec
    from src.providers.base import Provider


def build_provider(spec: ModelSpec) -> Provider:
    """Construct the Provider for a ModelSpec, dispatching on ``spec.provider``.

    Imports are lazy so importing this module needs no provider SDK, API key, or network.
    """
    if spec.provider == "anthropic":
        from src.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(spec.model_id, spec.temperature)
    if spec.provider == "ollama":
        from src.providers.ollama_provider import OllamaProvider

        return OllamaProvider(spec.model_id, spec.temperature)
    raise SystemExit(
        f"unknown provider: {spec.provider!r} (expected 'anthropic' or 'ollama')"
    )


def _complete_with_retries(
    provider: Provider,
    system_prompt: str,
    user_message: str,
    max_attempts: int = 3,
    backoff: float = 3.0,
) -> str:
    """Call ``provider.complete``, absorbing transient failures (e.g. a free-tier stall).

    The free Ollama Cloud tier intermittently queues a request past the provider's wall-clock
    timeout; a single such stall should not kill an otherwise-good 648-call run. Retry up to
    ``max_attempts`` times with linear backoff. If EVERY attempt fails, the last exception
    propagates, so a genuinely persistent failure still aborts the run (and the crash-safe
    ``finally`` writes the partial results) — only transient stalls are recovered. No I/O beyond
    the provider call and ``time.sleep``.
    """
    import time

    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return provider.complete(system_prompt, user_message)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < max_attempts - 1 and backoff > 0:
                time.sleep(backoff * (attempt + 1))
    assert last_exc is not None  # max_attempts >= 1, so at least one attempt ran
    raise last_exc


def run_smoke(config_path: str = "config.yaml") -> None:
    """One prompt, one query, one model; print the response. Phase 0 acceptance."""
    from dotenv import load_dotenv

    from src.experiment.config import load_config
    from src.target.app import TargetApp
    from src.target.prompts import PROMPTS

    load_dotenv()
    config = load_config(config_path)
    model = config.models[0]
    provider = build_provider(model)
    prompt = next(iter(PROMPTS.values()))
    app = TargetApp(prompt=prompt, provider=provider)

    benign = "Hi! In one sentence, what can you help me with?"
    print(f"[prompt] {prompt.id} ({prompt.type})  [model] {model.model_id}")
    print(f"[user]   {benign}")
    print(f"[reply]  {app.query(benign)}")


def run_full(
    config: ExperimentConfig | None = None,
    provider_factory: Callable[[ModelSpec], Provider] | None = None,
    max_attempts: int = 3,
    retry_backoff: float = 3.0,
) -> dict:
    """Run the full matrix, score every response, write results.json + results.csv.

    Loops models x prompts x attacks x defenses x repeats. For each (prompt, attack,
    defense) the response is produced under the right system prompt and scored against the
    appropriate target:
      - ``none`` and ``instructional`` are scored against the ORIGINAL ``prompt.text`` (the
        secret is unchanged; ``instructional`` only hardens the system prompt);
      - ``output_filter`` is scored against the POST-filter ``response`` — what the attacker
        actually receives — so a redacted reply correctly counts as "did not leak".

    ``provider_factory`` maps a ModelSpec to a Provider; the default is ``build_provider``,
    which dispatches on ``spec.provider`` and imports the backend lazily, so importing this
    module needs no API key. Tests inject a fake factory to run fully offline. Returns the
    results dict.

    Each model call is retried up to ``max_attempts`` times with ``retry_backoff`` linear backoff
    (see ``_complete_with_retries``), so a transient free-tier stall does not abort the whole run;
    a persistent failure still propagates and aborts gracefully via the crash-safe ``finally``.

    Writes only scored results (results.json + results.csv). Raw per-response transcripts are
    not persisted here; the standalone Phase 2 runner is the transcript-capture tool.
    """
    import csv
    import json
    import random
    from pathlib import Path

    from dotenv import load_dotenv

    from src.attacks.queries import ATTACKS
    from src.experiment.config import load_config
    from src.scoring.normalize import NormalizationOptions
    from src.scoring.verifier import score_against_ground_truth, self_agreement
    from src.target.defenses import instructional, output_filter
    from src.target.prompts import PROMPTS

    # Load .env so a key placed there (e.g. OLLAMA_API_KEY, per the quickstart) is picked up
    # on `make run`, not just on `--smoke`. Without this, the provider silently falls back to
    # a local server and a first run fails with a confusing connection error.
    load_dotenv()
    config = config or load_config()

    # Bridge the config's normalization block into the scoring options, so the filter and the
    # scoring share one config-driven definition of normalization (reproducible from config).
    opts = NormalizationOptions(
        lowercase=config.normalization.lowercase,
        collapse_whitespace=config.normalization.collapse_whitespace,
        strip=config.normalization.strip,
    )

    if provider_factory is None:
        provider_factory = build_provider

    # Reproducibility hook: seed the global RNG even if the current matrix is deterministic.
    random.seed(config.seed)

    prompts = [p for p in PROMPTS.values() if p.type in config.prompt_types]
    attacks = ATTACKS

    # Surface the matrix scale BEFORE the loop so an operator sees the spend on a live run
    # (every cell is a real API call). query_budget is a reporting axis, not a cap here.
    projected = (
        len(config.models) * len(prompts) * len(attacks) * len(config.defenses) * config.repeats
    )
    print(
        f"[run_full] matrix: {len(config.models)} models x {len(prompts)} prompts x "
        f"{len(attacks)} attacks x {len(config.defenses)} defenses x {config.repeats} "
        f"repeats = {projected} queries"
    )

    rows: list[dict] = []
    groups: list[dict] = []

    results_dir = Path(config.results_dir)
    json_path = results_dir / "results.json"
    csv_path = results_dir / "results.csv"

    fieldnames = [
        "model_id",
        "prompt_id",
        "prompt_type",
        "attack_id",
        "family",
        "defense",
        "repeat",
        "exact",
        "rouge_l",
        "token_f1",
    ]

    # Crash-safe writer: persist WHATEVER rows/groups exist so far. Called from the `finally`
    # below, so it runs on success, on a caught Exception (e.g. a free-tier GPU cutoff
    # mid-run), and on KeyboardInterrupt — a partial run never loses its completed rows.
    def _write(results: dict) -> None:
        results_dir.mkdir(parents=True, exist_ok=True)
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    complete = False
    error: str | None = None
    try:
        for spec in config.models:
            provider = provider_factory(spec)
            for prompt in prompts:
                for attack in attacks:
                    for defense in config.defenses:
                        system = (
                            instructional(prompt.text)
                            if defense == "instructional"
                            else prompt.text
                        )
                        group_responses: list[str] = []
                        group_rouge: list[float] = []
                        for repeat in range(config.repeats):
                            raw = _complete_with_retries(
                                provider,
                                system,
                                attack.template,
                                max_attempts,
                                retry_backoff,
                            )
                            response = (
                                output_filter(
                                    raw, prompt.text, config.output_filter_threshold, opts
                                )
                                if defense == "output_filter"
                                else raw
                            )
                            # none/instructional score the original secret; output_filter
                            # scores the post-filter response (what the attacker receives).
                            scored = score_against_ground_truth(
                                prompt.text, response, attack.id, repeat, opts
                            )
                            rows.append(
                                {
                                    "model_id": spec.model_id,
                                    "prompt_id": prompt.id,
                                    "prompt_type": prompt.type,
                                    "attack_id": attack.id,
                                    "family": attack.family,
                                    "defense": defense,
                                    "repeat": repeat,
                                    "exact": scored.exact,
                                    "rouge_l": scored.rouge_l,
                                    "token_f1": scored.token_f1,
                                }
                            )
                            group_responses.append(response)
                            group_rouge.append(scored.rouge_l)

                        mean_rouge_l = (
                            sum(group_rouge) / len(group_rouge) if group_rouge else 0.0
                        )
                        groups.append(
                            {
                                "model_id": spec.model_id,
                                "prompt_id": prompt.id,
                                "attack_id": attack.id,
                                "defense": defense,
                                "self_agreement": self_agreement(group_responses),
                                "mean_rouge_l": mean_rouge_l,
                                "n": config.repeats,
                            }
                        )
        complete = True
    except Exception as exc:  # noqa: BLE001
        # A provider failure (e.g. a free-tier GPU-time cutoff raising RuntimeError) aborts the
        # run but must NOT lose the rows already collected. Capture it and fall through to the
        # `finally` write; do NOT re-raise — return the partial results gracefully.
        # KeyboardInterrupt is deliberately NOT caught here, so Ctrl-C propagates — but the
        # `finally` still writes the partial results first (with complete=False and error=None,
        # since this except never ran, which is the distinguishable "interrupted" signal).
        # The error string holds the provider's exception message, which carries no API key by
        # design: OllamaProvider wraps urllib errors to host+status, and the Anthropic SDK does
        # not echo the key.
        complete = False
        error = f"{type(exc).__name__}: {exc}"
    finally:
        results = {
            "seed": config.seed,
            "query_count": len(rows),  # ACTUAL completed count, not the projected total
            "responses": rows,
            "groups": groups,
            "complete": complete,
            "error": error,
        }
        try:
            _write(results)
        except OSError as write_exc:
            # A write failure must NOT mask the real abort cause: surface it as a warning and
            # still return the in-memory results rather than raising out of `finally`.
            print(f"[run_full] WARNING: could not write results to {results_dir}: {write_exc}")

    if complete:
        print(
            f"[run_full] {len(rows)} rows, query_count={len(rows)} -> "
            f"{json_path} | {csv_path}"
        )
    else:
        print(
            f"[run_full] ABORTED after {len(rows)} of {projected} calls: {error}. "
            f"Partial results saved to {json_path}."
        )
    return results


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
        run_smoke(args.config)
    else:
        from src.experiment.config import load_config

        run_full(load_config(args.config))


if __name__ == "__main__":
    main()

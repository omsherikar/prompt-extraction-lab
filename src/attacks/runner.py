"""The attack runner.

Phase 2: given a TargetApp and the attack list, run every attack `repeat=k` times, capture
(attack_id, repeat, model_response), and persist raw transcripts to data/transcripts/. Record
query counts so the post can report success against a budget. The runner does no scoring;
scoring is Phase 3 and lives in src/scoring/.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from src.attacks.queries import Attack
from src.target.app import TargetApp

# Default location for raw transcripts; tests override this via tmp_path.
DEFAULT_TRANSCRIPTS_DIR = "data/transcripts"

# Characters allowed verbatim in a transcript filename stem. Anything else (path
# separators, colons, spaces, ...) is collapsed to '_' so model/prompt ids cannot escape
# transcripts_dir or create stray subdirectories.
_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class AttackRun:
    """One raw (attack, repeat) result before any scoring."""

    attack_id: str
    repeat: int
    response: str


def _sanitize(component: str) -> str:
    """Make one id safe to embed in a flat filename (no path separators, etc.)."""
    return _UNSAFE_CHARS.sub("_", component)


def _transcript_path(transcripts_dir: str, model_id: str, prompt_id: str) -> Path:
    """Deterministic transcript path keyed by model + prompt id."""
    name = f"{_sanitize(model_id)}__{_sanitize(prompt_id)}.jsonl"
    return Path(transcripts_dir) / name


def run_attacks(
    app: TargetApp,
    attacks: list[Attack],
    repeat: int,
    transcripts_dir: str = DEFAULT_TRANSCRIPTS_DIR,
) -> list[AttackRun]:
    """Run each attack `repeat` times against `app`, returning raw runs.

    For every attack and every repeat index ``0 .. repeat-1`` this calls
    ``app.query(attack.template)``, records an ``AttackRun(attack_id, repeat, response)``,
    and appends a JSONL line carrying the response plus its identifying metadata to a
    deterministic transcript under ``transcripts_dir`` (keyed by model + prompt id). The
    transcript directory is created if missing. No scoring is performed here; that is
    Phase 3 (``src/scoring/``). The returned list has ``len(attacks) * repeat`` records, so
    its length is the total query count.
    """
    prompt = app.prompt
    model_id = app.provider.model_id

    out_dir = Path(transcripts_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = _transcript_path(transcripts_dir, model_id, prompt.id)

    runs: list[AttackRun] = []
    with path.open("w", encoding="utf-8") as fh:
        for attack in attacks:
            for index in range(repeat):
                response = app.query(attack.template)
                runs.append(
                    AttackRun(attack_id=attack.id, repeat=index, response=response)
                )
                record = {
                    "prompt_id": prompt.id,
                    "prompt_type": prompt.type,
                    "model_id": model_id,
                    "attack_id": attack.id,
                    "family": attack.family,
                    "repeat": index,
                    "response": response,
                }
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    return runs

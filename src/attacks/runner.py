"""The attack runner.

Phase 2: given a TargetApp and the attack list, run every attack `repeat=k` times, capture
(attack_id, repeat, model_response), and persist raw transcripts to data/transcripts/. Record
query counts so the post can report success against a budget. The runner does no scoring;
scoring is Phase 3 and lives in src/scoring/.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.attacks.queries import Attack
from src.target.app import TargetApp


@dataclass(frozen=True)
class AttackRun:
    """One raw (attack, repeat) result before any scoring."""

    attack_id: str
    repeat: int
    response: str


def run_attacks(app: TargetApp, attacks: list[Attack], repeat: int) -> list[AttackRun]:
    """Run each attack `repeat` times against `app`, returning raw runs."""
    # Phase 2: loop attacks x repeat, call app.query(attack.template), collect AttackRun records,
    # and persist the raw transcript to data/transcripts/.
    raise NotImplementedError("Phase 2: implement the runner")

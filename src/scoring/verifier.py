"""The verifier: ground-truth scoring, and the no-ground-truth self-agreement demonstration.

This is the piece that makes the post original. Two modes:

  Ground-truth mode: score every response against the known true prompt with the metrics.
  This is what we can do because we control the secret.

  No-ground-truth mode: for the k repeats of one attack, compute pairwise Rouge-L *between the
  extractions themselves* to get a self-agreement score. Hypothesis: real extractions agree
  across runs, confabulations diverge. Validate by correlating self-agreement against the true
  ground-truth score. If they correlate, we have a way to estimate extraction reliability
  without the secret (the realistic attacker's situation), proven using our controlled setup.

INTEGRITY INVARIANT: the self-agreement score must be computed ONLY from the extractions
themselves. The true prompt must never touch that path. If it does, the headline result is
invalid. Tests must guard this.

Phase 3: implement, test-first.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoredResponse:
    """A single response scored against ground truth."""

    attack_id: str
    repeat: int
    exact: bool
    rouge_l: float
    token_f1: float


def score_against_ground_truth(true_prompt: str, response: str, attack_id: str, repeat: int) -> ScoredResponse:
    """Score one response against the known true prompt (ground-truth mode)."""
    # Phase 3: call the three metrics and package a ScoredResponse.
    raise NotImplementedError("Phase 3: implement ground-truth scoring")


def self_agreement(extractions: list[str]) -> float:
    """Mean pairwise Rouge-L among the k extractions of one attack (no-ground-truth mode).

    Computed only from the extractions; the true prompt is deliberately not a parameter here.
    """
    # Phase 3: average rouge_l_recall over all unordered pairs of extractions.
    raise NotImplementedError("Phase 3: implement self_agreement")

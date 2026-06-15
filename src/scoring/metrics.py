"""The three extraction metrics. Pure functions: strings in, numbers out.

  - exact_recovery: verbatim recovery (contiguous substring after normalization).
  - rouge_l_recall: primary continuous metric, LCS length over true-prompt token count.
    Implemented in-repo (no external dependency) so it is fully under our control and testable.
  - token_f1: secondary, order-insensitive overlap.

Phase 3: implement, test-first. Each function assumes inputs are already normalized by the
caller (the verifier), or normalizes via an explicit option; keep that choice consistent and
documented. These are the most-tested functions in the repo.
"""

from __future__ import annotations


def exact_recovery(true_prompt: str, response: str) -> bool:
    """True if the (normalized) true prompt appears as a contiguous substring of the response."""
    # Phase 3: substring containment after normalization.
    raise NotImplementedError("Phase 3: implement exact_recovery")


def rouge_l_recall(true_prompt: str, response: str) -> float:
    """LCS length between true prompt and response, divided by true-prompt token count.

    Recall-oriented Rouge-L: how much of the true prompt's token sequence survives, in order,
    somewhere in the response. Returns 0.0 for an empty true prompt by convention (documented
    and tested).
    """
    # Phase 3: tokenize, compute LCS length, divide by len(true tokens). Hand-verify on a
    # fixed example in the tests before trusting it.
    raise NotImplementedError("Phase 3: implement rouge_l_recall")


def token_f1(true_prompt: str, response: str) -> float:
    """Order-insensitive token overlap F1 between true prompt and response."""
    # Phase 3: multiset/precision-recall F1 over tokens.
    raise NotImplementedError("Phase 3: implement token_f1")

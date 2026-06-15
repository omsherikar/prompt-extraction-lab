"""The three extraction metrics. Pure functions: strings in, numbers out.

  - exact_recovery: verbatim recovery (contiguous substring after normalization).
  - rouge_l_recall: primary continuous metric, LCS length over true-prompt token count.
    Implemented in-repo (no external dependency) so it is fully under our control and testable.
  - token_f1: secondary, order-insensitive overlap.

Phase 3: each function normalizes its raw string inputs internally via ``opts`` (default all
flags on), reusing the single normalization chokepoint in ``src.scoring.normalize`` so there
is no second, divergent normalization path. Both token metrics share ONE tokenizer (see
``_tokenize``): the whitespace split of the normalized text. These are the most-tested
functions in the repo; values are hand-verified in ``tests/test_metrics.py``.
"""

from __future__ import annotations

from collections import Counter

from src.scoring.normalize import NormalizationOptions, normalize

# Default normalization: all flags on. Shared module-level singleton so it can be used as an
# argument default without a per-call construction (ruff B008). Safe to share because
# NormalizationOptions is a frozen (immutable) dataclass.
_DEFAULT_OPTS = NormalizationOptions()


def _tokenize(text: str, opts: NormalizationOptions) -> list[str]:
    """The single tokenizer for both token metrics: whitespace-split the normalized text.

    ``str.split()`` with no argument splits on runs of whitespace and discards empties, so an
    empty or whitespace-only input yields ``[]``. Both ``rouge_l_recall`` and ``token_f1``
    tokenize through here, guaranteeing they agree on what a "token" is.
    """
    return normalize(text, opts).split()


def _lcs_length(a: list[str], b: list[str]) -> int:
    """Length of the longest common subsequence of two token lists (standard O(m*n) DP).

    Subsequence, not substring: tokens must appear in the same relative order but need not be
    contiguous. ``dp[i][j]`` is the LCS length of ``a[:i]`` and ``b[:j]``.
    """
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]


def exact_recovery(
    true_prompt: str, response: str, opts: NormalizationOptions = _DEFAULT_OPTS
) -> bool:
    """True if the normalized true prompt is a contiguous substring of the normalized response.

    Both sides are normalized through the same chokepoint, so with the default (all-on) opts a
    case- or whitespace-only difference still counts as a recovery; disabling a flag (e.g.
    ``lowercase``) makes that difference matter again.
    """
    return normalize(true_prompt, opts) in normalize(response, opts)


def rouge_l_recall(
    true_prompt: str, response: str, opts: NormalizationOptions = _DEFAULT_OPTS
) -> float:
    """LCS length between the true-prompt and response token lists, divided by true-token count.

    Recall-oriented ROUGE-L: how much of the true prompt's token sequence survives, in order,
    somewhere in the response. Both sides use the shared ``_tokenize``; the LCS is computed in
    repo via the standard O(m*n) DP table (no ``rouge-score`` dependency). An empty true prompt
    (zero tokens) returns 0.0 by convention rather than dividing by zero.
    """
    true_tokens = _tokenize(true_prompt, opts)
    if not true_tokens:
        return 0.0
    response_tokens = _tokenize(response, opts)
    return _lcs_length(true_tokens, response_tokens) / len(true_tokens)


def token_f1(
    true_prompt: str, response: str, opts: NormalizationOptions = _DEFAULT_OPTS
) -> float:
    """Order-insensitive multiset token-overlap F1 between true prompt and response.

    Overlap is the sum over token types of ``min(count_in_true, count_in_response)`` (so a
    token repeated k times in both contributes k). Precision divides overlap by the response
    token count, recall by the true token count, and F1 is their harmonic mean. Conventions:
    both empty -> 1.0 (vacuously identical); exactly one empty -> 0.0.
    """
    true_tokens = _tokenize(true_prompt, opts)
    response_tokens = _tokenize(response, opts)

    if not true_tokens and not response_tokens:
        return 1.0
    if not true_tokens or not response_tokens:
        return 0.0

    overlap = sum((Counter(true_tokens) & Counter(response_tokens)).values())
    if overlap == 0:
        return 0.0

    precision = overlap / len(response_tokens)
    recall = overlap / len(true_tokens)
    return 2 * precision * recall / (precision + recall)

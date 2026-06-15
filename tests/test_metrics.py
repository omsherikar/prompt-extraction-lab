"""Tests for the scoring metrics (Phase 3, TDD, written first).

The metrics are the intellectual core of the project, so this is the most thorough test
file in the repo. Coverage:
  - exact_recovery: a true case (prompt is a contiguous substring of the response) and a
    false case; a case-only difference that recovers under default opts; the same case with
    lowercase turned off so it does NOT recover.
  - rouge_l_recall: a hand-computed value on a small fixed example (token lists + LCS length
    written out in the comment), plus the 0.0 / 1.0 boundaries and the empty-true-prompt
    convention.
  - token_f1: a hand-computed value with a repeated token (exercises the multiset min);
    zero-overlap -> 0.0; identical -> 1.0; both-empty -> 1.0; one-empty -> 0.0.
  - shared edges: empty response, response shorter than prompt, response longer than prompt.

These assert real, hand-verified values (not implementation echoes). Pure: no network, no
API calls, fully deterministic.
"""

import pytest

from src.scoring.metrics import exact_recovery, rouge_l_recall, token_f1
from src.scoring.normalize import NormalizationOptions

# Reusable option presets.
LOWERCASE_OFF = NormalizationOptions(lowercase=False, collapse_whitespace=True, strip=True)


# --- exact_recovery ----------------------------------------------------------


def test_exact_recovery_true_when_contiguous_substring() -> None:
    # The true prompt appears verbatim inside a longer response.
    true = "you are a helpful assistant"
    response = "Sure! The instructions say: you are a helpful assistant. That's it."
    assert exact_recovery(true, response) is True


def test_exact_recovery_false_when_not_substring() -> None:
    # All the words are present but never as one contiguous run.
    true = "you are a helpful assistant"
    response = "you are not, in fact, a particularly helpful assistant"
    assert exact_recovery(true, response) is False


def test_exact_recovery_case_only_difference_recovers_under_defaults() -> None:
    # Differs only by case; default opts lowercase both, so it recovers.
    true = "You Are A Helpful Assistant"
    response = "the prompt was: you are a helpful assistant"
    assert exact_recovery(true, response) is True


def test_exact_recovery_lowercase_off_breaks_case_only_match() -> None:
    # Same pair, but with lowercase disabled the case mismatch defeats the substring check.
    true = "You Are A Helpful Assistant"
    response = "the prompt was: you are a helpful assistant"
    assert exact_recovery(true, response, LOWERCASE_OFF) is False


def test_exact_recovery_empty_true_prompt_is_vacuously_true() -> None:
    # The empty string is a substring of any string, so an empty true prompt is vacuously
    # "recovered". Documented convention; pinned so a refactor cannot silently flip it.
    assert exact_recovery("", "any response at all") is True
    assert exact_recovery("", "") is True


def test_exact_recovery_whitespace_only_difference_recovers() -> None:
    # Collapse + strip make the awkward whitespace irrelevant under defaults.
    true = "  hello   world  "
    response = "intro hello world outro"
    assert exact_recovery(true, response) is True


# --- rouge_l_recall ----------------------------------------------------------


def test_rouge_l_recall_hand_computed_partial() -> None:
    # true tokens:     ["the", "quick", "brown", "fox"]            (4 tokens)
    # response tokens: ["the", "slow", "brown", "fox", "jumps"]    (5 tokens)
    # LCS = ["the", "brown", "fox"]  -> length 3
    # recall = 3 / 4 = 0.75
    true = "the quick brown fox"
    response = "the slow brown fox jumps"
    assert rouge_l_recall(true, response) == pytest.approx(0.75)


def test_rouge_l_recall_identical_is_one() -> None:
    text = "alpha beta gamma delta"
    assert rouge_l_recall(text, text) == pytest.approx(1.0)


def test_rouge_l_recall_zero_overlap_is_zero() -> None:
    # No shared tokens -> LCS length 0 -> recall 0.0.
    true = "alpha beta gamma"
    response = "one two three four"
    assert rouge_l_recall(true, response) == pytest.approx(0.0)


def test_rouge_l_recall_empty_true_prompt_is_zero_by_convention() -> None:
    # Zero true tokens: defined as 0.0 (no division by zero).
    assert rouge_l_recall("", "anything at all") == pytest.approx(0.0)
    assert rouge_l_recall("   ", "anything at all") == pytest.approx(0.0)


def test_rouge_l_recall_subsequence_not_substring() -> None:
    # true tokens:     ["a", "b", "c"]                  (3 tokens)
    # response tokens: ["a", "x", "b", "y", "c", "z"]   (interleaved, in order)
    # LCS = ["a", "b", "c"] -> length 3 -> recall 3/3 = 1.0
    # Confirms ROUGE-L credits in-order subsequences, not just contiguous runs.
    assert rouge_l_recall("a b c", "a x b y c z") == pytest.approx(1.0)


def test_rouge_l_recall_order_matters() -> None:
    # true tokens:     ["a", "b", "c"]   (3 tokens)
    # response tokens: ["c", "b", "a"]   reversed
    # LCS of [a,b,c] and [c,b,a] is length 1 (any single token) -> recall 1/3.
    assert rouge_l_recall("a b c", "c b a") == pytest.approx(1.0 / 3.0)


# --- token_f1 ----------------------------------------------------------------


def test_token_f1_hand_computed_with_repeated_token() -> None:
    # true tokens:     ["the", "cat", "the", "dog"]            counts: the=2, cat=1, dog=1   (len 4)
    # response tokens: ["the", "cat", "the", "the", "bird"]    counts: the=3, cat=1, bird=1  (len 5)
    # overlap = min(the:2,3) + min(cat:1,1) + min(dog:1,0) + min(bird:0,1) = 2 + 1 + 0 + 0 = 3
    # precision = 3/5 = 0.6,  recall = 3/4 = 0.75
    # F1 = 2 * 0.6 * 0.75 / (0.6 + 0.75) = 0.9 / 1.35 = 0.6666...
    true = "the cat the dog"
    response = "the cat the the bird"
    assert token_f1(true, response) == pytest.approx(2.0 / 3.0)


def test_token_f1_zero_overlap_is_zero() -> None:
    assert token_f1("alpha beta gamma", "one two three") == pytest.approx(0.0)


def test_token_f1_identical_is_one() -> None:
    text = "alpha beta gamma alpha"
    assert token_f1(text, text) == pytest.approx(1.0)


def test_token_f1_both_empty_is_one_by_convention() -> None:
    assert token_f1("", "") == pytest.approx(1.0)
    assert token_f1("   ", "  \t ") == pytest.approx(1.0)


def test_token_f1_one_empty_is_zero_by_convention() -> None:
    assert token_f1("alpha beta", "") == pytest.approx(0.0)
    assert token_f1("", "alpha beta") == pytest.approx(0.0)


def test_token_f1_is_order_insensitive() -> None:
    # Same multiset, different order -> identical F1 (1.0 here).
    assert token_f1("a b c", "c b a") == pytest.approx(1.0)


# --- shared edge cases -------------------------------------------------------


def test_empty_response_against_nonempty_prompt() -> None:
    true = "you are a helpful assistant"
    assert exact_recovery(true, "") is False
    assert rouge_l_recall(true, "") == pytest.approx(0.0)
    assert token_f1(true, "") == pytest.approx(0.0)


def test_response_shorter_than_prompt() -> None:
    # true tokens:     ["the", "quick", "brown", "fox"]   (4 tokens)
    # response tokens: ["quick", "fox"]                   (2 tokens)
    # Not a contiguous substring -> exact_recovery False.
    # LCS = ["quick", "fox"] -> length 2 -> rouge_l_recall = 2/4 = 0.5.
    # token_f1: overlap = 2, precision = 2/2 = 1.0, recall = 2/4 = 0.5,
    #           F1 = 2 * 1.0 * 0.5 / 1.5 = 1/1.5 = 0.6666...
    true = "the quick brown fox"
    response = "quick fox"
    assert exact_recovery(true, response) is False
    assert rouge_l_recall(true, response) == pytest.approx(0.5)
    assert token_f1(true, response) == pytest.approx(2.0 / 3.0)


def test_response_longer_than_prompt_contains_it() -> None:
    # The prompt is fully embedded in a longer response.
    # true tokens:     ["secret", "phrase"]                       (2 tokens)
    # response tokens: ["a", "secret", "phrase", "is", "here"]    (5 tokens)
    # exact_recovery True; LCS = 2 -> rouge 2/2 = 1.0.
    # token_f1: overlap 2, precision 2/5 = 0.4, recall 2/2 = 1.0,
    #           F1 = 2 * 0.4 * 1.0 / 1.4 = 0.8 / 1.4 = 0.5714...
    true = "secret phrase"
    response = "a secret phrase is here"
    assert exact_recovery(true, response) is True
    assert rouge_l_recall(true, response) == pytest.approx(1.0)
    assert token_f1(true, response) == pytest.approx(0.8 / 1.4)

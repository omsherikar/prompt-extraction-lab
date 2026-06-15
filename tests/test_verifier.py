"""Tests for the verifier (Phase 3, TDD, written first).

The verifier has two modes and one non-negotiable invariant.

Coverage:
  - score_against_ground_truth: on a known (true_prompt, response) pair, the returned
    ScoredResponse carries the right attack_id/repeat and metric values consistent with the
    three metrics (one hand-reasoned rouge_l value, one exact True/False).
  - self_agreement: k identical extractions -> 1.0; k non-overlapping extractions -> low;
    a single extraction and the empty list -> 1.0 by convention (no disagreement possible).
  - INTEGRITY GUARD (P3-A3): self_agreement depends ONLY on the extractions. Enforced two
    ways: (1) inspect its signature and assert it takes exactly one parameter, so a "true
    prompt" cannot even be passed; (2) assert its result for a fixed extraction list is
    identical no matter what unrelated "true prompt" value a caller has in scope. This guards
    the headline no-ground-truth result against ground-truth leakage.
  - agreement_vs_truth_correlation: perfectly correlated -> ~1.0; perfectly anti-correlated
    -> ~-1.0; a constant (zero-variance) list -> 0.0 by convention; mismatched lengths ->
    ValueError.

Pure: no network, no API calls, fully deterministic.
"""

import inspect

import pytest

from src.scoring.verifier import (
    ScoredResponse,
    agreement_vs_truth_correlation,
    score_against_ground_truth,
    self_agreement,
)

# --- score_against_ground_truth ---------------------------------------------


def test_score_against_ground_truth_packs_record_and_metrics() -> None:
    # The prompt is fully embedded in a longer response.
    #   true tokens:     ["secret", "phrase"]                       (2 tokens)
    #   response tokens: ["a", "secret", "phrase", "is", "here"]    (5 tokens)
    # exact_recovery: True (contiguous substring).
    # rouge_l_recall: LCS = 2 -> 2/2 = 1.0.
    # token_f1: overlap 2, precision 2/5 = 0.4, recall 2/2 = 1.0 -> 0.8/1.4 = 0.5714...
    true = "secret phrase"
    response = "a secret phrase is here"
    scored = score_against_ground_truth(true, response, attack_id="atk-1", repeat=2)

    assert isinstance(scored, ScoredResponse)
    assert scored.attack_id == "atk-1"
    assert scored.repeat == 2
    assert scored.exact is True
    assert scored.rouge_l == pytest.approx(1.0)
    assert scored.token_f1 == pytest.approx(0.8 / 1.4)


def test_score_against_ground_truth_miss_records_false_and_partial() -> None:
    # Words present but never contiguous, and only partial in-order overlap.
    #   true tokens:     ["the", "quick", "brown", "fox"]   (4 tokens)
    #   response tokens: ["quick", "fox"]                    (2 tokens)
    # exact_recovery: False; rouge_l: LCS ["quick","fox"] = 2 -> 2/4 = 0.5.
    true = "the quick brown fox"
    response = "quick fox"
    scored = score_against_ground_truth(true, response, attack_id="atk-2", repeat=0)

    assert scored.attack_id == "atk-2"
    assert scored.repeat == 0
    assert scored.exact is False
    assert scored.rouge_l == pytest.approx(0.5)


# --- self_agreement ----------------------------------------------------------


def test_self_agreement_identical_extractions_is_one() -> None:
    # Every pair is identical -> every symmetric pairwise Rouge-L is 1.0 -> mean 1.0.
    extractions = ["you are a helpful assistant"] * 3
    assert self_agreement(extractions) == pytest.approx(1.0)


def test_self_agreement_non_overlapping_extractions_is_low() -> None:
    # Three extractions with no shared tokens: every pairwise Rouge-L is 0.0, so the mean is
    # 0.0. This is the confabulation regime: divergent runs do not agree. Asserting a hard
    # floor (well under 0.1) documents "low" with a justified threshold.
    extractions = [
        "alpha beta gamma delta",
        "one two three four",
        "red green blue yellow",
    ]
    agreement = self_agreement(extractions)
    assert agreement == pytest.approx(0.0)
    assert agreement < 0.1


def test_self_agreement_partial_overlap_is_intermediate() -> None:
    # Two extractions, symmetric Rouge-L:
    #   a = ["the","quick","brown","fox"]   b = ["the","slow","brown","fox","jumps"]
    #   rouge_l_recall(a,b): LCS ["the","brown","fox"]=3 over len(a)=4 -> 0.75
    #   rouge_l_recall(b,a): same LCS 3 over len(b)=5            -> 0.6
    #   symmetric = (0.75 + 0.6) / 2 = 0.675  (one pair -> mean is that value)
    extractions = ["the quick brown fox", "the slow brown fox jumps"]
    assert self_agreement(extractions) == pytest.approx(0.675)


def test_self_agreement_single_extraction_is_one_by_convention() -> None:
    # Fewer than two extractions: no pair exists, so disagreement is impossible -> 1.0.
    assert self_agreement(["just one extraction"]) == pytest.approx(1.0)


def test_self_agreement_empty_list_is_one_by_convention() -> None:
    assert self_agreement([]) == pytest.approx(1.0)


# --- INTEGRITY GUARD (P3-A3): no ground-truth leakage ------------------------


def test_self_agreement_signature_takes_exactly_one_parameter() -> None:
    # Structural guard: the true prompt cannot leak into self_agreement because there is
    # nowhere to pass it. Exactly one parameter (the extractions list).
    params = inspect.signature(self_agreement).parameters
    assert len(params) == 1


def test_self_agreement_independent_of_any_true_prompt_value() -> None:
    # Behavioural guard: a caller may hold the secret in scope, but the result must depend
    # ONLY on the extractions. We compute self_agreement on a fixed list while varying an
    # unrelated "true prompt" value; the result must not move (it is not even an input).
    extractions = ["the quick brown fox", "the slow brown fox jumps"]
    expected = self_agreement(extractions)

    for true_prompt in ["", "the quick brown fox", "totally unrelated secret text", "x" * 50]:
        _ = true_prompt  # deliberately unused: it must have zero effect on the score
        assert self_agreement(extractions) == pytest.approx(expected)


# --- agreement_vs_truth_correlation ------------------------------------------


def test_correlation_perfectly_correlated_is_one() -> None:
    # Strictly increasing together (positive linear relation) -> Pearson r = +1.0.
    agreements = [0.1, 0.5, 0.9]
    truths = [1.0, 2.0, 3.0]
    assert agreement_vs_truth_correlation(agreements, truths) == pytest.approx(1.0)


def test_correlation_perfectly_anticorrelated_is_minus_one() -> None:
    # One rises as the other falls (negative linear relation) -> Pearson r = -1.0.
    agreements = [1.0, 2.0, 3.0]
    truths = [3.0, 2.0, 1.0]
    assert agreement_vs_truth_correlation(agreements, truths) == pytest.approx(-1.0)


def test_correlation_hand_computed_intermediate() -> None:
    # x = [0.0, 1.0, 2.0]  mean 1.0  deviations [-1, 0, 1]
    # y = [1.0, 0.0, 2.0]  mean 1.0  deviations [ 0,-1, 1]
    # cov_sum = (-1*0) + (0*-1) + (1*1) = 1
    # var_x_sum = 1+0+1 = 2 ; var_y_sum = 0+1+1 = 2
    # r = 1 / sqrt(2*2) = 1/2 = 0.5
    agreements = [0.0, 1.0, 2.0]
    truths = [1.0, 0.0, 2.0]
    assert agreement_vs_truth_correlation(agreements, truths) == pytest.approx(0.5)


def test_correlation_constant_list_returns_zero_by_convention() -> None:
    # Zero variance on either side -> Pearson is undefined (0/0). By documented convention
    # we return 0.0 rather than dividing by zero.
    assert agreement_vs_truth_correlation([0.5, 0.5, 0.5], [1.0, 2.0, 3.0]) == pytest.approx(0.0)
    assert agreement_vs_truth_correlation([1.0, 2.0, 3.0], [0.5, 0.5, 0.5]) == pytest.approx(0.0)
    assert agreement_vs_truth_correlation([2.0, 2.0], [2.0, 2.0]) == pytest.approx(0.0)


def test_correlation_mismatched_lengths_raises() -> None:
    with pytest.raises(ValueError):
        agreement_vs_truth_correlation([0.1, 0.2, 0.3], [1.0, 2.0])

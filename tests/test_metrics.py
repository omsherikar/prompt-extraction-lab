"""Tests for the scoring metrics. Write these FIRST (Phase 3, TDD).

The metrics are the core of the project, so they get the most thorough tests. Required coverage:
  - exact_recovery: a true case (prompt is a contiguous substring of the response) and a false
    case; normalization on/off changing the outcome.
  - rouge_l_recall: a known value on a small fixed example whose LCS you computed by hand;
    0.0 and 1.0 boundaries; empty true prompt convention.
  - token_f1: a known value; zero-overlap -> 0.0; identical strings -> 1.0.
  - shared edge cases: empty response, response shorter than prompt, response longer than prompt.

Keep these fast and deterministic: no network, no API calls.
"""

import pytest

# Phase 3: from src.scoring.metrics import exact_recovery, rouge_l_recall, token_f1


@pytest.mark.skip(reason="Phase 3: implement metrics and these tests first (TDD)")
def test_metrics_placeholder() -> None:
    raise NotImplementedError

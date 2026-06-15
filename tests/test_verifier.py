"""Tests for the verifier. Write these FIRST (Phase 3, TDD).

Required coverage:
  - score_against_ground_truth produces a correct per-response record on a known example.
  - self_agreement: k identical extractions -> 1.0; k wildly divergent -> low.
  - INTEGRITY GUARD: self_agreement must depend only on the extractions. A test should confirm
    its result does not change when the (unrelated) true prompt changes, since the true prompt is
    not even a parameter. This guards the headline no-ground-truth result.
  - the self-agreement vs ground-truth correlation pathway runs on a small synthetic set.
"""

import pytest

# Phase 3: from src.scoring.verifier import score_against_ground_truth, self_agreement


@pytest.mark.skip(reason="Phase 3: implement verifier and these tests first (TDD)")
def test_verifier_placeholder() -> None:
    raise NotImplementedError

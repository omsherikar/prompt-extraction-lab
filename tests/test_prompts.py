# tests/test_prompts.py
"""Tests for Phase 1 ground-truth prompts (src/target/prompts.py).

These tests enforce the structural contract of the PROMPTS registry: it is the source of
ground truth for leakage scoring, so registry consistency (keys == ids), type coverage,
id uniqueness, and non-empty text all matter. Fast and deterministic — pure data checks,
no network, no API calls.
"""

from __future__ import annotations

import typing

from src.target.prompts import PROMPTS, PromptType, TargetPrompt

# The allowed structural types, derived from the PromptType Literal so the test stays in
# sync with the source of truth rather than hardcoding a parallel list.
ALLOWED_TYPES: frozenset[str] = frozenset(typing.get_args(PromptType))


def test_registry_is_nonempty_and_values_are_targetprompts() -> None:
    """PROMPTS is non-empty and every value is a TargetPrompt instance.

    Requirement: the registry is the ground-truth secret store; it must contain typed
    records, not raw strings or other shapes.
    """
    assert isinstance(PROMPTS, dict)
    assert len(PROMPTS) > 0, "PROMPTS must contain at least one prompt"
    for key, value in PROMPTS.items():
        assert isinstance(value, TargetPrompt), f"value for {key!r} is not a TargetPrompt"


def test_registry_keys_match_value_ids() -> None:
    """Every registry key equals its value's id (registry consistency).

    Requirement: results key off prompt ids, so the dict key and the record id must agree
    or lookups silently diverge.
    """
    for key, value in PROMPTS.items():
        assert key == value.id, f"key {key!r} does not match its value's id {value.id!r}"


def test_all_three_types_present_with_at_least_two_entries_each() -> None:
    """Each of the three structural types has >= 2 entries.

    Requirement: Phase 1 calls for 2-3 prompts per type so the 'extractability varies by
    structure' comparison has more than one sample per cell.
    """
    counts: dict[str, int] = {}
    for value in PROMPTS.values():
        counts[value.type] = counts.get(value.type, 0) + 1

    for expected in ("direct", "role", "in_context"):
        assert counts.get(expected, 0) >= 2, (
            f"type {expected!r} must have >= 2 entries; got {counts.get(expected, 0)}"
        )


def test_all_ids_are_unique() -> None:
    """All prompt ids are unique across the registry.

    Requirement: ids are the join key for scoring; duplicates would collide results.
    """
    ids = [value.id for value in PROMPTS.values()]
    assert len(ids) == len(set(ids)), f"duplicate prompt ids found: {ids}"


def test_all_types_are_within_allowed_set() -> None:
    """Every prompt's type is one of the allowed PromptType values.

    Requirement: only direct / role / in_context are valid structural types.
    """
    for value in PROMPTS.values():
        assert value.type in ALLOWED_TYPES, (
            f"prompt {value.id!r} has invalid type {value.type!r}; "
            f"allowed: {sorted(ALLOWED_TYPES)}"
        )


def test_all_texts_are_nonempty() -> None:
    """Every prompt's text is a non-empty string (after stripping whitespace).

    Requirement: an empty ground-truth secret cannot be measured for leakage.
    """
    for value in PROMPTS.values():
        assert isinstance(value.text, str), f"text for {value.id!r} is not a str"
        assert value.text.strip() != "", f"text for {value.id!r} is empty/whitespace-only"

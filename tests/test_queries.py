"""Tests for the cited attack library in `src/attacks/queries.py`.

These tests encode the invariants the registry must hold, independent of the exact
wording of any single attack: it is non-empty, ids are unique, every entry is cited,
every required family is represented, families stay within the allowed set, and no
template is blank. They do not assert on novel content (there is none); they guard the
shape and the citation discipline the project is built on.
"""

from __future__ import annotations

from src.attacks.queries import ALLOWED_SOURCES, ATTACKS, Attack

# Families this phase must cover. `evasion` is Phase 4 and deliberately excluded here.
REQUIRED_FAMILIES = {
    "direct",
    "ignore_reveal",
    "repetition",
    "format_coercion",
    "role_debug",
}

# The full allowed set every entry's `family` must fall within.
ALLOWED_FAMILIES = REQUIRED_FAMILIES | {"evasion"}


def test_attacks_non_empty() -> None:
    assert ATTACKS, "ATTACKS must not be empty"


def test_attacks_are_attack_instances() -> None:
    assert all(isinstance(a, Attack) for a in ATTACKS)


def test_ids_unique() -> None:
    ids = [a.id for a in ATTACKS]
    assert len(ids) == len(set(ids)), "attack ids must be unique"


def test_ids_non_empty() -> None:
    assert all(a.id.strip() for a in ATTACKS), "every attack must have a non-empty id"


def test_every_source_non_empty() -> None:
    # No uncited attacks: this is the core citation discipline of the project.
    for a in ATTACKS:
        assert a.source.strip(), f"attack {a.id!r} has an empty source"


def test_every_source_is_a_known_citation() -> None:
    # Pin each source to the closed ALLOWED_SOURCES set, so a future edit cannot introduce
    # an uncited or fabricated citation and stay green. This is the project's credibility
    # backbone, enforced rather than left to convention.
    for a in ATTACKS:
        assert a.source in ALLOWED_SOURCES, (
            f"attack {a.id!r} cites an unapproved source: {a.source!r}"
        )


def test_no_placeholder_sources() -> None:
    # The seed entry shipped a TODO placeholder source; it must be gone.
    for a in ATTACKS:
        assert "TODO" not in a.source, f"attack {a.id!r} still has a TODO source"


def test_every_template_non_empty() -> None:
    for a in ATTACKS:
        assert a.template.strip(), f"attack {a.id!r} has an empty template"


def test_every_family_within_allowed_set() -> None:
    for a in ATTACKS:
        assert a.family in ALLOWED_FAMILIES, (
            f"attack {a.id!r} has family {a.family!r} outside {ALLOWED_FAMILIES}"
        )


def test_all_required_families_present() -> None:
    present = {a.family for a in ATTACKS}
    missing = REQUIRED_FAMILIES - present
    assert not missing, f"missing required families: {missing}"

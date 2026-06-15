"""Tests for the single normalization chokepoint (Phase 3, TDD, written first).

`normalize` is the only place normalization happens in the repo, so it gets explicit
coverage of each flag independently (on and off), the all-on combination, idempotence,
and the awkward inputs (empty, whitespace-only, multiline with tabs/newlines).

Pure: no I/O, no network.
"""

from src.scoring.normalize import NormalizationOptions, normalize

# Reusable option presets.
ALL_OFF = NormalizationOptions(lowercase=False, collapse_whitespace=False, strip=False)
ALL_ON = NormalizationOptions(lowercase=True, collapse_whitespace=True, strip=True)


# --- each flag independently ON (others off) ---------------------------------


def test_lowercase_only() -> None:
    opts = NormalizationOptions(lowercase=True, collapse_whitespace=False, strip=False)
    # Only case changes; the double space and the leading/trailing spaces survive.
    assert normalize("  HeLLo  World  ", opts) == "  hello  world  "


def test_collapse_whitespace_only() -> None:
    opts = NormalizationOptions(lowercase=False, collapse_whitespace=True, strip=False)
    # Runs collapse to a single space, including the leading/trailing runs; case untouched.
    assert normalize("  HeLLo   World  ", opts) == " HeLLo World "


def test_strip_only() -> None:
    opts = NormalizationOptions(lowercase=False, collapse_whitespace=False, strip=True)
    # Ends trimmed; the interior double space and case are untouched.
    assert normalize("  HeLLo  World  ", opts) == "HeLLo  World"


# --- each flag independently OFF: all-off is the identity --------------------


def test_all_off_is_identity() -> None:
    messy = "  HeLLo\t\tWorld \n Foo  "
    assert normalize(messy, ALL_OFF) == messy


# --- all flags ON, combined --------------------------------------------------


def test_all_on_combined() -> None:
    assert normalize("  HeLLo   World  ", ALL_ON) == "hello world"


def test_all_on_order_lowercase_before_collapse_before_strip() -> None:
    # Tabs and newlines are whitespace; the fixed order lowercase -> collapse -> strip
    # turns this into clean, lower, single-spaced, trimmed text.
    assert normalize("\t Foo\nBAR\t Baz \n", ALL_ON) == "foo bar baz"


# --- idempotence: normalize(normalize(x)) == normalize(x) --------------------


def test_idempotence_all_on() -> None:
    messy = "  HeLLo \t World \n Again  "
    once = normalize(messy, ALL_ON)
    assert normalize(once, ALL_ON) == once


def test_idempotence_each_preset() -> None:
    messy = "  MiXeD\t\tCase \n Text  "
    presets = [
        ALL_OFF,
        ALL_ON,
        NormalizationOptions(lowercase=True, collapse_whitespace=False, strip=False),
        NormalizationOptions(lowercase=False, collapse_whitespace=True, strip=False),
        NormalizationOptions(lowercase=False, collapse_whitespace=False, strip=True),
    ]
    for opts in presets:
        once = normalize(messy, opts)
        assert normalize(once, opts) == once, opts


# --- empty and whitespace-only inputs ---------------------------------------


def test_empty_string() -> None:
    assert normalize("", ALL_ON) == ""
    assert normalize("", ALL_OFF) == ""


def test_whitespace_only_all_on_becomes_empty() -> None:
    # Collapse makes it a single space, then strip removes it: empty result.
    assert normalize("   \t\n  ", ALL_ON) == ""


def test_whitespace_only_collapse_only() -> None:
    # Without strip, the collapsed single space remains.
    opts = NormalizationOptions(lowercase=False, collapse_whitespace=True, strip=False)
    assert normalize("   \t\n  ", opts) == " "


def test_whitespace_only_strip_only_becomes_empty() -> None:
    opts = NormalizationOptions(lowercase=False, collapse_whitespace=False, strip=True)
    assert normalize("   \t\n  ", opts) == ""


# --- multiline with tabs and newlines collapsing -----------------------------


def test_multiline_tabs_newlines_collapse_to_single_spaces() -> None:
    opts = NormalizationOptions(lowercase=False, collapse_whitespace=True, strip=True)
    text = "Line one\n\tLine two\r\n  Line three"
    assert normalize(text, opts) == "Line one Line two Line three"


def test_defaults_are_all_on() -> None:
    # The dataclass defaults match ALL_ON, so the no-arg options behave the same.
    assert normalize("  HeLLo   World  ", NormalizationOptions()) == "hello world"

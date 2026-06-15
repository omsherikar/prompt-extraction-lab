"""Text normalization.

Match rates are sensitive to normalization, so every step is explicit, toggleable from
config, and tested. No silent normalization anywhere else in the codebase: all matching
goes through this module.

Phase 3: implement.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizationOptions:
    """Which normalization steps to apply, read from config.yaml."""

    lowercase: bool = True
    collapse_whitespace: bool = True
    strip: bool = True


def normalize(text: str, opts: NormalizationOptions) -> str:
    """Apply the enabled normalization steps, in a fixed, documented order."""
    # Phase 3: lowercase -> collapse internal whitespace runs to single spaces -> strip ends,
    # each gated by opts. Order matters and must be stable.
    raise NotImplementedError("Phase 3: implement normalize")

"""Text normalization.

Match rates are sensitive to normalization, so every step is explicit, toggleable from
config, and tested. No silent normalization anywhere else in the codebase: all matching
goes through this module.

Phase 3: implement.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizationOptions:
    """Which normalization steps to apply, read from config.yaml."""

    lowercase: bool = True
    collapse_whitespace: bool = True
    strip: bool = True


def normalize(text: str, opts: NormalizationOptions) -> str:
    """Apply the enabled normalization steps, in this fixed order.

    This is the single normalization chokepoint for the whole repo; there is no silent
    normalization anywhere else. Each step is gated by its flag in ``opts``, and the order
    is stable and load-bearing (collapse before strip lets a whitespace-only string reduce
    to a single space and then to empty):

    1. ``lowercase``: lowercase the text.
    2. ``collapse_whitespace``: collapse every run of whitespace to a single space.
    3. ``strip``: strip leading and trailing whitespace.
    """
    if opts.lowercase:
        text = text.lower()
    if opts.collapse_whitespace:
        text = re.sub(r"\s+", " ", text)
    if opts.strip:
        text = text.strip()
    return text

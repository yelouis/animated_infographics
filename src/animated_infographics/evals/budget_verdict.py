"""Performance budget verdict evaluation."""

from __future__ import annotations


def budget_verdict(spans: dict[str, float], bars: dict[str, float]) -> int:
    """Evaluate measured spans against bars.

    Returns 0 when every span in bars is <= its bar, and 3 otherwise.
    A span exactly at its bar passes.
    """
    for span_name, bar_val in bars.items():
        if span_name not in spans or spans[span_name] > bar_val:
            return 3
    return 0

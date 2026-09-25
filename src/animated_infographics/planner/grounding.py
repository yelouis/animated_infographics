"""Grounding and normalization helpers for planner verification."""

import re
import unicodedata


def norm(s: str) -> str:
    """Normalize text: casefold, straight quotes, strip non-alphanumeric/spaces, collapse spaces.

    Per design_planner.md §8:
    - casefold
    - curly quotes -> straight
    - replace every char that is not letter, digit, apostrophe or space with a space
    - collapse whitespace, strip
    """
    if not s:
        return ""

    # Unicode normalization to decompose special forms
    s = unicodedata.normalize("NFKD", s)

    # Curly quotes to straight
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    s = s.casefold()

    # Replace anything not a letter, digit, apostrophe, or whitespace with space
    s = re.sub(r"[^a-z0-9'\s]+", " ", s)

    # Collapse whitespace and strip
    return re.sub(r"\s+", " ", s).strip()


def is_verbatim_span(needle: str, haystack: str) -> bool:
    """Check if normalized needle is a word-boundary substring of normalized haystack."""
    norm_needle = norm(needle)
    norm_haystack = norm(haystack)

    if not norm_needle or not norm_haystack:
        return False

    pattern = r"(?:^|\s)" + re.escape(norm_needle) + r"(?:$|\s)"
    return bool(re.search(pattern, norm_haystack))

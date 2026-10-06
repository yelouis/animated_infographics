"""Word counting, free-text field extraction, and graphic words calculation."""

from collections.abc import Mapping
from typing import Any

from animated_infographics.contracts.templates import WORD_CAPS


def count_words(s: str | None) -> int:
    """Count tokens of s.split() that contain a character with .isalnum(); 0 for None."""
    if not s:
        return 0
    return sum(1 for token in s.split() if any(c.isalnum() for c in token))


def _extract_fields(current: Any, parts: list[str], prefix: str) -> list[tuple[str, str]]:
    if not parts:
        if isinstance(current, str):
            return [(prefix, current)]
        return []

    head = parts[0]
    tail = parts[1:]

    if head.endswith("[]"):
        key = head[:-2]
        container = (
            current.get(key) if isinstance(current, Mapping) else getattr(current, key, None)
        )
        if not isinstance(container, (list, tuple)):
            return []
        results: list[tuple[str, str]] = []
        for i, item in enumerate(container):
            sub_prefix = f"{prefix}.{key}[{i}]" if prefix else f"{key}[{i}]"
            results.extend(_extract_fields(item, tail, sub_prefix))
        return results
    else:
        val = current.get(head) if isinstance(current, Mapping) else getattr(current, head, None)
        if val is None:
            return []
        sub_prefix = f"{prefix}.{head}" if prefix else head
        return _extract_fields(val, tail, sub_prefix)


def field_values(props: Mapping[str, Any], path: str) -> list[tuple[str, str]]:
    """Return every (concrete_path, value) for a WORD_CAPS path, skipping None."""
    parts = path.split(".")
    return _extract_fields(props, parts, "")


def graphic_words(
    template: str,
    props: Mapping[str, Any],
    overlays: Any = None,
) -> int:
    """Sum of count_words over every WORD_CAPS[template] path plus overlay text words."""
    caps = WORD_CAPS.get(template)
    total = 0
    if caps:
        for path in caps:
            for _, val in field_values(props, path):
                total += count_words(val)
    if overlays:
        for ov in overlays:
            text = ov.get("text") if isinstance(ov, Mapping) else getattr(ov, "text", None)
            if text:
                total += count_words(text)
    return total

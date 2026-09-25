"""Contrast test per design_visual_direction.md §2."""

import re
from pathlib import Path


def rel_luminance(hex_str: str) -> float:
    """Compute WCAG 2.x relative luminance from 6-digit hex color."""
    clean_hex = hex_str.strip().lstrip("#")
    r, g, b = [int(clean_hex[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def linearize(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def contrast_ratio(hex1: str, hex2: str) -> float:
    """Compute WCAG 2.x contrast ratio between two hex colors."""
    l1 = rel_luminance(hex1)
    l2 = rel_luminance(hex2)
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


def parse_palette_ts() -> tuple[dict[str, str], list[str]]:
    """Parse tokens from renderer/src/theme/palette.ts."""
    repo_root = Path(__file__).resolve().parents[1]
    palette_file = repo_root / "renderer" / "src" / "theme" / "palette.ts"
    content = palette_file.read_text(encoding="utf-8")

    tokens: dict[str, str] = {}
    for match in re.finditer(r'(\w+):\s*"#([0-9a-fA-F]{6})"', content):
        tokens[match.group(1)] = f"#{match.group(2)}"

    cast_slots_match = re.search(r"castSlots:\s*\[(.*?)\]", content, re.DOTALL)
    if not cast_slots_match:
        raise ValueError("Could not find castSlots in palette.ts")

    cast_slots = [
        f"#{m.group(1)}" for m in re.finditer(r'"#([0-9a-fA-F]{6})"', cast_slots_match.group(1))
    ]
    return tokens, cast_slots


def test_contrast_floors() -> None:
    tokens, cast_slots = parse_palette_ts()

    bg = tokens["bg"]
    bg_raised = tokens["bgRaised"]
    ink = tokens["ink"]
    ink_muted = tokens["inkMuted"]
    highlight = tokens["highlight"]
    danger = tokens["danger"]

    # 1. Primary text on backgrounds (WCAG AA text floor is 4.5)
    assert contrast_ratio(ink, bg) >= 4.5
    assert round(contrast_ratio(ink, bg), 2) == 14.53

    assert contrast_ratio(ink, bg_raised) >= 4.5
    assert round(contrast_ratio(ink, bg_raised), 2) == 12.04

    # 2. Secondary text
    assert contrast_ratio(ink_muted, bg) >= 4.5
    assert round(contrast_ratio(ink_muted, bg), 2) == 8.85

    assert contrast_ratio(ink_muted, bg_raised) >= 4.5
    assert round(contrast_ratio(ink_muted, bg_raised), 2) == 7.33

    # 3. Highlight
    assert contrast_ratio(highlight, bg) >= 4.5
    assert round(contrast_ratio(highlight, bg), 2) == 11.08

    # 4. Danger
    assert contrast_ratio(danger, bg) >= 4.5
    assert round(contrast_ratio(danger, bg), 2) == 5.88

    assert contrast_ratio(danger, bg_raised) >= 4.5
    assert round(contrast_ratio(danger, bg_raised), 2) == 4.87

    # 5. Cast slots on bg as shapes (floor >= 3.0)
    assert len(cast_slots) == 8
    for slot_hex in cast_slots:
        ratio = contrast_ratio(slot_hex, bg)
        assert ratio >= 3.0, f"Cast slot {slot_hex} on bg has ratio {ratio} < 3.0"

    # 6. bg text on cast slots (required pairing, floor >= 4.5)
    for slot_hex in cast_slots:
        ratio = contrast_ratio(bg, slot_hex)
        assert ratio >= 4.5, f"bg on cast slot {slot_hex} has ratio {ratio} < 4.5"

    # 7. Forbidden pairing: ink text on cast slots must be < 4.5
    for slot_hex in cast_slots:
        ratio = contrast_ratio(ink, slot_hex)
        assert ratio < 4.5, (
            f"Forbidden ink-on-cast became legal! Slot {slot_hex} has ratio {ratio} >= 4.5"
        )
        assert 1.50 <= ratio <= 3.30

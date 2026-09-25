"""WCAG 2.x relative luminance and contrast ratio verification for palette.ts."""

import re
from pathlib import Path


def parse_palette_hexes(palette_path: Path) -> dict[str, str | list[str]]:
    """Parse hex codes directly from renderer/src/theme/palette.ts."""
    content = palette_path.read_text(encoding="utf-8")
    result: dict[str, str | list[str]] = {}

    # Extract single hex fields: bg: "#14213D",
    for match in re.finditer(r'([a-zA-Z0-9]+):\s*"#(?:[0-9a-fA-F]{6})"', content):
        key = match.group(1)
        # re-match full hex
        val_match = re.search(r'"(#[0-9a-fA-F]{6})"', match.group(0))
        if val_match:
            result[key] = val_match.group(1)

    # Extract castSlots array
    cast_match = re.search(r"castSlots:\s*\[([^\]]+)\]", content)
    if cast_match:
        slots = re.findall(r'"(#[0-9a-fA-F]{6})"', cast_match.group(1))
        result["castSlots"] = slots

    return result


def hex_to_relative_luminance(hex_str: str) -> float:
    """Calculate WCAG 2.x relative luminance from hex string."""
    h = hex_str.lstrip("#")
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0

    def srgb_to_linear(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r_lin = srgb_to_linear(r)
    g_lin = srgb_to_linear(g)
    b_lin = srgb_to_linear(b)

    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(hex1: str, hex2: str) -> float:
    """Calculate WCAG 2.x contrast ratio between two hex colours."""
    l1 = hex_to_relative_luminance(hex1)
    l2 = hex_to_relative_luminance(hex2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def test_palette_contrast_floors() -> None:
    """Verify WCAG contrast floors from design_visual_direction.md §2."""
    palette_file = Path(__file__).parent.parent / "renderer" / "src" / "theme" / "palette.ts"
    assert palette_file.exists(), f"palette.ts not found at {palette_file}"
    pal = parse_palette_hexes(palette_file)

    bg = str(pal["bg"])
    bg_raised = str(pal["bgRaised"])
    bg_deep = str(pal["bgDeep"])
    ink = str(pal["ink"])
    ink_muted = str(pal["inkMuted"])
    highlight = str(pal["highlight"])
    danger = str(pal["danger"])
    cast_slots = list(pal["castSlots"])

    # 1. Primary text >= 4.5
    assert contrast_ratio(ink, bg) >= 4.5, "ink on bg must be >= 4.5"
    assert contrast_ratio(ink, bg_raised) >= 4.5, "ink on bgRaised must be >= 4.5"
    assert contrast_ratio(ink_muted, bg) >= 4.5, "inkMuted on bg must be >= 4.5"
    assert contrast_ratio(ink_muted, bg_raised) >= 4.5, "inkMuted on bgRaised must be >= 4.5"
    assert contrast_ratio(highlight, bg) >= 4.5, "highlight on bg must be >= 4.5"
    assert contrast_ratio(danger, bg) >= 4.5, "danger on bg must be >= 4.5"
    assert contrast_ratio(danger, bg_raised) >= 4.5, "danger on bgRaised must be >= 4.5"

    # 2. Captions on bgDeep stroke >= 4.5
    assert contrast_ratio(ink, bg_deep) >= 4.5, "ink on bgDeep must be >= 4.5"
    assert contrast_ratio(highlight, bg_deep) >= 4.5, "highlight on bgDeep must be >= 4.5"

    # 3. Cast slots on bg (as shapes) >= 3.0
    for idx, slot_hex in enumerate(cast_slots):
        ratio = contrast_ratio(slot_hex, bg)
        assert ratio >= 3.0, f"castSlot {idx} ({slot_hex}) on bg ({ratio:.2f}) must be >= 3.0"

    # 4. Required pairing: bg text on cast slots >= 4.5
    for idx, slot_hex in enumerate(cast_slots):
        ratio = contrast_ratio(bg, slot_hex)
        assert ratio >= 4.5, f"bg on castSlot {idx} ({slot_hex}) ({ratio:.2f}) must be >= 4.5"

    # 5. Forbidden pairing: ink text on cast slots < 4.5
    for idx, slot_hex in enumerate(cast_slots):
        ratio = contrast_ratio(ink, slot_hex)
        assert ratio < 4.5, (
            f"ink on castSlot {idx} ({slot_hex}) ({ratio:.2f}) unexpectedly passed 4.5"
        )

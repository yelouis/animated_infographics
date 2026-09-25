"""Text fit validation using Pillow ImageFont and greedy word-wrap."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

from animated_infographics.contracts.templates import TextSlot


@dataclass(frozen=True)
class FitResult:
    """Result of text fit measurement."""

    fits: bool
    lines: int
    max_lines: int
    error: str | None = None


_FONTS_DIR = Path(__file__).resolve().parents[2] / "renderer" / "public" / "fonts"


def _font_filename(font: str, weight: int) -> str:
    if font == "display":
        if weight >= 800:
            return "Poppins-ExtraBold.ttf"
        return "Poppins-Bold.ttf"
    else:
        if weight >= 700:
            return "Inter-Bold.ttf"
        elif weight >= 600:
            return "Inter-SemiBold.ttf"
        return "Inter-Medium.ttf"


@lru_cache(maxsize=32)
def _load_font(font_name: str, weight: int, size: int) -> ImageFont.FreeTypeFont:
    filename = _font_filename(font_name, weight)
    font_path = _FONTS_DIR / filename
    if not font_path.exists():
        raise FileNotFoundError(f"Font file not found: {font_path}")
    return ImageFont.truetype(str(font_path), size=size)


def fits(text: str, slot: TextSlot) -> FitResult:
    """Measure if text fits within slot using Pillow ImageFont at size_min with 5% margin.

    Per design_planner.md §7:
    - Font: Pillow ImageFont.truetype(<exact TTF>, size_min)
    - Box width: box_width * 0.95
    - Greedy word-wrap
    - Fits iff wrapped line count <= max_lines
    - A single word wider than the box on its own does not fit
    """
    if not text or not text.strip():
        return FitResult(fits=True, lines=0, max_lines=slot.max_lines, error=None)

    font = _load_font(slot.font, slot.weight, slot.size_min)
    max_width = slot.box_width * 0.95

    words = text.split()
    if not words:
        return FitResult(fits=True, lines=0, max_lines=slot.max_lines, error=None)

    # Check if any single word exceeds max_width on its own
    for word in words:
        word_width = font.getlength(word)
        if word_width > max_width:
            err = (
                f"word '{word}' ({word_width:.1f}px) exceeds box width {max_width:.1f}px "
                f"at {slot.size_min}px"
            )
            return FitResult(fits=False, lines=1, max_lines=slot.max_lines, error=err)

    # Greedy word-wrap
    lines: list[str] = []
    current_line = words[0]
    for word in words[1:]:
        test_line = current_line + " " + word
        if font.getlength(test_line) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)

    line_count = len(lines)
    if line_count <= slot.max_lines:
        return FitResult(fits=True, lines=line_count, max_lines=slot.max_lines, error=None)

    err = f"does not fit ({line_count} lines at {slot.size_min}px, max {slot.max_lines})"
    return FitResult(fits=False, lines=line_count, max_lines=slot.max_lines, error=err)

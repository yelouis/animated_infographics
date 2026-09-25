"""Unit tests for Pillow text fit measurement."""

from animated_infographics.contracts.templates import TextSlot
from animated_infographics.textfit import fits


def test_fits_short_text() -> None:
    slot = TextSlot(
        font="display",
        weight=800,
        size_max=104,
        size_min=64,
        max_lines=3,
        box_width=900,
    )
    result = fits("Short Title", slot)
    assert result.fits
    assert result.lines <= slot.max_lines
    assert result.error is None


def test_overflow_max_lines_plus_one() -> None:
    slot = TextSlot(
        font="body",
        weight=600,
        size_max=44,
        size_min=32,
        max_lines=2,
        box_width=400,
    )
    # A text that wraps to 3 lines (max_lines + 1)
    text = (
        "This is a longer piece of text specifically written to exceed the two line "
        "maximum threshold and wrap onto three lines."
    )
    result = fits(text, slot)
    assert not result.fits
    assert result.lines > slot.max_lines
    assert "does not fit" in result.error
    assert "max 2" in result.error


def test_single_word_wider_than_box() -> None:
    slot = TextSlot(
        font="display",
        weight=800,
        size_max=104,
        size_min=64,
        max_lines=3,
        box_width=200,
    )
    # A single very long word that cannot fit even on one line
    result = fits("Supercalifragilisticexpialidocious", slot)
    assert not result.fits
    assert "exceeds box width" in result.error

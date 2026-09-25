"""Unit tests for timing/items.py staggered item frames and counter animation frames."""

from animated_infographics.timing.items import (
    count_frames,
    item_frames,
)


def test_item_frames_spread_and_stagger() -> None:
    """Verify item_frames calculation with spread and stagger clamping."""
    # When spread division exceeds STAGGER_FRAMES:
    # 120 * 0.5 / 3 = 20. max(4, 20) = 20 -> [0, 20, 40]
    frames = item_frames(n=3, scene_frames=120, spread=0.5)
    assert frames == [0, 20, 40]

    # When spread division is smaller than STAGGER_FRAMES (4):
    # 20 * 0.4 / 4 = 2. max(4, 2) = 4 -> [0, 4, 8, 12]
    frames_stagger = item_frames(n=4, scene_frames=20, spread=0.4)
    assert frames_stagger == [0, 4, 8, 12]


def test_item_frames_edge_cases() -> None:
    """Verify item_frames returns empty list for n=0 or non-positive frames."""
    assert item_frames(n=0, scene_frames=100, spread=0.5) == []
    assert item_frames(n=3, scene_frames=0, spread=0.5) == []
    assert item_frames(n=3, scene_frames=-10, spread=0.5) == []


def test_count_frames() -> None:
    """Verify count_frames formula: min(24, floor(0.4 * scene_frames))."""
    assert count_frames(100) == 24
    assert count_frames(30) == 12
    assert count_frames(0) == 0
    assert count_frames(-5) == 0

"""Item and counter animation frame math."""

import math

STAGGER_FRAMES: int = 4
MAX_COUNT_FRAMES: int = 24


def item_frames(n: int, scene_frames: int, spread: float) -> list[int]:
    """Compute staggered entrance frames relative to scene start.

    Formula: item_frames[i] = i * max(STAGGER_FRAMES, floor(scene_frames * spread / n))
    """
    if n <= 0 or scene_frames <= 0:
        return []

    step = max(STAGGER_FRAMES, math.floor(scene_frames * spread / n))
    return [i * step for i in range(n)]


def count_frames(scene_frames: int) -> int:
    """Compute count-up animation duration in frames for stat_callout.

    Formula: count_frames = min(24, floor(0.4 * scene_frames))
    """
    if scene_frames <= 0:
        return 0
    return max(0, min(MAX_COUNT_FRAMES, math.floor(0.4 * scene_frames)))

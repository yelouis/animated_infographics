"""Frame calculations and conversions: ms_to_frame, scene_start_frames, and duration_frames."""

import math
from collections.abc import Sequence

from animated_infographics.contracts.models import Beat, Transcript

FPS: int = 30
LEAD_MS: int = 200
END_HOLD_MS: int = 1500


def ms_to_frame(ms: int) -> int:
    """Convert milliseconds to frame count at 30 FPS using round-half-up.

    Never use Python's banker's round (which rounds halves to even integers).
    """
    return math.floor(ms * FPS / 1000.0 + 0.5)


def scene_start_frames(beats: Sequence[Beat]) -> list[int]:
    """Compute strictly increasing scene start frames with LEAD_MS anticipation.

    scene_start_frame[0] = 0
    for k >= 1: max(scene_start_frame[k-1] + 1, ms_to_frame(beat[k].start_ms - LEAD_MS))
    """
    if not beats:
        return []

    starts = [0]
    for k in range(1, len(beats)):
        lead_target = ms_to_frame(beats[k].start_ms - LEAD_MS)
        start_k = max(starts[k - 1] + 1, lead_target)
        starts.append(start_k)

    return starts


def duration_frames(transcript: Transcript) -> int:
    """Compute total video duration in frames.

    duration_frames = ms_to_frame(max(transcript.duration_ms, words[-1].end_ms + END_HOLD_MS))
    """
    last_word_hold = transcript.words[-1].end_ms + END_HOLD_MS if transcript.words else 0
    total_ms = max(transcript.duration_ms, last_word_hold)
    return ms_to_frame(total_ms)

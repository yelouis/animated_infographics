"""Timing core package: frames, beats, captions, items, and SFX scheduling."""

from animated_infographics.timing.beats import build_beats
from animated_infographics.timing.captions import paginate
from animated_infographics.timing.frames import (
    END_HOLD_MS,
    FPS,
    LEAD_MS,
    duration_frames,
    ms_to_frame,
    scene_start_frames,
)
from animated_infographics.timing.items import count_frames, item_frames
from animated_infographics.timing.sfx import SfxCue, SfxEvent, schedule_sfx

__all__ = [
    "END_HOLD_MS",
    "FPS",
    "LEAD_MS",
    "SfxCue",
    "SfxEvent",
    "build_beats",
    "count_frames",
    "duration_frames",
    "item_frames",
    "ms_to_frame",
    "paginate",
    "scene_start_frames",
    "schedule_sfx",
]

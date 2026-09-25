"""Sound effect scheduling and rate-limiting."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from animated_infographics.contracts.models import TimelineSfx

SFX_MIN_GAP_FRAMES: int = 24
SFX_VOLUME: float = 0.35


@dataclass(frozen=True)
class SfxCue:
    """A resolved SFX cue with an absolute frame position and optional scene attribution."""

    role: str
    frame: int
    scene_id: str = ""


@dataclass(frozen=True)
class SfxEvent:
    """A scheduled SFX playback event with mapped audio file and volume."""

    role: str
    frame: int
    src: str
    volume: float = SFX_VOLUME

    def to_timeline_sfx(self) -> TimelineSfx:
        """Convert to Pydantic TimelineSfx model."""
        return TimelineSfx(src=self.src, frame=self.frame, volume=self.volume)


def schedule_sfx(
    cues: Sequence[SfxCue],
    available: Mapping[str, int],
    muted: set[str],
) -> list[SfxEvent]:
    """Schedule SFX events respecting muted scenes, availability, and min gap.

    1. Drop cues in scenes with mute_sfx: true (scene_id in muted),
       and cues whose role has no files.
    2. Sort by frame; drop any cue within SFX_MIN_GAP_FRAMES (24 frames) of previous kept cue.
    3. File choice per role: round-robin over available files (n = k mod count).
    """
    valid_cues: list[SfxCue] = []
    for cue in cues:
        if cue.scene_id and cue.scene_id in muted:
            continue
        if available.get(cue.role, 0) <= 0:
            continue
        valid_cues.append(cue)

    sorted_cues = sorted(valid_cues, key=lambda c: c.frame)

    kept_cues: list[SfxCue] = []
    for cue in sorted_cues:
        if not kept_cues:
            kept_cues.append(cue)
        elif cue.frame - kept_cues[-1].frame >= SFX_MIN_GAP_FRAMES:
            kept_cues.append(cue)

    role_counters: dict[str, int] = {}
    events: list[SfxEvent] = []
    for cue in kept_cues:
        count = available[cue.role]
        k = role_counters.get(cue.role, 0)
        n = k % count
        role_counters[cue.role] = k + 1
        src = f"audio/sfx/{cue.role}_{n}.wav"
        events.append(SfxEvent(role=cue.role, frame=cue.frame, src=src, volume=SFX_VOLUME))

    return events

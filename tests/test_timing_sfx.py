"""Unit tests for timing/sfx.py SFX scheduling and rate-limiting."""

from animated_infographics.timing.sfx import (
    SFX_VOLUME,
    SfxCue,
    schedule_sfx,
)


def test_schedule_sfx_muted_and_missing_roles() -> None:
    """Verify cues in muted scenes and cues with no available audio files are dropped."""
    cues = [
        SfxCue(role="whoosh", frame=0, scene_id="s000"),
        SfxCue(role="pop", frame=30, scene_id="s001"),
        SfxCue(role="ding", frame=60, scene_id="s002"),
    ]
    available = {"whoosh": 2, "pop": 0}  # "ding" missing entirely, "pop" count is 0
    muted = {"s000"}  # s000 is muted

    events = schedule_sfx(cues, available, muted)
    # s000 dropped because muted; pop dropped because count 0; ding dropped because not in available
    assert events == []


def test_schedule_sfx_24_frame_min_gap() -> None:
    """Verify any cue within 24 frames of the previous kept cue is dropped."""
    cues = [
        SfxCue(role="whoosh", frame=0),
        SfxCue(role="whoosh", frame=15),  # 15 - 0 = 15 < 24 -> dropped
        SfxCue(role="whoosh", frame=24),  # 24 - 0 = 24 >= 24 -> kept
        SfxCue(role="whoosh", frame=40),  # 40 - 24 = 16 < 24 -> dropped
        SfxCue(role="whoosh", frame=48),  # 48 - 24 = 24 >= 24 -> kept
    ]
    available = {"whoosh": 2}
    muted: set[str] = set()

    events = schedule_sfx(cues, available, muted)
    assert len(events) == 3
    assert [e.frame for e in events] == [0, 24, 48]


def test_schedule_sfx_round_robin_per_role() -> None:
    """Verify file choice is round-robin per role."""
    cues = [
        SfxCue(role="whoosh", frame=0),
        SfxCue(role="pop", frame=30),
        SfxCue(role="whoosh", frame=60),
        SfxCue(role="pop", frame=90),
        SfxCue(role="whoosh", frame=120),
        SfxCue(role="pop", frame=150),
    ]
    available = {"whoosh": 2, "pop": 3}
    muted: set[str] = set()

    events = schedule_sfx(cues, available, muted)
    assert len(events) == 6

    whoosh_events = [e for e in events if e.role == "whoosh"]
    assert [e.src for e in whoosh_events] == [
        "audio/sfx/whoosh_0.wav",
        "audio/sfx/whoosh_1.wav",
        "audio/sfx/whoosh_0.wav",
    ]

    pop_events = [e for e in events if e.role == "pop"]
    assert [e.src for e in pop_events] == [
        "audio/sfx/pop_0.wav",
        "audio/sfx/pop_1.wav",
        "audio/sfx/pop_2.wav",
    ]

    assert all(e.volume == SFX_VOLUME for e in events)

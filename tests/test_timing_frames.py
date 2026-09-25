"""Unit tests for timing/frames.py math and scene start frames."""

from animated_infographics.contracts.models import (
    Beat,
    Transcript,
    TranscriptSentence,
    TranscriptWord,
)
from animated_infographics.timing.frames import (
    END_HOLD_MS,
    duration_frames,
    ms_to_frame,
    scene_start_frames,
)


def test_ms_to_frame_round_half_up() -> None:
    """Verify round-half-up behavior at 30 FPS."""
    assert ms_to_frame(550) == 17
    assert ms_to_frame(516) == 15
    assert ms_to_frame(0) == 0
    assert ms_to_frame(1000) == 30


def test_scene_start_frames_lead() -> None:
    """Verify beat at 5,000 ms gets scene start frame 144."""
    b0 = Beat(i=0, word_start=0, word_end=1, start_ms=0, end_ms=5000, text="First")
    b1 = Beat(i=1, word_start=1, word_end=2, start_ms=5000, end_ms=8000, text="Second")

    starts = scene_start_frames([b0, b1])
    assert starts[0] == 0
    assert starts[1] == 144  # (5000 - 200) * 30 / 1000 = 4800 * 0.03 = 144


def test_scene_start_frames_strictly_increasing() -> None:
    """Verify LEAD_MS never makes a start negative or non-increasing."""
    # Even if beats are very close together (e.g. 50 ms apart)
    beats = [
        Beat(i=0, word_start=0, word_end=1, start_ms=0, end_ms=50, text="A"),
        Beat(i=1, word_start=1, word_end=2, start_ms=50, end_ms=100, text="B"),
        Beat(i=2, word_start=2, word_end=3, start_ms=100, end_ms=150, text="C"),
    ]
    starts = scene_start_frames(beats)
    assert starts[0] == 0
    assert starts[1] > starts[0]
    assert starts[2] > starts[1]
    assert all(s >= 0 for s in starts)


def test_scenes_tile_duration() -> None:
    """Verify scenes tile [0, duration_frames) cleanly."""
    w1 = TranscriptWord(i=0, text="Hello", start_ms=0, end_ms=1000, sentence_i=0)
    w2 = TranscriptWord(i=1, text="world", start_ms=1000, end_ms=2000, sentence_i=0)
    s = TranscriptSentence(
        i=0, text="Hello world", start_ms=0, end_ms=2000, word_start=0, word_end=2, paragraph_i=0
    )
    transcript = Transcript(
        source="tts",
        audio_path="narration.wav",
        duration_ms=2500,
        words=[w1, w2],
        sentences=[s],
    )

    total_frames = duration_frames(transcript)
    expected_hold_ms = max(2500, 2000 + END_HOLD_MS)  # 3500 ms
    assert total_frames == ms_to_frame(expected_hold_ms)
    assert total_frames == 105  # 3500 * 30 / 1000 = 105

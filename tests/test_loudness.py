"""Unit tests for ffmpeg loudness measurement and normalization."""

from pathlib import Path

from animated_infographics.audio.loudness import measure_loudness


def test_measure_loudness_fixture() -> None:
    """Verify measure_loudness reads EBU R128 metrics from audio file."""
    audio_path = Path(__file__).parent.parent / "fixtures" / "audio" / "molasses_flood_say.m4a"
    report = measure_loudness(audio_path)
    assert isinstance(report.integrated_lufs, float)
    assert isinstance(report.true_peak_dbtp, float)
    assert isinstance(report.lra, float)
    # molasses_flood_say.m4a is around -16.5 LUFS
    assert -20.0 <= report.integrated_lufs <= -14.0

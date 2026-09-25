"""Unit tests for final rendering and verification."""

import subprocess
from pathlib import Path

import pytest

from animated_infographics.contracts.models import (
    Timeline,
    TimelineAudio,
    TimelineCaptions,
    TimelineNarration,
)
from animated_infographics.render import verify_render


def _create_synthetic_mp4(
    path: Path,
    *,
    duration: float = 1.0,
    fps: int = 30,
    blank: bool = False,
    loudness_filter: str = "loudnorm=I=-16:TP=-1.5",
) -> None:
    v_src = (
        f"color=c=black:duration={duration}:size=1080x1920:rate={fps}"
        if blank
        else f"testsrc=duration={duration}:size=1080x1920:rate={fps}"
    )
    a_src = f"anoisesrc=d={duration}:c=pink:r=48000,{loudness_filter}"
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        v_src,
        "-f",
        "lavfi",
        "-i",
        a_src,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(fps),
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        str(path),
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def test_verify_render_pass(tmp_path: Path) -> None:
    mp4_path = tmp_path / "final.mp4"
    _create_synthetic_mp4(mp4_path, duration=1.0, fps=30, blank=False)

    timeline = Timeline(
        duration_frames=30,
        plan_sha256="testsha",
        audio=TimelineAudio(narration=TimelineNarration(src="audio/narration.wav")),
        captions=TimelineCaptions(pages=[]),
        scenes=[],
    )

    res = verify_render(mp4_path, timeline)
    assert res["video_stream"] is True
    assert res["frame_count"] is True
    assert res["audio_stream"] is True
    assert res["av_duration"] is True
    assert res["loudness"] is True
    assert res["non_blank"] is True
    assert (tmp_path / "verify.json").is_file()


def test_verify_render_frame_count_mismatch(tmp_path: Path) -> None:
    mp4_path = tmp_path / "final.mp4"
    _create_synthetic_mp4(mp4_path, duration=1.0, fps=30, blank=False)

    timeline = Timeline(
        duration_frames=60,  # Video only has 30 frames
        plan_sha256="testsha",
        audio=TimelineAudio(narration=TimelineNarration(src="audio/narration.wav")),
        captions=TimelineCaptions(pages=[]),
        scenes=[],
    )

    with pytest.raises(RuntimeError, match="frame_count"):
        verify_render(mp4_path, timeline)


def test_verify_render_blank_rejection(tmp_path: Path) -> None:
    mp4_path = tmp_path / "final.mp4"
    _create_synthetic_mp4(mp4_path, duration=1.0, fps=30, blank=True)

    timeline = Timeline(
        duration_frames=30,
        plan_sha256="testsha",
        audio=TimelineAudio(narration=TimelineNarration(src="audio/narration.wav")),
        captions=TimelineCaptions(pages=[]),
        scenes=[],
    )

    with pytest.raises(RuntimeError, match="non_blank"):
        verify_render(mp4_path, timeline)

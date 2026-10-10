"""Final video rendering and verification per design_rendering.md §8."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from animated_infographics.contracts.models import Timeline
from animated_infographics.memguard import guard, watch


def render_video(
    job_dir: Path,
    out_path: Path | None = None,
    *,
    sync_probe: bool = False,
    scale: float = 1.0,
    crf: int = 18,
    timeline_path: Path | None = None,
) -> Path:
    """Invoke Remotion render.ts media to render final MP4 with production settings."""
    out_file = out_path or (job_dir / "out" / "final.mp4")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    repo_root = Path(__file__).resolve().parents[2]
    renderer_dir = repo_root / "renderer"
    render_script = renderer_dir / "scripts" / "render.ts"

    cmd = [
        "npx",
        "tsx",
        str(render_script),
        "media",
        "--job",
        str(job_dir),
        "--out",
        str(out_file),
        "--scale",
        str(scale),
        "--crf",
        str(crf),
    ]

    if sync_probe:
        cmd.append("--sync-probe")

    if timeline_path:
        cmd.extend(["--timeline", str(timeline_path)])

    with guard("render"):
        proc = subprocess.Popen(cmd, cwd=renderer_dir)
        with watch("render", proc):
            ret = proc.wait()
            if ret != 0:
                raise subprocess.CalledProcessError(ret, cmd)

    if not out_file.is_file():
        raise FileNotFoundError(f"Render completed but output file not found: {out_file}")

    return out_file


def render_gallery(out_dir: Path, templates: str) -> None:
    """Invoke Remotion render.ts gallery under guard('render') and watch."""
    repo_root = Path(__file__).resolve().parents[2]
    renderer_dir = repo_root / "renderer"
    render_script = renderer_dir / "scripts" / "render.ts"

    cmd = [
        "npx",
        "tsx",
        str(render_script),
        "gallery",
        "--out-dir",
        str(out_dir),
        "--template",
        templates,
    ]

    with guard("render"):
        proc = subprocess.Popen(cmd, cwd=renderer_dir)
        with watch("render", proc):
            ret = proc.wait()
            if ret != 0:
                raise subprocess.CalledProcessError(ret, cmd)


def verify_render(mp4_path: Path, timeline: Timeline) -> dict[str, Any]:
    """Verify rendered MP4 against all bars in design_rendering.md §8.

    Checks:
    1. Video stream: h264, yuv420p, 1080x1920, r_frame_rate 30/1
    2. Frame count: nb_read_frames == timeline.duration_frames
    3. Audio stream: aac, 48000 Hz
    4. A/V duration: |audio_duration - video_duration| <= 50 ms
    5. Loudness: integrated in [-18, -14] LUFS, true peak <= -0.5 dBTP
    6. Non-blank: luma std-dev > 2 at 5 evenly spaced frames

    Writes verify.json in the same directory as mp4_path.
    Raises RuntimeError if any check fails.
    """
    if not mp4_path.is_file():
        raise FileNotFoundError(f"Rendered video not found: {mp4_path}")

    # 1. ffprobe stream info (video and audio)
    probe_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "stream=index,codec_type,codec_name,pix_fmt,width,height,r_frame_rate,sample_rate,duration",
        "-of",
        "json",
        str(mp4_path),
    ]
    probe_proc = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    probe_data = json.loads(probe_proc.stdout)
    streams = probe_data.get("streams", [])

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if not video_stream:
        raise RuntimeError("No video stream found in rendered MP4")
    if not audio_stream:
        raise RuntimeError("No audio stream found in rendered MP4")

    v_codec = video_stream.get("codec_name")
    v_pix_fmt = video_stream.get("pix_fmt")
    v_width = video_stream.get("width")
    v_height = video_stream.get("height")
    v_fps = video_stream.get("r_frame_rate")

    check_video_stream = (
        v_codec == "h264"
        and v_pix_fmt in {"yuv420p", "yuvj420p"}
        and v_width == 1080
        and v_height == 1920
        and v_fps == "30/1"
    )

    # 2. Frame count
    count_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-count_frames",
        "-show_entries",
        "stream=nb_read_frames",
        "-of",
        "json",
        str(mp4_path),
    ]
    count_proc = subprocess.run(count_cmd, capture_output=True, text=True, check=True)
    count_data = json.loads(count_proc.stdout)
    read_frames_str = count_data.get("streams", [{}])[0].get("nb_read_frames", "0")
    actual_frames = int(read_frames_str)
    check_frame_count = actual_frames == timeline.duration_frames

    # 3. Audio stream
    a_codec = audio_stream.get("codec_name")
    a_sr = int(audio_stream.get("sample_rate", 0))
    check_audio_stream = a_codec == "aac" and a_sr == 48000

    # 4. A/V duration difference
    v_dur = float(video_stream.get("duration", 0.0))
    a_dur = float(audio_stream.get("duration", 0.0))
    diff_s = abs(a_dur - v_dur)
    check_av_duration = diff_s <= 0.050

    # 5. Loudness ebur128
    ebur_cmd = [
        "ffmpeg",
        "-nostats",
        "-i",
        str(mp4_path),
        "-af",
        "ebur128=peak=true",
        "-f",
        "null",
        "-",
    ]
    ebur_proc = subprocess.run(ebur_cmd, capture_output=True, text=True, check=True)
    i_match = re.search(r"Integrated loudness:\s*\n\s*I:\s*([-\d.]+)\s*LUFS", ebur_proc.stderr)
    peak_match = re.search(r"Peak:\s*([-\d.]+)\s*(?:dBFS|dBTP)", ebur_proc.stderr)

    integrated_lufs = float(i_match.group(1)) if i_match else -99.0
    true_peak_dbtp = float(peak_match.group(1)) if peak_match else 99.0

    check_loudness = (-18.0 <= integrated_lufs <= -14.0) and (true_peak_dbtp <= -0.5)

    # 6. Non-blank: luma std-dev at 5 evenly spaced frames
    non_blank_samples: list[dict[str, Any]] = []
    n_frames = timeline.duration_frames
    sample_frames = [round(n_frames * i / 6) for i in range(1, 6)]
    all_non_blank = True

    for sf in sample_frames:
        t_sec = sf / 30.0
        # Extract 1 frame raw grayscale
        raw_cmd = [
            "ffmpeg",
            "-nostats",
            "-ss",
            f"{t_sec:.3f}",
            "-i",
            str(mp4_path),
            "-vframes",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "gray",
            "-",
        ]
        raw_proc = subprocess.run(raw_cmd, capture_output=True, check=True)
        arr = np.frombuffer(raw_proc.stdout, dtype=np.uint8)
        std_val = float(np.std(arr)) if len(arr) > 0 else 0.0
        is_ok = std_val > 2.0
        if not is_ok:
            all_non_blank = False
        non_blank_samples.append({"frame": sf, "luma_std": round(std_val, 2), "non_blank": is_ok})

    verify_report: dict[str, Any] = {
        "video_stream": check_video_stream,
        "frame_count": check_frame_count,
        "audio_stream": check_audio_stream,
        "av_duration": check_av_duration,
        "loudness": check_loudness,
        "non_blank": all_non_blank,
        "details": {
            "codec": v_codec,
            "pix_fmt": v_pix_fmt,
            "width": v_width,
            "height": v_height,
            "fps": v_fps,
            "frame_count": actual_frames,
            "expected_frame_count": timeline.duration_frames,
            "audio_codec": a_codec,
            "sample_rate": a_sr,
            "video_duration_s": round(v_dur, 4),
            "audio_duration_s": round(a_dur, 4),
            "av_diff_ms": round(diff_s * 1000, 2),
            "integrated_lufs": integrated_lufs,
            "true_peak_dbtp": true_peak_dbtp,
            "non_blank_samples": non_blank_samples,
        },
    }

    verify_path = mp4_path.parent / "verify.json"
    verify_path.write_text(json.dumps(verify_report, indent=2) + "\n", encoding="utf-8")

    failed_checks = [k for k, v in verify_report.items() if k != "details" and not v]
    if failed_checks:
        raise RuntimeError(
            f"Verification failed on {', '.join(failed_checks)}: {verify_report['details']}"
        )

    return verify_report

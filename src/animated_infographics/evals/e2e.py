"""E2E evaluation harness and sync probe checker.

Per design_rendering.md §8 and design_testing_and_validation.md §4.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

from animated_infographics.contracts.models import Timeline


def extract_pixel_luma(mp4_path: Path, frame: int, x: int = 24, y: int = 24) -> float:
    """Extract grayscale luma for a specific pixel at a specific frame using ffmpeg."""
    cmd = [
        "ffmpeg",
        "-nostats",
        "-i",
        str(mp4_path),
        "-vf",
        f"select=eq(n\\,{frame}),format=gray,crop=1:1:{x}:{y}",
        "-vframes",
        "1",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "gray",
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, check=True)
    arr = np.frombuffer(proc.stdout, dtype=np.uint8)
    if len(arr) == 0:
        raise RuntimeError(f"Failed to extract pixel at frame {frame} from {mp4_path}")
    return float(arr[0])


def check_sync_probe(
    mp4_path: Path,
    timeline: Timeline,
    skip_boundary: int | None = None,
) -> tuple[bool, int, list[str]]:
    """Check that sync probe pixel (24, 24) flips at every scene boundary k >= 1.

    Even scene index: black (#000000, luma < 40)
    Odd scene index: white (#FFFFFF, luma > 215)
    """
    errors: list[str] = []
    checked_count = 0

    scenes = timeline.scenes
    for k in range(1, len(scenes)):
        if skip_boundary is not None and k == skip_boundary:
            continue

        prev_sc = scenes[k - 1]
        curr_sc = scenes[k]

        start_f = curr_sc.start_frame
        f_before = start_f - 1
        f_after = start_f + 1

        luma_before = extract_pixel_luma(mp4_path, f_before, 24, 24)
        luma_after = extract_pixel_luma(mp4_path, f_after, 24, 24)

        prev_is_even = (k - 1) % 2 == 0
        curr_is_even = k % 2 == 0

        # Before start_f should match prev scene
        if prev_is_even and luma_before >= 40:
            errors.append(
                f"Scene {k} boundary frame {f_before}: expected black (<40) for "
                f"scene {prev_sc.id}, got luma={luma_before}"
            )
        elif not prev_is_even and luma_before <= 215:
            errors.append(
                f"Scene {k} boundary frame {f_before}: expected white (>215) for "
                f"scene {prev_sc.id}, got luma={luma_before}"
            )

        # After start_f should match curr scene
        if curr_is_even and luma_after >= 40:
            errors.append(
                f"Scene {k} boundary frame {f_after}: expected black (<40) for "
                f"scene {curr_sc.id}, got luma={luma_after}"
            )
        elif not curr_is_even and luma_after <= 215:
            errors.append(
                f"Scene {k} boundary frame {f_after}: expected white (>215) for "
                f"scene {curr_sc.id}, got luma={luma_after}"
            )

        checked_count += 1

    return len(errors) == 0, checked_count, errors


def get_media_duration(mp4_path: Path) -> float:
    """Return media duration in seconds via ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(mp4_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(proc.stdout.strip())


def measure_audio_rms(
    mp4_path: Path,
    start_s: float | None = None,
    end_s: float | None = None,
) -> tuple[float, float, float, float]:
    """Measure RMS audio level in dBFS between start_s and end_s using ffmpeg atrim + astats.

    Returns (duration, start_s, end_s, rms_dbfs).
    Defaults to [duration - 1.4 s, duration - 1.0 s] per design_testing_and_validation.md §4.
    """
    duration = get_media_duration(mp4_path)
    if start_s is None:
        start_s = max(0.0, duration - 1.4)
    if end_s is None:
        end_s = max(start_s, duration - 1.0)

    cmd = [
        "ffmpeg",
        "-nostats",
        "-vn",
        "-i",
        str(mp4_path),
        "-af",
        f"atrim=start={start_s}:end={end_s},astats=measure_overall=all:measure_perchannel=none",
        "-f",
        "null",
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    rms_dbfs: float | None = None
    for line in proc.stderr.splitlines():
        if "RMS level dB:" in line:
            val_str = line.split("RMS level dB:")[1].strip()
            if val_str == "-inf":
                rms_dbfs = float("-inf")
            else:
                rms_dbfs = float(val_str)
            break

    if rms_dbfs is None:
        raise RuntimeError(
            f"Could not extract RMS level dB from ffmpeg astats output:\n{proc.stderr}"
        )

    return duration, start_s, end_s, rms_dbfs


def compute_file_sha256(path: Path) -> str:
    """Compute sha256 of file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def generate_e2e_report(
    date_str: str,
    steps_results: list[dict[str, Any]],
    output_path: Path,
) -> None:
    """Write docs/evals/e2e_<date>.md report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        f"# End-to-End Evaluation Report — {date_str}",
        "",
        "## Summary",
        "",
        "| Step | Name | Exit Code | Status |",
        "|---|---|---|---|",
    ]

    for s in steps_results:
        code_str = str(s.get("exit_code", 0))
        status = "PASS" if s.get("passed", True) else "FAIL"
        lines.append(f"| {s.get('step', '-')} | {s.get('name', '-')} | `{code_str}` | {status} |")

    lines.extend(
        [
            "",
            "## Output Verification & Details",
            "",
        ]
    )

    for s in steps_results:
        lines.append(f"### Step {s.get('step')}: {s.get('name')}")
        lines.append("")
        if "details" in s:
            lines.append("```json")
            lines.append(json.dumps(s["details"], indent=2))
            lines.append("```")
            lines.append("")
        if "notes" in s:
            lines.append(s["notes"])
            lines.append("")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="E2E test utilities")
    subparsers = parser.add_subparsers(dest="command")

    # check-sync
    sync_p = subparsers.add_parser("check-sync")
    sync_p.add_argument("--mp4", type=Path, required=True)
    sync_p.add_argument("--timeline", type=Path, required=True)
    sync_p.add_argument(
        "--skip-boundary",
        type=int,
        default=None,
        help="Skip checking boundary at specific scene index (falsification)",
    )

    # measure-audio-rms
    rms_p = subparsers.add_parser("measure-audio-rms")
    rms_p.add_argument("--mp4", type=Path, required=True)
    rms_p.add_argument("--start", type=float, default=None)
    rms_p.add_argument("--end", type=float, default=None)
    rms_p.add_argument("--min-rms", type=float, default=None)

    args = parser.parse_args()
    if args.command == "check-sync":
        timeline = Timeline.model_validate_json(args.timeline.read_text(encoding="utf-8"))
        ok, count, errors = check_sync_probe(args.mp4, timeline, skip_boundary=args.skip_boundary)
        expected = len(timeline.scenes) - 1
        result = {
            "checked": count,
            "expected": expected,
            "failures": errors,
        }
        print(json.dumps(result))
        if count != expected or not ok:
            sys.exit(1)
        sys.exit(0)
    elif args.command == "measure-audio-rms":
        duration, start_s, end_s, rms_dbfs = measure_audio_rms(
            args.mp4, start_s=args.start, end_s=args.end
        )
        res = {
            "duration": round(duration, 4),
            "start_s": round(start_s, 4),
            "end_s": round(end_s, 4),
            "rms_dbfs": round(rms_dbfs, 2) if rms_dbfs != float("-inf") else "-inf",
        }
        print(json.dumps(res))
        if args.min_rms is not None:
            if rms_dbfs <= args.min_rms:
                sys.exit(1)
        sys.exit(0)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Audio loudness measurement and two-pass normalization via ffmpeg."""

import json
import re
import subprocess
from pathlib import Path

from animated_infographics.contracts.models import LoudnessReport


def measure_loudness(path: Path) -> LoudnessReport:
    """Measure EBU R128 integrated loudness, true peak, and LRA using ffmpeg ebur128."""
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-filter_complex",
        "ebur128=peak=true",
        "-f",
        "null",
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    stderr = proc.stderr
    summary_section = stderr.split("Summary:")[-1] if "Summary:" in stderr else stderr

    m_i = re.search(r"I:\s+([-\d.]+)\s+LUFS", summary_section)
    m_tp = re.search(r"Peak:\s+([-\d.]+)\s+dBFS", summary_section)
    m_lra = re.search(r"LRA:\s+([-\d.]+)\s+LU", summary_section)

    if not m_i or not m_tp or not m_lra:
        msg = f"Failed to parse ebur128 loudness metrics from ffmpeg output:\n{stderr}"
        raise RuntimeError(msg)

    return LoudnessReport(
        integrated_lufs=round(float(m_i.group(1)), 2),
        true_peak_dbtp=round(float(m_tp.group(1)), 2),
        lra=round(float(m_lra.group(1)), 2),
    )


def loudnorm_two_pass(
    src: Path,
    dst: Path,
    *,
    target_lufs: float,
    true_peak: float,
    lra: float,
    sample_rate: int,
    channels: int,
) -> LoudnessReport:
    """Perform two-pass loudnorm normalization with resampling and channel configuration."""
    # Pass 1: Measure audio characteristics with loudnorm
    cmd_pass1 = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-y",
        "-i",
        str(src),
        "-af",
        f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}:print_format=json",
        "-f",
        "null",
        "-",
    ]
    proc1 = subprocess.run(cmd_pass1, capture_output=True, text=True, check=True)

    json_match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", proc1.stderr)
    if not json_match:
        raise RuntimeError(f"loudnorm pass 1 failed to output JSON statistics:\n{proc1.stderr}")

    stats = json.loads(json_match.group(0))
    input_i = stats["input_i"]
    input_tp = stats["input_tp"]
    input_lra = stats["input_lra"]
    input_thresh = stats["input_thresh"]
    target_offset = stats["target_offset"]

    # Pass 2: Apply linear normalization with measured parameters
    filter_desc = (
        f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}:"
        f"measured_I={input_i}:measured_TP={input_tp}:"
        f"measured_LRA={input_lra}:measured_thresh={input_thresh}:"
        f"offset={target_offset}:linear=true"
    )

    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd_pass2 = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-y",
        "-i",
        str(src),
        "-af",
        filter_desc,
        "-ar",
        str(sample_rate),
        "-ac",
        str(channels),
        "-c:a",
        "pcm_s16le",
        str(dst),
    ]
    subprocess.run(cmd_pass2, capture_output=True, text=True, check=True)

    return measure_loudness(dst)

"""Audio preparation for mixing: music normalization and SFX role parsing and peak normalization."""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path
from typing import Final

from animated_infographics.audio.loudness import loudnorm_two_pass

logger = logging.getLogger(__name__)

KNOWN_SFX_ROLES: Final[frozenset[str]] = frozenset({"whoosh", "pop", "ding", "hit"})


def parse_sfx_role(filename: str) -> str | None:
    """Parse SFX role from filename prefix before first '_', '-', digit or '.'.

    Per design_audio_and_timing.md §5:
    Roles: whoosh, pop, ding, hit (casefolded). Other prefixes return None.
    """
    stem = Path(filename).name
    # Split on first occurrence of _, -, digit, or .
    m = re.match(r"^([A-Za-z]+)", stem)
    if not m:
        return None
    candidate = m.group(1).lower()
    return candidate if candidate in KNOWN_SFX_ROLES else None


def normalize_sfx_peak(src: Path, dst: Path, target_peak_db: float = -3.0) -> Path:
    """Peak-normalise SFX to target_peak_db (default -3 dBFS) and convert to 48 kHz stereo s16."""
    dst.parent.mkdir(parents=True, exist_ok=True)

    # Pass 1: detect volume
    cmd_detect = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        str(src),
        "-af",
        "volumedetect",
        "-f",
        "null",
        "-",
    ]
    proc = subprocess.run(cmd_detect, capture_output=True, text=True, check=True)
    m = re.search(r"max_volume:\s+([-\d.]+)\s+dB", proc.stderr)
    if not m:
        raise RuntimeError(f"Failed to detect max_volume for {src}:\n{proc.stderr}")

    max_vol = float(m.group(1))
    adjustment = target_peak_db - max_vol

    # Pass 2: apply adjustment, resample to 48kHz stereo s16
    cmd_apply = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-y",
        "-i",
        str(src),
        "-af",
        f"volume={adjustment:.2f}dB",
        "-ar",
        "48000",
        "-ac",
        "2",
        "-c:a",
        "pcm_s16le",
        str(dst),
    ]
    subprocess.run(cmd_apply, capture_output=True, text=True, check=True)
    return dst


def prepare_music(src: Path, dst: Path) -> Path:
    """Two-pass loudnorm to -16 LUFS, true peak -1.5 dBTP, 48 kHz stereo s16 -> audio/music.wav."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    loudnorm_two_pass(
        src,
        dst,
        target_lufs=-16.0,
        true_peak=-1.5,
        lra=11.0,
        sample_rate=48000,
        channels=2,
    )
    return dst


def prepare_sfx(sfx_dir: Path, out_dir: Path) -> dict[str, list[Path]]:
    """Scan sfx_dir, group by role, peak-normalize to -3 dBFS into audio/sfx/<role>_<n>.wav.

    Unknown roles are ignored with a warning naming the file.
    Returns mapping from role to list of normalized file paths.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted([f for f in sfx_dir.iterdir() if f.is_file() and not f.name.startswith(".")])

    role_files: dict[str, list[Path]] = {r: [] for r in sorted(KNOWN_SFX_ROLES)}

    for f in files:
        role = parse_sfx_role(f.name)
        if role is None:
            logger.warning("Ignoring unknown SFX file %s (role not recognized)", f.name)
            continue
        role_files[role].append(f)

    result: dict[str, list[Path]] = {}
    for role, file_list in role_files.items():
        if not file_list:
            continue
        normalized_list: list[Path] = []
        for idx, src_f in enumerate(file_list):
            dst_f = out_dir / f"{role}_{idx}.wav"
            normalize_sfx_peak(src_f, dst_f)
            normalized_list.append(dst_f)
        result[role] = normalized_list

    return result

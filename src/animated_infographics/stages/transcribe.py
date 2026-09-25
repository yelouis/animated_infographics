"""Transcribe stage runner for Animated Infographics pipeline."""

from pathlib import Path

from animated_infographics.audio.transcribe import transcribe
from animated_infographics.errors import ValidationFailed
from animated_infographics.jobs import Job, RunContext


def run_transcribe_stage(job: Job, ctx: RunContext) -> None:
    """Execute ASR transcription stage on audio inputs in job/input/."""
    input_dir = job.dir / "input"
    if not input_dir.is_dir():
        raise ValidationFailed(f"input directory missing in {job.dir}")

    music_name = ctx.music_path.name if ctx.music_path else None
    valid_suffixes = {".wav", ".m4a", ".mp3"}

    candidates: list[Path] = [
        f
        for f in input_dir.iterdir()
        if f.is_file() and f.suffix.lower() in valid_suffixes and f.name != music_name
    ]

    if not candidates:
        raise ValidationFailed(f"No audio input file (.wav, .m4a, .mp3) found in {input_dir}")

    input_audio = candidates[0]
    transcript = transcribe(input_audio, job.dir)

    out_file = job.dir / "transcript.json"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(transcript.model_dump_json(indent=2) + "\n")

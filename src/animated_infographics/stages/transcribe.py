"""Transcribe stage runner for Animated Infographics pipeline."""

from pathlib import Path

from animated_infographics.audio.transcribe import transcribe
from animated_infographics.contracts.models import IngestRecord
from animated_infographics.errors import ValidationFailed
from animated_infographics.jobs import Job, RunContext


def run_transcribe_stage(job: Job, ctx: RunContext) -> None:
    """Execute ASR transcription stage on audio inputs in job/input/."""
    input_dir = job.dir / "input"
    if not input_dir.is_dir():
        raise ValidationFailed(f"input directory missing in {job.dir}")

    ingest_file = job.dir / "ingest.json"
    ingest = (
        IngestRecord.model_validate_json(ingest_file.read_text(encoding="utf-8"))
        if ingest_file.is_file()
        else None
    )

    if ingest and ingest.kind == "audio":
        input_audio = job.dir / ingest.source
    else:
        music_name = Path(ingest.music).name if (ingest and ingest.music) else None
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

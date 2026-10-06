"""Ingest stage runner for Animated Infographics pipeline."""

from pathlib import Path

from animated_infographics.errors import ValidationFailed
from animated_infographics.ingest import ingest
from animated_infographics.jobs import Job, RunContext


def run_ingest_stage(job: Job, ctx: RunContext) -> None:
    """Execute ingest stage on the primary input file in job/input/."""
    input_dir = job.dir / "input"
    if not input_dir.is_dir():
        raise ValidationFailed(f"input directory missing in {job.dir}")

    # Exclude music file if copied into input
    music_name = ctx.music_path.name if ctx.music_path else None
    valid_suffixes = {".txt", ".wav", ".m4a", ".mp3"}

    candidates: list[Path] = [
        f
        for f in input_dir.iterdir()
        if f.is_file() and f.suffix.lower() in valid_suffixes and f.name != music_name
    ]

    if not candidates:
        raise ValidationFailed(f"No valid input file (.txt, .wav, .m4a, .mp3) found in {input_dir}")

    # If both text and audio are present, prefer text for text pipeline
    text_candidates = [f for f in candidates if f.suffix.lower() == ".txt"]
    primary_input = text_candidates[0] if text_candidates else candidates[0]

    music_rel = f"input/{ctx.music_path.name}" if ctx.music_path else None
    sfx_rel = "input/sfx" if ctx.sfx_dir else None

    record = ingest(
        primary_input,
        title_override=ctx.title,
        music=music_rel,
        sfx_dir=sfx_rel,
        style=ctx.style,  # type: ignore[arg-type]
    )

    out_file = job.dir / "ingest.json"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(record.model_dump_json(indent=2) + "\n")

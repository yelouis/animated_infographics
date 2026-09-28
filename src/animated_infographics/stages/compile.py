"""Compile stage: compiles storyboard and media assets into timeline.json."""

from __future__ import annotations

import time
from pathlib import Path

from animated_infographics.audio.mix_prep import prepare_music, prepare_sfx
from animated_infographics.compile import compile_timeline
from animated_infographics.contracts.models import (
    Beats,
    Bible,
    IngestRecord,
    Storyboard,
    Transcript,
)
from animated_infographics.errors import ValidationFailed
from animated_infographics.jobs import Job, RunContext


def run_compile_stage(job: Job, ctx: RunContext) -> None:
    """Compile storyboard, beats, bible, and media into timeline.json."""
    t0 = time.perf_counter()

    transcript_path = job.dir / "transcript.json"
    beats_path = job.dir / "beats.json"
    bible_path = job.dir / "bible.json"
    sb_path = job.dir / "storyboard.json"
    ingest_path = job.dir / "ingest.json"

    transcript = Transcript.model_validate_json(transcript_path.read_text(encoding="utf-8"))
    beats = Beats.model_validate_json(beats_path.read_text(encoding="utf-8")).beats
    bible = Bible.model_validate_json(bible_path.read_text(encoding="utf-8"))
    storyboard = Storyboard.model_validate_json(sb_path.read_text(encoding="utf-8"))
    ingest = (
        IngestRecord.model_validate_json(ingest_path.read_text(encoding="utf-8"))
        if ingest_path.is_file()
        else None
    )

    # Music preparation
    music_rel_path: str | None = None
    music_dst = job.dir / "audio" / "music.wav"
    if ingest and ingest.music:
        music_src = job.dir / ingest.music
        if not music_src.is_file():
            raise ValidationFailed(
                f"{ingest.music} is recorded in ingest.json but missing from the job"
            )
        prepare_music(music_src, music_dst)
        music_rel_path = "job/audio/music.wav"

    # SFX preparation
    sfx_files_by_role: dict[str, list[Path]] = {}
    sfx_dst_dir = job.dir / "audio" / "sfx"
    if ingest and ingest.sfx_dir:
        sfx_src = job.dir / ingest.sfx_dir
        if not sfx_src.is_dir():
            raise ValidationFailed(
                f"{ingest.sfx_dir} is recorded in ingest.json but missing from the job"
            )
        sfx_files_by_role = prepare_sfx(sfx_src, sfx_dst_dir)

    plan_sha = job.plan_sha256()

    available_images: set[str] = set()
    images_dir = job.dir / "assets" / "images"
    if images_dir.is_dir():
        for f in images_dir.iterdir():
            if f.is_file() and f.suffix.lower() == ".png":
                available_images.add(f.stem)

    timeline = compile_timeline(
        transcript,
        beats,
        bible,
        storyboard,
        plan_sha256=plan_sha,
        music_rel_path=music_rel_path,
        sfx_files_by_role=sfx_files_by_role,
        sync_probe=ctx.sync_probe,
        available_images=available_images,
    )

    timeline_path = job.dir / "timeline.json"
    timeline_path.write_text(
        timeline.model_dump_json(indent=2, by_alias=True) + "\n", encoding="utf-8"
    )

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    log_file = job.dir / "logs" / "compile.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text(f"llm_calls=0 cache_hits=0 elapsed_ms={elapsed_ms}\n", encoding="utf-8")

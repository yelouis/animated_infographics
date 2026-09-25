"""Segment stage wrapper for Animated Infographics pipeline."""

from __future__ import annotations

import time

from animated_infographics.contracts.models import Transcript
from animated_infographics.jobs import Job, RunContext
from animated_infographics.planner.llm import OllamaBackend
from animated_infographics.planner.segment import plan_beats


def run_segment_stage(job: Job, ctx: RunContext) -> None:
    """Execute narration segmentation stage on job inputs."""
    t0 = time.perf_counter()

    transcript_path = job.dir / "transcript.json"
    if not transcript_path.is_file():
        raise FileNotFoundError(f"transcript.json missing in job {job.job_id}")

    transcript = Transcript.model_validate_json(transcript_path.read_text(encoding="utf-8"))

    backend = OllamaBackend(no_cache=ctx.no_llm_cache)
    beats = plan_beats(transcript, backend)

    beats_path = job.dir / "beats.json"
    with open(beats_path, "w", encoding="utf-8") as f:
        f.write(beats.model_dump_json(indent=2) + "\n")

    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    log_file = job.dir / "logs" / "segment.log"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"Beats: {len(beats.beats)} beats generated\n")
        for b in beats.beats:
            dur = b.end_ms - b.start_ms
            f.write(
                f"  Beat {b.i}: [{b.start_ms}..{b.end_ms}] ms ({dur}ms), "
                f"words [{b.word_start}..{b.word_end}]: '{b.text[:50]}...'\n"
            )
        f.write(
            f"llm_calls={backend.calls} cache_hits={backend.cache_hits} elapsed_ms={elapsed_ms}\n"
        )

"""Render pipeline stage."""

from __future__ import annotations

import time

from animated_infographics.contracts.models import Timeline
from animated_infographics.jobs import Job, RunContext
from animated_infographics.render import render_video, verify_render


def run_render_stage(job: Job, ctx: RunContext) -> None:
    """Render final MP4 and execute verification checks."""
    t0 = time.perf_counter()

    timeline_path = job.dir / "timeline.json"
    if not timeline_path.is_file():
        raise FileNotFoundError(f"timeline.json not found in job {job.job_id}")

    timeline = Timeline.model_validate_json(timeline_path.read_text(encoding="utf-8"))

    out_mp4 = job.dir / "out" / "final.mp4"
    render_video(job.dir, out_mp4, sync_probe=ctx.sync_probe)

    verify_render(out_mp4, timeline)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    logs_dir = job.dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    render_log = logs_dir / "render.log"
    existing_memguard = ""
    if render_log.is_file():
        existing_memguard = "".join(
            line
            for line in render_log.read_text(encoding="utf-8").splitlines(keepends=True)
            if line.startswith("memguard ")
        )
    render_log.write_text(
        existing_memguard + f"llm_calls=0 cache_hits=0 elapsed_ms={elapsed_ms}\n",
        encoding="utf-8",
    )

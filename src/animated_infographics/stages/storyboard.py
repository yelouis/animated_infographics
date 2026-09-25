"""Storyboard stage wrapper for Animated Infographics pipeline."""

from __future__ import annotations

import time

from animated_infographics.contracts.models import Beats, Bible, Transcript
from animated_infographics.jobs import Job, RunContext
from animated_infographics.planner.llm import OllamaBackend
from animated_infographics.planner.props import plan_storyboard


def run_storyboard_stage(job: Job, ctx: RunContext) -> None:
    """Execute storyboard planning stage on job inputs."""
    t0 = time.perf_counter()

    transcript_path = job.dir / "transcript.json"
    if not transcript_path.is_file():
        raise FileNotFoundError(f"transcript.json missing in job {job.job_id}")

    beats_path = job.dir / "beats.json"
    if not beats_path.is_file():
        raise FileNotFoundError(f"beats.json missing in job {job.job_id}")

    bible_path = job.dir / "bible.json"
    if not bible_path.is_file():
        raise FileNotFoundError(f"bible.json missing in job {job.job_id}")

    transcript = Transcript.model_validate_json(transcript_path.read_text(encoding="utf-8"))
    beats = Beats.model_validate_json(beats_path.read_text(encoding="utf-8"))
    bible = Bible.model_validate_json(bible_path.read_text(encoding="utf-8"))

    backend = OllamaBackend(no_cache=ctx.no_llm_cache)
    storyboard, plan_report = plan_storyboard(transcript, beats.beats, bible, backend)

    storyboard_path = job.dir / "storyboard.json"
    with open(storyboard_path, "w", encoding="utf-8") as f:
        f.write(storyboard.model_dump_json(indent=2, by_alias=True) + "\n")

    plan_report_path = job.dir / "plan_report.json"
    with open(plan_report_path, "w", encoding="utf-8") as f:
        f.write(plan_report.model_dump_json(indent=2, by_alias=True) + "\n")

    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    log_file = job.dir / "logs" / "storyboard.log"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"Storyboard: {len(storyboard.scenes)} scenes planned\n")
        for sc in storyboard.scenes:
            f.write(f"  Scene {sc.id} (beat {sc.beat_i}): template={sc.template}\n")
        f.write(f"Rule repairs: {len(plan_report.rule_repairs)}\n")
        for r in plan_report.rule_repairs:
            f.write(f"  {r.rule} on {r.scene}: {r.from_} -> {r.to}\n")
        f.write(
            f"llm_calls={backend.calls} cache_hits={backend.cache_hits} elapsed_ms={elapsed_ms}\n"
        )

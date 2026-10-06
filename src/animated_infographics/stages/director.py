"""Director stage runner for Animated Infographics pipeline.

Per design_styles.md §3.3.
"""

from __future__ import annotations

import json
import time

from animated_infographics.contracts.models import Beats, Bible
from animated_infographics.jobs import Job, RunContext
from animated_infographics.planner.director import plan_director
from animated_infographics.planner.license import run_license_checks
from animated_infographics.planner.llm import OllamaBackend


def run_director_stage(job: Job, ctx: RunContext) -> None:
    """Execute director stage.

    For literal: recorded as skipped and writes nothing.
    For creative: plans motifs, metaphors, and asides across the whole story,
    checks them against the license stage, and saves director.json.
    """
    t0 = time.perf_counter()

    ingest_path = job.dir / "ingest.json"
    style = ctx.style
    if ingest_path.is_file():
        try:
            data = json.loads(ingest_path.read_text(encoding="utf-8"))
            style = data.get("style", style)
        except Exception:
            pass

    log_file = job.dir / "logs" / "director.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    if style == "literal":
        # Literal mode skips director and writes nothing
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        log_file.write_text(
            f"Director: skipped for literal style\n"
            f"llm_calls=0 cache_hits=0 elapsed_ms={elapsed_ms}\n",
            encoding="utf-8",
        )
        return

    # Creative style:
    beats_path = job.dir / "beats.json"
    bible_path = job.dir / "bible.json"
    if not beats_path.is_file():
        raise FileNotFoundError(f"beats.json missing in job {job.job_id}")
    if not bible_path.is_file():
        raise FileNotFoundError(f"bible.json missing in job {job.job_id}")

    beats = Beats.model_validate_json(beats_path.read_text(encoding="utf-8"))
    bible = Bible.model_validate_json(bible_path.read_text(encoding="utf-8"))

    backend = OllamaBackend(no_cache=ctx.no_llm_cache)
    calls_start = backend.calls
    hits_start = backend.cache_hits

    plan, attempts = plan_director(beats.beats, bible, backend)

    degraded_marker = job.dir / ".director_degraded"
    director_json_path = job.dir / "director.json"

    if plan is None:
        # All 3 attempts failed -> degrade to literal
        degraded_marker.touch()
        if director_json_path.is_file():
            director_json_path.unlink()

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        llm_calls = backend.calls - calls_start
        cache_hits = backend.cache_hits - hits_start
        log_file.write_text(
            f"Director: failed after {len(attempts)} attempts; degraded to literal\n"
            f"llm_calls={llm_calls} cache_hits={cache_hits} elapsed_ms={elapsed_ms}\n",
            encoding="utf-8",
        )
        return

    # Successful director plan: clean degraded marker and run license checks
    if degraded_marker.is_file():
        degraded_marker.unlink()

    checked_plan, dropped = run_license_checks(plan, beats.beats, backend)

    with open(director_json_path, "w", encoding="utf-8") as f:
        f.write(checked_plan.model_dump_json(indent=2) + "\n")

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    llm_calls = backend.calls - calls_start
    cache_hits = backend.cache_hits - hits_start
    log_file.write_text(
        f"Director: planned {len(checked_plan.motifs)} motifs, "
        f"{len(checked_plan.metaphors)} metaphors, {len(checked_plan.asides)} asides "
        f"({len(dropped)} license dropped)\n"
        f"llm_calls={llm_calls} cache_hits={cache_hits} elapsed_ms={elapsed_ms}\n",
        encoding="utf-8",
    )

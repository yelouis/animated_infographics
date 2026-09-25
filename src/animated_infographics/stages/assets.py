"""Assets stage: illustration generation for places and set pieces."""

from __future__ import annotations

import time

from animated_infographics.assets.illustrate import run_assets
from animated_infographics.contracts.models import Bible
from animated_infographics.jobs import Job, RunContext


def run_assets_stage(job: Job, ctx: RunContext) -> None:
    """Run assets stage, generating illustrations for places and set pieces."""
    t0 = time.perf_counter()

    bible_path = job.dir / "bible.json"
    if not bible_path.is_file():
        raise FileNotFoundError(f"Missing bible.json in {job.dir}")
    bible = Bible.model_validate_json(bible_path.read_text(encoding="utf-8"))

    manifest = run_assets(bible, job)

    cache_hits = sum(1 for e in manifest.entities if e.status == "cached")
    generated = sum(1 for e in manifest.entities if e.status == "generated")
    failed = sum(1 for e in manifest.entities if e.status == "failed")
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    log_file = job.dir / "logs" / "assets.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text(
        f"llm_calls=0 cache_hits={cache_hits} generated={generated} "
        f"failed={failed} elapsed_ms={elapsed_ms}\n",
        encoding="utf-8",
    )

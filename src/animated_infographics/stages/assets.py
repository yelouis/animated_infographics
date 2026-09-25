"""Assets stage: interim manifest generation for local asset resolution."""

from __future__ import annotations

import json
import time

from animated_infographics.jobs import Job, RunContext


def run_assets_stage(job: Job, ctx: RunContext) -> None:
    """Interim assets stage writing manifest.json with every image null."""
    t0 = time.perf_counter()

    assets_dir = job.dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    images_dir = assets_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = assets_dir / "manifest.json"
    manifest_data = {
        "schema_version": 1,
        "entities": [],
    }
    manifest_path.write_text(json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8")

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    log_file = job.dir / "logs" / "assets.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text(f"llm_calls=0 cache_hits=0 elapsed_ms={elapsed_ms}\n", encoding="utf-8")

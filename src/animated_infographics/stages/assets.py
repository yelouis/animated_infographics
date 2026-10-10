"""Assets stage: illustration generation for places and set pieces."""

from __future__ import annotations

import time

from animated_infographics.assets.illustrate import run_assets
from animated_infographics.contracts.models import Bible
from animated_infographics.jobs import Job, RunContext
from animated_infographics.planner.llm import OllamaBackend


def run_assets_stage(job: Job, ctx: RunContext) -> None:
    """Run assets stage, generating illustrations for places and set pieces."""
    t0 = time.perf_counter()

    bible_path = (
        job.dir / "deck_bible.json" if job.kind == "presentation" else job.dir / "bible.json"
    )
    if not bible_path.is_file():
        raise FileNotFoundError(f"Missing {bible_path.name} in {job.dir}")
    bible = Bible.model_validate_json(bible_path.read_text(encoding="utf-8"))

    backend = OllamaBackend(no_cache=ctx.no_llm_cache)
    manifest = run_assets(bible, job, backend=backend)

    cache_hits = sum(1 for e in manifest.entities if e.status == "cached")
    generated = sum(1 for e in manifest.entities if e.status == "generated")
    failed = sum(1 for e in manifest.entities if e.status == "failed")
    text_checks = sum(len(e.attempts) for e in manifest.entities)
    regenerations = sum(max(0, len(e.attempts) - 1) for e in manifest.entities)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    failed_lines: list[str] = []
    execution_errors_count = 0
    for e in manifest.entities:
        if e.status == "failed":
            err_str = e.error or ""
            first_line = err_str.splitlines()[0] if err_str else "unknown error"
            failed_lines.append(f"asset {e.id} failed: {first_line}\n")
            if not err_str.startswith("lettering detected"):
                execution_errors_count += 1

    summary_line = (
        f"llm_calls={backend.calls} cache_hits={cache_hits} generated={generated} "
        f"failed={failed} execution_errors={execution_errors_count} elapsed_ms={elapsed_ms} "
        f"text_checks={text_checks} regenerations={regenerations}\n"
    )

    log_file = job.dir / "logs" / "assets.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    existing_memguard = ""
    if log_file.is_file():
        existing_memguard = "".join(
            line
            for line in log_file.read_text(encoding="utf-8").splitlines(keepends=True)
            if line.startswith("memguard ")
        )
    log_file.write_text(existing_memguard + "".join(failed_lines) + summary_line, encoding="utf-8")

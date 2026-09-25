"""Voice stage wrapper for Animated Infographics pipeline."""

import json

from animated_infographics.jobs import Job, RunContext
from animated_infographics.planner.llm import OllamaBackend
from animated_infographics.planner.voice import select_voice


def run_voice_stage(job: Job, ctx: RunContext) -> None:
    """Execute voice selection stage on job inputs."""
    import time

    t0 = time.perf_counter()
    ingest_file = job.dir / "ingest.json"
    if not ingest_file.is_file():
        raise FileNotFoundError(f"ingest.json missing in job {job.job_id}")

    with open(ingest_file, encoding="utf-8") as f:
        ingest_data = json.load(f)

    title = ctx.title or ingest_data.get("title")
    paragraphs = ingest_data.get("paragraphs")
    if paragraphs is not None:
        body = "\n\n".join(paragraphs)
    else:
        body = ingest_data.get("body", ingest_data.get("text", ""))

    backend = OllamaBackend(no_cache=ctx.no_llm_cache)
    decision = select_voice(title, body, flag_voice=ctx.voice, backend=backend)

    voice_path = job.dir / "voice.json"
    with open(voice_path, "w", encoding="utf-8") as f:
        f.write(decision.model_dump_json(indent=2) + "\n")

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    log_file = job.dir / "logs" / "voice.log"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(
            f"Voice: {decision.voice}, source={decision.source}, reason={decision.reason}, "
            f"gender={decision.narrator_gender}\n"
        )
        if decision.evidence:
            f.write(f"Evidence: {decision.evidence}\n")
        f.write(
            f"llm_calls={backend.calls} cache_hits={backend.cache_hits} elapsed_ms={elapsed_ms}\n"
        )

"""Presentation hear stage: transcribes live simulated audio via MLX-Whisper.

Produces heard.json matching the Transcript contract with source: "asr".
Per design_presentation_simulation.md §5 and design_data_contracts.md §10.
"""

from __future__ import annotations

import time

from animated_infographics.audio.transcribe import transcribe
from animated_infographics.jobs import Job, RunContext


def run_hear_stage(job: Job, ctx: RunContext) -> None:
    """Execute hear stage transcribing audio/narration.wav into heard.json."""
    t0 = time.perf_counter()

    audio_path = job.dir / "audio" / "narration.wav"
    if not audio_path.is_file():
        raise FileNotFoundError(f"audio/narration.wav missing in job {job.job_id}")

    heard_transcript = transcribe(audio_path, job.dir)

    heard_path = job.dir / "heard.json"
    heard_path.write_text(heard_transcript.model_dump_json(indent=2) + "\n", encoding="utf-8")

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    log_file = job.dir / "logs" / "hear.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    existing_log = ""
    if log_file.is_file():
        existing_log = log_file.read_text(encoding="utf-8")
    with open(log_file, "w", encoding="utf-8") as f:
        if existing_log:
            f.write(existing_log)
        f.write(
            f"Hear: words={len(heard_transcript.words)}, "
            f"sentences={len(heard_transcript.sentences)}, "
            f"duration_ms={heard_transcript.duration_ms}, "
            f"llm_calls=0 cache_hits=0 elapsed_ms={elapsed_ms}\n"
        )

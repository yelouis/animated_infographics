"""Presentation speak stage: synthesizes narration from performance.json via Kokoro.

Produces audio/narration.wav and speak_timing.json with exact millisecond sentence offsets.
Per design_presentation_simulation.md §5 and design_data_contracts.md §10.
"""

from __future__ import annotations

import json
import time

from animated_infographics.audio.narrate import synthesize_narration
from animated_infographics.contracts.models import VoiceDecision
from animated_infographics.contracts.performance import PerformancePlan, SpeakTimingItem
from animated_infographics.jobs import Job, RunContext


def run_speak_stage(job: Job, ctx: RunContext) -> None:
    """Execute speak stage synthesizing audio from performance.json."""
    t0 = time.perf_counter()

    perf_path = job.dir / "performance.json"
    voice_path = job.dir / "voice.json"

    if not perf_path.is_file():
        raise FileNotFoundError(f"performance.json missing in job {job.job_id}")
    if not voice_path.is_file():
        raise FileNotFoundError(f"voice.json missing in job {job.job_id}")

    performance = PerformancePlan.model_validate_json(perf_path.read_text(encoding="utf-8"))
    voice = VoiceDecision.model_validate_json(voice_path.read_text(encoding="utf-8"))

    audio_dir = job.dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    raw_wav_path = audio_dir / "narration_raw.wav"
    final_wav_path = audio_dir / "narration.wav"

    sentence_specs = [(sent.text, idx, False) for idx, sent in enumerate(performance.sentences)]

    _, narration_offsets = synthesize_narration(
        sentence_specs=sentence_specs,
        voice=voice,
        raw_wav_path=raw_wav_path,
        final_wav_path=final_wav_path,
    )

    speak_timing_items = [
        SpeakTimingItem(sentence_i=off.i, start_ms=off.start_ms, end_ms=off.end_ms).model_dump()
        for off in narration_offsets.sentences
    ]

    timing_path = job.dir / "speak_timing.json"
    timing_path.write_text(json.dumps(speak_timing_items, indent=2) + "\n", encoding="utf-8")

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    log_file = job.dir / "logs" / "speak.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    existing_log = ""
    if log_file.is_file():
        existing_log = log_file.read_text(encoding="utf-8")
    with open(log_file, "w", encoding="utf-8") as f:
        if existing_log:
            f.write(existing_log)
        f.write(
            f"Speak: sentences={len(sentence_specs)}, voice={voice.voice}, "
            f"llm_calls=0 cache_hits=0 elapsed_ms={elapsed_ms}\n"
        )

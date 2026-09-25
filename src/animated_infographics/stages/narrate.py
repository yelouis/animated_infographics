"""Narrate stage runner for Animated Infographics pipeline."""

from animated_infographics.audio.narrate import narrate
from animated_infographics.contracts.models import IngestRecord, VoiceDecision
from animated_infographics.errors import ValidationFailed
from animated_infographics.jobs import Job, RunContext


def run_narrate_stage(job: Job, ctx: RunContext) -> None:
    """Execute narration stage with Kokoro synthesis."""
    ingest_path = job.dir / "ingest.json"
    if not ingest_path.is_file():
        raise ValidationFailed(f"ingest.json missing in job {job.job_id}")

    voice_path = job.dir / "voice.json"
    if not voice_path.is_file():
        raise ValidationFailed(f"voice.json missing in job {job.job_id}")

    ingest_record = IngestRecord.model_validate_json(ingest_path.read_text(encoding="utf-8"))
    voice_decision = VoiceDecision.model_validate_json(voice_path.read_text(encoding="utf-8"))

    transcript, narration_offsets = narrate(ingest_record, voice_decision, job.dir)

    transcript_path = job.dir / "transcript.json"
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcript.model_dump_json(indent=2) + "\n")

    narration_path = job.dir / "narration.json"
    with open(narration_path, "w", encoding="utf-8") as f:
        f.write(narration_offsets.model_dump_json(indent=2) + "\n")

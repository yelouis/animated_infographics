"""Bible stage wrapper for Animated Infographics pipeline."""

from __future__ import annotations

import time
from pathlib import Path

from animated_infographics.contracts.models import Transcript, VoiceDecision
from animated_infographics.jobs import Job, RunContext
from animated_infographics.planner.bible import plan_bible
from animated_infographics.planner.geo import Gazetteer, load_country_bboxes
from animated_infographics.planner.llm import OllamaBackend


def run_bible_stage(job: Job, ctx: RunContext) -> None:
    """Execute bible planning stage on job inputs."""
    t0 = time.perf_counter()

    transcript_path = job.dir / "transcript.json"
    if not transcript_path.is_file():
        raise FileNotFoundError(f"transcript.json missing in job {job.job_id}")

    transcript = Transcript.model_validate_json(transcript_path.read_text(encoding="utf-8"))

    voice_path = job.dir / "voice.json"
    voice: VoiceDecision | None = None
    if voice_path.is_file():
        voice = VoiceDecision.model_validate_json(voice_path.read_text(encoding="utf-8"))

    repo_root = Path(__file__).parent.parent.parent.parent
    cities_path = repo_root / "data" / "vendor" / "cities15000.txt"
    country_info_path = repo_root / "data" / "vendor" / "countryInfo.txt"
    bboxes_path = repo_root / "data" / "geo" / "country_bboxes.json"

    gazetteer = Gazetteer.load(cities_path, country_info_path)
    bboxes = load_country_bboxes(bboxes_path)

    backend = OllamaBackend(no_cache=ctx.no_llm_cache)
    bible = plan_bible(transcript, voice, backend, gazetteer, bboxes)

    bible_path = job.dir / "bible.json"
    with open(bible_path, "w", encoding="utf-8") as f:
        f.write(bible.model_dump_json(indent=2) + "\n")

    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    log_file = job.dir / "logs" / "bible.log"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(
            f"Bible: title='{bible.title}', genre={bible.genre}, "
            f"cast={len(bible.cast)}, places={len(bible.places)}, "
            f"set_pieces={len(bible.set_pieces)}\n"
        )
        for c in bible.cast:
            f.write(
                f"  Cast: id={c.id}, name='{c.name}', role='{c.role}', "
                f"is_narrator={c.is_narrator}, color_slot={c.color_slot}\n"
            )
        for p in bible.places:
            f.write(
                f"  Place: id={p.id}, name='{p.name}', kind={p.kind}, "
                f"country_iso3={p.country_iso3}, geo_source={p.geo_source}\n"
            )
        for sp in bible.set_pieces:
            f.write(f"  SetPiece: id={sp.id}, name='{sp.name}'\n")
        f.write(
            f"llm_calls={backend.calls} cache_hits={backend.cache_hits} elapsed_ms={elapsed_ms}\n"
        )

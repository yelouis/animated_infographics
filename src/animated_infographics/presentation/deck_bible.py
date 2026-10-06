"""Deck bible stage: generate world bible from deck text only.

Per design_presentation_simulation.md §3 and design_data_contracts.md §10.
"""

from __future__ import annotations

import time
from pathlib import Path

from animated_infographics.contracts.deck import DeckPlan
from animated_infographics.contracts.models import (
    Transcript,
    TranscriptSentence,
    TranscriptWord,
    VoiceDecision,
)
from animated_infographics.jobs import Job, RunContext
from animated_infographics.planner.bible import plan_bible
from animated_infographics.planner.geo import Gazetteer, load_country_bboxes
from animated_infographics.planner.llm import OllamaBackend


def build_deck_transcript(deck: DeckPlan) -> Transcript:
    """Build synthetic Transcript from slide titles and points joined as paragraphs.

    Strictly offline; does not read original script or audio.
    """
    words: list[TranscriptWord] = []
    sentences: list[TranscriptSentence] = []
    cur_ms = 0
    word_counter = 0
    sent_counter = 0

    for p_idx, slide in enumerate(deck.slides):
        slide_sentences = [slide.title, *(pt.text for pt in slide.points)]
        for s_in_slide, text in enumerate(slide_sentences):
            raw_tokens = text.split()
            if not raw_tokens:
                raw_tokens = [text]

            sent_start_ms = cur_ms
            sent_word_start = word_counter

            for tok in raw_tokens:
                w_start = cur_ms
                w_end = cur_ms + 250
                cur_ms += 300
                words.append(
                    TranscriptWord(
                        i=word_counter,
                        text=tok,
                        start_ms=w_start,
                        end_ms=w_end,
                        sentence_i=sent_counter,
                    )
                )
                word_counter += 1

            sent_end_ms = cur_ms
            sent_word_end = word_counter
            is_title = p_idx == 0 and s_in_slide == 0

            sentences.append(
                TranscriptSentence(
                    i=sent_counter,
                    text=text,
                    start_ms=sent_start_ms,
                    end_ms=sent_end_ms,
                    word_start=sent_word_start,
                    word_end=sent_word_end,
                    paragraph_i=p_idx,
                    is_title=is_title,
                )
            )
            sent_counter += 1

    return Transcript(
        schema_version=1,
        source="tts",
        audio_path="presentation_deck.wav",
        duration_ms=cur_ms,
        words=words,
        sentences=sentences,
    )


def run_deck_bible_stage(job: Job, ctx: RunContext) -> None:
    """Execute bible planning stage over deck text only, writing deck_bible.json."""
    t0 = time.perf_counter()

    deck_path = job.dir / "deck.json"
    if not deck_path.is_file():
        raise FileNotFoundError(f"deck.json missing in job {job.job_id}")

    deck = DeckPlan.model_validate_json(deck_path.read_text(encoding="utf-8"))
    transcript = build_deck_transcript(deck)

    voice_path = job.dir / "voice.json"
    voice: VoiceDecision | None = None
    if voice_path.is_file():
        voice = VoiceDecision.model_validate_json(voice_path.read_text(encoding="utf-8"))

    repo_root = Path(__file__).resolve().parents[3]
    cities_path = repo_root / "data" / "vendor" / "cities15000.txt"
    country_info_path = repo_root / "data" / "vendor" / "countryInfo.txt"
    bboxes_path = repo_root / "data" / "geo" / "country_bboxes.json"

    gazetteer = Gazetteer.load(cities_path, country_info_path)
    bboxes = load_country_bboxes(bboxes_path)

    backend = OllamaBackend(no_cache=ctx.no_llm_cache)
    bible = plan_bible(transcript, voice, backend, gazetteer, bboxes)

    deck_bible_path = job.dir / "deck_bible.json"
    with open(deck_bible_path, "w", encoding="utf-8") as f:
        f.write(bible.model_dump_json(indent=2) + "\n")

    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    log_file = job.dir / "logs" / "deck_bible.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(
            f"DeckBible: title='{bible.title}', genre={bible.genre}, "
            f"cast={len(bible.cast)}, places={len(bible.places)}, "
            f"set_pieces={len(bible.set_pieces)}, elapsed_ms={elapsed_ms}\n"
        )

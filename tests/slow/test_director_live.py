"""Live slow integration tests for creative director and license stages with gemma4:26b.

Per design_styles.md §3.3, §3.4, and agent_execution_guide.md G3.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from animated_infographics.audio.narrate import build_sentence_list
from animated_infographics.contracts.models import (
    Beat,
    Bible,
    Transcript,
    TranscriptSentence,
    TranscriptWord,
)
from animated_infographics.ingest import ingest
from animated_infographics.planner.director import plan_director
from animated_infographics.planner.license import run_license_checks
from animated_infographics.planner.llm import OllamaBackend
from animated_infographics.planner.segment import plan_beats

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "fixtures"

ALL_FIXTURES = [
    "molasses_flood",
    "emu_war",
    "story_recipe_box",
    "story_room_12",
    "story_overdue_book",
    "history_great_stink",
]


def _make_transcript_from_script(script_path: Path) -> Transcript:
    ing = ingest(script_path, None)
    sents = build_sentence_list(ing)
    words: list[TranscriptWord] = []
    transcript_sents: list[TranscriptSentence] = []
    ms = 0
    w_idx = 0

    for i, (text, p_idx, is_t) in enumerate(sents):
        toks = text.split()
        w_start = ms
        s_w_start = w_idx
        for t in toks:
            words.append(
                TranscriptWord(
                    i=w_idx,
                    sentence_i=i,
                    text=t,
                    start_ms=ms,
                    end_ms=ms + 250,
                )
            )
            w_idx += 1
            ms += 300
        transcript_sents.append(
            TranscriptSentence(
                i=i,
                text=text,
                start_ms=w_start,
                end_ms=ms,
                word_start=s_w_start,
                word_end=w_idx,
                paragraph_i=p_idx,
                is_title=is_t,
            )
        )
        ms += 250

    return Transcript(
        schema_version=1,
        source="tts",
        audio_path="simulated.wav",
        duration_ms=ms + 500,
        words=words,
        sentences=transcript_sents,
    )


def get_fixture_inputs(fixture_name: str) -> tuple[list[Beat], Bible]:
    script_path = FIXTURES_DIR / "scripts" / f"{fixture_name}.txt"
    bible_path = REPO_ROOT / "artifacts" / "evals" / "planner" / fixture_name / "bible.json"
    if not bible_path.is_file():
        raise FileNotFoundError(f"Bible artifact missing for {fixture_name}")
    bible = Bible.model_validate_json(bible_path.read_text(encoding="utf-8"))

    transcript = _make_transcript_from_script(script_path)
    # Use cached backend for segmentation beats to match evaluator baseline
    cached_backend = OllamaBackend(no_cache=False)
    beats_obj = plan_beats(transcript, cached_backend)
    return beats_obj.beats, bible


@pytest.mark.slow
@pytest.mark.parametrize("fixture_name", ALL_FIXTURES)
def test_director_live_fixture(fixture_name: str) -> None:
    """Run director cold on fixture, then license check. Enforces G3 bars."""
    beats, bible = get_fixture_inputs(fixture_name)
    cold_backend = OllamaBackend(no_cache=True)

    # 1. Director Stage (cold)
    plan, attempts = plan_director(beats, bible, cold_backend)
    assert plan is not None, f"Director failed all attempts on {fixture_name}"
    assert len(attempts) <= 3, f"Director used {len(attempts)} attempts on {fixture_name} (max 3)"

    # Bar 2: ≥ 1 motif with a plant and a payoff on long and personal stories
    if fixture_name in (
        "story_overdue_book",
        "history_great_stink",
        "story_recipe_box",
        "story_room_12",
    ):
        valid_motifs = [
            m
            for m in plan.motifs
            if any(a.role == "plant" for a in m.appearances)
            and any(a.role == "payoff" for a in m.appearances)
        ]
        assert len(valid_motifs) >= 1, (
            f"{fixture_name} requires ≥ 1 motif with both plant and payoff, "
            f"found {len(valid_motifs)}"
        )

    # 2. License Check Stage (cold)
    checked_plan, dropped = run_license_checks(plan, beats, cold_backend)

    # Save live result for reporting
    out_dir = REPO_ROOT / "artifacts" / "evals" / "director_live" / fixture_name
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "director.json").write_text(checked_plan.model_dump_json(indent=2), encoding="utf-8")
    (out_dir / "raw_plan.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    summary = {
        "fixture": fixture_name,
        "attempts": len(attempts),
        "motifs_count": len(checked_plan.motifs),
        "metaphors_kept": len(checked_plan.metaphors),
        "asides_kept": len(checked_plan.asides),
        "license_dropped_count": len(checked_plan.license_dropped),
        "license_dropped": [d.model_dump() for d in checked_plan.license_dropped],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

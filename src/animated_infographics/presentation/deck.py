"""Deck stage: Generates presentation slides and talking points from script sentences.

Per design_presentation_simulation.md §2 and design_data_contracts.md §10.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from animated_infographics.audio.narrate import build_sentence_list
from animated_infographics.contracts.deck import DeckPlan
from animated_infographics.contracts.models import IngestRecord
from animated_infographics.errors import ValidationFailed
from animated_infographics.jobs import Job, RunContext
from animated_infographics.planner.grounding import digits_grounded
from animated_infographics.planner.llm import (
    LLMBackend,
    OllamaBackend,
    llm_facing_schema,
    run_with_retries,
)
from animated_infographics.planner.validate import (
    PLACEHOLDER_WORDS,
    text_complete_errors,
)
from animated_infographics.planner.words import count_words

QUOTATION_MARKS = frozenset({'"', "'", "“", "”", "‘", "’"})


def compute_target_slides(word_count: int) -> int:
    """Slide count: round(words / 100), clamped to 4–10."""
    target = round(word_count / 100)
    return max(4, min(10, target))


def build_deck_schema() -> dict[str, Any]:
    """Build JSON schema for structured LLM deck generation."""
    point_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "sentence_ids": {
                "type": "array",
                "items": {"type": "integer"},
            },
        },
        "required": ["text", "sentence_ids"],
        "additionalProperties": False,
    }

    slide_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "title": {"type": "string"},
            "points": {
                "type": "array",
                "items": point_schema,
            },
            "sentence_ids": {
                "type": "array",
                "items": {"type": "integer"},
            },
        },
        "required": ["id", "title", "points", "sentence_ids"],
        "additionalProperties": False,
    }

    return {
        "type": "object",
        "properties": {
            "slides": {
                "type": "array",
                "items": slide_schema,
            },
        },
        "required": ["slides"],
        "additionalProperties": False,
    }


def load_deck_prompt_template() -> str:
    """Load prompts/deck.md."""
    prompt_path = Path(__file__).resolve().parent / "prompts" / "deck.md"
    if not prompt_path.is_file():
        # Fallback to planner/prompts if needed
        alt = Path(__file__).resolve().parents[1] / "planner" / "prompts" / "deck.md"
        if alt.is_file():
            return alt.read_text(encoding="utf-8")
        raise FileNotFoundError(f"deck.md prompt template not found at {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def format_deck_prompt(
    sentences: list[tuple[str, int, bool]],
    word_count: int,
    target_slides: int,
) -> str:
    """Format prompt with numbered sentences and target parameters."""
    template = load_deck_prompt_template()

    num_body = len(sentences) - 1 if len(sentences) > 0 and sentences[0][2] else len(sentences)
    max_sentence_id = num_body

    lines: list[str] = []
    for idx, (sent_text, _, is_title) in enumerate(sentences):
        if is_title:
            lines.append(f"Sentence {idx} (Title): {sent_text}")
        else:
            lines.append(f"Sentence {idx}: {sent_text}")

    sentences_text = "\n".join(lines)

    return template.format(
        target_slides=target_slides,
        max_sentence_id=max_sentence_id,
        sentences_text=sentences_text,
    )


def validate_deck(
    raw: dict[str, Any],
    sentences: list[tuple[str, int, bool]],
    word_count: int,
) -> tuple[dict[str, Any], list[str]]:
    """Validate a deck plan per design_presentation_simulation.md §2 rules 1–6.

    Returns (repaired_dict, errors).
    """
    errors: list[str] = []
    slides = raw.get("slides")
    if not isinstance(slides, list):
        return raw, ["Output missing 'slides' array"]

    target_slides = compute_target_slides(word_count)

    # 1. Slide count
    if len(slides) != target_slides:
        errors.append(
            f"Expected {target_slides} slides (round({word_count}/100) clamped to 4-10), "
            f"got {len(slides)}"
        )

    # Map sentences for text lookup and coverage
    num_body = len(sentences) - 1 if len(sentences) > 0 and sentences[0][2] else len(sentences)
    expected_body_sids = list(range(1, num_body + 1))
    sentence_text_by_id = {idx: text for idx, (text, _, _) in enumerate(sentences)}

    all_slide_sids: list[int] = []

    for s_idx, slide in enumerate(slides):
        if not isinstance(slide, dict):
            errors.append(f"slides[{s_idx}] is not an object")
            continue

        slide_id = slide.get("id", f"d{s_idx + 1}")
        title = slide.get("title", "")
        points = slide.get("points", [])
        slide_sids = slide.get("sentence_ids", [])

        # 2. Points: 2-4 per slide
        if not isinstance(points, list):
            errors.append(f"Slide {slide_id}: 'points' must be an array")
            points = []
        elif not (2 <= len(points) <= 4):
            errors.append(f"Slide {slide_id}: expected 2-4 points, got {len(points)}")

        # 3. Lengths: title <= 6 words
        if not isinstance(title, str):
            errors.append(f"Slide {slide_id}: 'title' must be a string")
            title = ""
        else:
            w_title = count_words(title)
            if w_title > 6:
                errors.append(f"Slide {slide_id} title: '{title}' has {w_title} words (limit 6)")

        # Point lengths & text checks
        for p_idx, pt in enumerate(points):
            if not isinstance(pt, dict):
                errors.append(f"Slide {slide_id} points[{p_idx}] is not an object")
                continue
            pt_text = pt.get("text", "")
            if not isinstance(pt_text, str):
                errors.append(f"Slide {slide_id} point {p_idx} 'text' must be a string")
                pt_text = ""
            else:
                w_pt = count_words(pt_text)
                if w_pt > 12:
                    errors.append(
                        f"Slide {slide_id} point {p_idx} text: '{pt_text}' "
                        f"has {w_pt} words (limit 12)"
                    )

            # 6. Text checks on point text
            _check_text_rules(f"Slide {slide_id} point {p_idx} text", pt_text, errors)

        # 6. Text checks on slide title
        _check_text_rules(f"Slide {slide_id} title", title, errors)

        # Coverage checks within slide
        if not isinstance(slide_sids, list):
            errors.append(f"Slide {slide_id}: 'sentence_ids' must be a list")
            slide_sids = []
        else:
            if 0 in slide_sids:
                errors.append(
                    f"Slide {slide_id} contains sentence 0 (title); "
                    f"only body sentences 1..N may be partitioned"
                )
            if not slide_sids:
                errors.append(f"Slide {slide_id} has empty sentence_ids")
            elif any(not isinstance(s, int) for s in slide_sids):
                errors.append(f"Slide {slide_id} sentence_ids contains non-integer")
            elif slide_sids != list(range(slide_sids[0], slide_sids[-1] + 1)):
                errors.append(f"Slide {slide_id} sentence_ids {slide_sids} are not contiguous")

            all_slide_sids.extend(slide_sids)

        # Point partition within slide
        all_point_sids: list[int] = []
        for p_idx, pt in enumerate(points):
            if not isinstance(pt, dict):
                continue
            pt_sids = pt.get("sentence_ids", [])
            if not isinstance(pt_sids, list) or not pt_sids:
                errors.append(f"Slide {slide_id} point {p_idx} has empty sentence_ids")
                continue
            if any(not isinstance(s, int) for s in pt_sids):
                errors.append(f"Slide {slide_id} point {p_idx} sentence_ids contains non-integer")
                continue
            if pt_sids != list(range(pt_sids[0], pt_sids[-1] + 1)):
                errors.append(
                    f"Slide {slide_id} point {p_idx} sentence_ids {pt_sids} are not contiguous"
                )
            all_point_sids.extend(pt_sids)

        if all_point_sids != slide_sids:
            errors.append(
                f"Slide {slide_id} points do not strictly partition slide sentence_ids "
                f"(points cover {all_point_sids}, slide has {slide_sids})"
            )

        # 5. Grounding
        slide_text = " ".join(sentence_text_by_id.get(sid, "") for sid in slide_sids)
        if not digits_grounded(title, slide_text):
            errors.append(
                f"Slide {slide_id} title '{title}': "
                f"digits not grounded in slide sentences {slide_sids}"
            )

        for p_idx, pt in enumerate(points):
            if isinstance(pt, dict):
                pt_text = pt.get("text", "")
                pt_sids = pt.get("sentence_ids", [])
                point_sentences = " ".join(sentence_text_by_id.get(sid, "") for sid in pt_sids)
                if not digits_grounded(pt_text, point_sentences):
                    errors.append(
                        f"Slide {slide_id} point {p_idx} '{pt_text}': "
                        f"digits not grounded in point sentences {pt_sids}"
                    )

    # 4. Coverage across slides
    missing = sorted(set(expected_body_sids) - set(all_slide_sids))
    extra = sorted(set(all_slide_sids) - set(expected_body_sids))
    if missing:
        errors.append(f"Slides partition skipped sentences: {missing}")
    if extra:
        errors.append(f"Slides partition included unexpected sentences: {extra}")
    if all_slide_sids != sorted(all_slide_sids):
        errors.append("Slides sentence_ids are out of order")
    if len(all_slide_sids) != len(set(all_slide_sids)):
        errors.append("Slides have overlapping sentence_ids")

    repaired = dict(raw)
    repaired["schema_version"] = 1
    return repaired, errors


def _check_text_rules(path: str, text: str, errors: list[str]) -> None:
    """Validate text checks per rule 6: quotation marks, placeholders, etc."""
    if not text:
        return

    # Quotation marks check
    if any(q in text for q in QUOTATION_MARKS):
        errors.append(f"{path}: contains quotation marks ('{text}')")

    # Instruction check
    if re.search(r"\bicon\s*:", text, re.IGNORECASE):
        errors.append(
            f'{path}: "{text}" is an instruction, not on-screen text — '
            "put icons only in icon fields"
        )

    # Placeholder check
    norm_val = re.sub(r"[^\w/ ]", "", text).strip().casefold()
    if norm_val in PLACEHOLDER_WORDS:
        errors.append(f'{path}: "{text}" is a placeholder — show only what the beat says')

    # Internal id check (c1-c9, p1-p9, v1-v9, d1-d9)
    tokens = re.findall(r"\b[A-Za-z0-9]+\b", text)
    for tok in tokens:
        if re.match(r"^[cpvd]\d+$", tok.lower()):
            errors.append(f'{path}: contains internal id "{tok}"')

    # Completeness check
    cut_errors = text_complete_errors(path, text)
    errors.extend(cut_errors)


def plan_deck(
    ingest: IngestRecord,
    backend: LLMBackend,
    no_cache: bool = False,
) -> DeckPlan:
    """Generate and validate a presentation slide deck from ingest script."""
    sentences = build_sentence_list(ingest)
    word_count = ingest.word_count or sum(len(p.split()) for p in (ingest.paragraphs or []))
    target_slides = compute_target_slides(word_count)

    schema = build_deck_schema()
    facing_schema = llm_facing_schema(schema)
    prompt = format_deck_prompt(sentences, word_count, target_slides)

    def _validate(raw_output: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        return validate_deck(raw_output, sentences, word_count)

    result, attempts = run_with_retries(
        backend,
        stage="deck",
        system="Return valid JSON matching the schema.",
        user=prompt,
        schema=facing_schema,
        validate=_validate,
        max_attempts=3,
        num_predict=2048,
        temperature=0.3,
    )

    if result is None:
        all_errs: list[str] = []
        for att in attempts:
            all_errs.extend(att.errors)
        err_msg = "\n".join(f"- {e}" for e in all_errs)
        raise ValidationFailed(f"deck stage failed after 3 attempts:\n{err_msg}")

    return DeckPlan.model_validate(result)


def run_deck_stage(job: Job, ctx: RunContext) -> None:
    """Stage runner for deck stage."""
    t0 = time.perf_counter()

    ingest_path = job.dir / "ingest.json"
    if not ingest_path.is_file():
        raise ValidationFailed(f"ingest.json missing in job {job.job_id}")

    ingest = IngestRecord.model_validate_json(ingest_path.read_text(encoding="utf-8"))

    backend = OllamaBackend(
        no_cache=ctx.no_llm_cache,
    )

    deck_plan = plan_deck(ingest, backend, no_cache=ctx.no_llm_cache)

    deck_path = job.dir / "deck.json"
    deck_path.write_text(deck_plan.model_dump_json(indent=2) + "\n", encoding="utf-8")

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    log_file = job.dir / "logs" / "deck.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text(
        f"llm_calls={backend.calls} cache_hits={backend.cache_hits} elapsed_ms={elapsed_ms}\n",
        encoding="utf-8",
    )

"""Presentation performance stage: simulates realistic presenter speech with seeded RNG.

Per design_presentation_simulation.md §4 and §5.
"""

from __future__ import annotations

import json
import random
import re
import time
from pathlib import Path
from typing import Any, Literal

from animated_infographics.audio.narrate import build_sentence_list
from animated_infographics.contracts.deck import DeckPlan
from animated_infographics.contracts.models import IngestRecord
from animated_infographics.contracts.performance import (
    BackRefTarget,
    PerformancePlan,
    PerformedSentence,
    PointTarget,
)
from animated_infographics.errors import ValidationFailed
from animated_infographics.jobs import Job, RunContext
from animated_infographics.planner.llm import LLMBackend, OllamaBackend

FILLERS = ["um", "so", "you know", "basically", "right"]


def _extract_digit_runs(text: str) -> list[str]:
    """Extract all digit runs and formatted numbers from text."""
    return re.findall(r"\b\d+(?:[.,]\d+)*\b", text)


def _extract_proper_names(text: str) -> list[str]:
    """Extract capitalized words that are not the first word of the sentence."""
    words = text.split()
    names: list[str] = []
    for w in words[1:]:
        cleaned = re.sub(r"^[^a-zA-Z]+|[^a-zA-Z]+$", "", w)
        if cleaned and cleaned[0].isupper() and cleaned.isalpha():
            names.append(cleaned)
    return names


def _validate_paraphrase(original: str, paraphrased: str) -> bool:
    """Validator: paraphrase must preserve all digit runs and proper names."""
    orig_digits = _extract_digit_runs(original)
    for d in orig_digits:
        if d not in paraphrased:
            return False

    orig_names = _extract_proper_names(original)
    for name in orig_names:
        if name not in paraphrased:
            return False

    # Check that quoted phrases (if any) survive
    quoted = re.findall(r'"([^"]*)"', original)
    for q in quoted:
        if q not in paraphrased:
            return False

    return True


def plan_performance(
    ingest: IngestRecord,
    deck: DeckPlan,
    backend: LLMBackend,
    level: Literal["mild", "strong"] = "mild",
    seed: int = 7,
) -> PerformancePlan:
    """Plan simulated presentation performance with isolated seeded RNG streams."""
    if level not in ("mild", "strong"):
        raise ValueError(f"Unknown perturb level '{level}', expected 'mild' or 'strong'")

    # 1. Independent RNG streams per operation per §4
    rng_paraphrase = random.Random(f"{seed}:paraphrase")
    rng_filler = random.Random(f"{seed}:filler")
    rng_drop = random.Random(f"{seed}:drop")
    rng_swap = random.Random(f"{seed}:swap")
    rng_adlib = random.Random(f"{seed}:adlib")
    rng_back_ref = random.Random(f"{seed}:back_ref")
    rng_skip_point = random.Random(f"{seed}:skip_point")

    # Rates
    p_paraphrase = 0.4 if level == "mild" else 0.8
    words_per_filler = 40 if level == "mild" else 15
    p_drop = 0.05 if level == "mild" else 0.15
    p_swap = 0.05 if level == "mild" else 0.15
    n_adlib = 1 if level == "mild" else 3
    n_back_ref = 0 if level == "mild" else 1
    n_skip_point = 0 if level == "mild" else 1

    op_counts: dict[str, int] = {
        "paraphrase": 0,
        "filler": 0,
        "drop": 0,
        "swap": 0,
        "adlib": 0,
        "back_ref": 0,
        "skip_point": 0,
    }

    # 2. Map sentence IDs to (slide_id, point_idx)
    raw_sentences = build_sentence_list(ingest)
    # Filter body sentences (sentence 0 is title)
    body_sentence_map: dict[int, str] = {
        idx: text for idx, (text, _, is_title) in enumerate(raw_sentences) if not is_title
    }

    sent_to_point: dict[int, tuple[str, int]] = {}
    slide_first_sentences: set[int] = set()

    for slide in deck.slides:
        if slide.sentence_ids:
            slide_first_sentences.add(slide.sentence_ids[0])
        for p_idx, pt in enumerate(slide.points):
            for sid in pt.sentence_ids:
                sent_to_point[sid] = (slide.id, p_idx)

    # 3. Skip a whole point (strong: 1, mild: 0; never on the first slide)
    skipped_points: set[tuple[str, int]] = set()
    if n_skip_point > 0:
        eligible_skip_points = [
            (s.id, p_idx)
            for s_idx, s in enumerate(deck.slides)
            if s_idx > 0
            for p_idx in range(len(s.points))
        ]
        if eligible_skip_points:
            pt_to_skip = rng_skip_point.choice(eligible_skip_points)
            skipped_points.add(pt_to_skip)
            op_counts["skip_point"] += 1

    # Load prompts
    prompts_dir = Path(__file__).resolve().parent / "prompts"
    paraphrase_prompt_template = (prompts_dir / "perform_paraphrase.md").read_text(encoding="utf-8")
    adlib_prompt_template = (prompts_dir / "perform_adlib.md").read_text(encoding="utf-8")
    back_ref_prompt_template = (prompts_dir / "perform_back_ref.md").read_text(encoding="utf-8")

    # 4. Process points and sentences in deck order
    performed_sentences: list[PerformedSentence] = []
    adlib_positions: list[int] = []

    # Prepare point groups
    point_groups: list[dict[str, Any]] = []
    for s_idx, slide in enumerate(deck.slides):
        for p_idx, pt in enumerate(slide.points):
            if (slide.id, p_idx) in skipped_points:
                continue

            # Gather and filter sentences for this point
            pt_sents: list[tuple[int, str]] = []
            for sid in pt.sentence_ids:
                if sid not in body_sentence_map:
                    continue
                # Sentence drop: never the slide's first sentence
                if sid in slide_first_sentences:
                    pt_sents.append((sid, body_sentence_map[sid]))
                elif rng_drop.random() < p_drop:
                    op_counts["drop"] += 1
                else:
                    pt_sents.append((sid, body_sentence_map[sid]))

            # If all sentences were dropped in this point, restore at least the first
            if not pt_sents and pt.sentence_ids:
                first_sid = pt.sentence_ids[0]
                if first_sid in body_sentence_map:
                    pt_sents.append((first_sid, body_sentence_map[first_sid]))
                    if op_counts["drop"] > 0:
                        op_counts["drop"] -= 1

            # Sentence swap within point
            if len(pt_sents) >= 2:
                for swap_i in range(len(pt_sents) - 1):
                    if rng_swap.random() < p_swap:
                        pt_sents[swap_i], pt_sents[swap_i + 1] = (
                            pt_sents[swap_i + 1],
                            pt_sents[swap_i],
                        )
                        op_counts["swap"] += 1

            point_groups.append(
                {
                    "slide_id": slide.id,
                    "slide_title": slide.title,
                    "slide_idx": s_idx,
                    "point_idx": p_idx,
                    "point_text": pt.text,
                    "sentences": pt_sents,
                }
            )

    # 5. Paraphrase and assemble
    for pt_info in point_groups:
        slide_id = pt_info["slide_id"]
        point_idx = pt_info["point_idx"]
        target_label = PointTarget(slide=slide_id, point=point_idx)

        for sid, text in pt_info["sentences"]:
            should_paraphrase = rng_paraphrase.random() < p_paraphrase
            final_text = text
            op: Literal["verbatim", "paraphrase", "filler", "adlib", "back_ref"] = "verbatim"

            if should_paraphrase:
                digits_str = ", ".join(_extract_digit_runs(text)) or "none"
                names_str = ", ".join(_extract_proper_names(text)) or "none"
                prompt = (
                    paraphrase_prompt_template.replace("{original_sentence}", text)
                    .replace("{numbers_list}", digits_str)
                    .replace("{names_list}", names_str)
                )

                resp = backend.generate_json(
                    stage="perform",
                    messages=[{"role": "user", "content": prompt}],
                    schema={
                        "type": "object",
                        "properties": {"paraphrase": {"type": "string"}},
                        "required": ["paraphrase"],
                    },
                    attempt=0,
                    temperature=0.7,
                )
                para_candidate = resp.get("paraphrase", "").strip() if resp else ""
                if para_candidate and _validate_paraphrase(text, para_candidate):
                    final_text = para_candidate
                    op = "paraphrase"
                    op_counts["paraphrase"] += 1

            performed_sentences.append(
                PerformedSentence(
                    text=final_text,
                    label=target_label,
                    op=op,
                    source_sentence_id=sid,
                )
            )

        # Record boundary after point
        adlib_positions.append(len(performed_sentences))

    # 6. Insert Fillers ("um", "so", "you know", "basically", "right")
    total_words = sum(len(s.text.split()) for s in performed_sentences)
    target_fillers = max(1, round(total_words / words_per_filler))

    # Find valid insertion points across performed sentences
    # Insertion spots: start of sentence or after commas
    for _ in range(target_fillers):
        if not performed_sentences:
            break
        sent_idx = rng_filler.randint(0, len(performed_sentences) - 1)
        cur_sent = performed_sentences[sent_idx]
        filler_word = rng_filler.choice(FILLERS)

        # Either insert at sentence start or after a comma
        commas = [m.start() for m in re.finditer(r",\s*", cur_sent.text)]
        if commas and rng_filler.random() < 0.5:
            insert_pos = rng_filler.choice(commas) + 1
            new_text = cur_sent.text[:insert_pos] + f" {filler_word}," + cur_sent.text[insert_pos:]
        else:
            first_word, _, rest = cur_sent.text.partition(" ")
            new_text = f"{filler_word.capitalize()}, {first_word.lower()} {rest}"

        performed_sentences[sent_idx] = PerformedSentence(
            text=new_text,
            label=cur_sent.label,
            op=cur_sent.op,
            source_sentence_id=cur_sent.source_sentence_id,
        )
        op_counts["filler"] += 1

    # 7. Insert Ad-lib tangents (mild: 1, strong: 3)
    if n_adlib > 0 and point_groups:
        # Choose distinct insertion points among point boundaries (excluding end of entire talk)
        valid_boundaries = list(range(1, len(point_groups)))
        if valid_boundaries:
            chosen_bounds = sorted(
                rng_adlib.sample(valid_boundaries, min(n_adlib, len(valid_boundaries)))
            )
            # Insert in reverse order to preserve indices
            for b_idx in reversed(chosen_bounds):
                preceding_pt = point_groups[b_idx - 1]
                adlib_prompt = adlib_prompt_template.replace(
                    "{slide_title}", preceding_pt["slide_title"]
                ).replace("{point_text}", preceding_pt["point_text"])

                resp = backend.generate_json(
                    stage="perform",
                    messages=[{"role": "user", "content": adlib_prompt}],
                    schema={
                        "type": "object",
                        "properties": {"adlib": {"type": "string"}},
                        "required": ["adlib"],
                    },
                    attempt=0,
                    temperature=0.7,
                )
                adlib_text = resp.get("adlib", "").strip() if resp else ""
                if not adlib_text:
                    adlib_text = "I love this part, honestly."

                # Find boundary position in performed_sentences
                insert_pos = adlib_positions[b_idx - 1]
                performed_sentences.insert(
                    insert_pos,
                    PerformedSentence(
                        text=adlib_text,
                        label="adlib",
                        op="adlib",
                        source_sentence_id=None,
                    ),
                )
                op_counts["adlib"] += 1

    # 8. Insert Back-reference (strong: 1, mild: 0; inserted >= 2 slides later)
    if n_back_ref > 0 and len(deck.slides) >= 3 and point_groups:
        # Pick an early point from slide 0 or 1
        early_candidates = [
            pt for pt in point_groups if pt["slide_idx"] in (0, 1) and pt["point_idx"] == 0
        ]
        if early_candidates:
            ref_pt = rng_back_ref.choice(early_candidates)
            ref_slide_idx = ref_pt["slide_idx"]

            # Insertion points >= 2 slides later
            later_candidates = [
                (idx, pt)
                for idx, pt in enumerate(point_groups)
                if pt["slide_idx"] >= ref_slide_idx + 2
            ]
            if later_candidates:
                insert_group_idx, current_pt = rng_back_ref.choice(later_candidates)
                back_ref_prompt = back_ref_prompt_template.replace(
                    "{earlier_point_text}", ref_pt["point_text"]
                ).replace("{current_slide_title}", current_pt["slide_title"])

                resp = backend.generate_json(
                    stage="perform",
                    messages=[{"role": "user", "content": back_ref_prompt}],
                    schema={
                        "type": "object",
                        "properties": {"back_ref": {"type": "string"}},
                        "required": ["back_ref"],
                    },
                    attempt=0,
                    temperature=0.7,
                )
                back_ref_text = resp.get("back_ref", "").strip() if resp else ""
                if not back_ref_text:
                    back_ref_text = f"Remember what we saw about {ref_pt['point_text']}?"

                # Insert after the current point's sentences
                insert_pos = adlib_positions[insert_group_idx]
                target_back_ref = BackRefTarget(
                    back_ref=PointTarget(slide=ref_pt["slide_id"], point=ref_pt["point_idx"])
                )
                performed_sentences.insert(
                    insert_pos,
                    PerformedSentence(
                        text=back_ref_text,
                        label=target_back_ref,
                        op="back_ref",
                        source_sentence_id=None,
                    ),
                )
                op_counts["back_ref"] += 1

    # 9. Enforce validators per §4
    source_body_count = len(body_sentence_map)
    surviving_sources = {
        s.source_sentence_id for s in performed_sentences if s.source_sentence_id is not None
    }
    retention_rate = len(surviving_sources) / float(source_body_count) if source_body_count else 1.0
    min_retention = 0.70 if level == "mild" else 0.50

    if retention_rate < min_retention:
        raise ValidationFailed(
            f"Performance retained only {retention_rate:.1%} of sentences, "
            f"below {min_retention:.1%} bar"
        )

    # Verify labels match deck partition
    for s in performed_sentences:
        if s.source_sentence_id is not None:
            expected_target = sent_to_point.get(s.source_sentence_id)
            if expected_target:
                assert isinstance(s.label, PointTarget)
                assert (s.label.slide, s.label.point) == expected_target

    return PerformancePlan(
        schema_version=1,
        seed=seed,
        level=level,
        sentences=performed_sentences,
        op_counts=op_counts,
    )


def run_perform_stage(job: Job, ctx: RunContext) -> None:
    """Execute perform stage producing performance.json."""
    t0 = time.perf_counter()

    ingest_path = job.dir / "ingest.json"
    deck_path = job.dir / "deck.json"

    if not ingest_path.is_file():
        raise FileNotFoundError(f"ingest.json missing in job {job.job_id}")
    if not deck_path.is_file():
        raise FileNotFoundError(f"deck.json missing in job {job.job_id}")

    ingest = IngestRecord.model_validate_json(ingest_path.read_text(encoding="utf-8"))
    deck = DeckPlan.model_validate_json(deck_path.read_text(encoding="utf-8"))

    level: Literal["mild", "strong"] = (
        "strong" if (ctx.perturb == "strong" or ingest.perturb == "strong") else "mild"
    )
    seed = ctx.seed if ctx.seed is not None else (ingest.seed if ingest.seed is not None else 7)

    backend = OllamaBackend(no_cache=ctx.no_llm_cache)
    performance = plan_performance(ingest, deck, backend, level=level, seed=seed)

    perf_path = job.dir / "performance.json"
    perf_path.write_text(performance.model_dump_json(indent=2) + "\n", encoding="utf-8")

    # Update report.json with op_counts
    report_path = job.dir / "preview" / "report.json"
    if report_path.is_file():
        try:
            report_data = json.loads(report_path.read_text(encoding="utf-8"))
            report_data["op_counts"] = performance.op_counts
            report_path.write_text(json.dumps(report_data, indent=2) + "\n", encoding="utf-8")
        except Exception:
            pass

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    log_file = job.dir / "logs" / "perform.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(
            f"Perform: level={level}, seed={seed}, sentences={len(performance.sentences)}, "
            f"op_counts={performance.op_counts}, llm_calls={backend.calls}, "
            f"elapsed_ms={elapsed_ms}\n"
        )

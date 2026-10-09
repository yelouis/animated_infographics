"""Anticipate stage: anticipated speech generation for presentation tree nodes.

Per design_presentation_simulation.md §6.6.1 and agent_execution_guide.md §1.3 (J2).
Runs after tree stage only when matcher is 'anticipate'.
Reads only deck.json and tree.json (isolation invariant).
Produces anticipation.json and logs/anticipate.log.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable
from typing import Any

from animated_infographics.contracts.anticipation import AnticipationPlan
from animated_infographics.contracts.tree import TreePlan
from animated_infographics.jobs import Job, RunContext
from animated_infographics.planner.llm import (
    OllamaBackend,
    run_with_retries,
)

logger = logging.getLogger(__name__)

ANTICIPATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "sentence_1": {"type": "string"},
        "sentence_2": {"type": "string"},
        "sentence_3": {"type": "string"},
        "sentence_4": {"type": "string"},
    },
    "required": ["sentence_1", "sentence_2", "sentence_3", "sentence_4"],
    "additionalProperties": False,
}


def build_point_prompt(slide: dict[str, Any], point_text: str) -> str:
    """Build point node user prompt verbatim per §6.6.1."""
    points = slide.get("points", [])
    bullet_lines = "\n".join(
        f"- {pt.get('text', '') if isinstance(pt, dict) else pt.text}" for pt in points
    )
    title = slide.get("title", "")
    return (
        "Here is one slide from a talk.\n"
        f"Slide title: {title}\n"
        "Points on this slide:\n"
        f"{bullet_lines}\n"
        f'The presenter is now covering this point: "{point_text}"\n'
        "Write 4 different sentences the presenter might actually say out loud while "
        "covering this point. "
        "Use plain spoken English, the way a person talks, not slide text. "
        "Do not add facts that are not on the slide."
    )


def build_section_prompt(slide: dict[str, Any]) -> str:
    """Build section node user prompt verbatim per §6.6.1."""
    points = slide.get("points", [])
    bullet_lines = "\n".join(
        f"- {pt.get('text', '') if isinstance(pt, dict) else pt.text}" for pt in points
    )
    title = slide.get("title", "")
    return (
        "Here is one slide from a talk.\n"
        f"Slide title: {title}\n"
        "Points on this slide:\n"
        f"{bullet_lines}\n"
        "The presenter is now moving on to this slide.\n"
        "Write 4 different sentences the presenter might say out loud to introduce this slide. "
        "Use plain spoken English, the way a person talks, not slide text. "
        "Do not add facts that are not on the slide."
    )


def _clean_for_comparison(s: str) -> str:
    """Casefold and strip punctuation for equivalence checks."""
    return re.sub(r"[^\w]", "", s.casefold())


def validate_anticipation_dict(
    raw: dict[str, Any],
    slide: dict[str, Any],
    target_text: str,
) -> list[str]:
    """Validate anticipation dictionary per §6.6.1 rules."""
    errors: list[str] = []
    keys = ["sentence_1", "sentence_2", "sentence_3", "sentence_4"]

    # Gather grounded digits from slide title and points
    slide_text_parts = [slide.get("title", "")]
    for pt in slide.get("points", []):
        pt_txt = pt.get("text", "") if isinstance(pt, dict) else getattr(pt, "text", "")
        slide_text_parts.append(pt_txt)
    slide_digits = set(re.findall(r"\d+", " ".join(slide_text_parts)))

    # 1. Per-sentence checks
    for k in keys:
        if k not in raw or not isinstance(raw[k], str):
            errors.append(f"{k}: missing or not a string")
            continue
        val = raw[k].strip()
        words = val.split()
        n = len(words)
        if not (6 <= n <= 35):
            errors.append(f"{k}: {n} words — write 6 to 35 words")

        # Copies slide check
        val_clean = _clean_for_comparison(val)
        target_clean = _clean_for_comparison(target_text)
        if val_clean == target_clean and val_clean:
            errors.append(f"{k} copies the slide — say it the way a presenter would")

        # Grounded digits check
        for d in re.findall(r"\d+", val):
            if d not in slide_digits:
                errors.append(f'{k}: "{d}" is not on the slide — do not add numbers')

    # 2. Duplicate checks across sentences:
    # "sentence_<j> repeats sentence_<k> — write a different sentence" (where j > k)
    for j_idx in range(len(keys)):
        k_j = keys[j_idx]
        val_j = raw.get(k_j, "")
        if not isinstance(val_j, str) or not val_j:
            continue
        clean_j = _clean_for_comparison(val_j)
        if not clean_j:
            continue
        for k_idx in range(j_idx):
            k_k = keys[k_idx]
            val_k = raw.get(k_k, "")
            if not isinstance(val_k, str) or not val_k:
                continue
            clean_k = _clean_for_comparison(val_k)
            if clean_j == clean_k:
                errors.append(f"{k_j} repeats {k_k} — write a different sentence")
                break

    return errors


def run_anticipate_stage(job: Job, ctx: RunContext) -> None:
    """Execute anticipation stage for tree nodes."""
    t0 = time.perf_counter()
    log_dir = job.dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "anticipate.log"

    matcher_name = ctx.matcher or "bm25"
    if matcher_name != "anticipate":
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"anticipate: skipped (matcher={matcher_name})\n")
        return

    deck_path = job.dir / "deck.json"
    tree_path = job.dir / "tree.json"

    if not deck_path.is_file():
        raise FileNotFoundError(f"deck.json missing in job {job.job_id}")
    if not tree_path.is_file():
        raise FileNotFoundError(f"tree.json missing in job {job.job_id}")

    deck_data = json.loads(deck_path.read_text(encoding="utf-8"))
    tree = TreePlan.model_validate_json(tree_path.read_text(encoding="utf-8"))

    slides_by_id = {s.get("id"): s for s in deck_data.get("slides", [])}

    backend = OllamaBackend(no_cache=ctx.no_llm_cache)

    anticipations: dict[str, list[str]] = {}
    filled = 0
    failed = 0
    log_lines: list[str] = []

    for node in tree.nodes:
        slide = slides_by_id.get(node.slide)
        if slide is None:
            anticipations[node.id] = []
            failed += 1
            log_lines.append(
                f"anticipate: {node.id} failed: slide {node.slide} not found in deck\n"
            )
            continue

        if node.kind == "section":
            prompt = build_section_prompt(slide)
            target_text = slide.get("title", "")
        else:
            if node.point_i is not None and 0 <= node.point_i < len(slide.get("points", [])):
                pt = slide["points"][node.point_i]
                point_text = pt.get("text", "") if isinstance(pt, dict) else getattr(pt, "text", "")
            else:
                point_text = node.text
            prompt = build_point_prompt(slide, point_text)
            target_text = point_text

        def _make_validator(
            s: dict[str, Any], t: str
        ) -> Callable[[dict[str, Any]], tuple[dict[str, Any], list[str]]]:
            def _validate(raw_out: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
                errs = validate_anticipation_dict(raw_out, s, t)
                return raw_out, errs

            return _validate

        validator_fn = _make_validator(slide, target_text)

        result, attempts = run_with_retries(
            backend,
            stage="anticipate",
            system="",
            user=prompt,
            schema=ANTICIPATE_SCHEMA,
            validate=validator_fn,
            max_attempts=3,
            num_predict=320,
            temperature=0.6,
        )

        if result is not None:
            sentences = [result[f"sentence_{idx}"].strip() for idx in range(1, 5)]
            anticipations[node.id] = sentences
            filled += 1
        else:
            anticipations[node.id] = []
            failed += 1
            last_err = (
                attempts[-1].errors[-1]
                if attempts and attempts[-1].errors
                else "max attempts exhausted"
            )
            log_lines.append(f"anticipate: {node.id} failed: {last_err}\n")

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    llm_calls = getattr(backend, "calls", 0)
    cache_hits = getattr(backend, "cache_hits", 0)

    log_lines.append(
        f"anticipate: nodes={len(tree.nodes)} filled={filled} failed={failed} "
        f"llm_calls={llm_calls} cache_hits={cache_hits} elapsed_ms={elapsed_ms}\n"
    )

    with open(log_file, "w", encoding="utf-8") as f:
        f.writelines(log_lines)

    plan = AnticipationPlan(schema_version=1, nodes=anticipations)
    (job.dir / "anticipation.json").write_text(
        plan.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )

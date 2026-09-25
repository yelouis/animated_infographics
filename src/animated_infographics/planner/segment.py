"""Narration segmentation into pacing beats with LLM proposal and deterministic timing rules."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final

from animated_infographics.contracts.models import Beats, Transcript
from animated_infographics.planner.llm import LLMBackend, run_with_retries
from animated_infographics.timing.beats import build_beats

SEGMENT_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        "groups": {
            "type": "array",
            "items": {
                "type": "array",
                "items": {"type": "integer"},
            },
        },
    },
    "required": ["groups"],
    "additionalProperties": False,
}


def load_prompt(name: str) -> str:
    """Load prompt template from planner/prompts/ directory."""
    prompt_path = Path(__file__).parent / "prompts" / name
    return prompt_path.read_text(encoding="utf-8")


def validate_partition(groups: Any, n_sentences: int) -> tuple[bool, str]:
    """Validate that groups form an exact ordered partition of 0..n_sentences-1."""
    if not isinstance(groups, list):
        return False, "groups must be a list"

    if n_sentences == 0:
        if len(groups) == 0:
            return True, ""
        return False, "expected empty groups for 0 sentences"

    if not groups:
        return False, "groups list cannot be empty"

    flattened: list[int] = []
    for g_idx, g in enumerate(groups):
        if not isinstance(g, list) or not g:
            return False, f"group {g_idx} must be a non-empty list of integers"

        for i, val in enumerate(g):
            if not isinstance(val, int):
                return False, f"item {val} in group {g_idx} is not an integer"
            if i > 0 and val != g[i - 1] + 1:
                return False, f"group {g_idx} has non-contiguous or out-of-order indices: {g}"
            flattened.append(val)

    expected = list(range(n_sentences))
    if flattened != expected:
        if len(flattened) != len(set(flattened)):
            return False, "groups contain duplicate sentence indices"
        if len(flattened) < n_sentences:
            return (
                False,
                f"groups have missing sentence indices (gap): "
                f"got {len(flattened)}, expected {n_sentences}",
            )
        return False, f"groups indices do not match 0..{n_sentences - 1} exactly in order"

    return True, ""


def build_fallback_groups(n_sentences: int) -> list[list[int]]:
    """Return fallback grouping: one group per sentence."""
    return [[i] for i in range(n_sentences)]


def plan_beats(
    transcript: Transcript,
    backend: LLMBackend,
    *,
    skip_merge: bool = False,
) -> Beats:
    """Plan scene beats by prompting the LLM for sentence groupings with deterministic fallback."""
    n_sentences = len(transcript.sentences)
    if n_sentences == 0:
        return Beats(schema_version=1, beats=[])

    lines: list[str] = []
    for s in transcript.sentences:
        dur = s.end_ms - s.start_ms
        tag = " (title)" if s.is_title else ""
        lines.append(f'[{s.i}] "{s.text}" (duration: {dur}ms, paragraph: {s.paragraph_i}{tag})')

    prompt_tmpl = load_prompt("segment.md")
    user_prompt = prompt_tmpl.format(
        max_sentence_idx=n_sentences - 1,
        sentences_text="\n".join(lines),
    )

    def validate_segment_output(output: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        if not isinstance(output, dict):
            return output, ["Output must be a JSON object"]
        groups = output.get("groups")
        ok, err = validate_partition(groups, n_sentences)
        if not ok:
            return output, [err]
        return output, []

    result, _attempts = run_with_retries(
        backend=backend,
        stage="segment",
        system=(
            "You are an expert video pacing editor. Group story sentences into scene beats. "
            "Output JSON strictly matching the schema."
        ),
        user=user_prompt,
        schema=SEGMENT_SCHEMA,
        validate=validate_segment_output,
        max_attempts=3,
    )

    if result is not None and "groups" in result:
        groups = result["groups"]
    else:
        groups = build_fallback_groups(n_sentences)

    beats = build_beats(transcript, groups, skip_merge=skip_merge)
    return Beats(schema_version=1, beats=beats)

"""Creative license stage critic for checking visual embellishments.

Per design_styles.md §3.4.
"""

from __future__ import annotations

from typing import Any

from animated_infographics.contracts.director import (
    AsideDirective,
    DirectorPlan,
    LicenseDropped,
    MetaphorDirective,
)
from animated_infographics.contracts.models import Beat
from animated_infographics.planner.llm import (
    LLMBackend,
    llm_facing_schema,
    run_with_retries,
)

LICENSE_SYSTEM_PROMPT: str = (
    "You evaluate whether proposed visuals add ungrounded events, dialogue, "
    "or facts to a story passage. Output JSON matching the schema."
)

LICENSE_QUESTION: str = (
    "Would showing this visual add something the passage does not contain: "
    "an event, a line of dialogue, or a fact; or contradict the passage? "
    "Background details that change nothing are fine."
)


def _build_passage(beats: list[Beat], target_i: int) -> str:
    """Build four-beat passage around target beat per critic framing."""
    indices = [target_i - 2, target_i - 1, target_i, target_i + 1]
    passage_beats: list[str] = []
    for idx in indices:
        if 0 <= idx < len(beats):
            b_text = beats[idx].text.strip()
            if b_text:
                passage_beats.append(b_text)
    return " ".join(passage_beats)


def _build_license_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["ok", "adds_event", "adds_dialogue", "adds_fact", "contradicts"],
            }
        },
        "required": ["verdict"],
        "additionalProperties": False,
    }


def _validate_verdict(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    v = raw.get("verdict")
    valid_verdicts = {"ok", "adds_event", "adds_dialogue", "adds_fact", "contradicts"}
    if v not in valid_verdicts:
        return raw, [f"invalid verdict '{v}' — expected one of {sorted(valid_verdicts)}"]
    return raw, []


def check_metaphor_license(
    metaphor: MetaphorDirective,
    beats: list[Beat],
    backend: LLMBackend,
) -> str:
    """Run blind license check for a single metaphor directive."""
    passage = _build_passage(beats, metaphor.beat_i)
    label_part = f'\nlabel: "{metaphor.label}"' if metaphor.label else ""
    visual_desc = f'image: "{metaphor.image}"{label_part}'

    user_content = (
        f"Passage (read all of it; who speaks is often named in the sentence before a quote):\n"
        f"{passage}\n\n"
        f"Visual:\n"
        f"{visual_desc}\n\n"
        f"{LICENSE_QUESTION}"
    )

    schema = llm_facing_schema(_build_license_schema())
    try:
        res, _ = run_with_retries(
            backend,
            stage="license",
            system=LICENSE_SYSTEM_PROMPT,
            user=user_content,
            schema=schema,
            validate=_validate_verdict,
            max_attempts=3,
            num_predict=64,
            temperature=0.0,
        )
        if res is None:
            return "failed"
        return str(res.get("verdict", "failed"))
    except Exception:
        return "failed"


def check_aside_license(
    aside: AsideDirective,
    beats: list[Beat],
    backend: LLMBackend,
) -> str:
    """Run blind license check for a single aside directive."""
    passage = _build_passage(beats, aside.beat_i)
    lines: list[str] = [f"kind: {aside.kind}"]
    if aside.icon:
        lines.append(f"icon: {aside.icon}")
    if aside.text:
        lines.append(f'text: "{aside.text}"')
    visual_desc = "\n".join(lines)

    user_content = (
        f"Passage (read all of it; who speaks is often named in the sentence before a quote):\n"
        f"{passage}\n\n"
        f"Visual:\n"
        f"{visual_desc}\n\n"
        f"{LICENSE_QUESTION}"
    )

    schema = llm_facing_schema(_build_license_schema())
    try:
        res, _ = run_with_retries(
            backend,
            stage="license",
            system=LICENSE_SYSTEM_PROMPT,
            user=user_content,
            schema=schema,
            validate=_validate_verdict,
            max_attempts=3,
            num_predict=64,
            temperature=0.0,
        )
        if res is None:
            return "failed"
        return str(res.get("verdict", "failed"))
    except Exception:
        return "failed"


def run_license_checks(
    plan: DirectorPlan,
    beats: list[Beat],
    backend: LLMBackend,
) -> tuple[DirectorPlan, list[LicenseDropped]]:
    """Evaluate each metaphor and aside against the license check.

    Any non-ok verdict (or failed call) drops the item and records it in license_dropped.
    """
    kept_metaphors: list[MetaphorDirective] = []
    dropped: list[LicenseDropped] = list(plan.license_dropped)

    for metaphor in plan.metaphors:
        verdict = check_metaphor_license(metaphor, beats, backend)
        if verdict == "ok":
            kept_metaphors.append(metaphor)
        else:
            dropped.append(LicenseDropped(item=metaphor.model_dump(), verdict=verdict))

    kept_asides: list[AsideDirective] = []
    for aside in plan.asides:
        verdict = check_aside_license(aside, beats, backend)
        if verdict == "ok":
            kept_asides.append(aside)
        else:
            dropped.append(LicenseDropped(item=aside.model_dump(), verdict=verdict))

    new_plan = DirectorPlan(
        schema_version=1,
        motifs=plan.motifs,
        metaphors=kept_metaphors,
        asides=kept_asides,
        license_dropped=dropped,
        overlay_dropped=plan.overlay_dropped,
    )
    return new_plan, dropped

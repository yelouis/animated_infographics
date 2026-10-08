"""Director stage planner and validators for creative style.

Per design_styles.md §3.3.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, get_args

from animated_infographics.assets.illustrate import text_expected
from animated_infographics.contracts.director import (
    AsideDirective,
    DirectorPlan,
    MetaphorDirective,
    MotifDirective,
)
from animated_infographics.contracts.icons import ICON_NAMES, IconName
from animated_infographics.contracts.models import Beat, Bible
from animated_infographics.planner.llm import (
    Attempt,
    LLMBackend,
    llm_facing_schema,
    run_with_retries,
)
from animated_infographics.planner.props import ICONS_PROMPT_BLOCK
from animated_infographics.planner.rhythm import QUOTED
from animated_infographics.planner.select import _build_compact_bible
from animated_infographics.planner.validate import (
    internal_id_errors,
    text_complete_errors,
)
from animated_infographics.planner.words import count_words

DIRECTOR_SYSTEM_PROMPT: str = (
    "You are the Creative Director for an animated explainer video. "
    "Plan recurring motifs, visual metaphors, and asides across the whole story. "
    "Return valid JSON matching the schema."
)


@dataclass(frozen=True)
class DirectorContext:
    """Context required for director validation."""

    beats: list[Beat]
    bible: Bible


def compute_director_counts(num_beats: int) -> tuple[int, int]:
    """Calculate expected counts for metaphors and asides per design_styles.md §3.3.

    metaphors: max(2, min(5, n // 12))
    asides: max(2, min(6, n // 10))
    """
    expected_metaphors = max(2, min(5, num_beats // 12))
    expected_asides = max(2, min(6, num_beats // 10))
    return expected_metaphors, expected_asides


def build_director_schema(beats: list[Beat], bible: Bible) -> dict[str, Any]:
    """Build JSON Schema for director output."""
    n = len(beats)
    beat_enums = list(range(1, n)) if n > 1 else [1]
    cast_enums = [c.id for c in bible.cast]
    icon_enums = list(ICON_NAMES)
    set_piece_enums = [sp.id for sp in bible.set_pieces]

    motif_appearance_schema = {
        "type": "object",
        "properties": {
            "beat_i": {"type": "integer", "enum": beat_enums},
            "role": {"type": "string", "enum": ["plant", "echo", "payoff"]},
        },
        "required": ["beat_i", "role"],
        "additionalProperties": False,
    }

    motif_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "icon": {"type": ["string", "null"], "enum": [*icon_enums, None]},
            "set_piece_id": {"type": ["string", "null"], "enum": [*set_piece_enums, None]},
            "appearances": {
                "type": "array",
                "items": motif_appearance_schema,
            },
        },
        "required": ["id", "name", "appearances"],
        "additionalProperties": False,
    }

    metaphor_schema = {
        "type": "object",
        "properties": {
            "beat_i": {"type": "integer", "enum": beat_enums},
            "image": {"type": "string"},
            "label": {"type": ["string", "null"]},
            "cast_ids": {
                "type": "array",
                "items": {"type": "string", "enum": cast_enums},
            },
        },
        "required": ["beat_i", "image"],
        "additionalProperties": False,
    }

    aside_schema = {
        "type": "object",
        "properties": {
            "beat_i": {"type": "integer", "enum": beat_enums},
            "kind": {"type": "string", "enum": ["thought", "label", "prop"]},
            "icon": {"type": ["string", "null"], "enum": [*icon_enums, None]},
            "text": {"type": ["string", "null"]},
            "cast_id": {"type": ["string", "null"], "enum": [*cast_enums, None]},
        },
        "required": ["beat_i", "kind"],
        "additionalProperties": False,
    }

    return {
        "type": "object",
        "properties": {
            "motifs": {"type": "array", "items": motif_schema},
            "metaphors": {"type": "array", "items": metaphor_schema},
            "asides": {"type": "array", "items": aside_schema},
        },
        "required": ["motifs", "metaphors", "asides"],
        "additionalProperties": False,
    }


def _check_name_leaks(
    path: str,
    text: str | None,
    bible: Bible,
    allowed_name: str | None = None,
) -> list[str]:
    """Check text contains no cast, place, or set piece names other than allowed_name."""
    if not text:
        return []
    errors: list[str] = []
    text_lower = text.casefold()

    names_to_check: list[str] = []
    for c in bible.cast:
        names_to_check.append(c.name)
    for p in bible.places:
        names_to_check.append(p.name)
    for sp in bible.set_pieces:
        names_to_check.append(sp.name)

    allowed_lower = allowed_name.casefold() if allowed_name else None

    for name in names_to_check:
        nl = name.casefold()
        if allowed_lower and nl == allowed_lower:
            continue
        # Check whole word match
        pattern = r"\b" + re.escape(nl) + r"\b"
        if re.search(pattern, text_lower):
            errors.append(
                f"{path}: contains the name '{name}' — "
                "cast, place, and set-piece names are not allowed"
            )
    return errors


def validate_director_plan(
    data: dict[str, Any],
    ctx: DirectorContext,
) -> tuple[dict[str, Any], list[str]]:
    """Validate director plan against the 7 validators of design_styles.md §3.3."""
    errors: list[str] = []
    num_beats = len(ctx.beats)
    expected_metaphors, expected_asides = compute_director_counts(num_beats)

    motifs_raw = data.get("motifs", [])
    metaphors_raw = data.get("metaphors", [])
    asides_raw = data.get("asides", [])

    if not isinstance(motifs_raw, list):
        errors.append("motifs: must be a list")
        motifs_raw = []
    if not isinstance(metaphors_raw, list):
        errors.append("metaphors: must be a list")
        metaphors_raw = []
    if not isinstance(asides_raw, list):
        errors.append("asides: must be a list")
        asides_raw = []

    # Counts
    if len(motifs_raw) < 1 or len(motifs_raw) > 3:
        errors.append(f"motifs: provide 1 to 3 motifs (got {len(motifs_raw)})")
    if len(metaphors_raw) != expected_metaphors:
        errors.append(
            f"metaphors: expected exactly {expected_metaphors} metaphors (got {len(metaphors_raw)})"
        )
    if len(asides_raw) != expected_asides:
        errors.append(f"asides: expected exactly {expected_asides} asides (got {len(asides_raw)})")

    valid_cast_ids = {c.id for c in ctx.bible.cast}
    valid_set_piece_ids = {sp.id for sp in ctx.bible.set_pieces}
    valid_icon_names = set(get_args(IconName))

    beat_metaphors: dict[int, list[int]] = {}
    beat_payoffs: dict[int, list[int]] = {}
    beat_asides: dict[int, list[int]] = {}

    # 1. Validator 1: beat_i in 1..n-1
    for m_idx, m in enumerate(metaphors_raw):
        b = m.get("beat_i")
        if b is None or not isinstance(b, int) or b < 1 or b >= num_beats:
            errors.append(
                f"metaphors[{m_idx}].beat_i: beat {b} is invalid — must be in 1 to {num_beats - 1}"
            )
        else:
            beat_metaphors.setdefault(b, []).append(m_idx)

    for a_idx, a in enumerate(asides_raw):
        b = a.get("beat_i")
        if b is None or not isinstance(b, int) or b < 1 or b >= num_beats:
            errors.append(
                f"asides[{a_idx}].beat_i: beat {b} is invalid — must be in 1 to {num_beats - 1}"
            )
        else:
            beat_asides.setdefault(b, []).append(a_idx)

    # 3. Validator 3: Each motif
    for m_idx, motif in enumerate(motifs_raw):
        m_name = motif.get("name", "")
        sp_id = motif.get("set_piece_id")
        icon = motif.get("icon")
        appearances = motif.get("appearances", [])

        # Validator 5: motif name checks
        if not isinstance(m_name, str) or not m_name.strip():
            errors.append(f"motifs[{m_idx}].name: name is required")
        else:
            if count_words(m_name) > 4:
                errors.append(
                    f"motifs[{m_idx}].name: '{m_name}' has {count_words(m_name)} words, "
                    "limit 4 — rewrite it shorter"
                )
            if any(c.isdigit() for c in m_name):
                errors.append(
                    f"motifs[{m_idx}].name: contains digits ('{m_name}') — numbers are not allowed"
                )
            if any(c in "\"“”'" for c in m_name):
                errors.append(
                    f"motifs[{m_idx}].name: contains quotation marks — quotes are not allowed"
                )
            errors.extend(text_complete_errors(f"motifs[{m_idx}].name", m_name))
            errors.extend(internal_id_errors(f"motifs[{m_idx}].name", m_name, ctx.bible))
            # Name leak check
            allowed_sp_name = None
            if sp_id and sp_id in valid_set_piece_ids:
                sp_obj = next((sp for sp in ctx.bible.set_pieces if sp.id == sp_id), None)
                if sp_obj:
                    allowed_sp_name = sp_obj.name
            errors.extend(
                _check_name_leaks(f"motifs[{m_idx}].name", m_name, ctx.bible, allowed_sp_name)
            )

        # Validator 7: motif set_piece_id / icon
        if sp_id is not None and sp_id not in valid_set_piece_ids:
            errors.append(f"motifs[{m_idx}].set_piece_id: set piece '{sp_id}' not found in bible")
        if icon is not None and icon not in valid_icon_names:
            errors.append(f"motifs[{m_idx}].icon: '{icon}' is not an allowed icon name")
        if not sp_id and not icon:
            errors.append(f"motifs[{m_idx}]: motif requires an icon or a set_piece_id")

        if not isinstance(appearances, list):
            errors.append(f"motifs[{m_idx}].appearances: must be a list")
            continue

        payoffs = [a for a in appearances if a.get("role") == "payoff"]
        plants = [a for a in appearances if a.get("role") == "plant"]
        echoes = [a for a in appearances if a.get("role") == "echo"]

        if len(payoffs) != 1:
            errors.append(
                f"motifs[{m_idx}].appearances: motif must have exactly one payoff "
                f"(got {len(payoffs)})"
            )
        if len(plants) < 1:
            errors.append(
                f"motifs[{m_idx}].appearances: motif must have at least 1 plant (got {len(plants)})"
            )
        if len(echoes) > 4:
            errors.append(f"motifs[{m_idx}].appearances: motif has {len(echoes)} echoes, limit 4")

        seen_beats: set[int] = set()
        payoff_beat: int | None = payoffs[0].get("beat_i") if payoffs else None

        for a_idx, app in enumerate(appearances):
            b = app.get("beat_i")
            role = app.get("role")
            if b is None or not isinstance(b, int) or b < 1 or b >= num_beats:
                errors.append(
                    f"motifs[{m_idx}].appearances[{a_idx}].beat_i: beat {b} is invalid — "
                    f"must be in 1 to {num_beats - 1}"
                )
                continue

            if b in seen_beats:
                errors.append(f"motifs[{m_idx}].appearances: duplicate appearance on beat {b}")
            seen_beats.add(b)

            if role == "payoff":
                beat_payoffs.setdefault(b, []).append(m_idx)
            elif role == "plant":
                if payoff_beat is not None and payoff_beat - b < 3:
                    errors.append(
                        f"motifs[{m_idx}].appearances: the payoff (beat {payoff_beat}) "
                        f"must come at least 3 beats after every plant (beat {b})"
                    )
            elif role == "echo":
                if payoff_beat is not None and b >= payoff_beat:
                    errors.append(
                        f"motifs[{m_idx}].appearances: echo on beat {b} "
                        f"must come before the payoff (beat {payoff_beat})"
                    )

    # 2. Validator 2: One directive per beat
    # at most one metaphor, one payoff, one aside; never both metaphor and payoff
    for b in range(1, num_beats):
        num_m = len(beat_metaphors.get(b, []))
        num_p = len(beat_payoffs.get(b, []))
        num_a = len(beat_asides.get(b, []))

        if num_m > 1:
            errors.append(
                f"metaphors: beat {b} has {num_m} metaphors — at most one allowed per beat"
            )
        if num_p > 1:
            errors.append(f"motifs: beat {b} has {num_p} payoffs — at most one allowed per beat")
        if num_a > 1:
            errors.append(f"asides: beat {b} has {num_a} asides — at most one allowed per beat")
        if num_m >= 1 and num_p >= 1:
            errors.append(f"beat {b}: cannot have both a metaphor and a payoff")

    # 4. Validator 4: Quoted speech stays
    for b, m_indices in beat_metaphors.items():
        if b < num_beats and QUOTED.search(ctx.beats[b].text):
            errors.append(
                f"metaphors[{m_indices[0]}]: beat {b} contains quoted speech "
                "— metaphors may not sit on quoted beats"
            )

    for b, p_indices in beat_payoffs.items():
        if b < num_beats and QUOTED.search(ctx.beats[b].text):
            errors.append(
                f"motifs[{p_indices[0]}].appearances: payoff on beat {b} contains quoted speech "
                "— payoffs may not sit on quoted beats"
            )

    # 5. Validator 5 & 6 & 7: Metaphors details
    for m_idx, m in enumerate(metaphors_raw):
        image = m.get("image", "")
        label = m.get("label")
        cast_ids = m.get("cast_ids", [])

        # Validator 6: image
        if not isinstance(image, str) or not image.strip():
            errors.append(f"metaphors[{m_idx}].image: image description is required")
        else:
            if count_words(image) > 25:
                errors.append(
                    f"metaphors[{m_idx}].image: {count_words(image)} words, limit 25 "
                    "— rewrite it shorter"
                )
            if any(c in "\"“”'" for c in image):
                errors.append(
                    f"metaphors[{m_idx}].image: contains quotation marks — quotes are not allowed"
                )
            if text_expected(image):
                errors.append(
                    f'metaphors[{m_idx}].image: asks for writing / lettering ("{image}") '
                    "— images must not contain text"
                )

        # Validator 5: label
        if label is not None:
            if not isinstance(label, str):
                errors.append(f"metaphors[{m_idx}].label: must be a string")
            else:
                if count_words(label) > 3:
                    errors.append(
                        f"metaphors[{m_idx}].label: '{label}' has {count_words(label)} words, "
                        "limit 3 — rewrite it shorter"
                    )
                if any(c.isdigit() for c in label):
                    errors.append(
                        f"metaphors[{m_idx}].label: contains digits ('{label}') "
                        "— numbers are not allowed"
                    )
                if any(c in "\"“”'" for c in label):
                    errors.append(
                        f"metaphors[{m_idx}].label: contains quotation marks — "
                        "quotes are not allowed"
                    )
                errors.extend(text_complete_errors(f"metaphors[{m_idx}].label", label))
                errors.extend(internal_id_errors(f"metaphors[{m_idx}].label", label, ctx.bible))
                errors.extend(_check_name_leaks(f"metaphors[{m_idx}].label", label, ctx.bible))

        # Validator 7: cast_ids
        if isinstance(cast_ids, list):
            if len(cast_ids) > 2:
                errors.append(
                    f"metaphors[{m_idx}].cast_ids: at most 2 cast avatars allowed, "
                    f"got {len(cast_ids)}"
                )
            for cid in cast_ids:
                if cid not in valid_cast_ids:
                    errors.append(f"metaphors[{m_idx}].cast_ids: cast '{cid}' not found in bible")
        else:
            errors.append(f"metaphors[{m_idx}].cast_ids: must be a list")

    # 5. Validator 5 & 7: Asides details
    for a_idx, a in enumerate(asides_raw):
        kind = a.get("kind")
        icon = a.get("icon")
        text = a.get("text")
        cid = a.get("cast_id")

        if kind == "thought":
            if not cid or cid not in valid_cast_ids:
                errors.append(f"asides[{a_idx}]: thought aside requires a valid cast_id")
            if not icon and not (text and isinstance(text, str) and text.strip()):
                errors.append(f"asides[{a_idx}]: a thought needs an icon or text")
        elif kind == "prop":
            if not icon or icon not in valid_icon_names:
                errors.append(f"asides[{a_idx}]: prop aside requires an icon from the allowed list")
        elif kind == "label":
            if not text or not isinstance(text, str) or not text.strip():
                errors.append(f"asides[{a_idx}]: label aside requires text")
        else:
            errors.append(f"asides[{a_idx}].kind: unknown aside kind '{kind}'")

        if text is not None:
            if not isinstance(text, str):
                errors.append(f"asides[{a_idx}].text: must be a string")
            else:
                if count_words(text) > 3:
                    errors.append(
                        f"asides[{a_idx}].text: '{text}' has {count_words(text)} words, "
                        "limit 3 — rewrite it shorter"
                    )
                if any(c.isdigit() for c in text):
                    errors.append(
                        f"asides[{a_idx}].text: contains digits ('{text}') "
                        "— numbers are not allowed"
                    )
                if any(c in "\"“”'" for c in text):
                    errors.append(
                        f"asides[{a_idx}].text: contains quotation marks — quotes are not allowed"
                    )
                errors.extend(text_complete_errors(f"asides[{a_idx}].text", text))
                errors.extend(internal_id_errors(f"asides[{a_idx}].text", text, ctx.bible))
                errors.extend(_check_name_leaks(f"asides[{a_idx}].text", text, ctx.bible))

        if icon is not None and icon not in valid_icon_names:
            errors.append(f"asides[{a_idx}].icon: '{icon}' is not an allowed icon name")

        if cid is not None and cid not in valid_cast_ids:
            errors.append(f"asides[{a_idx}].cast_id: cast '{cid}' not found in bible")

    return data, errors


def plan_director(
    beats: list[Beat],
    bible: Bible,
    backend: LLMBackend,
) -> tuple[DirectorPlan | None, list[Attempt]]:
    """Plan motifs, metaphors, and asides for the story with retry protocol.

    Returns (plan, attempts). If all attempts fail, returns (None, attempts).
    """
    ctx = DirectorContext(beats=beats, bible=bible)
    prompt_path = Path(__file__).resolve().parent / "prompts" / "director.md"
    prompt_tmpl = prompt_path.read_text(encoding="utf-8")

    expected_metaphors, expected_asides = compute_director_counts(len(beats))
    compact_bible = _build_compact_bible(bible)
    beats_text = "\n".join(f"[{b.i}] {b.text}" for b in beats)

    user_content = prompt_tmpl.format(
        num_beats=len(beats),
        max_beat_i=len(beats) - 1,
        expected_metaphors=expected_metaphors,
        expected_asides=expected_asides,
        compact_bible=compact_bible,
        icon_block=ICONS_PROMPT_BLOCK,
        beats_text=beats_text,
    )

    schema = build_director_schema(beats, bible)
    facing_schema = llm_facing_schema(schema)

    def validate_fn(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        return validate_director_plan(raw, ctx)

    result, attempts = run_with_retries(
        backend,
        stage="director",
        system=DIRECTOR_SYSTEM_PROMPT,
        user=user_content,
        schema=facing_schema,
        validate=validate_fn,
        max_attempts=3,
        num_predict=1536,
        temperature=0.3,
    )

    if result is None:
        return None, attempts

    # Parse into typed DirectorPlan
    try:
        plan = DirectorPlan(
            motifs=[MotifDirective.model_validate(m) for m in result.get("motifs", [])],
            metaphors=[MetaphorDirective.model_validate(m) for m in result.get("metaphors", [])],
            asides=[AsideDirective.model_validate(a) for a in result.get("asides", [])],
            license_dropped=[],
            overlay_dropped=[],
        )
        return plan, attempts
    except Exception:
        # Pydantic parsing failed, return None
        return None, attempts

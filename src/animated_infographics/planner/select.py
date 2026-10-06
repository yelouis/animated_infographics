"""Template selection planning and deterministic rule repairs."""

import math
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from animated_infographics.contracts.director import DirectorPlan
from animated_infographics.contracts.models import (
    Beat,
    Bible,
    RuleRepair,
    Transcript,
)
from animated_infographics.contracts.templates import (
    PICTURE_TEMPLATES,
    REGISTRY,
    REPLACEABLE_TEMPLATES,
)
from animated_infographics.planner.llm import LLMBackend, run_with_retries
from animated_infographics.planner.rhythm import QUOTED, rhythm_target


class Choice(BaseModel):
    """Template choice for a single scene/beat."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    beat_i: int
    primary: str
    alternate: str
    rhythm_id: str | None = None


def allowed_templates(bible: Bible) -> list[str]:
    """Compute the list of allowed templates based on bible contents.

    Per design_planner.md §4:
    - character_intro, emotion_beat, dialogue: cast has >= 1 member
    - relationship_map: cast has >= 2 members
    - location: places non-empty
    - set_piece: set_pieces non-empty
    - map_focus: some place has non-null lat/lon
    - title_card: never offered (beat 0 only)
    - all others: always
    """
    templates = [
        "kinetic_quote",
        "stat_callout",
        "icon_list",
        "reveal",
        "cause_effect",
        "comparison",
        "text_thread",
        "timeline",
    ]
    if len(bible.cast) >= 1:
        templates.extend(["character_intro", "emotion_beat", "dialogue"])
    if len(bible.cast) >= 2:
        templates.append("relationship_map")
    if len(bible.places) >= 1:
        templates.append("location")
    if len(bible.set_pieces) >= 1:
        templates.append("set_piece")
    if any(p.lat is not None and p.lon is not None for p in bible.places):
        templates.append("map_focus")

    return sorted(templates)


def apply_rules(
    choices: list[Choice],
    n_scenes: int,
    beats: Sequence[Beat] | None = None,
    bible: Bible | None = None,
    director_plan: DirectorPlan | None = None,
    profile: str = "video",
) -> tuple[list[Choice], list[RuleRepair]]:
    """Apply deterministic rules R1, R8, R6, R2, R4, R5, R7 to template choices in order.

    Per design_planner.md §4:
    R1: Scene 0 is not title_card / later scene is title_card -> Force / replace with alternate
    R8: Creative style: director metaphors and motif payoffs
    R6: More than one timeline or comparison in video -> later ones -> alternate or kinetic_quote
    R2: Two consecutive scenes share template (except dialogue, text_thread) ->
        second -> alternate; if that repeats -> kinetic_quote. R2 never rewrites an R8 scene.
    (R3 applied after props)
    R4: reveal > 2 times -> later ones -> alternate
    R5: kinetic_quote > ceil(0.30 * n_scenes) times (LLM primaries) ->
        excess (latest first) -> alternate
    R7: Reaction-shot rhythm: two worded scenes, then replaceable scene -> picture

    Presentation profile: R2, R6, and R7 are OFF. R1 is OFF (points never forced to title_card).
    """
    res = list(choices)
    repairs: list[RuleRepair] = []

    if not res:
        return (res, repairs)

    is_presentation = profile == "presentation"

    # R1: Scene 0 is title_card; later scenes are not (video profile only)
    if not is_presentation:
        if res[0].primary != "title_card":
            repairs.append(
                RuleRepair(rule="R1", scene="s000", to="title_card", **{"from": res[0].primary})
            )
            res[0] = Choice(beat_i=0, primary="title_card", alternate=res[0].alternate)

        for i in range(1, len(res)):
            if res[i].primary == "title_card":
                target = res[i].alternate if res[i].alternate != "title_card" else "kinetic_quote"
                repairs.append(
                    RuleRepair(rule="R1", scene=f"s{i:03d}", to=target, **{"from": "title_card"})
                )
                res[i] = Choice(beat_i=i, primary=target, alternate="kinetic_quote")

    # R8: Director metaphors and motif payoffs (creative style)
    r8_scenes: set[int] = set()
    if director_plan is not None:
        # Metaphors
        for met in director_plan.metaphors:
            b_idx = met.beat_i
            if 0 < b_idx < len(res):
                orig_prim = res[b_idx].primary
                if orig_prim != "metaphor":
                    repairs.append(
                        RuleRepair(
                            rule="R8", scene=f"s{b_idx:03d}", to="metaphor", **{"from": orig_prim}
                        )
                    )
                res[b_idx] = Choice(
                    beat_i=b_idx,
                    primary="metaphor",
                    alternate=orig_prim,
                )
                r8_scenes.add(b_idx)

        # Motifs payoff
        for motif in director_plan.motifs:
            for app in motif.appearances:
                if app.role == "payoff":
                    b_idx = app.beat_i
                    if 0 < b_idx < len(res):
                        orig_prim = res[b_idx].primary
                        if orig_prim != "callback":
                            repairs.append(
                                RuleRepair(
                                    rule="R8",
                                    scene=f"s{b_idx:03d}",
                                    to="callback",
                                    **{"from": orig_prim},
                                )
                            )
                        res[b_idx] = Choice(
                            beat_i=b_idx,
                            primary="callback",
                            alternate=orig_prim,
                        )
                        r8_scenes.add(b_idx)

    # R6: More than one timeline or comparison in video (video profile only)
    if not is_presentation:
        for limit_tmpl in ("timeline", "comparison"):
            indices = [i for i, c in enumerate(res) if c.primary == limit_tmpl]
            if len(indices) > 1:
                for idx in indices[1:]:
                    alt = res[idx].alternate
                    target = alt if alt not in (limit_tmpl, "title_card") else "kinetic_quote"
                    repairs.append(
                        RuleRepair(
                            rule="R6",
                            scene=f"s{idx:03d}",
                            to=target,
                            **{"from": limit_tmpl},
                        )
                    )
                    res[idx] = Choice(beat_i=idx, primary=target, alternate=res[idx].alternate)

    # R2: Consecutive duplicates (except dialogue, text_thread) (video profile only)
    # R2 never rewrites an R8 scene: rewrite the other scene instead
    if not is_presentation:
        for i in range(1, len(res)):
            if res[i].primary == res[i - 1].primary and res[i].primary not in (
                "dialogue",
                "text_thread",
            ):
                rewrite_idx = (i - 1) if (i in r8_scenes and (i - 1) not in r8_scenes) else i
                if rewrite_idx in r8_scenes:
                    continue

                prev = res[rewrite_idx - 1].primary if rewrite_idx > 0 else "title_card"
                next_t = res[rewrite_idx + 1].primary if rewrite_idx + 1 < len(res) else None
                alt = res[rewrite_idx].alternate
                if alt != prev and alt != "title_card" and alt != next_t:
                    new_prim = alt
                elif alt != prev and alt != "title_card":
                    new_prim = alt
                else:
                    new_prim = "kinetic_quote"
                repairs.append(
                    RuleRepair(
                        rule="R2",
                        scene=f"s{rewrite_idx:03d}",
                        to=new_prim,
                        **{"from": res[rewrite_idx].primary},
                    )
                )
                res[rewrite_idx] = Choice(
                    beat_i=rewrite_idx, primary=new_prim, alternate=res[rewrite_idx].alternate
                )

    # R4: reveal at most 2 times
    reveal_indices = [i for i, c in enumerate(res) if c.primary == "reveal"]
    if len(reveal_indices) > 2:
        for idx in reveal_indices[2:]:
            alt = res[idx].alternate
            new_prim = alt if alt != "reveal" else "kinetic_quote"
            repairs.append(
                RuleRepair(rule="R4", scene=f"s{idx:03d}", to=new_prim, **{"from": "reveal"})
            )
            res[idx] = Choice(beat_i=idx, primary=new_prim, alternate=res[idx].alternate)

    # R5: kinetic_quote at most ceil(0.30 * n_scenes)
    max_kq = math.ceil(0.30 * n_scenes)
    kq_indices = [i for i, c in enumerate(res) if i > 0 and c.primary == "kinetic_quote"]
    if len(kq_indices) > max_kq:
        excess = len(kq_indices) - max_kq
        for idx in reversed(kq_indices):
            if excess <= 0:
                break
            alt = res[idx].alternate
            if alt != "kinetic_quote":
                repairs.append(
                    RuleRepair(rule="R5", scene=f"s{idx:03d}", to=alt, **{"from": "kinetic_quote"})
                )
                res[idx] = Choice(beat_i=idx, primary=alt, alternate=res[idx].alternate)
                excess -= 1

    # R7: Rhythm rule (reaction-shot rhythm) (video profile only)
    if not is_presentation and beats is not None and bible is not None:
        run = 1
        n = len(res)
        for i in range(1, n):
            t = res[i].primary
            beat_text = beats[i].text if i < len(beats) else ""
            if run >= 2 and t in REPLACEABLE_TEMPLATES and not QUOTED.search(beat_text):
                prev_t = res[i - 1].primary
                next_t = res[i + 1].primary if i + 1 < n else None
                rhythm_cand = rhythm_target(beat_text, bible, prev=prev_t, next=next_t)
                if rhythm_cand is not None:
                    tmpl, eid = rhythm_cand
                    res[i] = Choice(beat_i=i, primary=tmpl, alternate=t, rhythm_id=eid)
                    repairs.append(RuleRepair(rule="R7", scene=f"s{i:03d}", to=tmpl, **{"from": t}))
            run = 0 if res[i].primary in PICTURE_TEMPLATES else run + 1

    return (res, repairs)


def _build_compact_bible(bible: Bible) -> str:
    parts = [f"Title: {bible.title} ({bible.genre})"]
    if bible.cast:
        cast_strs = [f"- {c.id}: {c.name} ({c.role})" for c in bible.cast]
        parts.append("Cast:\n" + "\n".join(cast_strs))
    if bible.places:
        places_strs = [
            f"- {p.id}: {p.name} ({p.country_iso3 or 'fictional'})" for p in bible.places
        ]
        parts.append("Places:\n" + "\n".join(places_strs))
    if bible.set_pieces:
        sp_strs = [f"- {sp.id}: {sp.name}" for sp in bible.set_pieces]
        parts.append("Set Pieces:\n" + "\n".join(sp_strs))
    return "\n\n".join(parts)


def _make_validate_choices(
    target_beats: Sequence[Beat], allowed: list[str]
) -> Callable[[dict[str, Any]], tuple[dict[str, Any], list[str]]]:
    def validate_choices(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        errs: list[str] = []
        raw_choices = raw.get("choices")
        if not isinstance(raw_choices, list):
            return (raw, ["Missing or non-array 'choices' in response"])
        if len(raw_choices) != len(target_beats):
            return (raw, [f"Expected {len(target_beats)} choices, got {len(raw_choices)}"])

        for idx, c in enumerate(raw_choices):
            if not isinstance(c, dict):
                errs.append(f"Choice {idx} is not an object")
                continue
            expected_beat_i = target_beats[idx].i
            beat_i = c.get("beat_i")
            prim = c.get("primary")
            alt = c.get("alternate")
            if beat_i != expected_beat_i:
                errs.append(f"Choice {idx} beat_i={beat_i}, expected {expected_beat_i}")
            if prim not in allowed:
                errs.append(f"Choice {idx} primary '{prim}' not in allowed templates")
            if alt not in allowed:
                errs.append(f"Choice {idx} alternate '{alt}' not in allowed templates")
            if prim == alt:
                errs.append(f"Choice {idx} has primary == alternate ('{prim}'). They must differ.")
        return (raw, errs)

    return validate_choices


def plan_template_selection(
    transcript: Transcript,
    beats: Sequence[Beat],
    bible: Bible,
    backend: LLMBackend,
    director_plan: DirectorPlan | None = None,
    profile: str = "video",
) -> tuple[list[Choice], list[RuleRepair], int, int]:
    """Plan visual templates for all narration beats using LLM in 6-beat windows with rule repairs.

    Returns:
        (choices, rule_repairs, llm_calls, llm_cache_hits)
    """
    n_beats = len(beats)
    if n_beats == 0:
        return ([], [], 0, 0)

    is_presentation = profile == "presentation"

    # Beat 0 is title_card for video profile; presentation plans all beats from 0
    all_choices: list[Choice] = (
        [] if is_presentation else [Choice(beat_i=0, primary="title_card", alternate="title_card")]
    )

    if n_beats == 1 and not is_presentation:
        repaired, repairs = apply_rules(
            all_choices, 1, beats, bible, director_plan=director_plan, profile=profile
        )
        return (repaired, repairs, 0, 0)

    allowed = allowed_templates(bible)
    template_menu = "\n".join(
        f"- {name}: {REGISTRY[name].use_when}" for name in allowed if name in REGISTRY
    )
    compact_bible = _build_compact_bible(bible)

    prompt_path = Path(__file__).resolve().parent / "prompts" / "select.md"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    total_calls = 0
    total_cache_hits = 0

    schema = {
        "type": "object",
        "properties": {
            "choices": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "beat_i": {"type": "integer"},
                        "primary": {"type": "string", "enum": allowed},
                        "alternate": {"type": "string", "enum": allowed},
                    },
                    "required": ["beat_i", "primary", "alternate"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["choices"],
        "additionalProperties": False,
    }

    # Process beats in windows of 6
    window_size = 6
    start_offset = 0 if is_presentation else 1
    for w_start in range(start_offset, n_beats, window_size):
        w_end = min(w_start + window_size, n_beats)
        window_beats = beats[w_start:w_end]

        # Previous 2 beats' choices
        prev_slice = all_choices[-2:] if len(all_choices) >= 2 else all_choices
        prev_strs = [
            f"Beat {c.beat_i}: primary={c.primary}, alternate={c.alternate}" for c in prev_slice
        ]
        prev_text = "\n".join(prev_strs) if prev_strs else "None (start of video)"

        beats_text = "\n".join(f"[Beat {b.i}]: {b.text}" for b in window_beats)

        user_content = prompt_template.format(
            compact_bible=compact_bible,
            previous_choices=prev_text,
            template_menu=template_menu,
            window_beats=beats_text,
        )

        system = (
            "You are an expert storyboard planner for animated educational explainer videos. "
            "Select the best visual infographic templates for each narration beat."
        )

        result, attempts = run_with_retries(
            backend,
            stage="select",
            system=system,
            user=user_content,
            schema=schema,
            validate=_make_validate_choices(window_beats, allowed),
            max_attempts=3,
        )
        total_calls += len(attempts)

        window_choices: list[Choice]
        if result is not None:
            window_choices = [
                Choice(
                    beat_i=window_beats[idx].i,
                    primary=c["primary"],
                    alternate=c["alternate"],
                )
                for idx, c in enumerate(result["choices"])
            ]
        else:
            window_choices = [
                Choice(beat_i=b.i, primary="kinetic_quote", alternate="kinetic_quote")
                for b in window_beats
            ]

        all_choices.extend(window_choices)

    repaired_choices, rule_repairs = apply_rules(
        all_choices, n_beats, beats, bible, director_plan=director_plan, profile=profile
    )
    return (repaired_choices, rule_repairs, total_calls, total_cache_hits)

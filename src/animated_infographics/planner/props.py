"""Props planning with fallback ladder, schema narrowing, and deterministic repairs."""

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from animated_infographics.contracts.models import (
    Beat,
    Bible,
    CauseEffectScene,
    CharacterIntroScene,
    ComparisonScene,
    CriticReport,
    DialogueScene,
    EmotionBeatScene,
    IconListScene,
    KineticQuoteProps,
    KineticQuoteScene,
    LocationScene,
    MapFocusScene,
    PlanReport,
    PlanReportScene,
    RelationshipMapScene,
    RevealScene,
    RuleRepair,
    Scene,
    SetPieceScene,
    StatCalloutScene,
    Storyboard,
    TextThreadScene,
    TimelineSceneModel,
    TitleCardProps,
    TitleCardScene,
    Transcript,
)
from animated_infographics.contracts.templates import REGISTRY, TextThreadProps
from animated_infographics.planner.critic import (
    build_critic_request,
    critic_mismatches,
    format_disagreement_message,
    needs_critic,
    resolve_contact,
    validate_critic_answer,
)
from animated_infographics.planner.llm import LLMBackend, run_with_retries
from animated_infographics.planner.select import plan_template_selection
from animated_infographics.planner.validate import (
    PlanContext,
    normalize_props_text,
    validate_scene,
)

SCENE_CLASS_MAP: dict[str, type[Scene]] = {
    "title_card": TitleCardScene,
    "kinetic_quote": KineticQuoteScene,
    "stat_callout": StatCalloutScene,
    "icon_list": IconListScene,
    "reveal": RevealScene,
    "cause_effect": CauseEffectScene,
    "comparison": ComparisonScene,
    "character_intro": CharacterIntroScene,
    "dialogue": DialogueScene,
    "text_thread": TextThreadScene,
    "emotion_beat": EmotionBeatScene,
    "relationship_map": RelationshipMapScene,
    "location": LocationScene,
    "set_piece": SetPieceScene,
    "map_focus": MapFocusScene,
    "timeline": TimelineSceneModel,
}


def build_deterministic_kinetic_quote(scene_id: str, beat_i: int, beat: Beat) -> KineticQuoteScene:
    """Build a deterministic kinetic_quote scene guaranteed to pass verbatim validation.

    Per design_planner.md §5:
    text = beat.text if <= 90 chars, else cut at last word boundary <= 89, followed by …
    emphasis = []
    attribution_cast_id = null
    """
    raw_text = beat.text.strip()
    if len(raw_text) <= 90:
        text = raw_text
    else:
        clipped = raw_text[:89]
        last_space = clipped.rfind(" ")
        if last_space != -1:
            text = clipped[:last_space] + "…"
        else:
            text = clipped + "…"

    return KineticQuoteScene(
        id=scene_id,
        beat_i=beat_i,
        template="kinetic_quote",
        props=KineticQuoteProps(
            text=text,
            emphasis=[],
            attribution_cast_id=None,
        ),
        mute_sfx=False,
        rationale="deterministic fallback",
    )


def build_deterministic_title_card(scene_id: str, beat_i: int, bible: Bible) -> TitleCardScene:
    """Build deterministic title_card for scene 0.

    Per design_planner.md §5:
    title = bible.title
    subtitle = null
    icon = first set piece's icon, else first place's icon, else null
    """
    icon = None
    if bible.set_pieces and bible.set_pieces[0].icon:
        icon = bible.set_pieces[0].icon
    elif bible.places and bible.places[0].icon:
        icon = bible.places[0].icon

    return TitleCardScene(
        id=scene_id,
        beat_i=beat_i,
        template="title_card",
        props=TitleCardProps(
            title=bible.title,
            subtitle=None,
            icon=icon,
        ),
        mute_sfx=False,
        rationale="deterministic title card",
    )


def narrow_schema_references(schema: dict[str, Any], template: str, bible: Bible) -> dict[str, Any]:
    """Recursively narrow reference ID patterns in props schema to enums of IDs in this bible."""
    if not isinstance(schema, dict):
        return schema

    res: dict[str, Any] = {}
    for k, v in schema.items():
        if isinstance(v, dict):
            res[k] = narrow_schema_references(v, template, bible)
        elif isinstance(v, list):
            res[k] = [
                narrow_schema_references(x, template, bible) if isinstance(x, dict) else x
                for x in v
            ]
        else:
            res[k] = v

    if "pattern" in res:
        pat = res["pattern"]
        if pat == r"^c[1-8]$" and bible.cast:
            del res["pattern"]
            res["enum"] = [c.id for c in bible.cast]
        elif pat == r"^p[1-4]$" and bible.places:
            del res["pattern"]
            if template == "map_focus":
                geo_places = [p.id for p in bible.places if p.lat is not None and p.lon is not None]
                res["enum"] = geo_places if geo_places else [p.id for p in bible.places]
            else:
                res["enum"] = [p.id for p in bible.places]
        elif pat == r"^v[1-3]$" and bible.set_pieces:
            del res["pattern"]
            res["enum"] = [sp.id for sp in bible.set_pieces]

    return res


def _format_writing_rules_and_slots(template_name: str) -> tuple[str, str]:
    spec = REGISTRY.get(template_name)
    if not spec:
        return ("", "")
    rules = "\n".join(f"- {r}" for r in spec.writing_rules)
    slots = "\n".join(
        f"- {sname}: {s.font} {s.weight}, max_lines={s.max_lines}, box_width={s.box_width}"
        for sname, s in spec.slots.items()
    )
    return (rules, slots)


def _format_pydantic_validation_error(err: Mapping[str, Any]) -> str:
    """Format Pydantic error into a clear retry message.

    Per design_planner.md §1:
    Limits are enforced afterwards with the retry message naming the field and its limit
    ('props.caption: 61 characters, limit 48 — rewrite it shorter as a complete phrase').
    """
    loc = err.get("loc", ())
    path = "props"
    for part in loc:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}"

    if err.get("type") == "string_too_long":
        limit = err.get("ctx", {}).get("max_length")
        inp = err.get("input")
        length = len(inp) if isinstance(inp, str) else "?"
        return (
            f"{path}: {length} characters, limit {limit} — rewrite it shorter as a complete phrase"
        )

    msg = err.get("msg", str(err))
    return f"{path}: {msg}"


def plan_single_template_props(
    template_name: str,
    scene_id: str,
    beat_i: int,
    beat: Beat,
    prev_beat: Beat | None,
    next_beat: Beat | None,
    transcript: Transcript,
    bible: Bible,
    backend: LLMBackend,
    prompt_template: str,
    compact_bible: str,
    extra_user_prompt: str | None = None,
    max_attempts: int = 3,
) -> tuple[Scene | None, list[str], int]:
    """Attempt up to max_attempts tries to generate and validate props for a single template.

    Returns:
        (scene_or_none, errors_accumulated, attempts_made)
    """
    spec = REGISTRY.get(template_name)
    if not spec:
        return (None, [f"Unknown template: {template_name}"], 0)

    scene_cls = SCENE_CLASS_MAP[template_name]
    raw_schema = spec.props_model.model_json_schema()
    narrowed_schema = narrow_schema_references(raw_schema, template_name, bible)

    writing_rules, field_limits = _format_writing_rules_and_slots(template_name)

    prev_text = prev_beat.text if prev_beat else "None (start of story)"
    next_text = next_beat.text if next_beat else "None (end of story)"

    base_user_prompt = prompt_template.format(
        compact_bible=compact_bible,
        prev_beat_text=prev_text,
        this_beat_text=beat.text,
        next_beat_text=next_text,
        template_name=template_name,
        use_when=spec.use_when,
        writing_rules=writing_rules,
        field_limits=field_limits,
    )
    if extra_user_prompt:
        base_user_prompt += f"\n\n{extra_user_prompt}"

    system = (
        "You are an expert storyboard planner for animated educational explainer videos. "
        "Generate concrete, grounded props for this infographic scene."
    )

    ctx = PlanContext(transcript=transcript, bible=bible, beat=beat)

    def validate_props(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        try:
            clean_raw = normalize_props_text(template_name, raw)
            props_instance = spec.props_model.model_validate(clean_raw)
            if template_name == "text_thread" and isinstance(props_instance, TextThreadProps):
                if props_instance.contact_cast_id is None:
                    matched_id = resolve_contact(props_instance, bible)
                    if matched_id is not None:
                        props_instance = props_instance.model_copy(
                            update={"contact_cast_id": matched_id}
                        )
                        clean_raw["contact_cast_id"] = matched_id
            scene_factory: Any = scene_cls
            candidate_scene: Scene = scene_factory(
                id=scene_id,
                beat_i=beat_i,
                template=template_name,
                props=props_instance,
                mute_sfx=False,
                rationale="llm planned",
            )
            val_errors = validate_scene(candidate_scene, ctx)
            return (clean_raw, val_errors)
        except ValidationError as e:
            formatted_errs = [_format_pydantic_validation_error(err) for err in e.errors()]
            return (raw, formatted_errs)
        except Exception as e:
            return (raw, [f"Failed to instantiate scene: {e}"])

    result, attempts = run_with_retries(
        backend,
        stage="props",
        system=system,
        user=base_user_prompt,
        schema=narrowed_schema,
        validate=validate_props,
        max_attempts=max_attempts,
    )

    if result is not None:
        props_instance = spec.props_model.model_validate(result)
        if template_name == "text_thread" and isinstance(props_instance, TextThreadProps):
            if props_instance.contact_cast_id is None:
                matched_id = resolve_contact(props_instance, bible)
                if matched_id is not None:
                    props_instance = props_instance.model_copy(
                        update={"contact_cast_id": matched_id}
                    )
        scene_factory: Any = scene_cls
        scene: Scene = scene_factory(
            id=scene_id,
            beat_i=beat_i,
            template=template_name,
            props=props_instance,
            mute_sfx=False,
            rationale="llm planned",
        )
        return (scene, [], len(attempts))

    last_errors = attempts[-1].errors if attempts else ["All attempts failed"]
    return (None, last_errors, len(attempts))


def _evaluate_scene_critic(
    candidate_scene: Scene,
    beat: Beat,
    prev_beat: Beat | None,
    next_beat: Beat | None,
    transcript: Transcript,
    bible: Bible,
    backend: LLMBackend,
    prompt_template: str,
    compact_bible: str,
    before_prev_beat: Beat | None = None,
) -> tuple[Scene, CriticReport, int]:
    """Run blind critic check on candidate scene if required per design_planner.md §11.

    Returns:
        (final_scene, critic_report, extra_llm_calls)
    """
    if not needs_critic(candidate_scene):
        return (
            candidate_scene,
            CriticReport(status="not_applicable", mismatches=[], changed=False),
            0,
        )

    system, user, schema = build_critic_request(
        candidate_scene,
        beat,
        prev_beat,
        next_beat,
        bible,
        before_prev_beat=before_prev_beat,
    )

    def validate_critic(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        return validate_critic_answer(candidate_scene, raw)

    critic_res, critic_attempts = run_with_retries(
        backend,
        stage="critic",
        system=system,
        user=user,
        schema=schema,
        validate=validate_critic,
        max_attempts=3,
        num_predict=256,
        temperature=0.0,
    )
    critic_calls = len(critic_attempts)

    if critic_res is None:
        return (
            candidate_scene,
            CriticReport(status="unavailable", mismatches=[], changed=False),
            critic_calls,
        )

    mismatches = critic_mismatches(candidate_scene, critic_res, bible)
    if not mismatches:
        return (
            candidate_scene,
            CriticReport(status="agree", mismatches=[], changed=False),
            critic_calls,
        )

    # Disagreement: re-request same template's props with disagreement message
    disagreement_msg = format_disagreement_message(mismatches)
    retry_scene, retry_errors, retry_attempts = plan_single_template_props(
        candidate_scene.template,
        candidate_scene.id,
        candidate_scene.beat_i,
        beat,
        prev_beat,
        next_beat,
        transcript,
        bible,
        backend,
        prompt_template,
        compact_bible,
        extra_user_prompt=disagreement_msg,
        max_attempts=3,
    )
    extra_calls = critic_calls + retry_attempts

    if retry_scene is not None:
        changed = candidate_scene.props.model_dump() != retry_scene.props.model_dump()
        return (
            retry_scene,
            CriticReport(
                status="mismatch_retried",
                mismatches=mismatches,
                changed=changed,
                repair=None,
                retry_errors=[],
            ),
            extra_calls,
        )

    # Retry failed: check for deterministic tone repair
    if isinstance(candidate_scene, DialogueScene) and mismatches:
        parsed_indices: list[int] = []
        all_tone_vs_unknown = True
        for m in mismatches:
            match = re.match(r"^lines\[(\d+)\]\.tone: (.+) vs unknown$", m)
            if match:
                parsed_indices.append(int(match.group(1)))
            else:
                all_tone_vs_unknown = False
                break

        if all_tone_vs_unknown:
            new_lines = list(candidate_scene.props.lines)
            for l_idx in parsed_indices:
                new_lines[l_idx] = new_lines[l_idx].model_copy(update={"tone": "neutral"})
            repaired_props = candidate_scene.props.model_copy(update={"lines": new_lines})
            repaired_scene = candidate_scene.model_copy(update={"props": repaired_props})
            ctx = PlanContext(transcript=transcript, bible=bible, beat=beat)
            val_errs = validate_scene(repaired_scene, ctx)
            if not val_errs:
                changed = candidate_scene.props.model_dump() != repaired_scene.props.model_dump()
                return (
                    repaired_scene,
                    CriticReport(
                        status="mismatch_retried",
                        mismatches=mismatches,
                        changed=changed,
                        repair="tone_neutral",
                        retry_errors=retry_errors,
                    ),
                    extra_calls,
                )

    return (
        candidate_scene,
        CriticReport(
            status="mismatch_retried",
            mismatches=mismatches,
            changed=False,
            repair=None,
            retry_errors=retry_errors,
        ),
        extra_calls,
    )


def plan_storyboard(
    transcript: Transcript,
    beats: Sequence[Beat],
    bible: Bible,
    backend: LLMBackend,
) -> tuple[Storyboard, PlanReport]:
    """Execute complete storyboard planning: select -> props with fallback ladder -> rule repairs.

    Returns:
        (Storyboard, PlanReport)
    """
    n_beats = len(beats)
    if n_beats == 0:
        return (
            Storyboard(schema_version=1, aspect="9:16", scenes=[]),
            PlanReport(
                schema_version=1,
                model=getattr(backend, "model", "gemma4:26b"),
                llm_calls=0,
                llm_cache_hits=0,
                scenes=[],
                rule_repairs=[],
            ),
        )

    # 1. Template selection stage
    choices, select_repairs, select_calls, select_hits = plan_template_selection(
        transcript, beats, bible, backend
    )

    prompt_path = Path(__file__).resolve().parent / "prompts" / "props.md"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    from animated_infographics.planner.select import _build_compact_bible

    compact_bible = _build_compact_bible(bible)

    total_llm_calls = select_calls
    total_cache_hits = select_hits

    scenes: list[Scene] = []
    plan_report_scenes: list[PlanReportScene] = []
    all_repairs: list[RuleRepair] = list(select_repairs)

    # 2. Props stage per scene with fallback ladder
    for idx, beat in enumerate(beats):
        scene_id = f"s{idx:03d}"
        before_prev_beat = beats[idx - 2] if idx > 1 else None
        prev_beat = beats[idx - 1] if idx > 0 else None
        next_beat = beats[idx + 1] if idx + 1 < n_beats else None

        choice = choices[idx]
        prim_template = choice.primary
        alt_template = choice.alternate

        if idx == 0:
            # Beat 0 is always title_card
            t_scene = build_deterministic_title_card(scene_id, 0, bible)
            scenes.append(t_scene)
            plan_report_scenes.append(
                PlanReportScene(
                    id=scene_id,
                    primary="title_card",
                    alternate="title_card",
                    final_template="title_card",
                    fallback_level=0,
                    attempts=0,
                    errors=[],
                    critic=CriticReport(status="not_applicable", mismatches=[], changed=False),
                )
            )
            continue

        accumulated_errors: list[str] = []
        scene_result: Scene | None = None
        fallback_level: int = 0
        total_scene_attempts = 0

        # Attempt primary template
        p_scene, p_errs, p_attempts = plan_single_template_props(
            prim_template,
            scene_id,
            idx,
            beat,
            prev_beat,
            next_beat,
            transcript,
            bible,
            backend,
            prompt_template,
            compact_bible,
        )
        total_scene_attempts += p_attempts
        total_llm_calls += p_attempts

        if p_scene is not None:
            scene_result = p_scene
            fallback_level = 0
        else:
            accumulated_errors.extend(p_errs)
            # Attempt alternate template
            if alt_template != prim_template:
                a_scene, a_errs, a_attempts = plan_single_template_props(
                    alt_template,
                    scene_id,
                    idx,
                    beat,
                    prev_beat,
                    next_beat,
                    transcript,
                    bible,
                    backend,
                    prompt_template,
                    compact_bible,
                )
                total_scene_attempts += a_attempts
                total_llm_calls += a_attempts
                if a_scene is not None:
                    scene_result = a_scene
                    fallback_level = 1
                else:
                    accumulated_errors.extend(a_errs)

        if scene_result is not None:
            # Fallback level 0 or 1: check critic per §11
            scene_result, critic_report, extra_calls = _evaluate_scene_critic(
                scene_result,
                beat,
                prev_beat,
                next_beat,
                transcript,
                bible,
                backend,
                prompt_template,
                compact_bible,
                before_prev_beat=before_prev_beat,
            )
            total_llm_calls += extra_calls
        else:
            # Fallback level 2: deterministic kinetic_quote
            fallback_level = 2
            scene_result = build_deterministic_kinetic_quote(scene_id, idx, beat)
            critic_report = CriticReport(status="not_applicable", mismatches=[], changed=False)

        scenes.append(scene_result)
        plan_report_scenes.append(
            PlanReportScene(
                id=scene_id,
                primary=prim_template,
                alternate=alt_template,
                final_template=scene_result.template,
                fallback_level=fallback_level,  # type: ignore[arg-type]
                attempts=total_scene_attempts,
                errors=accumulated_errors,
                critic=critic_report,
            )
        )

    # 3. Apply Rule R3 (character_intro for same cast_id at most once)
    seen_intro_cast: set[str] = set()
    for idx, sc in enumerate(scenes):
        if sc.template == "character_intro":
            cast_id = sc.props.cast_id  # type: ignore[attr-defined]
            if cast_id in seen_intro_cast:
                # Need repair to alternate or fallback
                alt_template = choices[idx].alternate
                if alt_template == "character_intro":
                    alt_template = "kinetic_quote"

                new_scene: Scene | None = None
                if alt_template != "kinetic_quote":
                    a_scene, _, a_attempts = plan_single_template_props(
                        alt_template,
                        sc.id,
                        idx,
                        beats[idx],
                        beats[idx - 1] if idx > 0 else None,
                        beats[idx + 1] if idx + 1 < n_beats else None,
                        transcript,
                        bible,
                        backend,
                        prompt_template,
                        compact_bible,
                    )
                    total_llm_calls += a_attempts
                    new_scene = a_scene

                if new_scene is None:
                    new_scene = build_deterministic_kinetic_quote(sc.id, idx, beats[idx])

                all_repairs.append(
                    RuleRepair(
                        rule="R3",
                        scene=sc.id,
                        to=new_scene.template,
                        **{"from": "character_intro"},
                    )
                )
                if needs_critic(new_scene):
                    critic_scene, critic_report, c_calls = _evaluate_scene_critic(
                        new_scene,
                        beats[idx],
                        beats[idx - 1] if idx > 0 else None,
                        beats[idx + 1] if idx + 1 < n_beats else None,
                        transcript,
                        bible,
                        backend,
                        prompt_template,
                        compact_bible,
                        before_prev_beat=beats[idx - 2] if idx > 1 else None,
                    )
                    new_scene = critic_scene
                    total_llm_calls += c_calls
                else:
                    critic_report = CriticReport(
                        status="not_applicable", mismatches=[], changed=False
                    )

                scenes[idx] = new_scene
                # Update report scene
                old_rep = plan_report_scenes[idx]
                plan_report_scenes[idx] = PlanReportScene(
                    id=old_rep.id,
                    primary=old_rep.primary,
                    alternate=old_rep.alternate,
                    final_template=new_scene.template,
                    fallback_level=1 if new_scene.template == alt_template else 2,
                    attempts=old_rep.attempts,
                    errors=old_rep.errors,
                    critic=critic_report,
                )
            else:
                seen_intro_cast.add(cast_id)

    storyboard = Storyboard(schema_version=1, aspect="9:16", scenes=scenes)
    plan_report = PlanReport(
        schema_version=1,
        model=getattr(backend, "model", "gemma4:26b"),
        llm_calls=total_llm_calls,
        llm_cache_hits=total_cache_hits,
        scenes=plan_report_scenes,
        rule_repairs=all_repairs,
    )

    return (storyboard, plan_report)

"""Validation for storyboard scenes and whole plans against contracts, bible, and grounding."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from animated_infographics.contracts.models import (
    Beat,
    Bible,
    CauseEffectProps,
    CharacterIntroProps,
    ComparisonProps,
    DialogueProps,
    EmotionBeatProps,
    IconListProps,
    KineticQuoteProps,
    LocationProps,
    MapFocusProps,
    RelationshipMapProps,
    RevealProps,
    Scene,
    SetPieceProps,
    StatCalloutProps,
    Storyboard,
    TextThreadProps,
    TimelineProps,
    TitleCardProps,
    Transcript,
)
from animated_infographics.contracts.templates import REGISTRY, TextSlot, TimelineEvent
from animated_infographics.planner.grounding import (
    digits_grounded,
    is_kinetic_quote_grounded,
    is_stat_grounded,
)
from animated_infographics.textfit import fits

RELATIVE_TIME_LABELS: Final[frozenset[str]] = frozenset(
    {
        "today",
        "now",
        "present day",
        "that night",
        "that weekend",
        "the next day",
        "days later",
        "weeks later",
        "months later",
        "years later",
        "last spring",
        "last summer",
        "last fall",
        "last winter",
        "last year",
        "earlier",
        "later",
    }
)


def normalize_date_label(s: str) -> str:
    """Normalize date label by casefolding, collapsing whitespace, and stripping punctuation."""
    cleaned = re.sub(r"\s+", " ", s.casefold()).strip()
    return cleaned.rstrip(".,!:")


def timeline_label_errors(events: Sequence[TimelineEvent], transcript_text: str) -> list[str]:
    """Validate timeline date_labels per Issue 4 / Option A (design_planner.md §8).

    - (a) per label: must contain >= 1 digit run with digits_grounded true,
          OR its normalised form must be in RELATIVE_TIME_LABELS.
    - (b) normalised labels are pairwise distinct.
    - (c) first four-digit year per label (\\b(1[0-9]{3}|20[0-9]{2})\\b), in event order,
          is non-decreasing.
    """
    errors: list[str] = []

    # (a) Per-label check
    for idx, event in enumerate(events):
        norm_label = normalize_date_label(event.date_label)
        has_digits = bool(re.search(r"\d+", event.date_label))
        is_grounded_date = has_digits and digits_grounded(event.date_label, transcript_text)
        is_allowed_relative = norm_label in RELATIVE_TIME_LABELS

        if not (is_grounded_date or is_allowed_relative):
            errors.append(
                f'props.events[{idx}].date_label: "{event.date_label}" '
                "is not a date from the narration or an allowed phrase"
            )

    # (b) Pairwise distinct normalised labels
    seen_labels: set[str] = set()
    for event in events:
        norm_label = normalize_date_label(event.date_label)
        if norm_label in seen_labels:
            errors.append(f'props.events: date labels repeat ("{norm_label}")')
            break
        seen_labels.add(norm_label)

    # (c) First four-digit year per label is non-decreasing
    prev_year: int | None = None
    for event in events:
        m = re.search(r"\b(1[0-9]{3}|20[0-9]{2})\b", event.date_label)
        if m:
            cur_year = int(m.group(1))
            if prev_year is not None and cur_year < prev_year:
                errors.append(f"props.events: years go backwards ({prev_year} → {cur_year})")
                break
            prev_year = cur_year

    return errors


@dataclass(frozen=True)
class PlanContext:
    """Context required for validating storyboard scenes."""

    transcript: Transcript
    bible: Bible
    beat: Beat | None = None
    beats: Sequence[Beat] | None = None


def _check_slot(path: str, text: str | None, slot: TextSlot) -> list[str]:
    if not text:
        return []
    res = fits(text, slot)
    if not res.fits:
        return [f"{path}: {res.error}"]
    return []


def _format_stat_value(val: float, decimals: int) -> str:
    if decimals == 0:
        return f"{int(round(val)):,}"
    elif decimals == 1:
        return f"{val:,.1f}"
    else:
        return f"{val:,.2f}"


def validate_scene(scene: Scene, ctx: PlanContext) -> list[str]:
    """Validate a storyboard scene against schema, references, fit, and rules.

    Per design_planner.md §6:
    1. Schema: Pydantic validation (guaranteed if scene is instantiated, checked if dict/props)
    2. References: every cast_id, place_id, set_piece_id, and edge endpoint exists;
       map_focus markers' places have non-null geo.
    3. Text fit (§7).
    4. Grounding (§8) where the template declares it.
    5. Template-specific rules listed per template in design_templates.md.
    """
    errors: list[str] = []
    template = scene.template
    spec = REGISTRY.get(template)
    if not spec:
        return [f"template: unknown template '{template}'"]

    # Resolve beat text
    beat = ctx.beat
    if beat is None and ctx.beats is not None and 0 <= scene.beat_i < len(ctx.beats):
        beat = ctx.beats[scene.beat_i]
    beat_text = beat.text if beat else ""

    # Full transcript text for transcript-wide digit grounding
    full_transcript = " ".join(s.text for s in ctx.transcript.sentences)

    bible = ctx.bible
    cast_map = {c.id: c for c in bible.cast}
    places_map = {p.id: p for p in bible.places}
    set_pieces_map = {sp.id: sp for sp in bible.set_pieces}

    slots = spec.slots
    props = scene.props

    if isinstance(props, TitleCardProps):
        if scene.beat_i != 0:
            errors.append(f"props: title_card is only allowed at beat 0, got beat {scene.beat_i}")
        errors.extend(_check_slot("props.title", props.title, slots["title"]))
        errors.extend(_check_slot("props.subtitle", props.subtitle, slots["subtitle"]))

    elif isinstance(props, KineticQuoteProps):
        if props.attribution_cast_id and props.attribution_cast_id not in cast_map:
            errors.append(
                f"props.attribution_cast_id: cast '{props.attribution_cast_id}' not found in bible"
            )
        errors.extend(_check_slot("props.text", props.text, slots["text"]))
        # Grounding
        _, quote_errors = is_kinetic_quote_grounded(props.text, props.emphasis, beat_text)
        errors.extend(quote_errors)

    elif isinstance(props, StatCalloutProps):
        # Meaning rule (Issue 5 / Option A): currency symbols in suffix
        if any(sym in props.suffix for sym in ("$", "£", "€")):
            errors.append("props.suffix: currency symbols belong in prefix")
        # Rendered value line
        rendered_val = props.prefix + _format_stat_value(props.value, props.decimals)
        if props.display_scale != "none":
            rendered_val += f" {props.display_scale}"
        errors.extend(_check_slot("props.value", rendered_val, slots["value"]))
        errors.extend(_check_slot("props.suffix", props.suffix, slots["suffix"]))
        errors.extend(_check_slot("props.caption", props.caption, slots["caption"]))
        # Grounding
        if not is_stat_grounded(props.value, props.display_scale, beat_text):
            errors.append(
                f"props.value: {props.value} (scale: {props.display_scale}) "
                "is not grounded in beat narration"
            )

    elif isinstance(props, IconListProps):
        errors.extend(_check_slot("props.heading", props.heading, slots["heading"]))
        for idx, item in enumerate(props.items):
            errors.extend(_check_slot(f"props.items[{idx}].label", item.label, slots["label"]))

    elif isinstance(props, RevealProps):
        errors.extend(_check_slot("props.kicker", props.kicker, slots["kicker"]))
        errors.extend(_check_slot("props.text", props.text, slots["text"]))

    elif isinstance(props, CauseEffectProps):
        for idx, node in enumerate(props.nodes):
            errors.extend(_check_slot(f"props.nodes[{idx}].label", node.label, slots["label"]))

    elif isinstance(props, ComparisonProps):
        if props.a.cast_id and props.a.cast_id not in cast_map:
            errors.append(f"props.a.cast_id: cast '{props.a.cast_id}' not found in bible")
        if props.b.cast_id and props.b.cast_id not in cast_map:
            errors.append(f"props.b.cast_id: cast '{props.b.cast_id}' not found in bible")
        errors.extend(_check_slot("props.a.heading", props.a.heading, slots["heading"]))
        errors.extend(_check_slot("props.b.heading", props.b.heading, slots["heading"]))
        for idx, pt in enumerate(props.a.points):
            errors.extend(_check_slot(f"props.a.points[{idx}]", pt, slots["point"]))
        for idx, pt in enumerate(props.b.points):
            errors.extend(_check_slot(f"props.b.points[{idx}]", pt, slots["point"]))

    elif isinstance(props, CharacterIntroProps):
        if props.cast_id not in cast_map:
            errors.append(f"props.cast_id: cast '{props.cast_id}' not found in bible")
        else:
            errors.extend(
                _check_slot("bible.cast.name", cast_map[props.cast_id].name, slots["name"])
            )
        errors.extend(_check_slot("props.descriptor", props.descriptor, slots["descriptor"]))
        for idx, trait in enumerate(props.traits):
            errors.extend(_check_slot(f"props.traits[{idx}]", trait, slots["trait"]))

    elif isinstance(props, DialogueProps):
        for idx, line in enumerate(props.lines):
            if line.cast_id not in cast_map:
                errors.append(
                    f"props.lines[{idx}].cast_id: cast '{line.cast_id}' not found in bible"
                )
            errors.extend(_check_slot(f"props.lines[{idx}].text", line.text, slots["line"]))

    elif isinstance(props, TextThreadProps):
        if props.contact_cast_id and props.contact_cast_id not in cast_map:
            errors.append(
                f"props.contact_cast_id: cast '{props.contact_cast_id}' not found in bible"
            )
        errors.extend(_check_slot("props.contact_name", props.contact_name, slots["contact"]))
        for idx, msg in enumerate(props.messages):
            errors.extend(_check_slot(f"props.messages[{idx}].text", msg.text, slots["message"]))

    elif isinstance(props, EmotionBeatProps):
        if props.cast_id not in cast_map:
            errors.append(f"props.cast_id: cast '{props.cast_id}' not found in bible")
        errors.extend(_check_slot("props.caption", props.caption, slots["caption"]))

    elif isinstance(props, RelationshipMapProps):
        for idx, cid in enumerate(props.cast_ids):
            if cid not in cast_map:
                errors.append(f"props.cast_ids[{idx}]: cast '{cid}' not found in bible")
        cast_ids_set = set(props.cast_ids)
        if len(cast_ids_set) < len(props.cast_ids):
            errors.append("props.cast_ids: duplicate cast_id in relationship map")

        seen_edges: set[tuple[str, str]] = set()
        for idx, edge in enumerate(props.edges):
            if edge.from_id not in cast_ids_set:
                errors.append(f"props.edges[{idx}].from_id: '{edge.from_id}' not in scene cast_ids")
            if edge.to_id not in cast_ids_set:
                errors.append(f"props.edges[{idx}].to_id: '{edge.to_id}' not in scene cast_ids")
            if edge.from_id == edge.to_id:
                errors.append(
                    f"props.edges[{idx}]: self-loop from '{edge.from_id}' to "
                    f"'{edge.to_id}' is not allowed"
                )
            u, v = sorted([edge.from_id, edge.to_id])
            pair = (u, v)
            if pair in seen_edges:
                errors.append(
                    f"props.edges[{idx}]: duplicate unordered edge between "
                    f"'{edge.from_id}' and '{edge.to_id}'"
                )
            seen_edges.add(pair)
            errors.extend(_check_slot(f"props.edges[{idx}].label", edge.label, slots["edge_label"]))

    elif isinstance(props, LocationProps):
        if props.place_id not in places_map:
            errors.append(f"props.place_id: place '{props.place_id}' not found in bible")
        else:
            errors.extend(
                _check_slot("bible.places.name", places_map[props.place_id].name, slots["name"])
            )
        errors.extend(_check_slot("props.caption", props.caption, slots["caption"]))
        errors.extend(_check_slot("props.era_label", props.era_label, slots["era"]))
        if props.era_label:
            if re.search(r"\bago\b", props.era_label, re.IGNORECASE) and not re.search(
                r"\bago\b", full_transcript, re.IGNORECASE
            ):
                errors.append('props.era_label: "ago" is not in the narration')
            if not digits_grounded(props.era_label, full_transcript):
                errors.append(
                    f"props.era_label: '{props.era_label}' "
                    "contains digits not grounded in transcript"
                )

    elif isinstance(props, SetPieceProps):
        if props.set_piece_id not in set_pieces_map:
            errors.append(
                f"props.set_piece_id: set piece '{props.set_piece_id}' not found in bible"
            )
        else:
            errors.extend(
                _check_slot(
                    "bible.set_pieces.name",
                    set_pieces_map[props.set_piece_id].name,
                    slots["name"],
                )
            )
        errors.extend(_check_slot("props.caption", props.caption, slots["caption"]))

    elif isinstance(props, MapFocusProps):
        marker_countries: set[str] = set()
        for idx, marker in enumerate(props.markers):
            if marker.place_id not in places_map:
                errors.append(
                    f"props.markers[{idx}].place_id: place '{marker.place_id}' not found in bible"
                )
            else:
                p = places_map[marker.place_id]
                if p.lat is None or p.lon is None:
                    errors.append(
                        f"props.markers[{idx}].place_id: place '{marker.place_id}' lacks "
                        "coordinates for map_focus"
                    )
                if p.country_iso3:
                    marker_countries.add(p.country_iso3)
            errors.extend(
                _check_slot(f"props.markers[{idx}].label", marker.label, slots["marker_label"])
            )
        if props.region != "world" and props.region not in marker_countries:
            errors.append(
                f"props.region: region '{props.region}' does not match any marker place's "
                f"country_iso3 ({marker_countries})"
            )
        errors.extend(_check_slot("props.caption", props.caption, slots["caption"]))

    elif isinstance(props, TimelineProps):
        if not (0 <= props.highlight_index < len(props.events)):
            errors.append(
                f"props.highlight_index: {props.highlight_index} "
                f"out of range [0, {len(props.events)})"
            )
        for idx, event in enumerate(props.events):
            errors.extend(
                _check_slot(f"props.events[{idx}].date_label", event.date_label, slots["date"])
            )
            errors.extend(_check_slot(f"props.events[{idx}].label", event.label, slots["label"]))

        errors.extend(timeline_label_errors(props.events, full_transcript))

    return errors


def validate_plan(bible: Bible, storyboard: Storyboard, ctx: PlanContext) -> list[str]:
    """Validate a storyboard plan against whole-plan rules, references, and scene validity.

    Per design_planner.md §6 and rules R1-R5:
    - Scene 0 is title_card
    - Scenes k >= 1 are not title_card
    - Character intro for the same cast_id appears at most once (R3)
    - Reveal appears at most twice (R4)
    - Every individual scene passes validate_scene
    """
    errors: list[str] = []

    if not storyboard.scenes:
        return ["storyboard.scenes: plan contains no scenes"]

    # Scene 0 rule
    if storyboard.scenes[0].template != "title_card":
        errors.append(
            f"scenes[0]: scene 0 must be 'title_card', got '{storyboard.scenes[0].template}'"
        )

    # Later scenes not title_card
    for idx, s in enumerate(storyboard.scenes[1:], start=1):
        if s.template == "title_card":
            errors.append(f"scenes[{idx}]: title_card is only allowed at scene 0")

    # Character intro at most once per cast_id (R3)
    seen_intro_cast: set[str] = set()
    reveal_count = 0

    for idx, scene in enumerate(storyboard.scenes):
        # Validate individual scene
        beat = ctx.beats[idx] if ctx.beats and idx < len(ctx.beats) else None
        scene_ctx = PlanContext(
            transcript=ctx.transcript,
            bible=bible,
            beat=beat,
            beats=ctx.beats,
        )
        scene_errors = validate_scene(scene, scene_ctx)
        for err in scene_errors:
            errors.append(f"scenes[{idx}].{err}")

        # Invariants across whole plan
        if scene.template == "character_intro":
            intro_cast = scene.props.cast_id  # type: ignore[attr-defined]
            if intro_cast in seen_intro_cast:
                errors.append(
                    f"scenes[{idx}]: character_intro for cast_id '{intro_cast}' "
                    "appears more than once"
                )
            seen_intro_cast.add(intro_cast)
        elif scene.template == "reveal":
            reveal_count += 1

    if reveal_count > 2:
        errors.append(f"storyboard: reveal appears {reveal_count} times (max 2 per video allowed)")

    return errors

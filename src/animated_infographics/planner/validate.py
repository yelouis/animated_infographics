"""Validation for storyboard scenes and whole plans against contracts, bible, and grounding."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Final

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


CUT_OFF_ENDINGS: Final[tuple[str, ...]] = ("-", "(", "[", ",", ":", "/")


def normalize_text(s: str) -> str:
    """Collapse runs of whitespace including newlines to a single space, strip ends."""
    return re.sub(r"\s+", " ", s).strip()


def text_complete_errors(path: str, s: str | None) -> list[str]:
    """Validate free-text completeness per design_planner.md §6 item 7.

    Errors return [f"{path}: looks cut off (\"{s}\")"] if:
    - Contains no letter or digit ("...", "—");
    - Ends with -, (, [, ,, :, or /;
    - (, [, or " characters are unbalanced;
    - Last word is a truncation fragment (single lowercase letter other than a).
    """
    if not s:
        return []

    # 1. Contains no letter or digit
    if not any(c.isalnum() for c in s):
        return [f'{path}: looks cut off ("{s}")']

    # 2. Ends with -, (, [, ,, :, or /
    if s.rstrip().endswith(CUT_OFF_ENDINGS):
        return [f'{path}: looks cut off ("{s}")']

    # 3. (, [, or " characters are unbalanced
    if s.count("(") != s.count(")") or s.count("[") != s.count("]") or (s.count('"') % 2 != 0):
        return [f'{path}: looks cut off ("{s}")']

    # 4. Last word is a truncation fragment (single lowercase letter other than a)
    tokens = s.strip().split()
    if tokens:
        last = tokens[-1].rstrip(".,!?:;\"'…")
        if len(last) == 1 and last.islower() and last != "a":
            return [f'{path}: looks cut off ("{s}")']

    return []


def internal_id_errors(path: str, s: str | None, bible: Bible | None) -> list[str]:
    """Validate free-text string contains no internal bible IDs per design_planner.md §6 item 8.

    Tokens are re.findall(r"[A-Za-z0-9]+", s), casefolded.
    It is an error if any token equals one of this bible's entity ids (cast, places, set_pieces).
    The message is exactly:
        f'{path}: contains the internal id "{tok_cf}" — use the name ("{name}")'
    """
    if not s or not bible:
        return []

    id_to_name: dict[str, str] = {}
    for member in bible.cast:
        id_to_name[member.id.casefold()] = member.name
    for place in bible.places:
        id_to_name[place.id.casefold()] = place.name
    for sp in bible.set_pieces:
        id_to_name[sp.id.casefold()] = sp.name

    tokens = re.findall(r"[A-Za-z0-9]+", s)
    errors: list[str] = []
    seen: set[str] = set()
    for tok in tokens:
        tok_cf = tok.casefold()
        if tok_cf in id_to_name and tok_cf not in seen:
            seen.add(tok_cf)
            name = id_to_name[tok_cf]
            errors.append(f'{path}: contains the internal id "{tok_cf}" — use the name ("{name}")')

    return errors


def normalize_props_text(template_name: str, props: dict[str, Any]) -> dict[str, Any]:
    """Normalize all free-text string fields in a props dictionary.

    Collapses whitespace including newlines to a single space, and strips ends.
    Never modifies ids, enums, prefix, date_label, or era_label.
    """
    p = dict(props)
    if template_name == "title_card":
        if "title" in p and isinstance(p["title"], str):
            p["title"] = normalize_text(p["title"])
        if "subtitle" in p and isinstance(p["subtitle"], str):
            p["subtitle"] = normalize_text(p["subtitle"])
    elif template_name == "kinetic_quote":
        if "text" in p and isinstance(p["text"], str):
            p["text"] = normalize_text(p["text"])
    elif template_name == "stat_callout":
        if "suffix" in p and isinstance(p["suffix"], str):
            p["suffix"] = normalize_text(p["suffix"])
        if "caption" in p and isinstance(p["caption"], str):
            p["caption"] = normalize_text(p["caption"])
    elif template_name == "icon_list":
        if "heading" in p and isinstance(p["heading"], str):
            p["heading"] = normalize_text(p["heading"])
        if "items" in p and isinstance(p["items"], list):
            new_items = []
            for item in p["items"]:
                if isinstance(item, dict):
                    it = dict(item)
                    if "label" in it and isinstance(it["label"], str):
                        it["label"] = normalize_text(it["label"])
                    new_items.append(it)
                else:
                    new_items.append(item)
            p["items"] = new_items
    elif template_name == "reveal":
        if "kicker" in p and isinstance(p["kicker"], str):
            p["kicker"] = normalize_text(p["kicker"])
        if "text" in p and isinstance(p["text"], str):
            p["text"] = normalize_text(p["text"])
    elif template_name == "cause_effect":
        if "nodes" in p and isinstance(p["nodes"], list):
            new_nodes = []
            for node in p["nodes"]:
                if isinstance(node, dict):
                    nd = dict(node)
                    if "label" in nd and isinstance(nd["label"], str):
                        nd["label"] = normalize_text(nd["label"])
                    new_nodes.append(nd)
                else:
                    new_nodes.append(node)
            p["nodes"] = new_nodes
    elif template_name == "comparison":
        for side in ("a", "b"):
            if side in p and isinstance(p[side], dict):
                panel = dict(p[side])
                if "heading" in panel and isinstance(panel["heading"], str):
                    panel["heading"] = normalize_text(panel["heading"])
                if "points" in panel and isinstance(panel["points"], list):
                    panel["points"] = [
                        normalize_text(pt) if isinstance(pt, str) else pt for pt in panel["points"]
                    ]
                p[side] = panel
    elif template_name == "character_intro":
        if "descriptor" in p and isinstance(p["descriptor"], str):
            p["descriptor"] = normalize_text(p["descriptor"])
        if "traits" in p and isinstance(p["traits"], list):
            p["traits"] = [normalize_text(tr) if isinstance(tr, str) else tr for tr in p["traits"]]
    elif template_name == "dialogue":
        if "lines" in p and isinstance(p["lines"], list):
            new_lines = []
            for line in p["lines"]:
                if isinstance(line, dict):
                    ln = dict(line)
                    if "text" in ln and isinstance(ln["text"], str):
                        ln["text"] = normalize_text(ln["text"])
                    new_lines.append(ln)
                else:
                    new_lines.append(line)
            p["lines"] = new_lines
    elif template_name == "text_thread":
        if "contact_name" in p and isinstance(p["contact_name"], str):
            p["contact_name"] = normalize_text(p["contact_name"])
        if "messages" in p and isinstance(p["messages"], list):
            new_msgs = []
            for msg in p["messages"]:
                if isinstance(msg, dict):
                    m = dict(msg)
                    if "text" in m and isinstance(m["text"], str):
                        m["text"] = normalize_text(m["text"])
                    new_msgs.append(m)
                else:
                    new_msgs.append(msg)
            p["messages"] = new_msgs
    elif template_name in ("emotion_beat", "location", "set_piece"):
        if "caption" in p and isinstance(p["caption"], str):
            p["caption"] = normalize_text(p["caption"])
    elif template_name == "relationship_map":
        if "edges" in p and isinstance(p["edges"], list):
            new_edges = []
            for edge in p["edges"]:
                if isinstance(edge, dict):
                    ed = dict(edge)
                    if "label" in ed and isinstance(ed["label"], str):
                        ed["label"] = normalize_text(ed["label"])
                    new_edges.append(ed)
                else:
                    new_edges.append(edge)
            p["edges"] = new_edges
    elif template_name == "map_focus":
        if "caption" in p and isinstance(p["caption"], str):
            p["caption"] = normalize_text(p["caption"])
        if "markers" in p and isinstance(p["markers"], list):
            new_markers = []
            for marker in p["markers"]:
                if isinstance(marker, dict):
                    mk = dict(marker)
                    if "label" in mk and isinstance(mk["label"], str):
                        mk["label"] = normalize_text(mk["label"])
                    new_markers.append(mk)
                else:
                    new_markers.append(marker)
            p["markers"] = new_markers
    elif template_name == "timeline":
        if "events" in p and isinstance(p["events"], list):
            new_events = []
            for ev in p["events"]:
                if isinstance(ev, dict):
                    event = dict(ev)
                    if "label" in event and isinstance(event["label"], str):
                        event["label"] = normalize_text(event["label"])
                    new_events.append(event)
                else:
                    new_events.append(ev)
            p["events"] = new_events
    return p


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
        errors.extend(text_complete_errors("props.title", props.title))
        errors.extend(text_complete_errors("props.subtitle", props.subtitle))
        errors.extend(internal_id_errors("props.title", props.title, bible))
        errors.extend(internal_id_errors("props.subtitle", props.subtitle, bible))

    elif isinstance(props, KineticQuoteProps):
        if props.attribution_cast_id and props.attribution_cast_id not in cast_map:
            errors.append(
                f"props.attribution_cast_id: cast '{props.attribution_cast_id}' not found in bible"
            )
        errors.extend(_check_slot("props.text", props.text, slots["text"]))
        errors.extend(text_complete_errors("props.text", props.text))
        errors.extend(internal_id_errors("props.text", props.text, bible))
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
        if props.suffix:
            errors.extend(text_complete_errors("props.suffix", props.suffix))
            errors.extend(internal_id_errors("props.suffix", props.suffix, bible))
        errors.extend(text_complete_errors("props.caption", props.caption))
        errors.extend(internal_id_errors("props.caption", props.caption, bible))
        # Grounding
        if not is_stat_grounded(props.value, props.display_scale, beat_text):
            errors.append(
                f"props.value: {props.value} (scale: {props.display_scale}) "
                "is not grounded in beat narration"
            )

    elif isinstance(props, IconListProps):
        errors.extend(_check_slot("props.heading", props.heading, slots["heading"]))
        errors.extend(text_complete_errors("props.heading", props.heading))
        errors.extend(internal_id_errors("props.heading", props.heading, bible))
        for idx, item in enumerate(props.items):
            errors.extend(_check_slot(f"props.items[{idx}].label", item.label, slots["label"]))
            errors.extend(text_complete_errors(f"props.items[{idx}].label", item.label))
            errors.extend(internal_id_errors(f"props.items[{idx}].label", item.label, bible))

    elif isinstance(props, RevealProps):
        errors.extend(_check_slot("props.kicker", props.kicker, slots["kicker"]))
        errors.extend(_check_slot("props.text", props.text, slots["text"]))
        errors.extend(text_complete_errors("props.kicker", props.kicker))
        errors.extend(text_complete_errors("props.text", props.text))
        errors.extend(internal_id_errors("props.kicker", props.kicker, bible))
        errors.extend(internal_id_errors("props.text", props.text, bible))

    elif isinstance(props, CauseEffectProps):
        for idx, node in enumerate(props.nodes):
            errors.extend(_check_slot(f"props.nodes[{idx}].label", node.label, slots["label"]))
            errors.extend(text_complete_errors(f"props.nodes[{idx}].label", node.label))
            errors.extend(internal_id_errors(f"props.nodes[{idx}].label", node.label, bible))

    elif isinstance(props, ComparisonProps):
        if props.a.cast_id and props.a.cast_id not in cast_map:
            errors.append(f"props.a.cast_id: cast '{props.a.cast_id}' not found in bible")
        if props.b.cast_id and props.b.cast_id not in cast_map:
            errors.append(f"props.b.cast_id: cast '{props.b.cast_id}' not found in bible")
        errors.extend(_check_slot("props.a.heading", props.a.heading, slots["heading"]))
        errors.extend(_check_slot("props.b.heading", props.b.heading, slots["heading"]))
        errors.extend(text_complete_errors("props.a.heading", props.a.heading))
        errors.extend(text_complete_errors("props.b.heading", props.b.heading))
        errors.extend(internal_id_errors("props.a.heading", props.a.heading, bible))
        errors.extend(internal_id_errors("props.b.heading", props.b.heading, bible))
        for idx, pt in enumerate(props.a.points):
            errors.extend(_check_slot(f"props.a.points[{idx}]", pt, slots["point"]))
            errors.extend(text_complete_errors(f"props.a.points[{idx}]", pt))
            errors.extend(internal_id_errors(f"props.a.points[{idx}]", pt, bible))
        for idx, pt in enumerate(props.b.points):
            errors.extend(_check_slot(f"props.b.points[{idx}]", pt, slots["point"]))
            errors.extend(text_complete_errors(f"props.b.points[{idx}]", pt))
            errors.extend(internal_id_errors(f"props.b.points[{idx}]", pt, bible))

    elif isinstance(props, CharacterIntroProps):
        if props.cast_id not in cast_map:
            errors.append(f"props.cast_id: cast '{props.cast_id}' not found in bible")
        else:
            errors.extend(
                _check_slot("bible.cast.name", cast_map[props.cast_id].name, slots["name"])
            )
        errors.extend(_check_slot("props.descriptor", props.descriptor, slots["descriptor"]))
        errors.extend(text_complete_errors("props.descriptor", props.descriptor))
        errors.extend(internal_id_errors("props.descriptor", props.descriptor, bible))
        for idx, trait in enumerate(props.traits):
            errors.extend(_check_slot(f"props.traits[{idx}]", trait, slots["trait"]))
            errors.extend(text_complete_errors(f"props.traits[{idx}]", trait))
            errors.extend(internal_id_errors(f"props.traits[{idx}]", trait, bible))

    elif isinstance(props, DialogueProps):
        for idx, line in enumerate(props.lines):
            if line.cast_id not in cast_map:
                errors.append(
                    f"props.lines[{idx}].cast_id: cast '{line.cast_id}' not found in bible"
                )
            errors.extend(_check_slot(f"props.lines[{idx}].text", line.text, slots["line"]))
            errors.extend(text_complete_errors(f"props.lines[{idx}].text", line.text))
            errors.extend(internal_id_errors(f"props.lines[{idx}].text", line.text, bible))

    elif isinstance(props, TextThreadProps):
        if props.contact_cast_id and props.contact_cast_id not in cast_map:
            errors.append(
                f"props.contact_cast_id: cast '{props.contact_cast_id}' not found in bible"
            )
        errors.extend(_check_slot("props.contact_name", props.contact_name, slots["contact"]))
        errors.extend(text_complete_errors("props.contact_name", props.contact_name))
        errors.extend(internal_id_errors("props.contact_name", props.contact_name, bible))
        for idx, msg in enumerate(props.messages):
            errors.extend(_check_slot(f"props.messages[{idx}].text", msg.text, slots["message"]))
            errors.extend(text_complete_errors(f"props.messages[{idx}].text", msg.text))
            errors.extend(internal_id_errors(f"props.messages[{idx}].text", msg.text, bible))

    elif isinstance(props, EmotionBeatProps):
        if props.cast_id not in cast_map:
            errors.append(f"props.cast_id: cast '{props.cast_id}' not found in bible")
        errors.extend(_check_slot("props.caption", props.caption, slots["caption"]))
        errors.extend(text_complete_errors("props.caption", props.caption))
        errors.extend(internal_id_errors("props.caption", props.caption, bible))

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
            errors.extend(text_complete_errors(f"props.edges[{idx}].label", edge.label))
            errors.extend(internal_id_errors(f"props.edges[{idx}].label", edge.label, bible))

    elif isinstance(props, LocationProps):
        if props.place_id not in places_map:
            errors.append(f"props.place_id: place '{props.place_id}' not found in bible")
        else:
            errors.extend(
                _check_slot("bible.places.name", places_map[props.place_id].name, slots["name"])
            )
        errors.extend(_check_slot("props.caption", props.caption, slots["caption"]))
        errors.extend(_check_slot("props.era_label", props.era_label, slots["era"]))
        errors.extend(text_complete_errors("props.caption", props.caption))
        errors.extend(internal_id_errors("props.caption", props.caption, bible))
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
        errors.extend(text_complete_errors("props.caption", props.caption))
        errors.extend(internal_id_errors("props.caption", props.caption, bible))

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
            errors.extend(text_complete_errors(f"props.markers[{idx}].label", marker.label))
            errors.extend(internal_id_errors(f"props.markers[{idx}].label", marker.label, bible))
        if props.region != "world" and props.region not in marker_countries:
            errors.append(
                f"props.region: region '{props.region}' does not match any marker place's "
                f"country_iso3 ({marker_countries})"
            )
        errors.extend(_check_slot("props.caption", props.caption, slots["caption"]))
        errors.extend(text_complete_errors("props.caption", props.caption))
        errors.extend(internal_id_errors("props.caption", props.caption, bible))

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
            errors.extend(text_complete_errors(f"props.events[{idx}].label", event.label))
            errors.extend(internal_id_errors(f"props.events[{idx}].label", event.label, bible))

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

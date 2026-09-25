"""Story bible planning, deterministic repairs, and entity consistency."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from animated_infographics.contracts.icons import ICON_NAMES, IconName
from animated_infographics.contracts.models import (
    AvatarConfig,
    Bible,
    CastMember,
    Place,
    SetPiece,
    Transcript,
    VoiceDecision,
)
from animated_infographics.planner.geo import Gazetteer, check_coords_in_bbox
from animated_infographics.planner.llm import LLMBackend, run_with_retries

BIBLE_SCHEMA: dict[str, Any] = Bible.model_json_schema()


def load_prompt(name: str) -> str:
    """Load prompt template from planner/prompts/ directory."""
    prompt_path = Path(__file__).parent / "prompts" / name
    return prompt_path.read_text(encoding="utf-8")


def _sanitize_icon(icon: str | None, default: str) -> IconName:
    """Ensure icon name is in the allow-list, falling back to a safe default."""
    if icon in ICON_NAMES:
        return icon  # type: ignore[return-value]
    return default  # type: ignore[return-value]


def repair_bible(
    raw: Bible | dict[str, Any],
    voice: VoiceDecision | None,
    gazetteer: Gazetteer,
    bboxes: Mapping[str, tuple[float, float, float, float]],
) -> Bible:
    """Apply deterministic repairs to a raw bible or raw dict (pure function).

    Repairs:
    1. Truncate lists to budget (keep first 8 cast, 4 places, 3 set pieces).
    2. Reassign duplicate color_slots to the lowest free slot in 0..7.
    3. If multiple cast members have is_narrator=True, keep only the first.
    4. Resolve geo for real places (gazetteer -> llm coords in bbox -> none).
    5. If voice is female and narrator exists, enforce facial_hair="none".
    """
    if isinstance(raw, Bible):
        raw_dict = raw.model_dump()
    else:
        raw_dict = dict(raw)

    title = str(raw_dict.get("title", "Untitled"))[:60]
    if not title:
        title = "Untitled"

    logline = str(raw_dict.get("logline", "Story summary."))[:140]
    if not logline:
        logline = "Story summary."

    genre = raw_dict.get("genre", "other")
    if genre not in {"history", "personal_story", "other"}:
        genre = "other"

    # 1. Truncate cast to <= 8 and process repairs
    raw_cast = list(raw_dict.get("cast", []))[:8]
    repaired_cast: list[CastMember] = []
    used_slots: set[int] = set()
    narrator_seen = False

    for i, item in enumerate(raw_cast):
        c_dict = item if isinstance(item, dict) else item.model_dump()
        cid = f"c{i + 1}"
        name = str(c_dict.get("name", f"Character {i + 1}"))[:24]
        if not name:
            name = f"Character {i + 1}"
        role = str(c_dict.get("role", "Participant"))[:40]
        if not role:
            role = "Participant"

        # Rule 3: Single narrator
        is_narr = bool(c_dict.get("is_narrator", False))
        if is_narr:
            if not narrator_seen:
                narrator_seen = True
            else:
                is_narr = False

        # Rule 2: Unique color slots
        slot_raw = c_dict.get("color_slot", i % 8)
        try:
            slot = int(slot_raw)
        except (ValueError, TypeError):
            slot = i % 8

        if slot not in used_slots and 0 <= slot <= 7:
            used_slots.add(slot)
        else:
            free_slots = [s for s in range(8) if s not in used_slots]
            slot = free_slots[0] if free_slots else 0
            used_slots.add(slot)

        # Avatar
        av_raw = c_dict.get("avatar", {})
        if not isinstance(av_raw, dict):
            av_raw = {}

        skin = av_raw.get("skin", 1)
        if not isinstance(skin, int) or not (0 <= skin <= 5):
            skin = 1

        hair_style = av_raw.get("hair_style", "short")
        if hair_style not in {"short", "long", "bun", "curly", "ponytail", "bald"}:
            hair_style = "short"

        hair_color = av_raw.get("hair_color", "black")
        if hair_color not in {"black", "brown", "blonde", "red", "gray", "white"}:
            hair_color = "black"

        facial_hair = av_raw.get("facial_hair", "none")
        if facial_hair not in {"none", "beard", "mustache"}:
            facial_hair = "none"

        # Rule 5: Narrator avatar consistency (female voice -> facial_hair="none")
        if is_narr and voice is not None and voice.narrator_gender == "female":
            facial_hair = "none"

        headwear = av_raw.get("headwear", "none")
        if headwear not in {"none", "hat", "crown", "military_cap", "helmet", "headscarf"}:
            headwear = "none"

        glasses = bool(av_raw.get("glasses", False))

        age = av_raw.get("age", "adult")
        if age not in {"child", "adult", "elder"}:
            age = "adult"

        avatar = AvatarConfig(
            skin=skin,
            hair_style=hair_style,
            hair_color=hair_color,
            facial_hair=facial_hair,
            headwear=headwear,
            glasses=glasses,
            age=age,
        )

        repaired_cast.append(
            CastMember(
                id=cid,
                name=name,
                role=role,
                is_narrator=is_narr,
                color_slot=slot,
                avatar=avatar,
            )
        )

    # 4. Truncate places to <= 4 and process geo repairs
    raw_places = list(raw_dict.get("places", []))[:4]
    repaired_places: list[Place] = []

    for i, item in enumerate(raw_places):
        p_dict = item if isinstance(item, dict) else item.model_dump()
        pid = f"p{i + 1}"
        name = str(p_dict.get("name", f"Place {i + 1}"))[:40]
        if not name:
            name = f"Place {i + 1}"

        kind = p_dict.get("kind", "real")
        if kind not in {"real", "fictional"}:
            kind = "real"

        country_iso3 = p_dict.get("country_iso3")
        if country_iso3 and isinstance(country_iso3, str):
            country_iso3 = country_iso3.strip().upper()[:3]
            if len(country_iso3) != 3 or not country_iso3.isalpha():
                country_iso3 = None
        else:
            country_iso3 = None

        raw_lat = p_dict.get("lat")
        raw_lon = p_dict.get("lon")
        lat: float | None = float(raw_lat) if raw_lat is not None else None
        lon: float | None = float(raw_lon) if raw_lon is not None else None

        geo_src: str
        if kind == "real":
            # Try gazetteer first
            resolved = gazetteer.resolve(name, country_iso3)
            if resolved is not None:
                lat, lon = resolved
                geo_src = "gazetteer"
            elif (
                lat is not None
                and lon is not None
                and check_coords_in_bbox(lat, lon, country_iso3, bboxes, margin=0.5)
            ):
                geo_src = "llm"
            else:
                lat, lon = None, None
                geo_src = "none"
        else:
            lat, lon = None, None
            geo_src = "none"

        vdesc = str(p_dict.get("visual_description", f"A {kind} place"))[:200]
        if not vdesc:
            vdesc = f"A {kind} place"

        icon = _sanitize_icon(p_dict.get("icon"), default="MapPin")

        repaired_places.append(
            Place(
                id=pid,
                name=name,
                kind=kind,
                country_iso3=country_iso3,
                lat=lat,
                lon=lon,
                geo_source=geo_src,  # type: ignore[arg-type]
                visual_description=vdesc,
                icon=icon,
            )
        )

    # Truncate set pieces to <= 3
    raw_sp = list(raw_dict.get("set_pieces", []))[:3]
    repaired_sp: list[SetPiece] = []

    for i, item in enumerate(raw_sp):
        v_dict = item if isinstance(item, dict) else item.model_dump()
        vid = f"v{i + 1}"
        name = str(v_dict.get("name", f"Set Piece {i + 1}"))[:40]
        if not name:
            name = f"Set Piece {i + 1}"

        vdesc = str(v_dict.get("visual_description", "A notable object"))[:200]
        if not vdesc:
            vdesc = "A notable object"

        icon = _sanitize_icon(v_dict.get("icon"), default="Sparkle")

        repaired_sp.append(
            SetPiece(
                id=vid,
                name=name,
                visual_description=vdesc,
                icon=icon,
            )
        )

    return Bible(
        schema_version=1,
        title=title,
        logline=logline,
        genre=genre,
        cast=repaired_cast,
        places=repaired_places,
        set_pieces=repaired_sp,
    )


def plan_bible(
    transcript: Transcript,
    voice: VoiceDecision | None,
    backend: LLMBackend,
    gazetteer: Gazetteer,
    bboxes: Mapping[str, tuple[float, float, float, float]],
) -> Bible:
    """Plan world bible via local LLM with retry protocol and deterministic fallback."""
    # Build transcript text with numbered sentences
    lines: list[str] = []
    title_candidate = "Untitled"
    for s in transcript.sentences:
        lines.append(f"[{s.i}] {s.text}")
        if s.is_title:
            title_candidate = s.text

    if title_candidate == "Untitled" and transcript.sentences:
        title_candidate = transcript.sentences[0].text[:60]

    numbered_transcript = "\n".join(lines)

    # Narrator guidance
    if voice is not None and voice.narrator_gender in {"female", "male"}:
        narrator_guidance = (
            f"- The story is told in the first person by a {voice.narrator_gender} narrator. "
            f"Include them as ONE cast member with is_narrator: true, name: 'Me', "
            f"and an avatar appropriate for a {voice.narrator_gender} narrator.\n"
        )
    else:
        narrator_guidance = (
            "- If the story is told in the first person (the narrator says 'I', 'me', 'my'), "
            "include the narrator as ONE cast member with is_narrator: true and name: 'Me'. "
            "If the story is a third-person narrative (e.g. historical account), "
            "all cast members must have is_narrator: false.\n"
        )

    prompt_tmpl = load_prompt("bible.md")
    user_prompt = prompt_tmpl.format(
        title=title_candidate,
        transcript=numbered_transcript,
        narrator_guidance=narrator_guidance,
    )

    def validate_bible_output(output: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        if not isinstance(output, dict):
            return output, ["Output must be a JSON object"]
        errors: list[str] = []
        if "title" not in output:
            errors.append("Missing required field: title")
        if "logline" not in output:
            errors.append("Missing required field: logline")
        if "genre" not in output:
            errors.append("Missing required field: genre")
        if errors:
            return output, errors

        try:
            repaired = repair_bible(output, voice, gazetteer, bboxes)
            return repaired.model_dump(), []
        except Exception as e:
            return output, [f"Bible repair failed: {e}"]

    result, _attempts = run_with_retries(
        backend=backend,
        stage="bible",
        system=(
            "You are an expert story bible planner and world-builder for animated infographics. "
            "Output JSON strictly matching the schema."
        ),
        user=user_prompt,
        schema=BIBLE_SCHEMA,
        validate=validate_bible_output,
        max_attempts=3,
    )

    if result is not None:
        return repair_bible(result, voice, gazetteer, bboxes)

    # Fallback bible after 3 failed attempts:
    # {title: <title or first 60 chars of sentence 0>,
    #  logline: <first 140 chars of transcript>,
    #  genre: "other", cast: [], places: [], set_pieces: []}
    full_text = " ".join(s.text for s in transcript.sentences)
    fallback = Bible(
        schema_version=1,
        title=title_candidate[:60],
        logline=full_text[:140] if full_text else "Story summary.",
        genre="other",
        cast=[],
        places=[],
        set_pieces=[],
    )
    return repair_bible(fallback, voice, gazetteer, bboxes)

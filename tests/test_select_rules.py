"""Unit tests for allowed templates and deterministic rule repairs (R1, R2, R4, R5)."""

from animated_infographics.contracts.models import (
    AvatarConfig,
    Bible,
    CastMember,
    Place,
    SetPiece,
)
from animated_infographics.planner.select import (
    Choice,
    allowed_templates,
    apply_rules,
)


def _make_dummy_bible(
    n_cast: int = 0,
    n_places: int = 0,
    has_geo: bool = False,
    n_set_pieces: int = 0,
) -> Bible:
    cast = [
        CastMember(
            id=f"c{i + 1}",
            name=f"Cast {i + 1}",
            role="Role",
            is_narrator=False,
            color_slot=i,
            avatar=AvatarConfig(
                skin=1,
                hair_style="short",
                hair_color="black",
                facial_hair="none",
                headwear="none",
                glasses=False,
                age="adult",
            ),
        )
        for i in range(n_cast)
    ]
    places = [
        Place(
            id=f"p{i + 1}",
            name=f"Place {i + 1}",
            kind="real" if has_geo else "fictional",
            country_iso3="USA" if has_geo else None,
            lat=42.0 if has_geo else None,
            lon=-71.0 if has_geo else None,
            geo_source="gazetteer" if has_geo else "none",
            visual_description="A location",
            icon="Buildings",
        )
        for i in range(n_places)
    ]
    set_pieces = [
        SetPiece(
            id=f"v{i + 1}",
            name=f"SetPiece {i + 1}",
            visual_description="An object",
            icon="Drop",
        )
        for i in range(n_set_pieces)
    ]
    return Bible(
        schema_version=1,
        title="Title",
        logline="Logline",
        genre="history",
        cast=cast,
        places=places,
        set_pieces=set_pieces,
    )


def test_allowed_templates_filters() -> None:
    # Minimal bible: no cast, no places, no set pieces
    b0 = _make_dummy_bible(0, 0, False, 0)
    allowed0 = allowed_templates(b0)
    assert "title_card" not in allowed0
    assert "character_intro" not in allowed0
    assert "relationship_map" not in allowed0
    assert "location" not in allowed0
    assert "set_piece" not in allowed0
    assert "map_focus" not in allowed0
    assert "kinetic_quote" in allowed0
    assert "stat_callout" in allowed0

    # 1 cast member -> character_intro, emotion_beat, dialogue allowed, relationship_map NOT
    b1 = _make_dummy_bible(1, 0, False, 0)
    allowed1 = allowed_templates(b1)
    assert "character_intro" in allowed1
    assert "emotion_beat" in allowed1
    assert "dialogue" in allowed1
    assert "relationship_map" not in allowed1

    # 2 cast members -> relationship_map allowed
    b2 = _make_dummy_bible(2, 0, False, 0)
    allowed2 = allowed_templates(b2)
    assert "relationship_map" in allowed2

    # Place with geo -> location and map_focus allowed
    b_geo = _make_dummy_bible(0, 1, True, 0)
    allowed_geo = allowed_templates(b_geo)
    assert "location" in allowed_geo
    assert "map_focus" in allowed_geo

    # Set piece -> set_piece allowed
    b_sp = _make_dummy_bible(0, 0, False, 1)
    allowed_sp = allowed_templates(b_sp)
    assert "set_piece" in allowed_sp


def test_rule_r1_title_card() -> None:
    # Scene 0 is not title_card, later scene is title_card
    choices = [
        Choice(beat_i=0, primary="stat_callout", alternate="kinetic_quote"),
        Choice(beat_i=1, primary="title_card", alternate="stat_callout"),
    ]
    repaired, repairs = apply_rules(choices, 2)
    assert repaired[0].primary == "title_card"
    assert repaired[1].primary == "stat_callout"
    assert len(repairs) == 2
    assert any(r.rule == "R1" and r.scene == "s000" for r in repairs)
    assert any(r.rule == "R1" and r.scene == "s001" for r in repairs)


def test_rule_r2_consecutive_duplicates() -> None:
    # Two consecutive stat_callouts: second switches to alternate
    choices = [
        Choice(beat_i=0, primary="title_card", alternate="title_card"),
        Choice(beat_i=1, primary="stat_callout", alternate="timeline"),
        Choice(beat_i=2, primary="stat_callout", alternate="timeline"),
    ]
    repaired, repairs = apply_rules(choices, 3)
    assert repaired[1].primary == "stat_callout"
    assert repaired[2].primary == "timeline"
    assert len(repairs) == 1
    assert repairs[0].rule == "R2"
    assert repairs[0].scene == "s002"

    # Consecutive dialogues are ALLOWED (not repaired)
    dialogue_choices = [
        Choice(beat_i=0, primary="title_card", alternate="title_card"),
        Choice(beat_i=1, primary="dialogue", alternate="kinetic_quote"),
        Choice(beat_i=2, primary="dialogue", alternate="kinetic_quote"),
    ]
    repaired_d, repairs_d = apply_rules(dialogue_choices, 3)
    assert repaired_d[1].primary == "dialogue"
    assert repaired_d[2].primary == "dialogue"
    assert len(repairs_d) == 0


def test_rule_r4_reveal_cap() -> None:
    # reveal appears 3 times (non-consecutive): 3rd is repaired to alternate
    choices = [
        Choice(beat_i=0, primary="title_card", alternate="title_card"),
        Choice(beat_i=1, primary="reveal", alternate="stat_callout"),
        Choice(beat_i=2, primary="stat_callout", alternate="timeline"),
        Choice(beat_i=3, primary="reveal", alternate="icon_list"),
        Choice(beat_i=4, primary="timeline", alternate="icon_list"),
        Choice(beat_i=5, primary="reveal", alternate="cause_effect"),
    ]
    repaired, repairs = apply_rules(choices, 6)
    assert repaired[1].primary == "reveal"
    assert repaired[3].primary == "reveal"
    assert repaired[5].primary == "cause_effect"
    assert len(repairs) == 1
    assert repairs[0].rule == "R4"
    assert repairs[0].scene == "s005"


def test_rule_r5_kinetic_quote_cap() -> None:
    # 10 scenes: ceil(0.30 * 10) = 3 kinetic_quotes allowed
    # Provide 4 kinetic_quotes (non-consecutive): latest 1 should be replaced with alternate
    choices = [
        Choice(beat_i=0, primary="title_card", alternate="title_card"),
        Choice(beat_i=1, primary="kinetic_quote", alternate="stat_callout"),
        Choice(beat_i=2, primary="timeline", alternate="stat_callout"),
        Choice(beat_i=3, primary="kinetic_quote", alternate="stat_callout"),
        Choice(beat_i=4, primary="icon_list", alternate="stat_callout"),
        Choice(beat_i=5, primary="kinetic_quote", alternate="stat_callout"),
        Choice(beat_i=6, primary="comparison", alternate="timeline"),
        Choice(beat_i=7, primary="kinetic_quote", alternate="cause_effect"),
        Choice(beat_i=8, primary="cause_effect", alternate="icon_list"),
        Choice(beat_i=9, primary="stat_callout", alternate="icon_list"),
    ]
    repaired, repairs = apply_rules(choices, 10)
    kq_count = sum(1 for c in repaired if c.primary == "kinetic_quote")
    assert kq_count == 3
    assert len(repairs) == 1
    assert repairs[0].rule == "R5"
    assert repairs[0].scene == "s007"
    assert repaired[7].primary == "cause_effect"

import pytest
from pydantic import ValidationError

from animated_infographics.contracts.models import (
    AvatarConfig,
    Beat,
    Bible,
    CastMember,
    CharacterIntroScene,
    KineticQuoteScene,
    MapFocusScene,
    Place,
    RelationshipMapScene,
    SetPiece,
    StatCalloutScene,
    Storyboard,
    TimelineSceneModel,
    TitleCardScene,
    Transcript,
    TranscriptSentence,
    TranscriptWord,
)
from animated_infographics.contracts.templates import (
    CharacterIntroProps,
    KineticQuoteProps,
    MapFocusProps,
    MapMarker,
    RelationshipEdge,
    RelationshipMapProps,
    StatCalloutProps,
    TimelineEvent,
    TimelineProps,
    TitleCardProps,
)
from animated_infographics.planner.validate import (
    PlanContext,
    validate_plan,
    validate_scene,
)


def _make_dummy_ctx() -> PlanContext:
    s0_text = "The Great Molasses Flood struck in 1919."
    s1_text = "About 150 people were injured when the tank burst."
    w_list = []
    w_idx = 0
    t = 0
    for s_idx, text in enumerate((s0_text, s1_text)):
        for token in text.split():
            w_list.append(
                TranscriptWord(
                    i=w_idx,
                    text=token,
                    start_ms=t,
                    end_ms=t + 200,
                    sentence_i=s_idx,
                )
            )
            w_idx += 1
            t += 250

    sentences = [
        TranscriptSentence(
            i=0,
            text=s0_text,
            start_ms=w_list[0].start_ms,
            end_ms=w_list[6].end_ms,
            word_start=0,
            word_end=7,
            paragraph_i=0,
            is_title=True,
        ),
        TranscriptSentence(
            i=1,
            text=s1_text,
            start_ms=w_list[7].start_ms,
            end_ms=w_list[15].end_ms,
            word_start=7,
            word_end=16,
            paragraph_i=0,
            is_title=False,
        ),
    ]
    transcript = Transcript(
        schema_version=1,
        source="tts",
        audio_path="test.wav",
        duration_ms=t + 100,
        words=w_list,
        sentences=sentences,
    )
    bible = Bible(
        schema_version=1,
        title="Molasses Flood",
        logline="A flood in Boston.",
        genre="history",
        cast=[
            CastMember(
                id="c1",
                name="John",
                role="Witness",
                is_narrator=False,
                color_slot=0,
                avatar=AvatarConfig(
                    skin=1,
                    hair_style="short",
                    hair_color="brown",
                    facial_hair="none",
                    headwear="none",
                    glasses=False,
                    age="adult",
                ),
            ),
            CastMember(
                id="c2",
                name="Mary",
                role="Worker",
                is_narrator=False,
                color_slot=1,
                avatar=AvatarConfig(
                    skin=2,
                    hair_style="bun",
                    hair_color="black",
                    facial_hair="none",
                    headwear="none",
                    glasses=False,
                    age="adult",
                ),
            ),
        ],
        places=[
            Place(
                id="p1",
                name="Boston",
                kind="real",
                country_iso3="USA",
                lat=42.36,
                lon=-71.06,
                geo_source="gazetteer",
                visual_description="Historic Boston streets.",
                icon="Buildings",
            ),
            Place(
                id="p2",
                name="Atlantis",
                kind="fictional",
                country_iso3=None,
                lat=None,
                lon=None,
                geo_source="none",
                visual_description="A mythical sunken city.",
                icon="WaveSine",
            ),
        ],
        set_pieces=[
            SetPiece(
                id="v1",
                name="The Great Tank",
                visual_description="A huge molasses tank.",
                icon="Drop",
            ),
        ],
    )
    beats = [
        Beat(
            i=0,
            text=s0_text,
            start_ms=0,
            end_ms=2000,
            word_start=0,
            word_end=7,
        ),
        Beat(
            i=1,
            text=s1_text,
            start_ms=2000,
            end_ms=5000,
            word_start=7,
            word_end=16,
        ),
    ]
    return PlanContext(transcript=transcript, bible=bible, beats=beats)


def test_title_card_validation() -> None:
    ctx = _make_dummy_ctx()
    # Passing at beat 0
    valid_scene = TitleCardScene(
        id="s000",
        beat_i=0,
        template="title_card",
        props=TitleCardProps(title="Molasses Flood"),
    )
    assert len(validate_scene(valid_scene, ctx)) == 0

    # Failing at beat 1
    invalid_scene = TitleCardScene(
        id="s001",
        beat_i=1,
        template="title_card",
        props=TitleCardProps(title="Molasses Flood"),
    )
    errs = validate_scene(invalid_scene, ctx)
    assert any("title_card is only allowed at beat 0" in e for e in errs)


def test_kinetic_quote_validation() -> None:
    ctx = _make_dummy_ctx()
    # Passing quote
    valid_scene = KineticQuoteScene(
        id="s001",
        beat_i=1,
        template="kinetic_quote",
        props=KineticQuoteProps(
            text="About 150 people were injured…",
            emphasis=["injured"],
            attribution_cast_id="c1",
        ),
    )
    assert len(validate_scene(valid_scene, ctx)) == 0

    # Unknown cast (c8 matches pattern ^c[1-8]$ but is not in bible)
    invalid_cast = KineticQuoteScene(
        id="s001",
        beat_i=1,
        template="kinetic_quote",
        props=KineticQuoteProps(
            text="About 150 people were injured…",
            attribution_cast_id="c8",
        ),
    )
    errs = validate_scene(invalid_cast, ctx)
    assert any("cast 'c8' not found" in e for e in errs)


def test_stat_callout_validation() -> None:
    ctx = _make_dummy_ctx()
    # Grounded stat
    valid = StatCalloutScene(
        id="s001",
        beat_i=1,
        template="stat_callout",
        props=StatCalloutProps(value=150, decimals=0, caption="Injured people"),
    )
    assert len(validate_scene(valid, ctx)) == 0

    # Ungrounded stat (1500 instead of 150)
    invalid = StatCalloutScene(
        id="s001",
        beat_i=1,
        template="stat_callout",
        props=StatCalloutProps(value=1500, decimals=0, caption="Injured people"),
    )
    errs = validate_scene(invalid, ctx)
    assert any("not grounded" in e for e in errs)


def test_relationship_map_validation() -> None:
    ctx = _make_dummy_ctx()
    # Valid
    valid = RelationshipMapScene(
        id="s001",
        beat_i=1,
        template="relationship_map",
        props=RelationshipMapProps(
            cast_ids=["c1", "c2"],
            edges=[RelationshipEdge(from_id="c1", to_id="c2", label="Colleague")],
        ),
    )
    assert len(validate_scene(valid, ctx)) == 0

    # Self-loop rejected by schema
    with pytest.raises(ValidationError):
        RelationshipMapProps(
            cast_ids=["c1", "c2"],
            edges=[RelationshipEdge(from_id="c1", to_id="c1", label="Self")],
        )

    # Cast member not in bible rejected by validate_scene
    unknown_cast = RelationshipMapScene(
        id="s001",
        beat_i=1,
        template="relationship_map",
        props=RelationshipMapProps(
            cast_ids=["c1", "c8"],
            edges=[RelationshipEdge(from_id="c1", to_id="c8", label="Friend")],
        ),
    )
    errs = validate_scene(unknown_cast, ctx)
    assert any("cast 'c8' not found" in e for e in errs)


def test_map_focus_validation() -> None:
    ctx = _make_dummy_ctx()
    # Valid map focus
    valid = MapFocusScene(
        id="s001",
        beat_i=1,
        template="map_focus",
        props=MapFocusProps(
            region="USA",
            markers=[MapMarker(place_id="p1", label="Boston Site")],
            path=False,
        ),
    )
    assert len(validate_scene(valid, ctx)) == 0

    # Marker lacks coordinates (p2 is Atlantis with null lat/lon)
    no_geo = MapFocusScene(
        id="s001",
        beat_i=1,
        template="map_focus",
        props=MapFocusProps(
            region="world",
            markers=[MapMarker(place_id="p2", label="Underwater")],
            path=False,
        ),
    )
    errs = validate_scene(no_geo, ctx)
    assert any("lacks coordinates" in e for e in errs)

    # Region does not match marker country
    wrong_region = MapFocusScene(
        id="s001",
        beat_i=1,
        template="map_focus",
        props=MapFocusProps(
            region="FRA",
            markers=[MapMarker(place_id="p1", label="Boston Site")],
            path=False,
        ),
    )
    errs = validate_scene(wrong_region, ctx)
    assert any("region 'FRA' does not match" in e for e in errs)


def test_timeline_validation() -> None:
    ctx = _make_dummy_ctx()
    # Valid timeline (date 1919 is grounded)
    valid = TimelineSceneModel(
        id="s001",
        beat_i=1,
        template="timeline",
        props=TimelineProps(
            events=[
                TimelineEvent(date_label="1919", label="The Flood"),
                TimelineEvent(date_label="Jan 1919", label="Cleanup"),
                TimelineEvent(date_label="1919", label="Inquiry"),
            ],
            highlight_index=0,
        ),
    )
    assert len(validate_scene(valid, ctx)) == 0

    # highlight_index out of range rejected by schema
    with pytest.raises(ValidationError):
        TimelineProps(
            events=[
                TimelineEvent(date_label="1919", label="The Flood"),
                TimelineEvent(date_label="Jan 1919", label="Cleanup"),
                TimelineEvent(date_label="1919", label="Inquiry"),
            ],
            highlight_index=5,
        )

    # Ungrounded year (2025 not in transcript) rejected by validate_scene
    ungrounded = TimelineSceneModel(
        id="s001",
        beat_i=1,
        template="timeline",
        props=TimelineProps(
            events=[
                TimelineEvent(date_label="2025", label="Future Event"),
                TimelineEvent(date_label="1919", label="Cleanup"),
                TimelineEvent(date_label="1919", label="Inquiry"),
            ],
            highlight_index=1,
        ),
    )
    errs = validate_scene(ungrounded, ctx)
    assert any("not grounded" in e for e in errs)


def test_validate_plan_rules() -> None:
    ctx = _make_dummy_ctx()
    # Plan with duplicate character intro for c1
    s0 = TitleCardScene(
        id="s000", beat_i=0, template="title_card", props=TitleCardProps(title="Title")
    )
    s1 = CharacterIntroScene(
        id="s001",
        beat_i=1,
        template="character_intro",
        props=CharacterIntroProps(cast_id="c1", descriptor="Hero"),
    )
    # Re-use s1 with different id to simulate duplicate intro
    s2 = CharacterIntroScene(
        id="s002",
        beat_i=2,
        template="character_intro",
        props=CharacterIntroProps(cast_id="c1", descriptor="Hero Again"),
    )
    plan = Storyboard(schema_version=1, aspect="9:16", scenes=[s0, s1, s2])
    errs = validate_plan(ctx.bible, plan, ctx)
    assert any("character_intro for cast_id 'c1' appears more than once" in e for e in errs)

from pathlib import Path

import pytest
from pydantic import ValidationError

from animated_infographics.contracts.models import (
    AvatarConfig,
    Beat,
    Bible,
    CastMember,
    CharacterIntroScene,
    KineticQuoteScene,
    LocationScene,
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
    LocationProps,
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
    word_cap_errors,
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
        props=StatCalloutProps(value=150, decimals=0),
    )
    assert len(validate_scene(valid, ctx)) == 0

    # Ungrounded stat (1500 instead of 150)
    invalid = StatCalloutScene(
        id="s001",
        beat_i=1,
        template="stat_callout",
        props=StatCalloutProps(value=1500, decimals=0),
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
                TimelineEvent(date_label="Feb 1919", label="Inquiry"),
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
                TimelineEvent(date_label="Feb 1919", label="Inquiry"),
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
                TimelineEvent(date_label="Jan 1919", label="Cleanup"),
                TimelineEvent(date_label="Feb 1919", label="Inquiry"),
            ],
            highlight_index=1,
        ),
    )
    errs = validate_scene(ungrounded, ctx)
    assert any("not grounded" in e or "not a date" in e for e in errs)


def test_timeline_labels_validation() -> None:
    """Verify timeline date labels per Issue 4 / Option A (design_testing_and_validation.md)."""
    # Context with 1932, 1934, 2013, Nov 2, 8, 10
    transcript_text = (
        "In 1932 and 1934, things changed. On Nov 2, Nov 8, and Dec 10, records were made. "
        "In 2013, 50 years had passed."
    )
    words = []
    t = 0
    for idx, token in enumerate(transcript_text.split()):
        words.append(TranscriptWord(i=idx, text=token, start_ms=t, end_ms=t + 200, sentence_i=0))
        t += 250
    transcript = Transcript(
        schema_version=1,
        source="tts",
        audio_path="test.wav",
        duration_ms=t + 500,
        words=words,
        sentences=[
            TranscriptSentence(
                i=0,
                text=transcript_text,
                start_ms=0,
                end_ms=t,
                word_start=0,
                word_end=len(words),
                paragraph_i=0,
            )
        ],
    )
    bible = Bible(
        schema_version=1,
        title="Timeline Test",
        logline="Logline",
        genre="history",
        cast=[],
        places=[],
        set_pieces=[],
    )
    beat = Beat(i=1, word_start=0, word_end=len(words), start_ms=0, end_ms=t, text=transcript_text)
    ctx = PlanContext(transcript=transcript, bible=bible, beat=beat)

    def _make_timeline_scene(labels: list[str]) -> TimelineSceneModel:
        return TimelineSceneModel(
            id="s001",
            beat_i=1,
            template="timeline",
            props=TimelineProps(
                events=[
                    TimelineEvent(date_label=lbl, label=f"Event {i}")
                    for i, lbl in enumerate(labels)
                ],
                highlight_index=0,
            ),
        )

    # Wave A defect 1: ["2013", "2013", "2013"] -> rejected (not distinct)
    errs = validate_scene(_make_timeline_scene(["2013", "2013", "2013"]), ctx)
    assert any('date labels repeat ("2013")' in e for e in errs)

    # Wave A defect 2: ["50+ Years", "No Record", "Memory Only"] -> rejected ("No Record")
    errs = validate_scene(_make_timeline_scene(["50+ Years", "No Record", "Memory Only"]), ctx)
    assert any(
        '"No Record" is not a date from the narration or an allowed phrase' in e for e in errs
    )

    # Wave A defect 3: ["Last Spring", "Present", "Now"] -> rejected ("Present")
    errs = validate_scene(_make_timeline_scene(["Last Spring", "Present", "Now"]), ctx)
    assert any('"Present" is not a date from the narration or an allowed phrase' in e for e in errs)

    # Years backwards: ["1934", "1932", "Today"] -> rejected
    errs = validate_scene(_make_timeline_scene(["1934", "1932", "Today"]), ctx)
    assert any("years go backwards (1934 → 1932)" in e for e in errs)

    # Ungrounded digit: ["Nov 2", "June 5", "Dec 10"] ("5" not in transcript) -> rejected
    errs = validate_scene(_make_timeline_scene(["Nov 2", "June 5", "Dec 10"]), ctx)
    assert any('"June 5" is not a date from the narration or an allowed phrase' in e for e in errs)

    # Accepted: ["Nov 2", "Nov 8", "Dec 10"]
    assert len(validate_scene(_make_timeline_scene(["Nov 2", "Nov 8", "Dec 10"]), ctx)) == 0

    # Accepted: ["1932", "1934", "Today"]
    assert len(validate_scene(_make_timeline_scene(["1932", "1934", "Today"]), ctx)) == 0

    # Accepted: ["Last spring", "That weekend", "Months later"]
    scene_rel = _make_timeline_scene(["Last spring", "That weekend", "Months later"])
    assert len(validate_scene(scene_rel, ctx)) == 0

    # Accepted: ["Present day.", "Years later", "Now"] (normalised trailing punctuation)
    scene_norm = _make_timeline_scene(["Present day.", "Years later", "Now"])
    assert len(validate_scene(scene_norm, ctx)) == 0


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


def test_meaning_rules_currency_and_ago() -> None:
    """Validate meaning rules per Issue 5 / Option A (design_planner.md §6 item 6)."""
    ctx = _make_dummy_ctx()
    # ctx.transcript sentences:
    # s0: "The Great Molasses Flood struck in 1919."
    # s1: "About 150 people were injured when the tank burst."
    # (Neither sentence contains "ago")

    # 1. stat_callout.suffix containing $, £, or €
    scene_dollar = StatCalloutScene(
        id="s001",
        beat_i=1,
        template="stat_callout",
        props=StatCalloutProps(value=150.0, decimals=0, display_scale="none", suffix="$"),
    )
    errs_dollar = validate_scene(scene_dollar, ctx)
    assert any("props.suffix: currency symbols belong in prefix" in e for e in errs_dollar)

    scene_pound = StatCalloutScene(
        id="s001",
        beat_i=1,
        template="stat_callout",
        props=StatCalloutProps(value=150.0, decimals=0, display_scale="none", suffix="£"),
    )
    errs_pound = validate_scene(scene_pound, ctx)
    assert any("props.suffix: currency symbols belong in prefix" in e for e in errs_pound)

    scene_euro = StatCalloutScene(
        id="s001",
        beat_i=1,
        template="stat_callout",
        props=StatCalloutProps(value=150.0, decimals=0, display_scale="none", suffix="€"),
    )
    errs_euro = validate_scene(scene_euro, ctx)
    assert any("props.suffix: currency symbols belong in prefix" in e for e in errs_euro)

    scene_dollars_word = StatCalloutScene(
        id="s001",
        beat_i=1,
        template="stat_callout",
        props=StatCalloutProps(
            value=150.0,
            decimals=0,
            display_scale="none",
            suffix="dollars",
        ),
    )
    errs_word = validate_scene(scene_dollars_word, ctx)
    assert not any("currency symbols belong in prefix" in e for e in errs_word)

    # 2. location.era_label containing whole word "ago" when transcript does not
    loc_scene_ago = LocationScene(
        id="s001",
        beat_i=1,
        template="location",
        props=LocationProps(place_id="p1", era_label="40 years ago"),
    )
    errs_ago = validate_scene(loc_scene_ago, ctx)
    assert any('props.era_label: "ago" is not in the narration' in e for e in errs_ago)

    # When transcript DOES contain "ago", era_label with "ago" is accepted
    ago_text = "That happened 40 years ago."
    ago_tokens = ago_text.split()
    ago_words = [
        TranscriptWord(i=i, text=tok, start_ms=i * 200, end_ms=(i + 1) * 200, sentence_i=0)
        for i, tok in enumerate(ago_tokens)
    ]
    ctx_with_ago = PlanContext(
        transcript=Transcript(
            schema_version=1,
            source="tts",
            audio_path="test.wav",
            duration_ms=1000,
            words=ago_words,
            sentences=[
                TranscriptSentence(
                    i=0,
                    text=ago_text,
                    start_ms=0,
                    end_ms=1000,
                    word_start=0,
                    word_end=len(ago_tokens),
                    paragraph_i=0,
                    is_title=False,
                )
            ],
        ),
        bible=ctx.bible,
        beats=ctx.beats,
    )
    errs_with_ago = validate_scene(loc_scene_ago, ctx_with_ago)
    assert not any('"ago" is not in the narration' in e for e in errs_with_ago)


def test_meaning_rule_year_is_not_a_stat() -> None:
    """Validate meaning rule: A year is not a stat (design_planner.md §6 item 6)."""
    bible = Bible(
        schema_version=1,
        title="Room 12",
        logline="Logline",
        genre="personal_story",
        cast=[],
        places=[],
        set_pieces=[],
    )

    def _ctx(text: str) -> PlanContext:
        words = [
            TranscriptWord(i=i, text=tok, start_ms=i * 200, end_ms=(i + 1) * 200, sentence_i=0)
            for i, tok in enumerate(text.split())
        ]
        sentences = [
            TranscriptSentence(
                i=0,
                text=text,
                start_ms=0,
                end_ms=len(words) * 200,
                word_start=0,
                word_end=len(words),
                paragraph_i=0,
                is_title=False,
            )
        ]
        tr = Transcript(
            schema_version=1,
            source="tts",
            audio_path="test.wav",
            duration_ms=len(words) * 200 + 100,
            words=words,
            sentences=sentences,
        )
        beat = Beat(
            i=1,
            word_start=0,
            word_end=len(words),
            start_ms=0,
            end_ms=len(words) * 200,
            text=text,
        )
        return PlanContext(transcript=tr, bible=bible, beat=beat)

    expected_2016_err = (
        "props.value: 2016 is a year in this beat; a year belongs in a timeline or an era label, "
        "not a stat"
    )

    # 1. 2016 with suffix "" -> error
    ctx_2016 = _ctx("She had died in 2016, and March 3rd was her birthday.")
    s_2016 = StatCalloutScene(
        id="s001",
        beat_i=1,
        template="stat_callout",
        props=StatCalloutProps(value=2016.0, decimals=0, display_scale="none", suffix=""),
    )
    errs_2016 = validate_scene(s_2016, ctx_2016)
    assert expected_2016_err in errs_2016

    # 2. 2016 with suffix "Year died" -> error
    s_2016_suffix = StatCalloutScene(
        id="s001",
        beat_i=1,
        template="stat_callout",
        props=StatCalloutProps(value=2016.0, decimals=0, display_scale="none", suffix="Year died"),
    )
    errs_2016_suffix = validate_scene(s_2016_suffix, ctx_2016)
    assert expected_2016_err in errs_2016_suffix

    # 3. 1932 in "In 1932, ..." -> error
    ctx_1932 = _ctx("In 1932, the farmers banded together.")
    s_1932 = StatCalloutScene(
        id="s001",
        beat_i=1,
        template="stat_callout",
        props=StatCalloutProps(value=1932.0, decimals=0, display_scale="none", suffix=""),
    )
    errs_1932 = validate_scene(s_1932, ctx_1932)
    expected_1932_err = (
        "props.value: 1932 is a year in this beat; a year belongs in a timeline or an era label, "
        "not a stat"
    )
    assert expected_1932_err in errs_1932

    # 4. 20,000 -> no error
    ctx_20k = _ctx("about 20,000 emus were running wild across the region.")
    s_20k = StatCalloutScene(
        id="s001",
        beat_i=1,
        template="stat_callout",
        props=StatCalloutProps(value=20000.0, decimals=0, display_scale="none", suffix="emus"),
    )
    errs_20k = validate_scene(s_20k, ctx_20k)
    assert not any("is a year in this beat" in e for e in errs_20k)

    # 5. 312 -> no error
    ctx_312 = _ctx("The box held 312 handwritten cards.")
    s_312 = StatCalloutScene(
        id="s001",
        beat_i=1,
        template="stat_callout",
        props=StatCalloutProps(value=312.0, decimals=0, display_scale="none", suffix="cards"),
    )
    errs_312 = validate_scene(s_312, ctx_312)
    assert not any("is a year in this beat" in e for e in errs_312)

    # 6. 1,500 written with a comma -> no error
    ctx_1500 = _ctx("They deployed 1,500 soldiers to the border.")
    s_1500 = StatCalloutScene(
        id="s001",
        beat_i=1,
        template="stat_callout",
        props=StatCalloutProps(value=1500.0, decimals=0, display_scale="none", suffix="soldiers"),
    )
    errs_1500 = validate_scene(s_1500, ctx_1500)
    assert not any("is a year in this beat" in e for e in errs_1500)


def test_meaning_rule_date_is_not_a_stat() -> None:
    """Validate meaning rule: A date is not a stat (design_planner.md §6 item 6, Wave F)."""
    import json
    from pathlib import Path

    cases_path = Path(__file__).parent / "data" / "wave_f_cases.json"
    cases_data = json.loads(cases_path.read_text(encoding="utf-8"))
    stat_dates = cases_data["stat_dates"]

    bible = Bible(
        schema_version=1,
        title="Room 12",
        logline="Logline",
        genre="personal_story",
        cast=[],
        places=[],
        set_pieces=[],
    )

    def _ctx(text: str) -> PlanContext:
        words = [
            TranscriptWord(i=i, text=tok, start_ms=i * 200, end_ms=(i + 1) * 200, sentence_i=0)
            for i, tok in enumerate(text.split())
        ]
        sentences = [
            TranscriptSentence(
                i=0,
                text=text,
                start_ms=0,
                end_ms=len(words) * 200,
                word_start=0,
                word_end=len(words),
                paragraph_i=0,
                is_title=False,
            )
        ]
        tr = Transcript(
            schema_version=1,
            source="tts",
            audio_path="test.wav",
            duration_ms=len(words) * 200 + 100,
            words=words,
            sentences=sentences,
        )
        beat = Beat(
            i=1,
            word_start=0,
            word_end=len(words),
            start_ms=0,
            end_ms=len(words) * 200,
            text=text,
        )
        return PlanContext(transcript=tr, bible=bible, beat=beat)

    # 1. Real frozen case: March 3rd in "She had died in 2016, and March 3rd was her birthday."
    c0 = stat_dates[0]
    ctx_room12 = _ctx(c0["beat"])
    s_room12 = StatCalloutScene(
        id=c0["scene_id"],
        beat_i=1,
        template="stat_callout",
        props=StatCalloutProps(**c0["props"]),
    )
    errs_room12 = validate_scene(s_room12, ctx_room12)
    assert c0["expected_error"] in errs_room12

    # 2. "3rd of March"
    ctx_3rd_of_march = _ctx("She was born on the 3rd of March before sunrise.")
    s_3rd_of_march = StatCalloutScene(
        id="s001",
        beat_i=1,
        template="stat_callout",
        props=StatCalloutProps(value=3.0, decimals=0, display_scale="none", suffix=""),
    )
    errs_3rd = validate_scene(s_3rd_of_march, ctx_3rd_of_march)
    assert any("is a day of a date in this beat" in e for e in errs_3rd)

    # 3. "November 2"
    ctx_nov2 = _ctx("The first attack came on November 2.")
    s_nov2 = StatCalloutScene(
        id="s001",
        beat_i=1,
        template="stat_callout",
        props=StatCalloutProps(value=2.0, decimals=0, display_scale="none", suffix=""),
    )
    errs_nov2 = validate_scene(s_nov2, ctx_nov2)
    assert any("is a day of a date in this beat" in e for e in errs_nov2)

    # 4. Must NOT error: 3 in "3 soldiers"
    ctx_3_soldiers = _ctx("Major Meredith arrived with 3 soldiers and ammunition.")
    s_3_soldiers = StatCalloutScene(
        id="s001",
        beat_i=1,
        template="stat_callout",
        props=StatCalloutProps(value=3.0, decimals=0, display_scale="none", suffix="soldiers"),
    )
    errs_soldiers = validate_scene(s_3_soldiers, ctx_3_soldiers)
    assert not any("is a day of a date in this beat" in e for e in errs_soldiers)

    # 5. Must NOT error: 20,000 in "about 20,000 emus"
    ctx_20k = _ctx("a drought pushed about 20,000 emus inland onto farms.")
    s_20k = StatCalloutScene(
        id="s001",
        beat_i=1,
        template="stat_callout",
        props=StatCalloutProps(value=20000.0, decimals=0, display_scale="none", suffix="emus"),
    )
    errs_20k = validate_scene(s_20k, ctx_20k)
    assert not any("is a day of a date in this beat" in e for e in errs_20k)

    # 6. Must NOT error: 312 in "The box held 312 handwritten cards"
    ctx_312 = _ctx("The box held 312 handwritten cards, forty years of cooking.")
    s_312 = StatCalloutScene(
        id="s001",
        beat_i=1,
        template="stat_callout",
        props=StatCalloutProps(value=312.0, decimals=0, display_scale="none", suffix="cards"),
    )
    errs_312 = validate_scene(s_312, ctx_312)
    assert not any("is a day of a date in this beat" in e for e in errs_312)


def test_internal_id_errors() -> None:
    """Verify internal_id_errors rejects internal IDs and accepts normal words (C4)."""
    from animated_infographics.planner.validate import internal_id_errors

    avatar = AvatarConfig(
        skin=1,
        hair_style="short",
        hair_color="black",
        facial_hair="none",
        headwear="none",
        glasses=False,
        age="adult",
    )
    bible = Bible(
        schema_version=1,
        title="Recipe Box",
        logline="Grandma's recipe box.",
        genre="personal_story",
        cast=[
            CastMember(
                id="c1", name="Me", role="narrator", is_narrator=True, color_slot=1, avatar=avatar
            ),
            CastMember(
                id="c3", name="Walt", role="friend", is_narrator=False, color_slot=3, avatar=avatar
            ),
            CastMember(
                id="c4",
                name="The Emus",
                role="adversary",
                is_narrator=False,
                color_slot=4,
                avatar=avatar,
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
        ],
        set_pieces=[
            SetPiece(
                id="v1",
                name="the recipe box",
                visual_description="Grandma's recipe box.",
                icon="Package",
            ),
        ],
    )

    # 1. Real Wave B leak strings rejected
    errs_v1 = internal_id_errors(
        "props.caption", "One card missing from the recipe box (v1).", bible
    )
    assert errs_v1 == [
        'props.caption: contains the internal id "v1" — use the name ("the recipe box")'
    ]

    errs_c1_c3 = internal_id_errors("props.text", "c1 buys the Sundowner from c3", bible)
    assert 'props.text: contains the internal id "c1" — use the name ("Me")' in errs_c1_c3
    assert 'props.text: contains the internal id "c3" — use the name ("Walt")' in errs_c1_c3

    errs_c4 = internal_id_errors("props.text", "Feathered adversaries (c4: The Emus)", bible)
    assert errs_c4 == ['props.text: contains the internal id "c4" — use the name ("The Emus")']

    # 2. Approved non-id words accepted
    assert internal_id_errors("props.text", "Plan B", bible) == []
    assert internal_id_errors("props.text", "Route 66", bible) == []
    assert internal_id_errors("props.text", "c3po", bible) == []


def test_validate_scene_rejects_internal_ids() -> None:
    """Verify validate_scene rejects internal id leaks in free text fields."""
    ctx = _make_dummy_ctx()
    # ctx.bible has p1 (Boston) and v1 (The Great Tank)
    scene = KineticQuoteScene(
        id="s001",
        beat_i=1,
        template="kinetic_quote",
        props=KineticQuoteProps(
            text="About 150 people were injured at v1.",
            emphasis=[],
            attribution_cast_id=None,
        ),
    )
    errs = validate_scene(scene, ctx)
    assert any(
        'props.text: contains the internal id "v1" — use the name ("The Great Tank")' in e
        for e in errs
    )


def test_text_audit_counts_id_leaks(tmp_path: Path) -> None:
    """Verify audit_storyboards counts internal id leaks (C4)."""
    import json

    from animated_infographics.evals.text_audit import audit_storyboards

    sb_dir = tmp_path / "job1"
    sb_dir.mkdir()
    bible_json = {
        "schema_version": 1,
        "title": "Recipe Box",
        "logline": "Grandma's recipe box.",
        "genre": "personal_story",
        "cast": [],
        "places": [],
        "set_pieces": [
            {
                "id": "v1",
                "name": "The Recipe Box",
                "visual_description": "A wooden box.",
                "icon": "Package",
            }
        ],
    }
    (sb_dir / "bible.json").write_text(json.dumps(bible_json))

    storyboard_json = {
        "schema_version": 1,
        "scenes": [
            {
                "id": "s001",
                "beat_i": 1,
                "template": "reveal",
                "props": {
                    "kicker": "Mystery",
                    "text": "One card missing from the recipe box (v1).",
                },
            }
        ],
    }
    sb_path = sb_dir / "storyboard.json"
    sb_path.write_text(json.dumps(storyboard_json))

    res = audit_storyboards([sb_path])
    assert res["id_leaks_count"] == 1
    assert any("v1" in e for e in res["id_leaks"][0]["errors"])


def test_word_cap_cases_frozen() -> None:
    """Verify all 9 frozen word cap cases from tests/data/word_cap_cases.json."""
    import json

    cases_path = Path(__file__).resolve().parent / "data" / "word_cap_cases.json"
    data = json.loads(cases_path.read_text(encoding="utf-8"))
    for case in data["cases"]:
        errors = word_cap_errors(case["template"], case["props"])
        msg = f"Failed for {case['template']} {case['scene_id']}"
        assert errors == case["expected_errors"], msg


def test_format_pydantic_validation_error_list_too_long() -> None:
    """Verify list too_long error formatting per D2."""
    from animated_infographics.planner.props import _format_pydantic_validation_error

    err = {
        "type": "too_long",
        "loc": ("items",),
        "input": ["a", "b", "c", "d"],
        "ctx": {"max_length": 3},
    }
    msg = _format_pydantic_validation_error(err)
    assert msg == "props.items: 4 items, limit 3 — keep the most important ones"


def test_deterministic_kinetic_quote_fallback_30_words() -> None:
    """Verify 30-word beat fallback produces <= 12 words, <= 90 chars, verbatim prefix."""
    from animated_infographics.planner.grounding import is_kinetic_quote_grounded
    from animated_infographics.planner.props import build_deterministic_kinetic_quote
    from animated_infographics.planner.words import count_words

    beat_text = (
        "In nineteen nineteen the molasses tank collapsed and flooded the entire north end "
        "of Boston with two million gallons of boiling syrup moving at thirty-five miles "
        "per hour destroying everything."
    )
    tokens = beat_text.split()
    beat = Beat(
        i=1,
        word_start=0,
        word_end=len(tokens),
        start_ms=0,
        end_ms=6000,
        text=beat_text,
    )
    scene = build_deterministic_kinetic_quote("s001", 1, beat)
    assert count_words(scene.props.text) <= 12
    assert len(scene.props.text) <= 90
    assert scene.props.text.endswith("…")
    prefix = scene.props.text.rstrip("…")
    assert beat_text.startswith(prefix)
    valid, errors = is_kinetic_quote_grounded(scene.props.text, [], beat_text)
    assert valid, f"Grounding failed: {errors}"


def test_word_cap_exact_cap_passes() -> None:
    """Verify props at exactly the word cap yield zero errors."""
    props = {
        "heading": "Three Big Things",  # 3 words, cap is 3
        "items": [
            {"icon": "Drop", "label": "One Small Step"},  # 3 words, cap is 3
            {"icon": "WaveSine", "label": "Two Giant Leaps"},  # 3 words, cap is 3
        ],
    }
    assert word_cap_errors("icon_list", props) == []

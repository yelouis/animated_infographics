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


def test_rule_r6_timeline_and_comparison() -> None:
    """Verify rule R6: at most one timeline and at most one comparison per video."""
    choices = [
        Choice(beat_i=0, primary="title_card", alternate="title_card"),
        Choice(beat_i=1, primary="timeline", alternate="location"),
        Choice(beat_i=2, primary="icon_list", alternate="stat_callout"),
        Choice(beat_i=3, primary="timeline", alternate="stat_callout"),
        Choice(beat_i=4, primary="comparison", alternate="dialogue"),
        Choice(beat_i=5, primary="comparison", alternate="comparison"),
    ]
    repaired, repairs = apply_rules(choices, 6)
    r6_repairs = [r for r in repairs if r.rule == "R6"]
    assert len(r6_repairs) == 2
    # Second timeline replaced with alternate 'stat_callout'
    assert repaired[3].primary == "stat_callout"
    assert r6_repairs[0].scene == "s003"
    assert r6_repairs[0].to == "stat_callout"
    # Second comparison whose alternate is comparison replaced with 'kinetic_quote'
    assert repaired[5].primary == "kinetic_quote"
    assert r6_repairs[1].scene == "s005"
    assert r6_repairs[1].to == "kinetic_quote"


def test_recipe_choices_exact() -> None:
    """Verify exact repair list and choices against recipe_choices.json per D3."""
    import json
    from pathlib import Path

    from animated_infographics.contracts.models import Beat

    data_path = Path(__file__).resolve().parent / "data" / "recipe_choices.json"
    data = json.loads(data_path.read_text(encoding="utf-8"))

    bible_data = {
        "schema_version": 1,
        "title": "Recipe Box",
        "logline": "Logline",
        "genre": "personal_story",
        "cast": [
            {
                "id": c["id"],
                "name": c["name"],
                "role": "Role",
                "is_narrator": c.get("is_narrator", False),
                "color_slot": i,
                "avatar": {
                    "skin": 1,
                    "hair_style": "short",
                    "hair_color": "brown",
                    "facial_hair": "none",
                    "headwear": "none",
                    "glasses": False,
                    "age": "adult",
                },
            }
            for i, c in enumerate(data["entities"]["cast"])
        ],
        "places": [
            {
                "id": p["id"],
                "name": p["name"],
                "kind": "real",
                "country_iso3": "USA",
                "lat": 46.78,
                "lon": -92.10,
                "geo_source": "gazetteer",
                "visual_description": "Desc",
                "icon": "Buildings",
            }
            for p in data["entities"]["places"]
        ],
        "set_pieces": [
            {
                "id": s["id"],
                "name": s["name"],
                "visual_description": "Desc",
                "icon": "Package",
            }
            for s in data["entities"]["set_pieces"]
        ],
    }
    bible = Bible.model_validate(bible_data)
    beats = [
        Beat(i=i, word_start=0, word_end=1, start_ms=0, end_ms=1000, text=text)
        for i, text in enumerate(data["beats"])
    ]
    choices = [
        Choice(beat_i=i, primary=c["primary"], alternate=c["alternate"])
        for i, c in enumerate(data["choices"])
    ]

    final_choices, final_repairs = apply_rules(choices, len(choices), beats, bible)

    exp_repairs = data["expected"]["rule_repairs"]
    actual_rep_dicts = [
        {"rule": r.rule, "scene": r.scene, "from": r.from_, "to": r.to} for r in final_repairs
    ]
    assert actual_rep_dicts == exp_repairs

    actual_choice_dicts = [
        {
            "primary": c.primary,
            "alternate": c.alternate,
            **({"rhythm_id": c.rhythm_id} if c.rhythm_id else {}),
        }
        for c in final_choices
    ]
    exp_choice_dicts = data["expected"]["choices"]
    assert actual_choice_dicts == exp_choice_dicts


def test_rhythm_cases_all_seven() -> None:
    """Verify all seven cases in tests/data/rhythm_cases.json."""
    import json
    from pathlib import Path

    from animated_infographics.contracts.templates import REPLACEABLE_TEMPLATES
    from animated_infographics.planner.rhythm import rhythm_target

    data_path = Path(__file__).resolve().parent / "data" / "rhythm_cases.json"
    data = json.loads(data_path.read_text(encoding="utf-8"))

    for case in data["cases"]:
        template_before = case["template_before"]
        if template_before not in REPLACEABLE_TEMPLATES:
            # Kept or Picture templates are never replaced by R7
            assert case["expected"] is None
        else:
            bible_data = {
                "schema_version": 1,
                "title": "Title",
                "logline": "Logline",
                "genre": "personal_story",
                "cast": [
                    {
                        "id": c["id"],
                        "name": c["name"],
                        "role": "Role",
                        "is_narrator": c.get("is_narrator", False),
                        "color_slot": i,
                        "avatar": {
                            "skin": 1,
                            "hair_style": "short",
                            "hair_color": "brown",
                            "facial_hair": "none",
                            "headwear": "none",
                            "glasses": False,
                            "age": "adult",
                        },
                    }
                    for i, c in enumerate(case["entities"].get("cast", []))
                ],
                "places": [
                    {
                        "id": p["id"],
                        "name": p["name"],
                        "kind": "real",
                        "country_iso3": "USA",
                        "lat": 46.78,
                        "lon": -92.10,
                        "geo_source": "gazetteer",
                        "visual_description": "Desc",
                        "icon": "Buildings",
                    }
                    for p in case["entities"].get("places", [])
                ],
                "set_pieces": [
                    {
                        "id": s["id"],
                        "name": s["name"],
                        "visual_description": "Desc",
                        "icon": "Package",
                    }
                    for s in case["entities"].get("set_pieces", [])
                ],
            }
            bible = Bible.model_validate(bible_data)
            res = rhythm_target(
                case["beat"],
                bible,
                prev=case["prev_template"],
                next=case["next_template"],
            )
            if case["expected"] is None:
                assert res is None
            else:
                assert res is not None
                tmpl, eid = res
                assert tmpl == case["expected"]["template"]
                assert eid == case["expected"]["id"]


def test_rhythm_picture_zero_backend_calls() -> None:
    """Verify that an R7 rhythm picture scene triggers 0 LLM backend calls."""
    from typing import Any

    from animated_infographics.contracts.models import (
        Beat,
        Transcript,
        TranscriptSentence,
        TranscriptWord,
    )
    from animated_infographics.planner.llm import LLMBackend
    from animated_infographics.planner.props import plan_storyboard

    class CountingStubBackend(LLMBackend):
        def __init__(self, responses: dict[str, list[dict[str, Any]]]):
            super().__init__()
            self.responses = responses
            self.calls = 0

        def generate_json(self, *, stage: str, **kwargs: Any) -> dict[str, Any]:
            self.calls += 1
            stage_resps = self.responses.get(stage, [])
            if stage_resps:
                return stage_resps.pop(0)
            return {}

    bible = _make_dummy_bible(n_cast=1, n_places=0, n_set_pieces=0)
    bible.cast[0] = bible.cast[0].model_copy(update={"is_narrator": True})

    beat0 = Beat(i=0, word_start=0, word_end=1, start_ms=0, end_ms=1000, text="Title")
    beat1 = Beat(
        i=1, word_start=1, word_end=2, start_ms=1000, end_ms=2000, text="First worded scene."
    )
    beat2 = Beat(
        i=2, word_start=2, word_end=3, start_ms=2000, end_ms=3000, text="I saw everything happen."
    )

    words = [
        TranscriptWord(i=0, sentence_i=0, text="Title", start_ms=0, end_ms=1000),
        TranscriptWord(i=1, sentence_i=1, text="First", start_ms=1000, end_ms=1500),
        TranscriptWord(i=2, sentence_i=1, text="worded", start_ms=1500, end_ms=2000),
        TranscriptWord(i=3, sentence_i=2, text="I", start_ms=2000, end_ms=2500),
        TranscriptWord(i=4, sentence_i=2, text="saw", start_ms=2500, end_ms=3000),
    ]
    sents = [
        TranscriptSentence(
            i=0,
            text="Title",
            start_ms=0,
            end_ms=1000,
            word_start=0,
            word_end=1,
            paragraph_i=0,
            is_title=True,
        ),
        TranscriptSentence(
            i=1,
            text="First worded",
            start_ms=1000,
            end_ms=2000,
            word_start=1,
            word_end=3,
            paragraph_i=0,
            is_title=False,
        ),
        TranscriptSentence(
            i=2,
            text="I saw",
            start_ms=2000,
            end_ms=3000,
            word_start=3,
            word_end=5,
            paragraph_i=0,
            is_title=False,
        ),
    ]
    transcript = Transcript(
        schema_version=1,
        source="tts",
        audio_path="test.wav",
        duration_ms=4000,
        words=words,
        sentences=sents,
    )

    backend = CountingStubBackend(
        {
            "select": [
                {
                    "choices": [
                        {"beat_i": 1, "primary": "kinetic_quote", "alternate": "stat_callout"},
                        {"beat_i": 2, "primary": "comparison", "alternate": "stat_callout"},
                    ]
                }
            ],
            "props": [{"text": "First worded scene.", "emphasis": [], "attribution_cast_id": None}],
        }
    )

    storyboard, report = plan_storyboard(transcript, [beat0, beat1, beat2], bible, backend)

    assert len(storyboard.scenes) == 3
    s2 = storyboard.scenes[2]
    r2 = report.scenes[2]
    assert s2.template == "emotion_beat"
    assert s2.props.cast_id == "c1"
    assert s2.props.emotion == "neutral"
    assert s2.rationale == "rhythm picture"
    assert r2.attempts == 0
    assert r2.fallback_level == 0
    assert r2.critic.status == "not_applicable"

    # Exactly 1 select call + 1 props call for beat 1; beat 2 made 0 props calls
    assert backend.calls == 2


def test_validate_plan_timeline_comparison_limits() -> None:
    """Verify validate_plan rejects more than 1 timeline and more than 1 comparison."""
    from animated_infographics.contracts.models import (
        ComparisonScene,
        Storyboard,
        TimelineSceneModel,
        TitleCardScene,
        Transcript,
    )
    from animated_infographics.contracts.templates import (
        ComparisonPanel,
        ComparisonProps,
        TimelineEvent,
        TimelineProps,
        TitleCardProps,
    )
    from animated_infographics.planner.validate import PlanContext, validate_plan

    bible = _make_dummy_bible()
    ctx = PlanContext(
        transcript=Transcript(
            schema_version=1,
            source="tts",
            audio_path="a.wav",
            duration_ms=1000,
            words=[],
            sentences=[],
        ),
        bible=bible,
        beats=[],
    )

    t_props = TimelineProps(
        events=[
            TimelineEvent(date_label="1919", label="Event One"),
            TimelineEvent(date_label="1920", label="Event Two"),
            TimelineEvent(date_label="1921", label="Event Three"),
        ],
        highlight_index=0,
    )
    c_props = ComparisonProps(
        a=ComparisonPanel(heading="Side A", points=["Point 1"]),
        b=ComparisonPanel(heading="Side B", points=["Point 2"]),
    )

    sb = Storyboard(
        schema_version=1,
        aspect="9:16",
        scenes=[
            TitleCardScene(
                id="s000",
                beat_i=0,
                template="title_card",
                props=TitleCardProps(title="Title"),
            ),
            TimelineSceneModel(id="s001", beat_i=1, template="timeline", props=t_props),
            TimelineSceneModel(id="s002", beat_i=2, template="timeline", props=t_props),
            ComparisonScene(id="s003", beat_i=3, template="comparison", props=c_props),
            ComparisonScene(id="s004", beat_i=4, template="comparison", props=c_props),
        ],
    )

    errors = validate_plan(bible, sb, ctx)
    assert any("storyboard: timeline appears 2 times (max 1 per video)" in e for e in errors)
    assert any("storyboard: comparison appears 2 times (max 1 per video)" in e for e in errors)

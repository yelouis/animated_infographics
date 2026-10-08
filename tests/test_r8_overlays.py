"""Tests for Rule R8 and overlay placement in creative style.

Per design_planner.md §4, design_styles.md §3.5, and design_testing_and_validation.md §2.
"""

from pathlib import Path

import pytest
from PIL import Image

from animated_infographics.compile import compute_scene_overlays
from animated_infographics.contracts.director import (
    AsideDirective,
    DirectorPlan,
    LicenseDropped,
    MetaphorDirective,
    MotifAppearance,
    MotifDirective,
    OverlayDropped,
)
from animated_infographics.contracts.models import (
    CallbackProps,
    CallbackScene,
    ComparisonProps,
    ComparisonScene,
    IconListProps,
    IconListScene,
    KineticQuoteProps,
    KineticQuoteScene,
    MetaphorProps,
    SceneOverlay,
    StatCalloutProps,
    StatCalloutScene,
    Storyboard,
    Timeline,
    TimelineAudio,
    TimelineCallbackScene,
    TimelineKineticQuoteScene,
    TimelineMetaphorScene,
    TimelineNarration,
    TimelineSceneModel,
    TimelineTitleCardScene,
    TitleCardProps,
    TitleCardScene,
)
from animated_infographics.contracts.templates import (
    ComparisonPanel,
    IconListItem,
    TimelineEvent,
    TimelineProps,
)
from animated_infographics.planner.select import Choice, apply_rules
from animated_infographics.planner.words import graphic_words
from animated_infographics.preview import generate_contact_sheet, generate_preview_report


def test_r8_places_metaphor_and_callback() -> None:
    """R8 places metaphor and callback with LLM primary as alternate."""
    choices = [
        Choice(beat_i=0, primary="title_card", alternate="title_card"),
        Choice(beat_i=1, primary="kinetic_quote", alternate="reveal"),
        Choice(beat_i=2, primary="stat_callout", alternate="reveal"),
        Choice(beat_i=3, primary="cause_effect", alternate="icon_list"),
        Choice(beat_i=4, primary="location", alternate="reveal"),
        Choice(beat_i=5, primary="kinetic_quote", alternate="stat_callout"),
    ]

    director_plan = DirectorPlan(
        motifs=[
            MotifDirective(
                id="m1",
                name="the old key",
                appearances=[
                    MotifAppearance(beat_i=1, role="plant"),
                    MotifAppearance(beat_i=5, role="payoff"),
                ],
            )
        ],
        metaphors=[
            MetaphorDirective(
                beat_i=2,
                image="two chairs facing each other",
                label="Mailbox",
            )
        ],
        asides=[],
    )

    repaired, repairs = apply_rules(choices, len(choices), director_plan=director_plan)

    assert repaired[2].primary == "metaphor"
    assert repaired[2].alternate == "stat_callout"

    assert repaired[5].primary == "callback"
    assert repaired[5].alternate == "kinetic_quote"

    r8_repairs = [r for r in repairs if r.rule == "R8"]
    assert len(r8_repairs) == 2
    assert r8_repairs[0].scene == "s002"
    assert r8_repairs[0].to == "metaphor"
    assert r8_repairs[0].from_ == "stat_callout"
    assert r8_repairs[1].scene == "s005"
    assert r8_repairs[1].to == "callback"
    assert r8_repairs[1].from_ == "kinetic_quote"


def test_r2_never_rewrites_r8_scene() -> None:
    """R2 never rewrites an R8 scene; consecutive duplicates rewrite the other scene."""
    choices = [
        Choice(beat_i=0, primary="title_card", alternate="title_card"),
        Choice(beat_i=1, primary="metaphor", alternate="kinetic_quote"),
        Choice(beat_i=2, primary="stat_callout", alternate="reveal"),
    ]
    director_plan = DirectorPlan(
        metaphors=[
            MetaphorDirective(
                beat_i=2,
                image="storm brewing",
                label="Storm",
            )
        ]
    )

    repaired, repairs = apply_rules(choices, len(choices), director_plan=director_plan)

    assert repaired[2].primary == "metaphor"
    assert repaired[1].primary != "metaphor"
    r2_repairs = [r for r in repairs if r.rule == "R2"]
    assert any(r.scene == "s001" for r in r2_repairs)
    assert not any(r.scene == "s002" for r in r2_repairs)


def test_graphic_words_counts_overlay_text() -> None:
    """Overlay text counts toward graphic_words."""
    props = {"value": 10.0, "decimals": 0, "display_scale": "none", "suffix": "items"}
    base_count = graphic_words("stat_callout", props)
    assert base_count == 1

    overlays = [
        SceneOverlay(kind="motif_token", icon="Key", anchor="top_right"),
        SceneOverlay(kind="label", text="Old Relic", anchor="top_left"),
    ]
    with_overlays = graphic_words("stat_callout", props, overlays=overlays)
    assert with_overlays == base_count + 2


def test_token_moves_when_beat_forbidden() -> None:
    """A motif token on a forbidden scene moves to nearest allowed scene.

    Target is <= 2 beats before payoff.
    """
    events = [
        TimelineEvent(date_label="1920", label="Event 1"),
        TimelineEvent(date_label="1921", label="Event 2"),
        TimelineEvent(date_label="1922", label="Event 3"),
    ]
    sb = Storyboard(
        scenes=[
            TitleCardScene(
                id="s000", beat_i=0, template="title_card", props=TitleCardProps(title="Title")
            ),
            KineticQuoteScene(
                id="s001",
                beat_i=1,
                template="kinetic_quote",
                props=KineticQuoteProps(text="Quote one"),
            ),
            TimelineSceneModel(
                id="s002",
                beat_i=2,
                template="timeline",
                props=TimelineProps(events=events, highlight_index=0),
            ),
            StatCalloutScene(
                id="s003",
                beat_i=3,
                template="stat_callout",
                props=StatCalloutProps(value=5.0, decimals=0),
            ),
            CallbackScene(
                id="s004", beat_i=4, template="callback", props=CallbackProps(motif_id="m1")
            ),
        ]
    )
    plan = DirectorPlan(
        motifs=[
            MotifDirective(
                id="m1",
                name="the key",
                icon="Key",
                appearances=[
                    MotifAppearance(beat_i=2, role="plant"),
                    MotifAppearance(beat_i=4, role="payoff"),
                ],
            )
        ]
    )
    overlays_map, dropped = compute_scene_overlays(sb, plan)
    assert len(dropped) == 0
    assert len(overlays_map[1]) == 1
    assert overlays_map[1][0].kind == "motif_token"
    assert overlays_map[1][0].motif_id == "m1"
    assert overlays_map[2] == []


def test_token_drops_when_no_allowed_scene_within_reach() -> None:
    """A motif token with no allowed scene <= 2 beats before payoff is dropped and recorded."""
    events = [
        TimelineEvent(date_label="1920", label="Event 1"),
        TimelineEvent(date_label="1921", label="Event 2"),
        TimelineEvent(date_label="1922", label="Event 3"),
    ]
    sb = Storyboard(
        scenes=[
            TitleCardScene(
                id="s000", beat_i=0, template="title_card", props=TitleCardProps(title="Title")
            ),
            ComparisonScene(
                id="s001",
                beat_i=1,
                template="comparison",
                props=ComparisonProps(
                    a=ComparisonPanel(heading="A", points=["p1"]),
                    b=ComparisonPanel(heading="B", points=["p2"]),
                ),
            ),
            TimelineSceneModel(
                id="s002",
                beat_i=2,
                template="timeline",
                props=TimelineProps(events=events, highlight_index=0),
            ),
            IconListScene(
                id="s003",
                beat_i=3,
                template="icon_list",
                props=IconListProps(
                    items=[
                        IconListItem(icon="Sparkle", label="Item 1"),
                        IconListItem(icon="Sparkle", label="Item 2"),
                    ]
                ),
            ),
            CallbackScene(
                id="s004", beat_i=4, template="callback", props=CallbackProps(motif_id="m1")
            ),
        ]
    )
    plan = DirectorPlan(
        motifs=[
            MotifDirective(
                id="m1",
                name="the key",
                icon="Key",
                appearances=[
                    MotifAppearance(beat_i=2, role="plant"),
                    MotifAppearance(beat_i=4, role="payoff"),
                ],
            )
        ]
    )
    overlays_map, dropped = compute_scene_overlays(sb, plan)
    assert len(dropped) == 1
    assert dropped[0].item["motif_id"] == "m1"
    assert dropped[0].item["beat_i"] == 2
    for s_overlays in overlays_map.values():
        assert len(s_overlays) == 0


def test_aside_moves_and_drops() -> None:
    """An aside on forbidden scene moves <= 1 beat, or drops if none allowed."""
    events = [
        TimelineEvent(date_label="1920", label="Event 1"),
        TimelineEvent(date_label="1921", label="Event 2"),
        TimelineEvent(date_label="1922", label="Event 3"),
    ]
    sb = Storyboard(
        scenes=[
            TitleCardScene(
                id="s000", beat_i=0, template="title_card", props=TitleCardProps(title="Title")
            ),
            KineticQuoteScene(
                id="s001", beat_i=1, template="kinetic_quote", props=KineticQuoteProps(text="Quote")
            ),
            TimelineSceneModel(
                id="s002",
                beat_i=2,
                template="timeline",
                props=TimelineProps(events=events, highlight_index=0),
            ),
            IconListScene(
                id="s003",
                beat_i=3,
                template="icon_list",
                props=IconListProps(
                    items=[
                        IconListItem(icon="Sparkle", label="Item 1"),
                        IconListItem(icon="Sparkle", label="Item 2"),
                    ]
                ),
            ),
            TimelineSceneModel(
                id="s004",
                beat_i=4,
                template="timeline",
                props=TimelineProps(events=events, highlight_index=0),
            ),
        ]
    )
    plan = DirectorPlan(
        asides=[
            AsideDirective(beat_i=2, kind="thought", text="Hmm"),
            AsideDirective(beat_i=4, kind="label", text="Old note"),
        ]
    )
    overlays_map, dropped = compute_scene_overlays(sb, plan)
    assert len(dropped) == 1
    assert dropped[0].item["beat_i"] == 4
    assert len(overlays_map[1]) == 1
    assert overlays_map[1][0].kind == "thought"
    assert overlays_map[1][0].text == "Hmm"


def test_collision_earlier_planned_wins() -> None:
    """When two items collide for the same scene, earlier-planned item wins, other moves."""
    sb = Storyboard(
        scenes=[
            TitleCardScene(
                id="s000", beat_i=0, template="title_card", props=TitleCardProps(title="Title")
            ),
            KineticQuoteScene(
                id="s001",
                beat_i=1,
                template="kinetic_quote",
                props=KineticQuoteProps(text="Quote 1"),
            ),
            StatCalloutScene(
                id="s002",
                beat_i=2,
                template="stat_callout",
                props=StatCalloutProps(value=1.0, decimals=0),
            ),
            KineticQuoteScene(
                id="s003",
                beat_i=3,
                template="kinetic_quote",
                props=KineticQuoteProps(text="Quote 3"),
            ),
            CallbackScene(
                id="s004", beat_i=4, template="callback", props=CallbackProps(motif_id="m1")
            ),
        ]
    )
    plan = DirectorPlan(
        motifs=[
            MotifDirective(
                id="m1",
                name="Key",
                icon="Key",
                appearances=[
                    MotifAppearance(beat_i=1, role="plant"),
                    MotifAppearance(beat_i=4, role="payoff"),
                ],
            ),
            MotifDirective(
                id="m2",
                name="Coin",
                icon="Coins",
                appearances=[
                    MotifAppearance(beat_i=1, role="plant"),
                    MotifAppearance(beat_i=4, role="payoff"),
                ],
            ),
        ]
    )
    overlays_map, dropped = compute_scene_overlays(sb, plan)
    assert len(dropped) == 0
    assert any(o.motif_id == "m1" for o in overlays_map[1])
    assert any(o.motif_id == "m2" for o in overlays_map[2])


def test_capacity_at_most_1_token_and_1_aside() -> None:
    """A scene can take 1 motif token and 1 aside concurrently."""
    sb = Storyboard(
        scenes=[
            TitleCardScene(
                id="s000", beat_i=0, template="title_card", props=TitleCardProps(title="Title")
            ),
            KineticQuoteScene(
                id="s001", beat_i=1, template="kinetic_quote", props=KineticQuoteProps(text="Quote")
            ),
            CallbackScene(
                id="s002", beat_i=2, template="callback", props=CallbackProps(motif_id="m1")
            ),
        ]
    )
    plan = DirectorPlan(
        motifs=[
            MotifDirective(
                id="m1",
                name="Key",
                icon="Key",
                appearances=[
                    MotifAppearance(beat_i=1, role="plant"),
                    MotifAppearance(beat_i=2, role="payoff"),
                ],
            )
        ],
        asides=[
            AsideDirective(beat_i=1, kind="thought", text="Thinking"),
        ],
    )
    overlays_map, dropped = compute_scene_overlays(sb, plan)
    assert len(dropped) == 0
    assert len(overlays_map[1]) == 2
    kinds = {o.kind for o in overlays_map[1]}
    assert kinds == {"motif_token", "thought"}


def test_contact_sheet_badges_and_report_fates(tmp_path: Path) -> None:
    """Preview draws M/C badges and records director item fates in report.json."""
    job_dir = tmp_path / "job"
    preview_dir = job_dir / "preview"
    preview_dir.mkdir(parents=True)

    for sid in ("s000", "s001", "s002", "s003"):
        im = Image.new("RGB", (270, 480), (10, 20, 30))
        im.save(preview_dir / f"scene_{sid}.png")

    timeline = Timeline(
        schema_version=1,
        fps=30,
        width=1080,
        height=1920,
        duration_frames=120,
        plan_sha256="abc",
        audio=TimelineAudio(narration=TimelineNarration(src="audio.wav")),
        scenes=[
            TimelineTitleCardScene(
                id="s000", start_frame=0, end_frame=30, props=TitleCardProps(title="Title")
            ),
            TimelineKineticQuoteScene(
                id="s001",
                start_frame=30,
                end_frame=60,
                props=KineticQuoteProps(text="Quote"),
                overlays=[
                    SceneOverlay(kind="motif_token", icon="Key", anchor="top_right", motif_id="m1")
                ],
            ),
            TimelineMetaphorScene(
                id="s002",
                start_frame=60,
                end_frame=90,
                props=MetaphorProps(image_entity="metaphor_2", label="Bridge"),
            ),
            TimelineCallbackScene(
                id="s003",
                start_frame=90,
                end_frame=120,
                props=CallbackProps(motif_id="m1", label="Key"),
            ),
        ],
    )

    cs_path = generate_contact_sheet(job_dir, timeline, set())
    assert cs_path.is_file()
    with Image.open(cs_path) as cs:
        assert cs.size[0] == 5 * 270

    d_plan = DirectorPlan(
        motifs=[
            MotifDirective(
                id="m1",
                name="Key",
                icon="Key",
                appearances=[
                    MotifAppearance(beat_i=1, role="plant"),
                    MotifAppearance(beat_i=3, role="payoff"),
                ],
            )
        ],
        metaphors=[
            MetaphorDirective(beat_i=2, image="bridge over river", label="Bridge"),
        ],
        asides=[],
        license_dropped=[
            LicenseDropped(item={"kind": "metaphor", "beat_i": 5}, verdict="adds_fact")
        ],
        overlay_dropped=[
            OverlayDropped(
                item={"kind": "thought", "beat_i": 4},
                reason="no_allowed_scene_within_reach",
            )
        ],
    )
    (job_dir / "director.json").write_text(d_plan.model_dump_json(), encoding="utf-8")
    (job_dir / "timeline.json").write_text(timeline.model_dump_json(), encoding="utf-8")

    rep = generate_preview_report(job_dir, None, [], "abc")
    assert "director_items" in rep
    fates = {f"{item['kind']}_{item.get('beat_i')}": item["fate"] for item in rep["director_items"]}
    assert fates["metaphor_2"] == "rendered"
    assert fates["callback_3"] == "rendered"
    assert fates["motif_token_1"] == "rendered"
    assert fates["metaphor_5"] == "license_dropped"
    assert fates["thought_4"] == "overlay_dropped"


def test_scene_overlay_anchor_validator() -> None:
    """SceneOverlay rejects invalid anchor for each overlay kind."""
    # motif_token requires top_right
    SceneOverlay(kind="motif_token", icon="Sparkle", anchor="top_right", motif_id="m1")
    with pytest.raises(ValueError, match="motif_token requires anchor 'top_right'"):
        SceneOverlay(kind="motif_token", icon="Sparkle", anchor="top_left", motif_id="m1")

    # thought requires top_left
    SceneOverlay(kind="thought", text="Hmm", anchor="top_left")
    with pytest.raises(ValueError, match="thought requires anchor 'top_left'"):
        SceneOverlay(kind="thought", text="Hmm", anchor="top_right")

    # label requires top_left
    SceneOverlay(kind="label", text="Old Relic", anchor="top_left")
    with pytest.raises(ValueError, match="label requires anchor 'top_left'"):
        SceneOverlay(kind="label", text="Old Relic", anchor="top_right")

    # prop requires bottom_left
    SceneOverlay(kind="prop", icon="Coins", anchor="bottom_left")
    with pytest.raises(ValueError, match="prop requires anchor 'bottom_left'"):
        SceneOverlay(kind="prop", icon="Coins", anchor="top_left")


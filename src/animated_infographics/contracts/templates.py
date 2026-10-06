"""Template specifications, registry, and props models for all 18 templates."""

from typing import Annotated, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from animated_infographics.contracts.icons import IconName


class TextSlot(BaseModel):
    """Typography and layout bounding box for a text slot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    font: Literal["display", "body"]
    weight: int
    size_max: int
    size_min: int
    max_lines: int
    box_width: int


class SfxCue(BaseModel):
    """Sound effect cue triggered by a template."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Literal["whoosh", "pop", "ding", "hit"]
    at: Literal["start", "item", "count_end"]


class TemplateSpec(BaseModel):
    """Specification of a template declared in the catalogue."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    category: Literal["statement", "people", "place_time", "fallback"]
    props_model: type[BaseModel] = Field(exclude=True)
    use_when: str
    writing_rules: list[str]
    slots: dict[str, TextSlot]
    sfx_cues: list[SfxCue]
    spread: float | None = None
    requires: dict[str, bool]


# ---------------------------------------------------------------------------
# Props models for the 16 templates
# ---------------------------------------------------------------------------


# 2.1 title_card
class TitleCardProps(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field(min_length=1, max_length=60)
    subtitle: str | None = Field(default=None, min_length=1, max_length=80)
    icon: IconName | None = None


# 2.2 kinetic_quote
class KineticQuoteProps(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(min_length=1, max_length=90)
    emphasis: list[Annotated[str, Field(min_length=1, max_length=24)]] = Field(
        default_factory=list, max_length=3
    )
    attribution_cast_id: str | None = Field(default=None, pattern=r"^c[1-8]$")


# 2.3 stat_callout
class StatCalloutProps(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    value: float = Field(ge=0.0)
    decimals: Literal[0, 1, 2]
    prefix: Literal["", "$", "£", "€", "~", "#"] = ""
    display_scale: Literal["none", "thousand", "million", "billion"] = "none"
    suffix: str = Field(default="", max_length=14)
    icon: IconName | None = None


# 2.4 icon_list
class IconListItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    icon: IconName
    label: str = Field(min_length=1, max_length=32)


class IconListProps(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    heading: str | None = Field(default=None, min_length=1, max_length=36)
    items: list[IconListItem] = Field(min_length=2, max_length=3)


# 2.5 reveal
class RevealProps(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kicker: str = Field(min_length=1, max_length=24)
    text: str = Field(min_length=1, max_length=60)


# 2.6 cause_effect
class CauseEffectNode(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str = Field(min_length=1, max_length=36)
    icon: IconName | None = None


class CauseEffectProps(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    nodes: list[CauseEffectNode] = Field(min_length=2, max_length=3)


# 2.7 comparison
class ComparisonPanel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    heading: str = Field(min_length=1, max_length=20)
    cast_id: str | None = Field(default=None, pattern=r"^c[1-8]$")
    icon: IconName | None = None
    points: list[Annotated[str, Field(min_length=1, max_length=32)]] = Field(
        min_length=1, max_length=2
    )


class ComparisonProps(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    a: ComparisonPanel
    b: ComparisonPanel


# 2.8 character_intro
class CharacterIntroProps(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cast_id: str = Field(pattern=r"^c[1-8]$")
    descriptor: str = Field(min_length=1, max_length=48)


# 2.9 dialogue
class DialogueLine(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cast_id: str = Field(pattern=r"^c[1-8]$")
    text: str = Field(min_length=1, max_length=90)
    tone: Literal["neutral", "angry", "happy", "sad", "shocked", "sarcastic"] = "neutral"


class DialogueProps(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    lines: list[DialogueLine] = Field(min_length=1, max_length=2)


# 2.10 text_thread
class TextMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    from_: Literal["me", "them"] = Field(alias="from")
    text: str = Field(min_length=1, max_length=80)


class TextThreadProps(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contact_name: str = Field(min_length=1, max_length=20)
    contact_cast_id: str | None = Field(default=None, pattern=r"^c[1-8]$")
    messages: list[TextMessage] = Field(min_length=2, max_length=3)


# 2.11 emotion_beat
class EmotionBeatProps(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cast_id: str = Field(pattern=r"^c[1-8]$")
    emotion: Literal["neutral", "happy", "sad", "angry", "shocked", "confused", "smug", "nervous"]


# 2.12 relationship_map
class RelationshipEdge(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    from_id: str = Field(pattern=r"^c[1-8]$")
    to_id: str = Field(pattern=r"^c[1-8]$")
    label: str = Field(min_length=1, max_length=18)
    style: Literal["solid", "dashed", "broken"] = "solid"


class RelationshipMapProps(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cast_ids: list[Annotated[str, Field(pattern=r"^c[1-8]$")]] = Field(min_length=2, max_length=5)
    edges: list[RelationshipEdge] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def validate_relationships(self) -> "RelationshipMapProps":
        if len(self.cast_ids) != len(set(self.cast_ids)):
            raise ValueError("cast_ids must contain unique ids")
        cast_set = set(self.cast_ids)
        seen_pairs: set[frozenset[str]] = set()
        for edge in self.edges:
            if edge.from_id not in cast_set:
                raise ValueError(f"edge endpoint {edge.from_id} not in cast_ids")
            if edge.to_id not in cast_set:
                raise ValueError(f"edge endpoint {edge.to_id} not in cast_ids")
            if edge.from_id == edge.to_id:
                raise ValueError("edge cannot connect a character to themselves")
            pair = frozenset([edge.from_id, edge.to_id])
            if pair in seen_pairs:
                raise ValueError(f"duplicate edge between {edge.from_id} and {edge.to_id}")
            seen_pairs.add(pair)
        return self


# 2.13 location
class LocationProps(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    place_id: str = Field(pattern=r"^p[1-4]$")
    era_label: str | None = Field(default=None, min_length=1, max_length=12)


# 2.14 set_piece
class SetPieceProps(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    set_piece_id: str = Field(pattern=r"^v[1-3]$")


# 2.15 map_focus
class MapMarker(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    place_id: str = Field(pattern=r"^p[1-4]$")
    label: str = Field(min_length=1, max_length=24)


class MapFocusProps(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    region: str = Field(pattern=r"^(world|[A-Z]{3})$")
    markers: list[MapMarker] = Field(min_length=1, max_length=3)
    path: bool = False


# 2.16 timeline
class TimelineEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    date_label: str = Field(min_length=1, max_length=14)
    label: str = Field(min_length=1, max_length=28)


class TimelineProps(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    events: list[TimelineEvent] = Field(min_length=3, max_length=4)
    highlight_index: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_highlight_index(self) -> "TimelineProps":
        if self.highlight_index >= len(self.events):
            raise ValueError(
                f"highlight_index {self.highlight_index} out of range for {len(self.events)} events"
            )
        return self


# 2.17 metaphor
class MetaphorProps(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    image_entity: str
    label: str | None = Field(default=None, max_length=24)
    cast_ids: list[str] = Field(default_factory=list, max_length=2)


# 2.18 callback
class CallbackProps(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    motif_id: str
    label: str | None = Field(default=None, max_length=24)
    set_piece_id: str | None = None
    icon: IconName | None = None


# Union of all 18 template props models
TemplateProps = (
    TitleCardProps
    | KineticQuoteProps
    | StatCalloutProps
    | IconListProps
    | RevealProps
    | CauseEffectProps
    | ComparisonProps
    | CharacterIntroProps
    | DialogueProps
    | TextThreadProps
    | EmotionBeatProps
    | RelationshipMapProps
    | LocationProps
    | SetPieceProps
    | MapFocusProps
    | TimelineProps
    | MetaphorProps
    | CallbackProps
)


# ---------------------------------------------------------------------------
# Template Registry
# ---------------------------------------------------------------------------

REGISTRY: dict[str, TemplateSpec] = {
    "title_card": TemplateSpec(
        name="title_card",
        category="fallback",
        props_model=TitleCardProps,
        use_when="scene 0, always (forced; never LLM-selected).",
        writing_rules=["title <= 60 chars", "subtitle <= 80 chars"],
        slots={
            "title": TextSlot(
                font="display", weight=800, size_max=104, size_min=64, max_lines=3, box_width=900
            ),
            "subtitle": TextSlot(
                font="body", weight=600, size_max=44, size_min=32, max_lines=2, box_width=860
            ),
        },
        sfx_cues=[SfxCue(role="whoosh", at="start")],
        spread=None,
        requires={"cast": False, "places": False, "set_pieces": False, "geo": False},
    ),
    "kinetic_quote": TemplateSpec(
        name="kinetic_quote",
        category="fallback",
        props_model=KineticQuoteProps,
        use_when="a line worth emphasising and nothing more specific fits.",
        writing_rules=[
            "text is a verbatim span of this beat, at most 12 words",
            "each emphasis word is a whole word of text",
        ],
        slots={
            "text": TextSlot(
                font="display", weight=800, size_max=84, size_min=56, max_lines=5, box_width=920
            ),
            "attribution_name": TextSlot(
                font="body", weight=700, size_max=36, size_min=28, max_lines=1, box_width=600
            ),
        },
        sfx_cues=[],
        spread=None,
        requires={"cast": False, "places": False, "set_pieces": False, "geo": False},
    ),
    "stat_callout": TemplateSpec(
        name="stat_callout",
        category="statement",
        props_model=StatCalloutProps,
        use_when="a specific number is the point of the beat.",
        writing_rules=[
            "value must be a number said in this beat",
            'suffix is the unit, at most 2 words (e.g. "gallons", "feet high")',
        ],
        slots={
            "value": TextSlot(
                font="display", weight=800, size_max=200, size_min=110, max_lines=1, box_width=940
            ),
            "suffix": TextSlot(
                font="display", weight=700, size_max=64, size_min=44, max_lines=1, box_width=900
            ),
        },
        sfx_cues=[SfxCue(role="ding", at="count_end")],
        spread=0.4,
        requires={"cast": False, "places": False, "set_pieces": False, "geo": False},
    ),
    "icon_list": TemplateSpec(
        name="icon_list",
        category="statement",
        props_model=IconListProps,
        use_when="2-3 parallel things (demands, causes, items, reasons).",
        writing_rules=[
            "2 to 3 items",
            "heading is optional, at most 3 words",
            "each label at most 3 words: a name or short noun phrase, not a sentence",
        ],
        slots={
            "heading": TextSlot(
                font="display", weight=800, size_max=64, size_min=44, max_lines=2, box_width=900
            ),
            "label": TextSlot(
                font="body", weight=700, size_max=48, size_min=34, max_lines=2, box_width=700
            ),
        },
        sfx_cues=[SfxCue(role="pop", at="item")],
        spread=0.5,
        requires={"cast": False, "places": False, "set_pieces": False, "geo": False},
    ),
    "reveal": TemplateSpec(
        name="reveal",
        category="statement",
        props_model=RevealProps,
        use_when="a twist, punchline or verdict.",
        writing_rules=[
            'kicker at most 3 words (rendered uppercase, e.g. "PLOT TWIST")',
            "text at most 6 words",
            "at most 2 per video (planner R4)",
        ],
        slots={
            "kicker": TextSlot(
                font="display", weight=800, size_max=56, size_min=40, max_lines=1, box_width=900
            ),
            "text": TextSlot(
                font="display", weight=800, size_max=96, size_min=60, max_lines=4, box_width=920
            ),
        },
        sfx_cues=[SfxCue(role="hit", at="start")],
        spread=None,
        requires={"cast": False, "places": False, "set_pieces": False, "geo": False},
    ),
    "cause_effect": TemplateSpec(
        name="cause_effect",
        category="statement",
        props_model=CauseEffectProps,
        use_when="X led to Y (to Z).",
        writing_rules=[
            "2 to 3 nodes in sequence",
            "each label at most 3 words",
        ],
        slots={
            "label": TextSlot(
                font="body", weight=700, size_max=44, size_min=32, max_lines=2, box_width=620
            ),
        },
        sfx_cues=[SfxCue(role="pop", at="item")],
        spread=0.6,
        requires={"cast": False, "places": False, "set_pieces": False, "geo": False},
    ),
    "comparison": TemplateSpec(
        name="comparison",
        category="statement",
        props_model=ComparisonProps,
        use_when="A versus B (two people, two prices, before/after).",
        writing_rules=[
            "each heading at most 3 words",
            "1 to 2 points per side, each at most 3 words",
        ],
        slots={
            "heading": TextSlot(
                font="display", weight=800, size_max=56, size_min=40, max_lines=1, box_width=760
            ),
            "point": TextSlot(
                font="body", weight=600, size_max=38, size_min=28, max_lines=2, box_width=820
            ),
        },
        sfx_cues=[SfxCue(role="whoosh", at="start"), SfxCue(role="pop", at="item")],
        spread=0.3,
        requires={"cast": False, "places": False, "set_pieces": False, "geo": False},
    ),
    "character_intro": TemplateSpec(
        name="character_intro",
        category="people",
        props_model=CharacterIntroProps,
        use_when="a person's first real appearance.",
        writing_rules=[
            (
                "descriptor at most 4 words, saying who they are, not their name"
                ' (e.g. "The motel manager")'
            ),
            "at most once per cast_id per video (planner R3)",
        ],
        slots={
            "name": TextSlot(
                font="display", weight=800, size_max=96, size_min=64, max_lines=1, box_width=900
            ),
            "descriptor": TextSlot(
                font="body", weight=600, size_max=44, size_min=32, max_lines=2, box_width=860
            ),
        },
        sfx_cues=[SfxCue(role="pop", at="start")],
        spread=None,
        requires={"cast": True, "places": False, "set_pieces": False, "geo": False},
    ),
    "dialogue": TemplateSpec(
        name="dialogue",
        category="people",
        props_model=DialogueProps,
        use_when="someone says something (quoted or reported speech).",
        writing_rules=[
            "1 to 2 lines",
            "each line at most 10 words",
        ],
        slots={
            "line": TextSlot(
                font="body", weight=700, size_max=44, size_min=32, max_lines=4, box_width=628
            ),
        },
        sfx_cues=[SfxCue(role="pop", at="item")],
        spread=0.6,
        requires={"cast": True, "places": False, "set_pieces": False, "geo": False},
    ),
    "text_thread": TemplateSpec(
        name="text_thread",
        category="people",
        props_model=TextThreadProps,
        use_when="text messages, DMs, chats.",
        writing_rules=[
            "contact_name at most 3 words",
            "2 to 3 messages",
            "each message at most 8 words",
        ],
        slots={
            "contact": TextSlot(
                font="body", weight=700, size_max=40, size_min=30, max_lines=1, box_width=560
            ),
            "message": TextSlot(
                font="body", weight=600, size_max=38, size_min=30, max_lines=4, box_width=476
            ),
        },
        sfx_cues=[SfxCue(role="pop", at="item")],
        spread=0.7,
        requires={"cast": False, "places": False, "set_pieces": False, "geo": False},
    ),
    "emotion_beat": TemplateSpec(
        name="emotion_beat",
        category="people",
        props_model=EmotionBeatProps,
        use_when="a reaction or feeling is the point.",
        writing_rules=[
            "emotion is the feeling this beat shows for that person; neutral if it shows none",
        ],
        slots={},
        sfx_cues=[],
        spread=None,
        requires={"cast": True, "places": False, "set_pieces": False, "geo": False},
    ),
    "relationship_map": TemplateSpec(
        name="relationship_map",
        category="people",
        props_model=RelationshipMapProps,
        use_when="how 2-5 people relate (family, alliances, betrayals).",
        writing_rules=[
            "2 to 5 cast_ids unique",
            "1 to 6 edges",
            "every edge endpoint in cast_ids",
            "no duplicate unordered pairs",
            "each edge label at most 3 words",
        ],
        slots={
            "name": TextSlot(
                font="body", weight=700, size_max=32, size_min=24, max_lines=1, box_width=220
            ),
            "edge_label": TextSlot(
                font="body", weight=700, size_max=30, size_min=24, max_lines=1, box_width=260
            ),
        },
        sfx_cues=[SfxCue(role="pop", at="start")],
        spread=None,
        requires={"cast": True, "places": False, "set_pieces": False, "geo": False},
    ),
    "location": TemplateSpec(
        name="location",
        category="place_time",
        props_model=LocationProps,
        use_when="arriving somewhere, or establishing where the story is.",
        writing_rules=[
            "era_label is optional, at most 2 words",
            "era_label digit grounding",
        ],
        slots={
            "name": TextSlot(
                font="display", weight=800, size_max=72, size_min=48, max_lines=2, box_width=880
            ),
            "era": TextSlot(
                font="display", weight=800, size_max=44, size_min=32, max_lines=1, box_width=240
            ),
        },
        sfx_cues=[SfxCue(role="whoosh", at="start")],
        spread=None,
        requires={"cast": False, "places": True, "set_pieces": False, "geo": False},
    ),
    "set_piece": TemplateSpec(
        name="set_piece",
        category="place_time",
        props_model=SetPieceProps,
        use_when="a key object or moment is the subject.",
        writing_rules=[
            "set_piece_id is the object this beat is about",
        ],
        slots={
            "name": TextSlot(
                font="display", weight=800, size_max=72, size_min=48, max_lines=2, box_width=880
            ),
        },
        sfx_cues=[SfxCue(role="whoosh", at="start")],
        spread=None,
        requires={"cast": False, "places": False, "set_pieces": True, "geo": False},
    ),
    "map_focus": TemplateSpec(
        name="map_focus",
        category="place_time",
        props_model=MapFocusProps,
        use_when="a journey, or where something is.",
        writing_rules=[
            "1 to 3 markers",
            "region is 'world' or ISO3",
            "each marker label at most 3 words",
        ],
        slots={
            "marker_label": TextSlot(
                font="display", weight=800, size_max=40, size_min=30, max_lines=1, box_width=360
            ),
        },
        sfx_cues=[SfxCue(role="pop", at="item")],
        spread=0.3,
        requires={"cast": False, "places": True, "set_pieces": False, "geo": True},
    ),
    "timeline": TemplateSpec(
        name="timeline",
        category="place_time",
        props_model=TimelineProps,
        use_when="3-4 dated events in sequence.",
        writing_rules=[
            "3 to 4 events",
            "0 <= highlight_index < len(events)",
            "date_label at most 3 words",
            "label at most 3 words",
            (
                "date_label is a date or year said in the narration, or exactly one of: "
                "Today, Now, Present day, That night, That weekend, The next day, "
                "Days later, Weeks later, Months later, Years later, "
                "Last spring, Last summer, Last fall, Last winter, Last year, Earlier, Later"
            ),
            "labels all differ and run forward in time",
        ],
        slots={
            "date": TextSlot(
                font="display", weight=800, size_max=44, size_min=32, max_lines=1, box_width=760
            ),
            "label": TextSlot(
                font="body", weight=600, size_max=40, size_min=28, max_lines=2, box_width=760
            ),
        },
        sfx_cues=[SfxCue(role="pop", at="item")],
        spread=0.6,
        requires={"cast": False, "places": False, "set_pieces": False, "geo": False},
    ),
    "metaphor": TemplateSpec(
        name="metaphor",
        category="place_time",
        props_model=MetaphorProps,
        use_when="creative style: an ungrounded visual metaphor placed by rule R8.",
        writing_rules=[
            "label is optional, at most 3 words",
            "cast_ids has at most 2 cast avatars",
        ],
        slots={
            "label": TextSlot(
                font="display", weight=800, size_max=72, size_min=48, max_lines=2, box_width=880
            ),
        },
        sfx_cues=[SfxCue(role="whoosh", at="start")],
        spread=None,
        requires={"cast": False, "places": False, "set_pieces": False, "geo": False},
    ),
    "callback": TemplateSpec(
        name="callback",
        category="place_time",
        props_model=CallbackProps,
        use_when="creative style: payoff scene calling back to a recurring motif.",
        writing_rules=[
            "label is optional, at most 3 words",
        ],
        slots={
            "label": TextSlot(
                font="display", weight=800, size_max=72, size_min=48, max_lines=2, box_width=880
            ),
        },
        sfx_cues=[SfxCue(role="ding", at="item")],
        spread=0.4,
        requires={"cast": False, "places": False, "set_pieces": False, "geo": False},
    ),
}

WORD_CAPS: Final[dict[str, dict[str, int]]] = {
    "kinetic_quote": {"text": 12},
    "stat_callout": {"suffix": 2},
    "icon_list": {"heading": 3, "items[].label": 3},
    "reveal": {"kicker": 3, "text": 6},
    "cause_effect": {"nodes[].label": 3},
    "comparison": {"a.heading": 3, "b.heading": 3, "a.points[]": 3, "b.points[]": 3},
    "character_intro": {"descriptor": 4},
    "dialogue": {"lines[].text": 10},
    "text_thread": {"contact_name": 3, "messages[].text": 8},
    "relationship_map": {"edges[].label": 3},
    "location": {"era_label": 2},
    "map_focus": {"markers[].label": 3},
    "timeline": {"events[].date_label": 3, "events[].label": 3},
    "metaphor": {"label": 3},
    "callback": {"label": 3},
}

PICTURE_TEMPLATES: Final[frozenset[str]] = frozenset(
    {"emotion_beat", "set_piece", "location", "stat_callout", "map_focus", "metaphor", "callback"}
)
REPLACEABLE_TEMPLATES: Final[frozenset[str]] = frozenset(
    {"kinetic_quote", "cause_effect", "icon_list", "comparison", "timeline", "relationship_map"}
)
KEPT_TEMPLATES: Final[frozenset[str]] = frozenset(
    {"title_card", "character_intro", "dialogue", "text_thread", "reveal"}
)

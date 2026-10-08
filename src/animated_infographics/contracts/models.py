"""Pydantic v2 data models for animated_infographics contracts.

Every model is frozen and extra="forbid". Every top-level model carries
schema_version: Literal[1].
"""

from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator

from animated_infographics.contracts.icons import IconName
from animated_infographics.contracts.styles import StyleName
from animated_infographics.contracts.templates import (
    CallbackProps,
    CauseEffectProps,
    CharacterIntroProps,
    ComparisonProps,
    DialogueProps,
    EmotionBeatProps,
    IconListProps,
    KineticQuoteProps,
    LocationProps,
    MapFocusProps,
    MetaphorProps,
    RelationshipMapProps,
    RevealProps,
    SectionTitleProps,
    SetPieceProps,
    StatCalloutProps,
    TextThreadProps,
    TimelineProps,
    TitleCardProps,
)

# ---------------------------------------------------------------------------
# Section 9: VoiceDecision
# ---------------------------------------------------------------------------


class VoiceDecision(BaseModel):
    """Narrator voice selection record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    voice: Literal["af_heart", "am_michael"]
    source: Literal["auto", "flag"]
    reason: Literal["flag", "third_person", "tag", "llm", "no_evidence"]
    perspective: Literal["first_person", "third_person"] | None = None
    first_person_rate: float | None = None
    narrator_gender: Literal["female", "male", "unknown"] | None = None
    evidence: str | None = None

    @model_validator(mode="after")
    def validate_invariants(self) -> "VoiceDecision":
        # 1. source == "flag" <=> reason == "flag" <=>
        # perspective, first_person_rate, narrator_gender and evidence are all null
        if self.source == "flag":
            if self.reason != "flag":
                raise ValueError("source 'flag' requires reason 'flag'")
            if (
                self.perspective is not None
                or self.first_person_rate is not None
                or self.narrator_gender is not None
                or self.evidence is not None
            ):
                raise ValueError("source 'flag' requires all analysis fields to be null")
        else:
            if self.reason == "flag":
                raise ValueError("reason 'flag' requires source 'flag'")
            if (
                self.perspective is None
                or self.first_person_rate is None
                or self.narrator_gender is None
            ):
                raise ValueError(
                    "source 'auto' requires perspective, first_person_rate, "
                    "and narrator_gender to be set"
                )

        # 3. If reason in {tag, llm}, then evidence is non-null
        # and narrator_gender in {female, male}
        if self.reason in {"tag", "llm"}:
            if self.evidence is None:
                raise ValueError(f"reason '{self.reason}' requires non-null evidence")
            if self.narrator_gender not in {"female", "male"}:
                raise ValueError(
                    f"reason '{self.reason}' requires narrator_gender in {{female, male}}"
                )

        # 4. If reason == "third_person", then perspective == "third_person"
        if self.reason == "third_person":
            if self.perspective != "third_person":
                raise ValueError("reason 'third_person' requires perspective 'third_person'")
            if self.narrator_gender != "unknown":
                raise ValueError("reason 'third_person' requires narrator_gender 'unknown'")
            if self.evidence is not None:
                raise ValueError("reason 'third_person' requires evidence to be null")

        # If reason == "no_evidence", evidence must be null
        if self.reason == "no_evidence":
            if self.evidence is not None:
                raise ValueError("reason 'no_evidence' requires evidence to be null")

        # 5. voice == "af_heart" with source == "auto" <=>
        # perspective == "first_person" and narrator_gender == "female"
        if self.source == "auto":
            is_af_heart_condition = (
                self.perspective == "first_person" and self.narrator_gender == "female"
            )
            if self.voice == "af_heart" and not is_af_heart_condition:
                raise ValueError(
                    "voice 'af_heart' in auto mode requires first_person and female narrator"
                )
            if self.voice != "af_heart" and is_af_heart_condition:
                raise ValueError(
                    "first_person female narrator in auto mode requires voice 'af_heart'"
                )

        return self


# ---------------------------------------------------------------------------
# Section 1: Ingest & Narration
# ---------------------------------------------------------------------------


class IngestRecord(BaseModel):
    """Normalized input ingestion record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    kind: Literal["text", "audio"]
    source: str
    title: str | None = None
    paragraphs: list[str] | None = None
    word_count: int | None = None
    music: str | None = None
    sfx_dir: str | None = None
    style: StyleName = "literal"
    perturb: Literal["mild", "strong"] | None = None
    seed: int | None = None
    tiebreak: Literal["none", "llm"] | None = None


class SentenceOffset(BaseModel):
    """Sentence audio offset in milliseconds."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    i: int
    start_ms: int
    end_ms: int


class NarrationOffsets(BaseModel):
    """Narration sentence timing record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    voice: Literal["af_heart", "am_michael"]
    sentences: list[SentenceOffset]


class LoudnessReport(BaseModel):
    """EBU R128 loudness measurement report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    integrated_lufs: float
    true_peak_dbtp: float
    lra: float


# ---------------------------------------------------------------------------
# Section 2: Transcript
# ---------------------------------------------------------------------------


class TranscriptWord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    i: int
    text: str
    start_ms: int
    end_ms: int
    sentence_i: int


class TranscriptSentence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    i: int
    text: str
    start_ms: int
    end_ms: int
    word_start: int
    word_end: int
    paragraph_i: int
    is_title: bool = False


class Transcript(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    source: Literal["tts", "asr"]
    audio_path: str
    duration_ms: int = Field(ge=0)
    words: list[TranscriptWord]
    sentences: list[TranscriptSentence]

    @model_validator(mode="after")
    def validate_transcript_invariants(self) -> "Transcript":
        for idx, w in enumerate(self.words):
            if w.i != idx:
                raise ValueError(f"Word at position {idx} has i={w.i}, expected {idx}")
            if w.end_ms <= w.start_ms:
                raise ValueError(f"Word {idx} has end_ms <= start_ms ({w.end_ms} <= {w.start_ms})")
            if idx > 0 and w.start_ms < self.words[idx - 1].end_ms:
                raise ValueError(f"Word {idx} start_ms < previous word end_ms")

        if self.words and self.duration_ms < self.words[-1].end_ms:
            raise ValueError(
                f"duration_ms ({self.duration_ms}) < last word end_ms ({self.words[-1].end_ms})"
            )

        # sentences partition words exactly, contiguous and in order
        if self.sentences:
            if self.sentences[0].word_start != 0:
                raise ValueError("First sentence word_start must be 0")
            for idx, s in enumerate(self.sentences):
                if s.i != idx:
                    raise ValueError(f"Sentence at position {idx} has i={s.i}, expected {idx}")
                if idx > 0 and s.word_start != self.sentences[idx - 1].word_end:
                    raise ValueError(f"Sentence {idx} word_start != previous sentence word_end")
                if s.word_end < s.word_start:
                    raise ValueError(f"Sentence {idx} word_end < word_start")
                for w_idx in range(s.word_start, s.word_end):
                    if w_idx < len(self.words) and self.words[w_idx].sentence_i != s.i:
                        raise ValueError(f"Word {w_idx} sentence_i does not match sentence {s.i}")
            if self.sentences[-1].word_end != len(self.words):
                raise ValueError("Last sentence word_end must equal total words count")

        # at most one sentence has is_title: True, and if present it is sentence 0
        title_sentences = [s for s in self.sentences if s.is_title]
        if len(title_sentences) > 1:
            raise ValueError("At most one sentence can have is_title=True")
        if title_sentences and title_sentences[0].i != 0:
            raise ValueError("is_title=True can only be on sentence 0")

        return self


# ---------------------------------------------------------------------------
# Section 3: Bible
# ---------------------------------------------------------------------------


class AvatarConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    skin: int = Field(ge=0, le=5)
    hair_style: Literal["short", "long", "bun", "curly", "ponytail", "bald"]
    hair_color: Literal["black", "brown", "blonde", "red", "gray", "white"]
    facial_hair: Literal["none", "beard", "mustache"]
    headwear: Literal["none", "hat", "crown", "military_cap", "helmet", "headscarf"]
    glasses: bool
    age: Literal["child", "adult", "elder"]


class CastMember(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^c[1-8]$")
    name: str = Field(min_length=1, max_length=24)
    role: str = Field(min_length=1, max_length=40)
    is_narrator: bool = False
    color_slot: int = Field(ge=0, le=7)
    avatar: AvatarConfig


class Place(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^p[1-4]$")
    name: str = Field(min_length=1, max_length=40)
    kind: Literal["real", "fictional"]
    country_iso3: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    lon: float | None = Field(default=None, ge=-180.0, le=180.0)
    geo_source: Literal["gazetteer", "llm", "none"]
    visual_description: str = Field(min_length=1, max_length=200)
    icon: IconName

    @model_validator(mode="after")
    def validate_geo(self) -> "Place":
        if (self.lat is None) != (self.lon is None):
            raise ValueError("lat and lon must both be set or both be null")
        return self


class SetPiece(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^v[1-3]$")
    name: str = Field(min_length=1, max_length=40)
    visual_description: str = Field(min_length=1, max_length=200)
    icon: IconName


class Bible(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    title: str = Field(min_length=1, max_length=60)
    logline: str = Field(min_length=1, max_length=140)
    genre: Literal["history", "personal_story", "other"]
    cast: list[CastMember] = Field(default_factory=list, max_length=8)
    places: list[Place] = Field(default_factory=list, max_length=4)
    set_pieces: list[SetPiece] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def validate_bible(self) -> "Bible":
        # cast id unique
        cast_ids = [c.id for c in self.cast]
        if len(cast_ids) != len(set(cast_ids)):
            raise ValueError("cast ids must be unique")
        # color_slot unique across cast
        color_slots = [c.color_slot for c in self.cast]
        if len(color_slots) != len(set(color_slots)):
            raise ValueError("cast color_slots must be unique across cast")
        # at most one is_narrator
        narrators = [c for c in self.cast if c.is_narrator]
        if len(narrators) > 1:
            raise ValueError("at most one cast member can have is_narrator: true")

        # places id unique
        place_ids = [p.id for p in self.places]
        if len(place_ids) != len(set(place_ids)):
            raise ValueError("place ids must be unique")

        # set pieces id unique
        sp_ids = [v.id for v in self.set_pieces]
        if len(sp_ids) != len(set(sp_ids)):
            raise ValueError("set piece ids must be unique")

        return self


# ---------------------------------------------------------------------------
# Section 4: Beats
# ---------------------------------------------------------------------------


class Beat(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    i: int
    word_start: int
    word_end: int
    start_ms: int
    end_ms: int
    text: str


class Beats(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    beats: list[Beat]

    @model_validator(mode="after")
    def validate_beats(self) -> "Beats":
        if self.beats:
            if self.beats[0].start_ms != 0:
                raise ValueError("beats[0].start_ms must be 0")
            if self.beats[0].word_start != 0:
                raise ValueError("beats[0].word_start must be 0")
            for idx, b in enumerate(self.beats):
                if b.i != idx:
                    raise ValueError(f"Beat at position {idx} has i={b.i}, expected {idx}")
                if b.end_ms <= b.start_ms:
                    raise ValueError(f"Beat {idx} end_ms <= start_ms")
                if b.word_end <= b.word_start:
                    raise ValueError(f"Beat {idx} word_end <= word_start")
                if idx > 0:
                    if b.start_ms != self.beats[idx - 1].end_ms:
                        raise ValueError(f"Beat {idx} start_ms != previous beat end_ms")
                    if b.word_start != self.beats[idx - 1].word_end:
                        raise ValueError(f"Beat {idx} word_start != previous beat word_end")
        return self


# ---------------------------------------------------------------------------
# Section 5: Storyboard Scenes (discriminated union on template)
# ---------------------------------------------------------------------------


class TitleCardScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    beat_i: int
    template: Literal["title_card"] = "title_card"
    props: TitleCardProps
    mute_sfx: bool = False
    rationale: str = Field(default="", max_length=140)


class KineticQuoteScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    beat_i: int
    template: Literal["kinetic_quote"] = "kinetic_quote"
    props: KineticQuoteProps
    mute_sfx: bool = False
    rationale: str = Field(default="", max_length=140)


class StatCalloutScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    beat_i: int
    template: Literal["stat_callout"] = "stat_callout"
    props: StatCalloutProps
    mute_sfx: bool = False
    rationale: str = Field(default="", max_length=140)


class IconListScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    beat_i: int
    template: Literal["icon_list"] = "icon_list"
    props: IconListProps
    mute_sfx: bool = False
    rationale: str = Field(default="", max_length=140)


class RevealScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    beat_i: int
    template: Literal["reveal"] = "reveal"
    props: RevealProps
    mute_sfx: bool = False
    rationale: str = Field(default="", max_length=140)


class CauseEffectScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    beat_i: int
    template: Literal["cause_effect"] = "cause_effect"
    props: CauseEffectProps
    mute_sfx: bool = False
    rationale: str = Field(default="", max_length=140)


class ComparisonScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    beat_i: int
    template: Literal["comparison"] = "comparison"
    props: ComparisonProps
    mute_sfx: bool = False
    rationale: str = Field(default="", max_length=140)


class CharacterIntroScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    beat_i: int
    template: Literal["character_intro"] = "character_intro"
    props: CharacterIntroProps
    mute_sfx: bool = False
    rationale: str = Field(default="", max_length=140)


class DialogueScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    beat_i: int
    template: Literal["dialogue"] = "dialogue"
    props: DialogueProps
    mute_sfx: bool = False
    rationale: str = Field(default="", max_length=140)


class TextThreadScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    beat_i: int
    template: Literal["text_thread"] = "text_thread"
    props: TextThreadProps
    mute_sfx: bool = False
    rationale: str = Field(default="", max_length=140)


class EmotionBeatScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    beat_i: int
    template: Literal["emotion_beat"] = "emotion_beat"
    props: EmotionBeatProps
    mute_sfx: bool = False
    rationale: str = Field(default="", max_length=140)


class RelationshipMapScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    beat_i: int
    template: Literal["relationship_map"] = "relationship_map"
    props: RelationshipMapProps
    mute_sfx: bool = False
    rationale: str = Field(default="", max_length=140)


class LocationScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    beat_i: int
    template: Literal["location"] = "location"
    props: LocationProps
    mute_sfx: bool = False
    rationale: str = Field(default="", max_length=140)


class SetPieceScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    beat_i: int
    template: Literal["set_piece"] = "set_piece"
    props: SetPieceProps
    mute_sfx: bool = False
    rationale: str = Field(default="", max_length=140)


class MapFocusScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    beat_i: int
    template: Literal["map_focus"] = "map_focus"
    props: MapFocusProps
    mute_sfx: bool = False
    rationale: str = Field(default="", max_length=140)


class TimelineSceneModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    beat_i: int
    template: Literal["timeline"] = "timeline"
    props: TimelineProps
    mute_sfx: bool = False
    rationale: str = Field(default="", max_length=140)


class MetaphorScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    beat_i: int
    template: Literal["metaphor"] = "metaphor"
    props: MetaphorProps
    mute_sfx: bool = False
    rationale: str = Field(default="", max_length=140)


class CallbackScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    beat_i: int
    template: Literal["callback"] = "callback"
    props: CallbackProps
    mute_sfx: bool = False
    rationale: str = Field(default="", max_length=140)


class SectionTitleScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    beat_i: int
    template: Literal["section_title"] = "section_title"
    props: SectionTitleProps
    mute_sfx: bool = False
    rationale: str = Field(default="", max_length=140)


SceneUnion = (
    TitleCardScene
    | KineticQuoteScene
    | StatCalloutScene
    | IconListScene
    | RevealScene
    | CauseEffectScene
    | ComparisonScene
    | CharacterIntroScene
    | DialogueScene
    | TextThreadScene
    | EmotionBeatScene
    | RelationshipMapScene
    | LocationScene
    | SetPieceScene
    | MapFocusScene
    | TimelineSceneModel
    | MetaphorScene
    | CallbackScene
    | SectionTitleScene
)
Scene = Annotated[SceneUnion, Field(discriminator="template")]


class Storyboard(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    aspect: Literal["9:16"] = "9:16"
    scenes: list[Scene]

    @model_validator(mode="after")
    def validate_storyboard(self) -> "Storyboard":
        for idx, s in enumerate(self.scenes):
            if s.beat_i != idx:
                raise ValueError(f"Scene at position {idx} has beat_i={s.beat_i}, expected {idx}")
            expected_id = f"s{idx:03d}"
            if s.id != expected_id:
                raise ValueError(
                    f"Scene at position {idx} has id='{s.id}', expected '{expected_id}'"
                )
        return self


# ---------------------------------------------------------------------------
# Section 6: PlanReport
# ---------------------------------------------------------------------------


class CriticReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["not_applicable", "agree", "mismatch_retried", "unavailable"] = "not_applicable"
    mismatches: list[str] = Field(default_factory=list)
    changed: bool = False
    repair: Literal["tone_neutral", "emotion_neutral", "attribution_dropped"] | None = None
    retry_errors: list[str] = Field(default_factory=list)


class PlanReportScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    primary: str
    alternate: str
    final_template: str
    fallback_level: Literal[0, 1, 2]
    attempts: int
    errors: list[str] = Field(default_factory=list)
    critic: CriticReport = Field(default_factory=CriticReport)


class RuleRepair(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    rule: str
    scene: str
    from_: str = Field(alias="from")
    to: str


class PlanReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    model: str
    llm_calls: int = Field(ge=0)
    llm_cache_hits: int = Field(ge=0)
    scenes: list[PlanReportScene] = Field(default_factory=list)
    rule_repairs: list[RuleRepair] = Field(default_factory=list)
    style: str | None = Field(default=None)
    style_degraded: bool | None = Field(default=None)

    @model_serializer(mode="wrap")
    def _serialize(self, handler: Any) -> dict[str, Any]:
        data = handler(self)
        if self.style is None or (self.style == "literal" and not self.style_degraded):
            data.pop("style", None)
            data.pop("style_degraded", None)
        return data

    @property
    def effective_style(self) -> str:
        return self.style if self.style is not None else "literal"

    @property
    def is_style_degraded(self) -> bool:
        return bool(self.style_degraded)


# ---------------------------------------------------------------------------
# Section 7: Timeline (Renderer input)
# ---------------------------------------------------------------------------


class TimelineDebug(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sync_probe: bool = False


class TimelineNarration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    src: str


class TimelineMusic(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    src: str
    volume: float = Field(ge=0.0, le=1.0)
    fade_in_frames: int = Field(ge=0)
    fade_out_frames: int = Field(ge=0)


class TimelineSfx(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    src: str
    frame: int = Field(ge=0)
    volume: float = Field(ge=0.0, le=1.0)


class TimelineAudio(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    narration: TimelineNarration
    music: TimelineMusic | None = None
    sfx: list[TimelineSfx] = Field(default_factory=list)


class TimelineCastMember(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=24)
    color: str
    avatar: AvatarConfig


class TimelinePlace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=40)
    image: str | None = None
    icon: IconName
    lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    lon: float | None = Field(default=None, ge=-180.0, le=180.0)
    country_iso3: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")


class TimelineSetPiece(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=40)
    image: str | None = None
    icon: IconName


class TimelineSceneTiming(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    item_frames: list[int] = Field(default_factory=list)
    count_frames: int | None = None


class SceneOverlay(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["motif_token", "thought", "label", "prop"]
    icon: IconName | None = None
    text: str | None = None
    anchor: Literal["top_right", "bottom_left", "top_left"]
    motif_id: str | None = None

    @model_validator(mode="after")
    def validate_anchor(self) -> Self:
        if self.kind == "motif_token" and self.anchor != "top_right":
            raise ValueError(
                f"motif_token requires anchor 'top_right', got '{self.anchor}'"
            )
        if self.kind in ("thought", "label") and self.anchor != "top_left":
            raise ValueError(
                f"{self.kind} requires anchor 'top_left', got '{self.anchor}'"
            )
        if self.kind == "prop" and self.anchor != "bottom_left":
            raise ValueError(
                f"prop requires anchor 'bottom_left', got '{self.anchor}'"
            )
        return self


# Timeline Scenes (discriminated union on template)
class TimelineTitleCardScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    template: Literal["title_card"] = "title_card"
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    hide_captions: bool = False
    timing: TimelineSceneTiming = Field(default_factory=TimelineSceneTiming)
    props: TitleCardProps
    overlays: list[SceneOverlay] = Field(default_factory=list)


class TimelineKineticQuoteScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    template: Literal["kinetic_quote"] = "kinetic_quote"
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    hide_captions: bool = False
    timing: TimelineSceneTiming = Field(default_factory=TimelineSceneTiming)
    props: KineticQuoteProps
    overlays: list[SceneOverlay] = Field(default_factory=list)


class TimelineStatCalloutScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    template: Literal["stat_callout"] = "stat_callout"
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    hide_captions: bool = False
    timing: TimelineSceneTiming = Field(default_factory=TimelineSceneTiming)
    props: StatCalloutProps
    overlays: list[SceneOverlay] = Field(default_factory=list)


class TimelineIconListScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    template: Literal["icon_list"] = "icon_list"
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    hide_captions: bool = False
    timing: TimelineSceneTiming = Field(default_factory=TimelineSceneTiming)
    props: IconListProps
    overlays: list[SceneOverlay] = Field(default_factory=list)


class TimelineRevealScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    template: Literal["reveal"] = "reveal"
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    hide_captions: bool = False
    timing: TimelineSceneTiming = Field(default_factory=TimelineSceneTiming)
    props: RevealProps
    overlays: list[SceneOverlay] = Field(default_factory=list)


class TimelineCauseEffectScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    template: Literal["cause_effect"] = "cause_effect"
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    hide_captions: bool = False
    timing: TimelineSceneTiming = Field(default_factory=TimelineSceneTiming)
    props: CauseEffectProps
    overlays: list[SceneOverlay] = Field(default_factory=list)


class TimelineComparisonScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    template: Literal["comparison"] = "comparison"
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    hide_captions: bool = False
    timing: TimelineSceneTiming = Field(default_factory=TimelineSceneTiming)
    props: ComparisonProps
    overlays: list[SceneOverlay] = Field(default_factory=list)


class TimelineCharacterIntroScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    template: Literal["character_intro"] = "character_intro"
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    hide_captions: bool = False
    timing: TimelineSceneTiming = Field(default_factory=TimelineSceneTiming)
    props: CharacterIntroProps
    overlays: list[SceneOverlay] = Field(default_factory=list)


class TimelineDialogueScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    template: Literal["dialogue"] = "dialogue"
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    hide_captions: bool = False
    timing: TimelineSceneTiming = Field(default_factory=TimelineSceneTiming)
    props: DialogueProps
    overlays: list[SceneOverlay] = Field(default_factory=list)


class TimelineTextThreadScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    template: Literal["text_thread"] = "text_thread"
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    hide_captions: bool = False
    timing: TimelineSceneTiming = Field(default_factory=TimelineSceneTiming)
    props: TextThreadProps
    overlays: list[SceneOverlay] = Field(default_factory=list)


class TimelineEmotionBeatScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    template: Literal["emotion_beat"] = "emotion_beat"
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    hide_captions: bool = False
    timing: TimelineSceneTiming = Field(default_factory=TimelineSceneTiming)
    props: EmotionBeatProps
    overlays: list[SceneOverlay] = Field(default_factory=list)


class TimelineRelationshipMapScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    template: Literal["relationship_map"] = "relationship_map"
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    hide_captions: bool = False
    timing: TimelineSceneTiming = Field(default_factory=TimelineSceneTiming)
    props: RelationshipMapProps
    overlays: list[SceneOverlay] = Field(default_factory=list)


class TimelineLocationScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    template: Literal["location"] = "location"
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    hide_captions: bool = False
    timing: TimelineSceneTiming = Field(default_factory=TimelineSceneTiming)
    props: LocationProps
    overlays: list[SceneOverlay] = Field(default_factory=list)


class TimelineSetPieceScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    template: Literal["set_piece"] = "set_piece"
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    hide_captions: bool = False
    timing: TimelineSceneTiming = Field(default_factory=TimelineSceneTiming)
    props: SetPieceProps
    overlays: list[SceneOverlay] = Field(default_factory=list)


class TimelineMapFocusScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    template: Literal["map_focus"] = "map_focus"
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    hide_captions: bool = False
    timing: TimelineSceneTiming = Field(default_factory=TimelineSceneTiming)
    props: MapFocusProps
    overlays: list[SceneOverlay] = Field(default_factory=list)


class TimelineTimelineScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    template: Literal["timeline"] = "timeline"
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    hide_captions: bool = False
    timing: TimelineSceneTiming = Field(default_factory=TimelineSceneTiming)
    props: TimelineProps
    overlays: list[SceneOverlay] = Field(default_factory=list)


class TimelineMetaphorScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    template: Literal["metaphor"] = "metaphor"
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    hide_captions: bool = False
    timing: TimelineSceneTiming = Field(default_factory=TimelineSceneTiming)
    props: MetaphorProps
    overlays: list[SceneOverlay] = Field(default_factory=list)


class TimelineCallbackScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    template: Literal["callback"] = "callback"
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    hide_captions: bool = False
    timing: TimelineSceneTiming = Field(default_factory=TimelineSceneTiming)
    props: CallbackProps
    overlays: list[SceneOverlay] = Field(default_factory=list)


class TimelineSectionTitleScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^s\d{3}$")
    template: Literal["section_title"] = "section_title"
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    hide_captions: bool = False
    timing: TimelineSceneTiming = Field(default_factory=TimelineSceneTiming)
    props: SectionTitleProps
    overlays: list[SceneOverlay] = Field(default_factory=list)


TimelineSceneUnion = (
    TimelineTitleCardScene
    | TimelineKineticQuoteScene
    | TimelineStatCalloutScene
    | TimelineIconListScene
    | TimelineRevealScene
    | TimelineCauseEffectScene
    | TimelineComparisonScene
    | TimelineCharacterIntroScene
    | TimelineDialogueScene
    | TimelineTextThreadScene
    | TimelineEmotionBeatScene
    | TimelineRelationshipMapScene
    | TimelineLocationScene
    | TimelineSetPieceScene
    | TimelineMapFocusScene
    | TimelineTimelineScene
    | TimelineMetaphorScene
    | TimelineCallbackScene
    | TimelineSectionTitleScene
)
TimelineScene = Annotated[TimelineSceneUnion, Field(discriminator="template")]


class CaptionWord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)


class CaptionPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    words: list[CaptionWord]


class TimelineCaptions(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    pages: list[CaptionPage] = Field(default_factory=list)


class Timeline(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    fps: Literal[30] = 30
    width: Literal[1080] = 1080
    height: Literal[1920] = 1920
    duration_frames: int = Field(gt=0)
    plan_sha256: str
    debug: TimelineDebug = Field(default_factory=TimelineDebug)
    audio: TimelineAudio
    cast: dict[str, TimelineCastMember] = Field(default_factory=dict)
    places: dict[str, TimelinePlace] = Field(default_factory=dict)
    set_pieces: dict[str, TimelineSetPiece] = Field(default_factory=dict)
    scenes: list[TimelineScene] = Field(default_factory=list)
    captions: TimelineCaptions = Field(default_factory=TimelineCaptions)

    @model_serializer(mode="wrap")
    def _serialize(self, handler: Any) -> dict[str, Any]:
        data = handler(self)
        for s in data.get("scenes", []):
            if "overlays" in s and not s["overlays"]:
                s.pop("overlays", None)
        return data

    @model_validator(mode="after")
    def validate_timeline_scenes(self) -> "Timeline":
        if self.scenes:
            if self.scenes[0].start_frame != 0:
                raise ValueError("First scene must start at frame 0")
            for idx, sc in enumerate(self.scenes):
                if idx > 0 and sc.start_frame != self.scenes[idx - 1].end_frame:
                    raise ValueError(f"Scene {sc.id} start_frame != previous scene end_frame")
                if sc.end_frame <= sc.start_frame:
                    raise ValueError(f"Scene {sc.id} end_frame <= start_frame")
            if self.scenes[-1].end_frame != self.duration_frames:
                raise ValueError(
                    f"Last scene end_frame ({self.scenes[-1].end_frame}) != "
                    f"duration_frames ({self.duration_frames})"
                )
        return self

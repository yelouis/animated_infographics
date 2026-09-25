"""Unit tests for timeline compilation, tiling, caption hiding, and SFX scheduling."""

from pathlib import Path

from animated_infographics.compile import compile_timeline
from animated_infographics.contracts.models import (
    AvatarConfig,
    Beat,
    Bible,
    CastMember,
    KineticQuoteProps,
    KineticQuoteScene,
    Place,
    Storyboard,
    TitleCardProps,
    TitleCardScene,
    Transcript,
    TranscriptSentence,
    TranscriptWord,
)


def _make_dummy_transcript() -> Transcript:
    words = [
        TranscriptWord(i=0, sentence_i=0, text="The", start_ms=0, end_ms=200),
        TranscriptWord(i=1, sentence_i=0, text="Title", start_ms=250, end_ms=500),
        TranscriptWord(i=2, sentence_i=1, text="Second", start_ms=1000, end_ms=1300),
        TranscriptWord(i=3, sentence_i=1, text="sentence", start_ms=1350, end_ms=1700),
        TranscriptWord(i=4, sentence_i=2, text="Third", start_ms=2500, end_ms=2800),
        TranscriptWord(i=5, sentence_i=2, text="sentence", start_ms=2850, end_ms=3200),
    ]
    sentences = [
        TranscriptSentence(
            i=0,
            paragraph_i=0,
            text="The Title",
            start_ms=0,
            end_ms=500,
            word_start=0,
            word_end=2,
            is_title=True,
        ),
        TranscriptSentence(
            i=1,
            paragraph_i=0,
            text="Second sentence",
            start_ms=1000,
            end_ms=1700,
            word_start=2,
            word_end=4,
            is_title=False,
        ),
        TranscriptSentence(
            i=2,
            paragraph_i=0,
            text="Third sentence",
            start_ms=2500,
            end_ms=3200,
            word_start=4,
            word_end=6,
            is_title=False,
        ),
    ]
    return Transcript(
        schema_version=1,
        source="tts",
        audio_path="test.wav",
        duration_ms=5000,
        words=words,
        sentences=sentences,
    )


def _make_dummy_bible() -> Bible:
    cast = [
        CastMember(
            id="c1",
            name="Alice",
            role="Explorer",
            color_slot=0,
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
    ]
    places = [
        Place(
            id="p1",
            name="Boston",
            kind="real",
            country_iso3="USA",
            lat=42.36,
            lon=-71.06,
            geo_source="gazetteer",
            visual_description="A city",
            icon="Buildings",
        )
    ]
    return Bible(
        schema_version=1,
        title="Test",
        logline="A test story",
        genre="history",
        cast=cast,
        places=places,
        set_pieces=[],
    )


def test_timeline_tiling() -> None:
    transcript = _make_dummy_transcript()
    bible = _make_dummy_bible()

    beats = [
        Beat(i=0, text="The Title", start_ms=0, end_ms=1000, word_start=0, word_end=2),
        Beat(i=1, text="Second sentence", start_ms=1000, end_ms=2500, word_start=2, word_end=4),
        Beat(i=2, text="Third sentence", start_ms=2500, end_ms=5000, word_start=4, word_end=6),
    ]

    scenes = [
        TitleCardScene(
            id="s000",
            beat_i=0,
            template="title_card",
            props=TitleCardProps(title="The Title"),
        ),
        KineticQuoteScene(
            id="s001",
            beat_i=1,
            template="kinetic_quote",
            props=KineticQuoteProps(text="Second sentence"),
        ),
        KineticQuoteScene(
            id="s002",
            beat_i=2,
            template="kinetic_quote",
            props=KineticQuoteProps(text="Third sentence"),
        ),
    ]
    storyboard = Storyboard(schema_version=1, aspect="9:16", scenes=scenes)

    timeline = compile_timeline(
        transcript,
        beats,
        bible,
        storyboard,
        plan_sha256="dummy_sha",
    )

    assert timeline.scenes[0].start_frame == 0
    for i in range(1, len(timeline.scenes)):
        assert timeline.scenes[i].start_frame == timeline.scenes[i - 1].end_frame
        assert timeline.scenes[i].end_frame > timeline.scenes[i].start_frame

    assert timeline.scenes[-1].end_frame == timeline.duration_frames


def test_hidden_captions_on_narrated_title_only() -> None:
    transcript = _make_dummy_transcript()
    bible = _make_dummy_bible()

    beats = [
        Beat(i=0, text="The Title", start_ms=0, end_ms=1000, word_start=0, word_end=2),
        Beat(i=1, text="Second sentence", start_ms=1000, end_ms=2500, word_start=2, word_end=4),
    ]

    scenes = [
        TitleCardScene(
            id="s000",
            beat_i=0,
            template="title_card",
            props=TitleCardProps(title="The Title"),
        ),
        KineticQuoteScene(
            id="s001",
            beat_i=1,
            template="kinetic_quote",
            props=KineticQuoteProps(text="Second sentence"),
        ),
    ]
    storyboard = Storyboard(schema_version=1, aspect="9:16", scenes=scenes)

    timeline = compile_timeline(
        transcript,
        beats,
        bible,
        storyboard,
        plan_sha256="dummy_sha",
    )

    # Scene 0 is title_card with sentence 0 (is_title=True) -> hide_captions = True
    assert timeline.scenes[0].hide_captions is True
    # Scene 1 is not title_card -> hide_captions = False
    assert timeline.scenes[1].hide_captions is False


def test_sfx_min_gap_24_frames(tmp_path: Path) -> None:
    transcript = _make_dummy_transcript()
    bible = _make_dummy_bible()

    beats = [
        Beat(i=0, text="The Title", start_ms=0, end_ms=500, word_start=0, word_end=2),
        Beat(i=1, text="Second sentence", start_ms=500, end_ms=1000, word_start=2, word_end=4),
        Beat(i=2, text="Third sentence", start_ms=2000, end_ms=3000, word_start=4, word_end=6),
    ]

    # title_card has whoosh at start (frame 0)
    # If scene 1 starts at frame 10 (less than 24 frames away), its start cue must be dropped
    # If scene 2 starts at frame 54 (>= 24 frames away from 0), its cue is kept
    scenes = [
        TitleCardScene(
            id="s000",
            beat_i=0,
            template="title_card",
            props=TitleCardProps(title="The Title"),
        ),
        TitleCardScene(
            id="s001",
            beat_i=1,
            template="title_card",
            props=TitleCardProps(title="The Title 2"),
        ),
        TitleCardScene(
            id="s002",
            beat_i=2,
            template="title_card",
            props=TitleCardProps(title="The Title 3"),
        ),
    ]
    storyboard = Storyboard(schema_version=1, aspect="9:16", scenes=scenes)

    sfx_file = tmp_path / "whoosh_0.wav"
    sfx_file.write_bytes(b"dummy")
    sfx_files = {"whoosh": [sfx_file]}

    timeline = compile_timeline(
        transcript,
        beats,
        bible,
        storyboard,
        plan_sha256="dummy_sha",
        sfx_files_by_role=sfx_files,
    )

    sfx_frames = [s.frame for s in timeline.audio.sfx]
    for i in range(1, len(sfx_frames)):
        assert sfx_frames[i] - sfx_frames[i - 1] >= 24


def test_sfx_round_robin_files(tmp_path: Path) -> None:
    f0 = tmp_path / "pop_0.wav"
    f1 = tmp_path / "pop_1.wav"
    f2 = tmp_path / "pop_2.wav"
    for f in (f0, f1, f2):
        f.write_bytes(b"dummy")

    available_sfx = {"pop": [f0, f1, f2]}

    # Schedule cues manually through compile_timeline with spaced beats
    transcript = _make_dummy_transcript()
    bible = _make_dummy_bible()

    # 4 beats spaced by 30 frames (1000ms), fitting within 5000ms transcript
    beats = [
        Beat(i=0, text="B0", start_ms=0, end_ms=1000, word_start=0, word_end=1),
        Beat(i=1, text="B1", start_ms=1000, end_ms=2000, word_start=1, word_end=2),
        Beat(i=2, text="B2", start_ms=2000, end_ms=3000, word_start=2, word_end=3),
        Beat(i=3, text="B3", start_ms=3000, end_ms=4500, word_start=3, word_end=4),
    ]
    # character_intro has cue pop at start
    from animated_infographics.contracts.models import CharacterIntroProps, CharacterIntroScene

    scenes = [
        CharacterIntroScene(
            id=f"s{i:03d}",
            beat_i=i,
            template="character_intro",
            props=CharacterIntroProps(cast_id="c1", descriptor="Hero"),
        )
        for i in range(4)
    ]
    storyboard = Storyboard(schema_version=1, aspect="9:16", scenes=scenes)

    timeline = compile_timeline(
        transcript,
        beats,
        bible,
        storyboard,
        plan_sha256="sha",
        sfx_files_by_role=available_sfx,
    )

    sfx_srcs = [s.src for s in timeline.audio.sfx]
    expected_srcs = [
        "job/audio/sfx/pop_0.wav",
        "job/audio/sfx/pop_1.wav",
        "job/audio/sfx/pop_2.wav",
        "job/audio/sfx/pop_0.wav",
    ]
    assert sfx_srcs == expected_srcs

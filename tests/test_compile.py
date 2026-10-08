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


def test_music_and_sfx_survive_review_journey(tmp_path: Path) -> None:
    import json
    import shutil
    from datetime import UTC, datetime

    from animated_infographics.jobs import Job, RunContext
    from animated_infographics.stages.compile import run_compile_stage

    job = Job.create(Path("story.txt"), tmp_path, datetime.now(UTC))
    job_dir = job.dir
    (job_dir / "input").mkdir(exist_ok=True)
    (job_dir / "input" / "sfx").mkdir(exist_ok=True)
    shutil.copy2("fixtures/music/test_bed.wav", job_dir / "input" / "test_bed.wav")
    shutil.copy2("fixtures/sfx/pop_test.wav", job_dir / "input" / "sfx" / "pop_test.wav")

    # Ingest record with job-local relative paths
    ingest_json = {
        "schema_version": 1,
        "kind": "text",
        "source": "input/story.txt",
        "title": "Title",
        "paragraphs": ["The Title", "Second sentence", "Third sentence"],
        "word_count": 6,
        "music": "input/test_bed.wav",
        "sfx_dir": "input/sfx",
    }
    (job_dir / "ingest.json").write_text(json.dumps(ingest_json), encoding="utf-8")

    transcript = _make_dummy_transcript()
    (job_dir / "transcript.json").write_text(transcript.model_dump_json(indent=2), encoding="utf-8")
    bible = _make_dummy_bible()
    (job_dir / "bible.json").write_text(bible.model_dump_json(indent=2), encoding="utf-8")
    beats = [
        Beat(i=0, text="The Title", start_ms=0, end_ms=1000, word_start=0, word_end=2),
        Beat(i=1, text="Second sentence", start_ms=1000, end_ms=2500, word_start=2, word_end=4),
        Beat(i=2, text="Third sentence", start_ms=2500, end_ms=3200, word_start=4, word_end=6),
    ]
    from animated_infographics.contracts.models import Beats

    (job_dir / "beats.json").write_text(
        Beats(schema_version=1, beats=beats).model_dump_json(indent=2), encoding="utf-8"
    )
    from animated_infographics.contracts.models import CharacterIntroProps, CharacterIntroScene

    scenes = [
        TitleCardScene(
            id="s000",
            beat_i=0,
            template="title_card",
            props=TitleCardProps(title="The Title"),
        ),
        CharacterIntroScene(
            id="s001",
            beat_i=1,
            template="character_intro",
            props=CharacterIntroProps(cast_id="c1", descriptor="Hero"),
        ),
        KineticQuoteScene(
            id="s002",
            beat_i=2,
            template="kinetic_quote",
            props=KineticQuoteProps(text="Third sentence"),
        ),
    ]
    storyboard = Storyboard(schema_version=1, aspect="9:16", scenes=scenes)
    (job_dir / "storyboard.json").write_text(storyboard.model_dump_json(indent=2), encoding="utf-8")

    job = Job(job_dir)
    # 1. First compile with bare RunContext (like preview or recompile)
    run_compile_stage(job, RunContext())
    assert (job_dir / "timeline.json").is_file()

    # 2. Invalidate after storyboard (as an edit would do)
    job.invalidate_after("storyboard")
    assert not (job_dir / "timeline.json").exists()
    assert not (job_dir / "audio" / "music.wav").exists()
    assert len(list((job_dir / "audio" / "sfx").iterdir())) == 0

    # 3. Re-compile with bare RunContext (as preview/rerun does)
    run_compile_stage(job, RunContext())

    timeline_data = json.loads((job_dir / "timeline.json").read_text(encoding="utf-8"))
    assert timeline_data["audio"]["music"] is not None
    assert len(timeline_data["audio"]["sfx"]) > 0


def test_no_forbidden_runcontext_music_sfx_reads() -> None:
    import re

    src_dir = Path("src/animated_infographics")
    allowed_files = {"cli.py", "stages/ingest.py"}
    pattern = re.compile(r"\bctx\.(music_path|sfx_dir)\b")

    violations: list[str] = []
    for py_file in src_dir.rglob("*.py"):
        rel_path = py_file.relative_to(src_dir).as_posix()
        if rel_path in allowed_files:
            continue
        content = py_file.read_text(encoding="utf-8")
        for line_no, line in enumerate(content.splitlines(), start=1):
            if pattern.search(line):
                violations.append(f"{rel_path}:{line_no}: {line.strip()}")

    assert not violations, "Forbidden RunContext music/sfx reads found:\n" + "\n".join(violations)


def test_compile_missing_music_fails_loudly(tmp_path: Path) -> None:
    import json
    import shutil
    from datetime import UTC, datetime

    import pytest

    from animated_infographics.contracts.models import (
        Beats,
        CharacterIntroProps,
        CharacterIntroScene,
    )
    from animated_infographics.errors import ValidationFailed
    from animated_infographics.jobs import Job, RunContext
    from animated_infographics.stages.compile import run_compile_stage

    job = Job.create(Path("story.txt"), tmp_path, datetime.now(UTC))
    job_dir = job.dir
    (job_dir / "input").mkdir(exist_ok=True)
    shutil.copy2("fixtures/music/test_bed.wav", job_dir / "input" / "test_bed.wav")

    ingest_json = {
        "schema_version": 1,
        "kind": "text",
        "source": "input/story.txt",
        "title": "Title",
        "paragraphs": ["The Title", "Second sentence", "Third sentence"],
        "word_count": 6,
        "music": "input/test_bed.wav",
        "sfx_dir": None,
    }
    (job_dir / "ingest.json").write_text(json.dumps(ingest_json), encoding="utf-8")

    transcript = _make_dummy_transcript()
    (job_dir / "transcript.json").write_text(transcript.model_dump_json(indent=2), encoding="utf-8")
    bible = _make_dummy_bible()
    (job_dir / "bible.json").write_text(bible.model_dump_json(indent=2), encoding="utf-8")
    beats = [
        Beat(i=0, text="The Title", start_ms=0, end_ms=1000, word_start=0, word_end=2),
        Beat(i=1, text="Second sentence", start_ms=1000, end_ms=2500, word_start=2, word_end=4),
        Beat(i=2, text="Third sentence", start_ms=2500, end_ms=3200, word_start=4, word_end=6),
    ]
    (job_dir / "beats.json").write_text(
        Beats(schema_version=1, beats=beats).model_dump_json(indent=2), encoding="utf-8"
    )
    scenes = [
        TitleCardScene(
            id="s000",
            beat_i=0,
            template="title_card",
            props=TitleCardProps(title="The Title"),
        ),
        CharacterIntroScene(
            id="s001",
            beat_i=1,
            template="character_intro",
            props=CharacterIntroProps(cast_id="c1", descriptor="Hero"),
        ),
        KineticQuoteScene(
            id="s002",
            beat_i=2,
            template="kinetic_quote",
            props=KineticQuoteProps(text="Third sentence"),
        ),
    ]
    storyboard = Storyboard(schema_version=1, aspect="9:16", scenes=scenes)
    (job_dir / "storyboard.json").write_text(storyboard.model_dump_json(indent=2), encoding="utf-8")

    # Delete the music file recorded in ingest.json
    (job_dir / "input" / "test_bed.wav").unlink()

    with pytest.raises(ValidationFailed) as exc_info:
        run_compile_stage(job, RunContext())

    expected_msg = "input/test_bed.wav is recorded in ingest.json but missing from the job"
    assert expected_msg in str(exc_info.value)

    # Also test missing sfx_dir fails loudly
    shutil.copy2("fixtures/music/test_bed.wav", job_dir / "input" / "test_bed.wav")
    ingest_json["sfx_dir"] = "input/missing_sfx_dir"
    (job_dir / "ingest.json").write_text(json.dumps(ingest_json), encoding="utf-8")

    with pytest.raises(ValidationFailed) as exc_info_sfx:
        run_compile_stage(job, RunContext())

    expected_sfx_msg = "input/missing_sfx_dir is recorded in ingest.json but missing from the job"
    assert expected_sfx_msg in str(exc_info_sfx.value)


def test_compile_callback_item_frames_from_overlays():
    from animated_infographics.contracts.models import (
        CallbackScene,
        CharacterIntroProps,
        CharacterIntroScene,
        SceneOverlay,
    )
    from animated_infographics.contracts.templates import CallbackProps
    from animated_infographics.timing.items import item_frames

    words = [
        TranscriptWord(i=0, sentence_i=0, text="The", start_ms=0, end_ms=200),
        TranscriptWord(i=1, sentence_i=0, text="Title", start_ms=250, end_ms=500),
        TranscriptWord(i=2, sentence_i=1, text="Second", start_ms=1000, end_ms=1300),
        TranscriptWord(i=3, sentence_i=1, text="sentence", start_ms=1350, end_ms=1700),
        TranscriptWord(i=4, sentence_i=2, text="Third", start_ms=2500, end_ms=2800),
        TranscriptWord(i=5, sentence_i=2, text="sentence", start_ms=2850, end_ms=3200),
        TranscriptWord(i=6, sentence_i=3, text="Fourth", start_ms=4000, end_ms=4300),
        TranscriptWord(i=7, sentence_i=3, text="sentence", start_ms=4350, end_ms=4700),
        TranscriptWord(i=8, sentence_i=4, text="Fifth", start_ms=5500, end_ms=5800),
        TranscriptWord(i=9, sentence_i=4, text="sentence", start_ms=5850, end_ms=6200),
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
        TranscriptSentence(
            i=3,
            paragraph_i=0,
            text="Fourth sentence",
            start_ms=4000,
            end_ms=4700,
            word_start=6,
            word_end=8,
            is_title=False,
        ),
        TranscriptSentence(
            i=4,
            paragraph_i=0,
            text="Fifth sentence",
            start_ms=5500,
            end_ms=6200,
            word_start=8,
            word_end=10,
            is_title=False,
        ),
    ]
    transcript = Transcript(
        schema_version=1,
        source="tts",
        audio_path="test.wav",
        duration_ms=7500,
        words=words,
        sentences=sentences,
    )
    beats = [
        Beat(i=0, text="The Title", start_ms=0, end_ms=1000, word_start=0, word_end=2),
        Beat(i=1, text="Second sentence", start_ms=1000, end_ms=2500, word_start=2, word_end=4),
        Beat(i=2, text="Third sentence", start_ms=2500, end_ms=4000, word_start=4, word_end=6),
        Beat(i=3, text="Fourth sentence", start_ms=4000, end_ms=5500, word_start=6, word_end=8),
        Beat(i=4, text="Fifth sentence", start_ms=5500, end_ms=7000, word_start=8, word_end=10),
    ]
    scenes = [
        TitleCardScene(
            id="s000",
            beat_i=0,
            template="title_card",
            props=TitleCardProps(title="The Title"),
        ),
        CharacterIntroScene(
            id="s001",
            beat_i=1,
            template="character_intro",
            props=CharacterIntroProps(cast_id="c1", descriptor="Hero"),
        ),
        KineticQuoteScene(
            id="s002",
            beat_i=2,
            template="kinetic_quote",
            props=KineticQuoteProps(text="Third sentence"),
        ),
        KineticQuoteScene(
            id="s003",
            beat_i=3,
            template="kinetic_quote",
            props=KineticQuoteProps(text="Fourth sentence"),
        ),
        CallbackScene(
            id="s004",
            beat_i=4,
            template="callback",
            props=CallbackProps(motif_id="m1", label="Key", icon="Key"),
        ),
    ]
    storyboard = Storyboard(schema_version=1, aspect="9:16", scenes=scenes)

    # 3 earlier scenes have motif_token m1
    scene_overlays = {
        1: [SceneOverlay(kind="motif_token", motif_id="m1", icon="Key", anchor="top_right")],
        2: [SceneOverlay(kind="motif_token", motif_id="m1", icon="Key", anchor="top_right")],
        3: [SceneOverlay(kind="motif_token", motif_id="m1", icon="Key", anchor="top_right")],
    }

    bible = _make_dummy_bible()
    timeline = compile_timeline(
        transcript, beats, bible, storyboard, plan_sha256="dummy", scene_overlays=scene_overlays
    )
    cb_scene = timeline.scenes[4]
    cb_frames = cb_scene.end_frame - cb_scene.start_frame
    expected_frames = item_frames(3, cb_frames, 0.4)
    assert len(cb_scene.timing.item_frames) == 3
    assert cb_scene.timing.item_frames == expected_frames

    # With only 1 earlier token -> 1
    scene_overlays_1 = {
        1: [SceneOverlay(kind="motif_token", motif_id="m1", icon="Key", anchor="top_right")],
    }
    timeline_1 = compile_timeline(
        transcript, beats, bible, storyboard, plan_sha256="dummy", scene_overlays=scene_overlays_1
    )
    cb_scene_1 = timeline_1.scenes[4]
    cb_frames_1 = cb_scene_1.end_frame - cb_scene_1.start_frame
    assert len(cb_scene_1.timing.item_frames) == 1
    assert cb_scene_1.timing.item_frames == item_frames(1, cb_frames_1, 0.4)

"""Unit tests for preview generation and formatting."""

import json
from pathlib import Path

import pytest
from PIL import Image

from animated_infographics.contracts.models import (
    Beat,
    PlanReport,
    PlanReportScene,
    Timeline,
    TimelineAudio,
    TimelineCaptions,
    TimelineNarration,
    TimelineSceneTiming,
    TimelineTitleCardScene,
    TitleCardProps,
    VoiceDecision,
)
from animated_infographics.preview import (
    compute_hero_frames,
    format_voice_line,
    generate_contact_sheet,
    generate_preview_report,
    generate_storyboard_markdown,
)


def test_format_voice_line_all_variants() -> None:
    # 1. Flag
    v_flag = VoiceDecision(
        schema_version=1,
        voice="af_heart",
        source="flag",
        reason="flag",
    )
    assert format_voice_line(v_flag) == "Voice: af_heart — set by --voice"

    # 2. Third person
    v_tp = VoiceDecision(
        schema_version=1,
        voice="am_michael",
        source="auto",
        reason="third_person",
        perspective="third_person",
        first_person_rate=0.0,
        narrator_gender="unknown",
    )
    assert format_voice_line(v_tp) == "Voice: am_michael — auto (third person)"

    # 3. First person, no evidence
    v_ne = VoiceDecision(
        schema_version=1,
        voice="am_michael",
        source="auto",
        reason="no_evidence",
        perspective="first_person",
        first_person_rate=5.0,
        narrator_gender="unknown",
    )
    assert (
        format_voice_line(v_ne)
        == "Voice: am_michael — auto (first person, no self-identification found)"
    )

    # 4. First person, female / male with evidence (llm or tag)
    v_llm = VoiceDecision(
        schema_version=1,
        voice="af_heart",
        source="auto",
        reason="llm",
        perspective="first_person",
        first_person_rate=5.45,
        narrator_gender="female",
        evidence="As the only granddaughter, I got Grandma Rose's recipe box",
    )
    expected_voice = (
        "Voice: af_heart — auto (first person, female narrator: "
        '"As the only granddaughter, I got Grandma Rose\'s recipe box")'
    )
    assert format_voice_line(v_llm) == expected_voice

    # 5. Audio input (voice is None)
    assert format_voice_line(None) == "Voice: (recorded audio)"


def test_compute_hero_frames() -> None:
    # Scene 1: 100 frames, item_frames = [20, 40]
    # hero_offset = min(100 - 1, max(round(0.6 * 100), 40 + 12)) = min(99, max(60, 52)) = 60
    # hero_frame = 0 + 60 = 60
    sc1 = TimelineTitleCardScene(
        id="s001",
        template="title_card",
        start_frame=0,
        end_frame=100,
        timing=TimelineSceneTiming(item_frames=[20, 40]),
        props=TitleCardProps(title="Hello"),
    )
    # Scene 2: 60 frames, item_frames = [50]
    # hero_offset = min(60 - 1, max(round(0.6 * 60), 50 + 12)) = min(59, max(36, 62)) = 59
    # hero_frame = 100 + 59 = 159
    sc2 = TimelineTitleCardScene(
        id="s002",
        template="title_card",
        start_frame=100,
        end_frame=160,
        timing=TimelineSceneTiming(item_frames=[50]),
        props=TitleCardProps(title="World"),
    )

    timeline = Timeline(
        duration_frames=160,
        plan_sha256="sha160",
        audio=TimelineAudio(narration=TimelineNarration(src="audio/narration.wav")),
        captions=TimelineCaptions(pages=[]),
        scenes=[sc1, sc2],
    )

    frames = compute_hero_frames(timeline)
    assert len(frames) == 2
    assert frames[0] == {"scene_id": "s001", "frame": 60, "out": "preview/scene_s001.png"}
    assert frames[1] == {"scene_id": "s002", "frame": 159, "out": "preview/scene_s002.png"}


def test_generate_contact_sheet(tmp_path: Path) -> None:
    preview_dir = tmp_path / "preview"
    preview_dir.mkdir(parents=True)

    # Create dummy still images
    for sid in ["s001", "s002"]:
        img = Image.new("RGB", (270, 480), color=(100, 100, 100))
        img.save(preview_dir / f"scene_{sid}.png")

    sc1 = TimelineTitleCardScene(
        id="s001",
        template="title_card",
        start_frame=0,
        end_frame=60,
        timing=TimelineSceneTiming(),
        props=TitleCardProps(title="One"),
    )
    sc2 = TimelineTitleCardScene(
        id="s002",
        template="title_card",
        start_frame=60,
        end_frame=120,
        timing=TimelineSceneTiming(),
        props=TitleCardProps(title="Two"),
    )
    timeline = Timeline(
        duration_frames=120,
        plan_sha256="sha120",
        audio=TimelineAudio(narration=TimelineNarration(src="audio/narration.wav")),
        captions=TimelineCaptions(pages=[]),
        scenes=[sc1, sc2],
    )

    out = generate_contact_sheet(tmp_path, timeline, flagged_scenes={"s002"})
    assert out.is_file()
    with Image.open(out) as im:
        assert im.size == (5 * 270, 1 * (480 + 44))


def test_generate_storyboard_markdown(tmp_path: Path) -> None:
    sc1 = TimelineTitleCardScene(
        id="s001",
        template="title_card",
        start_frame=0,
        end_frame=60,
        timing=TimelineSceneTiming(),
        props=TitleCardProps(title="Test Title"),
    )
    timeline = Timeline(
        duration_frames=60,
        plan_sha256="sha60",
        audio=TimelineAudio(narration=TimelineNarration(src="audio/narration.wav")),
        captions=TimelineCaptions(pages=[]),
        scenes=[sc1],
    )
    beats = [Beat(i=0, word_start=0, word_end=4, start_ms=0, end_ms=2000, text="This is beat one.")]
    voice = VoiceDecision(schema_version=1, voice="af_heart", source="flag", reason="flag")

    md_path = generate_storyboard_markdown(
        tmp_path,
        timeline,
        beats,
        voice,
        flags_by_scene={"s001": ["overflow"]},
    )
    assert md_path.is_file()
    content = md_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    assert lines[0] == "Voice: af_heart — set by --voice"
    expected_row = (
        "| `s001` | `0:00.0` | `title_card` | This is beat one. | Test Title | overflow |"
    )
    assert expected_row in lines


def test_generate_preview_report(tmp_path: Path) -> None:
    plan_report = PlanReport(
        model="qwen3.6:35b",
        llm_calls=2,
        llm_cache_hits=0,
        scenes=[
            PlanReportScene(
                id="s001",
                primary="title_card",
                alternate="title_card",
                final_template="title_card",
                fallback_level=0,
                attempts=1,
            ),
            PlanReportScene(
                id="s002",
                primary="stat_callout",
                alternate="kinetic_quote",
                final_template="kinetic_quote",
                fallback_level=2,
                attempts=2,
            ),
        ],
    )
    overflow = [{"scene_id": "s001", "slot": "title"}]

    rep = generate_preview_report(tmp_path, plan_report, overflow, "dummy_sha")
    assert rep["overflow"] == overflow
    assert rep["fallback_scenes"] == ["s002"]
    assert rep["plan_sha256"] == "dummy_sha"

    out_file = tmp_path / "preview" / "report.json"
    assert out_file.is_file()
    saved = json.loads(out_file.read_text(encoding="utf-8"))
    assert saved == rep


def test_contact_sheet_and_storyboard_flag_failed_images(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from animated_infographics.contracts.models import Beats, TimelineSetPieceScene
    from animated_infographics.contracts.templates import SetPieceProps
    from animated_infographics.jobs import Job, RunContext
    from animated_infographics.stages.preview import run_preview_stage

    job_dir = tmp_path / "test_job"
    job_dir.mkdir(parents=True)
    (job_dir / "state.json").write_text(
        json.dumps({"schema_version": 1, "status": "new"}), encoding="utf-8"
    )
    (job_dir / "bible.json").write_text("{}", encoding="utf-8")
    (job_dir / "storyboard.json").write_text("{}", encoding="utf-8")
    beats_obj = Beats(
        beats=[
            Beat(
                i=0,
                word_start=0,
                word_end=2,
                start_ms=0,
                end_ms=2000,
                text="The machine gun.",
            )
        ]
    )
    (job_dir / "beats.json").write_text(beats_obj.model_dump_json(), encoding="utf-8")
    v_decision = VoiceDecision(schema_version=1, voice="am_michael", source="flag", reason="flag")
    (job_dir / "voice.json").write_text(v_decision.model_dump_json(), encoding="utf-8")

    # Manifest with v1 marked as failed and p1 as text_check unavailable
    assets_dir = job_dir / "assets"
    assets_dir.mkdir(parents=True)
    manifest = {
        "entities": [
            {
                "id": "v1",
                "kind": "set_piece",
                "status": "failed",
                "error": "lettering detected in 3 attempts",
            },
            {
                "id": "p1",
                "kind": "place",
                "status": "clean",
                "text_check": "unavailable",
            },
        ]
    }
    (assets_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    # Timeline with s001 on set_piece v1
    sc1 = TimelineSetPieceScene(
        id="s001",
        template="set_piece",
        start_frame=0,
        end_frame=60,
        timing=TimelineSceneTiming(),
        props=SetPieceProps(set_piece_id="v1", caption="Lewis Gun"),
    )
    timeline = Timeline(
        duration_frames=60,
        plan_sha256="sha60",
        audio=TimelineAudio(narration=TimelineNarration(src="audio/narration.wav")),
        captions=TimelineCaptions(pages=[]),
        scenes=[sc1],
    )
    (job_dir / "timeline.json").write_text(timeline.model_dump_json(), encoding="utf-8")

    # Mock render_stills so remotion isn't invoked, but create a dummy scene_s001.png
    preview_dir = job_dir / "preview"
    preview_dir.mkdir(parents=True)
    dummy_still = Image.new("RGB", (270, 480), color=(50, 50, 50))
    dummy_still.save(preview_dir / "scene_s001.png")

    monkeypatch.setattr(
        "animated_infographics.stages.preview.render_stills",
        lambda *args, **kwargs: [],
    )

    job = Job(job_dir)
    ctx = RunContext()
    run_preview_stage(job, ctx)

    # 1. Contact sheet label strip pixel is #FF6B8B (RGB 255, 107, 139)
    cs_path = preview_dir / "contact_sheet.png"
    assert cs_path.is_file()
    with Image.open(cs_path) as im:
        # Tile 0: x in [0, 270], label strip is y in [480, 524]
        # Sample pixel at (10, 490)
        pixel = im.getpixel((10, 490))
        assert pixel == (255, 107, 139)

    # 2. Storyboard markdown row for s001 contains "image failed"
    sb_md = (preview_dir / "storyboard.md").read_text(encoding="utf-8")
    assert "image failed" in sb_md

    # 3. Report json contains failed_images ["v1"] and warnings ["p1"]
    rep_path = preview_dir / "report.json"
    assert rep_path.is_file()
    rep = json.loads(rep_path.read_text(encoding="utf-8"))
    assert rep["failed_images"] == ["v1"]
    assert "p1" in rep.get("warnings", [])

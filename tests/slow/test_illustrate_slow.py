"""Slow integration tests for illustration generation per docs/agent_execution_guide.md Item A21."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from animated_infographics.assets.illustrate import (
    generate,
    image_prompt,
)
from animated_infographics.compile import compile_timeline
from animated_infographics.contracts.models import (
    Beat,
    Bible,
    Place,
    SetPiece,
    Storyboard,
    Transcript,
    TranscriptWord,
)
from animated_infographics.jobs import Job, RunContext
from animated_infographics.preview import generate_preview_report
from animated_infographics.stages.assets import run_assets_stage


@pytest.mark.slow
def test_illustrate_cache_hit_under_one_second(tmp_path: Path) -> None:
    """The second generation of the same prompt is a cache hit in < 1 s."""
    prompt = image_prompt(
        "place",
        (
            "A rugged lakeside estate with an old house on the rocky shore of "
            "Lake Superior in Duluth in 1961"
        ),
    )
    out1 = tmp_path / "out1.png"
    out2 = tmp_path / "out2.png"

    # First run (may generate or already be cached from prior run)
    res1 = generate(prompt, out1)
    assert res1.ok is True
    assert out1.is_file()

    # Second run MUST be a cache hit in < 1 second
    t0 = time.perf_counter()
    res2 = generate(prompt, out2)
    elapsed = time.perf_counter() - t0

    assert res2.ok is True
    assert res2.status == "cached"
    assert out2.is_file()
    assert elapsed < 1.0, f"Cache hit took {elapsed:.3f}s, expected < 1.0s"


@pytest.mark.slow
def test_illustrate_timeout_fallback_falsification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Falsification of fallback path:

    With INFOGRAPHICS_IMAGE_TIMEOUT_S=1 every uncached image fails,
    manifest says 'failed', report lists them, and preview uses icon fallbacks.
    """
    dummy_input = tmp_path / "story.txt"
    dummy_input.write_text("Test fallback story", encoding="utf-8")
    job = Job.create(dummy_input, tmp_path, datetime.now(UTC))

    # Unique prompts guaranteed not in cache
    unique_ts = int(time.time() * 1000)
    place = Place(
        id="p1",
        name="Uncached Duluth",
        kind="real",
        country_iso3="USA",
        lat=46.78,
        lon=-92.11,
        geo_source="gazetteer",
        visual_description=f"Uncached unique location description {unique_ts}",
        icon="House",
    )
    set_piece = SetPiece(
        id="v1",
        name="Uncached Box",
        visual_description=f"Uncached unique set piece description {unique_ts}",
        icon="Package",
    )

    bible = Bible(
        title="Fallback Test Story",
        logline="Testing timeout fallback",
        genre="history",
        places=[place],
        set_pieces=[set_piece],
    )
    (job.dir / "bible.json").write_text(bible.model_dump_json(indent=2) + "\n", encoding="utf-8")

    # Set timeout to 1 second
    monkeypatch.setenv("INFOGRAPHICS_IMAGE_TIMEOUT_S", "1")

    # Run assets stage
    ctx = RunContext()
    run_assets_stage(job, ctx)

    # 1. Manifest says 'failed' for both entities
    manifest_path = job.dir / "assets" / "manifest.json"
    assert manifest_path.is_file()
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    entities = manifest_data.get("entities", [])
    assert len(entities) == 2
    for e in entities:
        assert e["status"] == "failed"
        assert "timed out" in e["error"].lower() or "timeout" in e["error"].lower()

    # 2. Compile timeline: image must be None, triggering icon fallbacks
    from animated_infographics.contracts.models import TranscriptSentence

    transcript = Transcript(
        schema_version=1,
        source="tts",
        audio_path="narration.wav",
        duration_ms=2400,
        sentences=[
            TranscriptSentence(
                i=0,
                text="A rugged house.",
                start_ms=0,
                end_ms=1200,
                word_start=0,
                word_end=3,
                paragraph_i=0,
            ),
            TranscriptSentence(
                i=1,
                text="And a recipe box.",
                start_ms=1200,
                end_ms=2400,
                word_start=3,
                word_end=7,
                paragraph_i=0,
            ),
        ],
        words=[
            TranscriptWord(i=0, text="A", start_ms=0, end_ms=200, sentence_i=0),
            TranscriptWord(i=1, text="rugged", start_ms=200, end_ms=600, sentence_i=0),
            TranscriptWord(i=2, text="house.", start_ms=600, end_ms=1200, sentence_i=0),
            TranscriptWord(i=3, text="And", start_ms=1200, end_ms=1500, sentence_i=1),
            TranscriptWord(i=4, text="a", start_ms=1500, end_ms=1700, sentence_i=1),
            TranscriptWord(i=5, text="recipe", start_ms=1700, end_ms=2000, sentence_i=1),
            TranscriptWord(i=6, text="box.", start_ms=2000, end_ms=2400, sentence_i=1),
        ],
    )
    beats = [
        Beat(i=0, word_start=0, word_end=3, start_ms=0, end_ms=1200, text="A rugged house."),
        Beat(i=1, word_start=3, word_end=7, start_ms=1200, end_ms=2400, text="And a recipe box."),
    ]
    from animated_infographics.contracts.models import (
        LocationProps,
        LocationScene,
        SetPieceProps,
        SetPieceScene,
    )

    storyboard = Storyboard(
        scenes=[
            LocationScene(
                id="s000",
                beat_i=0,
                template="location",
                props=LocationProps(place_id="p1"),
            ),
            SetPieceScene(
                id="s001",
                beat_i=1,
                template="set_piece",
                props=SetPieceProps(set_piece_id="v1"),
            ),
        ]
    )

    available_images: set[str] = set()
    images_dir = job.dir / "assets" / "images"
    if images_dir.is_dir():
        for f in images_dir.iterdir():
            if f.is_file() and f.suffix.lower() == ".png":
                available_images.add(f.stem)

    timeline = compile_timeline(
        transcript,
        beats,
        bible,
        storyboard,
        plan_sha256="test-sha",
        available_images=available_images,
    )
    assert timeline.places["p1"].image is None
    assert timeline.set_pieces["v1"].image is None

    timeline_path = job.dir / "timeline.json"
    timeline_path.write_text(timeline.model_dump_json(indent=2) + "\n", encoding="utf-8")

    # 3. preview/report.json lists the failed images
    report = generate_preview_report(job.dir, None, [], "test-sha")
    assert report["failed_images"] == ["p1", "v1"]
    report_file = job.dir / "preview" / "report.json"
    assert report_file.is_file()
    saved_report = json.loads(report_file.read_text(encoding="utf-8"))
    assert saved_report["failed_images"] == ["p1", "v1"]


@pytest.mark.slow
def test_story_recipe_box_assets_budget(tmp_path: Path) -> None:
    """Measure images per fixture and assets wall time on story_recipe_box (budget fixture)."""
    dummy_input = tmp_path / "story_recipe_box.txt"
    dummy_input.write_text("Recipe box story", encoding="utf-8")
    job = Job.create(dummy_input, tmp_path, datetime.now(UTC))

    # Recipe box bible entities: 2 places (Duluth, Thunder Bay) + 1 set piece (Recipe Box)
    bible = Bible(
        title="The Recipe Box Secret",
        logline="A granddaughter discovers Grandma Rose's secret recipes in Duluth.",
        genre="personal_story",
        places=[
            Place(
                id="p1",
                name="Duluth",
                kind="real",
                country_iso3="USA",
                lat=46.78,
                lon=-92.11,
                geo_source="gazetteer",
                visual_description=(
                    "A rugged lakeside estate with an old house on the rocky shore of "
                    "Lake Superior in Duluth in 1961"
                ),
                icon="House",
            ),
            Place(
                id="p2",
                name="Thunder Bay",
                kind="real",
                country_iso3="CAN",
                lat=48.38,
                lon=-89.25,
                geo_source="gazetteer",
                visual_description="The harbor and shoreline of Thunder Bay with ships docked",
                icon="MapPin",
            ),
        ],
        set_pieces=[
            SetPiece(
                id="v1",
                name="Grandma Rose's Recipe Box",
                visual_description="Grandma Rose vintage wooden recipe box with index cards",
                icon="Package",
            )
        ],
    )
    (job.dir / "bible.json").write_text(bible.model_dump_json(indent=2) + "\n", encoding="utf-8")

    t0 = time.perf_counter()
    ctx = RunContext()
    run_assets_stage(job, ctx)
    total_wall_s = time.perf_counter() - t0

    manifest_path = job.dir / "assets" / "manifest.json"
    assert manifest_path.is_file()
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    entities = manifest_data.get("entities", [])

    # Bible caps: places <= 4, set_pieces <= 3 (total <= 7)
    assert len(entities) == 3
    assert len(entities) <= 7

    # Log measurements for the budget report
    print(
        f"\n[ASSETS BUDGET] story_recipe_box: {len(entities)} images, "
        f"total wall time: {total_wall_s:.2f}s"
    )
    for ent in entities:
        print(f"  - {ent['id']}: status={ent['status']}, elapsed_ms={ent['elapsed_ms']}")
        assert ent["status"] in ("generated", "cached")

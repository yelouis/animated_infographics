"""Unit tests for illustration text check per design_visual_direction.md §7.1 and Item B10."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from animated_infographics.assets.illustrate import (
    run_assets,
    text_expected,
)
from animated_infographics.assets.text_check import (
    TextCheckResult,
    decide_has_text,
)
from animated_infographics.contracts.models import Bible, Place, SetPiece
from animated_infographics.jobs import Job


def test_text_expected_word_and_phrase_rules() -> None:
    """Verify text_expected classifies descriptions according to §7.1."""
    # Positive word cases
    assert text_expected("handwritten recipe cards") is True
    assert (
        text_expected("An old wooden box overflowing with hundreds of handwritten recipe cards")
        is True
    )
    assert text_expected("A book on the desk") is True
    assert text_expected("A blackboard in a classroom") is True
    assert text_expected("A parchment scroll") is True
    assert text_expected("A telegram on the table") is True

    # Positive phrase cases
    assert text_expected("a neon sign above the door") is True
    assert text_expected("a street sign at the intersection") is True
    assert text_expected("old road signs on route 66") is True
    assert text_expected("a shop sign in the market") is True
    assert text_expected("bright store signs") is True

    # Negative cases (including the bare 'sign' exclusion)
    assert text_expected("showing signs of structural weakness") is False
    assert text_expected("a wooden signpost") is True  # signpost is in words list
    assert text_expected("a wooden sign") is False  # bare sign excluded
    assert text_expected("signs of wear and tear") is False
    assert text_expected("A golden-crusted blueberry pie with deep purple fruit filling") is False
    assert text_expected("A lakeside city with historic houses and a view of the water") is False
    assert (
        text_expected("A cozy, nostalgic small-town diner with a counter and warm lighting")
        is False
    )
    assert text_expected("A rugged estate on the shore of Lake Superior") is False
    assert text_expected("A Lewis gun mounted on a tripod") is False

    # Word boundary checks
    assert text_expected("assign the task") is False
    assert text_expected("signature dish") is False


def test_decide_has_text_alphanumeric_count_rule() -> None:
    """has_text iff kind == 'letters_or_words' and alphanumeric count in sample >= 3."""
    assert decide_has_text("letters_or_words", "Pecipte") is True
    assert decide_has_text("letters_or_words", "abc") is True
    assert decide_has_text("letters_or_words", "A 1 B") is True
    assert decide_has_text("letters_or_words", "ab") is False  # 2 chars < 3
    assert decide_has_text("letters_or_words", "∕") is False  # 0 chars < 3
    assert decide_has_text("letters_or_words", "!@#$%^&*()") is False
    assert decide_has_text("none", "") is False
    assert decide_has_text("none", "Pecipte") is False  # kind is none


def test_text_expected_skips_check_and_makes_zero_backend_calls(tmp_path: Path) -> None:
    """When text_expected is True, image is generated once and text check is skipped."""
    dummy_input = tmp_path / "story.txt"
    dummy_input.write_text("Test", encoding="utf-8")
    job = Job.create(dummy_input, tmp_path, datetime.now(UTC))

    bible = Bible(
        title="Recipe Story",
        logline="Grandma's recipe box",
        genre="personal_story",
        places=[],
        set_pieces=[
            SetPiece(
                id="v1",
                name="Recipe Box",
                visual_description="handwritten recipe cards in an old box",
                icon="Package",
            )
        ],
    )

    mock_backend = MagicMock()
    mock_backend.calls = 0

    with patch("animated_infographics.assets.illustrate.generate") as mock_gen:
        mock_gen.return_value = MagicMock(
            ok=True,
            status="generated",
            cache_key="key_recipe",
            elapsed_ms=1500,
            error=None,
        )
        manifest = run_assets(bible, job, backend=mock_backend)

    assert mock_backend.calls == 0
    assert mock_gen.call_count == 1
    ent = manifest.entities[0]
    assert ent.text_expected is True
    assert ent.text_check == "skipped"
    assert ent.status == "generated"
    assert len(ent.attempts) == 0


def test_run_assets_clean_on_first_attempt(tmp_path: Path) -> None:
    """When the first generation is clean, status is generated/clean with 1 attempt."""
    dummy_input = tmp_path / "story.txt"
    dummy_input.write_text("Test", encoding="utf-8")
    job = Job.create(dummy_input, tmp_path, datetime.now(UTC))

    bible = Bible(
        title="Pie Story",
        logline="Blueberry pie",
        genre="personal_story",
        places=[],
        set_pieces=[
            SetPiece(
                id="v1",
                name="Pie",
                visual_description="A blueberry pie on a table",
                icon="Package",
            )
        ],
    )

    mock_backend = MagicMock()
    mock_backend.calls = 1

    clean_result = TextCheckResult(
        kind="none",
        sample="",
        has_text=False,
        elapsed_ms=800,
    )

    with patch("animated_infographics.assets.illustrate.generate") as mock_gen:
        mock_gen.return_value = MagicMock(
            ok=True,
            status="generated",
            cache_key="key_pie",
            elapsed_ms=1200,
            error=None,
        )
        with patch(
            "animated_infographics.assets.illustrate.check_image_for_text",
            return_value=clean_result,
        ) as mock_chk:
            manifest = run_assets(bible, job, backend=mock_backend)

    assert mock_gen.call_count == 1
    assert mock_chk.call_count == 1
    ent = manifest.entities[0]
    assert ent.text_expected is False
    assert ent.text_check == "clean"
    assert ent.status == "generated"
    assert len(ent.attempts) == 1
    assert ent.attempts[0].kind == "none"


def test_run_assets_regenerated_on_second_attempt(tmp_path: Path) -> None:
    """When attempt 0 has text and attempt 1 is clean, status is regenerated with seeds s, s+1."""
    dummy_input = tmp_path / "story.txt"
    dummy_input.write_text("Test", encoding="utf-8")
    job = Job.create(dummy_input, tmp_path, datetime.now(UTC))

    bible = Bible(
        title="Diner Story",
        logline="Small town diner",
        genre="history",
        places=[
            Place(
                id="p1",
                name="Diner",
                kind="real",
                country_iso3="USA",
                lat=40.0,
                lon=-80.0,
                geo_source="gazetteer",
                visual_description="A small town diner exterior",
                icon="House",
            )
        ],
        set_pieces=[],
    )

    mock_backend = MagicMock()
    mock_backend.calls = 2

    # Attempt 0: texty ("Pecipte"), Attempt 1: clean ("none")
    check_results = [
        TextCheckResult(kind="letters_or_words", sample="Pecipte", has_text=True, elapsed_ms=800),
        TextCheckResult(kind="none", sample="", has_text=False, elapsed_ms=750),
    ]

    seeds_called: list[int] = []

    def fake_generate(
        prompt: str, out: Path, *, seed: int | None = None, timeout_s: int = 180
    ) -> Any:
        seeds_called.append(seed or 0)
        return MagicMock(
            ok=True,
            status="generated",
            cache_key=f"key_seed_{seed}",
            elapsed_ms=1200,
            error=None,
        )

    with patch(
        "animated_infographics.assets.illustrate.generate", side_effect=fake_generate
    ) as mock_gen:
        with patch(
            "animated_infographics.assets.illustrate.check_image_for_text",
            side_effect=check_results,
        ) as mock_chk:
            manifest = run_assets(bible, job, backend=mock_backend)

    assert mock_gen.call_count == 2
    assert mock_chk.call_count == 2
    assert len(seeds_called) == 2
    assert seeds_called[1] == seeds_called[0] + 1

    ent = manifest.entities[0]
    assert ent.text_expected is False
    assert ent.text_check == "regenerated"
    assert ent.status == "generated"
    assert len(ent.attempts) == 2
    assert ent.attempts[0].kind == "letters_or_words"
    assert ent.attempts[1].kind == "none"


def test_run_assets_three_texty_attempts_fails(tmp_path: Path) -> None:
    """When all 3 attempts have lettering, status is failed and error is
    'lettering detected in 3 attempts'.
    """
    dummy_input = tmp_path / "story.txt"
    dummy_input.write_text("Test", encoding="utf-8")
    job = Job.create(dummy_input, tmp_path, datetime.now(UTC))

    bible = Bible(
        title="Diner Story",
        logline="Small town diner",
        genre="history",
        places=[
            Place(
                id="p1",
                name="Diner",
                kind="real",
                country_iso3="USA",
                lat=40.0,
                lon=-80.0,
                geo_source="gazetteer",
                visual_description="A small town diner exterior",
                icon="House",
            )
        ],
        set_pieces=[],
    )

    mock_backend = MagicMock()
    mock_backend.calls = 3

    check_results = [
        TextCheckResult(kind="letters_or_words", sample="TEXT1", has_text=True, elapsed_ms=800),
        TextCheckResult(kind="letters_or_words", sample="TEXT2", has_text=True, elapsed_ms=800),
        TextCheckResult(kind="letters_or_words", sample="TEXT3", has_text=True, elapsed_ms=800),
    ]

    seeds_called: list[int] = []

    def fake_generate(
        prompt: str, out: Path, *, seed: int | None = None, timeout_s: int = 180
    ) -> Any:
        seeds_called.append(seed or 0)
        return MagicMock(
            ok=True,
            status="generated",
            cache_key=f"key_seed_{seed}",
            elapsed_ms=1200,
            error=None,
        )

    with patch(
        "animated_infographics.assets.illustrate.generate", side_effect=fake_generate
    ) as mock_gen:
        with patch(
            "animated_infographics.assets.illustrate.check_image_for_text",
            side_effect=check_results,
        ) as mock_chk:
            manifest = run_assets(bible, job, backend=mock_backend)

    assert mock_gen.call_count == 3
    assert mock_chk.call_count == 3
    assert len(seeds_called) == 3
    s0 = seeds_called[0]
    assert seeds_called == [s0, s0 + 1, s0 + 2]

    ent = manifest.entities[0]
    assert ent.text_expected is False
    assert ent.text_check == "failed"
    assert ent.status == "failed"
    assert ent.error == "lettering detected in 3 attempts"
    assert len(ent.attempts) == 3


def test_run_assets_check_unavailable_keeps_image(tmp_path: Path) -> None:
    """When the check fails/times out, image is kept and text_check is unavailable."""
    dummy_input = tmp_path / "story.txt"
    dummy_input.write_text("Test", encoding="utf-8")
    job = Job.create(dummy_input, tmp_path, datetime.now(UTC))

    bible = Bible(
        title="Diner Story",
        logline="Small town diner",
        genre="history",
        places=[
            Place(
                id="p1",
                name="Diner",
                kind="real",
                country_iso3="USA",
                lat=40.0,
                lon=-80.0,
                geo_source="gazetteer",
                visual_description="A small town diner exterior",
                icon="House",
            )
        ],
        set_pieces=[],
    )

    mock_backend = MagicMock()

    with patch("animated_infographics.assets.illustrate.generate") as mock_gen:
        mock_gen.return_value = MagicMock(
            ok=True,
            status="generated",
            cache_key="key_p1",
            elapsed_ms=1200,
            error=None,
        )
        with patch(
            "animated_infographics.assets.illustrate.check_image_for_text", return_value=None
        ):
            manifest = run_assets(bible, job, backend=mock_backend)

    assert mock_gen.call_count == 1
    ent = manifest.entities[0]
    assert ent.text_expected is False
    assert ent.text_check == "unavailable"
    assert ent.status == "generated"

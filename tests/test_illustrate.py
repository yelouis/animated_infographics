"""Unit tests for illustration generation per design_visual_direction.md §7."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from animated_infographics.assets.illustrate import (
    STYLE,
    ImageResult,
    cache_key,
    image_prompt,
    image_seed,
    run_assets,
)
from animated_infographics.contracts.models import Bible, Place, SetPiece
from animated_infographics.jobs import Job


def test_style_string_matches_doc_verbatim() -> None:
    expected_style = (
        "Flat vector editorial illustration, bold simple geometric shapes, "
        "smooth flat colour fills, "
        "no gradients, no outlines, limited palette of deep navy, warm orange, teal, "
        "mustard yellow and coral, clean uncluttered composition, plain background. "
        "No text, no letters, no words, "
        "no numbers, no watermark, no logo."
    )
    assert STYLE == expected_style


def test_image_prompt_matches_doc_byte_for_byte() -> None:
    desc = "A rugged estate on the shore of Lake Superior"
    place_p = image_prompt("place", desc)
    expected_place = (
        f"{desc}. Wide establishing view of the place, no people in the foreground. {STYLE}"
    )
    assert place_p == expected_place

    sp_desc = "Grandma Rose's Recipe Box"
    sp_p = image_prompt("set_piece", sp_desc)
    expected_sp = f"{sp_desc}. One clear central subject. {STYLE}"
    assert sp_p == expected_sp

    with pytest.raises(ValueError, match="Unknown illustration kind"):
        image_prompt("character", desc)  # type: ignore[arg-type]


def test_image_seed_stable_and_in_range() -> None:
    prompts = [
        "Duluth harbor at sunrise",
        "Grandma Rose's Recipe Box",
        "Boston molasses tank",
        "A rugged estate on Lake Superior",
        "",
        "a" * 500,
    ]
    for p in prompts:
        s1 = image_seed(p)
        s2 = image_seed(p)
        assert s1 == s2, "Seed must be deterministic"
        assert 0 <= s1 < 2**31, f"Seed {s1} must be in [0, 2**31)"

        # Verify formula: int(sha256(p)[:8], 16) % 2**31
        expected = int(hashlib.sha256(p.encode("utf-8")).hexdigest()[:8], 16) % (2**31)
        assert s1 == expected


def test_cache_key_changes_on_any_keyed_field() -> None:
    prompt_a = "Prompt A"
    prompt_b = "Prompt B"
    version_1 = "0.20.0"
    version_2 = "0.21.0"

    key_base = cache_key(prompt_a, mflux_version=version_1)
    assert len(key_base) == 64
    assert isinstance(key_base, str)

    # Identical inputs produce identical key
    assert cache_key(prompt_a, mflux_version=version_1) == key_base

    # Prompt change
    key_prompt_change = cache_key(prompt_b, mflux_version=version_1)
    assert key_prompt_change != key_base

    # Version change
    key_version_change = cache_key(prompt_a, mflux_version=version_2)
    assert key_version_change != key_base


def test_cache_key_differs_for_seed_and_seed_plus_one() -> None:
    prompt = "A rugged estate on the shore of Lake Superior"
    version = "0.20.0"
    s = image_seed(prompt)
    key_s = cache_key(prompt, seed=s, mflux_version=version)
    key_s1 = cache_key(prompt, seed=s + 1, mflux_version=version)
    assert key_s != key_s1
    assert cache_key(prompt, seed=None, mflux_version=version) == key_s


def test_generate_cache_hit_does_not_invoke_subprocess(tmp_path: Path) -> None:
    from animated_infographics.assets.illustrate import generate

    prompt = "Test prompt for cache hit"
    version = "0.20.0"
    key = cache_key(prompt, mflux_version=version)

    # Prepare cached image
    cache_dir = Path("cache/images")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{key}.png"

    img = Image.new("RGB", (1024, 1024), color=(30, 45, 80))
    img.save(cache_file, "PNG")

    try:
        out_file = tmp_path / "out.png"
        with patch("subprocess.run") as mock_sub:
            with patch(
                "animated_infographics.assets.illustrate.get_mflux_version", return_value=version
            ):
                res = generate(prompt, out_file, timeout_s=10)

        assert mock_sub.call_count == 0
        assert res.ok is True
        assert res.status == "cached"
        assert res.path == out_file
        assert out_file.is_file()
        with Image.open(out_file) as out_img:
            assert out_img.size == (1024, 1024)
    finally:
        cache_file.unlink(missing_ok=True)


def test_generate_missing_executable_returns_failed_result(tmp_path: Path) -> None:
    from animated_infographics.assets.illustrate import generate

    prompt = "Test prompt for missing tool"
    out_file = tmp_path / "out.png"

    with patch("shutil.which", return_value=None):
        with patch.object(Path, "is_file", return_value=False):
            res = generate(prompt, out_file, timeout_s=10)

    assert res.ok is False
    assert res.status == "failed"
    assert res.path is None
    assert "not found" in (res.error or "")


def test_generate_timeout_returns_failed_result(tmp_path: Path) -> None:
    import subprocess

    from animated_infographics.assets.illustrate import generate

    prompt = "Test prompt for timeout"
    out_file = tmp_path / "out.png"

    timeout_exc = subprocess.TimeoutExpired(cmd=["mock"], timeout=1)
    with patch("shutil.which", return_value="/bin/mflux-mock"):
        with patch("subprocess.run", side_effect=timeout_exc):
            res = generate(prompt, out_file, timeout_s=1)

    assert res.ok is False
    assert res.status == "failed"
    assert "timed out" in (res.error or "").lower()


def test_run_assets_generates_manifest(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    dummy_input = tmp_path / "story.txt"
    dummy_input.write_text("Test", encoding="utf-8")
    job = Job.create(dummy_input, tmp_path, datetime.now(UTC))

    bible = Bible(
        title="Test Story",
        logline="Test Logline",
        genre="history",
        places=[
            Place(
                id="p1",
                name="Duluth",
                kind="real",
                country_iso3="USA",
                lat=46.78,
                lon=-92.11,
                geo_source="gazetteer",
                visual_description="A house on the shore",
                icon="House",
            )
        ],
        set_pieces=[
            SetPiece(
                id="v1",
                name="Recipe Box",
                visual_description="Wooden recipe box",
                icon="Package",
            )
        ],
    )

    mock_res = ImageResult(
        ok=True,
        path=tmp_path / "assets" / "images" / "p1.png",
        error=None,
        elapsed_ms=120,
        status="generated",
        cache_key="mockkey123",
    )

    with patch("animated_infographics.assets.illustrate.generate", return_value=mock_res):
        manifest = run_assets(bible, job)

    assert len(manifest.entities) == 2
    assert manifest.entities[0].id == "p1"
    assert manifest.entities[0].status == "generated"
    assert manifest.entities[1].id == "v1"

    manifest_file = job.dir / "assets" / "manifest.json"
    assert manifest_file.is_file()
    data = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert len(data["entities"]) == 2

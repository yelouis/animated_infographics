"""Illustration generation for places and set pieces using FLUX.2 klein 4B."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from PIL import Image
from pydantic import BaseModel, ConfigDict, Field

from animated_infographics.contracts.models import Bible
from animated_infographics.jobs import Job

# ---------------------------------------------------------------------------
# Constants per design_visual_direction.md §7
# ---------------------------------------------------------------------------

STYLE: Final[str] = (
    "Flat vector editorial illustration, bold simple geometric shapes, smooth flat colour fills, "
    "no gradients, no outlines, limited palette of deep navy, warm orange, teal, mustard yellow "
    "and coral, clean uncluttered composition, plain background. No text, no letters, no words, "
    "no numbers, no watermark, no logo."
)

MODEL_NAME: Final[str] = "flux2-klein-4b"
TOOL_NAME: Final[str] = "mflux-generate-flux2-klein"
IMAGE_WIDTH: Final[int] = 1024
IMAGE_HEIGHT: Final[int] = 1024
IMAGE_STEPS: Final[int] = 4
IMAGE_QUANTIZE: Final[int] = 8
DEFAULT_TIMEOUT_S: Final[int] = 180


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


class AssetEntity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    prompt: str
    cache_key: str
    status: Literal["generated", "cached", "failed"]
    elapsed_ms: int
    error: str | None = None


class AssetManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    entities: list[AssetEntity] = Field(default_factory=list)


@dataclass(frozen=True)
class ImageResult:
    ok: bool
    path: Path | None
    error: str | None
    elapsed_ms: int
    status: Literal["generated", "cached", "failed"] = "failed"
    cache_key: str = ""


# ---------------------------------------------------------------------------
# Core Interface Functions
# ---------------------------------------------------------------------------


def image_prompt(kind: Literal["place", "set_piece"], visual_description: str) -> str:
    """Build the exact prompt for a place or set piece per design_visual_direction.md §7."""
    clean_desc = visual_description.strip().rstrip(".")
    if kind == "place":
        return (
            f"{clean_desc}. Wide establishing view of the place, "
            f"no people in the foreground. {STYLE}"
        )
    elif kind == "set_piece":
        return f"{clean_desc}. One clear central subject. {STYLE}"
    else:
        raise ValueError(f"Unknown illustration kind: {kind}")


def image_seed(prompt: str) -> int:
    """Compute deterministic seed in [0, 2**31) from prompt hash."""
    return int(hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8], 16) % (2**31)


def cache_key(prompt: str, *, mflux_version: str) -> str:
    """Compute canonical cache key from generation parameters."""
    payload = {
        "height": IMAGE_HEIGHT,
        "mflux_version": mflux_version,
        "model": MODEL_NAME,
        "prompt": prompt,
        "quantize": IMAGE_QUANTIZE,
        "seed": image_seed(prompt),
        "steps": IMAGE_STEPS,
        "tool": TOOL_NAME,
        "width": IMAGE_WIDTH,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def get_mflux_version() -> str:
    """Inspect installed mflux version via uv tool list or return fallback."""
    try:
        proc = subprocess.run(
            ["uv", "tool", "list"], capture_output=True, text=True, timeout=5, check=False
        )
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line.startswith("mflux v"):
                return line.split("v", 1)[1].strip()
    except Exception:
        pass
    return "0.20.0"


def generate(prompt: str, out: Path, *, timeout_s: int = DEFAULT_TIMEOUT_S) -> ImageResult:
    """Generate image via mflux-generate-flux2-klein subprocess; never raises on tool failure."""
    t0 = time.perf_counter()
    mflux_ver = get_mflux_version()
    key = cache_key(prompt, mflux_version=mflux_ver)
    base_cache = Path(os.environ.get("INFOGRAPHICS_CACHE_DIR", "./cache"))
    cache_dir = base_cache / "images"
    cache_path = cache_dir / f"{key}.png"

    # 1. Check cache hit
    if cache_path.is_file():
        try:
            with Image.open(cache_path) as img:
                if img.size == (IMAGE_WIDTH, IMAGE_HEIGHT):
                    img.verify()
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(cache_path, out)
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            return ImageResult(
                ok=True,
                path=out,
                error=None,
                elapsed_ms=elapsed_ms,
                status="cached",
                cache_key=key,
            )
        except Exception:
            # Corrupted cache file; delete and re-generate
            cache_path.unlink(missing_ok=True)

    # 2. Locate tool binary
    bin_path = shutil.which(TOOL_NAME)
    if not bin_path:
        home_bin = Path.home() / ".local" / "bin" / TOOL_NAME
        if home_bin.is_file():
            bin_path = str(home_bin)
        else:
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            return ImageResult(
                ok=False,
                path=None,
                error=f"Executable '{TOOL_NAME}' not found",
                elapsed_ms=elapsed_ms,
                status="failed",
                cache_key=key,
            )

    seed = image_seed(prompt)
    temp_dir = Path(tempfile.gettempdir())
    temp_file = temp_dir / f"mflux_{key}_{int(time.time() * 1000)}.png"

    # Note: The installed mflux v0.20.0 supports --model flux2-klein-4b for the 4B weights.
    # Verified with `mflux-generate-flux2-klein --help` where --model accepts `flux2-klein-4b`.
    cmd = [
        bin_path,
        "--model",
        MODEL_NAME,
        "--quantize",
        str(IMAGE_QUANTIZE),
        "--steps",
        str(IMAGE_STEPS),
        "--width",
        str(IMAGE_WIDTH),
        "--height",
        str(IMAGE_HEIGHT),
        "--seed",
        str(seed),
        "--prompt",
        prompt,
        "--output",
        str(temp_file),
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        if proc.returncode != 0:
            if temp_file.is_file():
                temp_file.unlink(missing_ok=True)
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            err_msg = proc.stderr.strip() or f"Process exited with {proc.returncode}"
            return ImageResult(
                ok=False,
                path=None,
                error=f"mflux exited with code {proc.returncode}: {err_msg}",
                elapsed_ms=elapsed_ms,
                status="failed",
                cache_key=key,
            )

        if not temp_file.is_file():
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            return ImageResult(
                ok=False,
                path=None,
                error="mflux succeeded but output file was not found",
                elapsed_ms=elapsed_ms,
                status="failed",
                cache_key=key,
            )

        # Validate with Pillow
        with Image.open(temp_file) as img:
            if img.size != (IMAGE_WIDTH, IMAGE_HEIGHT):
                temp_file.unlink(missing_ok=True)
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                return ImageResult(
                    ok=False,
                    path=None,
                    error=(
                        f"Generated image size is {img.size}, "
                        f"expected ({IMAGE_WIDTH}, {IMAGE_HEIGHT})"
                    ),
                    elapsed_ms=elapsed_ms,
                    status="failed",
                    cache_key=key,
                )
            img.verify()

        # Atomic rename into cache/images/<key>.png
        cache_dir.mkdir(parents=True, exist_ok=True)
        temp_file.replace(cache_path)

        # Copy to destination
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cache_path, out)

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return ImageResult(
            ok=True,
            path=out,
            error=None,
            elapsed_ms=elapsed_ms,
            status="generated",
            cache_key=key,
        )

    except subprocess.TimeoutExpired:
        if temp_file.is_file():
            temp_file.unlink(missing_ok=True)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return ImageResult(
            ok=False,
            path=None,
            error=f"Image generation timed out after {timeout_s}s",
            elapsed_ms=elapsed_ms,
            status="failed",
            cache_key=key,
        )
    except Exception as e:
        if temp_file.is_file():
            temp_file.unlink(missing_ok=True)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return ImageResult(
            ok=False,
            path=None,
            error=str(e),
            elapsed_ms=elapsed_ms,
            status="failed",
            cache_key=key,
        )


def run_assets(bible: Bible, job: Job) -> AssetManifest:
    """Run illustration generation for all places and set pieces in bible."""
    timeout_s = int(os.environ.get("INFOGRAPHICS_IMAGE_TIMEOUT_S", DEFAULT_TIMEOUT_S))
    mflux_ver = get_mflux_version()
    images_dir = job.dir / "assets" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    entities: list[AssetEntity] = []

    # Places: up to 4 per bible cap
    for p in bible.places[:4]:
        prompt = image_prompt("place", p.visual_description)
        key = cache_key(prompt, mflux_version=mflux_ver)
        out_path = images_dir / f"{p.id}.png"
        res = generate(prompt, out_path, timeout_s=timeout_s)
        entities.append(
            AssetEntity(
                id=p.id,
                prompt=prompt,
                cache_key=key,
                status=res.status,
                elapsed_ms=res.elapsed_ms,
                error=res.error,
            )
        )

    # Set pieces: up to 3 per bible cap
    for s in bible.set_pieces[:3]:
        prompt = image_prompt("set_piece", s.visual_description)
        key = cache_key(prompt, mflux_version=mflux_ver)
        out_path = images_dir / f"{s.id}.png"
        res = generate(prompt, out_path, timeout_s=timeout_s)
        entities.append(
            AssetEntity(
                id=s.id,
                prompt=prompt,
                cache_key=key,
                status=res.status,
                elapsed_ms=res.elapsed_ms,
                error=res.error,
            )
        )

    manifest = AssetManifest(schema_version=1, entities=entities)
    manifest_path = job.dir / "assets" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return manifest

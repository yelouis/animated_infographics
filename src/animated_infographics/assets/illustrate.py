"""Illustration generation for places and set pieces using FLUX.2 klein 4B."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from PIL import Image
from pydantic import BaseModel, ConfigDict, Field

from animated_infographics.assets.text_check import check_image_for_text
from animated_infographics.contracts.models import Bible
from animated_infographics.jobs import Job
from animated_infographics.planner.llm import LLMBackend, OllamaBackend

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
TOOL_NAME: Final[str] = "mflux-generate-flux2"
IMAGE_WIDTH: Final[int] = 1024
IMAGE_HEIGHT: Final[int] = 1024
IMAGE_STEPS: Final[int] = 4
IMAGE_QUANTIZE: Final[int] = 8
DEFAULT_TIMEOUT_S: Final[int] = 180

TEXT_EXPECTED_WORDS: Final[frozenset[str]] = frozenset(
    {
        "recipe",
        "recipes",
        "card",
        "cards",
        "letter",
        "letters",
        "note",
        "notes",
        "signpost",
        "signposts",
        "signage",
        "newspaper",
        "newspapers",
        "headline",
        "headlines",
        "menu",
        "menus",
        "book",
        "books",
        "page",
        "pages",
        "label",
        "labels",
        "poster",
        "posters",
        "handwriting",
        "handwritten",
        "writing",
        "written",
        "text",
        "texts",
        "message",
        "messages",
        "document",
        "documents",
        "notebook",
        "notebooks",
        "diary",
        "diaries",
        "journal",
        "journals",
        "envelope",
        "envelopes",
        "receipt",
        "receipts",
        "invoice",
        "invoices",
        "certificate",
        "certificates",
        "ticket",
        "tickets",
        "banner",
        "banners",
        "billboard",
        "billboards",
        "plaque",
        "plaques",
        "scroll",
        "scrolls",
        "manuscript",
        "manuscripts",
        "telegram",
        "telegrams",
        "postcard",
        "postcards",
        "calendar",
        "calendars",
        "chalkboard",
        "chalkboards",
        "blackboard",
        "blackboards",
        "whiteboard",
        "whiteboards",
        "screen",
        "screens",
        "inscription",
        "inscriptions",
        "placard",
        "placards",
        "flyer",
        "flyers",
        "leaflet",
        "leaflets",
        "map",
        "maps",
    }
)

TEXT_EXPECTED_PHRASES: Final[frozenset[str]] = frozenset(
    {
        "street sign",
        "street signs",
        "shop sign",
        "shop signs",
        "road sign",
        "road signs",
        "neon sign",
        "neon signs",
        "store sign",
        "store signs",
    }
)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


class CheckAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    seed: int
    kind: str
    sample: str
    elapsed_ms: int


class AssetEntity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    prompt: str
    cache_key: str
    status: Literal["generated", "cached", "failed"]
    elapsed_ms: int
    error: str | None = None
    text_expected: bool = False
    text_check: Literal["skipped", "clean", "regenerated", "failed", "unavailable"] = "clean"
    attempts: list[CheckAttempt] = Field(default_factory=list)


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


def text_expected(visual_description: str) -> bool:
    """Determine if visual description calls for lettering per design_visual_direction.md §7.1."""
    text = visual_description.casefold()
    words = set(re.findall(r"\b\w+\b", text))
    if words & TEXT_EXPECTED_WORDS:
        return True
    for phrase in TEXT_EXPECTED_PHRASES:
        if re.search(r"\b" + re.escape(phrase) + r"\b", text):
            return True
    return False


def image_prompt(kind: Literal["place", "set_piece", "metaphor"], visual_description: str) -> str:
    """Build the exact prompt for a place, set piece, or metaphor per design."""
    clean_desc = visual_description.strip().rstrip(".")
    if kind == "place":
        return (
            f"{clean_desc}. Wide establishing view of the place, "
            f"no people in the foreground. {STYLE}"
        )
    elif kind in ("set_piece", "metaphor"):
        return f"{clean_desc}. One clear central subject. {STYLE}"
    else:
        raise ValueError(f"Unknown illustration kind: {kind}")


def image_seed(prompt: str) -> int:
    """Compute deterministic seed in [0, 2**31) from prompt hash."""
    return int(hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8], 16) % (2**31)


def cache_key(prompt: str, *, seed: int | None = None, mflux_version: str) -> str:
    """Compute canonical cache key from generation parameters."""
    actual_seed = image_seed(prompt) if seed is None else seed
    payload = {
        "height": IMAGE_HEIGHT,
        "mflux_version": mflux_version,
        "model": MODEL_NAME,
        "prompt": prompt,
        "quantize": IMAGE_QUANTIZE,
        "seed": actual_seed,
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


def generate(
    prompt: str,
    out: Path,
    *,
    seed: int | None = None,
    timeout_s: int = DEFAULT_TIMEOUT_S,
) -> ImageResult:
    """Generate image via mflux-generate-flux2 subprocess; never raises on tool failure."""
    t0 = time.perf_counter()
    mflux_ver = get_mflux_version()
    actual_seed = image_seed(prompt) if seed is None else seed
    key = cache_key(prompt, seed=actual_seed, mflux_version=mflux_ver)
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

    temp_dir = Path(tempfile.gettempdir())
    temp_file = temp_dir / f"mflux_{key}_{int(time.time() * 1000)}.png"

    # Note: The installed mflux v0.20.0 supports --model flux2-klein-4b for the 4B weights.
    # Verified with `mflux-generate-flux2 --help` where --model accepts `flux2-klein-4b`.
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
        str(actual_seed),
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


def run_assets(bible: Bible, job: Job, backend: LLMBackend | None = None) -> AssetManifest:
    llm_backend = backend or OllamaBackend()
    timeout_s = int(os.environ.get("INFOGRAPHICS_IMAGE_TIMEOUT_S", DEFAULT_TIMEOUT_S))
    images_dir = job.dir / "assets" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    def process_entity(
        ent_id: str, kind: Literal["place", "set_piece", "metaphor"], visual_desc: str
    ) -> AssetEntity:
        prompt = image_prompt(kind, visual_desc)
        out_path = images_dir / f"{ent_id}.png"
        expected = text_expected(visual_desc)

        if expected:
            s0 = image_seed(prompt)
            res = generate(prompt, out_path, seed=s0, timeout_s=timeout_s)
            status: Literal["generated", "cached", "failed"] = res.status if res.ok else "failed"
            return AssetEntity(
                id=ent_id,
                prompt=prompt,
                cache_key=res.cache_key,
                status=status,
                elapsed_ms=res.elapsed_ms,
                error=res.error,
                text_expected=True,
                text_check="skipped",
                attempts=[],
            )

        # text_expected is False: check image with retry up to 2 regenerations (3 images total)
        s0 = image_seed(prompt)
        attempts: list[CheckAttempt] = []
        entity_status: Literal["generated", "cached", "failed"] = "failed"
        entity_error: str | None = None
        entity_text_check: Literal["skipped", "clean", "regenerated", "failed", "unavailable"] = (
            "clean"
        )
        final_key = ""
        total_elapsed_ms = 0

        for attempt_idx in range(3):
            current_seed = s0 + attempt_idx
            res = generate(prompt, out_path, seed=current_seed, timeout_s=timeout_s)
            final_key = res.cache_key
            total_elapsed_ms += res.elapsed_ms
            if not res.ok:
                entity_status = "failed"
                entity_error = res.error
                entity_text_check = "failed"
                break

            check_res = check_image_for_text(out_path, llm_backend)
            if check_res is None:
                # Check failed/unavailable -> keep image, text_check: unavailable
                entity_status = res.status
                entity_error = None
                entity_text_check = "unavailable"
                attempts.append(
                    CheckAttempt(
                        seed=current_seed,
                        kind="none",
                        sample="",
                        elapsed_ms=0,
                    )
                )
                break

            attempts.append(
                CheckAttempt(
                    seed=current_seed,
                    kind=check_res.kind,
                    sample=check_res.sample,
                    elapsed_ms=check_res.elapsed_ms,
                )
            )

            if not check_res.has_text:
                entity_status = res.status
                entity_error = None
                entity_text_check = "clean" if attempt_idx == 0 else "regenerated"
                break
            else:
                if attempt_idx == 2:
                    # 3 texty images -> failed with exact error
                    entity_status = "failed"
                    entity_error = "lettering detected in 3 attempts"
                    entity_text_check = "failed"
                    out_path.unlink(missing_ok=True)

        return AssetEntity(
            id=ent_id,
            prompt=prompt,
            cache_key=final_key,
            status=entity_status,
            elapsed_ms=total_elapsed_ms,
            error=entity_error,
            text_expected=False,
            text_check=entity_text_check,
            attempts=attempts,
        )

    entities: list[AssetEntity] = []

    # Places: up to 4 per bible cap
    for p in bible.places[:4]:
        entities.append(process_entity(p.id, "place", p.visual_description))

    # Set pieces: up to 3 per bible cap
    for s in bible.set_pieces[:3]:
        entities.append(process_entity(s.id, "set_piece", s.visual_description))

    # Metaphors from director.json if present
    director_path = job.dir / "director.json"
    if director_path.is_file():
        try:
            from animated_infographics.contracts.director import DirectorPlan

            d_plan = DirectorPlan.model_validate_json(director_path.read_text(encoding="utf-8"))
            for m in d_plan.metaphors:
                ent_id = f"metaphor_{m.beat_i}"
                entities.append(process_entity(ent_id, "metaphor", m.image))
        except Exception:
            pass

    manifest = AssetManifest(schema_version=1, entities=entities)
    manifest_path = job.dir / "assets" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return manifest

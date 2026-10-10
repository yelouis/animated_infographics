"""Illustration text check with automatic retry per design_visual_direction.md §7.1."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Literal

from PIL import Image

from animated_infographics.errors import DependencyMissing
from animated_infographics.planner.llm import LLMBackend, run_with_retries

TEXT_CHECK_PROMPT: Final[str] = (
    "You are checking an illustration for unwanted lettering. List marks that look like a "
    "LETTER, WORD or NUMBER (real or fake/illegible handwriting or lettering, e.g. on signs, "
    "cards, paper, screens). Do NOT count windows, bricks, stripes, textures, patterns, "
    "reflections, lines, arrows or single abstract symbols. Return JSON: kind = "
    '"letters_or_words" if any such marks exist, else "none"; sample = up to 20 characters '
    "of your best reading of the marks (gibberish allowed), empty if none."
)

TEXT_CHECK_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        "kind": {
            "type": "string",
            "enum": ["letters_or_words", "none"],
        },
        "sample": {
            "type": "string",
        },
    },
    "required": ["kind", "sample"],
    "additionalProperties": False,
}

REJECTED_NAIVE_PROMPT: Final[str] = (
    "Look at this illustration. Does it contain any letters, words, numbers or text-like marks, "
    "including illegible pseudo-handwriting or fake lettering on signs, cards or paper? "
    "Answer JSON: has_text (boolean) and evidence (where the marks are, or empty)."
)

REJECTED_NAIVE_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        "has_text": {"type": "boolean"},
        "evidence": {"type": "string"},
    },
    "required": ["has_text", "evidence"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class TextCheckResult:
    kind: Literal["letters_or_words", "none"]
    sample: str
    has_text: bool
    elapsed_ms: int


def decide_has_text(kind: str, sample: str) -> bool:
    """Decision rule per §7.1: kind == 'letters_or_words' and alphanumeric count in sample >= 3."""
    if kind != "letters_or_words":
        return False
    alphanumerics = re.findall(r"[A-Za-z0-9]", sample)
    return len(alphanumerics) >= 3


def validate_text_check(data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Validate structured response from Ollama for text check prompt."""
    errors: list[str] = []
    kind = data.get("kind")
    if kind not in ("letters_or_words", "none"):
        errors.append(f"Invalid kind '{kind}', expected 'letters_or_words' or 'none'")
    sample = data.get("sample")
    if not isinstance(sample, str):
        errors.append(f"Sample must be a string, got {type(sample).__name__}")
    return data, errors


def validate_naive_text_check(data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Validate structured response for rejected naive prompt."""
    errors: list[str] = []
    if "has_text" not in data or not isinstance(data.get("has_text"), bool):
        errors.append("has_text must be a boolean")
    if "evidence" not in data or not isinstance(data.get("evidence"), str):
        errors.append("evidence must be a string")
    return data, errors


def check_image_for_text(
    png_path: Path,
    backend: LLMBackend,
    *,
    prompt: str = TEXT_CHECK_PROMPT,
    schema: dict[str, Any] = TEXT_CHECK_SCHEMA,
    cache_dir: Path | None = None,
    attempt_offset: int = 0,
) -> TextCheckResult | None:
    """Run local vision text check using gemma4:26b resized to 512x512 via Lanczos.

    Returns None if backend request fails or times out.
    """
    base_cache = cache_dir or Path(os.environ.get("INFOGRAPHICS_CACHE_DIR", "./cache"))
    text_check_cache = base_cache / "text_check"

    if not png_path.is_file():
        return None

    try:
        png_bytes = png_path.read_bytes()
    except Exception:
        return None
    model_name = getattr(backend, "model", "gemma4:26b")
    cache_key = hashlib.sha256(
        png_bytes
        + model_name.encode("utf-8")
        + prompt.encode("utf-8")
        + str(attempt_offset).encode("utf-8")
    ).hexdigest()
    cache_file = text_check_cache / f"{cache_key}.json"

    # 1. Check disk cache
    if not getattr(backend, "no_cache", False) and cache_file.is_file():
        try:
            cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
            return TextCheckResult(
                kind=cached_data["kind"],
                sample=cached_data["sample"],
                has_text=cached_data["has_text"],
                elapsed_ms=cached_data.get("elapsed_ms", 0),
            )
        except Exception:
            pass

    # 2. Resize to 512x512 with Lanczos
    try:
        with Image.open(png_path) as img:
            img_rgb = img.convert("RGB")
            resized = img_rgb.resize((512, 512), resample=Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            resized.save(buf, format="PNG")
            resized_bytes = buf.getvalue()
    except Exception:
        return None

    # 3. Call backend through run_with_retries
    t0 = time.perf_counter()
    validate_fn = (
        validate_naive_text_check if prompt == REJECTED_NAIVE_PROMPT else validate_text_check
    )

    try:
        result, _attempts = run_with_retries(
            backend,
            stage="text_check",
            system="",
            user=prompt,
            schema=schema,
            validate=validate_fn,
            images=[resized_bytes],
            num_predict=96,
            temperature=0.0,
            max_attempts=3,
            attempt_offset=attempt_offset,
        )
    except DependencyMissing:
        return None
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    if result is None:
        return None

    if prompt == REJECTED_NAIVE_PROMPT:
        has_text = bool(result.get("has_text", False))
        sample = str(result.get("evidence", ""))
        kind = "letters_or_words" if has_text else "none"
    else:
        kind = result.get("kind", "none")
        sample = result.get("sample", "")
        has_text = decide_has_text(kind, sample)

    res = TextCheckResult(
        kind=kind,  # type: ignore[arg-type]
        sample=sample,
        has_text=has_text,
        elapsed_ms=elapsed_ms,
    )

    # 4. Cache verdict
    try:
        text_check_cache.mkdir(parents=True, exist_ok=True)
        cache_data = {
            "kind": res.kind,
            "sample": res.sample,
            "has_text": res.has_text,
            "elapsed_ms": res.elapsed_ms,
        }
        cache_file.write_text(
            json.dumps(cache_data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except Exception:
        pass

    return res

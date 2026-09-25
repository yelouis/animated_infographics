"""Input ingestion and normalization for text and audio files."""

import re
from pathlib import Path

from animated_infographics.contracts.models import IngestRecord
from animated_infographics.errors import ValidationFailed

SUPPORTED_AUDIO_EXTENSIONS = frozenset({".mp3", ".wav", ".m4a"})
MAX_BODY_WORDS = 1200


def normalize_text(raw: str) -> str:
    """Normalize text in the exact four-step order specified in design_audio_and_timing.md §1.

    1. Convert CRLF to LF.
    2. Replace curly quotes with straight quotes.
    3. Collapse runs of spaces/tabs to one space.
    4. Strip each line.
    """
    # 1. Convert CRLF to LF
    text = raw.replace("\r\n", "\n").replace("\r", "\n")

    # 2. Replace curly quotes
    text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")

    # 3. Collapse runs of spaces and tabs to one space
    text = re.sub(r"[ \t]+", " ", text)

    # 4. Strip each line
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines)


def ingest(input_path: Path, title_override: str | None) -> IngestRecord:
    """Ingest and validate an input text or audio file."""
    ext = input_path.suffix.lower()

    if ext in SUPPORTED_AUDIO_EXTENSIONS:
        return IngestRecord(
            schema_version=1,
            kind="audio",
            source=f"input/{input_path.name}",
            title=title_override,
            paragraphs=None,
            word_count=None,
        )

    if ext != ".txt":
        raise ValidationFailed(f"unsupported input type: {ext}")

    raw_text = input_path.read_text(encoding="utf-8")
    normalized = normalize_text(raw_text)
    lines = normalized.split("\n")

    # Detect title in text: line 1 non-empty and line 2 empty
    if len(lines) >= 2 and lines[0] != "" and lines[1] == "":
        detected_title: str | None = lines[0]
        body_lines = lines[2:]
    else:
        detected_title = None
        body_lines = lines

    title = title_override if title_override is not None else detected_title

    body_str = "\n".join(body_lines).strip()
    if not body_str:
        raise ValidationFailed("empty body after normalisation")

    raw_paragraphs = re.split(r"\n\s*\n+", body_str)
    paragraphs = [p.strip() for p in raw_paragraphs if p.strip()]
    if not paragraphs:
        raise ValidationFailed("empty body after normalisation")

    body_words = [w for p in paragraphs for w in p.split()]
    word_count = len(body_words)

    if word_count > MAX_BODY_WORDS:
        raise ValidationFailed("input too long for MVP (max 1200 words)")

    return IngestRecord(
        schema_version=1,
        kind="text",
        source=f"input/{input_path.name}",
        title=title,
        paragraphs=paragraphs,
        word_count=word_count,
    )

"""Unit tests for input ingest and text normalization."""

from pathlib import Path

import pytest

from animated_infographics.errors import ValidationFailed
from animated_infographics.ingest import ingest, normalize_text


def test_normalize_text_rules() -> None:
    """Verify four-step normalization order."""
    raw = "Line 1\r\n“Curly double” and ‘curly single’\t\twith   spaces.  \r\n  Line 3  "
    norm = normalize_text(raw)
    assert "\r" not in norm
    assert '"Curly double"' in norm
    assert "'curly single'" in norm
    assert "\t" not in norm
    assert "   " not in norm
    assert norm.split("\n")[0] == "Line 1"
    assert norm.split("\n")[-1] == "Line 3"


def test_ingest_text_with_title(tmp_path: Path) -> None:
    """Title on line 1 followed by blank line on line 2."""
    doc = tmp_path / "story.txt"
    doc.write_text("My Great Title\n\nFirst paragraph here.\n\nSecond paragraph.", encoding="utf-8")

    record = ingest(doc, title_override=None)
    assert record.kind == "text"
    assert record.title == "My Great Title"
    assert record.paragraphs == ["First paragraph here.", "Second paragraph."]
    assert record.word_count == 5


def test_ingest_text_without_title(tmp_path: Path) -> None:
    """Line 2 not blank -> whole file is body with no title."""
    doc = tmp_path / "story.txt"
    doc.write_text("First line.\nSecond line.\n\nSecond paragraph.", encoding="utf-8")

    record = ingest(doc, title_override=None)
    assert record.kind == "text"
    assert record.title is None
    assert record.paragraphs == ["First line.\nSecond line.", "Second paragraph."]
    assert record.word_count == 6


def test_ingest_text_title_override(tmp_path: Path) -> None:
    """--title overrides title text."""
    doc = tmp_path / "story.txt"
    doc.write_text("Old Title\n\nFirst paragraph.", encoding="utf-8")

    record = ingest(doc, title_override="New Custom Title")
    assert record.title == "New Custom Title"
    assert record.paragraphs == ["First paragraph."]


def test_ingest_audio_file(tmp_path: Path) -> None:
    """Audio files return kind 'audio' with title_override."""
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"RIFFdummy")

    record = ingest(audio, title_override="Audio Title")
    assert record.kind == "audio"
    assert record.source == "input/sample.wav"
    assert record.title == "Audio Title"
    assert record.paragraphs is None
    assert record.word_count is None


def test_ingest_unsupported_extension(tmp_path: Path) -> None:
    """Unsupported extension raises ValidationFailed."""
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"dummy")

    with pytest.raises(ValidationFailed, match="unsupported input type: .pdf"):
        ingest(pdf, title_override=None)


def test_ingest_empty_body(tmp_path: Path) -> None:
    """Empty body after normalization raises ValidationFailed."""
    doc = tmp_path / "empty.txt"
    doc.write_text("Title\n\n   \n\n", encoding="utf-8")

    with pytest.raises(ValidationFailed, match="empty body after normalisation"):
        ingest(doc, title_override=None)


def test_ingest_too_long(tmp_path: Path) -> None:
    """Body longer than 1200 words raises ValidationFailed."""
    doc = tmp_path / "long.txt"
    words = " ".join(["word"] * 1201)
    doc.write_text(f"Title\n\n{words}", encoding="utf-8")

    with pytest.raises(ValidationFailed, match="max 1200 words"):
        ingest(doc, title_override=None)

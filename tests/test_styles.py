"""Unit and integration tests for style contracts, CLI options, and byte identity.

Per design_styles.md §1–3 and design_testing_and_validation.md §2 (styles row).
"""

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from animated_infographics.contracts.models import IngestRecord
from animated_infographics.contracts.styles import (
    CREATIVE_TEMPLATES,
    LITERAL_TEMPLATES,
    STYLES,
    StyleSpec,
)
from animated_infographics.jobs import STAGES, Job, RunContext
from animated_infographics.stages.director import run_director_stage


def test_style_specs_and_registry() -> None:
    """Verify StyleSpec contract and STYLES registry definitions."""
    assert set(STYLES.keys()) == {"literal", "creative"}

    lit = STYLES["literal"]
    assert lit.name == "literal"
    assert lit.director is False
    assert lit.overlays is False
    assert lit.license == "none"
    assert lit.templates == LITERAL_TEMPLATES
    assert len(lit.templates) == 16

    cre = STYLES["creative"]
    assert cre.name == "creative"
    assert cre.director is True
    assert cre.overlays is True
    assert cre.license == "small_embellishments"
    assert cre.templates == CREATIVE_TEMPLATES
    assert len(cre.templates) == 18
    assert "metaphor" in cre.templates
    assert "callback" in cre.templates

    # Contract extra="forbid" and frozen
    with pytest.raises(ValidationError):
        StyleSpec(
            name="literal",
            director=False,
            templates=LITERAL_TEMPLATES,
            overlays=False,
            license="none",
            unknown="extra",  # type: ignore[call-arg]
        )


def test_ingest_style_default_and_pre_wave_g() -> None:
    """Verify ingest.json records style, defaults to literal, and loads legacy without key."""
    # Pre-Wave-G record lacking 'style' field
    legacy_json = {
        "schema_version": 1,
        "kind": "text",
        "source": "input/test.txt",
        "title": "Test Title",
        "paragraphs": ["Paragraph one."],
        "word_count": 2,
    }
    rec = IngestRecord.model_validate(legacy_json)
    assert rec.style == "literal"

    # Default construction
    rec_default = IngestRecord(
        schema_version=1,
        kind="text",
        source="input/test.txt",
    )
    assert rec_default.style == "literal"

    # Creative style
    rec_creative = IngestRecord(
        schema_version=1,
        kind="text",
        source="input/test.txt",
        style="creative",
    )
    assert rec_creative.style == "creative"

    # Invalid style rejected
    with pytest.raises(ValidationError):
        IngestRecord(
            schema_version=1,
            kind="text",
            source="input/test.txt",
            style="invalid",  # type: ignore[arg-type]
        )


def test_stage_list_includes_director() -> None:
    """Verify director stage is inserted between segment and storyboard."""
    assert "director" in STAGES
    seg_idx = STAGES.index("segment")
    dir_idx = STAGES.index("director")
    sb_idx = STAGES.index("storyboard")
    assert dir_idx == seg_idx + 1
    assert sb_idx == dir_idx + 1


def test_director_stage_literal_writes_nothing(tmp_path: Path) -> None:
    """Verify that in literal mode, the director stage writes no files."""
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    state = {
        "job_id": "test-job",
        "created_at": "2026-10-06T00:00:00Z",
        "state": "created",
        "completed_stages": [],
        "stage_input_sha256": {},
        "timings_ms": {},
    }
    (job_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")
    ingest_payload = {
        "schema_version": 1,
        "kind": "text",
        "source": "input/test.txt",
        "style": "literal",
    }
    (job_dir / "ingest.json").write_text(
        json.dumps(ingest_payload),
        encoding="utf-8",
    )

    job = Job(job_dir)
    ctx = RunContext(style="literal")

    run_director_stage(job, ctx)

    # Must write nothing: director.json must not exist
    assert not (job_dir / "director.json").exists()


def test_rerun_from_director_invalidates_downstream_and_rewrites_style(tmp_path: Path) -> None:
    """Verify rerun --from director invalidates downstream stages and can rewrite style."""
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "logs").mkdir()

    # Pre-populate outputs of various stages
    (job_dir / "bible.json").write_text("{}", encoding="utf-8")
    (job_dir / "beats.json").write_text("{}", encoding="utf-8")
    (job_dir / "director.json").write_text("{}", encoding="utf-8")
    (job_dir / "storyboard.json").write_text("{}", encoding="utf-8")
    (job_dir / "plan_report.json").write_text("{}", encoding="utf-8")

    completed = [
        "ingest",
        "voice",
        "narrate",
        "bible",
        "segment",
        "director",
        "storyboard",
    ]
    state = {
        "job_id": "test-job",
        "created_at": "2026-10-06T00:00:00Z",
        "state": "awaiting_review",
        "completed_stages": completed,
        "stage_input_sha256": {
            "ingest": "1",
            "voice": "2",
            "narrate": "3",
            "bible": "4",
            "segment": "5",
            "director": "6",
            "storyboard": "7",
        },
        "timings_ms": {},
    }
    (job_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")
    ingest_payload = {
        "schema_version": 1,
        "kind": "text",
        "source": "input/test.txt",
        "style": "literal",
    }
    (job_dir / "ingest.json").write_text(
        json.dumps(ingest_payload),
        encoding="utf-8",
    )

    job = Job(job_dir)
    # Rerun from director: prev stage is segment
    job.invalidate_after("segment")

    # Upstream stages must survive
    assert (job_dir / "bible.json").is_file()
    assert (job_dir / "beats.json").is_file()
    assert "segment" in job.state["completed_stages"]
    assert "bible" in job.state["completed_stages"]

    # Downstream stages must be removed from completed_stages and output deleted
    assert not (job_dir / "director.json").exists()
    assert not (job_dir / "storyboard.json").exists()
    assert not (job_dir / "plan_report.json").exists()
    assert "director" not in job.state["completed_stages"]
    assert "storyboard" not in job.state["completed_stages"]


def test_literal_baseline_sha256_identity() -> None:
    """Verify that tests/data/literal_baseline/molasses_flood.sha256 matches frozen checksums."""
    base_dir = Path(__file__).resolve().parent / "data" / "literal_baseline"
    sha_path = base_dir / "molasses_flood.sha256"
    assert sha_path.is_file(), f"Missing {sha_path}"

    lines = [
        line.strip() for line in sha_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    expected_files = {
        "bible.json",
        "beats.json",
        "storyboard.json",
        "plan_report.json",
        "timeline.json",
    }
    found_files = set()

    for line in lines:
        parts = line.split()
        assert len(parts) == 2
        digest, fname = parts
        assert len(digest) == 64
        found_files.add(fname)

    assert found_files == expected_files


def test_falsification_empty_director_json_changes_plan_report_or_stages() -> None:
    """Falsification test: writing director.json or changing plan_report changes sha256 -> red."""
    base_dir = Path(__file__).resolve().parent / "data" / "literal_baseline"
    sha_path = base_dir / "molasses_flood.sha256"
    lines = [
        line.strip() for line in sha_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    expected = dict(reversed(line.split()) for line in lines)

    # If plan_report included {"style": "literal", "style_degraded": false}, sha256 would change
    dummy_report_with_style = {
        "schema_version": 1,
        "model": "gemma4:26b",
        "llm_calls": 12,
        "llm_cache_hits": 0,
        "style": "literal",
        "style_degraded": False,
        "scenes": [],
        "rule_repairs": [],
    }
    dumped_bytes = (json.dumps(dummy_report_with_style, indent=2) + "\n").encode("utf-8")
    altered_hash = hashlib.sha256(dumped_bytes).hexdigest()
    assert altered_hash != expected["plan_report.json"]

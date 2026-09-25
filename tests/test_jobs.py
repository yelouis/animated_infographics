"""Unit tests for Job store, directory layout, invalidation, and runner."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from animated_infographics.errors import ValidationFailed
from animated_infographics.jobs import Job, RunContext


def test_job_create_and_open(tmp_path: Path) -> None:
    """Verify Job.create sets up directories and state.json; Job.open resolves path and id."""
    jobs_dir = tmp_path / "jobs"
    input_file = tmp_path / "molasses_flood.txt"
    input_file.write_text("The great molasses flood happened in Boston in 1919.", encoding="utf-8")

    fixed_now = datetime(2026, 9, 24, 20, 15, 0, tzinfo=UTC)
    job = Job.create(input_file, jobs_dir, fixed_now)

    expected_id = "molasses-flood-20260924-201500"
    assert job.job_id == expected_id
    assert job.dir == jobs_dir / expected_id

    # Check directory structure
    assert (job.dir / "input").is_dir()
    assert (job.dir / "audio" / "sfx").is_dir()
    assert (job.dir / "assets" / "images").is_dir()
    assert (job.dir / "preview").is_dir()
    assert (job.dir / "out").is_dir()
    assert (job.dir / "logs").is_dir()

    # Check state.json content
    assert job.state["schema_version"] == 1
    assert job.state["job_id"] == expected_id
    assert job.state["state"] == "planning"
    assert job.state["completed_stages"] == []
    assert job.state["stage_input_sha256"] == {}
    assert job.state["plan_sha256"] is None
    assert job.state["preview_plan_sha256"] is None
    assert job.state["timeline_plan_sha256"] is None
    assert job.state["approval"] is None
    assert job.state["timings_ms"] == {}
    assert job.state["failed_stage"] is None

    # Open by path
    job_from_path = Job.open(str(job.dir), jobs_dir)
    assert job_from_path.job_id == expected_id

    # Open by job_id
    job_from_id = Job.open(expected_id, jobs_dir)
    assert job_from_id.job_id == expected_id

    # Open non-existent
    with pytest.raises(ValidationFailed, match="Job not found"):
        Job.open("non-existent-id", jobs_dir)


def test_plan_sha256(tmp_path: Path) -> None:
    """Verify plan_sha256 computes sha256(bible + '\\n' + storyboard)."""
    jobs_dir = tmp_path / "jobs"
    input_file = tmp_path / "input.txt"
    input_file.write_text("test input", encoding="utf-8")

    job = Job.create(input_file, jobs_dir, datetime.now(UTC))

    # Missing files return empty string
    assert job.plan_sha256() == ""

    # Create dummy bible.json and storyboard.json
    bible_bytes = b'{"title":"test"}'
    sb_bytes = b'{"scenes":[]}'
    (job.dir / "bible.json").write_bytes(bible_bytes)
    (job.dir / "storyboard.json").write_bytes(sb_bytes)

    import hashlib

    expected_sha = hashlib.sha256(bible_bytes + b"\n" + sb_bytes).hexdigest()
    assert job.plan_sha256() == expected_sha


def test_invalidation_after(tmp_path: Path) -> None:
    """Verify re-running segment deletes storyboard.json, timeline.json, and preview/."""
    jobs_dir = tmp_path / "jobs"
    input_file = tmp_path / "input.txt"
    input_file.write_text("test input", encoding="utf-8")

    job = Job.create(input_file, jobs_dir, datetime.now(UTC))

    # Populate downstream files
    sb_file = job.dir / "storyboard.json"
    sb_file.write_text("{}", encoding="utf-8")
    tl_file = job.dir / "timeline.json"
    tl_file.write_text("{}", encoding="utf-8")
    preview_file = job.dir / "preview" / "contact_sheet.png"
    preview_file.write_text("fake png", encoding="utf-8")
    out_file = job.dir / "out" / "final.mp4"
    out_file.write_text("fake mp4", encoding="utf-8")

    job.state["completed_stages"] = [
        "ingest",
        "voice",
        "narrate",
        "bible",
        "segment",
        "storyboard",
        "assets",
        "compile",
        "preview",
        "render",
    ]
    job.state["stage_input_sha256"] = {
        "storyboard": "123",
        "assets": "234",
        "compile": "345",
        "preview": "456",
        "render": "567",
    }
    job.state["plan_sha256"] = "abc"
    job.state["preview_plan_sha256"] = "abc"
    job.state["timeline_plan_sha256"] = "abc"
    job.state["approval"] = {"plan_sha256": "abc"}
    job.save_state()

    # Invalidate after segment
    job.invalidate_after("segment")

    # Downstream files deleted
    assert not sb_file.exists()
    assert not tl_file.exists()
    assert not preview_file.exists()
    assert not out_file.exists()
    assert (job.dir / "preview").is_dir()
    assert (job.dir / "out").is_dir()

    # Completed stages updated
    assert job.state["completed_stages"] == [
        "ingest",
        "voice",
        "narrate",
        "bible",
        "segment",
    ]
    assert "storyboard" not in job.state["stage_input_sha256"]
    assert "compile" not in job.state["stage_input_sha256"]

    # Plan and approval hashes cleared because storyboard was invalidated
    assert job.state["plan_sha256"] is None
    assert job.state["preview_plan_sha256"] is None
    assert job.state["timeline_plan_sha256"] is None
    assert job.state["approval"] is None


def test_job_run_skip_and_failure(tmp_path: Path) -> None:
    """Verify Job.run skips unchanged stages and handles failures correctly."""
    jobs_dir = tmp_path / "jobs"
    input_file = tmp_path / "input.txt"
    input_file.write_text("test input", encoding="utf-8")

    job = Job.create(input_file, jobs_dir, datetime.now(UTC))

    call_count = {"ingest": 0, "voice": 0}

    def fake_ingest(j: Job, ctx: RunContext) -> None:
        call_count["ingest"] += 1
        (j.dir / "ingest.json").write_text("{}", encoding="utf-8")

    def fake_voice(j: Job, ctx: RunContext) -> None:
        call_count["voice"] += 1
        (j.dir / "voice.json").write_text("{}", encoding="utf-8")

    registry = {"ingest": fake_ingest, "voice": fake_voice}
    ctx = RunContext()

    # First run
    job.run(["ingest", "voice"], registry, ctx)
    assert call_count["ingest"] == 1
    assert call_count["voice"] == 1
    assert job.state["completed_stages"] == ["ingest", "voice"]
    assert "ingest" in job.state["timings_ms"]
    assert "voice" in job.state["timings_ms"]

    # Second run without changes -> should skip both
    job.run(["ingest", "voice"], registry, ctx)
    assert call_count["ingest"] == 1
    assert call_count["voice"] == 1

    # Stage failure
    def failing_stage(j: Job, ctx: RunContext) -> None:
        raise ValueError("Stage blew up")

    registry["narrate"] = failing_stage

    with pytest.raises(ValueError, match="Stage blew up"):
        job.run(["narrate"], registry, ctx)

    assert job.state["state"] == "failed"
    assert job.state["failed_stage"] == "narrate"
    log_file = job.dir / "logs" / "narrate.log"
    assert log_file.is_file()
    assert "ValueError: Stage blew up" in log_file.read_text(encoding="utf-8")

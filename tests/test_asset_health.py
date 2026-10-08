"""Unit and integration tests for asset execution health (Item I6).

Per agent_execution_guide.md §3.I6 and design_testing_and_validation.md §4 & §5:
- a unit case: a manifest with one `lettering detected in 3 attempts` entry -> 0
- one with `mflux exited with code 1` -> 1
- a missing manifest -> an error
- the current G12 jobs, which have one lettering failure, -> 0
- recorded presentation jobs -> 5, 7, 5, 5
- assets.log format: asset <id> failed: <first line>, summary has execution_errors=<n>
"""

from __future__ import annotations

import json
from pathlib import Path

from animated_infographics.evals.asset_health import execution_errors


def test_asset_health_lettering_failure_ignored(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    assets_dir = job_dir / "assets"
    assets_dir.mkdir(parents=True)
    manifest = {
        "schema_version": 1,
        "entities": [
            {
                "id": "v3",
                "status": "failed",
                "error": "lettering detected in 3 attempts",
                "attempts": [],
            }
        ],
    }
    (assets_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    errs = execution_errors(job_dir)
    assert len(errs) == 0


def test_asset_health_mflux_exit_failure(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    assets_dir = job_dir / "assets"
    assets_dir.mkdir(parents=True)
    manifest = {
        "schema_version": 1,
        "entities": [
            {
                "id": "p1",
                "status": "failed",
                "error": "mflux exited with code 1: Traceback (most recent call last):\n ...",
                "attempts": [],
            }
        ],
    }
    (assets_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    errs = execution_errors(job_dir)
    assert len(errs) == 1
    assert errs[0]["id"] == "p1"
    assert "mflux exited with code 1" in errs[0]["error"]


def test_asset_health_missing_manifest_is_error(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    assets_dir = job_dir / "assets"
    assets_dir.mkdir(parents=True)
    # assets directory exists, but manifest.json is missing

    errs = execution_errors(job_dir)
    assert len(errs) == 1
    assert errs[0]["id"] == "__manifest__"
    assert "Missing assets/manifest.json" in errs[0]["error"]


def test_asset_health_g12_jobs() -> None:
    # G12 E2E jobs have at least one lettering failure in molasses-flood, but 0 execution errors
    g12_jobs_dir = Path("artifacts/e2e/20261006_210906/jobs")
    if not g12_jobs_dir.is_dir():
        return

    job_dirs = [
        g12_jobs_dir / "molasses-flood-20261007-040909",
        g12_jobs_dir / "audio_run" / "molasses-flood-say-20261007-041158",
        g12_jobs_dir / "recipe_run" / "story-recipe-box-20261007-041301",
        g12_jobs_dir / "emu_run" / "emu-war-20261007-041951",
    ]

    for j in job_dirs:
        if j.is_dir():
            errs = execution_errors(j)
            assert len(errs) == 0, f"Expected 0 execution errors in {j.name}, got {errs}"


def test_asset_health_four_recorded_presentation_jobs() -> None:
    expected_counts = {
        "jobs/history-great-stink-20261006-124512": 5,
        "jobs/history-great-stink-20261006-132526": 7,
        "jobs/story-overdue-book-20261006-134157": 5,
        "jobs/story-overdue-book-20261006-124735": 5,
    }

    for job_path_str, expected in expected_counts.items():
        job_path = Path(job_path_str)
        if job_path.is_dir():
            errs = execution_errors(job_path)
            assert len(errs) == expected, (
                f"Expected {expected} errors in {job_path_str}, got {len(errs)}"
            )

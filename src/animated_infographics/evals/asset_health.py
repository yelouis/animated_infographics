"""Asset health evaluation for execution error detection.

Per design_testing_and_validation.md §4 step 10 & §5, and agent_execution_guide.md §3.I6:
Detect manifest entries with status == "failed" whose error does not start with
"lettering detected". A job that ran the assets stage but has no assets/manifest.json
is itself an error (fail closed).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _ran_assets_stage(job_dir: Path) -> bool:
    """Determine whether a job has run (or was expected to have run) the assets stage."""
    manifest_path = job_dir / "assets" / "manifest.json"
    if manifest_path.is_file():
        return True
    if (job_dir / "assets").is_dir():
        return True
    if (job_dir / "logs" / "assets.log").is_file():
        return True

    state_path = job_dir / "state.json"
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            completed = state.get("completed_stages", [])
            failed = state.get("failed_stage")
            if "assets" in completed or failed == "assets":
                return True
            later_stages = {
                "perform",
                "speak",
                "hear",
                "follow",
                "compose",
                "compile",
                "preview",
                "render",
            }
            if any(s in completed for s in later_stages):
                return True
            # Job explicitly recorded stages and stopped before assets
            return False
        except Exception:
            return True

    if (job_dir / "out" / "final.mp4").is_file():
        return True

    return False


def execution_errors(job_dir: Path | str) -> list[dict[str, Any]]:
    """Return manifest entries with status == 'failed' without 'lettering detected'.

    A job that ran the assets stage but has no assets/manifest.json is itself
    an error (fail closed).
    """
    job_path = Path(job_dir)
    manifest_path = job_path / "assets" / "manifest.json"

    if not manifest_path.is_file():
        if _ran_assets_stage(job_path):
            return [
                {
                    "id": "__manifest__",
                    "status": "failed",
                    "error": f"Missing assets/manifest.json in job {job_path}",
                }
            ]
        return []

    try:
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [
            {
                "id": "__manifest__",
                "status": "failed",
                "error": f"Unreadable assets/manifest.json in job {job_path}: {exc}",
            }
        ]

    entities = manifest_data.get("entities", [])
    errors: list[dict[str, Any]] = []
    for ent in entities:
        if not isinstance(ent, dict):
            continue
        if ent.get("status") == "failed":
            err = ent.get("error") or ""
            if not err.startswith("lettering detected"):
                errors.append(ent)
    return errors

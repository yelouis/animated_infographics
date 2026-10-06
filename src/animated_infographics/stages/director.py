"""Director stage runner for Animated Infographics pipeline."""

from __future__ import annotations

import json

from animated_infographics.jobs import Job, RunContext


def run_director_stage(job: Job, ctx: RunContext) -> None:
    """Execute director stage.

    For literal: recorded as skipped and writes nothing.
    For creative: will be implemented in G3.
    """
    ingest_path = job.dir / "ingest.json"
    style = ctx.style
    if ingest_path.is_file():
        try:
            data = json.loads(ingest_path.read_text(encoding="utf-8"))
            style = data.get("style", style)
        except Exception:
            pass

    if style == "literal":
        # Literal mode skips director and writes nothing
        return

    raise NotImplementedError("Creative director stage will be implemented in G3")

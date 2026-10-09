"""Presentation follow stage: simulates live presentation following via streaming matcher.

Consumes heard.json and tree.json only (isolation invariant).
Produces playback.json and logs/follow.log.
Per design_presentation_simulation.md §6 and design_data_contracts.md §10.
"""

from __future__ import annotations

import time

from animated_infographics.contracts.anticipation import AnticipationPlan
from animated_infographics.contracts.models import Transcript
from animated_infographics.contracts.playback import PlaybackPlan
from animated_infographics.contracts.tree import TreePlan
from animated_infographics.errors import ValidationFailed
from animated_infographics.jobs import Job, RunContext
from animated_infographics.planner.llm import OllamaBackend
from animated_infographics.presentation.match import AnticipateMatcher, LiveMatcher


def run_follow_stage(job: Job, ctx: RunContext) -> None:
    """Execute follow stage matching heard speech to tree nodes."""
    t0 = time.perf_counter()

    tree_path = job.dir / "tree.json"
    heard_path = job.dir / "heard.json"

    if not tree_path.is_file():
        raise FileNotFoundError(f"tree.json missing in job {job.job_id}")
    if not heard_path.is_file():
        raise FileNotFoundError(f"heard.json missing in job {job.job_id}")

    matcher_name = ctx.matcher or "bm25"
    if matcher_name not in {"bm25", "anticipate", "llm"}:
        raise ValidationFailed(
            f"matcher must be one of bm25, anticipate, llm; got '{matcher_name}'"
        )
    if matcher_name == "llm":
        raise ValidationFailed(f"matcher '{matcher_name}' is not built yet")

    tree = TreePlan.model_validate_json(tree_path.read_text(encoding="utf-8"))
    heard = Transcript.model_validate_json(heard_path.read_text(encoding="utf-8"))
    tiebreak = ctx.tiebreak or "none"

    playback: PlaybackPlan
    if matcher_name == "anticipate":
        anticipation_path = job.dir / "anticipation.json"
        if not anticipation_path.is_file():
            raise ValidationFailed("anticipation.json missing — run the anticipate stage")
        ant_plan = AnticipationPlan.model_validate_json(
            anticipation_path.read_text(encoding="utf-8")
        )
        ant_matcher = AnticipateMatcher(tree=tree, anticipations=ant_plan.nodes)
        playback = ant_matcher.run(heard.words)
    else:
        backend = OllamaBackend(no_cache=ctx.no_llm_cache) if tiebreak == "llm" else None

        live_matcher = LiveMatcher(tree=tree, tiebreak=tiebreak, backend=backend)
        playback = live_matcher.run(heard.words)

    playback_path = job.dir / "playback.json"
    playback_path.write_text(playback.model_dump_json(indent=2) + "\n", encoding="utf-8")

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    log_file = job.dir / "logs" / "follow.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(
            f"Follow: commits={len(playback.commits)}, holds={len(playback.holds)}, "
            f"tiebreak={tiebreak}, matcher={matcher_name}, elapsed_ms={elapsed_ms}\n"
        )

"""Job store, directory layout, and stage state machine."""

import hashlib
import json
import re
import shutil
import time
import traceback
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from animated_infographics.errors import ValidationFailed

STAGES = (
    "ingest",
    "voice",
    "narrate",
    "transcribe",
    "bible",
    "segment",
    "storyboard",
    "assets",
    "compile",
    "preview",
)

ALL_STAGES = (*STAGES, "render")

STAGE_OUTPUT_MAP: dict[str, list[str]] = {
    "ingest": ["ingest.json", "input"],
    "voice": ["voice.json"],
    "narrate": ["narration.json", "audio/narration.wav", "transcript.json"],
    "transcribe": ["transcript.json"],
    "bible": ["bible.json"],
    "segment": ["beats.json"],
    "storyboard": ["storyboard.json", "plan_report.json"],
    "assets": ["assets/images", "assets/manifest.json"],
    "compile": ["timeline.json", "audio/music.wav", "audio/sfx"],
    "preview": ["preview"],
    "render": ["out"],
}

STAGE_INPUT_DEPENDENCIES: dict[str, list[str]] = {
    "ingest": ["input"],
    "voice": ["ingest.json"],
    "narrate": ["ingest.json", "voice.json"],
    "transcribe": ["input"],
    "bible": ["transcript.json", "voice.json"],
    "segment": ["transcript.json", "bible.json"],
    "storyboard": ["beats.json", "bible.json"],
    "assets": ["storyboard.json", "bible.json"],
    "compile": ["storyboard.json", "bible.json", "beats.json"],
    "preview": ["timeline.json"],
    "render": ["timeline.json"],
}


@dataclass(frozen=True)
class RunContext:
    """Execution context for stage functions."""

    title: str | None = None
    voice: str | None = None
    music_path: Path | None = None
    sfx_dir: Path | None = None
    no_llm_cache: bool = False
    preview_video: bool = False
    sync_probe: bool = False
    now: datetime = field(default_factory=lambda: datetime.now(UTC))


StageFn = Callable[["Job", RunContext], None]


class Job:
    """Encapsulates a job directory, state.json, and execution lifecycle."""

    def __init__(self, dir_path: Path) -> None:
        self.dir = dir_path.resolve()
        self.state_file = self.dir / "state.json"
        self.state: dict[str, Any] = self._load_state()

    def _load_state(self) -> dict[str, Any]:
        if not self.state_file.is_file():
            raise ValidationFailed(f"state.json not found in {self.dir}")
        with open(self.state_file, encoding="utf-8") as f:
            data = json.load(f)
            return dict(data)

    def save_state(self) -> None:
        """Write self.state to state.json deterministically."""
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, sort_keys=True)
            f.write("\n")

    @property
    def job_id(self) -> str:
        return str(self.state["job_id"])

    @classmethod
    def create(cls, input_path: Path, jobs_dir: Path, now: datetime) -> "Job":
        """Create a new job directory and initialize state.json."""
        stem = input_path.stem.lower()
        slug = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")[:40]
        if not slug:
            slug = "job"
        job_id = f"{slug}-{now.strftime('%Y%m%d-%H%M%S')}"
        job_dir = jobs_dir.resolve() / job_id

        job_dir.mkdir(parents=True, exist_ok=True)
        (job_dir / "input").mkdir(exist_ok=True)
        (job_dir / "audio").mkdir(exist_ok=True)
        (job_dir / "audio" / "sfx").mkdir(exist_ok=True)
        (job_dir / "assets").mkdir(exist_ok=True)
        (job_dir / "assets" / "images").mkdir(exist_ok=True)
        (job_dir / "preview").mkdir(exist_ok=True)
        (job_dir / "out").mkdir(exist_ok=True)
        (job_dir / "logs").mkdir(exist_ok=True)

        initial_state: dict[str, Any] = {
            "schema_version": 1,
            "job_id": job_id,
            "state": "planning",
            "completed_stages": [],
            "stage_input_sha256": {},
            "plan_sha256": None,
            "preview_plan_sha256": None,
            "timeline_plan_sha256": None,
            "approval": None,
            "timings_ms": {},
            "failed_stage": None,
        }

        with open(job_dir / "state.json", "w", encoding="utf-8") as f:
            json.dump(initial_state, f, indent=2, sort_keys=True)
            f.write("\n")

        return cls(job_dir)

    @classmethod
    def open(cls, ref: str, jobs_dir: Path) -> "Job":
        """Open an existing job by directory path or job_id."""
        candidate = Path(ref)
        if candidate.is_dir():
            job_dir = candidate.resolve()
        else:
            job_dir = (jobs_dir / ref).resolve()

        if not (job_dir / "state.json").is_file():
            raise ValidationFailed(f"Job not found: {ref}")

        return cls(job_dir)

    def plan_sha256(self) -> str:
        """Compute sha256(bytes(bible.json) + b'\\n' + bytes(storyboard.json))."""
        bible_path = self.dir / "bible.json"
        sb_path = self.dir / "storyboard.json"
        if not bible_path.is_file() or not sb_path.is_file():
            return ""
        return hashlib.sha256(bible_path.read_bytes() + b"\n" + sb_path.read_bytes()).hexdigest()

    def _compute_stage_input_sha(self, stage: str) -> str:
        """Compute hash of input dependencies for stage skip logic."""
        deps = STAGE_INPUT_DEPENDENCIES.get(stage, [])
        hasher = hashlib.sha256()
        hasher.update(stage.encode("utf-8"))

        for dep_rel in deps:
            p = self.dir / dep_rel
            if p.is_file():
                hasher.update(dep_rel.encode("utf-8"))
                hasher.update(p.read_bytes())
            elif p.is_dir():
                hasher.update(dep_rel.encode("utf-8"))
                for child in sorted(p.rglob("*")):
                    if child.is_file():
                        hasher.update(child.relative_to(self.dir).as_posix().encode("utf-8"))
                        hasher.update(child.read_bytes())

        return hasher.hexdigest()

    def invalidate_after(self, stage: str) -> None:
        """Delete outputs of every later stage and remove from completed_stages."""
        try:
            stage_idx = ALL_STAGES.index(stage)  # type: ignore[arg-type]
        except ValueError:
            return

        later_stages = ALL_STAGES[stage_idx + 1 :]
        completed = list(self.state.get("completed_stages", []))
        input_shas = dict(self.state.get("stage_input_sha256", {}))

        invalidated_any_plan = False
        for later in later_stages:
            if later in completed:
                completed.remove(later)
            if later in input_shas:
                del input_shas[later]

            if later in {"bible", "storyboard"}:
                invalidated_any_plan = True

            # Delete outputs
            outputs = STAGE_OUTPUT_MAP.get(later, [])
            for out_rel in outputs:
                p = self.dir / out_rel
                if p.is_file():
                    p.unlink()
                elif p.is_dir():
                    shutil.rmtree(p)
                    p.mkdir(exist_ok=True)

        if invalidated_any_plan:
            self.state["plan_sha256"] = None
            self.state["preview_plan_sha256"] = None
            self.state["timeline_plan_sha256"] = None
            self.state["approval"] = None

        self.state["completed_stages"] = completed
        self.state["stage_input_sha256"] = input_shas
        self.save_state()

    def run(
        self,
        stages: Sequence[str],
        registry: Mapping[str, StageFn],
        ctx: RunContext,
    ) -> None:
        """Run stages sequentially, supporting skip logic and invalidation."""
        for stage in stages:
            if stage not in registry:
                raise NotImplementedError(f"stage not implemented: {stage}")

            stage_fn = registry[stage]
            current_input_sha = self._compute_stage_input_sha(stage)
            recorded_input_sha = self.state.get("stage_input_sha256", {}).get(stage)

            # Skip logic: if already completed with identical inputs
            if (
                stage in self.state.get("completed_stages", [])
                and recorded_input_sha == current_input_sha
            ):
                continue

            # Invalidate downstream
            self.invalidate_after(stage)

            start_time = time.time()
            try:
                stage_fn(self, ctx)
            except Exception as exc:
                self.state["failed_stage"] = stage
                self.state["state"] = "failed"
                self.save_state()

                # Write traceback to logs/<stage>.log
                log_file = self.dir / "logs" / f"{stage}.log"
                with open(log_file, "w", encoding="utf-8") as f:
                    traceback.print_exc(file=f)

                raise exc

            elapsed_ms = int((time.time() - start_time) * 1000)
            self.state.setdefault("timings_ms", {})[stage] = elapsed_ms

            completed = self.state.get("completed_stages", [])
            if stage not in completed:
                completed.append(stage)
            self.state["completed_stages"] = completed

            input_shas = self.state.get("stage_input_sha256", {})
            input_shas[stage] = current_input_sha
            self.state["stage_input_sha256"] = input_shas

            self.save_state()

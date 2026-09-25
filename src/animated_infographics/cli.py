"""CLI entry point for Animated Infographics."""

import json
import os
import shutil
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

# Runtime environment settings
os.environ["HF_HUB_OFFLINE"] = "1"

from animated_infographics.contracts.models import Beats, Bible, Storyboard, Transcript
from animated_infographics.doctor import run_doctor
from animated_infographics.errors import (
    DependencyMissing,
    GateRefused,
    ValidationFailed,
)
from animated_infographics.jobs import (
    ALL_STAGES,
    STAGES,
    Job,
    RunContext,
    StageFn,
)
from animated_infographics.planner.validate import PlanContext, validate_plan
from animated_infographics.stages.assets import run_assets_stage
from animated_infographics.stages.bible import run_bible_stage
from animated_infographics.stages.compile import run_compile_stage
from animated_infographics.stages.ingest import run_ingest_stage
from animated_infographics.stages.narrate import run_narrate_stage
from animated_infographics.stages.preview import run_preview_stage
from animated_infographics.stages.segment import run_segment_stage
from animated_infographics.stages.storyboard import run_storyboard_stage
from animated_infographics.stages.transcribe import run_transcribe_stage
from animated_infographics.stages.voice import run_voice_stage

app = typer.Typer(no_args_is_help=True, help="Animated Infographics CLI")


# ---------------------------------------------------------------------------
# Stage Registry and Execution
# ---------------------------------------------------------------------------


def _unimplemented_stage(stage_name: str) -> StageFn:
    def _fn(job: Job, ctx: RunContext) -> None:
        raise NotImplementedError(f"stage not implemented: {stage_name}")

    return _fn


STAGE_REGISTRY: dict[str, StageFn] = {stage: _unimplemented_stage(stage) for stage in ALL_STAGES}
STAGE_REGISTRY["ingest"] = run_ingest_stage
STAGE_REGISTRY["voice"] = run_voice_stage
STAGE_REGISTRY["narrate"] = run_narrate_stage
STAGE_REGISTRY["transcribe"] = run_transcribe_stage
STAGE_REGISTRY["bible"] = run_bible_stage
STAGE_REGISTRY["segment"] = run_segment_stage
STAGE_REGISTRY["storyboard"] = run_storyboard_stage
STAGE_REGISTRY["assets"] = run_assets_stage
STAGE_REGISTRY["compile"] = run_compile_stage
STAGE_REGISTRY["preview"] = run_preview_stage


def set_stage_registry(custom: Mapping[str, StageFn]) -> None:
    """Override stage functions, used primarily in tests."""
    global STAGE_REGISTRY
    STAGE_REGISTRY = dict(custom)


@contextmanager
def handle_errors() -> Iterator[None]:
    """Map domain exceptions to specific CLI exit codes."""
    try:
        yield
    except ValidationFailed as e:
        print(f"Error (validation): {e}", file=sys.stderr)
        sys.exit(2)
    except GateRefused as e:
        print(f"Error (gate refused): {e}", file=sys.stderr)
        sys.exit(3)
    except DependencyMissing as e:
        print(f"Error (dependency missing): {e}", file=sys.stderr)
        sys.exit(4)
    except SystemExit:
        raise
    except NotImplementedError as e:
        print(f"Error (not implemented): {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------------------------


@app.callback()
def main() -> None:
    """Animated Infographics command-line tool."""


@app.command("doctor")
def doctor() -> None:
    """Run environment, model, tool, and asset checks."""
    code = run_doctor()
    if code != 0:
        sys.exit(code)


@app.command("new")
def new(
    input_path: Annotated[Path, typer.Argument(help="Path to input text or audio file")],
    title: Annotated[str | None, typer.Option(help="Optional title")] = None,
    voice: Annotated[
        str | None, typer.Option(help="Voice override: af_heart or am_michael")
    ] = None,
    music: Annotated[Path | None, typer.Option(help="Optional background music WAV")] = None,
    sfx_dir: Annotated[Path | None, typer.Option(help="Optional SFX directory")] = None,
    jobs_dir: Annotated[Path, typer.Option(help="Jobs directory")] = Path("./jobs"),
    no_llm_cache: Annotated[bool, typer.Option(help="Bypass LLM response cache")] = False,
    preview_video: Annotated[bool, typer.Option(help="Render preview MP4")] = False,
) -> None:
    """Create and run a new infographic job through preview."""
    with handle_errors():
        # Pre-validation BEFORE creating job directory
        if not input_path.is_file():
            raise ValidationFailed(f"Input file not found: {input_path}")

        suffix = input_path.suffix.lower()
        is_text = suffix == ".txt"
        is_audio = suffix in {".wav", ".m4a", ".mp3"}

        if not is_text and not is_audio:
            raise ValidationFailed(
                f"Unsupported input type '{suffix}'. Must be .txt, .wav, .m4a, or .mp3"
            )

        if is_audio and voice is not None:
            raise ValidationFailed("--voice cannot be used with audio input")

        if is_text and voice is not None and voice not in {"af_heart", "am_michael"}:
            raise ValidationFailed(f"voice must be one of af_heart, am_michael; got '{voice}'")

        if music is not None and not music.is_file():
            raise ValidationFailed(f"Music file not found: {music}")

        if sfx_dir is not None and not sfx_dir.is_dir():
            raise ValidationFailed(f"SFX directory not found: {sfx_dir}")

        now = datetime.now(UTC)
        job = Job.create(input_path, jobs_dir, now)

        # Copy inputs into job/input/
        dest_input = job.dir / "input" / input_path.name
        shutil.copy2(input_path, dest_input)

        if music is not None:
            shutil.copy2(music, job.dir / "input" / music.name)

        if sfx_dir is not None:
            dest_sfx = job.dir / "input" / "sfx"
            if dest_sfx.exists():
                shutil.rmtree(dest_sfx)
            shutil.copytree(sfx_dir, dest_sfx)

        ctx = RunContext(
            title=title,
            voice=voice,
            music_path=music,
            sfx_dir=sfx_dir,
            no_llm_cache=no_llm_cache,
            preview_video=preview_video,
            now=now,
        )

        stages = (
            [
                "ingest",
                "voice",
                "narrate",
                "bible",
                "segment",
                "storyboard",
                "assets",
                "compile",
                "preview",
            ]
            if is_text
            else [
                "ingest",
                "transcribe",
                "bible",
                "segment",
                "storyboard",
                "assets",
                "compile",
                "preview",
            ]
        )

        job.run(stages, STAGE_REGISTRY, ctx)

        plan_sha = job.plan_sha256()
        job.state["plan_sha256"] = plan_sha
        job.state["preview_plan_sha256"] = plan_sha
        job.state["timeline_plan_sha256"] = plan_sha
        job.state["state"] = "awaiting_review"
        job.save_state()

        print(f"preview/contact_sheet.png: {job.dir / 'preview' / 'contact_sheet.png'}")
        print(f"preview/storyboard.md: {job.dir / 'preview' / 'storyboard.md'}")
        print(f"bible.json: {job.dir / 'bible.json'}")
        print(f"storyboard.json: {job.dir / 'storyboard.json'}")


@app.command("preview")
def preview(
    job_ref: Annotated[str, typer.Argument(help="Job ID or job directory path")],
    jobs_dir: Annotated[Path, typer.Option(help="Jobs directory")] = Path("./jobs"),
    preview_video: Annotated[bool, typer.Option(help="Render preview MP4")] = False,
) -> None:
    """Re-validate plan, recompile timeline, and regenerate preview."""
    with handle_errors():
        job = Job.open(job_ref, jobs_dir)

        if job.state.get("state") not in {"awaiting_review", "approved", "rendered"}:
            raise GateRefused(f"job state '{job.state.get('state')}' cannot run preview")

        # Validate human-edited plan files
        bible_path = job.dir / "bible.json"
        sb_path = job.dir / "storyboard.json"

        if not bible_path.is_file():
            raise ValidationFailed(f"bible.json missing in job {job.job_id}")
        if not sb_path.is_file():
            raise ValidationFailed(f"storyboard.json missing in job {job.job_id}")

        try:
            bible = Bible.model_validate_json(bible_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise ValidationFailed(f"bible.json validation failed: {e}") from e

        try:
            storyboard = Storyboard.model_validate_json(sb_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise ValidationFailed(f"storyboard.json validation failed: {e}") from e

        # Validate storyboard plan against transcript and bible
        transcript_path = job.dir / "transcript.json"
        beats_path = job.dir / "beats.json"
        if transcript_path.is_file() and beats_path.is_file():
            try:
                transcript = Transcript.model_validate_json(
                    transcript_path.read_text(encoding="utf-8")
                )
                beats = Beats.model_validate_json(beats_path.read_text(encoding="utf-8")).beats
                plan_ctx = PlanContext(transcript=transcript, bible=bible, beats=beats)
                val_errors = validate_plan(bible, storyboard, plan_ctx)
                if val_errors:
                    err_msg = "storyboard validation failed:\n" + "\n".join(
                        f"- {e}" for e in val_errors
                    )
                    raise ValidationFailed(err_msg)
            except ValidationFailed:
                raise
            except Exception as e:
                raise ValidationFailed(f"transcript or beats validation failed: {e}") from e

        # Invalidate approval
        job.state["approval"] = None

        # Re-run assets, compile and preview
        job.invalidate_after("storyboard")
        ctx = RunContext(preview_video=preview_video)
        job.run(["assets", "compile", "preview"], STAGE_REGISTRY, ctx)

        plan_sha = job.plan_sha256()
        job.state["plan_sha256"] = plan_sha
        job.state["preview_plan_sha256"] = plan_sha
        job.state["timeline_plan_sha256"] = plan_sha
        job.state["state"] = "awaiting_review"
        job.save_state()

        print(f"preview/contact_sheet.png: {job.dir / 'preview' / 'contact_sheet.png'}")
        print(f"preview/storyboard.md: {job.dir / 'preview' / 'storyboard.md'}")


@app.command("approve")
def approve(
    job_ref: Annotated[str, typer.Argument(help="Job ID or job directory path")],
    jobs_dir: Annotated[Path, typer.Option(help="Jobs directory")] = Path("./jobs"),
) -> None:
    """Approve a job plan for final rendering."""
    with handle_errors():
        job = Job.open(job_ref, jobs_dir)

        if job.state.get("state") != "awaiting_review":
            st = job.state.get("state")
            raise GateRefused(f"Cannot approve job in state '{st}' (expected 'awaiting_review')")

        # Refuse approval if preview/report.json has text overflows
        report_path = job.dir / "preview" / "report.json"
        if report_path.is_file():
            try:
                rep_data = json.loads(report_path.read_text(encoding="utf-8"))
                overflow_entries = rep_data.get("overflow", [])
                if overflow_entries:
                    overflow_ids = sorted(
                        set(
                            e.get("scene_id", "unknown")
                            for e in overflow_entries
                            if isinstance(e, dict)
                        )
                    )
                    ids_str = ", ".join(overflow_ids)
                    msg = (
                        f"text overflows in {ids_str} — "
                        "shorten it in storyboard.json and run preview"
                    )
                    raise GateRefused(msg)
            except GateRefused:
                raise
            except Exception:
                pass

        current_plan = job.plan_sha256()
        if not current_plan:
            raise GateRefused("No valid plan found to approve")

        if job.state.get("preview_plan_sha256") != current_plan:
            raise GateRefused("plan changed since preview — run: infographics preview <job>")

        job.state["approval"] = {
            "plan_sha256": current_plan,
            "approved_at": datetime.now(UTC).isoformat(),
        }
        job.state["state"] = "approved"
        job.save_state()
        print(f"Approved job {job.job_id}")


@app.command("render")
def render(
    job_ref: Annotated[str, typer.Argument(help="Job ID or job directory path")],
    jobs_dir: Annotated[Path, typer.Option(help="Jobs directory")] = Path("./jobs"),
) -> None:
    """Render the approved job video to out/final.mp4."""
    with handle_errors():
        job = Job.open(job_ref, jobs_dir)

        if job.state.get("state") != "approved":
            raise GateRefused(
                f"Cannot render job in state '{job.state.get('state')}' (expected 'approved')"
            )

        approval = job.state.get("approval")
        if not approval or not isinstance(approval, dict):
            raise GateRefused("Job is not approved")

        current_plan = job.plan_sha256()
        if approval.get("plan_sha256") != current_plan:
            raise GateRefused("plan changed since approval — run: infographics preview <job>")

        if job.state.get("timeline_plan_sha256") != current_plan:
            raise GateRefused(
                "timeline not compiled for current plan — run: infographics preview <job>"
            )

        job.state["state"] = "rendering"
        job.save_state()

        ctx = RunContext()
        job.run(["render"], STAGE_REGISTRY, ctx)

        job.state["state"] = "rendered"
        job.save_state()
        print(f"Rendered job {job.job_id} to {job.dir / 'out' / 'final.mp4'}")


@app.command("status")
def status(
    job_ref: Annotated[str, typer.Argument(help="Job ID or job directory path")],
    jobs_dir: Annotated[Path, typer.Option(help="Jobs directory")] = Path("./jobs"),
) -> None:
    """Print job state, completed stages, timings, and metadata."""
    with handle_errors():
        job = Job.open(job_ref, jobs_dir)
        print(f"Job: {job.job_id}")
        print(f"State: {job.state.get('state')}")
        print(f"Completed stages: {', '.join(job.state.get('completed_stages', []))}")
        print(f"Timings: {job.state.get('timings_ms', {})}")
        print(f"Plan SHA-256: {job.plan_sha256()}")


@app.command("rerun")
def rerun(
    job_ref: Annotated[str, typer.Argument(help="Job ID or job directory path")],
    from_stage: Annotated[str, typer.Option("--from", "-f", help="Stage to rerun from")] = "bible",
    jobs_dir: Annotated[Path, typer.Option(help="Jobs directory")] = Path("./jobs"),
) -> None:
    """Rerun job pipeline from a specified stage through preview."""
    with handle_errors():
        allowed_stages = ("bible", "segment", "storyboard", "assets", "compile")
        if from_stage not in allowed_stages:
            raise ValidationFailed(
                f"Invalid rerun stage '{from_stage}'. Allowed: {', '.join(allowed_stages)}"
            )

        job = Job.open(job_ref, jobs_dir)

        # Invalidate from previous stage
        idx = STAGES.index(from_stage)  # type: ignore[arg-type]
        prev_stage = STAGES[idx - 1]
        job.invalidate_after(prev_stage)

        stages_to_run = list(STAGES[idx:])
        ctx = RunContext()
        job.run(stages_to_run, STAGE_REGISTRY, ctx)

        plan_sha = job.plan_sha256()
        job.state["plan_sha256"] = plan_sha
        job.state["preview_plan_sha256"] = plan_sha
        job.state["timeline_plan_sha256"] = plan_sha
        job.state["state"] = "awaiting_review"
        job.save_state()
        print(f"Rerun completed for job {job.job_id} through preview.")


if __name__ == "__main__":
    app()

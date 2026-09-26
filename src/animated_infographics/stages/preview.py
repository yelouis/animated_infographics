"""Preview stage: renders preview stills, generates contact sheet and storyboard markdown."""

from __future__ import annotations

import json
import time

from animated_infographics.contracts.models import (
    Beats,
    PlanReport,
    Timeline,
    VoiceDecision,
)
from animated_infographics.jobs import Job, RunContext
from animated_infographics.preview import (
    compute_hero_frames,
    generate_contact_sheet,
    generate_preview_report,
    generate_storyboard_markdown,
    render_preview_video,
    render_stills,
)


def run_preview_stage(job: Job, ctx: RunContext) -> None:
    """Render preview stills, assemble contact sheet, write storyboard.md and report.json."""
    t0 = time.perf_counter()

    timeline_path = job.dir / "timeline.json"
    beats_path = job.dir / "beats.json"
    voice_path = job.dir / "voice.json"
    report_path = job.dir / "plan_report.json"

    timeline = Timeline.model_validate_json(timeline_path.read_text(encoding="utf-8"))
    beats = Beats.model_validate_json(beats_path.read_text(encoding="utf-8")).beats

    voice: VoiceDecision | None = None
    if voice_path.is_file():
        voice = VoiceDecision.model_validate_json(voice_path.read_text(encoding="utf-8"))

    plan_report: PlanReport | None = None
    if report_path.is_file():
        plan_report = PlanReport.model_validate_json(report_path.read_text(encoding="utf-8"))

    # 1. Compute hero frames and render stills
    frames = compute_hero_frames(timeline)
    overflow_entries = render_stills(job.dir, frames, scale=0.5)

    # 2. Determine flagged scenes
    overflow_scene_ids = {entry["scene_id"] for entry in overflow_entries if "scene_id" in entry}
    fallback_scene_ids: set[str] = set()
    critic_changed_scene_ids: set[str] = set()
    critic_unavailable_scene_ids: set[str] = set()
    if plan_report:
        fallback_scene_ids = {s.id for s in plan_report.scenes if s.fallback_level == 2}
        for s in plan_report.scenes:
            if hasattr(s, "critic") and s.critic:
                if s.critic.changed:
                    critic_changed_scene_ids.add(s.id)
                elif s.critic.status == "unavailable":
                    critic_unavailable_scene_ids.add(s.id)

    manifest_path = job.dir / "assets" / "manifest.json"
    failed_image_ids: set[str] = set()
    if manifest_path.is_file():
        try:
            m_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            for ent in m_data.get("entities", []):
                if ent.get("status") == "failed":
                    failed_image_ids.add(ent.get("id", ""))
        except Exception:
            pass

    image_failed_scene_ids: set[str] = set()
    if failed_image_ids:
        for sc in timeline.scenes:
            props = sc.props
            pid = getattr(props, "place_id", None) or (
                props.get("place_id") if isinstance(props, dict) else None
            )
            spid = getattr(props, "set_piece_id", None) or (
                props.get("set_piece_id") if isinstance(props, dict) else None
            )
            if (pid and pid in failed_image_ids) or (spid and spid in failed_image_ids):
                image_failed_scene_ids.add(sc.id)

    flags_by_scene: dict[str, list[str]] = {}
    for sc in timeline.scenes:
        flags: list[str] = []
        if sc.id in overflow_scene_ids:
            flags.append("overflow")
        if sc.id in fallback_scene_ids:
            flags.append("fallback")
        if sc.id in image_failed_scene_ids:
            flags.append("image failed")
        if sc.id in critic_changed_scene_ids:
            flags.append("critic changed")
        if sc.id in critic_unavailable_scene_ids:
            flags.append("critic unavailable")
        if flags:
            flags_by_scene[sc.id] = flags

    flagged_scenes = overflow_scene_ids | fallback_scene_ids | image_failed_scene_ids

    # 3. Generate contact sheet
    generate_contact_sheet(job.dir, timeline, flagged_scenes)

    # 4. Generate storyboard markdown
    generate_storyboard_markdown(job.dir, timeline, beats, voice, flags_by_scene)

    # 5. Generate report.json
    plan_sha = job.plan_sha256()
    generate_preview_report(job.dir, plan_report, overflow_entries, plan_sha)

    # 6. Optional preview video
    if ctx.preview_video:
        render_preview_video(job.dir)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    log_file = job.dir / "logs" / "preview.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text(f"llm_calls=0 cache_hits=0 elapsed_ms={elapsed_ms}\n", encoding="utf-8")

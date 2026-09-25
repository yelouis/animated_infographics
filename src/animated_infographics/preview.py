"""Preview generation: stills rendering, contact sheet creation, and storyboard markdown."""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from animated_infographics.contracts.models import (
    Beat,
    PlanReport,
    Timeline,
    VoiceDecision,
)

ENTER_FRAMES: int = 12


def format_voice_line(voice: VoiceDecision | None) -> str:
    """Format the review gate voice line header according to design_planner.md §10."""
    if voice is None:
        return "Voice: (recorded audio)"

    if voice.source == "flag":
        return f"Voice: {voice.voice} — set by --voice"

    if voice.reason == "third_person":
        return f"Voice: {voice.voice} — auto (third person)"

    if voice.reason == "no_evidence":
        return f"Voice: {voice.voice} — auto (first person, no self-identification found)"

    if voice.reason in ("llm", "tag"):
        ev_str = f': "{voice.evidence}"' if voice.evidence else ""
        return (
            f"Voice: {voice.voice} — auto (first person, {voice.narrator_gender} narrator{ev_str})"
        )

    return f"Voice: {voice.voice} — auto ({voice.reason})"


def compute_hero_frames(timeline: Timeline) -> list[dict[str, Any]]:
    """Compute hero frame per scene per design_rendering.md §7:

    start_frame + min(
        sceneFrames - 1,
        max(round(0.6 * sceneFrames), max(item_frames, default=0) + ENTER_FRAMES)
    )
    """
    frames: list[dict[str, Any]] = []
    for sc in timeline.scenes:
        scene_frames = sc.end_frame - sc.start_frame
        max_item = max(sc.timing.item_frames) if sc.timing.item_frames else 0
        hero_offset = min(
            scene_frames - 1,
            max(round(0.6 * scene_frames), max_item + ENTER_FRAMES),
        )
        hero_frame = sc.start_frame + hero_offset
        frames.append(
            {
                "scene_id": sc.id,
                "frame": hero_frame,
                "out": f"preview/scene_{sc.id}.png",
            }
        )
    return frames


def render_stills(
    job_dir: Path,
    frames: list[dict[str, Any]],
    scale: float = 0.5,
) -> list[dict[str, Any]]:
    """Invoke Remotion render.ts stills to produce preview PNGs and capture overflow."""
    preview_dir = job_dir / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    frames_path = preview_dir / "frames.json"
    frames_path.write_text(json.dumps(frames, indent=2), encoding="utf-8")

    repo_root = Path(__file__).resolve().parents[2]
    renderer_dir = repo_root / "renderer"
    render_script = renderer_dir / "scripts" / "render.ts"

    cmd = [
        "npx",
        "tsx",
        str(render_script),
        "stills",
        "--job",
        str(job_dir),
        "--frames",
        str(frames_path),
        "--scale",
        str(scale),
    ]

    subprocess.run(cmd, cwd=renderer_dir, check=True)

    overflow_path = job_dir / "logs" / "overflow.json"
    if overflow_path.is_file():
        try:
            return json.loads(overflow_path.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def render_preview_video(job_dir: Path) -> Path:
    """Invoke Remotion render.ts media to produce preview/preview.mp4 at half scale."""
    preview_dir = job_dir / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = preview_dir / "preview.mp4"

    repo_root = Path(__file__).resolve().parents[2]
    renderer_dir = repo_root / "renderer"
    render_script = renderer_dir / "scripts" / "render.ts"

    cmd = [
        "npx",
        "tsx",
        str(render_script),
        "media",
        "--job",
        str(job_dir),
        "--out",
        str(out_mp4),
        "--scale",
        "0.5",
        "--crf",
        "28",
    ]

    subprocess.run(cmd, cwd=renderer_dir, check=True)
    return out_mp4


def format_key_props(scene: Any) -> str:
    """Format key props for readable storyboard table."""
    props = scene.props
    t = scene.template
    if t == "title_card":
        sub = f" / {props.subtitle}" if getattr(props, "subtitle", None) else ""
        return f"{props.title}{sub}"
    if t == "kinetic_quote":
        return f'"{props.text}"'
    if t == "stat_callout":
        sc = f" {props.display_scale}" if props.display_scale != "none" else ""
        suf = f" {props.suffix}" if props.suffix else ""
        pre = props.prefix or ""
        return f"{pre}{props.value}{sc}{suf}"
    if t == "icon_list":
        return ", ".join(i.label for i in props.items)
    if t == "reveal":
        return f"{props.kicker}: {props.text}"
    if t == "cause_effect":
        return " -> ".join(n.label for n in props.nodes)
    if t == "comparison":
        return f"{props.a.heading} vs {props.b.heading}"
    if t == "character_intro":
        return f"cast={props.cast_id} ({props.descriptor})"
    if t == "dialogue":
        return f"{len(props.lines)} lines"
    if t == "text_thread":
        return f"{props.contact_name}: {len(props.messages)} msgs"
    if t == "emotion_beat":
        return f"cast={props.cast_id} ({props.emotion})"
    if t == "relationship_map":
        return f"{len(props.cast_ids)} nodes, {len(props.edges)} edges"
    if t == "location":
        return f"place={props.place_id}"
    if t == "set_piece":
        return f"set_piece={props.set_piece_id}"
    if t == "map_focus":
        return f"region={props.region}, {len(props.markers)} markers"
    if t == "timeline":
        return f"{len(props.events)} events"
    return ""


def generate_contact_sheet(
    job_dir: Path,
    timeline: Timeline,
    flagged_scenes: set[str],
) -> Path:
    """Generate 5-column contact sheet using Pillow per design_rendering.md §7.

    Each tile is 270x480 image + 44px label strip.
    Label strip is danger (#FF6B8B) for flagged scenes, else bgRaised (#1F2F52).
    """
    preview_dir = job_dir / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    out_path = preview_dir / "contact_sheet.png"

    n_scenes = len(timeline.scenes)
    cols = 5
    rows = max(1, math.ceil(n_scenes / cols))

    tile_w = 270
    img_h = 480
    label_h = 44
    tile_h = img_h + label_h

    canvas_w = cols * tile_w
    canvas_h = rows * tile_h

    bg_color = (20, 33, 61)  # #14213D
    raised_color = (31, 47, 82)  # #1F2F52
    danger_color = (255, 107, 139)  # #FF6B8B
    ink_color = (248, 244, 233)  # #F8F4E9

    sheet = Image.new("RGB", (canvas_w, canvas_h), color=bg_color)
    draw = ImageDraw.Draw(sheet)

    # Attempt to load bundled font, fallback to default
    repo_root = Path(__file__).resolve().parents[2]
    font_path = repo_root / "renderer" / "public" / "fonts" / "Inter-SemiBold.ttf"
    font: Any
    try:
        font = ImageFont.truetype(str(font_path), size=18)
    except Exception:
        font = ImageFont.load_default()

    for idx, sc in enumerate(timeline.scenes):
        r = idx // cols
        c = idx % cols
        x = c * tile_w
        y = r * tile_h

        still_path = preview_dir / f"scene_{sc.id}.png"
        if still_path.is_file():
            try:
                with Image.open(still_path) as im:
                    resized = im.convert("RGB").resize((tile_w, img_h), Image.Resampling.LANCZOS)
                    sheet.paste(resized, (x, y))
            except Exception:
                draw.rectangle([x, y, x + tile_w, y + img_h], fill=(11, 19, 38))
        else:
            # Placeholder tile
            draw.rectangle([x, y, x + tile_w, y + img_h], fill=(11, 19, 38))

        # Label strip
        is_flagged = sc.id in flagged_scenes
        strip_color = danger_color if is_flagged else raised_color
        strip_top = y + img_h
        draw.rectangle([x, strip_top, x + tile_w, strip_top + label_h], fill=strip_color)

        sec = sc.start_frame / 30.0
        m = int(sec // 60)
        s = int(sec % 60)
        t = int((sec * 10) % 10)
        time_str = f"{m}:{s:02d}.{t}"
        label_text = f"{sc.id} · {sc.template} · {time_str}"

        # Draw text centered vertically with 10px left margin
        draw.text((x + 10, strip_top + 12), label_text, fill=ink_color, font=font)

    sheet.save(out_path, format="PNG")
    return out_path


def generate_storyboard_markdown(
    job_dir: Path,
    timeline: Timeline,
    beats: list[Beat],
    voice: VoiceDecision | None,
    flags_by_scene: dict[str, list[str]],
) -> Path:
    """Generate preview/storyboard.md per design_rendering.md §7."""
    preview_dir = job_dir / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    out_path = preview_dir / "storyboard.md"

    lines = [
        format_voice_line(voice),
        "",
        "| scene | time | template | beat text | key props | flags |",
        "|---|---|---|---|---|---|",
    ]

    for idx, sc in enumerate(timeline.scenes):
        sec = sc.start_frame / 30.0
        m = int(sec // 60)
        s = int(sec % 60)
        t = int((sec * 10) % 10)
        time_str = f"{m}:{s:02d}.{t}"

        beat_text = beats[idx].text if idx < len(beats) else ""
        safe_beat = " ".join(beat_text.replace("|", "/").split())
        props_str = " ".join(format_key_props(sc).replace("|", "/").split())
        flags = flags_by_scene.get(sc.id, [])
        flags_str = ", ".join(flags) if flags else "-"

        row = (
            f"| `{sc.id}` | `{time_str}` | `{sc.template}` | "
            f"{safe_beat} | {props_str} | {flags_str} |"
        )
        lines.append(row)

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def generate_preview_report(
    job_dir: Path,
    plan_report: PlanReport | None,
    overflow_entries: list[dict[str, Any]],
    plan_sha: str,
) -> dict[str, Any]:
    """Generate preview/report.json per design_rendering.md §7."""
    preview_dir = job_dir / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    out_path = preview_dir / "report.json"

    fallback_scenes: list[str] = []
    if plan_report:
        fallback_scenes = [s.id for s in plan_report.scenes if s.fallback_level == 2]

    failed_images: list[str] = []

    report_data = {
        "overflow": overflow_entries,
        "fallback_scenes": fallback_scenes,
        "failed_images": failed_images,
        "plan_sha256": plan_sha,
    }

    out_path.write_text(json.dumps(report_data, indent=2) + "\n", encoding="utf-8")
    return report_data

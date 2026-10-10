"""Preview generation: stills rendering, contact sheet creation, and storyboard markdown."""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from animated_infographics.contracts.deck import DeckPlan
from animated_infographics.contracts.models import (
    Beat,
    PlanReport,
    Timeline,
    VoiceDecision,
)
from animated_infographics.memguard import guard, watch

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

    with guard("render"):
        proc = subprocess.Popen(cmd, cwd=renderer_dir)
        with watch("render", proc):
            ret = proc.wait()
            if ret != 0:
                raise subprocess.CalledProcessError(ret, cmd)

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

    with guard("render"):
        proc = subprocess.Popen(cmd, cwd=renderer_dir)
        with watch("render", proc):
            ret = proc.wait()
            if ret != 0:
                raise subprocess.CalledProcessError(ret, cmd)
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
    if t == "metaphor":
        lbl = f' "{props.label}"' if getattr(props, "label", None) else ""
        return f"metaphor={props.image_entity}{lbl}"
    if t == "callback":
        lbl = f' "{props.label}"' if getattr(props, "label", None) else ""
        return f"callback={props.motif_id}{lbl}"
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

        # Draw "M" / "C" badge for metaphor / callback scenes
        if sc.template in ("metaphor", "callback"):
            badge_letter = "M" if sc.template == "metaphor" else "C"
            bx, by = x + 8, y + 8
            bw, bh = 24, 24
            draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=4, fill=(233, 196, 106))
            bfont: Any
            try:
                bfont = ImageFont.truetype(str(font_path), size=14)
            except Exception:
                bfont = ImageFont.load_default()
            draw.text((bx + 6, by + 3), badge_letter, fill=(20, 33, 61), font=bfont)

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


def generate_deck_contact_sheet(
    job_dir: Path,
    deck: DeckPlan,
    timeline: Timeline | None = None,
    flagged_scenes: set[str] | None = None,
) -> Path:
    """Generate presentation contact sheet displaying slides and points per H1/review gate."""
    preview_dir = job_dir / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    out_path = preview_dir / "contact_sheet.png"

    canvas_w = 1350
    bg_color = (20, 33, 61)  # #14213D
    raised_color = (31, 47, 82)  # #1F2F52
    border_color = (42, 63, 109)
    accent_color = (252, 163, 17)  # #FCA311
    ink_color = (248, 244, 233)  # #F8F4E9
    muted_color = (148, 163, 184)  # #94A3B8
    bullet_color = (96, 165, 250)  # #60A5FA

    repo_root = Path(__file__).resolve().parents[2]
    font_path = repo_root / "renderer" / "public" / "fonts" / "Inter-SemiBold.ttf"
    header_font: Any
    title_font: Any
    body_font: Any
    small_font: Any
    try:
        header_font = ImageFont.truetype(str(font_path), size=26)
        title_font = ImageFont.truetype(str(font_path), size=20)
        body_font = ImageFont.truetype(str(font_path), size=16)
        small_font = ImageFont.truetype(str(font_path), size=14)
    except Exception:
        header_font = ImageFont.load_default()
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Pre-calculate card heights
    card_w = 1270
    card_margin_x = (canvas_w - card_w) // 2
    card_padding = 18
    gap_y = 20

    cards_info: list[dict[str, Any]] = []
    current_y = 100  # Start after header banner

    for slide in deck.slides:
        # Title height + point lines
        lines_count = len(slide.points)
        # title line (30px) + each point (26px) + padding (36px)
        card_h = card_padding * 2 + 30 + lines_count * 28 + 8
        cards_info.append({"slide": slide, "y": current_y, "h": card_h})
        current_y += card_h + gap_y

    canvas_h = max(600, current_y + 20)

    sheet = Image.new("RGB", (canvas_w, canvas_h), color=bg_color)
    draw = ImageDraw.Draw(sheet)

    # 1. Header Banner
    draw.rectangle([0, 0, canvas_w, 80], fill=raised_color)
    draw.text((40, 16), "PRESENTATION SIMULATION DECK", fill=accent_color, font=header_font)
    total_pts = sum(len(s.points) for s in deck.slides)
    sub_text = f"{len(deck.slides)} Slides · {total_pts} Talking Points"
    draw.text((40, 48), sub_text, fill=muted_color, font=small_font)

    # 2. Slide Cards
    for item in cards_info:
        slide = item["slide"]
        cy = item["y"]
        ch = item["h"]

        # Card rectangle
        draw.rectangle(
            [card_margin_x, cy, card_margin_x + card_w, cy + ch],
            fill=raised_color,
            outline=border_color,
            width=2,
        )

        # Slide ID badge & Title
        draw.rectangle(
            [
                card_margin_x + card_padding,
                cy + card_padding,
                card_margin_x + card_padding + 46,
                cy + card_padding + 24,
            ],
            fill=border_color,
        )
        draw.text(
            (card_margin_x + card_padding + 8, cy + card_padding + 3),
            slide.id.upper(),
            fill=accent_color,
            font=small_font,
        )

        draw.text(
            (card_margin_x + card_padding + 58, cy + card_padding + 1),
            slide.title,
            fill=ink_color,
            font=title_font,
        )

        # Sentence scope on right
        sids_text = (
            f"Sentences {slide.sentence_ids[0]}–{slide.sentence_ids[-1]}"
            if slide.sentence_ids
            else ""
        )
        draw.text(
            (card_margin_x + card_w - card_padding - 160, cy + card_padding + 4),
            sids_text,
            fill=muted_color,
            font=small_font,
        )

        # Points
        pt_y = cy + card_padding + 34
        for pt in slide.points:
            # Bullet circle
            draw.ellipse(
                [
                    card_margin_x + card_padding + 12,
                    pt_y + 6,
                    card_margin_x + card_padding + 18,
                    pt_y + 12,
                ],
                fill=bullet_color,
            )
            draw.text(
                (card_margin_x + card_padding + 28, pt_y),
                pt.text,
                fill=ink_color,
                font=body_font,
            )
            pt_sids = f"({', '.join(str(i) for i in pt.sentence_ids)})"
            draw.text(
                (card_margin_x + card_w - card_padding - 140, pt_y + 2),
                pt_sids,
                fill=muted_color,
                font=small_font,
            )
            pt_y += 28

    sheet.save(out_path, format="PNG")
    return out_path


def generate_deck_storyboard_markdown(
    job_dir: Path,
    deck: DeckPlan,
    title: str | None = None,
    voice: VoiceDecision | None = None,
) -> Path:
    """Generate preview/storyboard.md for presentation deck jobs."""
    preview_dir = job_dir / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    out_path = preview_dir / "storyboard.md"

    total_pts = sum(len(s.points) for s in deck.slides)
    lines = [
        f"# Presentation Deck: {title or 'Presentation'}",
        "",
        format_voice_line(voice),
        "",
        f"**Slides:** {len(deck.slides)} | **Talking Points:** {total_pts}",
        "",
        "| slide | title | points | sentences |",
        "|---|---|---|---|",
    ]

    for s in deck.slides:
        pts_str = "<br>".join(f"• {p.text} ({p.sentence_ids})" for p in s.points)
        sids_str = ", ".join(str(i) for i in s.sentence_ids)
        lines.append(f"| `{s.id}` | **{s.title}** | {pts_str} | `{sids_str}` |")

    lines.append("")
    lines.append("## Detailed Slide Plan")
    lines.append("")
    for s in deck.slides:
        lines.append(f"### Slide {s.id}: {s.title} (sentences: {s.sentence_ids})")
        for p_idx, p in enumerate(s.points):
            lines.append(f"- **Point {p_idx + 1}:** {p.text} *(sentences {p.sentence_ids})*")
        lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
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

    director_path = job_dir / "director.json"
    director_lines: list[str] = []
    if director_path.is_file():
        try:
            from animated_infographics.contracts.director import DirectorPlan

            d_plan = DirectorPlan.model_validate_json(director_path.read_text(encoding="utf-8"))
            director_lines.append("## Creative Director Plan")
            director_lines.append("")
            if d_plan.motifs:
                director_lines.append("### Motifs")
                for motif in d_plan.motifs:
                    extra = f", icon: {motif.icon}" if motif.icon else ""
                    if motif.set_piece_id:
                        extra += f", set_piece: {motif.set_piece_id}"
                    director_lines.append(f"- **{motif.name}** (`{motif.id}`{extra}):")
                    for app in motif.appearances:
                        director_lines.append(f"  - beat {app.beat_i}: {app.role}")
                director_lines.append("")
            if d_plan.metaphors:
                director_lines.append("### Metaphors")
                for met in d_plan.metaphors:
                    lbl = f' (label: "{met.label}")' if met.label else ""
                    c_str = f" [cast: {', '.join(met.cast_ids)}]" if met.cast_ids else ""
                    director_lines.append(f'- beat {met.beat_i}: "{met.image}"{lbl}{c_str}')
                director_lines.append("")
            if d_plan.asides:
                director_lines.append("### Asides")
                for a in d_plan.asides:
                    details: list[str] = []
                    if a.cast_id:
                        details.append(f"cast: {a.cast_id}")
                    if a.icon:
                        details.append(f"icon: {a.icon}")
                    if a.text:
                        details.append(f'text: "{a.text}"')
                    det_str = f" ({', '.join(details)})" if details else ""
                    director_lines.append(f"- beat {a.beat_i}: {a.kind}{det_str}")
                director_lines.append("")
            if getattr(d_plan, "director_dropped", None):
                director_lines.append("### Dropped by Director Salvage")
                for dd in d_plan.director_dropped:
                    director_lines.append(f"- `{dd.item}`: {dd.error}")
                director_lines.append("")
        except Exception:
            pass

    lines = [
        *director_lines,
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
    warnings: list[str] = []
    if plan_report and plan_report.style_degraded:
        warnings.append("director stage failed after 3 attempts; degraded to literal")
    elif (job_dir / ".director_degraded").is_file():
        warnings.append("director stage failed after 3 attempts; degraded to literal")

    manifest_path = job_dir / "assets" / "manifest.json"
    if manifest_path.is_file():
        try:
            m_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            for ent in m_data.get("entities", []):
                ent_id = ent.get("id", "")
                if ent.get("status") == "failed":
                    failed_images.append(ent_id)
                if ent.get("text_check") == "unavailable":
                    warnings.append(ent_id)
        except Exception:
            pass

    report_data: dict[str, Any] = {
        "overflow": overflow_entries,
        "fallback_scenes": fallback_scenes,
        "failed_images": failed_images,
        "warnings": warnings,
        "plan_sha256": plan_sha,
    }

    director_items: list[dict[str, Any]] = []
    director_path = job_dir / "director.json"
    if director_path.is_file():
        try:
            from animated_infographics.contracts.director import DirectorPlan

            d_plan = DirectorPlan.model_validate_json(director_path.read_text(encoding="utf-8"))
            timeline_path = job_dir / "timeline.json"
            t_scenes: list[dict[str, Any]] = []
            if timeline_path.is_file():
                try:
                    t_data = json.loads(timeline_path.read_text(encoding="utf-8"))
                    t_scenes = t_data.get("scenes", [])
                except Exception:
                    pass

            # 0. director_dropped
            for dd in getattr(d_plan, "director_dropped", []):
                director_items.append(
                    {
                        "item": dd.item,
                        "fate": "director_dropped",
                        "error": dd.error,
                    }
                )

            # 1. license_dropped
            for ld in d_plan.license_dropped:
                director_items.append(
                    {
                        "kind": ld.item.get("kind", "license_item"),
                        "beat_i": ld.item.get("beat_i"),
                        "fate": "license_dropped",
                        "verdict": ld.verdict,
                    }
                )

            # 2. overlay_dropped
            for od in d_plan.overlay_dropped:
                director_items.append(
                    {
                        "kind": od.item.get("kind", "overlay_item"),
                        "beat_i": od.item.get("beat_i"),
                        "fate": "overlay_dropped",
                        "reason": od.reason,
                    }
                )

            # 3. Metaphors
            for met in d_plan.metaphors:
                sc_match = next(
                    (s for s in t_scenes if s.get("id") == f"s{met.beat_i:03d}"),
                    None,
                )
                fate = (
                    "rendered"
                    if (sc_match and sc_match.get("template") == "metaphor")
                    else "dropped"
                )
                director_items.append(
                    {
                        "kind": "metaphor",
                        "beat_i": met.beat_i,
                        "fate": fate,
                        "label": met.label,
                    }
                )

            # 4. Motifs
            for motif in d_plan.motifs:
                for app in motif.appearances:
                    if app.role == "payoff":
                        sc_match = next(
                            (s for s in t_scenes if s.get("id") == f"s{app.beat_i:03d}"),
                            None,
                        )
                        fate = (
                            "rendered"
                            if (sc_match and sc_match.get("template") == "callback")
                            else "dropped"
                        )
                        director_items.append(
                            {
                                "kind": "callback",
                                "motif_id": motif.id,
                                "beat_i": app.beat_i,
                                "fate": fate,
                            }
                        )
                    elif app.role in ("plant", "echo"):
                        is_dropped = any(
                            od.item.get("motif_id") == motif.id
                            and od.item.get("beat_i") == app.beat_i
                            for od in d_plan.overlay_dropped
                        )
                        if is_dropped:
                            fate = "overlay_dropped"
                        else:
                            orig_sc = next(
                                (s for s in t_scenes if s.get("id") == f"s{app.beat_i:03d}"),
                                None,
                            )
                            has_in_orig = orig_sc and any(
                                o.get("kind") == "motif_token" and o.get("motif_id") == motif.id
                                for o in orig_sc.get("overlays", [])
                            )
                            if has_in_orig:
                                fate = "rendered"
                            else:
                                placed_sc = next(
                                    (
                                        s
                                        for s in t_scenes
                                        if any(
                                            o.get("kind") == "motif_token"
                                            and o.get("motif_id") == motif.id
                                            for o in s.get("overlays", [])
                                        )
                                    ),
                                    None,
                                )
                                fate = "moved" if placed_sc else "overlay_dropped"
                        director_items.append(
                            {
                                "kind": "motif_token",
                                "motif_id": motif.id,
                                "beat_i": app.beat_i,
                                "fate": fate,
                            }
                        )

            # 5. Asides
            for aside in d_plan.asides:
                is_dropped = any(
                    od.item.get("beat_i") == aside.beat_i and od.item.get("kind") == aside.kind
                    for od in d_plan.overlay_dropped
                )
                if is_dropped:
                    fate = "overlay_dropped"
                else:
                    orig_sc = next(
                        (s for s in t_scenes if s.get("id") == f"s{aside.beat_i:03d}"),
                        None,
                    )
                    has_in_orig = orig_sc and any(
                        o.get("kind") == aside.kind for o in orig_sc.get("overlays", [])
                    )
                    if has_in_orig:
                        fate = "rendered"
                    else:
                        placed_sc = next(
                            (
                                s
                                for s in t_scenes
                                if any(o.get("kind") == aside.kind for o in s.get("overlays", []))
                            ),
                            None,
                        )
                        fate = "moved" if placed_sc else "overlay_dropped"
                director_items.append(
                    {
                        "kind": aside.kind,
                        "beat_i": aside.beat_i,
                        "fate": fate,
                        "text": aside.text,
                    }
                )
        except Exception:
            pass

    if director_items:
        report_data["director_items"] = director_items

    perf_path = job_dir / "performance.json"
    if perf_path.is_file():
        try:
            perf_data = json.loads(perf_path.read_text(encoding="utf-8"))
            if "op_counts" in perf_data:
                report_data["op_counts"] = perf_data["op_counts"]
        except Exception:
            pass

    out_path.write_text(json.dumps(report_data, indent=2) + "\n", encoding="utf-8")
    return report_data

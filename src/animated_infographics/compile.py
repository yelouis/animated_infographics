"""Compilation of storyboard, beats, bible, and audio into resolved timeline.json."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final, Literal, Mapping, Sequence

from pydantic import TypeAdapter

from animated_infographics.config import (
    MUSIC_FADE_IN_FRAMES,
    MUSIC_FADE_OUT_FRAMES,
    MUSIC_VOLUME,
    SFX_MIN_GAP_FRAMES,
    SFX_VOLUME,
)
from animated_infographics.contracts.director import DirectorPlan, OverlayDropped
from animated_infographics.contracts.icons import ICON_NAMES
from animated_infographics.contracts.models import (
    Beat,
    Bible,
    SceneOverlay,
    Storyboard,
    Timeline,
    TimelineAudio,
    TimelineCaptions,
    TimelineCastMember,
    TimelineDebug,
    TimelineMusic,
    TimelineNarration,
    TimelinePlace,
    TimelineScene,
    TimelineSceneTiming,
    TimelineSetPiece,
    TimelineSfx,
    Transcript,
)
from animated_infographics.contracts.templates import (
    ALLOWED_OVERLAY_TEMPLATES,
)
from animated_infographics.contracts.templates import (
    REGISTRY as TEMPLATE_REGISTRY,
)
from animated_infographics.planner.validate import normalize_props_text
from animated_infographics.timing.captions import paginate
from animated_infographics.timing.frames import duration_frames, scene_start_frames
from animated_infographics.timing.items import count_frames, item_frames

CAST_COLORS: Final[tuple[str, ...]] = (
    "#F4A261",
    "#2A9D8F",
    "#E76F51",
    "#E9C46A",
    "#8AB17D",
    "#7B7FE0",
    "#F28482",
    "#4CC9F0",
)
_TIMELINE_SCENE_ADAPTER: Final[TypeAdapter[TimelineScene]] = TypeAdapter(TimelineScene)


def _get_item_count(scene: Any) -> int:
    props = scene.props
    template = scene.template
    if template == "icon_list":
        return len(getattr(props, "items", []))
    if template == "cause_effect":
        return len(getattr(props, "nodes", []))
    if template == "comparison":
        return 2
    if template == "dialogue":
        return len(getattr(props, "lines", []))
    if template == "text_thread":
        return len(getattr(props, "messages", []))
    if template == "map_focus":
        return len(getattr(props, "markers", []))
    if template == "timeline":
        return len(getattr(props, "events", []))
    return 0


def callback_item_count(
    idx: int,
    scenes: Sequence[Any],
    scene_overlays: Mapping[int, Sequence[Any]] | None,
) -> int:
    """Return the number of earlier scenes with a motif_token matching the callback's motif_id.

    Per design_templates.md §2.18 and design_styles.md §3.6.
    """
    if idx <= 0 or not scene_overlays:
        return 0
    if idx >= len(scenes):
        return 0
    cb_scene = scenes[idx]
    template = getattr(cb_scene, "template", None) or (
        cb_scene.get("template") if isinstance(cb_scene, dict) else None
    )
    if template != "callback":
        return 0
    props = getattr(cb_scene, "props", None) or (
        cb_scene.get("props") if isinstance(cb_scene, dict) else None
    )
    target_motif_id = (
        getattr(props, "motif_id", None)
        if props is not None and hasattr(props, "motif_id")
        else (props.get("motif_id") if isinstance(props, dict) else None)
    )
    if not target_motif_id:
        return 0

    count = 0
    for earlier_idx in range(idx):
        overlays = scene_overlays.get(earlier_idx, [])
        for ov in overlays:
            kind = getattr(ov, "kind", None) or (ov.get("kind") if isinstance(ov, dict) else None)
            motif_id = getattr(ov, "motif_id", None) or (
                ov.get("motif_id") if isinstance(ov, dict) else None
            )
            if kind == "motif_token" and motif_id == target_motif_id:
                count += 1
                break
    return count


def compute_scene_overlays(
    storyboard: Storyboard,
    director_plan: DirectorPlan,
    bible: Bible | None = None,
) -> tuple[dict[int, list[SceneOverlay]], list[OverlayDropped]]:
    """Compute overlay assignments for each scene per design_styles.md §3.5.

    Rules:
    - Motif token on every plant and echo beat.
    - Aside on its beat.
    - Allowed templates: ALLOWED_OVERLAY_TEMPLATES.
    - If beat is forbidden or occupied:
      - Motif token moves to nearest allowed scene <= 2 beats before payoff.
      - Aside moves to nearest allowed scene <= 1 beat.
      - Otherwise dropped and recorded under overlay_dropped.
    - At most 1 motif token and 1 aside per scene.
    - When two collide, earlier-planned item wins.
    """
    n_scenes = len(storyboard.scenes)
    scene_overlays: dict[int, list[SceneOverlay]] = {i: [] for i in range(n_scenes)}
    token_scenes: set[int] = set()
    aside_scenes: set[int] = set()
    dropped: list[OverlayDropped] = []

    # 1. Place motif tokens (plants and echoes)
    for motif in director_plan.motifs:
        payoff_beat = next(
            (a.beat_i for a in motif.appearances if a.role == "payoff"),
            n_scenes,
        )
        icon_name = motif.icon
        if not icon_name and motif.set_piece_id and bible:
            sp = next((s for s in bible.set_pieces if s.id == motif.set_piece_id), None)
            if sp and sp.icon:
                icon_name = sp.icon
        if not icon_name or icon_name not in ICON_NAMES:
            icon_name = "Sparkle"

        for app in motif.appearances:
            if app.role not in ("plant", "echo"):
                continue

            orig_beat = app.beat_i
            candidates = [
                b
                for b in range(n_scenes)
                if b < payoff_beat
                and abs(b - orig_beat) <= 2
                and storyboard.scenes[b].template in ALLOWED_OVERLAY_TEMPLATES
                and b not in token_scenes
            ]
            candidates.sort(key=lambda b: (abs(b - orig_beat), b))

            if candidates:
                best_beat = candidates[0]
                token_scenes.add(best_beat)
                overlay = SceneOverlay(
                    kind="motif_token",
                    icon=icon_name,  # type: ignore[arg-type]
                    anchor="top_right",
                    motif_id=motif.id,
                )
                scene_overlays[best_beat].append(overlay)
            else:
                dropped.append(
                    OverlayDropped(
                        item={
                            "kind": "motif_token",
                            "motif_id": motif.id,
                            "beat_i": orig_beat,
                            "role": app.role,
                            "icon": icon_name,
                        },
                        reason="no_allowed_scene_within_reach",
                    )
                )

    # 2. Place asides
    for aside in director_plan.asides:
        orig_beat = aside.beat_i
        aside_icon = aside.icon if aside.icon in ICON_NAMES else None
        has_text = bool(aside.text and isinstance(aside.text, str) and aside.text.strip())

        is_incomplete = False
        if aside.kind == "thought":
            is_incomplete = not aside_icon and not has_text
        elif aside.kind == "prop":
            is_incomplete = not aside_icon
        elif aside.kind == "label":
            is_incomplete = not has_text
        else:
            is_incomplete = True

        if is_incomplete:
            dropped.append(
                OverlayDropped(
                    item=aside.model_dump(),
                    reason="incomplete",
                )
            )
            continue

        candidates = [
            b
            for b in range(n_scenes)
            if abs(b - orig_beat) <= 1
            and storyboard.scenes[b].template in ALLOWED_OVERLAY_TEMPLATES
            and b not in aside_scenes
        ]
        candidates.sort(key=lambda b: (abs(b - orig_beat), b))

        if candidates:
            best_beat = candidates[0]
            aside_scenes.add(best_beat)
            anchor: Literal["top_left", "bottom_left"] = (
                "bottom_left" if aside.kind == "prop" else "top_left"
            )
            overlay = SceneOverlay(
                kind=aside.kind,
                icon=aside_icon,  # type: ignore[arg-type]
                text=aside.text,
                anchor=anchor,
            )
            scene_overlays[best_beat].append(overlay)
        else:
            dropped.append(
                OverlayDropped(
                    item=aside.model_dump(),
                    reason="no_allowed_scene_within_reach",
                )
            )

    return scene_overlays, dropped


def compile_timeline(
    transcript: Transcript,
    beats: list[Beat],
    bible: Bible,
    storyboard: Storyboard,
    *,
    plan_sha256: str,
    music_rel_path: str | None = None,
    sfx_files_by_role: dict[str, list[Path]] | None = None,
    sync_probe: bool = False,
    available_images: set[str] | None = None,
    director_plan: DirectorPlan | None = None,
    scene_overlays: dict[int, list[SceneOverlay]] | None = None,
) -> Timeline:
    """Compile storyboard into fully-resolved Timeline object adhering to design contracts."""
    total_frames = duration_frames(transcript)
    n_scenes = len(storyboard.scenes)

    if n_scenes == 0:
        raise ValueError("Cannot compile timeline from empty storyboard")

    starts = scene_start_frames(beats)

    if scene_overlays is None and director_plan is not None:
        scene_overlays, _ = compute_scene_overlays(storyboard, director_plan, bible)

    # 1. Compile timeline scenes
    timeline_scenes: list[TimelineScene] = []
    all_raw_cues: list[tuple[int, str]] = []  # (frame, role)

    for idx, sc in enumerate(storyboard.scenes):
        start_f = starts[idx]
        end_f = starts[idx + 1] if idx < n_scenes - 1 else total_frames
        scene_frames = end_f - start_f

        # Check hide_captions: true iff title_card and every sentence in beat is_title
        beat = beats[idx]
        beat_sentences = [
            s
            for s in transcript.sentences
            if not (s.word_end <= beat.word_start or s.word_start >= beat.word_end)
        ]
        hide_captions = (
            sc.template == "title_card"
            and len(beat_sentences) > 0
            and all(s.is_title for s in beat_sentences)
        )

        spec = TEMPLATE_REGISTRY.get(sc.template)
        spread = spec.spread if spec and spec.spread is not None else 0.0
        if sc.template == "callback":
            n_items = callback_item_count(idx, storyboard.scenes, scene_overlays)
        else:
            n_items = _get_item_count(sc)

        if n_items > 0 and spread > 0.0:
            it_frames = item_frames(n_items, scene_frames, spread)
        else:
            it_frames = []

        if sc.template == "stat_callout":
            cnt_frames: int | None = count_frames(scene_frames)
        else:
            cnt_frames = None

        timing = TimelineSceneTiming(item_frames=it_frames, count_frames=cnt_frames)

        # Normalize free-text fields before writing to timeline
        props_data = sc.props.model_dump() if hasattr(sc.props, "model_dump") else dict(sc.props)
        clean_props_data = normalize_props_text(sc.template, props_data)
        clean_props = (
            spec.props_model.model_validate(clean_props_data) if spec else clean_props_data
        )

        overlays_for_scene = scene_overlays.get(idx, []) if scene_overlays is not None else []

        # Build timeline scene dictionary
        sc_dict = {
            "id": sc.id,
            "template": sc.template,
            "start_frame": start_f,
            "end_frame": end_f,
            "hide_captions": hide_captions,
            "timing": timing,
            "props": clean_props,
            "overlays": overlays_for_scene,
        }
        timeline_scene = _TIMELINE_SCENE_ADAPTER.validate_python(sc_dict)
        timeline_scenes.append(timeline_scene)

        # Collect SFX cues if not muted
        if not sc.mute_sfx and spec and spec.sfx_cues:
            for cue in spec.sfx_cues:
                if cue.at == "start":
                    all_raw_cues.append((start_f, cue.role))
                elif cue.at == "count_end":
                    if cnt_frames is not None:
                        all_raw_cues.append((start_f + cnt_frames, cue.role))
                elif cue.at == "item":
                    for it_f in it_frames:
                        all_raw_cues.append((start_f + it_f, cue.role))

    # 2. Schedule SFX
    # Drop cues whose role has no files
    available_sfx = sfx_files_by_role or {}
    valid_cues = [(f, r) for f, r in all_raw_cues if available_sfx.get(r)]
    valid_cues.sort(key=lambda x: x[0])

    # Min gap filtering (24 frames)
    kept_cues: list[tuple[int, str]] = []
    last_cue_frame: int | None = None
    for f, r in valid_cues:
        if last_cue_frame is None or (f - last_cue_frame) >= SFX_MIN_GAP_FRAMES:
            kept_cues.append((f, r))
            last_cue_frame = f

    # Round-robin file selection
    role_counters: dict[str, int] = {}
    timeline_sfx_list: list[TimelineSfx] = []
    for f, r in kept_cues:
        files = available_sfx[r]
        choice_idx = role_counters.get(r, 0) % len(files)
        role_counters[r] = role_counters.get(r, 0) + 1
        sfx_file = files[choice_idx]
        timeline_sfx_list.append(
            TimelineSfx(
                src=f"job/audio/sfx/{sfx_file.name}",
                frame=f,
                volume=SFX_VOLUME,
            )
        )

    # 3. Audio section
    narration_audio = TimelineNarration(src="job/audio/narration.wav")
    music_audio: TimelineMusic | None = None
    if music_rel_path:
        music_audio = TimelineMusic(
            src=music_rel_path,
            volume=MUSIC_VOLUME,
            fade_in_frames=MUSIC_FADE_IN_FRAMES,
            fade_out_frames=MUSIC_FADE_OUT_FRAMES,
        )

    audio = TimelineAudio(
        narration=narration_audio,
        music=music_audio,
        sfx=timeline_sfx_list,
    )

    # 4. Cast, places, set pieces
    cast_map = {
        c.id: TimelineCastMember(
            name=c.name,
            color=CAST_COLORS[c.color_slot % len(CAST_COLORS)],
            avatar=c.avatar,
        )
        for c in bible.cast
    }
    places_map = {
        p.id: TimelinePlace(
            name=p.name,
            image=f"job/assets/images/{p.id}.png"
            if (available_images and p.id in available_images)
            else None,
            icon=p.icon,
            lat=p.lat,
            lon=p.lon,
            country_iso3=p.country_iso3,
        )
        for p in bible.places
    }
    set_pieces_map = {
        s.id: TimelineSetPiece(
            name=s.name,
            image=f"job/assets/images/{s.id}.png"
            if (available_images and s.id in available_images)
            else None,
            icon=s.icon,
        )
        for s in bible.set_pieces
    }

    # Register metaphor entities in set_pieces_map for metaphor scenes
    for sc in storyboard.scenes:
        if sc.template == "metaphor":
            ent_id = getattr(sc.props, "image_entity", f"metaphor_{sc.beat_i}")
            if ent_id not in set_pieces_map:
                has_img = available_images is not None and ent_id in available_images
                set_pieces_map[ent_id] = TimelineSetPiece(
                    name=getattr(sc.props, "label", None) or f"Metaphor {sc.beat_i}",
                    image=f"job/assets/images/{ent_id}.png" if has_img else None,
                    icon="Sparkle",
                )

    # 5. Captions
    caption_pages = paginate(transcript, to_frames=True)
    captions = TimelineCaptions(pages=caption_pages)

    return Timeline(
        schema_version=1,
        fps=30,
        width=1080,
        height=1920,
        duration_frames=total_frames,
        plan_sha256=plan_sha256,
        debug=TimelineDebug(sync_probe=sync_probe),
        audio=audio,
        cast=cast_map,
        places=places_map,
        set_pieces=set_pieces_map,
        scenes=timeline_scenes,
        captions=captions,
    )

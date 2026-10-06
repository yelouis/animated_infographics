"""Presentation compose stage: builds timeline.json from tree scenes and playback.json.

Per design_presentation_simulation.md §7.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from animated_infographics.audio.mix_prep import prepare_music, prepare_sfx
from animated_infographics.config import (
    ENTER_FRAMES,
    EXIT_FRAMES,
    FPS,
    MUSIC_FADE_IN_FRAMES,
    MUSIC_FADE_OUT_FRAMES,
    MUSIC_VOLUME,
)
from animated_infographics.contracts.models import (
    Bible,
    CaptionPage,
    CaptionWord,
    IngestRecord,
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
from animated_infographics.contracts.playback import PlaybackPlan
from animated_infographics.contracts.templates import REGISTRY
from animated_infographics.contracts.tree import TreePlan
from animated_infographics.errors import ValidationFailed
from animated_infographics.jobs import Job, RunContext
from animated_infographics.planner.validate import normalize_props_text
from animated_infographics.timing.captions import paginate
from animated_infographics.timing.items import count_frames, item_frames

CAST_COLORS: tuple[str, ...] = (
    "#F4A261",
    "#2A9D8F",
    "#E76F51",
    "#E9C46A",
    "#8AB17D",
    "#7B7FE0",
    "#F28482",
    "#4CC9F0",
)
_TIMELINE_SCENE_ADAPTER: TypeAdapter[TimelineScene] = TypeAdapter(TimelineScene)


def round_half_up(x: float) -> int:
    import math

    return math.floor(x + 0.5)


def _get_item_count(scene: Any) -> int:
    props = getattr(scene, "props", None)
    if not props:
        return 0
    props_dict = props.model_dump() if hasattr(props, "model_dump") else dict(props)
    items = props_dict.get("items")
    return len(items) if isinstance(items, list) else 0


def paginate_live_captions(transcript: Transcript) -> TimelineCaptions:
    """Paginate ASR words with 300 ms lag after words end per §7."""
    raw_pages = paginate(transcript, to_frames=False)
    if not raw_pages:
        return TimelineCaptions(pages=[])

    caption_pages: list[CaptionPage] = []
    num_pages = len(raw_pages)

    for i in range(num_pages):
        page = raw_pages[i]
        p_words = page.words
        if not p_words:
            continue

        last_word_end_ms = p_words[-1].end_frame
        page_start_ms = last_word_end_ms + 300

        if i + 1 < num_pages and raw_pages[i + 1].words:
            next_last_end = raw_pages[i + 1].words[-1].end_frame
            next_start_ms = next_last_end + 300
            page_end_ms = next_start_ms
        else:
            page_end_ms = page_start_ms + 2500

        p_start_f = round_half_up(page_start_ms * FPS / 1000.0)
        p_end_f = round_half_up(page_end_ms * FPS / 1000.0)

        orig_first_ms = p_words[0].start_frame
        c_words = [
            CaptionWord(
                text=w.text,
                start_frame=round_half_up(
                    (w.start_frame - orig_first_ms + page_start_ms) * FPS / 1000.0
                ),
                end_frame=round_half_up(
                    (w.end_frame - orig_first_ms + page_start_ms) * FPS / 1000.0
                ),
            )
            for w in p_words
        ]

        caption_pages.append(CaptionPage(start_frame=p_start_f, end_frame=p_end_f, words=c_words))

    return TimelineCaptions(pages=caption_pages)


def compose_presentation_timeline(
    tree: TreePlan,
    playback: PlaybackPlan,
    heard: Transcript,
    bible: Bible | None,
    plan_sha: str = "",
    music_rel_path: str | None = None,
    sfx_files_by_role: dict[str, list[Path]] | None = None,
) -> tuple[Timeline, list[str]]:
    """Compose presentation playback commits and tree scenes into Timeline."""
    node_map = {n.id: n for n in tree.nodes}
    min_frames = ENTER_FRAMES + EXIT_FRAMES  # 20 frames = 667 ms
    merged_scene_notes: list[str] = []

    # Total duration in frames
    total_dur_ms = heard.duration_ms
    total_frames = max(1, round_half_up(total_dur_ms * FPS / 1000.0))

    raw_scenes: list[dict[str, Any]] = []

    for idx, commit in enumerate(playback.commits):
        node = node_map.get(commit.node_id)
        if not node:
            continue
        sc = node.scene

        start_f = raw_scenes[-1]["end_frame"] if raw_scenes else 0
        if idx + 1 < len(playback.commits):
            end_ms = playback.commits[idx + 1].at_ms
            end_f = max(start_f, round_half_up(end_ms * FPS / 1000.0))
        else:
            end_f = total_frames

        # Short scene merging per §7
        if (end_f - start_f < min_frames) and raw_scenes:
            # Merge into previous scene
            prev_sc = raw_scenes[-1]
            prev_sc["end_frame"] = max(prev_sc["end_frame"], end_f)
            merged_scene_notes.append(
                f"Merged short scene {sc.id} ({end_f - start_f} frames) into {prev_sc['id']}"
            )
            continue

        if not raw_scenes and end_f < min_frames:
            end_f = min_frames

        raw_scenes.append(
            {
                "id": f"s{len(raw_scenes):03d}",
                "orig_scene": sc,
                "node_id": node.id,
                "start_frame": start_f,
                "end_frame": end_f,
            }
        )

    # Ensure last scene reaches total frames
    if raw_scenes and raw_scenes[-1]["end_frame"] < total_frames:
        raw_scenes[-1]["end_frame"] = total_frames

    timeline_scenes: list[TimelineScene] = []
    for r_sc in raw_scenes:
        sc = r_sc["orig_scene"]
        s_f = r_sc["start_frame"]
        e_f = r_sc["end_frame"]
        scene_frames = e_f - s_f

        spec = REGISTRY.get(sc.template)
        spread = spec.spread if spec and spec.spread is not None else 0.0
        n_items = _get_item_count(sc)

        if n_items > 0 and spread > 0.0:
            it_frames = item_frames(n_items, scene_frames, spread)
        else:
            it_frames = []

        cnt_frames = count_frames(scene_frames) if sc.template == "stat_callout" else None
        timing = TimelineSceneTiming(item_frames=it_frames, count_frames=cnt_frames)

        props_data = sc.props.model_dump() if hasattr(sc.props, "model_dump") else dict(sc.props)
        clean_props_data = normalize_props_text(sc.template, props_data)
        clean_props = (
            spec.props_model.model_validate(clean_props_data) if spec else clean_props_data
        )

        sc_dict = {
            "id": r_sc["id"],
            "template": sc.template,
            "start_frame": s_f,
            "end_frame": e_f,
            "hide_captions": False,
            "timing": timing,
            "props": clean_props,
            "overlays": [],
        }
        timeline_scene = _TIMELINE_SCENE_ADAPTER.validate_python(sc_dict)
        timeline_scenes.append(timeline_scene)

    # Cast, places, set pieces from bible
    cast_map: dict[str, TimelineCastMember] = {}
    places_map: dict[str, TimelinePlace] = {}
    set_pieces_map: dict[str, TimelineSetPiece] = {}

    if bible:
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
                image=None,
                icon=p.icon,
                lat=p.lat,
                lon=p.lon,
                country_iso3=p.country_iso3,
            )
            for p in bible.places
        }
        set_pieces_map = {
            sp.id: TimelineSetPiece(
                name=sp.name,
                image=None,
                icon=sp.icon,
            )
            for sp in bible.set_pieces
        }

    # Live captions with 300 ms lag
    captions = paginate_live_captions(heard)

    music = (
        TimelineMusic(
            src=music_rel_path,
            volume=MUSIC_VOLUME,
            fade_in_frames=MUSIC_FADE_IN_FRAMES,
            fade_out_frames=MUSIC_FADE_OUT_FRAMES,
        )
        if music_rel_path
        else None
    )
    sfx_list: list[TimelineSfx] = []

    narration_audio = TimelineNarration(src="job/audio/narration.wav")
    audio = TimelineAudio(narration=narration_audio, music=music, sfx=sfx_list)
    debug = TimelineDebug()

    timeline = Timeline(
        schema_version=1,
        duration_frames=total_frames,
        fps=30,
        width=1080,
        height=1920,
        plan_sha256=plan_sha,
        cast=cast_map,
        places=places_map,
        set_pieces=set_pieces_map,
        scenes=timeline_scenes,
        captions=captions,
        audio=audio,
        debug=debug,
    )
    return timeline, merged_scene_notes


def run_compose_stage(job: Job, ctx: RunContext) -> None:
    """Execute presentation compose stage building timeline.json."""
    t0 = time.perf_counter()

    tree_path = job.dir / "tree.json"
    playback_path = job.dir / "playback.json"
    heard_path = job.dir / "heard.json"
    audio_path = job.dir / "audio" / "narration.wav"
    bible_path = job.dir / "deck_bible.json"
    ingest_path = job.dir / "ingest.json"

    if not tree_path.is_file():
        raise FileNotFoundError(f"tree.json missing in job {job.job_id}")
    if not playback_path.is_file():
        raise FileNotFoundError(f"playback.json missing in job {job.job_id}")
    if not heard_path.is_file():
        raise FileNotFoundError(f"heard.json missing in job {job.job_id}")
    if not audio_path.is_file():
        raise FileNotFoundError(f"audio/narration.wav missing in job {job.job_id}")

    tree = TreePlan.model_validate_json(tree_path.read_text(encoding="utf-8"))
    playback = PlaybackPlan.model_validate_json(playback_path.read_text(encoding="utf-8"))
    heard = Transcript.model_validate_json(heard_path.read_text(encoding="utf-8"))

    bible = (
        Bible.model_validate_json(bible_path.read_text(encoding="utf-8"))
        if bible_path.is_file()
        else None
    )
    ingest = (
        IngestRecord.model_validate_json(ingest_path.read_text(encoding="utf-8"))
        if ingest_path.is_file()
        else None
    )

    # Music preparation
    music_rel_path: str | None = None
    music_dst = job.dir / "audio" / "music.wav"
    if ingest and ingest.music:
        music_src = job.dir / ingest.music
        if not music_src.is_file():
            raise ValidationFailed(
                f"{ingest.music} is recorded in ingest.json but missing from the job"
            )
        prepare_music(music_src, music_dst)
        music_rel_path = "job/audio/music.wav"

    # SFX preparation
    sfx_files_by_role: dict[str, list[Path]] = {}
    sfx_dst_dir = job.dir / "audio" / "sfx"
    if ingest and ingest.sfx_dir:
        sfx_src = job.dir / ingest.sfx_dir
        if not sfx_src.is_dir():
            raise ValidationFailed(
                f"{ingest.sfx_dir} is recorded in ingest.json but missing from the job"
            )
        sfx_files_by_role = prepare_sfx(sfx_src, sfx_dst_dir)

    plan_sha = job.plan_sha256()

    timeline, merged_notes = compose_presentation_timeline(
        tree=tree,
        playback=playback,
        heard=heard,
        bible=bible,
        plan_sha=plan_sha,
        music_rel_path=music_rel_path,
        sfx_files_by_role=sfx_files_by_role,
    )

    timeline_path = job.dir / "timeline.json"
    timeline_path.write_text(
        timeline.model_dump_json(indent=2, by_alias=True) + "\n", encoding="utf-8"
    )

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    log_file = job.dir / "logs" / "compose.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(
            f"Compose: scenes={len(timeline.scenes)}, duration_frames={timeline.duration_frames}, "
            f"merged_short_scenes={len(merged_notes)}, elapsed_ms={elapsed_ms}\n"
        )

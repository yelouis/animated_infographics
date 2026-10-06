"""Presentation animation tree stage.

Plans deterministic section nodes with section_title, plans point nodes with
infographic templates and slide context, generates transition edges (next, skip, back),
normalises matching text, and runs assets.

Per design_presentation_simulation.md §3 and design_data_contracts.md §10.
"""

from __future__ import annotations

import time
from pathlib import Path

from animated_infographics.assets.illustrate import run_assets
from animated_infographics.compile import (
    _TIMELINE_SCENE_ADAPTER,
    CAST_COLORS,
    _get_item_count,
)
from animated_infographics.contracts.deck import DeckPlan
from animated_infographics.contracts.models import (
    Beat,
    Bible,
    SectionTitleProps,
    SectionTitleScene,
    Timeline,
    TimelineAudio,
    TimelineCaptions,
    TimelineCastMember,
    TimelineDebug,
    TimelineNarration,
    TimelinePlace,
    TimelineScene,
    TimelineSceneTiming,
    TimelineSetPiece,
    Transcript,
    TranscriptSentence,
    TranscriptWord,
)
from animated_infographics.contracts.templates import REGISTRY
from animated_infographics.contracts.tree import TreeEdge, TreeNode, TreePlan
from animated_infographics.jobs import Job, RunContext
from animated_infographics.planner.critic import needs_critic
from animated_infographics.planner.director import plan_director
from animated_infographics.planner.llm import LLMBackend, OllamaBackend
from animated_infographics.planner.props import (
    _evaluate_scene_critic,
    build_deterministic_kinetic_quote,
    plan_single_template_props,
)
from animated_infographics.planner.select import (
    _build_compact_bible,
    plan_template_selection,
)
from animated_infographics.planner.validate import normalize_props_text
from animated_infographics.presentation.match import (
    extract_scene_free_text,
    normalize_node_text,
)
from animated_infographics.timing.items import count_frames, item_frames


def build_points_transcript(points: list[tuple[str, str, int]]) -> Transcript:
    """Build a synthetic one-beat-per-point transcript for grounding."""
    words: list[TranscriptWord] = []
    sentences: list[TranscriptSentence] = []
    cur_ms = 0
    w_idx = 0

    for s_idx, (_slide_id, text, _p_i) in enumerate(points):
        raw_tokens = text.split()
        if not raw_tokens:
            raw_tokens = [text]

        sent_start_ms = cur_ms
        sent_w_start = w_idx

        for tok in raw_tokens:
            words.append(
                TranscriptWord(
                    i=w_idx,
                    text=tok,
                    start_ms=cur_ms,
                    end_ms=cur_ms + 250,
                    sentence_i=s_idx,
                )
            )
            w_idx += 1
            cur_ms += 300

        sent_end_ms = cur_ms
        sentences.append(
            TranscriptSentence(
                i=s_idx,
                text=text,
                start_ms=sent_start_ms,
                end_ms=sent_end_ms,
                word_start=sent_w_start,
                word_end=w_idx,
                paragraph_i=s_idx,
                is_title=False,
            )
        )

    return Transcript(
        schema_version=1,
        source="tts",
        audio_path="points.wav",
        duration_ms=cur_ms,
        words=words,
        sentences=sentences,
    )


def plan_tree(
    deck: DeckPlan,
    bible: Bible,
    backend: LLMBackend,
    style: str = "literal",
) -> TreePlan:
    """Plan complete presentation animation tree with nodes and edges."""
    all_points: list[tuple[str, str, int, str]] = []  # (slide_id, pt_text, p_idx, slide_title)
    for slide in deck.slides:
        for p_idx, pt in enumerate(slide.points):
            all_points.append((slide.id, pt.text, p_idx, slide.title))

    # 1. Build synthetic points transcript and beats
    points_transcript = build_points_transcript([(s, t, p) for s, t, p, _ in all_points])
    beats = [
        Beat(
            i=k,
            word_start=sent.word_start,
            word_end=sent.word_end,
            start_ms=sent.start_ms,
            end_ms=sent.end_ms,
            text=pt_text,
        )
        for k, ((_, pt_text, _, _), sent) in enumerate(
            zip(all_points, points_transcript.sentences, strict=False)
        )
    ]

    # 2. Director if creative
    director_plan = None
    if style == "creative":
        director_plan, _ = plan_director(beats, bible, backend)

    # 3. Select templates with presentation profile (R2, R6, R7 off)
    choices, _, _, _ = plan_template_selection(
        transcript=points_transcript,
        beats=beats,
        bible=bible,
        backend=backend,
        director_plan=director_plan,
        profile="presentation",
    )

    repo_root = Path(__file__).resolve().parents[3]
    props_prompt_path = (
        repo_root / "src" / "animated_infographics" / "planner" / "prompts" / "props.md"
    )
    props_prompt = props_prompt_path.read_text(encoding="utf-8")
    compact_bible = _build_compact_bible(bible)

    # 4. Build nodes
    nodes: list[TreeNode] = []
    node_to_slide_idx: dict[str, int] = {}
    point_node_ids: list[str] = []

    scene_counter = 0
    pt_cursor = 0

    for s_idx, slide in enumerate(deck.slides):
        # Section node (deterministic)
        sec_id = f"{slide.id}_section"
        sec_scene_id = f"s{scene_counter:03d}"
        scene_counter += 1

        sec_props = SectionTitleProps(
            title=slide.title,
            index=s_idx,
            count=len(deck.slides),
        )
        sec_scene = SectionTitleScene(
            id=sec_scene_id,
            beat_i=pt_cursor,
            template="section_title",
            props=sec_props,
            rationale="deterministic section",
        )
        sec_norm_text = normalize_node_text(slide.title)
        sec_node = TreeNode(
            id=sec_id,
            slide=slide.id,
            kind="section",
            point_i=None,
            text=sec_norm_text,
            scene=sec_scene,
        )
        nodes.append(sec_node)
        node_to_slide_idx[sec_id] = s_idx

        # Point nodes for this slide
        slide_passage = f"{slide.title}. " + " ".join(p.text for p in slide.points)
        slide_context = (
            f"Presentation Slide Context:\nSlide Title: {slide.title}\n"
            f"Points on this slide:\n" + "\n".join(f"- {p.text}" for p in slide.points)
        )

        for p_idx, pt in enumerate(slide.points):
            pt_id = f"{slide.id}_p{p_idx}"
            global_k = pt_cursor
            pt_cursor += 1

            beat = beats[global_k]
            prev_beat = beats[global_k - 1] if global_k > 0 else None
            next_beat = beats[global_k + 1] if global_k + 1 < len(beats) else None

            choice = choices[global_k] if global_k < len(choices) else None
            primary = choice.primary if choice else "kinetic_quote"
            alternate = choice.alternate if choice else "kinetic_quote"

            scene_id_str = f"s{scene_counter:03d}"
            scene_counter += 1

            # Attempt primary
            planned_scene, _, _ = plan_single_template_props(
                primary,
                scene_id_str,
                global_k,
                beat,
                prev_beat,
                next_beat,
                points_transcript,
                bible,
                backend,
                props_prompt,
                compact_bible,
                extra_user_prompt=slide_context,
                max_attempts=3,
            )

            # Fallback to alternate if primary failed
            if planned_scene is None and alternate != primary:
                planned_scene, _, _ = plan_single_template_props(
                    alternate,
                    scene_id_str,
                    global_k,
                    beat,
                    prev_beat,
                    next_beat,
                    points_transcript,
                    bible,
                    backend,
                    props_prompt,
                    compact_bible,
                    extra_user_prompt=slide_context,
                    max_attempts=3,
                )

            # Deterministic fallback
            if planned_scene is None:
                planned_scene = build_deterministic_kinetic_quote(scene_id_str, global_k, beat)

            # Critic check on people scenes
            if needs_critic(planned_scene):
                planned_scene, _, _ = _evaluate_scene_critic(
                    planned_scene,
                    beat,
                    prev_beat,
                    next_beat,
                    points_transcript,
                    bible,
                    backend,
                    props_prompt,
                    compact_bible,
                    passage=slide_passage,
                )

            # Extract free-text fields and compute normalized matching text
            scene_free_texts = extract_scene_free_text(planned_scene)
            combined_raw = f"{slide.title} {pt.text} {' '.join(scene_free_texts)}"
            norm_text = normalize_node_text(combined_raw)

            pt_node = TreeNode(
                id=pt_id,
                slide=slide.id,
                kind="point",
                point_i=p_idx,
                text=norm_text,
                scene=planned_scene,
            )
            nodes.append(pt_node)
            node_to_slide_idx[pt_id] = s_idx
            point_node_ids.append(pt_id)

    # 5. Build edges
    edges: list[TreeEdge] = []
    point_set = set(point_node_ids)

    # Next edges:
    # - section -> first point
    # - point k -> point k+1 of same slide
    # - last point of slide -> next slide's section
    next_edge_pairs: set[tuple[str, str]] = set()

    for s_idx, slide in enumerate(deck.slides):
        sec_id = f"{slide.id}_section"
        first_pt_id = f"{slide.id}_p0" if slide.points else None
        if first_pt_id:
            edges.append(TreeEdge(to=first_pt_id, kind="next", cost=0.0, **{"from": sec_id}))
            next_edge_pairs.add((sec_id, first_pt_id))

        for p_idx in range(len(slide.points) - 1):
            cur_pt = f"{slide.id}_p{p_idx}"
            nxt_pt = f"{slide.id}_p{p_idx + 1}"
            edges.append(TreeEdge(to=nxt_pt, kind="next", cost=0.0, **{"from": cur_pt}))
            next_edge_pairs.add((cur_pt, nxt_pt))

        if slide.points and s_idx + 1 < len(deck.slides):
            last_pt = f"{slide.id}_p{len(slide.points) - 1}"
            next_sec = f"{deck.slides[s_idx + 1].id}_section"
            edges.append(TreeEdge(to=next_sec, kind="next", cost=0.0, **{"from": last_pt}))
            next_edge_pairs.add((last_pt, next_sec))

    # Skip edges:
    # any node -> any point of the same or next two slides that is ahead of it
    # Cost: 0.15 per point skipped, capped at 0.6
    for i, from_node in enumerate(nodes):
        s_from = node_to_slide_idx[from_node.id]
        for j in range(i + 1, len(nodes)):
            to_node = nodes[j]
            if to_node.id not in point_set:
                continue
            s_to = node_to_slide_idx[to_node.id]
            if not (s_from <= s_to <= s_from + 2):
                continue
            if (from_node.id, to_node.id) in next_edge_pairs:
                continue

            # Points skipped: count of point nodes strictly between from_node and to_node
            pts_skipped = sum(1 for k in range(i + 1, j) if nodes[k].id in point_set)
            cost = round(min(0.6, max(0.15, 0.15 * pts_skipped)), 2)
            edges.append(TreeEdge(to=to_node.id, kind="skip", cost=cost, **{"from": from_node.id}))

    # Back edges:
    # any node -> any earlier point | cost 0.5
    for i, from_node in enumerate(nodes):
        for j in range(0, i):
            to_node = nodes[j]
            if to_node.id in point_set:
                edges.append(
                    TreeEdge(to=to_node.id, kind="back", cost=0.5, **{"from": from_node.id})
                )

    return TreePlan(schema_version=1, nodes=nodes, edges=edges)


def compile_tree_timeline(tree: TreePlan, bible: Bible, plan_sha: str = "") -> Timeline:
    """Compile presentation tree node scenes into a timeline for preview stills rendering."""
    timeline_scenes: list[TimelineScene] = []

    for idx, node in enumerate(tree.nodes):
        sc = node.scene
        start_f = idx * 150
        end_f = (idx + 1) * 150
        scene_frames = 150

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
            "id": sc.id,
            "template": sc.template,
            "start_frame": start_f,
            "end_frame": end_f,
            "hide_captions": True,
            "timing": timing,
            "props": clean_props,
            "overlays": [],
        }
        timeline_scene = _TIMELINE_SCENE_ADAPTER.validate_python(sc_dict)
        timeline_scenes.append(timeline_scene)

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
    sp_map = {
        sp.id: TimelineSetPiece(
            name=sp.name,
            image=None,
            icon=sp.icon,
        )
        for sp in bible.set_pieces
    }

    return Timeline(
        schema_version=1,
        duration_frames=len(tree.nodes) * 150,
        fps=30,
        width=1080,
        height=1920,
        plan_sha256=plan_sha,
        cast=cast_map,
        places=places_map,
        set_pieces=sp_map,
        scenes=timeline_scenes,
        captions=TimelineCaptions(pages=[]),
        audio=TimelineAudio(narration=TimelineNarration(src="points.wav"), music=None, sfx=[]),
        debug=TimelineDebug(),
    )


def run_tree_stage(job: Job, ctx: RunContext) -> None:
    """Execute tree planning stage, enforcing strict offline isolation."""
    t0 = time.perf_counter()

    # Isolation invariant: read only deck.json, deck_bible.json, and style
    deck_path = job.dir / "deck.json"
    if not deck_path.is_file():
        raise FileNotFoundError(f"deck.json missing in job {job.job_id}")

    deck_bible_path = job.dir / "deck_bible.json"
    if not deck_bible_path.is_file():
        raise FileNotFoundError(f"deck_bible.json missing in job {job.job_id}")

    deck = DeckPlan.model_validate_json(deck_path.read_text(encoding="utf-8"))
    bible = Bible.model_validate_json(deck_bible_path.read_text(encoding="utf-8"))

    style = ctx.style or "literal"
    backend = OllamaBackend(no_cache=ctx.no_llm_cache)

    tree = plan_tree(deck, bible, backend, style=style)

    # Save tree.json
    tree_path = job.dir / "tree.json"
    tree_path.write_text(tree.model_dump_json(by_alias=True, indent=2) + "\n", encoding="utf-8")

    # Compile and save timeline.json for preview stills rendering
    timeline = compile_tree_timeline(tree, bible, plan_sha=job.plan_sha256())
    timeline_path = job.dir / "timeline.json"
    timeline_path.write_text(timeline.model_dump_json(indent=2) + "\n", encoding="utf-8")

    # Run assets illustration once at tree time per §3
    run_assets(bible, job, backend=backend)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    log_file = job.dir / "logs" / "tree.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(
            f"Tree: nodes={len(tree.nodes)}, edges={len(tree.edges)}, "
            f"llm_calls={backend.calls}, elapsed_ms={elapsed_ms}\n"
        )

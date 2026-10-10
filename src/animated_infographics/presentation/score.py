"""Presentation scoring, metrics computation, strip chart, and oracle baseline.

Per design_presentation_simulation.md §8 and design_testing_and_validation.md §4c.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from animated_infographics.contracts.deck import Deck
from animated_infographics.contracts.models import Bible, Transcript
from animated_infographics.contracts.playback import PlaybackCommit, PlaybackPlan
from animated_infographics.contracts.score import PresentationMetricResult, PresentationScore
from animated_infographics.contracts.tree import TreePlan
from animated_infographics.planner.words import graphic_words
from animated_infographics.presentation.compose import compose_presentation_timeline
from animated_infographics.render import render_video


def _get_sentence_label_info(sent: dict[str, Any]) -> tuple[str | None, int | None]:
    """Extract (slide_id, point_i) from sentence label dict, handling back_ref."""
    lbl = sent.get("label")
    if not isinstance(lbl, dict):
        return None, None
    if "back_ref" in lbl and isinstance(lbl["back_ref"], dict):
        br = lbl["back_ref"]
        return br.get("slide"), br.get("point")
    return lbl.get("slide"), lbl.get("point")


def _get_shown_node_at_time(commits: list[dict[str, Any]], t_ms: int) -> str:
    """Find the active node_id from commits at time t_ms."""
    if not commits or commits[0]["at_ms"] > t_ms:
        return ""
    cur = commits[0]["node_id"]
    for c in commits:
        if c["at_ms"] <= t_ms:
            cur = c["node_id"]
        else:
            break
    return cur


def calculate_slide_accuracy(
    sentences: list[dict[str, Any]],
    timing: list[dict[str, Any]],
    commits: list[dict[str, Any]],
) -> float:
    """Fraction of non-ad-lib speech time where shown slide = ground-truth slide."""
    total_non_adlib_ms = 0
    correct_slide_ms = 0

    for sent, t in zip(sentences, timing, strict=False):
        if sent.get("op") == "adlib" or sent.get("label") == "adlib":
            continue

        gt_slide, _ = _get_sentence_label_info(sent)
        if not gt_slide:
            continue

        s_ms = int(t["start_ms"])
        e_ms = int(t["end_ms"])
        step = 10
        for cur_t in range(s_ms, e_ms, step):
            total_non_adlib_ms += step
            shown_node = _get_shown_node_at_time(commits, cur_t)
            shown_slide = shown_node.split("_")[0]
            if shown_slide == gt_slide:
                correct_slide_ms += step

    if total_non_adlib_ms == 0:
        return 1.0
    return round(correct_slide_ms / total_non_adlib_ms, 4)


def calculate_point_accuracy(
    sentences: list[dict[str, Any]],
    timing: list[dict[str, Any]],
    commits: list[dict[str, Any]],
) -> float:
    """Point accuracy: a section node counts as correct during its slide's first point."""
    total_non_adlib_ms = 0
    correct_point_ms = 0

    for sent, t in zip(sentences, timing, strict=False):
        if sent.get("op") == "adlib" or sent.get("label") == "adlib":
            continue

        gt_slide, gt_pt = _get_sentence_label_info(sent)
        if gt_slide is None or gt_pt is None:
            continue

        target_point_id = f"{gt_slide}_p{gt_pt}"
        s_ms = int(t["start_ms"])
        e_ms = int(t["end_ms"])
        step = 10

        for cur_t in range(s_ms, e_ms, step):
            total_non_adlib_ms += step
            shown_node = _get_shown_node_at_time(commits, cur_t)
            is_correct = (shown_node == target_point_id) or (
                gt_pt == 0 and shown_node == f"{gt_slide}_section"
            )
            if is_correct:
                correct_point_ms += step

    if total_non_adlib_ms == 0:
        return 1.0
    return round(correct_point_ms / total_non_adlib_ms, 4)


def calculate_onset_lag(
    sentences: list[dict[str, Any]],
    timing: list[dict[str, Any]],
    commits: list[dict[str, Any]],
) -> tuple[float | None, float | None]:
    """Onset lag: time from first spoken word of a point to its node's display.

    Per design_presentation_simulation.md §8 (revised October 9, 2026, Wave K):
    - Per point, with t0 the start of its first spoken sentence:
      * t_end is the start of the first later sentence whose label is not this
        point (ad-libs and back-references included), or the end of the talk.
      * The valid nodes are the point's node and, for point 0, its slide's section node.
    - The lag:
      * if a valid node is on screen at t0, the lag is 0;
      * otherwise, the first commit to a valid node in (t0, t_end), minus t0;
      * otherwise, the point is missed and scores max(10.0, (t_end - t0) / 1000).
    - Median and p90.
    """
    if not sentences or not timing:
        return None, None

    talk_end_ms = (
        int(timing[-1]["end_ms"]) if "end_ms" in timing[-1] else int(timing[-1]["start_ms"])
    )

    def _get_point_id(sent: dict[str, Any]) -> str | None:
        if sent.get("op") in ("adlib", "back_ref") or sent.get("label") == "adlib":
            return None
        lbl = sent.get("label")
        if not isinstance(lbl, dict) or "back_ref" in lbl:
            return None
        s_id = lbl.get("slide")
        p_id = lbl.get("point")
        if s_id is not None and p_id is not None:
            return f"{s_id}_p{p_id}"
        return None

    # Identify first spoken sentence for each unique point
    seen_points: set[str] = set()
    point_runs: list[tuple[str, int, int]] = []  # (pt_id, t0, t_end)

    n_sentences = min(len(sentences), len(timing))
    for i in range(n_sentences):
        sent = sentences[i]
        pt_id = _get_point_id(sent)
        if pt_id is None or pt_id in seen_points:
            continue
        seen_points.add(pt_id)
        t0 = int(timing[i]["start_ms"])

        # Find t_end: start of first later sentence whose label is not this point,
        # or the end of the talk
        t_end = talk_end_ms
        for j in range(i + 1, n_sentences):
            later_sent = sentences[j]
            later_pt = _get_point_id(later_sent)
            if later_pt != pt_id:
                t_end = int(timing[j]["start_ms"])
                break

        point_runs.append((pt_id, t0, t_end))

    if not point_runs:
        return None, None

    lags: list[float] = []
    for pt_id, t0, t_end in point_runs:
        slide_prefix = pt_id.split("_")[0]
        valid_nodes = {pt_id}
        if pt_id.endswith("_p0"):
            valid_nodes.add(f"{slide_prefix}_section")

        # 1. If a valid node is on screen at t0, lag is 0
        shown_at_t0 = _get_shown_node_at_time(commits, t0)
        if shown_at_t0 in valid_nodes:
            lags.append(0.0)
            continue

        # 2. Otherwise, first commit to a valid node in (t0, t_end), minus t0
        matching_commit = next(
            (c for c in commits if c["node_id"] in valid_nodes and t0 < c["at_ms"] < t_end),
            None,
        )
        if matching_commit is not None:
            lag_s = max(0.0, (matching_commit["at_ms"] - t0) / 1000.0)
            lags.append(lag_s)
        else:
            # 3. Otherwise, missed: max(10.0, (t_end - t0) / 1000)
            miss_penalty = max(10.0, (t_end - t0) / 1000.0)
            lags.append(miss_penalty)

    if not lags:
        return None, None

    lags.sort()
    median_lag = float(np.median(lags))
    p90_lag = float(np.percentile(lags, 90))
    return round(median_lag, 2), round(p90_lag, 2)


def calculate_false_switches(
    sentences: list[dict[str, Any]],
    timing: list[dict[str, Any]],
    commits: list[dict[str, Any]],
    deck: dict[str, Any],
    total_dur_ms: int,
) -> float:
    """Commits to a node that is neither the ground-truth node nor next one in deck, per min."""
    if len(commits) <= 1:
        return 0.0

    # Build deck point sequence
    deck_points: list[str] = []
    for s in deck.get("slides", []):
        sid = s["id"]
        for p_idx in range(len(s.get("points", []))):
            deck_points.append(f"{sid}_p{p_idx}")

    deck_idx_map = {pid: idx for idx, pid in enumerate(deck_points)}
    false_count = 0

    for c in commits[1:]:  # Skip initial commit at 0 ms
        c_at = int(c["at_ms"])
        # Find active sentence at commit time
        active_sent = None
        for sent, t in zip(sentences, timing, strict=False):
            if int(t["start_ms"]) <= c_at <= int(t["end_ms"]):
                active_sent = sent
                break
        if not active_sent:
            # In a pause: find last sentence before c_at
            for sent, t in zip(sentences, timing, strict=False):
                if int(t["end_ms"]) <= c_at:
                    active_sent = sent
                else:
                    break

        if not active_sent:
            continue

        if active_sent.get("op") == "adlib" or active_sent.get("label") == "adlib":
            false_count += 1
            continue

        gt_slide, gt_pt = _get_sentence_label_info(active_sent)
        if gt_slide is None or gt_pt is None:
            continue

        gt_id = f"{gt_slide}_p{gt_pt}"
        allowed_nodes = {gt_id}
        if gt_pt == 0:
            allowed_nodes.add(f"{gt_slide}_section")

        curr_idx = deck_idx_map.get(gt_id)
        if curr_idx is not None and curr_idx + 1 < len(deck_points):
            next_id = deck_points[curr_idx + 1]
            allowed_nodes.add(next_id)
            if next_id.endswith("_p0"):
                allowed_nodes.add(f"{next_id.split('_')[0]}_section")

        if c["node_id"] not in allowed_nodes:
            false_count += 1

    total_minutes = max(0.1, total_dur_ms / 60000.0)
    return round(false_count / total_minutes, 2)


def calculate_adlib_stability(
    sentences: list[dict[str, Any]],
    timing: list[dict[str, Any]],
    commits: list[dict[str, Any]],
) -> float:
    """Fraction of ad-lib time with no commit."""
    total_adlib_ms = 0
    stable_adlib_ms = 0

    for sent, t in zip(sentences, timing, strict=False):
        if sent.get("op") == "adlib" or sent.get("label") == "adlib":
            s_ms = int(t["start_ms"])
            e_ms = int(t["end_ms"])
            dur = e_ms - s_ms
            total_adlib_ms += dur

            commits_during = [c for c in commits if s_ms <= c["at_ms"] <= e_ms]
            if not commits_during:
                stable_adlib_ms += dur
            else:
                first_c = min(c["at_ms"] for c in commits_during)
                stable_adlib_ms += max(0, first_c - s_ms)

    if total_adlib_ms == 0:
        return 1.0
    return round(stable_adlib_ms / total_adlib_ms, 4)


def calculate_skip_recovery(
    sentences: list[dict[str, Any]],
    timing: list[dict[str, Any]],
    commits: list[dict[str, Any]],
    deck: dict[str, Any],
) -> float | None:
    """Time from first word after a skipped point to the correct node."""
    deck_points: list[str] = []
    for s in deck.get("slides", []):
        sid = s["id"]
        for p_idx in range(len(s.get("points", []))):
            deck_points.append(f"{sid}_p{p_idx}")

    perf_points: set[str] = set()
    for sent in sentences:
        s_id, p_id = _get_sentence_label_info(sent)
        if s_id and p_id is not None:
            perf_points.add(f"{s_id}_p{p_id}")

    skipped = [p for p in deck_points if p not in perf_points]
    if not skipped:
        return None

    # Find the first point after skipped point
    sk_point = skipped[0]
    sk_idx = deck_points.index(sk_point)
    if sk_idx + 1 >= len(deck_points):
        return None

    next_point = deck_points[sk_idx + 1]
    # Find first spoken timing of next_point
    first_spoken_ms = None
    for sent, t in zip(sentences, timing, strict=False):
        s_id, p_id = _get_sentence_label_info(sent)
        if s_id and p_id is not None and f"{s_id}_p{p_id}" == next_point:
            first_spoken_ms = int(t["start_ms"])
            break

    if first_spoken_ms is None:
        return None

    matching_commit = next(
        (c for c in commits if c["node_id"] == next_point and c["at_ms"] >= first_spoken_ms - 500),
        None,
    )
    if matching_commit:
        recovery_s = max(0.0, (matching_commit["at_ms"] - first_spoken_ms) / 1000.0)
        return round(recovery_s, 2)
    return 99.0


def generate_strip_chart(
    sentences: list[dict[str, Any]],
    timing: list[dict[str, Any]],
    commits: list[dict[str, Any]],
    deck: dict[str, Any],
    total_dur_ms: int,
    out_path: Path,
) -> None:
    """Draw ground-truth slide vs shown slide over time using Pillow."""
    width = 1200
    height = 450
    margin_left = 80
    margin_right = 50
    margin_top = 70
    margin_bottom = 60

    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    slides = [s["id"] for s in deck.get("slides", [])]
    n_slides = len(slides)
    slide_y_map = {
        s: margin_top + int((n_slides - 1 - idx) * (plot_h / max(1, n_slides - 1)))
        for idx, s in enumerate(slides)
    }

    img = Image.new("RGB", (width, height), color="#0F172A")
    draw = ImageDraw.Draw(img)

    font = ImageFont.load_default()

    # Title
    draw.text(
        (margin_left, 20),
        "Presentation Simulation: Ground-Truth vs Shown Slide Over Time",
        fill="#F8FAFC",
        font=font,
    )

    # Legend
    legend_x = width - margin_right - 260
    draw.rectangle([legend_x, 22, legend_x + 18, 28], fill="#38BDF8")
    draw.text((legend_x + 24, 18), "Ground-Truth Slide", fill="#94A3B8", font=font)
    draw.rectangle([legend_x + 140, 22, legend_x + 158, 28], fill="#F59E0B")
    draw.text((legend_x + 164, 18), "Shown Slide", fill="#94A3B8", font=font)

    # Grid lines and Y labels
    for s_id, y_pos in slide_y_map.items():
        draw.line([(margin_left, y_pos), (width - margin_right, y_pos)], fill="#1E293B", width=1)
        draw.text((margin_left - 40, y_pos - 6), s_id.upper(), fill="#64748B", font=font)

    # X axis time labels
    dur_s = max(1, total_dur_ms // 1000)
    step_s = 30 if dur_s <= 180 else 60
    for t_s in range(0, dur_s + 1, step_s):
        x_pos = margin_left + int((t_s * 1000 / total_dur_ms) * plot_w)
        draw.line([(x_pos, margin_top), (x_pos, height - margin_bottom)], fill="#1E293B", width=1)
        mins = t_s // 60
        secs = t_s % 60
        draw.text(
            (x_pos - 12, height - margin_bottom + 10),
            f"{mins}:{secs:02d}",
            fill="#64748B",
            font=font,
        )

    # Plot ad-lib shaded regions
    for sent, t in zip(sentences, timing, strict=False):
        if sent.get("op") == "adlib" or sent.get("label") == "adlib":
            x0 = margin_left + int((t["start_ms"] / total_dur_ms) * plot_w)
            x1 = margin_left + int((t["end_ms"] / total_dur_ms) * plot_w)
            draw.rectangle([x0, margin_top, x1, height - margin_bottom], fill="#1E293B")
            draw.text((x0 + 4, margin_top + 4), "Ad-lib", fill="#475569", font=font)

    # Plot Ground Truth (step function in blue)
    gt_pts: list[tuple[int, int]] = []
    for sent, t in zip(sentences, timing, strict=False):
        if sent.get("op") == "adlib" or sent.get("label") == "adlib":
            continue
        gt_slide, _ = _get_sentence_label_info(sent)
        if not gt_slide or gt_slide not in slide_y_map:
            continue
        y_val = slide_y_map[gt_slide]
        x_start = margin_left + int((t["start_ms"] / total_dur_ms) * plot_w)
        x_end = margin_left + int((t["end_ms"] / total_dur_ms) * plot_w)
        gt_pts.extend([(x_start, y_val), (x_end, y_val)])

    for i in range(len(gt_pts) - 1):
        draw.line([gt_pts[i], gt_pts[i + 1]], fill="#38BDF8", width=3)

    # Plot Shown Slide (step function in amber)
    shown_pts: list[tuple[int, int]] = []
    for idx, c in enumerate(commits):
        c_slide = c["node_id"].split("_")[0]
        y_val = slide_y_map.get(c_slide, slide_y_map.get(slides[0], margin_top))
        x_start = margin_left + int((c["at_ms"] / total_dur_ms) * plot_w)
        next_t = commits[idx + 1]["at_ms"] if idx + 1 < len(commits) else total_dur_ms
        x_end = margin_left + int((next_t / total_dur_ms) * plot_w)
        shown_pts.extend([(x_start, y_val), (x_end, y_val)])

    for i in range(len(shown_pts) - 1):
        draw.line([shown_pts[i], shown_pts[i + 1]], fill="#F59E0B", width=2)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)


def evaluate_presentation_bars(
    score_data: PresentationScore | dict[str, Any],
) -> list[PresentationMetricResult]:
    """Evaluate presentation metrics against §8 bars for a score object or dict."""
    if isinstance(score_data, PresentationScore):
        level = score_data.level
        slide_acc = score_data.slide_accuracy
        point_acc = score_data.point_accuracy
        median_lag = score_data.onset_lag_median_s
        p90_lag = score_data.onset_lag_p90_s
        false_switches = score_data.false_switches_per_min
        adlib_stab = score_data.adlib_stability
        skip_rec = score_data.skip_recovery_s
    else:
        level = score_data.get("level", "mild")
        slide_acc = float(score_data.get("slide_accuracy", 0.0))
        point_acc = float(score_data.get("point_accuracy", 0.0))
        median_lag = score_data.get("onset_lag_median_s")
        if median_lag is not None:
            median_lag = float(median_lag)
        p90_lag = score_data.get("onset_lag_p90_s")
        if p90_lag is not None:
            p90_lag = float(p90_lag)
        false_switches = float(score_data.get("false_switches_per_min", 0.0))
        adlib_stab = float(score_data.get("adlib_stability", 0.0))
        skip_rec = score_data.get("skip_recovery_s")
        if skip_rec is not None:
            skip_rec = float(skip_rec)

    # Bars definition per §8
    slide_bar = 0.90 if level == "mild" else 0.80
    point_bar = 0.75 if level == "mild" else 0.60
    median_lag_bar = 3.0 if level == "mild" else 4.0
    p90_lag_bar = 6.0 if level == "mild" else 8.0
    false_sw_bar = 1.0 if level == "mild" else 2.0
    adlib_bar = 0.80 if level == "mild" else 0.70

    metrics: list[PresentationMetricResult] = [
        PresentationMetricResult(
            metric="slide_accuracy",
            value=slide_acc,
            bar=slide_bar,
            passed=(slide_acc >= slide_bar),
        ),
        PresentationMetricResult(
            metric="point_accuracy",
            value=point_acc,
            bar=point_bar,
            passed=(point_acc >= point_bar),
        ),
        PresentationMetricResult(
            metric="onset_lag_median_s",
            value=median_lag,
            bar=median_lag_bar,
            passed=(median_lag is not None and median_lag <= median_lag_bar),
        ),
        PresentationMetricResult(
            metric="onset_lag_p90_s",
            value=p90_lag,
            bar=p90_lag_bar,
            passed=(p90_lag is not None and p90_lag <= p90_lag_bar),
        ),
        PresentationMetricResult(
            metric="false_switches_per_min",
            value=false_switches,
            bar=false_sw_bar,
            passed=(false_switches <= false_sw_bar),
        ),
        PresentationMetricResult(
            metric="adlib_stability",
            value=adlib_stab,
            bar=adlib_bar,
            passed=(adlib_stab >= adlib_bar),
        ),
    ]

    if level == "strong":
        skip_passed = (skip_rec is None) or (skip_rec <= 6.0)
        metrics.append(
            PresentationMetricResult(
                metric="skip_recovery_s",
                value=skip_rec,
                bar=6.0,
                passed=skip_passed,
            )
        )

    return metrics


def format_bar_str(metric: str, bar: float | str | None) -> str:
    """Format metric bar condition as string, e.g. '>=0.90' or '<=3.0'."""
    if bar is None:
        return ""
    if isinstance(bar, str) and (bar.startswith(">=") or bar.startswith("<=")):
        return bar
    if metric in ("slide_accuracy", "point_accuracy", "adlib_stability"):
        return f">={float(bar):.2f}"
    return f"<={float(bar):.1f}"


def compute_presentation_score(job_dir: Path, oracle: bool = False) -> PresentationScore:
    """Compute presentation simulation metrics against §8 bars."""
    perf_path = job_dir / "performance.json"
    timing_path = job_dir / "speak_timing.json"
    playback_path = job_dir / "playback.json"
    deck_path = job_dir / "deck.json"
    tree_path = job_dir / "tree.json"
    heard_path = job_dir / "heard.json"
    timeline_path = job_dir / "timeline.json"
    ingest_path = job_dir / "ingest.json"

    if not perf_path.is_file():
        raise FileNotFoundError(f"performance.json missing in {job_dir}")
    if not timing_path.is_file():
        raise FileNotFoundError(f"speak_timing.json missing in {job_dir}")
    if not playback_path.is_file():
        raise FileNotFoundError(f"playback.json missing in {job_dir}")
    if not deck_path.is_file():
        raise FileNotFoundError(f"deck.json missing in {job_dir}")
    if not tree_path.is_file():
        raise FileNotFoundError(f"tree.json missing in {job_dir}")
    if not timeline_path.is_file():
        raise FileNotFoundError(f"timeline.json missing in {job_dir}")

    perf_data = json.loads(perf_path.read_text(encoding="utf-8"))
    timing_data = json.loads(timing_path.read_text(encoding="utf-8"))
    playback_data = json.loads(playback_path.read_text(encoding="utf-8"))
    deck_data = json.loads(deck_path.read_text(encoding="utf-8"))
    tree_data = json.loads(tree_path.read_text(encoding="utf-8"))
    timeline_data = json.loads(timeline_path.read_text(encoding="utf-8"))

    level = perf_data.get("level", "mild")
    sentences = perf_data.get("sentences", [])
    commits = playback_data.get("commits", [])
    total_dur_ms = int(timeline_data.get("duration_frames", 0)) * 1000 // 30

    ingest_data = (
        json.loads(ingest_path.read_text(encoding="utf-8")) if ingest_path.is_file() else {}
    )
    style = ingest_data.get("style", "literal")

    # Metrics computation
    slide_acc = calculate_slide_accuracy(sentences, timing_data, commits)
    point_acc = calculate_point_accuracy(sentences, timing_data, commits)
    median_lag, p90_lag = calculate_onset_lag(sentences, timing_data, commits)
    false_switches = calculate_false_switches(
        sentences, timing_data, commits, deck_data, total_dur_ms
    )
    adlib_stab = calculate_adlib_stability(sentences, timing_data, commits)
    skip_rec = calculate_skip_recovery(sentences, timing_data, commits, deck_data)

    metrics = evaluate_presentation_bars(
        {
            "level": level,
            "slide_accuracy": slide_acc,
            "point_accuracy": point_acc,
            "onset_lag_median_s": median_lag,
            "onset_lag_p90_s": p90_lag,
            "false_switches_per_min": false_switches,
            "adlib_stability": adlib_stab,
            "skip_recovery_s": skip_rec,
        }
    )
    all_passed = all(m.passed for m in metrics)

    # Inherited checks: word density and scene criteria
    total_graphic = 0
    scenes = timeline_data.get("scenes", [])
    for sc in scenes:
        template = sc.get("template", "")
        props = sc.get("props", {})
        total_graphic += graphic_words(template, props)

    dur_s = max(1.0, total_dur_ms / 1000.0)
    density = round(total_graphic / dur_s, 2)

    # Scene criteria checks
    clean_scenes = True
    for sc in scenes:
        props = sc.get("props", {})
        # check placeholder text
        from animated_infographics.planner.validate import placeholder_errors

        if placeholder_errors(sc.get("template", ""), props):
            clean_scenes = False
            break

    # Generate strip chart
    strip_chart_path = job_dir / "strip_chart.png"
    generate_strip_chart(sentences, timing_data, commits, deck_data, total_dur_ms, strip_chart_path)

    out_score_json = job_dir / "presentation_score.json"
    oracle_score_obj: PresentationScore | None = None
    if oracle:
        oracle_score_obj = _run_oracle_baseline(
            job_dir,
            sentences,
            timing_data,
            deck_data,
            tree_data,
            heard_path,
            total_dur_ms,
            level,
            style,
        )
    elif out_score_json.is_file():
        try:
            prev = json.loads(out_score_json.read_text(encoding="utf-8"))
            if prev.get("oracle"):
                oracle_score_obj = PresentationScore.model_validate(prev["oracle"])
        except Exception:
            pass

    score_result = PresentationScore(
        schema_version=1,
        job_id=job_dir.name,
        level=level,
        style=style,
        slide_accuracy=slide_acc,
        point_accuracy=point_acc,
        onset_lag_median_s=median_lag,
        onset_lag_p90_s=p90_lag,
        false_switches_per_min=false_switches,
        adlib_stability=adlib_stab,
        skip_recovery_s=skip_rec,
        all_passed=all_passed,
        metrics=metrics,
        density_words_per_s=density,
        scene_criteria_clean=clean_scenes,
        oracle=oracle_score_obj,
    )

    out_score_json = job_dir / "presentation_score.json"
    out_score_json.write_text(score_result.model_dump_json(indent=2), encoding="utf-8")
    return score_result


def _run_oracle_baseline(
    job_dir: Path,
    sentences: list[dict[str, Any]],
    timing: list[dict[str, Any]],
    deck: dict[str, Any],
    tree_data: dict[str, Any],
    heard_path: Path,
    total_dur_ms: int,
    level: str,
    style: str,
) -> PresentationScore:
    """Compose and render oracle baseline from ground truth timing."""
    tree = TreePlan.model_validate(tree_data)
    heard = Transcript.model_validate_json(heard_path.read_text(encoding="utf-8"))
    deck_obj = Deck.model_validate(deck)

    # Build oracle commits
    first_slide_id = deck_obj.slides[0].id if deck_obj.slides else "d1"
    initial_node = f"{first_slide_id}_section"

    oracle_commits: list[PlaybackCommit] = []
    seen_points: set[str] = set()
    for sent, t in zip(sentences, timing, strict=False):
        if sent.get("op") == "adlib" or sent.get("label") == "adlib":
            continue
        s_id, p_id = _get_sentence_label_info(sent)
        if s_id is None or p_id is None:
            continue
        target_pt = f"{s_id}_p{p_id}"
        if target_pt not in seen_points:
            seen_points.add(target_pt)
            oracle_commits.append(
                PlaybackCommit(
                    node_id=target_pt,
                    at_ms=int(t["start_ms"]),
                    decision_ms=int(t["start_ms"]),
                    compute_ms=0,
                    score=10.0,
                )
            )

    oracle_commits.sort(key=lambda c: c.at_ms)
    if not oracle_commits or oracle_commits[0].at_ms > 0:
        oracle_commits.insert(
            0,
            PlaybackCommit(
                node_id=initial_node,
                at_ms=0,
                decision_ms=0,
                compute_ms=0,
                score=10.0,
            ),
        )

    oracle_playback = PlaybackPlan(
        schema_version=1,
        commits=oracle_commits,
        holds=[],
    )

    # Compose oracle timeline
    bible_path = job_dir / "deck_bible.json"
    bible = (
        Bible.model_validate_json(bible_path.read_text(encoding="utf-8"))
        if bible_path.is_file()
        else None
    )

    oracle_timeline, _ = compose_presentation_timeline(
        tree=tree,
        playback=oracle_playback,
        heard=heard,
        bible=bible,
    )

    oracle_timeline_path = job_dir / "oracle_timeline.json"
    oracle_timeline_path.write_text(
        oracle_timeline.model_dump_json(indent=2, by_alias=True) + "\n", encoding="utf-8"
    )

    # Render oracle.mp4
    oracle_mp4 = job_dir / "out" / "oracle.mp4"
    try:
        render_video(job_dir, out_path=oracle_mp4, timeline_path=oracle_timeline_path)
    except Exception as e:
        print(f"Warning: oracle video rendering failed: {e}")

    # Calculate oracle metrics
    oracle_commits_dicts = [c.model_dump() for c in oracle_commits]
    slide_acc = calculate_slide_accuracy(sentences, timing, oracle_commits_dicts)
    point_acc = calculate_point_accuracy(sentences, timing, oracle_commits_dicts)
    median_lag, p90_lag = calculate_onset_lag(sentences, timing, oracle_commits_dicts)
    false_switches = calculate_false_switches(
        sentences, timing, oracle_commits_dicts, deck, total_dur_ms
    )
    adlib_stab = calculate_adlib_stability(sentences, timing, oracle_commits_dicts)

    oracle_metrics = evaluate_presentation_bars(
        {
            "level": level,
            "slide_accuracy": slide_acc,
            "point_accuracy": point_acc,
            "onset_lag_median_s": median_lag,
            "onset_lag_p90_s": p90_lag,
            "false_switches_per_min": false_switches,
            "adlib_stability": adlib_stab,
            "skip_recovery_s": 0.0 if level == "strong" else None,
        }
    )
    oracle_all_passed = all(m.passed for m in oracle_metrics)

    oracle_score = PresentationScore(
        schema_version=1,
        job_id=f"{job_dir.name}_oracle",
        level=level,
        style=style,
        slide_accuracy=slide_acc,
        point_accuracy=point_acc,
        onset_lag_median_s=median_lag,
        onset_lag_p90_s=p90_lag,
        false_switches_per_min=false_switches,
        adlib_stability=adlib_stab,
        skip_recovery_s=0.0 if level == "strong" else None,
        all_passed=oracle_all_passed,
        metrics=oracle_metrics,
    )
    return oracle_score

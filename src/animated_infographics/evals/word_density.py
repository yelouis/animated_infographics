"""Word-density evaluation CLI measuring on-screen graphic words per second and light scene share.

Per design_templates.md §5 and design_testing_and_validation.md §4 step 9.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from animated_infographics.planner.words import graphic_words


def evaluate_job_word_density(job_dir: Path | str) -> dict[str, Any]:
    """Evaluate word density and light scene share for a single job directory.

    Loads timeline.json:
    - graphic_words = sum of graphic_words(scene.template, scene.props)
    - seconds = duration_frames / fps
    - per_second = graphic_words / seconds
    - light = k / m (k = scenes after title card with <= 2 graphic words,
      m = scenes after title card)
    """
    p = Path(job_dir)
    timeline_path = p / "timeline.json" if p.is_dir() else p
    if not timeline_path.is_file():
        raise FileNotFoundError(f"timeline.json not found at {timeline_path}")

    data = json.loads(timeline_path.read_text(encoding="utf-8"))
    meta = data.get("meta", {})
    fps = float(data.get("fps") or meta.get("fps") or 30)
    duration_frames = float(data.get("duration_frames") or meta.get("duration_frames") or 0)
    seconds = (duration_frames / fps) if fps > 0 else 0.0

    scenes = data.get("scenes", [])
    total_graphic_words = sum(
        graphic_words(sc.get("template", ""), sc.get("props", {}), sc.get("overlays"))
        for sc in scenes
    )
    per_second = (total_graphic_words / seconds) if seconds > 0 else 0.0

    post_title_scenes = (
        scenes[1:]
        if len(scenes) > 1 and scenes[0].get("template") == "title_card"
        else [s for s in scenes if s.get("template") != "title_card"]
    )
    m = len(post_title_scenes)
    k = sum(
        1
        for sc in post_title_scenes
        if graphic_words(sc.get("template", ""), sc.get("props", {}), sc.get("overlays")) <= 2
    )

    passed = (per_second <= 1.0) and (k >= (m / 3.0) if m > 0 else True)

    job_label = p.name if p.is_dir() else p.parent.name
    return {
        "job": job_label,
        "graphic_words": total_graphic_words,
        "seconds": seconds,
        "per_second": per_second,
        "k": k,
        "m": m,
        "passed": passed,
    }


def format_density_line(res: dict[str, Any]) -> str:
    """Format evaluation line.

    Output format:
    <job>: graphic_words=<n> seconds=<s.s> per_second=<x.xx> light=<k>/<m>
    """
    return (
        f"{res['job']}: graphic_words={res['graphic_words']} "
        f"seconds={res['seconds']:.1f} per_second={res['per_second']:.2f} "
        f"light={res['k']}/{res['m']}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Measure graphic words per second and light scene share across jobs."
    )
    parser.add_argument(
        "job_dirs",
        nargs="+",
        help="One or more job directories containing timeline.json",
    )
    args = parser.parse_args(argv)

    all_passed = True
    for job_arg in args.job_dirs:
        try:
            res = evaluate_job_word_density(job_arg)
            line = format_density_line(res)
            print(line)
            if not res["passed"]:
                all_passed = False
        except Exception as exc:
            print(f"Error evaluating {job_arg}: {exc}", file=sys.stderr)
            all_passed = False

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

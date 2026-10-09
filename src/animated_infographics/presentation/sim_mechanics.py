"""Presentation simulation mechanics validation (Item I8).

Per design_testing_and_validation.md §4c and agent_execution_guide.md §3.I8:
Mechanics, each failing with exit 1:
- every artefact exists;
- step 10 is all 0, including I5's and I6's columns, and the density bar holds;
- the oracle meets every §8 bar, judged by the same bars function the follower is judged by;
- no point node uses title_card;
- each creative run has style_degraded: false, >= 1 metaphor node, a tree.log whose
  license_calls equals the metaphors plus asides plus license_dropped, and >= 1 non-empty overlays.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from animated_infographics.evals.verify_e2e_scenes import verify_job_scenes
from animated_infographics.evals.word_density import evaluate_job_word_density
from animated_infographics.presentation.score import evaluate_presentation_bars

REQUIRED_ARTEFACTS: list[str] = [
    "state.json",
    "ingest.json",
    "deck.json",
    "deck_bible.json",
    "tree.json",
    "performance.json",
    "speak_timing.json",
    "heard.json",
    "playback.json",
    "timeline.json",
    "oracle_timeline.json",
    "presentation_score.json",
    "strip_chart.png",
    "out/final.mp4",
    "out/oracle.mp4",
    "logs/tree.log",
]


def check_job_mechanics(job_dir: Path) -> list[str]:
    """Validate all mechanics rules for a presentation simulation job.

    Returns a list of error strings. Empty list indicates clean mechanics.
    """
    errors: list[str] = []
    if not job_dir.is_dir():
        return [f"Job directory does not exist: {job_dir}"]

    # 1. Every artefact exists and is non-empty
    for rel_path in REQUIRED_ARTEFACTS:
        p = job_dir / rel_path
        if not p.is_file():
            errors.append(f"Missing required artefact: {rel_path}")
        elif p.stat().st_size == 0:
            errors.append(f"Required artefact is empty (0 bytes): {rel_path}")

    # Load ingest to check style
    ingest_path = job_dir / "ingest.json"
    style = "literal"
    if ingest_path.is_file():
        try:
            ingest_data = json.loads(ingest_path.read_text(encoding="utf-8"))
            style = ingest_data.get("style", "literal")
        except Exception as e:
            errors.append(f"Failed to parse ingest.json: {e}")

    if style == "creative":
        dir_p = job_dir / "director.json"
        if not dir_p.is_file():
            errors.append("Missing required artefact in creative run: director.json")
        elif dir_p.stat().st_size == 0:
            errors.append("Required artefact is empty (0 bytes): director.json")

    # 2. Step 10 is all 0, including I5's and I6's columns, and density bar holds
    try:
        scene_res = verify_job_scenes(job_dir)
        if not scene_res.get("passed", False):
            errors.append(
                f"Step 10 criteria failed: "
                f"tones={scene_res.get('unneutral_flagged_tones')}, "
                f"attr={scene_res.get('disputed_attributions_kept')}, "
                f"r7={scene_res.get('r7_quoted_repairs')}, "
                f"years={scene_res.get('year_stats')}, "
                f"dates={scene_res.get('date_stats')}, "
                f"junk={scene_res.get('junk_text')}, "
                f"era={scene_res.get('invented_era_stamps')}, "
                f"armchairs={scene_res.get('armchair_count')}, "
                f"names={scene_res.get('names_before_narration')}, "
                f"assets={scene_res.get('asset_execution_errors')}"
            )
    except Exception as e:
        errors.append(f"Failed to execute verify_job_scenes: {e}")

    try:
        density_res = evaluate_job_word_density(job_dir)
        per_sec = density_res.get("per_second", 0.0)
        if per_sec > 1.0:
            errors.append(f"Graphic word density {per_sec:.2f} exceeds 1.0 words/s bar")
    except Exception as e:
        errors.append(f"Failed to evaluate word density: {e}")

    # 3. The oracle meets every §8 bar, judged by the same bars function
    score_path = job_dir / "presentation_score.json"
    if score_path.is_file():
        try:
            score_data = json.loads(score_path.read_text(encoding="utf-8"))
            oracle_score = score_data.get("oracle")
            if not oracle_score:
                errors.append("Missing oracle baseline score in presentation_score.json")
            else:
                oracle_metrics = evaluate_presentation_bars(oracle_score)
                for m in oracle_metrics:
                    if not m.passed:
                        errors.append(f"Oracle missed §8 bar: {m.metric}={m.value} (bar {m.bar})")
        except Exception as e:
            errors.append(f"Failed to check oracle baseline bars: {e}")

    # 4. No point node uses title_card
    tree_path = job_dir / "tree.json"
    tree_data: dict[str, Any] = {}
    if tree_path.is_file():
        try:
            tree_data = json.loads(tree_path.read_text(encoding="utf-8"))
            nodes = tree_data.get("nodes", [])
            for node in nodes:
                if node.get("kind") == "point":
                    tmpl = node.get("scene", {}).get("template")
                    if tmpl == "title_card":
                        errors.append(
                            f"Point node {node.get('id')} uses forbidden template 'title_card'"
                        )
        except Exception as e:
            errors.append(f"Failed to parse tree.json: {e}")

    # 5. Creative run specific checks
    if style == "creative":
        if tree_data.get("style_degraded", False):
            errors.append("Creative presentation tree has style_degraded == True")

        nodes = tree_data.get("nodes", [])
        metaphor_nodes = [n for n in nodes if n.get("scene", {}).get("template") == "metaphor"]
        if len(metaphor_nodes) < 1:
            errors.append(
                f"Creative presentation tree has {len(metaphor_nodes)} metaphor nodes (bar >= 1)"
            )

        overlay_nodes = [n for n in nodes if len(n.get("overlays", [])) > 0]
        if len(overlay_nodes) < 1:
            errors.append(
                f"Creative presentation tree has {len(overlay_nodes)} "
                f"nodes with overlays (bar >= 1)"
            )

        tree_log_path = job_dir / "logs" / "tree.log"
        if tree_log_path.is_file():
            tree_log = tree_log_path.read_text(encoding="utf-8")
            match = re.search(
                r"director=(\w+)\s+license_calls=(\d+)\s+license_dropped=(\d+)\s+overlays=(\d+)",
                tree_log,
            )
            if not match:
                errors.append(
                    "logs/tree.log missing required summary line "
                    "'director=... license_calls=... license_dropped=... overlays=...'"
                )
            else:
                calls = int(match.group(2))
                dropped = int(match.group(3))
                dir_path = job_dir / "director.json"
                if dir_path.is_file():
                    try:
                        dir_data = json.loads(dir_path.read_text(encoding="utf-8"))
                        metaphors_n = len(dir_data.get("metaphors", []))
                        asides_n = len(dir_data.get("asides", []))
                        expected_calls = metaphors_n + asides_n + dropped
                        if calls != expected_calls:
                            errors.append(
                                f"logs/tree.log license_calls={calls} != expected {expected_calls} "
                                f"({metaphors_n} metaphors + {asides_n} asides + {dropped} dropped)"
                            )
                    except Exception as e:
                        errors.append(f"Failed to parse director.json: {e}")

    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m animated_infographics.presentation.sim_mechanics <job_dir> ...")
        return 1

    all_ok = True
    for arg in sys.argv[1:]:
        p = Path(arg)
        errs = check_job_mechanics(p)
        if errs:
            all_ok = False
            print(f"[-] Mechanics FAILED for {p.name}:", file=sys.stderr)
            for err in errs:
                print(f"    - {err}", file=sys.stderr)
        else:
            print(f"[+] Mechanics PASSED for {p.name}")

    if not all_ok:
        return 1
    print("[+] All mechanics passed across all checked jobs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

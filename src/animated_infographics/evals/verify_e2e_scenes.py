"""Verification of Wave E criteria across rendered E2E jobs.

Per agent_execution_guide.md §3.E6:
- 0 dialogue lines whose tone the critic flagged as 'vs unknown' remain non-neutral;
- 0 kinetic_quote scenes keep a disputed attribution;
- 0 R7 repairs on beats with quoted speech;
- 0 year-like stats;
- Armchair count (must be 0).
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from animated_infographics.planner.rhythm import QUOTED


def verify_job_scenes(job_dir: Path) -> dict[str, Any]:
    plan_report_path = job_dir / "plan_report.json"
    storyboard_path = job_dir / "storyboard.json"
    beats_path = job_dir / "beats.json"

    if not plan_report_path.exists() or not storyboard_path.exists():
        raise FileNotFoundError(f"Missing plan_report.json or storyboard.json in {job_dir}")

    plan_report = json.loads(plan_report_path.read_text(encoding="utf-8"))
    storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
    beats_map: dict[int, str] = {}
    if beats_path.exists():
        beats_data = json.loads(beats_path.read_text(encoding="utf-8"))
        beats_list = beats_data.get("beats", []) if isinstance(beats_data, dict) else beats_data
        beats_map = {b["i"]: b["text"] for b in beats_list if isinstance(b, dict) and "i" in b}

    scenes_by_id = {s["id"]: s for s in storyboard.get("scenes", [])}

    unneutral_flagged_tones = 0
    disputed_attributions_kept = 0
    r7_quoted_repairs = 0
    year_stats = 0
    armchair_count = 0

    # 1. Critic tone & attribution checks from plan_report
    for sc_rep in plan_report.get("scenes", []):
        sc_id = sc_rep.get("id") or sc_rep.get("scene_id")
        sb_scene = scenes_by_id.get(sc_id)
        if not sb_scene:
            continue

        critic = sc_rep.get("critic")
        if critic:
            mismatches = critic.get("mismatches", [])
            # Dialogue tone vs unknown
            for m in mismatches:
                tone_m = re.match(r"lines\[(\d+)\]\.tone:\s*(\w+)\s*vs\s*unknown", m)
                if tone_m and sb_scene.get("template") == "dialogue":
                    line_idx = int(tone_m.group(1))
                    props = sb_scene.get("props", {})
                    lines = props.get("lines", [])
                    if line_idx < len(lines):
                        if lines[line_idx].get("tone") != "neutral":
                            unneutral_flagged_tones += 1

            # Disputed kinetic_quote attribution
            has_attr_dispute = any(
                "attribution:" in m or "speaker:" in m or "attribution" in m for m in mismatches
            )
            if has_attr_dispute and sb_scene.get("template") == "kinetic_quote":
                props = sb_scene.get("props", {})
                if props.get("attribution_cast_id") is not None:
                    disputed_attributions_kept += 1

    # 2. R7 repairs on beats with quoted speech
    for repair in plan_report.get("rule_repairs", []):
        if repair.get("rule") == "R7":
            sc_id = repair.get("scene")
            sb_scene = scenes_by_id.get(sc_id)
            beat_i = sb_scene.get("beat_i") if sb_scene else None
            beat_text = beats_map.get(beat_i, "") if beat_i is not None else ""
            if beat_text and QUOTED.search(beat_text):
                r7_quoted_repairs += 1

    # 3. Year-like stats and Armchair count from storyboard
    for sc in storyboard.get("scenes", []):
        props = sc.get("props", {})
        props_str = json.dumps(props)
        armchair_count += props_str.count('"Armchair"')

        if sc.get("template") == "stat_callout":
            val = props.get("value")
            decimals = props.get("decimals")
            display_scale = props.get("display_scale")
            beat_i = sc.get("beat_i")
            beat_text = beats_map.get(beat_i, "") if beat_i is not None else ""
            if (
                isinstance(val, (int, float))
                and int(val) == val
                and 1000 <= int(val) <= 2100
                and decimals == 0
                and display_scale == "none"
            ):
                if re.search(rf"(?<![\d,.]){int(val)}(?![\d]|,\d)", beat_text):
                    year_stats += 1

    return {
        "job_dir": str(job_dir),
        "unneutral_flagged_tones": unneutral_flagged_tones,
        "disputed_attributions_kept": disputed_attributions_kept,
        "r7_quoted_repairs": r7_quoted_repairs,
        "year_stats": year_stats,
        "armchair_count": armchair_count,
        "passed": (
            unneutral_flagged_tones == 0
            and disputed_attributions_kept == 0
            and r7_quoted_repairs == 0
            and year_stats == 0
            and armchair_count == 0
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Wave E scene criteria across jobs")
    parser.add_argument("jobs", nargs="+", type=Path, help="Paths to rendered job directories")
    args = parser.parse_args()

    all_passed = True
    print("\n=======================================================")
    print("Wave E Scene Verification (E6)")
    print("=======================================================")
    print(
        f"{'Job':<25} | {'Tones (=0)':<10} | {'Attr (=0)':<10} | {'R7 Q (=0)':<10} | "
        f"{'Years (=0)':<10} | {'Armchairs (=0)':<14} | Status"
    )
    print("-" * 105)

    for job_path in args.jobs:
        if not job_path.is_dir() or not (job_path / "plan_report.json").exists():
            continue
        try:
            res = verify_job_scenes(job_path)
            st = "PASS" if res["passed"] else "FAIL"
            if not res["passed"]:
                all_passed = False
            job_name = job_path.name[:25]
            print(
                f"{job_name:<25} | {res['unneutral_flagged_tones']:<10} | "
                f"{res['disputed_attributions_kept']:<10} | {res['r7_quoted_repairs']:<10} | "
                f"{res['year_stats']:<10} | {res['armchair_count']:<14} | {st}"
            )
        except Exception as e:
            print(f"{job_path.name:<25} | ERROR: {e}")
            all_passed = False

    print("=" * 105)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()

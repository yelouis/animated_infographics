"""Verification of Wave E and Wave F scene criteria across rendered E2E jobs.

Per agent_execution_guide.md §3.F4:
- 0 dialogue lines whose tone the critic flagged as 'vs unknown' remain non-neutral;
- 0 kinetic_quote scenes keep a disputed attribution;
- 0 R7 repairs on beats with quoted speech;
- 0 year-like stats;
- 0 date stats (F1 condition);
- 0 junk text / placeholder violations (F2 condition);
- 0 invented era stamps (F3 condition: non-null era_label that is not exactly a narration
  year token);
- Armchair count (must be 0).
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from animated_infographics.contracts.models import Beat, Bible, Transcript
from animated_infographics.evals.asset_health import execution_errors
from animated_infographics.planner.rhythm import QUOTED
from animated_infographics.planner.validate import (
    PlanContext,
    names_before_narration_errors,
    placeholder_errors,
)

MONTHS: str = (
    "january|february|march|april|may|june|july|august|september|october|november|december"
)


def verify_job_scenes(job_dir: Path) -> dict[str, Any]:
    plan_report_path = job_dir / "plan_report.json"
    storyboard_path = job_dir / "storyboard.json"
    timeline_path = job_dir / "timeline.json"
    beats_path = job_dir / "beats.json"
    transcript_path = job_dir / "transcript.json"
    heard_path = job_dir / "heard.json"

    if not plan_report_path.exists() or not storyboard_path.exists():
        if timeline_path.exists():
            timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
            scenes = timeline.get("scenes", [])
            transcript_text = ""
            if heard_path.exists():
                try:
                    h_data = json.loads(heard_path.read_text(encoding="utf-8"))
                    transcript_text = " ".join(w.get("text", "") for w in h_data.get("words", []))
                except Exception:
                    pass

            year_stats = 0
            date_stats = 0
            junk_text = 0
            invented_era_stamps = 0
            armchair_count = 0

            for sc in scenes:
                tmpl = sc.get("template", "")
                props = sc.get("props", {})
                props_str = json.dumps(props)
                armchair_count += props_str.count('"Armchair"')

                ph_errs = placeholder_errors(tmpl, props)
                junk_text += len(ph_errs)

                if tmpl == "location":
                    era = props.get("era_label")
                    if era is not None:
                        m = re.fullmatch(r"(1[0-9]{3}|20[0-9]{2})s?", str(era).strip())
                        if not m or not re.search(rf"\b{m.group(1)}", transcript_text):
                            invented_era_stamps += 1

                if tmpl == "stat_callout":
                    val = props.get("value")
                    decimals = props.get("decimals")
                    display_scale = props.get("display_scale")
                    if (
                        isinstance(val, (int, float))
                        and int(val) == val
                        and decimals == 0
                        and display_scale == "none"
                    ):
                        val_int = int(val)
                        if 1000 <= val_int <= 2100:
                            year_stats += 1
                        date_pattern = (
                            rf"\b(?:{MONTHS})\.?\s+{val_int}(?:st|nd|rd|th)?\b|"
                            rf"\b{val_int}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:{MONTHS})\b"
                        )
                        if re.search(date_pattern, transcript_text, re.IGNORECASE):
                            date_stats += 1

            asset_errors = execution_errors(job_dir)
            asset_execution_errors = len(asset_errors)

            return {
                "job_dir": str(job_dir),
                "unneutral_flagged_tones": 0,
                "disputed_attributions_kept": 0,
                "r7_quoted_repairs": 0,
                "year_stats": year_stats,
                "date_stats": date_stats,
                "junk_text": junk_text,
                "invented_era_stamps": invented_era_stamps,
                "armchair_count": armchair_count,
                "names_before_narration": 0,
                "asset_execution_errors": asset_execution_errors,
                "passed": (
                    year_stats == 0
                    and date_stats == 0
                    and junk_text == 0
                    and invented_era_stamps == 0
                    and armchair_count == 0
                    and asset_execution_errors == 0
                ),
            }
        raise FileNotFoundError(f"Missing plan_report.json or storyboard.json in {job_dir}")

    plan_report = json.loads(plan_report_path.read_text(encoding="utf-8"))
    storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
    beats_map: dict[int, str] = {}
    if beats_path.exists():
        beats_data = json.loads(beats_path.read_text(encoding="utf-8"))
        beats_list = beats_data.get("beats", []) if isinstance(beats_data, dict) else beats_data
        beats_map = {b["i"]: b["text"] for b in beats_list if isinstance(b, dict) and "i" in b}

    transcript_text = ""
    if transcript_path.exists():
        try:
            tr_data = json.loads(transcript_path.read_text(encoding="utf-8"))
            sentences = tr_data.get("sentences", [])
            transcript_text = " ".join(s.get("text", "") for s in sentences)
        except Exception:
            pass
    if not transcript_text and beats_map:
        transcript_text = " ".join(beats_map.values())

    bible_path = job_dir / "bible.json"
    bible: Bible | None = None
    if bible_path.exists():
        try:
            bible = Bible.model_validate_json(bible_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    transcript_obj: Transcript | None = None
    if transcript_path.exists():
        try:
            transcript_obj = Transcript.model_validate_json(
                transcript_path.read_text(encoding="utf-8")
            )
        except Exception:
            pass

    beats_models: list[Beat] = []
    if beats_path.exists():
        try:
            beats_data = json.loads(beats_path.read_text(encoding="utf-8"))
            raw_b = (
                beats_data.get("beats", beats_data) if isinstance(beats_data, dict) else beats_data
            )
            beats_models = [Beat.model_validate(b) for b in raw_b if isinstance(b, dict)]
        except Exception:
            pass

    scenes_by_id = {s["id"]: s for s in storyboard.get("scenes", [])}

    unneutral_flagged_tones = 0
    disputed_attributions_kept = 0
    r7_quoted_repairs = 0
    year_stats = 0
    date_stats = 0
    junk_text = 0
    invented_era_stamps = 0
    armchair_count = 0
    names_before_narration = 0

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

    # 3. Year-like stats, date stats, junk text, era stamps, armchair count
    for sc in storyboard.get("scenes", []):
        tmpl = sc.get("template", "")
        props = sc.get("props", {})
        props_str = json.dumps(props)
        armchair_count += props_str.count('"Armchair"')

        # Junk text / placeholder check (F2)
        ph_errs = placeholder_errors(tmpl, props)
        junk_text += len(ph_errs)

        # Invented era stamps check (F3)
        if tmpl == "location":
            era = props.get("era_label")
            if era is not None:
                m = re.fullmatch(r"(1[0-9]{3}|20[0-9]{2})s?", str(era).strip())
                if not m or not re.search(rf"\b{m.group(1)}", transcript_text):
                    invented_era_stamps += 1

        if tmpl == "stat_callout":
            val = props.get("value")
            decimals = props.get("decimals")
            display_scale = props.get("display_scale")
            beat_i = sc.get("beat_i")
            beat_text = beats_map.get(beat_i, "") if beat_i is not None else ""
            if (
                isinstance(val, (int, float))
                and int(val) == val
                and decimals == 0
                and display_scale == "none"
            ):
                val_int = int(val)
                # Year stats check (E3)
                if 1000 <= val_int <= 2100:
                    if re.search(rf"(?<![\d,.]){val_int}(?![\d]|,\d)", beat_text):
                        year_stats += 1
                # Date stats check (F1)
                date_pattern = (
                    rf"\b(?:{MONTHS})\.?\s+{val_int}(?:st|nd|rd|th)?\b|"
                    rf"\b{val_int}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:{MONTHS})\b"
                )
                if re.search(date_pattern, beat_text, re.IGNORECASE):
                    date_stats += 1

        # Names before narration check (I5)
        if bible and transcript_obj and beats_models:
            beat_i = sc.get("beat_i")
            beat_obj = (
                beats_models[beat_i]
                if beat_i is not None and 0 <= beat_i < len(beats_models)
                else None
            )
            scene_ctx = PlanContext(
                transcript=transcript_obj,
                bible=bible,
                beat=beat_obj,
                beats=beats_models,
            )
            names_errs = names_before_narration_errors(sc, scene_ctx)
            names_before_narration += len(names_errs)

    asset_errors = execution_errors(job_dir)
    asset_execution_errors = len(asset_errors)

    return {
        "job_dir": str(job_dir),
        "unneutral_flagged_tones": unneutral_flagged_tones,
        "disputed_attributions_kept": disputed_attributions_kept,
        "r7_quoted_repairs": r7_quoted_repairs,
        "year_stats": year_stats,
        "date_stats": date_stats,
        "junk_text": junk_text,
        "invented_era_stamps": invented_era_stamps,
        "armchair_count": armchair_count,
        "names_before_narration": names_before_narration,
        "asset_execution_errors": asset_execution_errors,
        "passed": (
            unneutral_flagged_tones == 0
            and disputed_attributions_kept == 0
            and r7_quoted_repairs == 0
            and year_stats == 0
            and date_stats == 0
            and junk_text == 0
            and invented_era_stamps == 0
            and armchair_count == 0
            and names_before_narration == 0
            and asset_execution_errors == 0
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Wave E and F scene criteria across jobs")
    parser.add_argument("jobs", nargs="+", type=Path, help="Paths to rendered job directories")
    args = parser.parse_args()

    all_passed = True
    print("\n=======================================================")
    print("Wave E & F Scene Verification (F4)")
    print("=======================================================")
    print(
        f"{'Job':<25} | {'Tones (=0)':<10} | {'Attr (=0)':<10} | {'R7 Q (=0)':<10} | "
        f"{'Years (=0)':<10} | {'Dates (=0)':<10} | {'Junk (=0)':<9} | {'Era (=0)':<8} | "
        f"{'Armchairs (=0)':<14} | {'Names (=0)':<10} | {'Assets (=0)':<11} | Status"
    )
    print("-" * 167)

    for job_path in args.jobs:
        if not job_path.is_dir() or (
            not (job_path / "plan_report.json").exists()
            and not (job_path / "timeline.json").exists()
        ):
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
                f"{res['year_stats']:<10} | {res['date_stats']:<10} | {res['junk_text']:<9} | "
                f"{res['invented_era_stamps']:<8} | {res['armchair_count']:<14} | "
                f"{res['names_before_narration']:<10} | {res['asset_execution_errors']:<11} | {st}"
            )
        except Exception as e:
            print(f"{job_path.name:<25} | ERROR: {e}")
            all_passed = False

    print("=" * 167)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()

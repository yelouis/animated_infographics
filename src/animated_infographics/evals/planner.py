"""Offline planner evaluation running voice -> bible -> segment -> storyboard on fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from animated_infographics.audio.narrate import build_sentence_list
from animated_infographics.contracts.models import (
    Transcript,
    TranscriptSentence,
    TranscriptWord,
)
from animated_infographics.ingest import ingest
from animated_infographics.planner.bible import plan_bible
from animated_infographics.planner.geo import Gazetteer, load_country_bboxes
from animated_infographics.planner.llm import OllamaBackend
from animated_infographics.planner.props import plan_storyboard
from animated_infographics.planner.segment import plan_beats
from animated_infographics.planner.validate import PlanContext, validate_plan
from animated_infographics.planner.voice import select_voice


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _make_transcript_from_script(script_path: Path) -> Transcript:
    ing = ingest(script_path, None)
    sents = build_sentence_list(ing)
    words: list[TranscriptWord] = []
    transcript_sents: list[TranscriptSentence] = []
    ms = 0
    w_idx = 0

    for i, (text, p_idx, is_t) in enumerate(sents):
        toks = text.split()
        w_start = ms
        s_w_start = w_idx
        for t in toks:
            words.append(
                TranscriptWord(
                    i=w_idx,
                    sentence_i=i,
                    text=t,
                    start_ms=ms,
                    end_ms=ms + 200,
                )
            )
            w_idx += 1
            ms += 250
        transcript_sents.append(
            TranscriptSentence(
                i=i,
                text=text,
                start_ms=w_start,
                end_ms=ms,
                word_start=s_w_start,
                word_end=w_idx,
                paragraph_i=p_idx,
                is_title=is_t,
            )
        )
        ms += 250

    return Transcript(
        schema_version=1,
        source="tts",
        audio_path="simulated.wav",
        duration_ms=ms + 500,
        words=words,
        sentences=transcript_sents,
    )


def run_eval(
    fixtures: list[str],
    no_llm_cache: bool = True,
    out_dir: Path | None = None,
) -> int:
    repo_root = Path(__file__).resolve().parents[3]
    fixtures_dir = repo_root / "fixtures"
    prompts_dir = repo_root / "src" / "animated_infographics" / "planner" / "prompts"

    cities_path = repo_root / "data" / "vendor" / "cities15000.txt"
    country_info_path = repo_root / "data" / "vendor" / "countryInfo.txt"
    bboxes_path = repo_root / "data" / "geo" / "country_bboxes.json"

    print("Loading gazetteer and country bounding boxes...")
    gazetteer = Gazetteer.load(cities_path, country_info_path)
    bboxes = load_country_bboxes(bboxes_path)

    prompt_files = ["voice.md", "bible.md", "segment.md", "select.md", "props.md"]
    prompt_shas: dict[str, str] = {}
    for pf in prompt_files:
        p_path = prompts_dir / pf
        prompt_shas[pf] = _sha256_file(p_path) if p_path.exists() else "missing"

    results: list[dict[str, Any]] = []
    all_passed = True

    for fix_name in fixtures:
        print("\n==================================================")
        print(f"Running planner eval on fixture: {fix_name}")
        print("==================================================")

        script_path = fixtures_dir / "scripts" / f"{fix_name}.txt"
        expected_path = fixtures_dir / "expected" / f"{fix_name}.json"
        if not script_path.exists():
            print(f"Error: script {script_path} not found")
            return 1
        expected: dict[str, Any] = {}
        if expected_path.exists():
            expected = json.loads(expected_path.read_text(encoding="utf-8"))

        backend = OllamaBackend(no_cache=no_llm_cache)
        t0 = time.perf_counter()

        # 1. Ingest & Voice
        ing = ingest(script_path, None)
        body = "\n\n".join(ing.paragraphs or [])
        voice = select_voice(ing.title, body, flag_voice=None, backend=backend)
        print(f"Voice decision: voice={voice.voice}, reason={voice.reason}")

        # 2. Transcript
        transcript = _make_transcript_from_script(script_path)

        # 3. Bible
        bible = plan_bible(transcript, voice, backend, gazetteer, bboxes)
        print(
            f"Bible: {len(bible.cast)} cast, {len(bible.places)} places, "
            f"{len(bible.set_pieces)} set pieces"
        )

        # 4. Segment
        beats_obj = plan_beats(transcript, backend)
        beats = beats_obj.beats
        print(f"Segment: {len(beats)} beats")

        # 5. Storyboard
        storyboard, report = plan_storyboard(transcript, beats, bible, backend)
        wall_time = time.perf_counter() - t0
        print(f"Storyboard: {len(storyboard.scenes)} scenes planned in {wall_time:.1f}s")

        # 6. Re-validation
        ctx = PlanContext(transcript=transcript, bible=bible, beats=beats)
        violations = validate_plan(bible, storyboard, ctx)
        print(f"Independent validation violations: {len(violations)}")

        # Metrics
        n_scenes = len(storyboard.scenes)
        templates_used = [s.template for s in storyboard.scenes]
        distinct_templates = len(set(templates_used))

        l0_count = sum(1 for s in report.scenes if s.fallback_level == 0)
        l1_count = sum(1 for s in report.scenes if s.fallback_level == 1)
        l2_count = sum(1 for s in report.scenes if s.fallback_level == 2)
        l2_pct = (l2_count / n_scenes * 100.0) if n_scenes > 0 else 0.0

        repairs_by_rule: dict[str, int] = {}
        for rep in report.rule_repairs:
            repairs_by_rule[rep.rule] = repairs_by_rule.get(rep.rule, 0) + 1

        val_err_hist: dict[str, int] = {}
        for sc_rep in report.scenes:
            for err in sc_rep.errors:
                key = err.split(":")[0] if ":" in err else err[:30]
                val_err_hist[key] = val_err_hist.get(key, 0) + 1

        # Check bars
        expected_voice = expected.get("voice")
        expected_reason = expected.get("voice_reason")
        voice_match = voice.voice == expected_voice and voice.reason == expected_reason

        min_distinct = 5 if fix_name == "molasses_flood" else 7
        distinct_bar_pass = distinct_templates >= min_distinct
        l2_bar_pass = l2_pct <= 15.0
        violations_pass = len(violations) == 0
        time_bar_pass = True
        if fix_name == "story_recipe_box":
            time_bar_pass = wall_time <= 240.0

        fixture_pass = (
            voice_match and distinct_bar_pass and l2_bar_pass and violations_pass and time_bar_pass
        )
        if not fixture_pass:
            all_passed = False

        fix_res: dict[str, Any] = {
            "name": fix_name,
            "voice": voice.model_dump(),
            "expected_voice": expected_voice,
            "expected_reason": expected_reason,
            "voice_match": voice_match,
            "n_scenes": n_scenes,
            "distinct_templates": distinct_templates,
            "min_distinct": min_distinct,
            "distinct_bar_pass": distinct_bar_pass,
            "l0_count": l0_count,
            "l1_count": l1_count,
            "l2_count": l2_count,
            "l2_pct": l2_pct,
            "l2_bar_pass": l2_bar_pass,
            "violations": violations,
            "violations_pass": violations_pass,
            "repairs_by_rule": repairs_by_rule,
            "val_err_hist": val_err_hist,
            "llm_calls": report.llm_calls,
            "llm_cache_hits": report.llm_cache_hits,
            "wall_time": wall_time,
            "time_bar_pass": time_bar_pass,
            "passed": fixture_pass,
        }
        results.append(fix_res)

    # Write Markdown report
    if out_dir is None:
        out_dir = repo_root / "docs" / "evals"
    out_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    report_file = out_dir / f"planner_{today}.md"

    md_lines: list[str] = [
        f"# Planner Evaluation Report ({today})",
        "",
        "- **Model**: `gemma4:26b`",
        f"- **Cache Mode**: `{'--no-llm-cache (cold)' if no_llm_cache else 'warm cache'}`",
        f"- **Timestamp**: `{datetime.now(UTC).isoformat()}`",
        "",
        "## Prompt Hashes (SHA-256)",
        "",
        "| Prompt | SHA-256 |",
        "|---|---|",
    ]
    for pf, sha in prompt_shas.items():
        md_lines.append(f"| `{pf}` | `{sha}` |")

    table_header = (
        "| Fixture | Voice Match | Scenes | Distinct (Bar) | L2 % (≤15%) | "
        "Violations (=0) | LLM Calls | Wall Time | Status |"
    )
    table_sep = "|---|---|---|---|---|---|---|---|---|"
    md_lines.extend(["", "## Summary Table", "", table_header, table_sep])

    for r in results:
        v_str = "PASS" if r["voice_match"] else "FAIL"
        d_str = f"{r['distinct_templates']} (≥{r['min_distinct']})"
        l2_str = f"{r['l2_pct']:.1f}% ({r['l2_count']}/{r['n_scenes']})"
        viol_str = str(len(r["violations"]))
        status_str = "**PASS**" if r["passed"] else "**FAIL**"
        time_str = f"{r['wall_time']:.1f}s"
        row = (
            f"| `{r['name']}` | {v_str} | {r['n_scenes']} | {d_str} | {l2_str} | "
            f"{viol_str} | {r['llm_calls']} | {time_str} | {status_str} |"
        )
        md_lines.append(row)

    md_lines.extend(["", "## Fixture Details", ""])

    for r in results:
        v_reason = r["voice"]["reason"]
        v_ev = r["voice"]["evidence"]
        v_voice = r["voice"]["voice"]
        voice_line = f"- **Voice**: `{v_voice}` (reason: `{v_reason}`, evidence: `{v_ev}`)"
        fb_line = (
            f"- **Fallback Levels**: L0={r['l0_count']}, L1={r['l1_count']}, "
            f"L2={r['l2_count']} ({r['l2_pct']:.1f}%, Bar: ≤15%)"
        )
        md_lines.extend(
            [
                f"### `{r['name']}`",
                "",
                voice_line,
                f"  - Expected: `{r['expected_voice']}` (`{r['expected_reason']}`)",
                f"  - Match: {'YES' if r['voice_match'] else 'NO'}",
                f"- **Scene Count**: {r['n_scenes']}",
                f"- **Distinct Templates**: {r['distinct_templates']} (Bar: ≥{r['min_distinct']})",
                fb_line,
                f"- **Rule Repairs**: {json.dumps(r['repairs_by_rule'])}",
                f"- **Validation Violations**: {len(r['violations'])}",
                f"- **LLM Calls**: {r['llm_calls']} (cache hits: {r['llm_cache_hits']})",
                f"- **Wall Time**: {r['wall_time']:.1f}s",
                "",
            ]
        )
        if r["violations"]:
            md_lines.append("#### Violations List")
            for v in r["violations"]:
                md_lines.append(f"- `{v}`")
            md_lines.append("")

    report_content = "\n".join(md_lines) + "\n"
    report_file.write_text(report_content, encoding="utf-8")
    print(f"\nReport written to: {report_file}")

    return 0 if all_passed else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Planner evaluation on fixtures")
    parser.add_argument(
        "--fixture",
        choices=["molasses_flood", "emu_war", "story_recipe_box", "story_room_12", "all"],
        default="all",
        help="Fixture to evaluate (default: all)",
    )
    parser.add_argument(
        "--no-llm-cache",
        action="store_true",
        default=True,
        help="Bypass LLM cache reads (default: True for eval)",
    )
    parser.add_argument(
        "--allow-cache",
        action="store_true",
        help="Allow warm LLM cache reads (overrides --no-llm-cache)",
    )
    args = parser.parse_args()

    no_cache = not args.allow_cache

    if args.fixture == "all":
        fixtures = ["molasses_flood", "emu_war", "story_recipe_box", "story_room_12"]
    else:
        fixtures = [args.fixture]

    exit_code = run_eval(fixtures, no_llm_cache=no_cache)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

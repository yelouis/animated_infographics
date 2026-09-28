"""Offline planner evaluation running voice -> bible -> segment -> storyboard on fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from animated_infographics.audio.narrate import build_sentence_list
from animated_infographics.contracts.models import (
    AvatarConfig,
    Beat,
    Bible,
    CastMember,
    DialogueScene,
    KineticQuoteScene,
    Scene,
    TextThreadScene,
    Transcript,
    TranscriptSentence,
    TranscriptWord,
)
from animated_infographics.contracts.templates import (
    DialogueLine,
    DialogueProps,
    KineticQuoteProps,
    TextMessage,
    TextThreadProps,
)
from animated_infographics.evals.text_audit import audit_storyboards
from animated_infographics.ingest import ingest
from animated_infographics.planner.bible import plan_bible
from animated_infographics.planner.critic import (
    build_critic_request,
    critic_mismatches,
    validate_critic_answer,
)
from animated_infographics.planner.geo import Gazetteer, load_country_bboxes
from animated_infographics.planner.llm import LLMBackend, OllamaBackend, run_with_retries
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


def run_critic_regression_set(backend: LLMBackend, attempt_offset: int = 0) -> list[dict[str, Any]]:
    """Run the critic regression set from design_planner.md §11."""
    avatar = AvatarConfig(
        skin=1,
        hair_style="short",
        hair_color="black",
        facial_hair="none",
        headwear="none",
        glasses=False,
        age="adult",
    )
    bible = Bible(
        schema_version=1,
        title="Recipe Box",
        logline="Grandma's recipe box.",
        genre="personal_story",
        cast=[
            CastMember(
                id="c1",
                name="Me",
                role="narrator",
                is_narrator=True,
                color_slot=1,
                avatar=avatar,
            ),
            CastMember(
                id="c2",
                name="Danny",
                role="brother",
                is_narrator=False,
                color_slot=2,
                avatar=avatar,
            ),
            CastMember(
                id="c3",
                name="Walt",
                role="friend",
                is_narrator=False,
                color_slot=3,
                avatar=avatar,
            ),
            CastMember(
                id="c4",
                name="Deb",
                role="mom",
                is_narrator=False,
                color_slot=4,
                avatar=avatar,
            ),
        ],
    )

    cases_file = Path("tests/data/critic_text_thread_cases.json")
    if not cases_file.exists():
        cases_file = (
            Path(__file__).resolve().parents[3] / "tests" / "data" / "critic_text_thread_cases.json"
        )
    h_data = next(
        c for c in json.loads(cases_file.read_text(encoding="utf-8"))["cases"] if c["case"] == "H"
    )

    h_bible = Bible(
        schema_version=1,
        title="Recipe Box",
        logline="Grandma's recipe box.",
        genre="personal_story",
        cast=[
            CastMember(
                id=c["id"],
                name=c["name"],
                role=c["role"],
                is_narrator=c["is_narrator"],
                color_slot=i + 1,
                avatar=avatar,
            )
            for i, c in enumerate(h_data["cast"])
        ],
    )
    h_scene = TextThreadScene(
        id=h_data["scene_id"],
        beat_i=11,
        template="text_thread",
        props=TextThreadProps(
            contact_name=h_data["props"]["contact_name"],
            contact_cast_id=h_data["props"]["contact_cast_id"],
            messages=[TextMessage.model_validate(m) for m in h_data["props"]["messages"]],
        ),
    )

    cases = [
        {
            "id": "A",
            "name": "Danny's text 'Who is Walter Lindqvist…' as kinetic_quote",
            "scene": KineticQuoteScene(
                id="s012",
                beat_i=12,
                template="kinetic_quote",
                props=KineticQuoteProps(
                    text="Who is Walter Lindqvist and why did he write to Grandma 60 times?",
                    emphasis=[],
                    attribution_cast_id="c1",
                ),
            ),
            "before_prev_beat": Beat(
                i=10,
                text="Last spring, Danny finally sold the house.",
                start_ms=53000,
                end_ms=55925,
                word_start=135,
                word_end=142,
            ),
            "prev_beat": Beat(
                i=11,
                text=(
                    "While clearing the attic, he found a shoebox of letters and texted me a photo:"
                ),
                start_ms=55925,
                end_ms=60800,
                word_start=142,
                word_end=157,
            ),
            "beat": Beat(
                i=12,
                text='"Who is Walter Lindqvist and why did he write to Grandma 60 times?"',
                start_ms=60800,
                end_ms=65800,
                word_start=157,
                word_end=170,
            ),
            "next_beat": Beat(
                i=13,
                text=(
                    "The return address was in Thunder Bay, Ontario, about 190 miles up the shore."
                ),
                start_ms=65800,
                end_ms=72525,
                word_start=170,
                word_end=184,
            ),
            "expected": "mismatch",
        },
        {
            "id": "B",
            "name": "'Rose?' as dialogue line with angry tone",
            "scene": DialogueScene(
                id="s015",
                beat_i=15,
                template="dialogue",
                props=DialogueProps(
                    lines=[
                        DialogueLine(cast_id="c1", text="Rose?", tone="angry"),
                    ]
                ),
            ),
            "before_prev_beat": Beat(
                i=13,
                text=(
                    "The return address was in Thunder Bay, Ontario, about 190 miles up the shore."
                ),
                start_ms=65800,
                end_ms=72525,
                word_start=170,
                word_end=184,
            ),
            "prev_beat": Beat(
                i=14,
                text="I called the number I found online, expecting nothing.",
                start_ms=72525,
                end_ms=76425,
                word_start=184,
                word_end=193,
            ),
            "beat": Beat(
                i=15,
                text=(
                    "A man answered, and when I said Rose's name, "
                    "he was quiet for a long time. Then he said,"
                ),
                start_ms=76425,
                end_ms=82900,
                word_start=193,
                word_end=212,
            ),
            "next_beat": Beat(
                i=16,
                text='"I\'ve been waiting for someone to call about the pie."',
                start_ms=82900,
                end_ms=86325,
                word_start=212,
                word_end=222,
            ),
            "expected": "mismatch",
        },
        {
            "id": "B'",
            "name": "'Rose?' as dialogue line with neutral tone",
            "scene": DialogueScene(
                id="s015",
                beat_i=15,
                template="dialogue",
                props=DialogueProps(
                    lines=[
                        DialogueLine(cast_id="c1", text="Rose?", tone="neutral"),
                    ]
                ),
            ),
            "before_prev_beat": Beat(
                i=13,
                text=(
                    "The return address was in Thunder Bay, Ontario, about 190 miles up the shore."
                ),
                start_ms=65800,
                end_ms=72525,
                word_start=170,
                word_end=184,
            ),
            "prev_beat": Beat(
                i=14,
                text="I called the number I found online, expecting nothing.",
                start_ms=72525,
                end_ms=76425,
                word_start=184,
                word_end=193,
            ),
            "beat": Beat(
                i=15,
                text=(
                    "A man answered, and when I said Rose's name, "
                    "he was quiet for a long time. Then he said,"
                ),
                start_ms=76425,
                end_ms=82900,
                word_start=193,
                word_end=212,
            ),
            "next_beat": Beat(
                i=16,
                text='"I\'ve been waiting for someone to call about the pie."',
                start_ms=82900,
                end_ms=86325,
                word_start=212,
                word_end=222,
            ),
            "expected": "agree",
        },
        {
            "id": "C",
            "name": "'I\\'ve been waiting for someone to call about the pie.' with attribution c3",
            "scene": KineticQuoteScene(
                id="s016",
                beat_i=16,
                template="kinetic_quote",
                props=KineticQuoteProps(
                    text="I've been waiting for someone to call about the pie.",
                    emphasis=[],
                    attribution_cast_id="c3",
                ),
            ),
            "before_prev_beat": Beat(
                i=14,
                text="I called the number I found online, expecting nothing.",
                start_ms=72525,
                end_ms=76425,
                word_start=184,
                word_end=193,
            ),
            "prev_beat": Beat(
                i=15,
                text=(
                    "A man answered, and when I said Rose's name, "
                    "he was quiet for a long time. Then he said,"
                ),
                start_ms=76425,
                end_ms=82900,
                word_start=193,
                word_end=212,
            ),
            "beat": Beat(
                i=16,
                text='"I\'ve been waiting for someone to call about the pie."',
                start_ms=82900,
                end_ms=86325,
                word_start=212,
                word_end=222,
            ),
            "next_beat": Beat(
                i=17,
                text="I drove up that weekend.",
                start_ms=86325,
                end_ms=88725,
                word_start=222,
                word_end=227,
            ),
            "expected": "agree",
        },
        {
            "id": "E",
            "name": "Quote with speaker named in sentence before: Danny found letters",
            "bible": Bible(
                schema_version=1,
                title="Recipe Box",
                logline="Grandma's recipe box.",
                genre="personal_story",
                cast=[
                    CastMember(
                        id="c1",
                        name="Me",
                        role="narrator",
                        is_narrator=True,
                        color_slot=1,
                        avatar=avatar,
                    ),
                    CastMember(
                        id="c2",
                        name="Grandma Rose",
                        role="character",
                        is_narrator=False,
                        color_slot=2,
                        avatar=avatar,
                    ),
                    CastMember(
                        id="c3",
                        name="Danny",
                        role="character",
                        is_narrator=False,
                        color_slot=3,
                        avatar=avatar,
                    ),
                    CastMember(
                        id="c4",
                        name="Walt",
                        role="character",
                        is_narrator=False,
                        color_slot=4,
                        avatar=avatar,
                    ),
                ],
            ),
            "scene": KineticQuoteScene(
                id="s012",
                beat_i=12,
                template="kinetic_quote",
                props=KineticQuoteProps(
                    text="Who is Walter Lindqvist and why did he write to Grandma 60 times?",
                    emphasis=[],
                    attribution_cast_id="c1",
                ),
            ),
            "before_prev_beat": Beat(
                i=10,
                text="Last spring, Danny finally sold the house.",
                start_ms=53000,
                end_ms=55925,
                word_start=135,
                word_end=142,
            ),
            "prev_beat": Beat(
                i=11,
                text=(
                    "While clearing the attic, he found a shoebox of letters and texted me a photo:"
                ),
                start_ms=55925,
                end_ms=60800,
                word_start=142,
                word_end=157,
            ),
            "beat": Beat(
                i=12,
                text='"Who is Walter Lindqvist and why did he write to Grandma 60 times?"',
                start_ms=60800,
                end_ms=65800,
                word_start=157,
                word_end=170,
            ),
            "next_beat": Beat(
                i=13,
                text=(
                    "The return address was in Thunder Bay, Ontario, about 190 miles up the shore."
                ),
                start_ms=65800,
                end_ms=72525,
                word_start=170,
                word_end=184,
            ),
            "expected": "mismatch",
        },
        {
            "id": "H",
            "name": "Text thread with consecutive 'them' messages (Danny)",
            "bible": h_bible,
            "scene": h_scene,
            "before_prev_beat": Beat(
                i=9,
                text=h_data["beats"]["before_previous"],
                start_ms=0,
                end_ms=1000,
                word_start=0,
                word_end=10,
            ),
            "prev_beat": Beat(
                i=10,
                text=h_data["beats"]["previous"],
                start_ms=1000,
                end_ms=2000,
                word_start=10,
                word_end=20,
            ),
            "beat": Beat(
                i=11,
                text=h_data["beats"]["current"],
                start_ms=2000,
                end_ms=3000,
                word_start=20,
                word_end=30,
            ),
            "next_beat": Beat(
                i=12,
                text=h_data["beats"]["next"],
                start_ms=3000,
                end_ms=4000,
                word_start=30,
                word_end=40,
            ),
            "expected": "agree",
        },
    ]

    results: list[dict[str, Any]] = []
    print("\n==================================================")
    print("Running Critic Regression Set (§11)")
    print("==================================================")

    for c in cases:
        case_bible = cast(Bible, c.get("bible", bible))
        scene = cast(Scene, c["scene"])
        beat = cast(Beat, c["beat"])
        prev_beat = cast(Beat | None, c.get("prev_beat"))
        before_prev_beat = cast(Beat | None, c.get("before_prev_beat"))
        next_beat = cast(Beat | None, c.get("next_beat"))
        system, user, schema = build_critic_request(
            scene,
            beat,
            prev_beat,
            next_beat,
            case_bible,
            before_prev_beat=before_prev_beat,
        )

        def validate_c(raw: dict[str, Any], sc: Scene = scene) -> tuple[dict[str, Any], list[str]]:
            return validate_critic_answer(sc, raw)

        raw_ans, _ = run_with_retries(
            backend,
            stage="critic",
            system=system,
            user=user,
            schema=schema,
            validate=validate_c,
            max_attempts=3,
            attempt_offset=attempt_offset,
            num_predict=256,
            temperature=0.0,
        )

        if raw_ans is None:
            actual = "unavailable"
            mismatches: list[str] = []
        else:
            mismatches = critic_mismatches(scene, raw_ans, case_bible)
            actual = "mismatch" if mismatches else "agree"

        passed = actual == c["expected"]
        status_tag = "PASS" if passed else "FAIL"
        print(f"Case {c['id']}: {c['name']} -> {actual} (expected {c['expected']}) [{status_tag}]")
        if mismatches:
            print(f"  Mismatches: {mismatches}")

        results.append(
            {
                "id": c["id"],
                "name": c["name"],
                "expected": c["expected"],
                "actual": actual,
                "mismatches": mismatches,
                "raw_answer": raw_ans,
                "passed": passed,
            }
        )

    return results


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
    saved_storyboard_paths: list[Path] = []
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

        # Save storyboard.json for independent audit
        storyboard_dir = repo_root / "artifacts" / "evals" / "planner" / fix_name
        storyboard_dir.mkdir(parents=True, exist_ok=True)
        sb_path = storyboard_dir / "storyboard.json"
        sb_path.write_text(storyboard.model_dump_json(indent=2), encoding="utf-8")
        saved_storyboard_paths.append(sb_path)

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

        critic_calls = 0
        critic_mismatches = 0
        critic_changed = 0
        for s in report.scenes:
            if s.critic is not None:
                if s.critic.status in ("agree", "mismatch_retried", "unavailable"):
                    critic_calls += 1
                critic_mismatches += len(s.critic.mismatches)
                if s.critic.changed:
                    critic_changed += 1

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
            "critic_calls": critic_calls,
            "critic_mismatches": critic_mismatches,
            "critic_changed": critic_changed,
            "llm_calls": report.llm_calls,
            "llm_cache_hits": report.llm_cache_hits,
            "wall_time": wall_time,
            "time_bar_pass": time_bar_pass,
            "passed": fixture_pass,
        }
        results.append(fix_res)

    # 7. Run Text Audit (§6 item 7)
    text_audit_result = audit_storyboards(saved_storyboard_paths, dedup=False)
    if (
        text_audit_result["contains_newline_count"] > 0
        or text_audit_result["completeness_failures_count"] > 0
    ):
        all_passed = False

    # 8. Run Critic Regression Set (§11)
    eval_backend = OllamaBackend(no_cache=no_llm_cache)
    regression_results = run_critic_regression_set(eval_backend)
    if not all(cr["passed"] for cr in regression_results):
        all_passed = False

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
                (
                    f"- **Critic**: {r['critic_calls']} calls, "
                    f"{r['critic_mismatches']} mismatches, {r['critic_changed']} changed"
                ),
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

    # Text Audit section in report
    audit_passed = (
        text_audit_result["contains_newline_count"] == 0
        and text_audit_result["completeness_failures_count"] == 0
    )
    at_max_with_punct = (
        text_audit_result["at_max_length_count"] - text_audit_result["at_max_length_no_punct_count"]
    )
    md_lines.extend(
        [
            "## Text Audit (§6 item 7)",
            "",
            f"- **Total Strings Audited**: {text_audit_result['total_strings']}",
            f"- **At maxLength (Total)**: {text_audit_result['at_max_length_count']}",
            f"- **At maxLength with Terminal Punctuation**: {at_max_with_punct}",
            (
                "- **At maxLength WITHOUT Terminal Punctuation**: "
                f"{text_audit_result['at_max_length_no_punct_count']}"
            ),
            (
                "- **Strings Containing Newlines**: "
                f"{text_audit_result['contains_newline_count']} (Bar: 0)"
            ),
            (
                "- **Completeness Failures**: "
                f"{text_audit_result['completeness_failures_count']} (Bar: 0)"
            ),
            f"- **Text Audit Status**: {'**PASS**' if audit_passed else '**FAIL**'}",
            "",
        ]
    )
    if text_audit_result["contains_newline_count"] > 0:
        md_lines.append("### Strings Containing Newlines")
        for item in text_audit_result["contains_newline"]:
            md_lines.append(f"- `{item['template']}` {item['path']}: {repr(item['value'])}")
        md_lines.append("")

    if text_audit_result["completeness_failures_count"] > 0:
        md_lines.append("### Completeness Failures")
        for item in text_audit_result["completeness_failures"]:
            md_lines.append(f"- `{item['template']}` {item['path']}: {repr(item['value'])}")
        md_lines.append("")

    if text_audit_result["at_max_length_no_punct_count"] > 0:
        md_lines.append("### At maxLength Without Terminal Punctuation")
        for item in text_audit_result["at_max_length_no_punct"]:
            tmpl = item["template"]
            p = item["path"]
            ml = item["max_length"]
            v = repr(item["value"])
            md_lines.append(f"- `{tmpl}` {p} (limit {ml}): {v}")
        md_lines.append("")

    # Critic Regression Set section in report
    reg_passed_count = sum(1 for cr in regression_results if cr["passed"])
    md_lines.extend(
        [
            "## Critic Regression Set (§11)",
            "",
            (
                f"- **Score**: {reg_passed_count}/{len(regression_results)} "
                f"(Bar: {len(regression_results)}/{len(regression_results)})"
            ),
            "",
            "| Case | Name | Expected | Actual | Status |",
            "|---|---|---|---|---|",
        ]
    )
    for cr in regression_results:
        st = "**PASS**" if cr["passed"] else "**FAIL**"
        md_lines.append(
            f"| `{cr['id']}` | {cr['name']} | `{cr['expected']}` | `{cr['actual']}` | {st} |"
        )
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

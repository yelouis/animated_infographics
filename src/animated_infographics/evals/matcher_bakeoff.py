"""Matcher bake-off evaluation harness.

Runs presentation replay bake-off over a frozen corpus of 8 jobs across matchers:
bm25, anticipate, llm.
Per design_presentation_simulation.md §6.6.3 and agent_execution_guide.md §1.3 (J1).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import statistics
import sys
from pathlib import Path
from typing import Any

from animated_infographics.contracts.models import (
    Transcript,
    TranscriptSentence,
    TranscriptWord,
)
from animated_infographics.contracts.performance import PerformancePlan
from animated_infographics.contracts.playback import PlaybackPlan
from animated_infographics.errors import ValidationFailed
from animated_infographics.jobs import Job, RunContext
from animated_infographics.presentation.compose import run_compose_stage
from animated_infographics.presentation.follow import run_follow_stage
from animated_infographics.presentation.score import (
    compute_presentation_score,
    evaluate_presentation_bars,
    format_bar_str,
)

HASH_FILES = [
    "deck.json",
    "tree.json",
    "performance.json",
    "speak_timing.json",
    "heard.json",
]


def verify_corpus(corpus_dir: Path) -> dict[str, Any]:
    """Verify integrity of frozen corpus via corpus.json SHA-256 hashes.

    Exits 1 immediately if corpus.json is missing, any file is missing,
    or any hash mismatches.
    """
    corpus_json_path = corpus_dir / "corpus.json"
    if not corpus_json_path.is_file():
        print(f"[-] Corpus error: {corpus_json_path} does not exist", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(corpus_json_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[-] Corpus error: failed to parse {corpus_json_path}: {e}", file=sys.stderr)
        sys.exit(1)

    jobs = data.get("jobs", [])
    if not jobs:
        print("[-] Corpus error: no jobs defined in corpus.json", file=sys.stderr)
        sys.exit(1)

    for job in jobs:
        job_id = job.get("job_id")
        if not job_id:
            print("[-] Corpus error: job missing job_id", file=sys.stderr)
            sys.exit(1)
        job_dir = corpus_dir / job_id
        if not job_dir.is_dir():
            print(f"[-] Corpus error: job directory {job_dir} missing", file=sys.stderr)
            sys.exit(1)

        hashes = job.get("hashes", {})
        for fname in HASH_FILES:
            expected_hash = hashes.get(fname)
            if not expected_hash:
                print(
                    f"[-] Corpus error: missing hash for {job_id}/{fname}",
                    file=sys.stderr,
                )
                sys.exit(1)
            fpath = job_dir / fname
            if not fpath.is_file():
                print(f"[-] Corpus error: missing file {fpath}", file=sys.stderr)
                sys.exit(1)
            actual_hash = hashlib.sha256(fpath.read_bytes()).hexdigest()
            if actual_hash != expected_hash:
                print(
                    f"[-] Corpus hash mismatch for {job_id}/{fname}: "
                    f"expected {expected_hash}, got {actual_hash}",
                    file=sys.stderr,
                )
                sys.exit(1)

    return data


def synthesize_perfect_hearing(job_dir: Path) -> None:
    """Synthesize perfect heard.json from performance.json and speak_timing.json.

    Feeds performance text spread evenly across speak_timing spans to isolate
    matcher error from ASR error.
    """
    perf_path = job_dir / "performance.json"
    timing_path = job_dir / "speak_timing.json"

    if not perf_path.is_file():
        raise FileNotFoundError(f"performance.json missing in {job_dir}")
    if not timing_path.is_file():
        raise FileNotFoundError(f"speak_timing.json missing in {job_dir}")

    perf = PerformancePlan.model_validate_json(perf_path.read_text(encoding="utf-8"))
    timings = json.loads(timing_path.read_text(encoding="utf-8"))

    timing_by_sent_i = {int(item["sentence_i"]): item for item in timings}

    all_words: list[TranscriptWord] = []
    all_sentences: list[TranscriptSentence] = []
    current_word_i = 0
    last_word_end = 0

    for sent_idx, sent in enumerate(perf.sentences):
        timing = timing_by_sent_i.get(sent_idx)
        if timing is None:
            continue
        s_start = max(int(timing["start_ms"]), last_word_end)
        s_end = max(int(timing["end_ms"]), s_start + 1)
        words_text = sent.text.split()
        n = len(words_text)
        sent_word_start = current_word_i
        if n > 0:
            dur = s_end - s_start
            if dur < n:
                s_end = s_start + n
                dur = n
            for k, wt in enumerate(words_text):
                w_s = s_start + int(round(k * dur / n))
                w_e = s_start + int(round((k + 1) * dur / n))
                if w_s < last_word_end:
                    w_s = last_word_end
                if w_e <= w_s:
                    w_e = w_s + 1
                last_word_end = w_e
                all_words.append(
                    TranscriptWord(
                        i=current_word_i,
                        text=wt,
                        start_ms=w_s,
                        end_ms=w_e,
                        sentence_i=sent_idx,
                    )
                )
                current_word_i += 1
            sent_word_end = current_word_i
        else:
            sent_word_end = sent_word_start

        all_sentences.append(
            TranscriptSentence(
                i=sent_idx,
                text=sent.text,
                start_ms=s_start,
                end_ms=max(s_end, last_word_end),
                word_start=sent_word_start,
                word_end=sent_word_end,
                paragraph_i=0,
                is_title=False,
            )
        )

    duration_ms = max(last_word_end, all_sentences[-1].end_ms if all_sentences else 0)
    transcript = Transcript(
        schema_version=1,
        source="asr",
        audio_path="audio/narration.wav",
        duration_ms=duration_ms,
        words=all_words,
        sentences=all_sentences,
    )
    (job_dir / "heard.json").write_text(
        transcript.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )


def run_bakeoff(
    corpus_dir: Path,
    matcher: str,
    out_dir: Path,
    hearing: str = "asr",
    no_llm_cache: bool = False,
) -> tuple[int, list[dict[str, Any]]]:
    """Execute bakeoff evaluation on corpus jobs."""
    # 1. Verify corpus before any work
    corpus_data = verify_corpus(corpus_dir)

    out_dir.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict[str, Any]] = []
    all_passed = True

    for job_info in corpus_data["jobs"]:
        job_id = job_info["job_id"]
        src_job_dir = corpus_dir / job_id
        dst_job_dir = out_dir / job_id

        # Copy job to out dir
        if dst_job_dir.exists():
            shutil.rmtree(dst_job_dir)
        shutil.copytree(src_job_dir, dst_job_dir)

        # Handle hearing diagnostic
        if hearing == "perfect":
            synthesize_perfect_hearing(dst_job_dir)

        # Load job metadata
        ingest_path = dst_job_dir / "ingest.json"
        if not ingest_path.is_file():
            print(f"[-] Missing ingest.json in {dst_job_dir}", file=sys.stderr)
            sys.exit(1)
        ingest_data = json.loads(ingest_path.read_text(encoding="utf-8"))
        style = ingest_data.get("style", "literal")
        perturb = ingest_data.get("perturb", "mild")
        seed = ingest_data.get("seed", 7)
        tiebreak = ingest_data.get("tiebreak", "none")

        job_obj = Job(dst_job_dir)
        ctx = RunContext(
            style=style,
            perturb=perturb,
            seed=seed,
            matcher=matcher,
            tiebreak=tiebreak,
            no_llm_cache=no_llm_cache,
        )

        # Run pipeline stages
        if matcher == "anticipate":
            try:
                import importlib

                anticipate_mod = importlib.import_module(
                    "animated_infographics.presentation.anticipate"
                )
                run_anticipate_stage = anticipate_mod.run_anticipate_stage
                run_anticipate_stage(job_obj, ctx)
            except (ImportError, AttributeError):
                raise ValidationFailed(f"matcher '{matcher}' is not built yet") from None

        run_follow_stage(job_obj, ctx)
        run_compose_stage(job_obj, ctx)
        score_res = compute_presentation_score(dst_job_dir, oracle=False)

        # Extract matcher stats
        llm_calls = 0
        follow_log_path = dst_job_dir / "logs" / "follow.log"
        if follow_log_path.is_file():
            follow_log_text = follow_log_path.read_text(encoding="utf-8")
            m_llm = re.search(r"llm_calls=(\d+)", follow_log_text)
            if m_llm:
                llm_calls += int(m_llm.group(1))

        anticipate_log_path = dst_job_dir / "logs" / "anticipate.log"
        if anticipate_log_path.is_file():
            ant_log_text = anticipate_log_path.read_text(encoding="utf-8")
            m_ant_llm = re.search(r"llm_calls=(\d+)", ant_log_text)
            if m_ant_llm:
                llm_calls += int(m_ant_llm.group(1))

        pb = PlaybackPlan.model_validate_json(
            (dst_job_dir / "playback.json").read_text(encoding="utf-8")
        )
        compute_times = [float(c.compute_ms) for c in pb.commits]
        if compute_times:
            lat_median = round(statistics.median(compute_times), 3)
            p90_idx = int(math.ceil(0.9 * len(compute_times))) - 1
            lat_p90 = round(sorted(compute_times)[p90_idx], 3)
        else:
            lat_median = 0.0
            lat_p90 = 0.0

        metrics = evaluate_presentation_bars(score_res)
        for m in metrics:
            if not m.passed:
                all_passed = False

            if isinstance(m.value, float):
                val_str = (
                    f"{m.value:.4f}"
                    if m.metric.endswith("accuracy") or m.metric.endswith("stability")
                    else f"{m.value:.2f}"
                )
            else:
                val_str = str(m.value)

            bar_str = format_bar_str(m.metric, m.bar)
            status_str = "PASS" if m.passed else "MISS"
            print(f"BAR {job_id} {m.metric} {val_str} {bar_str} {status_str}")

            row = {
                "job": job_id,
                "fixture": job_info.get("fixture", ""),
                "style": style,
                "perturb": perturb,
                "seed": seed,
                "metric": m.metric,
                "value": m.value,
                "bar": m.bar,
                "bar_str": bar_str,
                "status": status_str,
                "passed": m.passed,
                "llm_calls": llm_calls,
                "compute_time_median_ms": lat_median,
                "compute_time_p90_ms": lat_p90,
            }
            all_rows.append(row)

    # Verify corpus again to ensure untouched
    verify_corpus(corpus_dir)

    # Write bakeoff.json
    bakeoff_path = out_dir / "bakeoff.json"
    bakeoff_path.write_text(json.dumps(all_rows, indent=2) + "\n", encoding="utf-8")

    exit_code = 0 if all_passed else 1
    return exit_code, all_rows


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for matcher bake-off replay harness."""
    parser = argparse.ArgumentParser(description="Presentation Matcher Bake-off Replay Harness")
    parser.add_argument(
        "--corpus", type=Path, required=True, help="Path to frozen corpus directory"
    )
    parser.add_argument(
        "--matcher",
        type=str,
        default="bm25",
        choices=["bm25", "anticipate", "llm"],
        help="Follower matcher to evaluate",
    )
    parser.add_argument("--out", type=Path, required=True, help="Output directory for replay runs")
    parser.add_argument(
        "--hearing",
        type=str,
        default="asr",
        choices=["asr", "perfect"],
        help="Hearing mode: asr (default) or perfect (diagnostic)",
    )
    parser.add_argument("--no-llm-cache", action="store_true", help="Bypass LLM response cache")

    args = parser.parse_args(argv)

    exit_code, _ = run_bakeoff(
        corpus_dir=args.corpus.resolve(),
        matcher=args.matcher,
        out_dir=args.out.resolve(),
        hearing=args.hearing,
        no_llm_cache=args.no_llm_cache,
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

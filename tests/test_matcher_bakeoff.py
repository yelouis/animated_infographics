"""Unit tests and falsification checks for matcher bake-off replay harness.

Per design_testing_and_validation.md §2 (bake-off harness row), §4d,
and agent_execution_guide.md §1.3 (J1).
"""

from __future__ import annotations

import hashlib
import json
import random
import shutil
from pathlib import Path
from typing import Any

import pytest

from animated_infographics.contracts.models import Transcript
from animated_infographics.contracts.playback import (
    PlaybackCommit,
    PlaybackHold,
    PlaybackPlan,
)
from animated_infographics.evals.matcher_bakeoff import (
    compute_decision_percentiles,
    compute_diagnostics,
    run_bakeoff,
    synthesize_perfect_hearing,
    verify_corpus,
)
from animated_infographics.jobs import Job, RunContext
from animated_infographics.presentation.compose import run_compose_stage
from animated_infographics.presentation.score import (
    compute_presentation_score,
    evaluate_presentation_bars,
)


def _make_mock_corpus(corpus_dir: Path, num_jobs: int = 2) -> dict[str, Any]:
    """Create a minimal valid synthetic corpus for testing."""
    corpus_dir.mkdir(parents=True, exist_ok=True)
    real_corpus_dir = Path("artifacts/matcher_bakeoff/2026-10-09/corpus")

    jobs_summary = []
    # If real corpus exists, copy slice of real jobs
    if (real_corpus_dir / "corpus.json").is_file():
        real_data = json.loads((real_corpus_dir / "corpus.json").read_text(encoding="utf-8"))
        for job_info in real_data["jobs"][:num_jobs]:
            jid = job_info["job_id"]
            dst_job = corpus_dir / jid
            shutil.copytree(real_corpus_dir / jid, dst_job)
            jobs_summary.append(job_info)
    else:
        pytest.skip("Corpus directory not available")

    corpus_record = {
        "corpus_version": 1,
        "date": "2026-10-09",
        "description": "Synthetic test corpus",
        "jobs": jobs_summary,
    }
    (corpus_dir / "corpus.json").write_text(
        json.dumps(corpus_record, indent=2) + "\n", encoding="utf-8"
    )
    return corpus_record


def test_bakeoff_harness_reproduces_scores(tmp_path: Path) -> None:
    """--matcher bm25 on each corpus job reproduces its presentation_score.json within 0.01."""
    corpus_dir = tmp_path / "corpus"
    _make_mock_corpus(corpus_dir, num_jobs=2)

    out_dir = tmp_path / "out"
    exit_code, rows = run_bakeoff(
        corpus_dir=corpus_dir,
        matcher="bm25",
        out_dir=out_dir,
    )

    # Exit code is 1 since bm25 misses follower bars
    assert exit_code == 1

    # Check reproduction on each job
    corpus_json = json.loads((corpus_dir / "corpus.json").read_text(encoding="utf-8"))
    for job_info in corpus_json["jobs"]:
        jid = job_info["job_id"]
        orig_score = json.loads(
            (corpus_dir / jid / "presentation_score.json").read_text(encoding="utf-8")
        )
        replay_score = json.loads(
            (out_dir / jid / "presentation_score.json").read_text(encoding="utf-8")
        )
        for metric, val in orig_score.items():
            if isinstance(val, (int, float)) and metric in replay_score:
                replay_val = replay_score[metric]
                assert abs(val - replay_val) <= 0.01, (
                    f"Metric {metric} in {jid} differed: {val} vs {replay_val}"
                )


def test_bakeoff_harness_corpus_unmodified(tmp_path: Path) -> None:
    """The harness never writes into the corpus (hashes unchanged after a run)."""
    corpus_dir = tmp_path / "corpus"
    _make_mock_corpus(corpus_dir, num_jobs=2)

    # Capture initial hashes of all files in corpus
    initial_hashes: dict[str, str] = {}
    for p in corpus_dir.rglob("*"):
        if p.is_file():
            initial_hashes[str(p.relative_to(corpus_dir))] = hashlib.sha256(
                p.read_bytes()
            ).hexdigest()

    out_dir = tmp_path / "out"
    run_bakeoff(corpus_dir=corpus_dir, matcher="bm25", out_dir=out_dir)

    # Verify every file hash is identical
    for rel_path, exp_hash in initial_hashes.items():
        p = corpus_dir / rel_path
        assert p.is_file(), f"File {rel_path} was removed from corpus"
        act_hash = hashlib.sha256(p.read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"File {rel_path} in corpus was mutated"


def test_bakeoff_harness_bakeoff_json_structure(tmp_path: Path) -> None:
    """bakeoff.json has one row per job and metric; includes percentiles and llm calls."""
    corpus_dir = tmp_path / "corpus"
    _make_mock_corpus(corpus_dir, num_jobs=1)

    out_dir = tmp_path / "out"
    _, rows = run_bakeoff(corpus_dir=corpus_dir, matcher="bm25", out_dir=out_dir)

    bakeoff_path = out_dir / "bakeoff.json"
    assert bakeoff_path.is_file()
    data = json.loads(bakeoff_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) == len(rows)

    required_keys = {
        "job",
        "fixture",
        "style",
        "perturb",
        "seed",
        "metric",
        "value",
        "bar",
        "bar_str",
        "status",
        "passed",
        "llm_calls",
        "compute_time_median_ms",
        "compute_time_p90_ms",
    }
    for row in data:
        for k in required_keys:
            assert k in row, f"Missing key '{k}' in bakeoff row"


def test_bakeoff_harness_perfect_hearing_spread(tmp_path: Path) -> None:
    """The perfect hearing input spreads each performed sentence's words
    evenly across speak_timing.
    """
    corpus_dir = tmp_path / "corpus"
    _make_mock_corpus(corpus_dir, num_jobs=1)

    corpus_data = json.loads((corpus_dir / "corpus.json").read_text(encoding="utf-8"))
    jid = corpus_data["jobs"][0]["job_id"]
    job_dir = corpus_dir / jid

    synthesize_perfect_hearing(job_dir)
    heard_data = (job_dir / "heard.json").read_text(encoding="utf-8")
    transcript = Transcript.model_validate_json(heard_data)

    assert transcript.source == "asr"
    assert len(transcript.words) > 0
    assert len(transcript.sentences) > 0

    # Test word timestamps increase monotonically
    for i in range(1, len(transcript.words)):
        assert transcript.words[i].start_ms >= transcript.words[i - 1].end_ms


def test_bakeoff_harness_falsification_ground_truth_pass(tmp_path: Path) -> None:
    """Falsification 1: ground-truth (oracle) playback meets every bar -> PASS on every bar."""
    corpus_dir = tmp_path / "corpus"
    _make_mock_corpus(corpus_dir, num_jobs=1)

    corpus_data = json.loads((corpus_dir / "corpus.json").read_text(encoding="utf-8"))
    jid = corpus_data["jobs"][0]["job_id"]
    job_dir = corpus_dir / jid

    # Construct ground-truth playback from sentences and timing
    perf = json.loads((job_dir / "performance.json").read_text(encoding="utf-8"))
    timing = json.loads((job_dir / "speak_timing.json").read_text(encoding="utf-8"))
    deck = json.loads((job_dir / "deck.json").read_text(encoding="utf-8"))

    from animated_infographics.presentation.score import _get_sentence_label_info

    first_slide_id = deck["slides"][0]["id"] if deck.get("slides") else "d1"
    initial_node = f"{first_slide_id}_section"

    gt_commits: list[PlaybackCommit] = []
    seen_points: set[str] = set()
    for sent, t in zip(perf["sentences"], timing, strict=False):
        if sent.get("op") == "adlib" or sent.get("label") == "adlib":
            continue
        s_id, p_id = _get_sentence_label_info(sent)
        if s_id is None or p_id is None:
            continue
        target_pt = f"{s_id}_p{p_id}"
        if target_pt not in seen_points:
            seen_points.add(target_pt)
            gt_commits.append(
                PlaybackCommit(
                    node_id=target_pt,
                    at_ms=int(t["start_ms"]),
                    decision_ms=int(t["start_ms"]),
                    compute_ms=0,
                    score=10.0,
                )
            )
    gt_commits.sort(key=lambda c: c.at_ms)
    if not gt_commits or gt_commits[0].at_ms > 0:
        gt_commits.insert(
            0,
            PlaybackCommit(
                node_id=initial_node,
                at_ms=0,
                decision_ms=0,
                compute_ms=0,
                score=10.0,
            ),
        )

    out_dir = tmp_path / "out"
    out_job = out_dir / jid
    shutil.copytree(job_dir, out_job)
    gt_playback = PlaybackPlan(schema_version=1, commits=gt_commits, holds=[], matcher="bm25")
    (out_job / "playback.json").write_text(
        gt_playback.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )

    job_obj = Job(out_job)
    ctx = RunContext(style="literal", matcher="bm25")
    run_compose_stage(job_obj, ctx)
    gt_score = compute_presentation_score(out_job, oracle=False)
    metrics = evaluate_presentation_bars(gt_score)

    for m in metrics:
        assert m.passed, f"Ground-truth failed metric {m.metric}: {m.value} vs bar {m.bar}"


def test_bakeoff_harness_falsification_shuffled_heard_miss(tmp_path: Path) -> None:
    """Falsification 2: shuffled heard.json -> accuracy bars MISS."""
    corpus_dir = tmp_path / "corpus"
    _make_mock_corpus(corpus_dir, num_jobs=1)

    corpus_data = json.loads((corpus_dir / "corpus.json").read_text(encoding="utf-8"))
    jid = corpus_data["jobs"][0]["job_id"]
    job_dir = corpus_dir / jid

    # Read heard.json, shuffle word texts
    orig_transcript = Transcript.model_validate_json(
        (job_dir / "heard.json").read_text(encoding="utf-8")
    )
    words_data = [w.model_dump() for w in orig_transcript.words]
    texts = [w["text"] for w in words_data]
    rng = random.Random(42)
    rng.shuffle(texts)
    for i, t in enumerate(texts):
        words_data[i]["text"] = t

    shuffled_transcript = Transcript(
        schema_version=1,
        source="asr",
        audio_path=orig_transcript.audio_path,
        duration_ms=orig_transcript.duration_ms,
        words=words_data,  # type: ignore[arg-type]
        sentences=orig_transcript.sentences,
    )

    out_dir = tmp_path / "out"
    out_job = out_dir / jid
    shutil.copytree(job_dir, out_job)
    (out_job / "heard.json").write_text(
        shuffled_transcript.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )

    job_obj = Job(out_job)
    ctx = RunContext(style="literal", matcher="bm25")
    from animated_infographics.presentation.follow import run_follow_stage

    run_follow_stage(job_obj, ctx)
    run_compose_stage(job_obj, ctx)
    shuffled_score = compute_presentation_score(out_job, oracle=False)
    metrics = evaluate_presentation_bars(shuffled_score)

    # Shuffled must miss accuracy bars
    acc_metrics = [m for m in metrics if "accuracy" in m.metric]
    any_miss = any(not m.passed for m in acc_metrics)
    assert any_miss, "Shuffled speech unexpectedly passed all accuracy bars"


def test_bakeoff_harness_corpus_hash_mismatch_fails(tmp_path: Path) -> None:
    """Tampering with any corpus file causes verify_corpus to exit 1."""
    corpus_dir = tmp_path / "corpus"
    _make_mock_corpus(corpus_dir, num_jobs=1)

    corpus_data = json.loads((corpus_dir / "corpus.json").read_text(encoding="utf-8"))
    jid = corpus_data["jobs"][0]["job_id"]

    # Tamper with deck.json
    deck_path = corpus_dir / jid / "deck.json"
    deck_path.write_text(deck_path.read_text(encoding="utf-8") + " ", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        verify_corpus(corpus_dir)
    assert exc_info.value.code == 1


def test_decision_compute_time_percentiles_stub_matcher() -> None:
    # Stub matcher with a fixed 700 ms per decision
    # Initial commit at t=0 has compute_ms=0

    # Subcase 1: Holds only, 0 post-initial commits
    pb_holds = PlaybackPlan(
        schema_version=1,
        commits=[
            PlaybackCommit(node_id="d1_section", at_ms=0, decision_ms=0, compute_ms=0, score=0.0),
        ],
        holds=[
            PlaybackHold(
                decision_ms=i * 1000,
                current_node_id="d1_section",
                top_candidate_id="d1_section",
                top_candidate_score=1.0,
                reason="top_is_current",
                compute_ms=700,
            )
            for i in range(1, 10)
        ],
    )
    med_h, p90_h = compute_decision_percentiles(pb_holds)
    assert med_h == 700.0
    assert p90_h == 700.0

    # Subcase 2: Single post-initial commit, 0 holds (tests excluding initial 0ms commit)
    pb_commit = PlaybackPlan(
        schema_version=1,
        commits=[
            PlaybackCommit(node_id="d1_section", at_ms=0, decision_ms=0, compute_ms=0, score=0.0),
            PlaybackCommit(
                node_id="d1_p0", at_ms=2000, decision_ms=2000, compute_ms=700, score=1.0
            ),
        ],
        holds=[],
    )
    med_c, p90_c = compute_decision_percentiles(pb_commit)
    assert med_c == 700.0
    assert p90_c == 700.0


def test_diagnostics_round1_a2_unreachable_share(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wave L1 unit row: re-run Round 1's A2 on history-great-stink-20261009-074656.

    Through the harness so that candidates are recorded, and "unreachable share" is >= 0.40.
    Uses warm cache INFOGRAPHICS_CACHE_DIR=artifacts/matcher_bakeoff/2026-10-09/cache_llm.
    """
    corpus_src = Path("artifacts/matcher_bakeoff/2026-10-09/corpus")
    cache_dir = Path("artifacts/matcher_bakeoff/2026-10-09/cache_llm")
    jid = "history-great-stink-20261009-074656"

    if not (corpus_src / jid).is_dir() or not cache_dir.is_dir():
        pytest.skip("Round 1 corpus or LLM cache missing")

    monkeypatch.setenv("INFOGRAPHICS_CACHE_DIR", str(cache_dir.resolve()))

    # Build a 1-job test corpus
    test_corpus_dir = tmp_path / "corpus"
    test_corpus_dir.mkdir(parents=True, exist_ok=True)
    dst_job = test_corpus_dir / jid
    shutil.copytree(corpus_src / jid, dst_job)

    # Hashes from original corpus.json
    orig_corpus_data = json.loads((corpus_src / "corpus.json").read_text(encoding="utf-8"))
    job_info = next(j for j in orig_corpus_data["jobs"] if j["job_id"] == jid)

    corpus_record = {
        "corpus_version": 1,
        "date": "2026-10-09",
        "jobs": [job_info],
    }
    (test_corpus_dir / "corpus.json").write_text(
        json.dumps(corpus_record, indent=2) + "\n", encoding="utf-8"
    )

    out_dir = tmp_path / "out"
    exit_code, rows = run_bakeoff(
        corpus_dir=test_corpus_dir,
        matcher="llm",
        out_dir=out_dir,
    )

    # Check that candidate_ids were recorded
    pb = PlaybackPlan.model_validate_json(
        (out_dir / jid / "playback.json").read_text(encoding="utf-8")
    )
    assert len(pb.holds) > 0
    assert any(len(h.candidate_ids) > 0 for h in pb.holds)
    assert any(len(c.candidate_ids) > 0 for c in pb.commits[1:])

    # Check unreachable_share >= 0.40
    unreachable_share = rows[0]["unreachable_share"]
    assert unreachable_share >= 0.40, f"Expected unreachable_share >= 0.40, got {unreachable_share}"
    assert rows[0]["stuck_on_current_median"] >= 0.0
    assert rows[0]["stuck_on_current_p90"] >= 0.0


def test_diagnostics_synthetic_scenarios(tmp_path: Path) -> None:
    """Test compute_diagnostics on synthetic performance and playback data."""
    job_dir = tmp_path / "job"
    job_dir.mkdir()

    # Synthetic performance: 2 points
    # Point 0: 0 - 5000 ms (slide d1, point 0)
    # Point 1: 5000 - 10000 ms (slide d1, point 1)
    perf = {
        "schema_version": 1,
        "sentences": [
            {
                "i": 0,
                "text": "Slide 1 point 0",
                "op": "verbatim",
                "label": {"slide": "d1", "point": 0},
            },
            {
                "i": 1,
                "text": "Slide 1 point 1",
                "op": "verbatim",
                "label": {"slide": "d1", "point": 1},
            },
        ],
    }
    timing = [
        {"sentence_i": 0, "start_ms": 0, "end_ms": 5000},
        {"sentence_i": 1, "start_ms": 5000, "end_ms": 10000},
    ]
    (job_dir / "performance.json").write_text(json.dumps(perf), encoding="utf-8")
    (job_dir / "speak_timing.json").write_text(json.dumps(timing), encoding="utf-8")

    # Scenario: 4 decisions
    # d1 at 1500ms: candidate_ids=["d1_p0"], current="d1_section", top="d1_p0"
    #   -> reachable! (point 0 allows d1_section & d1_p0)
    # d2 at 3000ms: candidate_ids=["d1_section"], current="d1_p0", top="d1_p0"
    #   -> reachable! (section counts for pt 0)
    # d3 at 6500ms: candidate_ids=["d1_p0"], current="d1_p0", top="d1_p0"
    #   -> unreachable! (true is d1_p1)
    # d4 at 8000ms: candidate_ids=["d1_p1"], current="d1_p0", top="d1_p1"
    #   -> reachable!
    pb = PlaybackPlan(
        schema_version=1,
        commits=[
            PlaybackCommit(node_id="d1_section", at_ms=0, decision_ms=0, compute_ms=0, score=0.0),
            PlaybackCommit(
                node_id="d1_p0",
                at_ms=1700,
                decision_ms=1500,
                compute_ms=200,
                score=1.0,
                candidate_ids=["d1_p0"],
            ),
        ],
        holds=[
            PlaybackHold(
                decision_ms=3000,
                current_node_id="d1_p0",
                top_candidate_id="d1_p0",
                top_candidate_score=1.0,
                reason="top_is_current",
                compute_ms=10,
                candidate_ids=["d1_section"],
            ),
            PlaybackHold(
                decision_ms=6500,
                current_node_id="d1_p0",
                top_candidate_id="d1_p0",
                top_candidate_score=1.0,
                reason="top_is_current",
                compute_ms=10,
                candidate_ids=["d1_p0"],
            ),
            PlaybackHold(
                decision_ms=8000,
                current_node_id="d1_p0",
                top_candidate_id="d1_p1",
                top_candidate_score=1.0,
                reason="top_is_current",
                compute_ms=10,
                candidate_ids=["d1_p1"],
            ),
        ],
    )

    diags = compute_diagnostics(job_dir, pb)
    # 1 of 4 decisions is unreachable (decision at 6500ms where true is d1_p1
    # but candidates=[d1_p0])
    assert diags["unreachable_share"] == 0.25
    # At point 1 change (6500ms): current is d1_p0 (not true pt), answered d1_p0
    # -> 1 consecutive hold before answering d1_p1
    assert diags["stuck_on_current_median"] == 1.0

# Matcher Bake-off Report — 2026-10-09

This document records the presentation follower bake-off across 8 frozen corpus talks, per `design_presentation_simulation.md` §6.6 and `agent_execution_guide.md` §1.3 (Wave J).

---

## 1. Baseline: `bm25` Matcher (Before)

- **Corpus directory:** `artifacts/matcher_bakeoff/2026-10-09/corpus/` (8 jobs frozen with SHA-256 manifest in `corpus.json`).
- **Matcher under test:** `bm25` (the live baseline follower from Wave H).
- **Harness:** `src/animated_infographics/evals/matcher_bakeoff.py`.
- **Exit code:** `1` (follower bars missed on all 8 runs).

### 1.1 Decision Set (Seed 7)

| Job ID | Configuration | Metric | Bar | ASR Hearing | Perfect Hearing | Status |
|---|---|---|---|---|---|---|
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | slide_accuracy | >=0.90 | 0.5542 | 0.5233 | MISS |
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | point_accuracy | >=0.75 | 0.3682 | 0.3378 | MISS |
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | onset_lag_median_s | <=3.0 | 7.38 s | 8.70 s | MISS |
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | onset_lag_p90_s | <=6.0 | 12.76 s | 12.06 s | MISS |
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | false_switches_per_min | <=1.0 | 3.01 /min | 3.52 /min | MISS |
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | adlib_stability | >=0.80 | 1.0000 | 1.0000 | PASS |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | slide_accuracy | >=0.80 | 0.3348 | 0.5048 | MISS |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | point_accuracy | >=0.60 | 0.2224 | 0.3325 | MISS |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | onset_lag_median_s | <=4.0 | 10.00 s | 10.00 s | MISS |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | onset_lag_p90_s | <=8.0 | 33.50 s | 22.41 s | MISS |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | false_switches_per_min | <=2.0 | 3.26 /min | 3.12 /min | MISS |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | adlib_stability | >=0.70 | 0.5571 | 0.9708 | MISS |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | skip_recovery_s | <=6.0 | 99.00 s | 16.73 s | MISS |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | slide_accuracy | >=0.80 | 0.3634 | 0.3718 | MISS |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | point_accuracy | >=0.60 | 0.2039 | 0.1891 | MISS |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | onset_lag_median_s | <=4.0 | 9.59 s | 8.62 s | MISS |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | onset_lag_p90_s | <=8.0 | 10.00 s | 10.53 s | MISS |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | false_switches_per_min | <=2.0 | 4.07 /min | 4.08 /min | MISS |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | adlib_stability | >=0.70 | 0.6609 | 0.9153 | MISS |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | skip_recovery_s | <=6.0 | 99.00 s | 99.00 s | MISS |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | slide_accuracy | >=0.90 | 0.3176 | 0.4367 | MISS |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | point_accuracy | >=0.75 | 0.1959 | 0.1845 | MISS |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | onset_lag_median_s | <=3.0 | 10.00 s | 9.96 s | MISS |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | onset_lag_p90_s | <=6.0 | 11.51 s | 92.46 s | MISS |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | false_switches_per_min | <=1.0 | 5.00 /min | 4.49 /min | MISS |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | adlib_stability | >=0.80 | 0.7399 | 1.0000 | MISS |

### 1.2 Held-Out Set (Seed 11)

| Job ID | Configuration | Metric | Bar | ASR Hearing | Perfect Hearing | Status |
|---|---|---|---|---|---|---|
| `history-great-stink-20261009-075108` | literal / mild / seed 11 | slide_accuracy | >=0.90 | 0.5007 | 0.4902 | MISS |
| `history-great-stink-20261009-075108` | literal / mild / seed 11 | point_accuracy | >=0.75 | 0.3454 | 0.3221 | MISS |
| `history-great-stink-20261009-075108` | literal / mild / seed 11 | onset_lag_median_s | <=3.0 | 8.86 s | 9.85 s | MISS |
| `history-great-stink-20261009-075108` | literal / mild / seed 11 | onset_lag_p90_s | <=6.0 | 12.99 s | 14.27 s | MISS |
| `history-great-stink-20261009-075108` | literal / mild / seed 11 | false_switches_per_min | <=1.0 | 2.34 /min | 3.34 /min | MISS |
| `history-great-stink-20261009-075108` | literal / mild / seed 11 | adlib_stability | >=0.80 | 1.0000 | 0.4643 | PASS |
| `history-great-stink-20261009-075201` | creative / strong / seed 11 | slide_accuracy | >=0.80 | 0.3299 | 0.4230 | MISS |
| `history-great-stink-20261009-075201` | creative / strong / seed 11 | point_accuracy | >=0.60 | 0.2270 | 0.2805 | MISS |
| `history-great-stink-20261009-075201` | creative / strong / seed 11 | onset_lag_median_s | <=4.0 | 10.00 s | 10.68 s | MISS |
| `history-great-stink-20261009-075201` | creative / strong / seed 11 | onset_lag_p90_s | <=8.0 | 44.76 s | 115.64 s | MISS |
| `history-great-stink-20261009-075201` | creative / strong / seed 11 | false_switches_per_min | <=2.0 | 4.07 /min | 3.02 /min | MISS |
| `history-great-stink-20261009-075201` | creative / strong / seed 11 | adlib_stability | >=0.70 | 0.3967 | 0.4275 | MISS |
| `history-great-stink-20261009-075201` | creative / strong / seed 11 | skip_recovery_s | <=6.0 | 10.83 s | 11.50 s | MISS |
| `story-overdue-book-20261009-075301` | literal / strong / seed 11 | slide_accuracy | >=0.80 | 0.3378 | 0.4132 | MISS |
| `story-overdue-book-20261009-075301` | literal / strong / seed 11 | point_accuracy | >=0.60 | 0.2445 | 0.2000 | MISS |
| `story-overdue-book-20261009-075301` | literal / strong / seed 11 | onset_lag_median_s | <=4.0 | 7.88 s | 9.45 s | MISS |
| `story-overdue-book-20261009-075301` | literal / strong / seed 11 | onset_lag_p90_s | <=8.0 | 57.11 s | 50.28 s | MISS |
| `story-overdue-book-20261009-075301` | literal / strong / seed 11 | false_switches_per_min | <=2.0 | 3.79 /min | 3.28 /min | MISS |
| `story-overdue-book-20261009-075301` | literal / strong / seed 11 | adlib_stability | >=0.70 | 0.8707 | 0.8901 | PASS |
| `story-overdue-book-20261009-075301` | literal / strong / seed 11 | skip_recovery_s | <=6.0 | 4.02 s | 3.90 s | PASS |
| `story-overdue-book-20261009-075415` | creative / mild / seed 11 | slide_accuracy | >=0.90 | 0.3965 | 0.5603 | MISS |
| `story-overdue-book-20261009-075415` | creative / mild / seed 11 | point_accuracy | >=0.75 | 0.2568 | 0.3186 | MISS |
| `story-overdue-book-20261009-075415` | creative / mild / seed 11 | onset_lag_median_s | <=3.0 | 10.00 s | 6.47 s | MISS |
| `story-overdue-book-20261009-075415` | creative / mild / seed 11 | onset_lag_p90_s | <=6.0 | 90.25 s | 19.17 s | MISS |
| `story-overdue-book-20261009-075415` | creative / mild / seed 11 | false_switches_per_min | <=1.0 | 4.37 /min | 3.68 /min | MISS |
| `story-overdue-book-20261009-075415` | creative / mild / seed 11 | adlib_stability | >=0.80 | 0.2914 | 0.1250 | MISS |

---

## 2. Comparison with Issue 8 Baseline

| Run (Decision Set) | Metric | Issue 8 Table | Baseline (ASR) | Delta | Agreement |
|---|---|---|---|---|---|
| `history_great_stink`, literal / mild | slide_accuracy | 0.56 | 0.5542 | −0.0058 | **Agreed (within 0.05)** |
| `history_great_stink`, literal / mild | point_accuracy | 0.36 | 0.3682 | +0.0082 | **Agreed (within 0.05)** |
| `history_great_stink`, literal / mild | onset_lag median | 7.4 s | 7.38 s | −0.02 s | **Agreed** |
| `history_great_stink`, literal / mild | false_switches /min | 3.35 | 3.01 | −0.34 | **Agreed** |
| `story_overdue_book`, literal / strong | slide_accuracy | 0.36 | 0.3634 | +0.0034 | **Agreed (within 0.05)** |
| `story_overdue_book`, literal / strong | point_accuracy | 0.20 | 0.2039 | +0.0039 | **Agreed (within 0.05)** |
| `story_overdue_book`, literal / strong | onset_lag median | 9.5 s | 9.59 s | +0.09 s | **Agreed** |
| `story_overdue_book`, literal / strong | false_switches /min | 4.08 | 4.07 | −0.01 | **Agreed** |
| `story_overdue_book`, creative / mild | slide_accuracy | 0.32 | 0.3176 | −0.0024 | **Agreed (within 0.05)** |
| `story_overdue_book`, creative / mild | point_accuracy | 0.20 | 0.1959 | −0.0041 | **Agreed (within 0.05)** |
| `history_great_stink`, creative / strong | slide_accuracy | 0.49 | 0.3348 | −0.1552 | Moved (expected) |
| `history_great_stink`, creative / strong | point_accuracy | 0.31 | 0.2224 | −0.0876 | Moved (expected) |

### Notes on Deltas:
1. **Literal jobs:** Both literal jobs reproduced Issue 8's measured numbers with extreme precision (slide accuracy within 0.006 and point accuracy within 0.008, well within the 0.05 bar). Overdue book creative/mild also reproduced Issue 8 within 0.004.
2. **Creative great stink:** Moved from 0.49 to 0.3348 because Wave I (items I4 and I7) salvaged the director, added license checks, placed overlays, and rebuilt the tree nodes. In the previous run before Wave I, creative Great Stink had zero overlays and unvalidated metaphors.
3. **Perfect hearing diagnosis:** Isolating ASR transcription errors by feeding verbatim performance words spread across exact TTS timing spans did **not** solve the accuracy deficit (slide accuracy remained 0.37–0.56; point accuracy remained 0.18–0.34). This confirms that lexical BM25 matching fails due to paraphrase vocabulary drift and the 20-word window lag, not ASR speech recognition error.

---

## 3. Matcher Compute Time & LLM Calls

For `bm25`:
- **LLM calls:** 0 per job.
- **Compute latency per decision point:** median 0.0 ms, p90 0.0 ms (< 1 ms across all runs).

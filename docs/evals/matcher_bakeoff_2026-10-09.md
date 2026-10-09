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

## 3. Matcher Compute Time & LLM Calls (Baseline)

For `bm25`:
- **LLM calls:** 0 per job.
- **Compute latency per decision point:** median 0.0 ms, p90 0.0 ms (< 1 ms across all runs).

---

## 4. Contestant A1: `anticipate` Matcher

- **Corpus directory:** `artifacts/matcher_bakeoff/2026-10-09/corpus/` (unmodified frozen corpus).
- **Matcher under test:** `anticipate` (Contestant A1 per `design_presentation_simulation.md` §6.6.1).
- **Harness output directory:** `artifacts/matcher_bakeoff/2026-10-09/anticipate_run/`.
- **Exit code:** `1` (follower bars missed).

### 4.1 Decision Set (Seed 7)

| Job ID | Configuration | Metric | Bar | ASR Hearing | Perfect Hearing | Status |
|---|---|---|---|---|---|---|
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | slide_accuracy | >=0.90 | 0.1789 | 0.2186 | MISS |
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | point_accuracy | >=0.75 | 0.1412 | 0.1845 | MISS |
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | onset_lag_median_s | <=3.0 | 10.00 s | 10.00 s | MISS |
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | onset_lag_p90_s | <=6.0 | 14.60 s | 10.00 s | MISS |
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | false_switches_per_min | <=1.0 | 4.52 /min | 4.36 /min | MISS |
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | adlib_stability | >=0.80 | 0.0686 | 0.1305 | MISS |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | slide_accuracy | >=0.80 | 0.2183 | 0.1839 | MISS |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | point_accuracy | >=0.60 | 0.1727 | 0.1436 | MISS |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | onset_lag_median_s | <=4.0 | 10.00 s | 10.00 s | MISS |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | onset_lag_p90_s | <=8.0 | 56.09 s | 49.21 s | MISS |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | false_switches_per_min | <=2.0 | 4.82 /min | 4.68 /min | MISS |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | adlib_stability | >=0.70 | 0.1934 | 0.2716 | MISS |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | skip_recovery_s | <=6.0 | 99.00 s | 99.00 s | MISS |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | slide_accuracy | >=0.80 | 0.2092 | 0.2089 | MISS |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | point_accuracy | >=0.60 | 0.1575 | 0.1446 | MISS |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | onset_lag_median_s | <=4.0 | 10.00 s | 10.00 s | MISS |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | onset_lag_p90_s | <=8.0 | 17.02 s | 10.00 s | MISS |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | false_switches_per_min | <=2.0 | 5.95 /min | 5.65 /min | MISS |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | adlib_stability | >=0.70 | 0.9757 | 0.9859 | PASS |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | skip_recovery_s | <=6.0 | 99.00 s | 99.00 s | MISS |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | slide_accuracy | >=0.90 | 0.2466 | 0.1854 | MISS |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | point_accuracy | >=0.75 | 0.1946 | 0.1410 | MISS |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | onset_lag_median_s | <=3.0 | 10.00 s | 10.00 s | MISS |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | onset_lag_p90_s | <=6.0 | 16.08 s | 42.36 s | MISS |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | false_switches_per_min | <=1.0 | 5.87 /min | 6.05 /min | MISS |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | adlib_stability | >=0.80 | 0.2545 | 0.3334 | MISS |

### 4.2 Held-Out Set (Seed 11)

| Job ID | Configuration | Metric | Bar | ASR Hearing | Perfect Hearing | Status |
|---|---|---|---|---|---|---|
| `history-great-stink-20261009-075108` | literal / mild / seed 11 | slide_accuracy | >=0.90 | 0.2022 | 0.2412 | MISS |
| `history-great-stink-20261009-075108` | literal / mild / seed 11 | point_accuracy | >=0.75 | 0.1335 | 0.1906 | MISS |
| `history-great-stink-20261009-075108` | literal / mild / seed 11 | onset_lag_median_s | <=3.0 | 10.00 s | 10.00 s | MISS |
| `history-great-stink-20261009-075108` | literal / mild / seed 11 | onset_lag_p90_s | <=6.0 | 16.64 s | 10.00 s | MISS |
| `history-great-stink-20261009-075108` | literal / mild / seed 11 | false_switches_per_min | <=1.0 | 4.51 /min | 4.01 /min | MISS |
| `history-great-stink-20261009-075108` | literal / mild / seed 11 | adlib_stability | >=0.80 | 1.0000 | 1.0000 | PASS |
| `history-great-stink-20261009-075201` | creative / strong / seed 11 | slide_accuracy | >=0.80 | 0.2183 | 0.2226 | MISS |
| `history-great-stink-20261009-075201` | creative / strong / seed 11 | point_accuracy | >=0.60 | 0.1486 | 0.1691 | MISS |
| `history-great-stink-20261009-075201` | creative / strong / seed 11 | onset_lag_median_s | <=4.0 | 10.00 s | 10.00 s | MISS |
| `history-great-stink-20261009-075201` | creative / strong / seed 11 | onset_lag_p90_s | <=8.0 | 11.14 s | 13.60 s | MISS |
| `history-great-stink-20261009-075201` | creative / strong / seed 11 | false_switches_per_min | <=2.0 | 4.37 /min | 3.92 /min | MISS |
| `history-great-stink-20261009-075201` | creative / strong / seed 11 | adlib_stability | >=0.70 | 0.7938 | 0.8159 | PASS |
| `history-great-stink-20261009-075201` | creative / strong / seed 11 | skip_recovery_s | <=6.0 | 4.31 s | 4.76 s | PASS |
| `story-overdue-book-20261009-075301` | literal / strong / seed 11 | slide_accuracy | >=0.80 | 0.2067 | 0.2052 | MISS |
| `story-overdue-book-20261009-075301` | literal / strong / seed 11 | point_accuracy | >=0.60 | 0.1564 | 0.1469 | MISS |
| `story-overdue-book-20261009-075301` | literal / strong / seed 11 | onset_lag_median_s | <=4.0 | 10.00 s | 10.00 s | MISS |
| `story-overdue-book-20261009-075301` | literal / strong / seed 11 | onset_lag_p90_s | <=8.0 | 43.45 s | 39.80 s | MISS |
| `story-overdue-book-20261009-075301` | literal / strong / seed 11 | false_switches_per_min | <=2.0 | 6.21 /min | 6.22 /min | MISS |
| `story-overdue-book-20261009-075301` | literal / strong / seed 11 | adlib_stability | >=0.70 | 0.8149 | 0.8116 | PASS |
| `story-overdue-book-20261009-075301` | literal / strong / seed 11 | skip_recovery_s | <=6.0 | 2.48 s | 3.90 s | PASS |
| `story-overdue-book-20261009-075415` | creative / mild / seed 11 | slide_accuracy | >=0.90 | 0.1653 | 0.2070 | MISS |
| `story-overdue-book-20261009-075415` | creative / mild / seed 11 | point_accuracy | >=0.75 | 0.1355 | 0.1559 | MISS |
| `story-overdue-book-20261009-075415` | creative / mild / seed 11 | onset_lag_median_s | <=3.0 | 10.00 s | 10.00 s | MISS |
| `story-overdue-book-20261009-075415` | creative / mild / seed 11 | onset_lag_p90_s | <=6.0 | 39.77 s | 41.88 s | MISS |
| `story-overdue-book-20261009-075415` | creative / mild / seed 11 | false_switches_per_min | <=1.0 | 6.12 /min | 6.48 /min | MISS |
| `story-overdue-book-20261009-075415` | creative / mild / seed 11 | adlib_stability | >=0.80 | 1.0000 | 1.0000 | PASS |

### 4.3 Inspection of Anticipated Sentences (`anticipation.json`)

Sampled from `history-great-stink-20261009-074656`:

- **Node `d1_p1`:**
  - *"The big issue was that the sewers were actually draining straight into the city's drinking water."*
  - *"Basically, the waste from the sewers was going directly into the water people were using for drinking."*
  - *"At the time, the sewage was being dumped right into the same water supply that people relied on for drinking."*
  - *"What made things so dangerous was that the sewers drained directly into the drinking water."*
- **Node `d2_p0`:**
  - *"It was so bad that the smell actually made its way all the way into the Houses of Parliament."*
  - *"The stench was powerful enough to reach the Houses of Parliament."*
  - *"You could actually smell it inside the Houses of Parliament."*
  - *"The smell was so intense that it even reached the Houses of Parliament."*
- **Node `d2_p2`:**
  - *"At the time, there was this widespread belief that disease was actually caused by breathing in bad air."*
  - *"Back then, people were convinced that the smell itself was what made you sick."*
  - *"The general idea was that if you inhaled this foul air, it would lead to illness."*
  - *"People really believed that the air being bad was the direct cause of the disease."*

**Judgement:** The sentences sound like natural spoken presentation language. They strictly adhere to grounding rules: no extraneous ungrounded facts or digits are added.

### 4.4 Strip Chart Analysis: BM25 vs A1

Examining `history-great-stink-20261009-074656/strip_chart.png`:
- **Under BM25 baseline:** The follower traversed the entire deck, stepping from D1 through D7 over time, though lagging by 7–10 seconds at transitions.
- **Under A1 (`anticipate`):** Slide accuracy collapsed from 0.5542 down to 0.1789. The strip chart shows that the shown slide (orange) quickly stepped to D2, but repeatedly jumped back to D1, remaining trapped between D1 and D2 for almost the entire 5-minute presentation.
- **Root Cause:** A1 opens the entire prefix of deck point nodes as candidates with a fixed cost of 0.5. Because anticipated sentences enriched the vocabulary of early nodes with common conversational phrases ("London", "1858", "water", "crisis"), spoken references to the general topic continually produced BM25 scores on early nodes exceeding the current node plus 1.5. At 2 consecutive decision points, the follower took backward jumps, failing to maintain forward progress.

### 4.5 Compute Time and Resource Usage

For `anticipate`:
- **Stage LLM calls:** 28 to 31 calls per presentation talk (1 per tree node).
- **Stage execution time:** ~35 s cold per talk, ~0 s warm via response cache.
- **Live loop compute latency per decision:** median 0.0 ms, p90 0.0 ms (< 1 ms per decision). Live latency requirement (< 1.5 s) is easily satisfied since no LLM runs in the live loop.

### 4.6 Adoption Decision per §6.6.4

Per `design_presentation_simulation.md` §6.6.4:
> "If A1 meets every §8 bar on all 4 decision-set jobs and all 4 held-out jobs, adopt A1 and stop; A2 is not built.
> If A1 passes the decision set but misses on the held-out set, stop and file it with both tables.
> **Otherwise build A2 and run the harness.**"

**Outcome:** Contestant A1 missed the accuracy bars on **all 4 decision-set jobs** (slide accuracy 0.17–0.24 vs bar 0.80–0.90; point accuracy 0.14–0.19 vs bar 0.60–0.75).
Therefore, under §6.6.4:
**A1 is NOT adopted. Proceed to J3 (Contestant A2: LLM point classifier).**


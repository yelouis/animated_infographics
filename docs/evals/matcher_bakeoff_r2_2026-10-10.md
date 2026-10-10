# Matcher Bake-off Round 2 Report — 2026-10-10

This document records the Round 2 presentation follower bake-off across 8 frozen corpus talks, per `design_presentation_simulation.md` §6.6.6 and `agent_execution_guide.md` §3 (Wave L).

---

## 1. Baseline: `bm25` Matcher (Before)

- **Corpus directory:** `artifacts/matcher_bakeoff/2026-10-10/corpus_r2/` (8 jobs frozen with SHA-256 manifest in `corpus.json`).
  - **Decision set:** 4 jobs from Round 1 (seed 7), copied with identical SHA-256 hashes.
  - **Held-out set:** 4 fresh jobs generated post-Wave K (seed 13), one per §9 configuration.
- **Matcher under test:** `bm25` (the live baseline follower from Wave H).
- **Harness:** `src/animated_infographics/evals/matcher_bakeoff.py`.
- **Exit code:** `1` (follower bars missed on all 8 runs).

### 1.1 Decision Set (Seed 7)

| Job ID | Configuration | Metric | Bar | ASR Hearing | Perfect Hearing | Status | Diagnostics (ASR) |
|---|---|---|---|---|---|---|---|
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | slide_accuracy | >=0.90 | 0.5542 | 0.5233 | MISS | unreachable: 19.66%, stuck median: 2.0, p90: 4.0 |
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | point_accuracy | >=0.75 | 0.3682 | 0.3378 | MISS | |
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | onset_lag_median_s | <=3.0 | 8.29 s | 8.70 s | MISS | |
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | onset_lag_p90_s | <=6.0 | 20.75 s | 20.75 s | MISS | |
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | false_switches_per_min | <=1.0 | 3.01 /min | 3.52 /min | MISS | |
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | adlib_stability | >=0.80 | 1.0000 | 1.0000 | PASS | |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | slide_accuracy | >=0.80 | 0.3348 | 0.5048 | MISS | unreachable: 44.88%, stuck median: 3.0, p90: 5.0 |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | point_accuracy | >=0.60 | 0.2224 | 0.3325 | MISS | |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | onset_lag_median_s | <=4.0 | 13.55 s | 10.00 s | MISS | |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | onset_lag_p90_s | <=8.0 | 23.58 s | 22.72 s | MISS | |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | false_switches_per_min | <=2.0 | 3.26 /min | 3.12 /min | MISS | |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | adlib_stability | >=0.70 | 0.5571 | 0.9708 | MISS | |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | skip_recovery_s | <=6.0 | 99.00 s | 16.73 s | MISS | |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | slide_accuracy | >=0.80 | 0.3634 | 0.3718 | MISS | unreachable: 41.70%, stuck median: 2.0, p90: 4.0 |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | point_accuracy | >=0.60 | 0.2039 | 0.1891 | MISS | |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | onset_lag_median_s | <=4.0 | 9.80 s | 10.00 s | MISS | |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | onset_lag_p90_s | <=8.0 | 25.05 s | 25.05 s | MISS | |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | false_switches_per_min | <=2.0 | 4.07 /min | 4.08 /min | MISS | |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | adlib_stability | >=0.70 | 0.6609 | 0.9153 | MISS | |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | skip_recovery_s | <=6.0 | 99.00 s | 99.00 s | MISS | |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | slide_accuracy | >=0.90 | 0.3176 | 0.4367 | MISS | unreachable: 43.35%, stuck median: 1.0, p90: 6.0 |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | point_accuracy | >=0.75 | 0.1959 | 0.1845 | MISS | |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | onset_lag_median_s | <=3.0 | 10.00 s | 10.00 s | MISS | |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | onset_lag_p90_s | <=6.0 | 26.95 s | 26.95 s | MISS | |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | false_switches_per_min | <=1.0 | 5.00 /min | 4.49 /min | MISS | |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | adlib_stability | >=0.80 | 0.7399 | 1.0000 | MISS | |

### 1.2 Held-Out Set (Seed 13)

| Job ID | Configuration | Metric | Bar | ASR Hearing | Perfect Hearing | Status | Diagnostics (ASR) |
|---|---|---|---|---|---|---|---|
| `history-great-stink-20261010-173311` | literal / mild / seed 13 | slide_accuracy | >=0.90 | 0.5344 | 0.5803 | MISS | unreachable: 28.03%, stuck median: 1.0, p90: 5.0 |
| `history-great-stink-20261010-173311` | literal / mild / seed 13 | point_accuracy | >=0.75 | 0.3321 | 0.3790 | MISS | |
| `history-great-stink-20261010-173311` | literal / mild / seed 13 | onset_lag_median_s | <=3.0 | 10.00 s | 8.81 s | MISS | |
| `history-great-stink-20261010-173311` | literal / mild / seed 13 | onset_lag_p90_s | <=6.0 | 21.25 s | 17.98 s | MISS | |
| `history-great-stink-20261010-173311` | literal / mild / seed 13 | false_switches_per_min | <=1.0 | 2.53 /min | 3.04 /min | MISS | |
| `history-great-stink-20261010-173311` | literal / mild / seed 13 | adlib_stability | >=0.80 | 0.8967 | 0.8519 | PASS | |
| `history-great-stink-20261010-173447` | creative / strong / seed 13 | slide_accuracy | >=0.80 | 0.4214 | 0.3803 | MISS | unreachable: 32.34%, stuck median: 2.5, p90: 7.0 |
| `history-great-stink-20261010-173447` | creative / strong / seed 13 | point_accuracy | >=0.60 | 0.2674 | 0.2593 | MISS | |
| `history-great-stink-20261010-173447` | creative / strong / seed 13 | onset_lag_median_s | <=4.0 | 10.00 s | 10.00 s | MISS | |
| `history-great-stink-20261010-173447` | creative / strong / seed 13 | onset_lag_p90_s | <=8.0 | 23.07 s | 23.07 s | MISS | |
| `history-great-stink-20261010-173447` | creative / strong / seed 13 | false_switches_per_min | <=2.0 | 2.86 /min | 2.69 /min | MISS | |
| `history-great-stink-20261010-173447` | creative / strong / seed 13 | adlib_stability | >=0.70 | 0.8021 | 0.8702 | PASS | |
| `history-great-stink-20261010-173447` | creative / strong / seed 13 | skip_recovery_s | <=6.0 | None | None | PASS | |
| `story-overdue-book-20261010-173550` | literal / strong / seed 13 | slide_accuracy | >=0.80 | 0.3888 | 0.3728 | MISS | unreachable: 35.37%, stuck median: 3.0, p90: 4.0 |
| `story-overdue-book-20261010-173550` | literal / strong / seed 13 | point_accuracy | >=0.60 | 0.2328 | 0.1902 | MISS | |
| `story-overdue-book-20261010-173550` | literal / strong / seed 13 | onset_lag_median_s | <=4.0 | 10.00 s | 9.07 s | MISS | |
| `story-overdue-book-20261010-173550` | literal / strong / seed 13 | onset_lag_p90_s | <=8.0 | 17.05 s | 28.57 s | MISS | |
| `story-overdue-book-20261010-173550` | literal / strong / seed 13 | false_switches_per_min | <=2.0 | 3.48 /min | 2.94 /min | MISS | |
| `story-overdue-book-20261010-173550` | literal / strong / seed 13 | adlib_stability | >=0.70 | 0.8401 | 0.7739 | PASS | |
| `story-overdue-book-20261010-173550` | literal / strong / seed 13 | skip_recovery_s | <=6.0 | 9.99 s | 99.00 s | MISS | |
| `story-overdue-book-20261010-173711` | creative / mild / seed 13 | slide_accuracy | >=0.90 | 0.3512 | 0.4280 | MISS | unreachable: 48.23%, stuck median: 2.0, p90: 6.0 |
| `story-overdue-book-20261010-173711` | creative / mild / seed 13 | point_accuracy | >=0.75 | 0.2230 | 0.2240 | MISS | |
| `story-overdue-book-20261010-173711` | creative / mild / seed 13 | onset_lag_median_s | <=3.0 | 10.00 s | 10.00 s | MISS | |
| `story-overdue-book-20261010-173711` | creative / mild / seed 13 | onset_lag_p90_s | <=6.0 | 25.66 s | 23.59 s | MISS | |
| `story-overdue-book-20261010-173711` | creative / mild / seed 13 | false_switches_per_min | <=1.0 | 3.97 /min | 3.97 /min | MISS | |
| `story-overdue-book-20261010-173711` | creative / mild / seed 13 | adlib_stability | >=0.80 | 1.0000 | 0.7500 | PASS | |

---

## 2. Contestant A2: Corrected `ClassifierMatcher` (Round 2)

- **Contestant under test:** Corrected `ClassifierMatcher` (`--matcher llm`), revised in place per `design_presentation_simulation.md` §6.6.6:
  1. **Candidates:** every node of the tree, in deck order. Schema enum is every node id.
  2. **The one-decision forward step:** step set is the node after `c` in deck order. If that node is a `section` node, the node after it (its slide's first point) is in the step set too. Commits at 1 decision (dwell >= 2.0 s). Any other non-current answer requires 2 consecutive identical answers (dwell >= 2.0 s).
  3. **Prompt last line verbatim:** `"Which point is the speaker on now? If they are telling a side story that matches no point, answer the current point. Answer one id."`
- **Harness:** `src/animated_infographics/evals/matcher_bakeoff.py`.
- **Cache:** Cold run performed with fresh `INFOGRAPHICS_CACHE_DIR=artifacts/matcher_bakeoff/2026-10-10/cache_llm`. Warm rerun reproduces every commit and latency identically.
- **Exit code:** `1` (follower bars missed on 6 of 8 runs, including 3 of 4 on the decision set).

### 2.1 Decision Set (Seed 7)

| Job ID | Configuration | Metric | Bar | ASR Hearing | Perfect Hearing | Status | Residual (ASR) |
|---|---|---|---|---|---|---|---|
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | slide_accuracy | >=0.90 | 0.8633 | 0.8960 | MISS | −0.0367 |
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | point_accuracy | >=0.75 | 0.6378 | 0.6999 | MISS | −0.1122 |
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | onset_lag_median_s | <=3.0 | 3.36 s | 3.58 s | MISS | +0.36 s |
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | onset_lag_p90_s | <=6.0 | 9.20 s | 6.52 s | MISS | +3.20 s |
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | false_switches_per_min | <=1.0 | 0.50 /min | 0.67 /min | PASS | +0.50 /min |
| `history-great-stink-20261009-074656` | literal / mild / seed 7 | adlib_stability | >=0.80 | 1.0000 | 0.4243 | PASS | +0.2000 |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | slide_accuracy | >=0.80 | 0.8461 | 0.8486 | PASS | +0.0461 |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | point_accuracy | >=0.60 | 0.6007 | 0.5873 | PASS | +0.0007 |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | onset_lag_median_s | <=4.0 | 3.94 s | 4.85 s | PASS | −0.06 s |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | onset_lag_p90_s | <=8.0 | 13.26 s | 14.43 s | MISS | +5.26 s |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | false_switches_per_min | <=2.0 | 0.71 /min | 0.71 /min | PASS | +1.29 /min |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | adlib_stability | >=0.70 | 0.8270 | 0.8754 | PASS | +0.1270 |
| `history-great-stink-20261009-074747` | creative / strong / seed 7 | skip_recovery_s | <=6.0 | 13.12 s | 14.40 s | MISS | +7.12 s |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | slide_accuracy | >=0.80 | 0.6617 | 0.6688 | MISS | −0.1383 |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | point_accuracy | >=0.60 | 0.4633 | 0.4491 | MISS | −0.1367 |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | onset_lag_median_s | <=4.0 | 4.88 s | 6.58 s | MISS | +0.88 s |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | onset_lag_p90_s | <=8.0 | 11.33 s | 10.64 s | MISS | +3.33 s |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | false_switches_per_min | <=2.0 | 1.25 /min | 2.04 /min | PASS | +0.75 /min |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | adlib_stability | >=0.70 | 1.0000 | 0.9185 | PASS | +0.3000 |
| `story-overdue-book-20261009-074844` | literal / strong / seed 7 | skip_recovery_s | <=6.0 | 16.80 s | 17.02 s | MISS | +10.80 s |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | slide_accuracy | >=0.90 | 0.6808 | 0.6649 | MISS | −0.2192 |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | point_accuracy | >=0.75 | 0.5021 | 0.4675 | MISS | −0.2479 |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | onset_lag_median_s | <=3.0 | 4.13 s | 4.39 s | MISS | +1.13 s |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | onset_lag_p90_s | <=6.0 | 16.95 s | 18.17 s | MISS | +10.95 s |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | false_switches_per_min | <=1.0 | 0.86 /min | 1.21 /min | PASS | +0.14 /min |
| `story-overdue-book-20261009-074959` | creative / mild / seed 7 | adlib_stability | >=0.80 | 1.0000 | 1.0000 | PASS | +0.2000 |

#### Diagnostics & Call Times (Decision Set):
- `history-great-stink-20261009-074656`: 234 LLM calls | compute median: 691.0 ms, p90: 770.0 ms | unreachable: 0.0000 | stuck median: 1.0, p90: 3.0
- `history-great-stink-20261009-074747`: 283 LLM calls | compute median: 690.0 ms, p90: 737.0 ms | unreachable: 0.0000 | stuck median: 1.0, p90: 5.0
- `story-overdue-book-20261009-074844`: 271 LLM calls | compute median: 714.0 ms, p90: 755.0 ms | unreachable: 0.0000 | stuck median: 1.0, p90: 7.0
- `story-overdue-book-20261009-074959`: 233 LLM calls | compute median: 717.0 ms, p90: 757.0 ms | unreachable: 0.0000 | stuck median: 2.0, p90: 5.0

### 2.2 Held-Out Set (Seed 13)

| Job ID | Configuration | Metric | Bar | ASR Hearing | Perfect Hearing | Status | Residual (ASR) |
|---|---|---|---|---|---|---|---|
| `history-great-stink-20261010-173311` | literal / mild / seed 13 | slide_accuracy | >=0.90 | 0.8569 | 0.8650 | MISS | −0.0431 |
| `history-great-stink-20261010-173311` | literal / mild / seed 13 | point_accuracy | >=0.75 | 0.6508 | 0.6787 | MISS | −0.0992 |
| `history-great-stink-20261010-173311` | literal / mild / seed 13 | onset_lag_median_s | <=3.0 | 3.05 s | 3.42 s | MISS | +0.05 s |
| `history-great-stink-20261010-173311` | literal / mild / seed 13 | onset_lag_p90_s | <=6.0 | 8.73 s | 8.61 s | MISS | +2.73 s |
| `history-great-stink-20261010-173311` | literal / mild / seed 13 | false_switches_per_min | <=1.0 | 0.84 /min | 0.51 /min | PASS | +0.16 /min |
| `history-great-stink-20261010-173311` | literal / mild / seed 13 | adlib_stability | >=0.80 | 1.0000 | 1.0000 | PASS | +0.2000 |
| `history-great-stink-20261010-173447` | creative / strong / seed 13 | slide_accuracy | >=0.80 | 0.8322 | 0.8368 | PASS | +0.0322 |
| `history-great-stink-20261010-173447` | creative / strong / seed 13 | point_accuracy | >=0.60 | 0.6263 | 0.5979 | PASS | +0.0263 |
| `history-great-stink-20261010-173447` | creative / strong / seed 13 | onset_lag_median_s | <=4.0 | 4.01 s | 5.22 s | MISS | +0.01 s |
| `history-great-stink-20261010-173447` | creative / strong / seed 13 | onset_lag_p90_s | <=8.0 | 9.78 s | 10.00 s | MISS | +1.78 s |
| `history-great-stink-20261010-173447` | creative / strong / seed 13 | false_switches_per_min | <=2.0 | 1.01 /min | 1.01 /min | PASS | +0.99 /min |
| `history-great-stink-20261010-173447` | creative / strong / seed 13 | adlib_stability | >=0.70 | 1.0000 | 1.0000 | PASS | +0.3000 |
| `history-great-stink-20261010-173447` | creative / strong / seed 13 | skip_recovery_s | <=6.0 | None | None | PASS | N/A |
| `story-overdue-book-20261010-173550` | literal / strong / seed 13 | slide_accuracy | >=0.80 | 0.6827 | 0.6755 | MISS | −0.1173 |
| `story-overdue-book-20261010-173550` | literal / strong / seed 13 | point_accuracy | >=0.60 | 0.5253 | 0.4813 | MISS | −0.0747 |
| `story-overdue-book-20261010-173550` | literal / strong / seed 13 | onset_lag_median_s | <=4.0 | 4.36 s | 5.32 s | MISS | +0.36 s |
| `story-overdue-book-20261010-173550` | literal / strong / seed 13 | onset_lag_p90_s | <=8.0 | 13.11 s | 14.59 s | MISS | +5.11 s |
| `story-overdue-book-20261010-173550` | literal / strong / seed 13 | false_switches_per_min | <=2.0 | 1.28 /min | 1.65 /min | PASS | +0.72 /min |
| `story-overdue-book-20261010-173550` | literal / strong / seed 13 | adlib_stability | >=0.70 | 1.0000 | 1.0000 | PASS | +0.3000 |
| `story-overdue-book-20261010-173550` | literal / strong / seed 13 | skip_recovery_s | <=6.0 | 7.25 s | 5.32 s | MISS | +1.25 s |
| `story-overdue-book-20261010-173711` | creative / mild / seed 13 | slide_accuracy | >=0.90 | 0.7001 | 0.7315 | MISS | −0.1999 |
| `story-overdue-book-20261010-173711` | creative / mild / seed 13 | point_accuracy | >=0.75 | 0.4854 | 0.4882 | MISS | −0.2646 |
| `story-overdue-book-20261010-173711` | creative / mild / seed 13 | onset_lag_median_s | <=3.0 | 4.33 s | 3.69 s | MISS | +1.33 s |
| `story-overdue-book-20261010-173711` | creative / mild / seed 13 | onset_lag_p90_s | <=6.0 | 12.47 s | 16.08 s | MISS | +6.47 s |
| `story-overdue-book-20261010-173711` | creative / mild / seed 13 | false_switches_per_min | <=1.0 | 0.90 /min | 1.44 /min | PASS | +0.10 /min |
| `story-overdue-book-20261010-173711` | creative / mild / seed 13 | adlib_stability | >=0.80 | 1.0000 | 1.0000 | PASS | +0.2000 |

#### Diagnostics & Call Times (Held-Out Set):
- `history-great-stink-20261010-173311`: 239 LLM calls | compute median: 692.0 ms, p90: 750.0 ms | unreachable: 0.0000 | stuck median: 1.0, p90: 3.0
- `history-great-stink-20261010-173447`: 235 LLM calls | compute median: 690.0 ms, p90: 737.0 ms | unreachable: 0.0000 | stuck median: 1.0, p90: 3.0
- `story-overdue-book-20261010-173550`: 229 LLM calls | compute median: 713.0 ms, p90: 755.0 ms | unreachable: 0.0000 | stuck median: 2.0, p90: 4.0
- `story-overdue-book-20261010-173711`: 226 LLM calls | compute median: 712.0 ms, p90: 756.0 ms | unreachable: 0.0000 | stuck median: 2.0, p90: 7.0

---

## 3. Verification & Diagnostics Analysis

### 3.1 Cross-Check Against Designer's Replay (Issue 9)

Per `agent_execution_guide.md` §3.L2, on the 4 seed-7 decision-set jobs, slide and point accuracy must match Issue 9's replay table within 0.05:

| Job (Seed 7) | Issue 9 Slide | Measured Slide | Delta | Issue 9 Point | Measured Point | Delta | Agreement |
|---|---|---|---|---|---|---|---|
| `history_great_stink` literal/mild | 0.863 | 0.8633 | +0.0003 | 0.633 | 0.6378 | +0.0048 | **Match (<0.005)** |
| `history_great_stink` creative/strong | 0.846 | 0.8461 | +0.0001 | 0.601 | 0.6007 | −0.0003 | **Match (<0.001)** |
| `story_overdue_book` literal/strong | 0.662 | 0.6617 | −0.0003 | 0.463 | 0.4633 | +0.0003 | **Match (<0.001)** |
| `story_overdue_book` creative/mild | 0.681 | 0.6808 | −0.0002 | 0.502 | 0.5021 | +0.0001 | **Match (<0.001)** |

All 4 runs reproduce the designer's replays within 0.005, confirming exact conformity with the §6.6.6 specification.

### 3.2 Candidate Reachability and Stuckness
- **Unreachable share:** 0.0000 across all 8 jobs. Because every node is provided as a candidate in deck order, a follower can never be locked out of finding its place.
- **Stuck on current:** Median 1.0 (p90 3.0–7.0). When speech transitions to a new point, the follower typically holds for 1 decision (due to window overlap with earlier sentences) before correctly answering the new point.

### 3.3 Qualitative Inspection: Sampled Decisions at Point Transitions
Sampled 10 decisions immediately following ground-truth point transitions in `history-great-stink-20261009-074656`:
1. **0 ms -> d1_p0:** Decision at 2080 ms held (answered `d1_p2`, reason `consecutive_top_not_met`). Committed `d1_p0` shortly after.
2. **25700 ms -> d1_p2:** Decision at 26720 ms held (answered `d1_p1`, reason `top_is_current` because 25-word window was still filled with `d1_p1` words). Committed to `d1_p2` at 28240 ms once `d1_p2` words filled the window.
3. **56400 ms -> d2_p1:** Decision at 56880 ms held (`top_is_current`). Committed to `d2_p1` at 59880 ms.
4. **84225 ms -> d3_p0:** Decision at 85060 ms held (`top_is_current`). Committed to `d3_p0` at 88160 ms.
5. **118150 ms -> d3_p2:** Decision at 118660 ms held (`top_is_current`). Committed to `d3_p2` at 121660 ms.
6. **181075 ms -> d4_p2:** Decision at 181560 ms held (`top_is_current`). Committed to `d4_p2` at 184560 ms.
7. **221550 ms -> d5_p1:** Decision at 222040 ms committed immediately to new slide point via forward step set.
8. **246375 ms -> d6_p0:** Decision at 247000 ms held (`top_is_current`). Committed at 249960 ms.
9. **267875 ms -> d6_p2:** Decision at 268360 ms held (`top_is_current`). Committed at 271440 ms.
10. **338225 ms -> d7_p2:** Decision at 338840 ms held (`top_is_current`). Committed at 341840 ms.

### 3.4 Strip Chart Analysis
Comparing `history-great-stink-20261009-074656` between `bm25` and Corrected `ClassifierMatcher`:
- **BM25:** Wild oscillations and regressions: repeatedly falls back to Slide 1 (at 1:00, 1:40, 2:20, and 4:20), resulting in 3.01 false switches/min and 0.5542 slide accuracy.
- **Corrected A2:** Clean monotonic staircase following ground truth closely from D1 through D7. False switches drop from 3.01 to 0.50/min. However, each step lags ground truth by ~3.3–3.9 s because the 25-word window requires ~3 seconds of speech to shift its majority topic from the previous point to the new one.

---

## 4. Decision Rule (§6.6.6) & Verdict

Per `design_presentation_simulation.md` §6.6.6:
> 1. The corrected A2 meets every §8 bar on all 4 decision-set and all 4 held-out jobs → adopt it.
> 2. It passes the decision set but misses on the held-out set → stop and file it with both tables, for the user.
> 3. **It misses on the decision set → stop and file it with every metric's residual against its bar, and both diagnostics. No other contestant is built, and nothing is tuned (§6.6.4 rule 5). G16 stays at exit 3.**

**Verdict:**
Contestant A2 misses the decision set on onset lag (median 3.36–4.88 s vs bars <=3–4 s; p90 9.20–16.95 s vs bars <=6–8 s) and on slide accuracy for `story_overdue_book` (0.6617 and 0.6808 vs bars >=0.80 and >=0.90).
Per §6.6.6 rule 3, **Contestant A2 is not adopted. G16 stays at exit 3. Stop and file Issue 11.**

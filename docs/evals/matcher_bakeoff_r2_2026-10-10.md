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

## 2. Contestant A2: Corrected `ClassifierMatcher` (Pending L2 Evaluation)

Will be populated in item L2 per `design_presentation_simulation.md` §6.6.6.

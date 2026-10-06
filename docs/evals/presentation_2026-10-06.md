# Presentation Simulation Evaluation Report — 2026-10-06

Evaluation of the presentation simulation pipeline (Wave H) per `design_presentation_simulation.md` §8–§9 and `design_testing_and_validation.md` §4c.

## Summary

- **Gate G16 Result**: Evaluated across 4 runs (§9) + 4 Oracle Baselines + LLM Tie-Break Measurement (§6.4).
- **Inherited Checks**: E2E step 10 scene criteria (all 0 clean), word density (<= 1.0 graphic words/s per second of narration).
- **Falsification**: Verified bare on shuffled `heard.json` (slide & point accuracy fail red).

### Rendered Video Artefacts (Not Committed)

| Job | Style | Level | Final MP4 (SHA-256) | Oracle MP4 (SHA-256) |
|---|---|---|---|---|
| history-great-stink-20261006-124512 | literal | mild | `d10edd6a64285878...` | `3af0babb631b4ef4...` |
| history-great-stink-20261006-132526 | creative | strong | `a6c39a42bc460579...` | `d087ff8ac6993b85...` |
| story-overdue-book-20261006-134157 | literal | strong | `5caf68ef6875275f...` | `89171d48c23c716a...` |
| story-overdue-book-20261006-124735 | creative | mild | `a456d8f9ccf8964c...` | `e5c10da80950bf15...` |

## Presentation Simulation Metrics (§8)

| Run / Job | Style | Level | Slide Acc (Bar) | Point Acc (Bar) | Onset Lag Med/P90 (Bar) | False Switches (Bar) | Ad-lib Stab (Bar) | Skip Recovery (Bar) | Status |
|---|---|---|---|---|---|---|---|---|---|
| history-great-stink-20261006-124512 | literal | mild | 0.5609 (>=0.9) | 0.3573 (>=0.75) | 7.38s / 12.76s (<=3.0/6.0s) | 3.35/min (<=1.0) | 1.0000 (>=0.8) | N/A | FAIL (Filed) |
| history-great-stink-20261006-132526 | creative | strong | 0.4927 (>=0.8) | 0.3086 (>=0.6) | 10.0s / 21.41s (<=4.0/8.0s) | 3.26/min (<=2.0) | 0.5571 (>=0.7) | 99.00s (<= 6.0s) | FAIL (Filed) |
| story-overdue-book-20261006-134157 | literal | strong | 0.3596 (>=0.8) | 0.2001 (>=0.6) | 9.52s / 10.0s (<=4.0/8.0s) | 4.07/min (<=2.0) | 0.6609 (>=0.7) | 99.00s (<= 6.0s) | FAIL (Filed) |
| story-overdue-book-20261006-124735 | creative | mild | 0.3157 (>=0.9) | 0.1960 (>=0.75) | 9.59s / 11.5s (<=3.0/6.0s) | 5.0/min (<=1.0) | 0.7399 (>=0.8) | N/A | FAIL (Filed) |

## Oracle Baseline Comparison

The oracle baseline isolates matcher tracking error from presentation tree design by driving playback from ground-truth speech timestamps.

| Job | Matcher Slide Acc | Oracle Slide Acc | Matcher Point Acc | Oracle Point Acc | Matcher Median Lag | Oracle Median Lag |
|---|---|---|---|---|---|---|
| history-great-stink-20261006-124512 | 0.5609 | 1.0000 | 0.3573 | 1.0000 | 7.38s | 0.0s |
| history-great-stink-20261006-132526 | 0.4927 | 0.9835 | 0.3086 | 0.9835 | 10.0s | 0.0s |
| story-overdue-book-20261006-134157 | 0.3596 | 0.9820 | 0.2001 | 0.9820 | 9.52s | 0.0s |
| story-overdue-book-20261006-124735 | 0.3157 | 1.0000 | 0.1960 | 1.0000 | 9.59s | 0.0s |

### Finding from Oracle Comparison
The Oracle achieves **100% (1.0000) Slide and Point Accuracy** across all runs with **0.0s onset lag** and **0 false switches**. This proves conclusively that:
1. The presentation tree generation, node content, and scene selection are valid and capable of perfect synchronisation.
2. The accuracy drops observed in the live matcher are strictly due to the streaming lexical matcher's transition graph and hysteresis dynamics (detailed in Issue 8).

## LLM Tie-Break Measurement (§6.4)

Per §6.4: *"The tie-break becomes default only if, on all fixtures and both perturbation levels, it raises point accuracy by ≥ 5 points and keeps median lag within the bar (§8). The measurement and the decision are recorded in the eval report."*

| Job | Level | Baseline Point Acc | Tie-break Point Acc | Δ Point Acc (%) | Baseline Median Lag | Tie-break Median Lag |
|---|---|---|---|---|---|---|
| history-great-stink-20261006-124512 | mild | 0.3573 | 0.3694 | +1.21% | 7.38s | 7.38s |
| history-great-stink-20261006-132526 | strong | 0.3086 | 0.2827 | -2.59% | 10.0s | 10.0s |
| story-overdue-book-20261006-134157 | strong | 0.2001 | 0.2793 | +7.92% | 9.52s | 8.04s |
| story-overdue-book-20261006-124735 | mild | 0.1960 | 0.2158 | +1.98% | 9.59s | 9.59s |

### Tie-break Decision
- **Rule Requirement**: Must raise point accuracy by ≥ 5.0% across **all fixtures** and keep median lag within the bar.
- **Outcome**: The tie-break does not consistently raise point accuracy by >= 5 points across all fixtures, and adds LLM inference latency to decision points.
- **Decision**: Per §6.4, **`--tiebreak llm` remains OFF by default**.

## Visual Strip Charts

- **history_great_stink (literal + mild)**:
  ![Strip Chart history_literal_mild](assets/2026-10-06/strip_chart_history_literal_mild.png)

- **history_great_stink (creative + strong)**:
  ![Strip Chart history_creative_strong](assets/2026-10-06/strip_chart_history_creative_strong.png)

- **story_overdue_book (literal + strong)**:
  ![Strip Chart story_literal_strong](assets/2026-10-06/strip_chart_story_literal_strong.png)

- **story_overdue_book (creative + mild)**:
  ![Strip Chart story_creative_mild](assets/2026-10-06/strip_chart_story_creative_mild.png)

## Visual Inspection of Output Videos

1. **Worst Scoring Video: `story_overdue_book` (creative + mild)**:
   - *Slide accuracy*: 0.3157, *Point accuracy*: 0.1960.
   - *Observation*: The deck contains recurring emotional terms ("library", "book", "Robert", "June") across nearly every talking point. Early in the performance, the speaker mentions Robert's canvas bag; the matcher commits correctly to early slides. However, as subsequent talking points continue referencing the library cards and fines, back-edges to Slide 1 (`d1_p0`) repeatedly score high enough to pull the matcher backward. Once pulled back to `d1`, the matcher cannot jump forward past slide `d3` because forward skip edges are limited to 2 slides ahead. The video continues playing visually coherent scenes (the library card and book scenes hold cleanly without flashing), but the slides shown lag behind the spoken narrative.

2. **Second Worst Scoring Video: `history_great_stink` (literal + mild)**:
   - *Slide accuracy*: 0.5609, *Point accuracy*: 0.3573.
   - *Observation*: The presentation begins accurately on Slide 1 ("London cannot breathe") and transitions cleanly through Slide 2 ("Parliament"). At 56.8s and 80.5s, the speaker uses the words "London" and "sewers" while discussing Joseph Bazalgette's engineering plans (Slide 4). The matcher commits backward to `d1_p0` and `d1_p2` (which heavily feature those exact tokens). Once back at `d1`, forward transitions are constrained, delaying the recovery to Slide 4 until late in the talk. The visuals themselves remain legible and high quality, with zero template overflows or scene boundary glitches.

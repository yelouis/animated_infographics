# Agent Execution Guide — Active Build: Wave K (measurement fixes, 4 items), then Wave L (follower Round 2, 3 items) — October 10, 2026

**You are an engineering agent with no memory of this project.** Waves A–J are built, committed and pushed (head `main`).
- **The verification.** Waves I and J were independently verified by the designer on October 9, 2026. **All 12 items do what their specs say,** and every Wave I target is fixed on fresh output (`ongoing_general_errors.md` §1, §3).
- **The bake-off.** Wave J's bake-off ended with neither follower adopted. The designer traced most of that to a defect in **the designer's own** §6.6 spec: a lost follower could never get back. Replays with that corrected roughly double the LLM follower's accuracy, but lag still misses (Issue 9, rewritten).
- **The user's decisions (October 10, 2026):** *"For issue 9 select Option A, for issue 10 select Option A. Update the agent_execution_guide to reflect these choices"*.
  - **Issue 9 → A:** Round 2 of the bake-off. The corrected LLM follower is judged against the unchanged bars on fresh held-out talks. That is **Wave L**.
  - **Issue 10 → A:** long-story budgets are judged on the total time per narration minute only. That is part of **K1**.
- **Wave K comes first.** It fixes three measurement defects (the budget exit code, onset lag, per-decision compute time) that Round 2 is judged by.

**Status:** **Active Build: Wave K** (K1–K4), then **Wave L** (L1–L3), in the §2 order. No user decision is pending. L2 may end in a filed **Issue 11**, whose `Your selection:` line will belong to the user.

**Every number and literal string in this guide and the design docs is a decision, not a suggestion.**

**The product, in one paragraph.** A local-only CLI that turns a text story (narrated by local TTS) or an audio narration into a 1080×1920 animated explainer video. It has karaoke captions, a persistent avatar cast, checked illustrations, a blind critic, and a mandatory review gate. It has two styles:
- **literal**: the pictures show what is said;
- **creative**: a director adds motifs and callbacks, visual metaphors and small asides, under the user's "small embellishments" license.

An offline **presentation simulation** derives a deck from a script, builds an animation tree from the deck alone, perturbs the script into a "performed" talk, follows it with a causal matcher, and scores the result.

**The lessons that shape this wave** (`ongoing_general_errors.md` §2):
- **2.14:** a gate's exit code must state its bars. The budget script still writes FAIL and exits 0.
- **2.17:** an evaluation must measure what it claims. The onset-lag scorer counted a point already on screen as a 10 s miss, and the harness's "per-decision" latency was measured over commits only.
- **Still binding:** 2.8, 2.10, 2.12, 2.13.

---

## 0. Standing constraints (apply to every item)

1. **The battery is the regression bar.** After every item, run the full battery (G1–G16) bare and update §1.3. Read every exit code bare.
   - **The expected G16 code is 3** (follower bars missed) **until L3 adopts the corrected A2; then it is 0.**
   - A 1 is always a regression. A 0 before L3 is impossible without a follower change, so investigate it.
2. **Fully local at runtime.** No cloud API, and no network except loopback. **Pull no new models**: `gemma4:26b`, Kokoro, mlx-whisper and FLUX.2 klein 4B only.
3. **Python (Pydantic) is the source of truth for every contract.** Generated files are never hand-edited, and G8 covers every contract change (K3).
4. **Templates read time only through the clock.**
5. **The review gate is mandatory** for video and presentation jobs alike. No auto-approve.
6. **The planner never crashes the pipeline.** Every LLM call goes through `run_with_retries`. Every new error string is copied **verbatim** from the design doc that defines it.
7. **Red first, on real inputs.** Before building, run the item's falsifying check against the current code, using the recorded artefacts this guide names, and record the failure.
8. **One item = one Conventional Commit, scope = item id** (`fix(k1): …`). Put the WHY and the red and green runs in the body. Push after every item. Never amend a pushed commit.
9. **Record each resolution in the same commit,** as one line under a new "**Wave K:**" heading in `ongoing_general_errors.md` §3: `K<n> — <title> — git log --grep "(k<n>)" — <measured result>`.
10. **When this guide and a design doc disagree, stop and file it.**
11. Every stage log ends in `llm_calls=<n> cache_hits=<m> elapsed_ms=<t>`.
12. **Nothing in the package changes the environment at import.** Any run that generates images must show 0 asset execution errors to count.
13. **Ids:** waves A–L; deferred features DF1–DF9; live constraints LC1–LC6; issues up to 10 (the next is Issue 11).
14. **Eval reports are named by date.** A second E2E or budget run on the same day overwrites the first. Commit each report in the item that produced it.
15. **The follower changes only in L2, and only as `design_presentation_simulation.md` §6.6.6 says.**
    - **In Wave K and L1:** do not change any matcher's candidates, window, prompt, commit rule, costs or tie-break. L1 only *records* candidate ids.
    - K2 changes **how onset lag is measured**, to match §8's definition; it does not change what any follower does.
    - **Never:** change the §8 bars or the frozen scorer during Round 2, regenerate `corpus_r2`, or tune §6.6.6's constants to pass.

---

## 1. Verified baseline (October 9, 2026; the designer's re-run of Waves I and J)

### 1.1 Environment

`doctor`: 22 checks OK.
- M4 Max 64 GB; ffmpeg 8.1; Node v26.5.0; Python 3.12 (uv).
- Ollama with `gemma4:26b`; Kokoro 0.9.4; mlx-whisper 0.4.3.
- mflux (`flux2-klein-4b`); Remotion 4.0.528.

### 1.2 Repository

- Waves A–H: `4df212a` … `6150482`.
- Wave I: `ae0d00f` … `e71006e`.
- Wave J: `b11dfde` … `a3fe8c2`.
- Per-item verdicts: `ongoing_general_errors.md` §3.

### 1.3 Gates (run bare October 9, 2026 by the designer; the regression bar)

| # | Gate | Result |
|---|---|---|
| G1–G3 | ruff / format / mypy | exit 0 |
| G4 | `uv run pytest -q -m "not slow"` | exit 0 · **411 passed** |
| G5–G7 | renderer typecheck / lint / vitest | exit 0 · 21 vitest |
| G8 | schema sync | exit 0 |
| G9 | renderer purity | exit 0 |
| G10 | gallery | exit 0 · 82 goldens, 0 overflows, 0 overlaps |
| G11 | `uv run pytest -q -m slow` | exit 0 · **43 passed** (378 s) |
| G12 | `./scripts/e2e.sh` | exit 0 (916 s) · steps 1–10 · 0.52–0.83 graphic words/s |
| G13 | offline | exit 0 (263 s) |
| G14 | doctor | exit 0 · 22 OK |
| G15 | `./scripts/creative_e2e.sh` | exit 0 (1,534 s) · 0.68 / 0.82 graphic words/s · callbacks 4 dots = 4 tokens · 0 spoilers |
| G16 | `./scripts/presentation_sim.sh` | **exit 3** (3,263 s) · four fresh jobs · falsifications (a)–(c) pass · follower slide 0.33–0.56, point 0.20–0.35, lag median 7.4–10 s |
| Budget | `story_recipe_box`, cold | 218.02 / 193.65 / 411.67 s (≤ 390 / 210 / 600), 0 cache hits, 0 execution errors |
| Budget (long) | literal | total **138.90 s/min (≤ 170)**. Watch numbers: new 58.43, render 80.47 s/min. The render bar was removed under Issue 10 → A; the script's exit 0 on its FAIL row is fixed in K1 |
| Budget (long creative) | creative | 77.05 / 79.54 / 156.58 s/min (≤ 110 / 85 / 195), 9 images, not degraded |

### 1.4 Measurements that shaped Wave K and Issue 9 (October 9, 2026)

| What | Result |
|---|---|
| Budget fail-open | `measure_budget.sh:292–295` computes PASS/FAIL and writes it, but nothing turns FAIL into an exit code: the long literal run wrote FAIL and exited 0 |
| Onset-lag scorer | `score.py:146` ignores any commit made more than 0.5 s before the point's first word, and `:154` then scores the point as a 10 s miss. A point shown early and still on screen is "missed" (`history-great-stink-20261009-074656`, d4_p1, in the designer's replay). A later revisit counts as the onset (lags of 74.7 s in October 6 runs), while a point never shown counts only 10 s |
| Harness latency | `matcher_bakeoff.py:278` takes "per decision" compute percentiles over **commits only**, including the 0 ms initial commit. Holds carry no compute time (`contracts/playback.py:48–57`). The reported "A2 p90 598 ms" is therefore not a per-decision figure; the replay's cache entries show 0.65–0.78 s per call |
| Follower trap (Issue 9) | The true point was unreachable 46–60% of the talk for A2, 68–81% for A1 and 32–62% for `bm25`. The designer's corrections cut it to 2–9% and raise A2's slide accuracy to 0.66–0.86 |

---

## 2. Execution order

| # | Item | Why this position |
|---|---|---|
| K1 | The budget script's exit code states its bars; long stories judged on the total (Issue 10 → A) | Independent and small |
| K2 | Onset lag measured as §8 defines it | Changes every follower's lag numbers. It must land before Round 2, and before K3 re-baselines the harness |
| K3 | Compute time recorded and reported per decision | Needs the harness to be re-baselined after K2 |
| K4 | Re-measure; close-out of Wave K | The Round 2 corpus must be scored by the finished scorer |
| L1 | The Round 2 corpus (seed 7 + a fresh seed 13) and the diagnostics | The yardstick first. It needs K2's scorer and K3's per-decision times |
| L2 | The corrected A2; Round 2; decide | Needs L1's corpus and diagnostics |
| L3 | Adopt or file; close out | Needs the decision |

---

## 3. The items

### K1 — The budget script's exit code states its bars

**What this means for the user:** today a budget run can say FAIL in its report and still look green to anything reading its exit code. After this item, a missed time bar is visible as a missed time bar, and long stories are judged on the total time, as the user chose (Issue 10 → A).

**The gap:**
- `scripts/measure_budget.sh:238–241` (primary) and `:292–295` (long) compute PASS/FAIL per span, but the script exits 0 regardless.
- The designer's long literal run on October 9, 2026 wrote `render … 80.47 s/min … ≤ 80 s/min … FAIL` and exited 0.
- **Contract:** `design_testing_and_validation.md` §5: step 4 (revised) and the long-story table (total only, Issue 10 → A); and the "budget exit codes" row in §2.

**Implementation:**
1. Add `src/animated_infographics/evals/budget_verdict.py` with `budget_verdict(spans: dict[str, float], bars: dict[str, float]) -> int`. It returns 0 when every span is ≤ its bar and 3 otherwise. A span exactly at its bar passes.
2. In `measure_budget.sh`, after the report is written, compute the verdict through that function and print one line per span: `BUDGET <span> <value> <bar> PASS|FAIL`. Exit with the function's code. Mechanical failures keep exit 1 (the existing `fail`). **No test-only switch in the script.**
3. **The bars passed in.**
   - The primary run passes its three spans (≤ 390 / 210 / 600 s).
   - A `--long` run passes **only its total** (≤ 170 s/min literal, ≤ 195 creative).
   - The long run's `new` and `render` per minute are printed and reported as **watch numbers**, next to their former bars (90 / 80 literal, 110 / 85 creative), never as PASS/FAIL.
4. **The report** states the exit code and, on 3, the line `exit 3: a budget bar was missed — file it with the per-stage timings`.

**Validation:**
- **Red first:** the designer's October 9 long literal run wrote a FAIL row and exited 0 (§1.3). Confirm in the source that nothing after `:292–295` exits on a FAIL, and record it. The function in step 1 does not exist yet, so its unit cases are red by construction.
- **Green:**
  - the unit row: all under → 0; one span 0.01 over → 3; exactly at the bar → 0;
  - the October 9 long numbers (render 80.47, total 138.90 s/min) give exit 0;
  - a real `./scripts/measure_budget.sh --long` run exits 0 with its total ≤ 170 s/min. Record the code, the total and both watch numbers.
- **Falsify:** make `budget_verdict` always return 0 → the "one span over" unit case goes red. Restore.

**Blast radius:** `evals/budget_verdict.py` (new), `scripts/measure_budget.sh`, and tests.

---

### K2 — Onset lag measured as §8 defines it

**What this means for the user:** the lag number is how far the visuals trail the speaker. Today it can call a point "missed" when it was on screen all along, and call a point "74 s late" because of a later revisit. Every follower decision is judged on this number.

**The gap:**
- `src/animated_infographics/presentation/score.py:117–160` (`calculate_onset_lag`):
  - it matches the first commit to a valid node with `at_ms >= first_t - 500` (`:146`), so a node committed earlier and still on screen is not found;
  - an unmatched point scores a fixed 10.0 s (`:154`), so a miss can beat a long lag;
  - any later commit, including a revisit minutes later, counts as the onset.
- **Contract:** `design_presentation_simulation.md` §8, the revised onset-lag definition, and the "onset lag" row in `design_testing_and_validation.md` §2.

**Implementation** (§8, verbatim rules):
1. **Per point,** with `t0` the start of its first spoken sentence:
   - `t_end` is the start of the first later sentence whose label is not this point (ad-libs and back-references included), or the end of the talk.
   - The valid nodes are the point's node and, for point 0, its slide's `section` node.
2. **The lag:**
   - if a valid node is on screen at `t0`, the lag is 0;
   - otherwise, the first commit to a valid node in `(t0, t_end)`, minus `t0`;
   - otherwise, the point is missed and scores `max(10.0, (t_end − t0)/1000)`.
3. **Median and p90** as today. The oracle must still score 0.0 on every point.
4. **Re-baseline the harness.** Re-run `score` on the 8 frozen corpus jobs, so the J1 baseline check (`bm25` reproduces each job's own `presentation_score.json`) compares against the new scorer. The corpus hashes cover only the inputs, so they do not change; verify that they still pass.

**Validation:**
- **Red first:** the new unit case "node already on screen at the first word → 0" fails against today's scorer, which gives 10.0.
- **Green:**
  - the unit row;
  - the oracle still scores 0.0 everywhere;
  - `bm25` through the harness reproduces the re-scored corpus within 0.01;
  - re-score the designer's G16 fresh jobs and the bake-off runs (`artifacts/matcher_bakeoff/2026-10-09/{bm25,anticipate,llm}_run/*`) and report before/after lag medians per job in the commit body.
- **Falsify:** restore the `- 500` window → the early-shown unit case goes red. Restore.

**Blast radius:** `presentation/score.py`, the corpus jobs' `presentation_score.json` (outputs, not hashed), tests, and the report addendum (K4).

---

### K3 — Compute time recorded and reported per decision

**What this means for the user:** whether an LLM follower could run live depends on how long **each decision** takes. Today that number is measured over a handful of commits, plus a 0 ms placeholder.

**The gap:**
- `PlaybackHold` (`contracts/playback.py:48–57`) has no compute time.
- `evals/matcher_bakeoff.py:278` takes percentiles over `pb.commits`, which includes the initial t = 0 commit.
- **Contract:** `design_presentation_simulation.md` §6.6.2 ("the median and p90 call time per decision"), `design_data_contracts.md` §10 (`playback.json`), and the "decision compute time" row in `design_testing_and_validation.md` §2.

**Implementation:**
1. `PlaybackHold` gains `compute_ms: int = Field(default=0, ge=0)` (G8). All three matchers (`LiveMatcher`, `AnticipateMatcher`, `ClassifierMatcher`) fill it with the same measured value a commit at that decision would have carried (for A2, the cached or live call time plus the non-LLM time).
2. The harness computes median and p90 over every decision: holds, plus commits after the first.
3. Re-run the harness with `--matcher llm` on the corpus (warm cache, so it is fast), and add its per-decision median and p90 to the bake-off report as an addendum.

**Validation:**
- **Red first:** the stub-matcher unit case (a fixed 700 ms per decision) gives a p90 that includes the 0 ms commit today.
- **Green:** the unit row: median = p90 = 700; G8 in sync; the addendum's numbers.
- **Falsify:** include the initial commit again → the unit case goes red. Restore.

**Blast radius:** `contracts/playback.py` and generated files, the three matchers in `presentation/match.py` (hold construction only), `evals/matcher_bakeoff.py`, tests, and the report addendum.

---

### K4 — Re-measure; close-out

1. **The full battery G1–G16, bare.** Expected: all 0 except **G16 = 3**.
2. **The three cold budgets.** Record their exit codes. Long literal is 0 or 3, with 3 filed under Issue 10 while it is open.
3. **Update the docs:**
   - `ongoing_general_errors.md` §3: the Wave K lines;
   - §1: a short paragraph for Wave K;
   - Issue 9: a one-line note with the K2-corrected lag of the four seed-7 `bm25` jobs.
4. **Update §1.3** (re-measured) and add Wave K to §5.1. **Do not stop:** continue with L1.

---

### L1 — The Round 2 corpus and the diagnostics

**What this means for the user:** Round 2 is judged on talks nobody has looked at, and the report says *why* the follower lags, not just by how much.

**The gap:**
- **The held-out set has been seen.** Round 1's held-out jobs (seed 11) were looked at by the designer's replays.
- **No diagnostics:** the harness (`evals/matcher_bakeoff.py`) reports neither the share of decisions whose true node was not a candidate nor how long the follower kept answering "current" after the speaker moved on.
- **No candidate record:** a playback does not record which candidates each decision considered.
- **Contract:** `design_presentation_simulation.md` §6.6.6 (corpus and diagnostics), and the "bake-off diagnostics" row in `design_testing_and_validation.md` §2.

**Implementation:**
1. **The candidate record.** `PlaybackCommit` and `PlaybackHold` gain `candidate_ids: list[str] = []` (G8). Every matcher fills it with the ids it considered at that decision; for `LiveMatcher`, the current node plus the nodes reachable by an edge. It is diagnostics only: `compose` and `score` ignore it, and **no matcher reads the ground truth.**
2. **The diagnostics,** computed in the harness from the ground truth (as it already does for scoring):
   - **"unreachable share":** among all decisions, the share whose true node at the decision time (for a point 0, its slide's section also counts) is not in `candidate_ids`;
   - **"stuck on current":** after each change of the true point, the number of consecutive decisions whose answer or top candidate was the current node while the current node was not the true one. Report its median and p90 per job.
3. **The corpus,** built only after K4:
   - copy the 4 seed-7 jobs from `artifacts/matcher_bakeoff/2026-10-09/corpus/` into `artifacts/matcher_bakeoff/<date>/corpus_r2/`, and verify that their hashes equal Round 1's;
   - create **4 new seed-13 jobs**, one per §9 configuration: `present-sim … --seed 13 --matcher bm25 --jobs-dir <corpus_r2>`, then `score` (the K2 scorer);
   - check: 0 asset execution errors; creative jobs not degraded, each with a `director.json`;
   - write `corpus_r2/corpus.json` with all 8 jobs and their hashes.
4. **The baseline:** the harness with `--matcher bm25` on `corpus_r2`, written as the "before" of `docs/evals/matcher_bakeoff_r2_<date>.md`, with both diagnostics.

**Validation:**
- **Red first:** today the harness has no diagnostics, and `PlaybackHold` has no `candidate_ids`.
- **Green:**
  - the unit row: re-run Round 1's A2 on `history-great-stink-20261009-074656` through the harness so that candidates are recorded, and "unreachable share" is ≥ 0.40.
    - Use `INFOGRAPHICS_CACHE_DIR=artifacts/matcher_bakeoff/2026-10-09/cache_llm`, so the warm cache reproduces Round 1's decisions.
    - This must run **before L2** changes `ClassifierMatcher`; that is why L1 comes first.
  - `bm25` reproduces every `corpus_r2` job's own score within 0.01;
  - the corpus hashes are verified before and after the run.
- **Falsify:** make "unreachable share" ignore `candidate_ids` and return 0.0 → the Round 1 case goes red. Restore.

**Blast radius:** `contracts/playback.py` and generated files, the three matchers (recording only), `evals/matcher_bakeoff.py`, tests, the corpus (artifacts), and the report.

---

### L2 — The corrected A2; Round 2; decide

**What this means for the user:** the LLM follower can always find its place again after a wrong turn, steps onto a new slide in one decision, and holds only during side stories. The user chose to test this on fresh talks against the original bars.

**The gap** (`presentation/match.py`, `ClassifierMatcher`):
- **Candidates:** the current node, the next 3 nodes and earlier points (`:825–842`). One slide behind, the true point is unreachable.
- **The forward step** is a single node (`:904`), so a slide's first point needs two decisions after its section.
- **The prompt's last line** says "or you are unsure, answer the current point" (`:767`).
- **Contract:** `design_presentation_simulation.md` §6.6.6, verbatim.

**Implementation** (§6.6.6, revised in place; `playback.json`'s `matcher` stays `llm`):
1. **Candidates:** every node of the tree, in deck order. The schema enum is every node id.
2. **The step set:** the node after `c`, plus the node after that when the first is a `section` node. An answer in the step set commits at one decision point. Any other non-current answer needs 2 consecutive identical answers. Dwell is ≥ 2.0 s in every case.
3. **The prompt's last line,** verbatim: `Which point is the speaker on now? If they are telling a side story that matches no point, answer the current point. Answer one id.`
4. **Everything else** in §6.6.2 is unchanged, as is K3's per-decision compute time.
5. **Round 2:** run the harness with `--matcher llm` on `corpus_r2`, **cold** (a fresh `INFOGRAPHICS_CACHE_DIR`), so that call times are real. Then run it with `--hearing perfect`.
6. **Decide by §6.6.6's rule,** quoting it in the report:
   - **Every §8 bar on all 8 jobs → adopted.** Go to L3.
   - **The decision set passes but the held-out set misses → STOP.** File **Issue 11** with both tables, following `.agents/skills/bug_documentation_guidelines/SKILL.md` (options included), and wait.
   - **The decision set misses → STOP.** File **Issue 11** with each metric's residual against its bar, both diagnostics, "perfect hearing" and the call-time percentiles, and wait. Nothing is tuned.

**Validation:**
- **Red first:** the unit case "6 nodes behind; the stub answers the true point twice → commit" fails against today's `ClassifierMatcher`, because the true point is not a candidate.
- **Green:**
  - the "corrected A2, Round 2" unit row;
  - causality;
  - a warm rerun reproduces the cold run's commits and latencies exactly;
  - "unreachable share" is 0.0 on all 8 jobs.
- **Cross-check against the designer's replay.** On the 4 seed-7 jobs, slide and point accuracy should land within 0.05 of Issue 9's last column (slide 0.863 / 0.846 / 0.662 / 0.681; point 0.633 / 0.601 / 0.463 / 0.502). K2 changes lag, not accuracy. A larger gap means the build differs from §6.6.6: find out why before deciding.
- **Falsify:** restore Round 1's "next 3 nodes" candidate block → "unreachable share" > 0 on at least one decision-set job, and the 6-behind unit case goes red. Restore.
- **Look:**
  - read 10 decisions sampled at true point changes in one decision-set job: prompt, answer, ground truth;
  - open one strip chart, against `bm25`'s;
  - describe both in the report.

**Blast radius:** `presentation/match.py` (`ClassifierMatcher` only), tests, and the report.

---

### L3 — Adopt or file; close out

**What this means for the user:** either presentations now follow the speaker well enough to meet the bars, and the presentation gate turns green honestly, or the user gets one more evidence-based decision.

1. **If L2 adopted the corrected A2:**
   - make `llm` the default of `present-sim` (`cli.py`) and the matcher G16 gates. G16's falsifications use it.
   - Run G16 bare on fresh jobs: **exit 0**. Record the BAR table. If it is not 0, STOP and file it; never re-tune. G16 now makes about 250 LLM calls per job, so expect it to take ≈ 12 min longer.
   - Update the docs:
     - `design_presentation_simulation.md` §6.6.6 gains a short **Result** paragraph;
     - `design_future_live_and_video.md` §4 records the adopted matcher and its per-decision p90 for DF4;
     - Issue 9 moves to the resolved index;
     - the README documents `--matcher`.
2. **If L2 stopped:** Issue 11 is filed. G16 stays at exit 3.
3. **Full battery, bare** (G1–G16). Update §1.3.
4. **Rewrite this guide** to **Queue Complete** (or **Queue Complete — waiting on Issue 11**). **Then stop. Do not invent work.**

---

## 4. Deferred — do NOT start

- **Issue 9's options that were not selected:** B (restated bars), C (an embedding contestant) and D (a pause). Do not build them. A1 (`anticipate`) is retired from Round 2.
- **Budget bars:** apart from removing the long-story span bars (K1, Issue 10 → A), change none.
- **DF1–DF9** (`ongoing_general_errors.md` §4). The real-time parts of DF4 (live mode) stay deferred:
  - slide import (.pptx / PDF / Google Slides);
  - a browser player on a requestAnimationFrame clock;
  - the microphone, streaming ASR and the webcam.
- **Known limitations, unscheduled:**
  - a quotation spanning two sentences can be split between beats;
  - the critic's `emotion_beat` *who* reading is noisy;
  - R7 treats reported speech without quotation marks as narration;
  - the spoiler rule treats a name token that is also a common word ("June") as naming.

---

## 5. Do NOT change

### 5.1 Already delivered

- Waves **A** (verified September 25), **B** (September 26), **C/D** (October 3), **E** and **F** (October 4), **G** and **H** (October 6), and **I** and **J** (October 9, 2026), all independently verified.
- One line per item, with verdicts: `ongoing_general_errors.md` §3. Nothing marked "✓" is reworked beyond what a Wave K item names.

### 5.2 Accepted equivalents (checked; do not "fix" these back)

- The sync probe is drawn inside each scene's layer.
- The antimeridian bbox handling.
- `image_prompt` strips a trailing period.
- `FitText`'s 0.35-line ascender allowance.
- The gallery's TypeScript port of `item_frames`.
- `CHECKSUMS` paths are relative to `fixtures/`.
- `plan_report.llm_calls` counts the storyboard stage only.
- Node 26.
- At-limit strings are reported, not failed.
- `AudioLayer`'s volume clamp and `loopVolumeCurveBehavior="extend"`.
- The pretty-printed lakes file.
- The critic's cast list has no `Cast:` label.
- `battery.sh` exports `HF_HOME`.
- E4's icon block follows any disagreement message.
- R6 keeps the original alternate even when it equals the new primary.
- F3's era normalisation runs before the length check.
- **New, October 6, 2026:**
  - **`num_predict=2048` in the deck stage.** `design_presentation_simulation.md` §2 suggested 1536; 8–10 slides need ≈ 1,520–1,600 tokens.
  - **The presentation profile also skips R1.** `section_title` replaces the title card. There were 0 `title_card` nodes in 4 trees, and I7 makes R1's second half an assertion.
  - **Motif ids are free strings** (e.g. `motif_blue_ink`). The spec's `m1` was an example, and ids never reach the screen.
- **New, October 9, 2026:**
  - **The overlap probe skips elements nested inside a `data-occupies` element.** The enclosing box already contains them.
  - **The harness calls the stage functions directly** (`run_follow_stage`, `run_compose_stage`, `compute_presentation_score`), as specified, rather than shelling out to the CLI.

### 5.3 User decisions

**September 23, 2026:**
- Offline first; a template library.
- History + Reddit-style stories; text + audio inputs.
- Mixed imagery; Python + TypeScript/Remotion; fully local.
- 9:16; karaoke captions; flat editorial vector; 1–3 min videos in about 10 min. *For the long fixtures, the budget is restated per minute, as the user's 4–6-minute choice implied.*
- Scenes + a persistent cast; single narrator; a mandatory review gate; music + SFX.
- Live mode later, with the webcam in a corner.

**September 24–25, 2026:** Issues 1–5 (verbatim in `ongoing_general_errors.md` §3).

**September 27, 2026:**
- **Issue 6 → D:** "I think the paraphrasing is fine."
- **Live presentations:** "For real-time presentations, it makes sense to show timelines and repeated graphics to drive home the point."
- **Issue 7 → A** (Wave D).

**October 5, 2026:**
- **A style library**, keeping today's output as one style, with a creative style that "adds something to the story".
- **Creative ingredients:** motifs & callbacks, visual metaphors, foreshadowing & reveals, visual gags & asides.
- **License:** "Small embellishments".
- **Stories:** 4–6 minutes.
- **The presentation simulation,** as described above.
- **Slide import:** not now.
- **"Make sure to not actually perform any coding and just update the docs + execution guide for another agent to implement".** This applies to the designer; you implement.

**October 10, 2026:** *"For issue 9 select Option A, for issue 10 select Option A. Update the agent_execution_guide to reflect these choices"*.
- **Issue 9 → A:** Round 2 with the corrected A2 against the unchanged bars, on a fresh held-out set (Wave L).
- **Issue 10 → A:** long-story budgets are judged on the total only (K1).

**October 7, 2026:**
- **Issue 8 → Option A:** *"For issue 8, select Option A and write the agent execution guide to reflect that with validation"*.
- **Designer's validation, added under that instruction:** a held-out seed-11 set. If it disagrees with the decision set, that is filed for the user, not decided by you.

### 5.4 Invariants and intentional design decisions

**New (October 9, 2026):**
- **Every follower state can reach every correct state** (lesson 2.17), and any follower evaluation reports the share of talk time during which the true point was not a candidate.
- **Missing a point is never scored better than being late to it** (§8 onset lag, K2).

**New (October 7, 2026):**
- **The follower bake-off is judged on a frozen corpus by the unchanged scorer,** and no contestant is tuned on it. The held-out set exists to catch exactly that.
- **Every follower sees only the deck** (and sentences anticipated from the deck) **and the words heard so far.** `LiveMatcher` (`bm25`) stays as the measured baseline.

**New (October 6, 2026):**
- **An overlay's anchor follows from its kind:** token top-right, thought and label top-left, prop bottom-left. Overlap is measured on the rendered gallery, never in a hand-kept table.
- **The renderer has no data defaults for creative devices:** no fallback icons, and no fallback dots.
- **A name reaches the screen only after the narration has said it.** Avatars may come earlier.
- **Fallbacks never hide execution errors.** A gate fails when a generator never ran.
- **A gate's exit code states its bars.** A known, filed miss is exit 3, never 0.
- **A stage reused in another pipeline brings all of its checks.**

**From October 5, 2026:**
- **A style changes how, never what is true.** Grounding, the critic, word caps, validators and the review gate apply in every style.
- **`literal` is byte-identical to the pre-Wave-G pipeline.**
- **Creative items only ever add interpretation or small embellishments.** The license check removes anything else, and a failed check removes the item.
- **Plants show only the object, never its meaning,** and come ≥ 3 beats before their payoff.
- **Overlays only on the 10 allowed templates;** at most one token and one aside per scene. Overlay text counts as graphic words.
- **In the presentation simulation:**
  - the tree sees only the deck;
  - the matcher sees only heard words;
  - only `score` sees the ground truth;
  - the matcher is causal;
  - nothing leads the voice.

**From Waves C–F:**
- Enforcement after the round; the `unknown`-emotion rule; R7 never replaces quoted speech.
- The icon list in prompts; no environment changes at import.
- Dates are never stats; no placeholder or instruction text; era stamps are narration years or nothing.
- Quoted speech is kept whole; passage framing; keyed text-thread answers; contact resolution.
- 3-attempt critic retries; no ids on screen; caption spacing.
- Missing inputs are errors; paraphrased dialogue is allowed.
- `WORD_CAPS` is the single source; R6/R7; karaoke captions.

**Unchanged:**
- Job-local inputs are authoritative; `run_with_retries` everywhere; no LLM length constraints.
- Scrim ≥ 85%; the text check is skipped for text-expected descriptions.
- A blind critic with one call per scene; the timeline label rule; the voice asymmetry.
- Avatars only; no auto-approve; a 200 ms scene lead (video jobs); absolute frames; timings computed in Python.
- Grounding is a hard gate; navy text on cast colours; never FLUX klein 9B.
- Beats are not human-editable; the offline gate stays; fixtures are original texts; commit scope = item id.

### 5.5 Assessed and rejected — do NOT re-propose

- **Every item listed in the Wave F guide's §5.5**, which is preserved in git at `69c0378`.
- **From October 5, 2026:**
  - **Slide import in these waves**, per the user.
  - **A real-time player in these waves.**
  - **Letting the tree or the matcher see the script, the performance or the ground truth.** It makes the simulation meaningless.
  - **Creative embellishments beyond the license:** new events, dialogue, facts, contradictions, or plants that reveal the twist.
  - **Raising word caps for creative scenes.**
  - **A creative style that changes the cast's look or the illustration `STYLE`.**
- **New, October 6, 2026:**
  - **Making G16 green by tuning edge costs, loosening the §8 bars or enabling the tie-break.** Wave J's rule decides.
  - **Tuning a contestant on the corpus,** whether windows, margins, costs, candidate sets, prompts or temperatures. A miss is filed with its evidence.
  - **Raising the back-edge cost as the fix for Issue 8.** It was measured: at best slide 0.55–0.59.
  - **Re-introducing renderer defaults** for dots or overlay icons.
  - **Loosening the motif spacing (3 / 20) or the spoiler rule** to keep a fixture from degrading. File it instead.
  - **Re-running Round 1's contestants unchanged.** Their candidate sets contain a trap (Issue 9). A1 also measured weak with the trap removed (slide 0.34–0.57, 5–8 false switches per minute).
  - **Removing "book" (or any word) from `TEXT_EXPECTED_WORDS`, or skipping rule 6 for metaphors,** to stop a degradation. A book in a FLUX image grows lettering that the skipped text check would never catch; salvage is the fix.

---

## 6. Where the contracts live

| What | Where |
|---|---|
| Styles, the director, the license, overlays, creative bars | `design_styles.md` §3.3–3.7 |
| The presentation simulation; the follower bake-off (§6.6), its Round 1 result (§6.6.5) and **Round 2** (§6.6.6); the onset-lag definition (§8) | `design_presentation_simulation.md` |
| Job files incl. `playback.json` (holds gain `compute_ms`) | `design_data_contracts.md` §10 |
| The name rule (item 6), R8 and the rule order | `design_planner.md` §4, §6 |
| Templates; the callback dot count; word caps | `design_templates.md` §2.18, §5 |
| Test rows (Wave K: onset lag, decision compute time, budget exit codes; Wave L: corrected A2, bake-off diagnostics), gates, the budget rules (long stories: total only) | `design_testing_and_validation.md` §2–§5 |
| Issues 9 and 10 (decided October 10), lessons (2.13–2.17), verdicts, the deferred list | `ongoing_general_errors.md` |

---

## 7. Validation standard

- **Red first, on real inputs** (lesson 2.6). Every item names its recorded artefacts.
- **Measure outcomes before and after** (2.7).
- **Measure the rendered result** (2.8, 2.15).
- **Enforce rules on the final result** (2.10).
- **Name the defect class** (2.12).
- **A gate must be able to fail, must fail closed, and its exit code must state its bars** (2.13, 2.14).
- **An evaluation must measure what it names** (2.17): a lag that calls an on-screen point "missed", or a "per-decision" time taken over commits, is a defect.
- **Never loosen a bar to pass it.** File it with the measurement and options.

---

## 8. THE LOOP

```
(1) Is there an approved item? Wave K (K1–K4), then Wave L (L1–L3), in §2
    order. If all are done, STOP. Never start DF1–DF9 or anything not in §3.
    Never fill in a `Your selection:` line.
(2) Read the item and EVERY design section it names. Copy rules, thresholds
    and error strings VERBATIM.
(3) RED FIRST on the recorded artefacts the item names; record the failure.
(4) Build only what the item says. Nothing from §5.5.
(5) GREEN; then falsify (break, see red, restore, see green).
(6) Open every artefact and describe it.
(7) Full battery, bare. Update §1.3.
(8) ONE commit, scope = item id (`fix(k1): …`, `feat(l2): …`). WHY +
    red/green in the body. ONE line under "Wave K" or "Wave L" in
    ongoing_general_errors.md §3.
    Never amend after pushing.
(9) git push origin main.
(10) Next item. A failed bar or an impossible rule → file it and stop at
    that item until the user selects. In L2, §6.6.6's rule says exactly
    when a result means "adopt" and when it means "stop and file".
```

---

## 9. Definition of Done: Waves K and L

**Wave K**

- [ ] K1: `measure_budget.sh` exits 0 / 3 / 1 by its bars; long runs are judged on the total only, with `new` and `render` shown as watch numbers; the verdict is unit-tested and falsified; a real long run's code is recorded.
- [ ] K2: onset lag follows §8 (on screen at the first word → 0; the first run only; missing never beats late). The oracle stays at 0, the harness is re-baselined, and before/after numbers are recorded.
- [ ] K3: every hold carries `compute_ms`; the harness reports per-decision percentiles; the A2 addendum is written.
- [ ] §1.3 re-measured bare (G1–G16, three budgets with their exit codes); continue to Wave L.

**Wave L**
- [ ] L1: every decision records `candidate_ids`; the harness reports "unreachable share" and "stuck on current"; `corpus_r2` (seed 7 copied, 4 new seed-13 jobs) is frozen with hashes; the `bm25` baseline is written.
- [ ] L2: `ClassifierMatcher` matches §6.6.6 verbatim. Round 2 is run cold on all 8 jobs, with "unreachable share" 0.0, the cross-check against Issue 9's replay within 0.05, and the decision written out with the rule.
- [ ] L3: `llm` is the default and G16 on fresh jobs exits **0**; or Issue 11 is filed and G16 stays at 3.
- [ ] §1.3 re-measured bare (G1–G16).
- [ ] This guide rewritten to **Queue Complete** (or **Queue Complete — waiting on Issue 11**). **Then stop. Do not invent work.**

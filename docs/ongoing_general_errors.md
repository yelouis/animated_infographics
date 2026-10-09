# Engineering Issues & Decisions — Working Log

**What this file is:** the live queue of open issues, the decisions the user has made or still has to make, the deferred features and their triggers, and a one-line index of resolved work. The execution guide (`docs/agent_execution_guide.md`) is the build spec; this file is where findings and choices live.

**Filing format** is in `.agents/skills/bug_documentation_guidelines/SKILL.md`. Open issues end with a `Your selection: _____` line. **That line belongs to the user, and an agent must never fill it in.**

---

## 1. Open & in-flight

**Wave B (B1–B17) was delivered as 17 commits (`cad065d`…`beb4c4f`) and independently verified on September 26, 2026.** Every gate G1–G14 was re-run bare in a separate session (numbers in `agent_execution_guide.md` §1), and the cold budget was re-measured. Each item's source was read against its spec: **all 17 do what their specs say** (per-item verdicts in §3).

**Waves C (C1–C8) and D (D1–D5) were delivered as 13 commits (`12209d2`…`98db684`) and independently verified on October 3, 2026.**
- Every gate G1–G14 was re-run bare in a separate session: 254 fast tests, the slow suite, the E2E (913 s), the offline gate and the cold budget (199.2 s / 191.6 s / 390.8 s, 0 cache hits). All green; numbers in `agent_execution_guide.md` §1.
- Each item's source was read against its spec: **all 13 do what their specs say** (verdicts in §3).
- The Wave D bars hold on real renders: every job ≤ 1.0 graphic word/s (0.49–0.81) with ≥ 1/3 light scenes.

**Wave E (E1–E6) was delivered as 6 commits (`26e0f2c`…`66b377f`) and independently verified on October 4, 2026, in a separate session.**
- **Gates:** every gate G1–G14 was re-run bare: 257 fast tests, 37 slow tests, the E2E (1,033 s, steps 1–9), the offline gate (226 s) and the cold budget (202.8 s / 200.2 s / 403.0 s, 0 cache hits).
- **Source:** each item was read against its spec, and **all 6 do what their specs say** (verdicts in §3).
- **Every Wave E target is fixed on screen.** Rose's note is back as her quote. "It's a joke.", "Rose?" and "Meredith was impressed" are neutral. The narration line no longer belongs to The Soldiers. Icons depict their labels. There are 0 armchairs in 12 rendered jobs (two E2E runs).

**Wave F (F1–F4) was delivered as 4 commits (`084d666`…`c88a69f`) and independently verified on October 4, 2026, in a separate session.**
- **Gates:** every gate G1–G14 was re-run bare: 265 fast tests, 37 slow tests, the E2E (859 s, steps 1–10), the offline gate (235 s) and the cold budget (205.8 s / 191.3 s / 397.1 s, 0 cache hits). All green.
- **Source:** each item was read against its spec, and **all 4 do what their specs say** (verdicts in §3).
- **Every Wave F target is fixed on screen**, checked in the renders:
  - "She had died in 2016, and March 3rd was her birthday." is shown as the sentence, not a counter;
  - the "March 3rd" counters are gone;
  - the emu comparison reads "9,860 rounds / 10 per bird" against "986 kills", with no "Icon:" text;
  - every era stamp is a narration year ("1919", "1932") or absent.
- **The new E2E step 10 is a real gate.** It reports 0 in every column on both Wave F runs. Run on the pre-Wave-F jobs, it caught 3 date stats and 1–3 invented stamps per job, and exited 1.
- **Real-output review found no new defect that needs work.** The remaining observations are watch items or deliberately unscheduled behaviour, listed in `agent_execution_guide.md` §2. **The queue is complete.**

**Waves G (G1–G6) and H (H1–H6) were delivered as 12 commits (`afb1b5f`…`6150482`) and independently verified on October 6, 2026, in a separate session.**
- **Gates:** every gate G1–G16 was re-run bare, along with the three cold budgets: 350 fast tests, 43 slow tests, 19 vitest, the gallery (59 goldens, 0 overflows), the E2E, the offline gate, doctor, the creative E2E and the presentation simulation. Numbers are in `agent_execution_guide.md` §1.3. **A green G16 means less than it says** (below).
- **Source:** each item was read against its spec. **11 of the 12 do what their specs say.** G4's callback "seen before" dots do not. `compile._get_item_count` (`compile.py:62–79`) returns 0 for `callback`, so `item_frames` is empty. `callback.tsx:75–77` then falls back to `[15, 27]`, so every callback shows exactly two dots, whatever the motif's history: both creative E2E callbacks had 4 earlier tokens on screen. Its `ding` cues, one per item frame, have no frames to fire on.
- **What works on screen:**
  - "thick soup" for the Thames;
  - "invisible poison" for miasma;
  - the "smell blocker" label over Parliament and the "so gross" thought;
  - the pump callback at "Snow got a pub…".
  
  Creative word density is 0.74 and 0.84 graphic words/s.
- **Real-output review found nine defects that the gates could not see. Six of them trace to the designer's specs, not to the code.**
  1. **Asides sit on the motif token and on the avatar.** Thought and label asides are anchored top-right, where the motif token is (`design_styles.md` §3.6), and over `character_intro`'s 440 px avatar. The overlay test checks a hand-written slot table (`renderer/src/theme/overlayLayout.ts:68–104`). That table omits the avatar, and the test never checks one overlay against another. Spec gap.
  2. **A thought aside may carry neither icon nor text.** Validator 7 does not forbid it, and the renderer draws a generic `ChatCircleDots` "…" bubble. Seen on `story_overdue_book` s001 (a `character_intro`). Spec gap.
  3. **Motif names are never license-checked, and nothing spaces a motif's appearances.**
     - "Silver Pump Handle": the narration never says "silver".
     - "Blue ink pen": the narration never says "pen".
     - The ink motif's echoes cluster at beats 15, 18 and 19, and its payoff comes at 51, 32 beats (≈ 2.5 min) after the last echo.
     
     Spec gap.
  4. **G16 is green while every follower bar fails.** `presentation_sim.sh:336` prints "FAIL (Filed)", and the script ends `exit 0` (`:424`). Its falsification (`:226–268`) asserts that shuffled speech scores below the mild bars. The real, unshuffled runs score below them too (slide 0.32–0.56), so the check cannot fail. The designer's guide said both "every §8 bar on every run" and "met or filed". Spec gap.
     - **Worse, G16 does not run the simulation when it finds an old job.** `presentation_sim.sh:52–80` scans the git-ignored `jobs/` directory for any job with the same fixture, style, level and seed, and re-scores it. On this machine that means it never builds anything.
     - **The evidence:** the designer's battery run (1,416 s, exit 0) only re-scored the agent's four jobs from 12:45–13:41 on October 6, and H6's "re-measure" did the same.
     - **Unspecified, not a code defect:** the designer's §4c never said "fresh jobs dir", although §4 and §4b do.
  5. **Creative presentation jobs skip the license check and the overlays, and lose the director silently.**
     - `presentation/tree.py:155` calls the director but never the license check, so unchecked metaphors reached the screen.
     - `tree.py:494` and `compose.py:219` hard-code `overlays: []`.
     - When the director fails, the job silently runs literal. `story_overdue_book` creative/mild has no `director.json`, and its tree's template counts are identical to the literal run's. The cause is defect 9: every attempt keeps a "book" metaphor.
     
     The designer's spec said only "the style applies as in `design_styles.md`". Spec gap.
  6. **Names appear on screen before the narration says them.** This affects every style, and the defect predates Wave G: **7 of 32** named displays in the 7 most recent storyboards. Examples:
     - "Robert Okafor" attributed to the anonymous note, in two runs;
     - "June Lind" in a relationship map while the narration still says "J.", in two runs;
     - "Sofia" introduced on "a woman walked in";
     - "John Snow" introduced on "One man disagreed." and shown in a map at s004.
     
     All 7 are `llm planned`.
  7. **No image was generated in any of the agent's four presentation runs,** with 5–7 failures each. Every entry failed in ≈ 970 ms with `mflux exited with code 1`, inside `huggingface_hub.snapshot_download`, with `attempts: []`. That is an environment failure, not lettering. The videos rendered with fallbacks, and every gate stayed green.
  8. **The presentation matcher misses every accuracy bar on every run.** The tree is not at fault: the oracle scores 0.98–1.00. This is **Issue 8**, rewritten below with new measurements and options.
  9. **One stuck metaphor silently turns a creative video literal, and the creative budget never noticed.**
     - **The cause:** the director is all-or-nothing. With a cold cache after `ollama stop` (the budget's conditions), all 3 attempts on `story_overdue_book` kept "A paper book … mailbox flag" for beat 24. Rule 6 rejects "book", so the job degraded to literal.
     - **What the budget reported:** 5 images, 3 text checks and 114 LLM calls, the literal signature (a creative run gives 9, 7 and 117), and "PASS" for a creative budget. The agent's committed creative budget has the identical signature. So no creative budget has yet measured a creative video.
     - **The same failure in the presentation path:** the overdue deck fails identically ("…burying a single small book"; defect 5).
     - **Not reproducible warm:** with the model already loaded, the same story planned 1 motif, 4 metaphors and 5 asides.
     - **Evidence:** the attempts are recorded in `docs/evals/assets/2026-10-06/wave_i_director_attempts.json`.
     - **The spec gaps:** the designer's spec never showed the model rule 6's word list (lesson 2.11), and specified degradation without salvage.
- **Defects 1–7 and 9 are Wave I** (I1–I9 in the guide), within approved behaviour. **Defect 8 needs the user's selection.**

**Wave I (I1–I9) was delivered as 9 commits (`ae0d00f`…`HEAD`) and independently verified on October 8–9, 2026.**
- **Gates:** every gate G1–G15 exited 0 bare, and G16 exited 3 bare as specified (Issue 8 follower misses; mechanics and all 3 falsifications clean). 388 fast tests, 43 slow tests, 21 vitest, 59 gallery goldens (0 overflows, hold motion verified, caption spacing verified).
- **Cold budgets:** all 3 measured cold with 0 cache hits and 0 asset execution errors:
  - primary: 200.52 s / 189.37 s / 389.89 s (bars ≤ 390 / 210 / 600 s)
  - long literal: 56.80 / 78.22 / 135.01 s/min (bars ≤ 90 / 80 / 170 s/min)
  - long creative: 76.17 / 79.54 / 155.71 s/min (bars ≤ 110 / 85 / 195 s/min), style_degraded=False, 9 images (≥ 2 metaphors)
- **Cold planner eval:** 6/6 fixtures valid bare, 0 independent validation violations, names_before_narration = 0 on all 6, critic regression 8/8 PASS, text audit PASS.
- **Visual artefacts verified on real renders:** callback dots count real appearances (I1), asides anchored top-left with 0 overlap on motif tokens (I2), empty thought bubble eliminated on overdue s001 (I3), motif spacing and salvage verified (I4), 7 former spoiler scenes clean (I5), asset execution failures caught (I6), and presentation metaphor nodes and images generated (I7).

**One open decision: Issue 9.** Waves I and J are complete through J3. In the Wave J bake-off, neither Contestant A1 nor Contestant A2 met the §8 accuracy bars on the frozen corpus. Issue 9 is filed below awaiting user selection.

## ⚠️ Unresolved Issues & Suggestions

### Issue 8: The presentation follower cannot track paraphrased speech with lexical matching

**Status**: ✅ Decided: **Option A**, by the user in chat on October 7, 2026. It is being built as **Wave J** (`agent_execution_guide.md`); the contract is `design_presentation_simulation.md` §6.6.
- **Validation added by the designer:** each contestant must also pass a held-out set (the same four configurations at seed 11). If the held-out result disagrees with the decision set, that is filed for the user, not decided by the agent.
- **The original filing:** by the implementing agent on October 6, 2026; **re-measured and rewritten by the designer the same day.** Every run misses every accuracy bar. The tree is not the cause: the oracle (each point shown from its first spoken word) scores 1.00, 0.98, 0.98 and 1.00. The follower is.

| Run (`jobs/…`) | Slide (bar) | Point (bar) | Lag median / p90 (bar) | False switches (bar) |
|---|---|---|---|---|
| `history-great-stink-20261006-124512`, literal/mild | 0.56 (≥ 0.90) | 0.36 (≥ 0.75) | 7.4 s / 12.8 s (≤ 3 / 6 s) | 3.35/min (≤ 1.0) |
| `history-great-stink-20261006-132526`, creative/strong | 0.49 (≥ 0.80) | 0.31 (≥ 0.60) | 10.0 s / 21.4 s (≤ 4 / 8 s) | 3.26/min (≤ 2.0) |
| `story-overdue-book-20261006-134157`, literal/strong | 0.36 (≥ 0.80) | 0.20 (≥ 0.60) | 9.5 s / 10.0 s (≤ 4 / 8 s) | 4.08/min (≤ 2.0) |
| `story-overdue-book-20261006-124735`, creative/mild | 0.32 (≥ 0.90) | 0.20 (≥ 0.75) | 9.6 s / 11.5 s (≤ 3 / 6 s) | 5.01/min (≤ 1.0) |

**Reproduced at HEAD.** The designer re-ran G16 into a fresh jobs dir (`artifacts/presentation_sim/verify_20261006_224207/jobs`), building four new jobs. Every number above reproduced within 0.05:
- slide 0.558, 0.493, 0.365 and 0.316;
- point 0.352, 0.309, 0.205 and 0.196;
- oracle 1.00, 0.98, 0.98 and 1.00.

The LLM tie-break changed point accuracy by +1.4, −2.6, +0.8 and 0.0 points.

**What the designer measured** by replaying the agent's own `LiveMatcher` on the recorded `heard.json` files:
- **Wrong backward commits are about half of all commits:** 17, 18, 17 and 24 per run.
- **Correct switches arrive 2.9–8.5 s after the point's first word.** Several points are never shown.
- **The cause is the 20-word window, which holds ≈ 8 s of speech.** A new point's words outnumber the old point's only halfway through it. **The 20-word window is the designer's spec value** (`design_presentation_simulation.md` §6.1).
- **The agent's original Option A (raise the back cost) was tested and cannot reach the bars.** The edge-cost variants on the same four runs:

| Variant | Slide | Point | Lag median | False/min |
|---|---|---|---|---|
| Delivered (back 0.5) | 0.32–0.56 | 0.20–0.36 | 7.4–10.0 s | 3.3–5.0 |
| Back 1.0 | 0.30–0.57 | 0.20–0.36 | 7.4–10.0 s | 3.4–4.7 |
| Back 2.0 | 0.39–0.54 | 0.23–0.34 | 7.4–10.0 s | 2.8–4.5 |
| **Back 4.0 (best)** | **0.55–0.59** | **0.31–0.39** | 6.6–10.0 s | 2.0–2.7 |
| No back edges at all | 0.45–0.55 | 0.26–0.30 | 9.6–10.0 s | 1.0–1.25 |
| Back 2.0 + skip anywhere ahead | 0.49–0.61 | 0.32–0.39 | 6.6–10.8 s | 2.5–4.3 |

- **Even with no back edges at all, slide accuracy is 0.45–0.55.** So back-edge trapping is a symptom. The disease is that a 12-word deck point and a paraphrase of it share too few words for BM25 to tell, quickly, which point is being spoken.
- **The LLM tie-break** (`--tiebreak llm`, measured by the agent) adds 1–8 points of point accuracy. By its §6.4 rule it stays off.

**Option A (recommended)**: **Bake-off of two deck-only matchers, using the existing models; adopt by rule.** Build A1, replay it on the four recorded `heard.json` files, and run G16. If it meets every §8 bar on all four runs, adopt it and stop. Otherwise build A2 and do the same. If neither meets the bars, file both sets of numbers with the best per-metric results and stop.
  - **A1, anticipated speech + forward tracker (no LLM in the live loop).**
    - **At tree time, from the deck only:** one LLM call per point writes 4 short sentences a presenter might say while covering it. They are stored on the node, and the node's BM25 document becomes the point text plus those 4 sentences.
    - **Live:** the window shrinks to the last **10** heard words.
    - Only the current node and its next 3 nodes are scored at each decision point.
    - **Moving forward to the next node** needs one decision point with a margin ≥ 0.5.
    - **Skips and backs** keep the 2-consecutive-tops rule, with a margin ≥ 1.5.
    - Dwell stays at 2 s.
    - The isolation test extends to the new call: it may see only the deck.
  - **A2, LLM point classifier.**
    - At each decision point, one `gemma4:26b` call receives the current slide's points, the next 3 points, the titles of earlier slides, and the last 25 heard words. It answers with one node id, from an enum.
    - A move to the next node commits on one answer; any other move needs the same answer twice in a row.
    - The call's measured compute time is already counted in the simulated latency (§6.3).
  - *Pros*: Both attack the real cause (vocabulary overlap and window lag), not the symptom. Both keep the isolation invariant and add no model. A1 is deterministic and cheap live; A2 understands paraphrase best. The rule decides between them on numbers, not on taste.
  - *Cons*:
    - A1 adds ~22 LLM calls per tree (≈ 20–30 s).
    - A2 adds ~200–300 LLM calls per 5-minute talk (≈ 2–4 min offline), and live it is viable only if each call finishes well under the 1.5 s decision cadence.
    - A lag median ≤ 3 s may be out of reach for any causal matcher, since a point must be heard before it can be recognised. The bake-off measures this, and Option E stays available afterwards.

**Option B**: **A1 only.** Build only the anticipated-speech tracker, and file its numbers if it misses.
  - *Pros*: The smallest change, with no LLM in the live loop: the live path stays a few milliseconds per decision.
  - *Cons*: If paraphrase still defeats BM25 (likely on the `strong` level, where 30–50% of sentences are reworded), a second round is needed for A2 anyway.

**Option C**: **A2 only.** Replace BM25 with the LLM classifier.
  - *Pros*: The best understanding of paraphrase and ad-libs; the edge costs become a prior rather than the decision.
  - *Cons*: The heaviest compute (above). The live mode inherits a model call every 1.5 s, and that call's latency counts toward the onset-lag bar.

**Option D**: **Option A plus A3, a local embedding model.**
- **The model:** pull a small embedding model into the existing Ollama (e.g. `nomic-embed-text`, ≈ 0.3 GB; the agent records the real size with `ollama show`).
- **Scoring:** the cosine similarity between the last 15 heard words and each node's point text and anticipated sentences.
- **The bake-off:** A3 joins as a third contestant, with the same adoption rule.

  - *Pros*: Embeddings are the standard tool for matching paraphrase; they are fast (milliseconds per window) and need no LLM call in the live loop.
  - *Cons*: It lifts the standing "no new models" constraint (fully local still holds). One more model in `doctor`, the offline gate and the setup script.

**Option E**: **Keep lexical matching with back cost 4.0, and restate the §8 bars at the measured level.** The bars would become slide ≥ 0.55, point ≥ 0.30, lag median ≤ 10 s and false switches ≤ 3/min, for both levels.
  - *Pros*: No new work beyond one constant; G16 can go green honestly.
  - *Cons*: On screen, the deck is wrong about 40–45% of the time and visuals trail the voice by 7–10 s. That is not a usable presentation, and prepared mode (DF4) would inherit it.

Your selection: **Option A**. Given by the user in chat on October 7, 2026, verbatim: *"For issue 8, select Option A and write the agent execution guide to reflect that with validation"*. Recorded by the designer.

---

### Issue 9: Neither follower contestant met the accuracy bars in the Wave J bake-off

**Status**: ⚠️ Confirmed Unresolved — `docs/evals/matcher_bakeoff_2026-10-09.md`: Contestant A1 (`anticipate`) and Contestant A2 (`llm`) both missed all accuracy bars on all 4 decision-set jobs in the frozen corpus bake-off. A1 scored slide accuracy 0.1789–0.2466 (bar ≥ 0.80–0.90) and point accuracy 0.1412–0.1946 (bar ≥ 0.60–0.75). A2 scored slide accuracy 0.3390–0.3962 and point accuracy 0.2271–0.2859. BM25 baseline remains highest on literal/mild (0.5542 / 0.3682); A2 is highest on creative/strong (0.3804 / 0.2322) and creative/mild (0.3437 / 0.2859). Perfect hearing diagnostic confirms tracking error is algorithmic, not ASR-driven (A2 slide 0.3233–0.3805 under synthetic ground-truth speech). G16 remains at exit 3 per §6.6.4 rule 3.

#### Measured Results: Decision Set (Seed 7)

| Job Configuration | Metric | Bar | BM25 Baseline | Contestant A1 | Contestant A2 | Best Result | Perfect Hearing (A2) |
|---|---|---|---|---|---|---|---|
| `history-great-stink`, literal/mild | slide_accuracy | ≥ 0.90 | **0.5542** | 0.1789 | 0.3962 | **0.5542** (BM25) | 0.3654 |
| `history-great-stink`, literal/mild | point_accuracy | ≥ 0.75 | **0.3682** | 0.1412 | 0.2859 | **0.3682** (BM25) | 0.2782 |
| `history-great-stink`, literal/mild | onset_lag_median_s | ≤ 3.0 | **7.38 s** | 10.00 s | 10.00 s | **7.38 s** (BM25) | 10.00 s |
| `history-great-stink`, literal/mild | false_switches_per_min | ≤ 1.0 | **3.01 /min** | 4.52 /min | 4.02 /min | **3.01 /min** (BM25) | 3.52 /min |
| `history-great-stink`, creative/strong | slide_accuracy | ≥ 0.80 | 0.3348 | 0.2183 | **0.3804** | **0.3804** (A2) | 0.3805 |
| `history-great-stink`, creative/strong | point_accuracy | ≥ 0.60 | 0.2224 | 0.1727 | **0.2322** | **0.2322** (A2) | 0.2549 |
| `history-great-stink`, creative/strong | onset_lag_median_s | ≤ 4.0 | **10.00 s** | **10.00 s** | 32.15 s | **10.00 s** (BM25/A1) | 10.00 s |
| `history-great-stink`, creative/strong | false_switches_per_min | ≤ 2.0 | **3.26 /min** | 4.82 /min | 3.97 /min | **3.26 /min** (BM25) | 3.69 /min |
| `story-overdue-book`, literal/strong | slide_accuracy | ≥ 0.80 | **0.3634** | 0.2092 | 0.3390 | **0.3634** (BM25) | 0.3233 |
| `story-overdue-book`, literal/strong | point_accuracy | ≥ 0.60 | 0.2039 | 0.1575 | **0.2271** | **0.2271** (A2) | 0.2255 |
| `story-overdue-book`, literal/strong | onset_lag_median_s | ≤ 4.0 | 9.59 s | 10.00 s | **5.49 s** | **5.49 s** (A2) | 5.28 s |
| `story-overdue-book`, literal/strong | false_switches_per_min | ≤ 2.0 | **4.07 /min** | 5.95 /min | 4.39 /min | **4.07 /min** (BM25) | 4.39 /min |
| `story-overdue-book`, creative/mild | slide_accuracy | ≥ 0.90 | 0.3176 | 0.2466 | **0.3437** | **0.3437** (A2) | 0.3399 |
| `story-overdue-book`, creative/mild | point_accuracy | ≥ 0.75 | 0.1959 | 0.1946 | **0.2859** | **0.2859** (A2) | 0.2647 |
| `story-overdue-book`, creative/mild | onset_lag_median_s | ≤ 3.0 | 10.00 s | 10.00 s | **5.86 s** | **5.86 s** (A2) | 6.56 s |
| `story-overdue-book`, creative/mild | false_switches_per_min | ≤ 1.0 | 5.00 /min | 5.87 /min | **3.62 /min** | **3.62 /min** (A2) | 3.46 /min |

**What the bake-off proved:**
- **Tracking failure is algorithmic, not acoustic:** Replaying ground-truth synthetic hearing (`--hearing perfect`) left accuracy virtually unchanged (A2 slide 0.32–0.38, point 0.23–0.28). Eliminating ASR WER does not fix follower tracking.
- **A1 failure mechanism:** Pre-generating 4 conversational sentences per point expanded lexical overlap across all candidates. Because the candidate set included backward points with low transition cost (0.5), early nodes with common keywords repeatedly outscored forward nodes, trapping the follower between D1 and D2 for entire talks.
- **A2 failure mechanism & viability:** A2's median compute latency is 429–484 ms and P90 is 598 ms, easily satisfying the 1.5 s live cadence bar (`live-viable: yes`). However, error analysis showed two primary failure modes:
  1. *Current-node confirmation bias:* The prompt instructs the model to answer the current point when unsure or between points. Once any delay occurs, the model repeatedly confirms $c$, pinning the follower while narration moves on.
  2. *Intermediate section title barriers:* Transitioning from slide $k$ point 2 to slide $k+1$ point 0 treats `d(k+1)_section` as $f1$ and `d(k+1)_p0` as $f2$. Because $f2$ requires two consecutive identical decisions, transitions across slides stall.

**Option A (recommended)**: **Contestant A3: Local dense embedding matcher with Ollama** — Add a small local embedding model in Ollama (e.g. `nomic-embed-text`, ~274 MB) to compute cosine similarities between the heard window (15–20 words) and node embeddings precomputed at tree time.
  - *Pros*: Directly bridges lexical paraphrase gap without LLM generation latency; executes in < 20 ms per decision point; avoids prompt-wording confirmation bias; fully local at runtime.
  - *Cons*: Introduces one new model into Ollama, requiring updates to doctor, offline gate, and setup scripts; relaxes the standing "no new models" constraint.

**Option B**: **Hierarchical monotonic forward progression with A2 classifier** — Restructure the A2 follower graph: remove intermediate `section_title` nodes from the live candidate set (collapsing slide transitions directly to the next slide's first point), remove the "answer current point when unsure" fallback instruction from the classifier prompt, and require 3 consecutive decisions to trigger any backward jump while forward transitions commit on 1 decision.
  - *Pros*: Directly addresses both identified root causes of A2's tracking failures without adding new models or changing dependencies; builds upon A2's proven live compute viability (P90 598 ms < 1.5 s).
  - *Cons*: Still requires ~250 LLM calls (~1.8 min) per presentation; heavily paraphrased ad-lib sections may still slip if prompt context is too narrow.

**Option C**: **Recalibrate §8 presentation bars to realistic human-presentation levels and adopt A2** — Acknowledge that human presentation speech naturally leads or trails visual slides by 5–10 seconds and wanders into ad-libs, making ≥ 80–90% continuous time alignment unrealistic for any causal follower. Recalibrate bars to slide ≥ 0.50, point ≥ 0.30, lag median ≤ 8 s, false switches ≤ 4/min, and adopt A2 (which provides the best semantic tracking on creative presentations).
  - *Pros*: No architectural refactoring or model additions; G16 turns green honestly under restated bars.
  - *Cons*: Displays on screen will continue to lag spoken narration by 6–10 seconds; slide alignment will be incorrect ~50% of the time.

Your selection: _____

---

## 2. Lessons that still bite

Each entry is a trap that is **live in this codebase**, found in the September 25 (Wave A) and September 26 (Wave B) verifications. It points at the contract that now owns the detail.

#### 2.1 Constrained decoding truncates to satisfy `maxLength`; it does not shorten

Ollama enforces a schema `maxLength` by force-closing the string at the limit. 34 of 701 on-screen strings were cut mid-word or mid-thought and **still passed every validator**. That made the planner eval's 0.0% fallback rate a symptom, not a success. **A perfect score from a gate is a reason to look harder.** Contract: `design_planner.md` §1 (LLM-facing schemas carry no length constraints).

#### 2.2 Invocation options are not job state

`compile` read music and SFX from the command-line context. `preview`, `rerun` and `render` receive no such options, and invalidation deletes `compile`'s outputs. So every reviewed-and-edited video lost its music and SFX, and the E2E never asserted they survived. **Anything a later stage needs must be copied into the job and recorded.** Contract: `design_system_architecture.md` §4.

#### 2.3 A value that is never measured as composited passes every gate

The map's land/sea pair (1.30 : 1) and captions over illustrations (1.95 : 1) were spec values, implemented exactly, invisible on screen, and green in every gate. The contrast test measured flat token pairs only. Contract: `design_visual_direction.md` §2.1.

#### 2.4 Warm-cache timings are not a budget measurement

The E2E's planning stages took 0.0–0.2 s because the LLM cache was warm, yet the delivery report called the 10-minute budget "met". Contract: `design_testing_and_validation.md` §5 (`scripts/measure_budget.sh`).

#### 2.5 A commit cannot contain its own hash

The resolved index cited 22 SHAs. 14 pointed at pre-amend commits no longer on `main` and one (`5b88db1`) at nothing, because each line was written and then the commit amended. **From Wave B on, every commit subject carries its item id as the Conventional-Commit scope (`fix(b3): …`), and resolved lines cite that id rather than a hash.** Contract: `agent_execution_guide.md` §0.

#### 2.6 A regression set built from tidy inputs can pass while production fails

The critic's regression set scored 4/4 on every seed. Every case had the speaker and the quote in the same beat, but the real pipeline's beat splitter separates them. On the real beats the critic agreed with a wrong attribution on three seeds out of three. **An upstream stage shapes a downstream check's input. Add real production cases to the set** (case E). Contracts: `design_planner.md` §11, `design_audio_and_timing.md` §7.

#### 2.7 An outcome metric must compare before and after

`critic.changed` was set whenever a retry *returned*, even when it returned the same props. Retries that *failed* were invisible, because their errors were not recorded. So "119 changed" overstated what the critic fixed, and "30 unchanged" had no explanation. **Count an effect by comparing the result to the original, and record why a repair did not happen.** Contract: `design_data_contracts.md` §6.

#### 2.8 A visual transform that does not reflow can break layout silently

`transform: scale(1.12)` on the active caption word never changes layout. On long words it swallowed the word spacing, from Wave A on, and every gate passed because nothing measured rendered gaps. **Measure the rendered result (here, empty-column runs), not the style values.** Contract: `design_visual_direction.md` §8.


#### 2.9 A list whose length the model chooses can silently shrink

With a JSON array for "one sender per message", `gemma4:26b` merged consecutive identical answers: 2–3 "them" messages came back as one element on every seed. The length check made each reply a failed attempt, so the scene ended `unavailable`, unchecked, and **3 of 8** real text threads would have lost their critic. **When the count is known in advance, ask for one required key per item**, and measure answer completeness on real cases whenever a prompt changes. Contract: `design_planner.md` §11.


#### 2.10 A retry the model may decline is not a repair

The critic-triggered retry tells the model "fix the props if that reading fits better; otherwise keep yours". It kept the flagged tone in 35 of 87 cases and the disputed quote speaker in 7 of 8. Each of those retries counted as a success, so the deterministic fallback, which ran only when every attempt *failed*, never fired. **When a rule decides what is acceptable, enforce the rule on the final result, not on the path that produced it.** Contract: `design_planner.md` §11 ("Enforcement after the round").

#### 2.11 A choice list the model never sees becomes a default

The props schema's `enum` held 157 icon names, but the prompt listed none. The model guessed, and constrained decoding snapped each unknown guess to an early allowed name: "Armchair" was 9–18% of all icons in every wave and was never noticed, because the icon was valid. **Show the model the names it must choose from, and measure the distribution of what it picks, not just its validity.** Contract: `design_planner.md` §5.


#### 2.12 A fix written for one example misses its siblings, and a prompt change moves errors elsewhere

E3 was specced from one case, "2016", so the model's next move, "March 3rd" as a stat, passed. E4 showed the icon names, so the model began writing "Icon: Bullet" into text fields. **Name the defect class in the spec (a date, not a year), test the class against every past run, and re-read every template a prompt change reaches.** Contracts: `design_planner.md` §6 item 6 and item 7.

#### 2.13 A pipeline that never crashes hides a machine that never ran

Every failed image falls back to an icon, by design, so that one bad model output never ends a job. In all four of Wave H's presentation runs, **every** image failed in ≈ 970 ms because mflux could not find its weights. The videos rendered, and every gate stayed green. **Fallbacks are for the model's failures, not the machine's.** A gate must tell a quality failure (lettering found, then fallback) from an execution failure (the generator never produced an image) and fail on the second.

The same happened one level up. The director's fallback to literal, after one metaphor failed three times, hid that both cold creative budgets timed a literal video and called it a creative PASS. **A measurement must check that it measured the thing it names.**

Contracts: `design_testing_and_validation.md` §4 (asset execution errors) and §5 (a creative budget must be creative); `design_styles.md` §3.3 (salvage).

#### 2.14 A falsification must be able to fail on the real input; "met or filed" makes a gate green on a miss; and a gate that reuses old outputs tests nothing

G16's falsification asserted that shuffled speech scores below the bar. It did, but so did the real speech, so the check proved nothing. Meanwhile the script printed "FAIL (Filed)" and exited 0, because the spec said bars are "met or filed". **A gate's exit code must state its bars.** A known, filed failure gets its own exit code, and the baseline records that code. **The oracle proves the tree and the scorer, not the follower.**

G16 also re-scored any matching job it found in `jobs/` instead of running the pipeline, so on the machine where the jobs were made it never tested the current code. **A gate builds its own fresh outputs every time** (like lesson 2.4's warm caches, but worse: here the whole output was cached). Contract: `design_testing_and_validation.md` §4c.

#### 2.15 A layout test against a hand-kept table tests the table

The overlay test checked each overlay against a hand-written list of template rectangles. The list left out `character_intro`'s avatar, and the test never compared one overlay with another. The spec's own coordinates put the label and the thought bubble on top of the motif token. **Measure the rendered boxes** (2.8, applied to layout). Contract: `design_styles.md` §3.6.

#### 2.16 A stage reused in a second pipeline leaves its guards behind

The presentation tree called the director but not the license check, and it hard-coded `overlays: []`. A failed director silently turned a creative run literal. The spec said only "the style applies as in `design_styles.md`". **When a stage is reused, list every check, record and side output that travels with it, and test each one in the new pipeline.** Contract: `design_presentation_simulation.md` §3.

---

## 3. Resolved index

One line per delivered item: `<id> — <title> — <commit> — <verified result>`. Wave A hashes below were **corrected on September 25, 2026** to the commits actually on `main` (`git log --reverse 9d704f2..e374a15`).

**Wave A — delivered; verified September 25, 2026.** "✓" = matches its spec. "→ B<n>" = delivered, but verification found a defect specced in Wave B.

- A1 — Bootstrap — `4df212a` — ✓ toolchains, battery; G1–G7 reproduce.
- A2 — Setup + doctor — `927d076` — ✓ doctor 21 checks OK; → B15 (the README's credits are inaccurate).
- A3 — Fixtures — `66c11a9` — ✓ the four story SHA-256 values match; `CHECKSUMS` verifies from `fixtures/` (accepted equivalent, see guide §5.2).
- A4 — Contracts + schema sync — `5ad59ba` — ✓ G8 reproduces.
- A5 — Job store, CLI, review gate — `617e569` — ✓ gate logic correct (state + approval hash + timeline hash; no bypass); → B1 (music/SFX lost across `preview`/`rerun`).
- A6 — Timing core — `10dd3a2` — ✓ round-half-up, lead, beats, captions; → B14 (`timing/sfx.py` is dead duplicate code).
- A7 — LLM backend — `7186803` — ✓ entry-point counter, cache key, retries; → B2 ("not found" in a 200 body crashes as a missing model).
- A8 — Narrator voice selection — `9590fb7` — ✓ five steps in order, four named sub-rules, 23 evidence cases.
- A9 — Narration (Kokoro) — `5824005` — ✓ slow suite green.
- A10 — Transcription (Whisper) — `bc78bf8` — ✓ slow suite green (WER and timing bars per the agent's report).
- A11 — Renderer foundation — `92dbcd3` — ✓ clock, spans, sync probe; → B13 (purity-gate exemption too broad; fixtures copied into every render).
- A12 — Bible + geo — `1eb9146` — ✓ repairs 1–5, gazetteer; antimeridian handling accepted (guide §5.2).
- A13 — Segmentation — `f8210b7` — ✓.
- A14 — Storyboard + planner eval — `3bc92d5` — → B3 (select/props crash on malformed JSON), B4 (scale-word grounding leak), B7 (truncation via `maxLength`).
- A15 — Compile + preview — `4d7bf6c` — → B1 (music/SFX), B8 (failed images not flagged on the contact sheet).
- A16 — Final render + E2E — `0a73878` — ✓ `verify.json` is a real gate; → B16 (E2E asserts neither music/SFX nor a computed sync count).
- A17 — Visual primitives + gallery gate — `346ba96` — ✓ 51 goldens compared, hold motion; → B13 (overflow check fails open; stale output dirs).
- A18 — Templates: statement set — `ca735c5` — ✓.
- A19 — Templates: people set — `b205b77` — → B12 (`kinetic_quote` attribution is a monogram, not the avatar).
- A20 — Templates: place & time set — `9cddf93` — → B11 (caption scrim), B12 (map legibility); both are spec defects, now corrected in the design.
- A21 — Illustrations — `142b6a7` — ✓ 4B only, `STYLE` byte-identical, seed/cache per design; → B9 (mflux invoked through a symlink in `~/.local/bin`); fake writing in one image → Issue 3 → B10.
- A22 — E2E, offline, budget, README — `e374a15` — ✓ G13 offline gate real (self-check + fresh cache); → B17 (budget never measured cold), B15 (README).

**Issues:**
- **Issue 1 — Narrator voice** — selected September 24, 2026: *"Proceed with Option A and B. If the story from reddit seems to be from a female's perspective then use af_heart, else use am_michael."* — delivered by A8 `9590fb7` + A9 `5824005`. Verified September 25: `voice.json` matched the expectation on 4 of 4 fixtures, in both the cold planner eval and the E2E (`af_heart` for `story_recipe_box` via evidence "As the only granddaughter, I"; `am_michael` for the other three); `--voice am_michael` makes 0 voice-stage LLM calls. The rule's permanent home is `design_planner.md` §10.
- **Issue 2 — Illustration model** — selected September 24, 2026: *"Proceed with Option A."* — delivered by A21 `142b6a7`. Verified September 25: mflux runs with `--model flux2-klein-4b` only, 1024², 4 steps, q8; no Z-Image code path exists. The permanent home is `design_visual_direction.md` §7.
- **Issue 3 — Generated illustrations fake writing** — selected September 25, 2026: *"Proceed with Option A. Though, in the example provided, I think that text is fine if the description calls for text like a recipe."* — delivered by B10 git log --grep "(b10)". Verified: vision check with gemma4:26b runs on generated illustrations not marked text_expected; transcription prompt with >= 3 alphanumeric rule classifies 7/7 fixture images on seeds 7 and 8; naive prompt falsified (flags waterfronts, scoring 5/7); recipe card entity v1 in story_recipe_box skipped as expected; text detected triggers up to 2 retries on seed+1, seed+2; 3 texty images marks failed and deletes image file; unavailable check keeps image as warning. The rules' permanent home is `design_visual_direction.md` §7.1.
- **Issue 4 — Timeline date labels** — selected September 25, 2026: *"Proceed with Option A."* — delivered by B5 git log --grep "(b5)". Verified: date_labels must contain a grounded digit run or match one of 17 relative time phrases; pairwise distinct; first four-digit years in event order non-decreasing. Wave A defects ("2013/2013/2013", "No Record", "Present") rejected; valid dates and relative phrases accepted. The rule's permanent home is `design_planner.md` §8.
- **Issue 5 — Meaning rules + people-scene critic** — selected September 25, 2026: *"Option A"* — delivered by B6 git log --grep "(b6)". Verified: currency symbols rejected in stat_callout suffix; ungrounded 'ago' rejected in location era_label; blind local critic checks dialogue, text_thread, emotion_beat, and attributed kinetic_quote with at most 1 retry and 0 loops; regression set classifies 4/4 cases as expected with gemma4:26b. The rules' permanent home is `design_planner.md` §6 item 6 and §11.
- **Issue 6 — Dialogue and text messages the story never contains** — decided September 27, 2026 in chat, after watching the `story_recipe_box` and `story_room_12` renders: *"I think the paraphrasing is fine."* Recorded as **Option D (keep as is)**: `dialogue` and `text_thread` lines may paraphrase or dramatise in every genre; no verbatim or word-overlap check; the reviewer judges at the gate. Nothing to build. *Who* speaks is still checked by the critic (and, from C8, who the contact is). The permanent home is `design_planner.md` §5.
- **Issue 7 — Too many words on screen in story videos** — selected September 27, 2026: *"Proceed with Option A."* Picture-first stories: no restating text, word caps, a reaction-shot rhythm; karaoke captions stay. To be delivered by **Wave D (D1–D5)**. The measurements behind the option (≈ 4.5 words/s on screen against 2.6 spoken; 6 of 12 sampled Casually Explained frames wordless) and the measured design (`design_templates.md` §5.5: caps met on 93/94 real scenes; 0.52–0.89 graphic words/s and 39–56% light scenes after R6/R7) live in the design docs. The permanent homes are `design_templates.md` §5 and `design_planner.md` §4–§6 and §9.

**Wave B — delivered; independently verified September 26, 2026.** Verdicts: B1 ✓ (a missing recorded input is silently dropped → C6) · B2 ✓ · B3 ✓ (7 `run_with_retries` sites; `generate_json` only in `llm.py`) · B4 ✓ · B5 ✓ (all 8 probe cases, exact error strings) · **B6** as specced, but the spec had gaps → C1, C2, C3 · B7 ✓ (the audit's 4 at-limit strings are complete phrases; the bar was corrected in `design_planner.md` §9) · B8 ✓ · B9 ✓ (symlink gone) · B10 ✓ (prompt and lists byte-identical) · B11 ✓ (the white worst case is legible) · B12 ✓ (Lake Superior drawn; country codes hand-copied → C6) · B13 ✓ · B14 ✓ · B15 ✓ · B16 ✓ (sync count parsed from JSON) · B17 ✓ (re-measured; see `agent_execution_guide.md` §1.3).

**Wave B:**

- B1 — Music and SFX survive the review journey — git log --grep "(b1)" — G1–G14 green bare, 171 passed (+2 tests); ingest records job-relative music/sfx; compile reads ingest.json on every run; review journey test verifies music and sfx survive edit and invalidation; e2e step 4 asserts music and sfx present in timeline and files.
- B2 — LLM error classification — git log --grep "(b2)" — G1–G14 green bare, 175 passed (+3 tests); 200 responses containing 'not found' accepted; 404 raises DependencyMissing; non-200 raises LLMResponseError; run_with_retries recovers from transient 500.
- B3 — Planner crash containment — git log --grep "(b3)" — G1–G14 green bare, 180 passed (+5 tests); generate_json called only in llm.py; 5 run_with_retries call sites in planner; select and props recover on attempt 2 after malformed attempt 0; truncated replies complete with fallback_level 2.
- B4 — Grounding scale words — git log --grep "(b4)" — G1–G14 green bare, 181 passed (+1 test); numbers("holding 2.3 million gallons") returns 2.3 and 2300000.0 without stray 1000000.0; spelled runs require small number or leading a/an.
- B5 — Timeline date labels — git log --grep "(b5)" — G1–G14 green bare; timeline_label_errors rejects non-distinct, non-grounded, unapproved relative phrases, and decreasing years; template writing rules updated; schema sync G8 green.
- B6 — Meaning rules + people-scene critic — git log --grep "(b6)" — G1–G14 green bare, 192 passed (+11 tests); stat_callout suffix currency errors rejected; location era_label ungrounded 'ago' rejected; critic runs blind on people scenes with 256 num_predict and temp 0; 1 props retry on mismatch, 0 further critic calls; regression set passes 4/4 on gemma4:26b; planner containment asserts 6 run_with_retries sites.
- B7 — LLM-facing schemas without length limits; text completeness; planner eval re-run — git log --grep "(b7)" — G1–G14 green bare, 203 passed (+11 tests); llm_facing_schema strips length and pattern constraints inside generate_json; retry messages prompt shorter complete phrases; normalize_text collapses whitespace; text_complete_errors catches truncation fragments and punctuation issues; cold planner eval passes all §9 bars (0 newlines, 0 completeness failures, 0 timeline errors, critic 4/4); byte-identity determinism holds.
- B8 — The contact sheet flags failed images — git log --grep "(b8)" — G1–G14 green bare, 204 passed (+1 test); flagged scenes includes overflow ∪ fallback_level 2 ∪ failed image entities; storyboard.md flags gain 'image failed'; report.json carries failed_images and warnings for text_check unavailable.
- B9 — Invoke mflux directly; drop the symlink — git log --grep "(b9)" — G1–G14 green bare; TOOL_NAME set to mflux-generate-flux2; cache_key and generate support seed parameter and actual seed is included in canonical cache key; doctor asserts mflux-generate-flux2 on PATH and --help contains flux2-klein-4b (exit 4 otherwise); setup.sh removes legacy symlink; design docs updated.
- B10 — Illustration text check with automatic retry — git log --grep "(b10)" — G1–G14 green bare, 211 passed (+7 unit tests); vision check with gemma4:26b evaluates illustrations not marked text_expected; text_expected handles whole words and phrases at word boundaries; retries on seed+1, seed+2; 3 texty failures mark entity failed and remove image; unavailable fallback preserves image as warning; fixtures/vision/ achieves 7/7 on seeds 7 and 8; naive prompt falsified at 5/7; run_with_retries count asserts 7 across planner/assets.
- B11 — Legible text over images; captions through FitText — git log --grep "(b11)" — G1–G14 green bare, 215 passed (+1 test); layout.ts exports IMAGE_SCRIM with stops at 640 (0), 800 (0.85), 1120 (0.92) and IMAGE_TEXT_MIN_TOP 807; ImageScrim used in location and set_piece; test_contrast asserts alpha >= 0.85 and ink/inkMuted >= 4.5:1 over white (9.15:1 and 5.57:1 measured; falsified at 0.53 with 1.95:1); captions render through FitText with CAPTION_SLOT; white.png and location__worst golden added; G10 gallery gate passes with 0 overflows.
- B12 — Map legibility; kinetic_quote attribution avatar — git log --grep "(b12)" — G1–G14 green bare, 217 passed (+2 tests); map colors mapSea #0B1326, mapLand #4466A0, mapRegion #7C9FDB, mapBorder #0B1326; test_contrast asserts map contrast rows (land/sea 3.22:1, region/land 2.15:1, stroke/land 3.22:1, stroke/region 6.90:1, fill/stroke 12.83:1, chip ink/bgDeep 16.83:1; falsified with mapLand #1F2F52); Natural Earth ne_50m_lakes downloaded, checksummed, and generated into renderer/public/geo/lakes-50m.json; lakes drawn above land in mapSea; doctor check 13 asserts lakes-50m.json; marker dot radius 14 with 4px bgDeep stroke and 14->48 pulse ring; computeChipPlacement places chips with 12px gap (above at y-26, below at y+26 when y < 120); vitest asserts marker dot and chip disjointness (falsified with -48); kinetic_quote renders parametric Avatar at 120px with name chip in cast color; G10 gallery passes with 0 overflows on all 52 goldens; story_recipe_box preview tile s013 verified with Lake Superior water separating Duluth and Thunder Bay.
- B13 — Gates fail closed; bundle hygiene — git log --grep "(b13)" — G1–G14 green bare, 217 passed; check_gallery.sh cleans output dirs first and fails closed if overflow.json is missing or unparseable (falsified with rm overflow.json -> exit 1); check_renderer_purity.sh drops only paths starting with renderer/src/clock/remotion/ (falsified with renderer/src/templates/remotion/x.tsx -> G9 exit 1); render.ts drops copy of fixtures into render_public (asserted not exists after render); test_smoke_sync_probe builds temporary job dir with fixtures/music/test_bed.wav at audio/narration.wav and verifies bundle hygiene and sync probe flips.
- B14 — Remove the dead SFX scheduler — git log --grep "(b14)" — G1–G14 green bare, 214 passed (-3 tests); timing/sfx.py, its exports from timing/__init__.py, and tests/test_timing_sfx.py deleted; grep asserts zero references in src and tests; test_compile.py SFX tests pass.
- B15 — README accuracy — git log --grep "(b15)" — G1–G14 green bare; README updated with Wave B in progress status, accurate audio mix specs (-16 LUFS, -18 dB / volume 0.126, 1s fade-in, 2s fade-out, no ducking), template-accurate SFX role mappings, font credits restricted to Poppins and Inter, Natural Earth lakes dataset credited, and automatic checks section added; banned terms grep returns 0 matches.
- B16 — E2E: computed counts, audible music — git log --grep "(b16)" — G1–G14 green bare, 218 passed (+4 tests); check-sync outputs JSON {"checked", "expected", "failures"} and asserts equality to len(scenes) - 1 with 0 failures (falsified by --skip-boundary 1 -> exit 1); voice lines read dynamically from voice.json across all fixtures; step 4 final MP4 audio RMS in [duration - 1.4s, duration - 1.0s] measured at -39.85 dBFS (> -60.0 dBFS required; falsified on music-less re-render at -91.16 dBFS -> exit 1); Remotion AudioLayer audio volume clamped to >= 0.001 to prevent unregistering render asset, and RemotionAudioCue passes loop and loopVolumeCurveBehavior="extend" to Audio; report lists critic counts and text_check statuses per fixture.
- B17 — Cold-cache performance budget; close-out — git log --grep "(b17)" — G1–G14 green bare; scripts/measure_budget.sh created and verified on story_recipe_box (~3 min story); cold new->awaiting_review 252.29 s (<= 390 s), render 197.01 s (<= 210 s), total 449.30 s (<= 600 s), warm preview 15.25 s (<= 60 s); verified 0 cache hits; critic 10 calls, text checks 4 calls, 5 images generated; docs/evals/budget_2026-09-26.md generated and committed; full battery G1–G14 exits 0 bare.

**Waves C and D — delivered; independently verified October 3, 2026.** Verdicts: C1 ✓ (quote tracking resets per sentence, so a quotation spanning two sentences can still be split between them; the spec allowed it, and it is recorded as a known limitation) · C2 ✓ (the critic prompt drops the `Cast:` label; accepted equivalent, regression 8/8) · C8 ✓ · C3 ✓ to spec, but the spec had a gap → E1 · C4 ✓ · C5 ✓ · C6 ✓ · C7 ✓ · D1 ✓ (plus an out-of-scope `HF_HOME` override in `__init__.py` → E5) · D2 ✓ · D3 ✓ to spec, but the spec had a gap → E2; R6's alternates exposed a year-as-stat → E3 · D4 ✓ · D5 ✓.

**Wave C:**

- C1 — Quoted speech stays whole when splitting beats — git log --grep "(c1)" — G1–G14 green bare, 221 passed (+3 tests); colon removed from PUNCT_SUFFIXES; QUOTED_SENTENCE_MAX_MS = 16000; quote spans and opening quotes preserved in split pass; tests/data/quote_sentence.json yields 1 beat instead of 2 (falsified on colon bonus and quote exclusion removal); 17,000ms synthetic sentence splits without breaking opening quote; beat counts: molasses_flood 10, emu_war 25, story_recipe_box 32->29, story_room_12 33->34.
- C2 — Critic passage framing, keyed text-thread answers, regression cases E + H — git log --grep "(c2)" — G1–G14 green bare, 224 passed (+3 tests), 24 slow passed (+2 tests); critic prompt updated to passage framing with verbatim header 'Passage (read all of it; who speaks is often named in the sentence before a quote):\n' and 4 beats joined by spaces, removing all 'context only' text; text_thread answers use keyed message_1..n schema and are normalized to messages array in validate_critic_answer; regression cases E and H added to slow tests and planner eval; cases A, B, B', C, E, H pass on seeds 7, 8, 9 (18/18); falsified on old framing (Case E returns narrator c1 -> agree) and missing keys (failed attempt).
- C8 — Text-thread contact identity — git log --grep "(c8)" — G1–G14 green bare, 226 passed (+2 tests), 24 slow passed (8/8 cases on seeds 7, 8, 9 = 24/24); resolve_contact matches contact_cast_id or unique non-narrator casefolded name; contact question appended to text_thread prompt; contact enum with non-narrator IDs + "unknown" appended as required last property; validate_critic_answer validates and normalizes contact; critic_mismatches checks contact against resolved contact and emits mismatch 'contact: <name> vs <name> (<cid>)'; contact fill populates props_instance.contact_cast_id before validate_scene and in final scene construction; regression cases F and G added; falsified by deleting contact comparison (Case F goes red).
- C3 — Critic retry robustness — git log --grep "(c3)" — G1–G14 green bare, 231 passed (+5 tests); critic-triggered props retry upgraded to 3 attempts with run_with_retries; honest changed bool based on props dict comparison; deterministic tone repair sets line tone to neutral when all mismatches are dialogue tone vs unknown; CriticReport gains repair and retry_errors fields; rule R3 repair path calls _evaluate_scene_critic on replacement scene when needs_critic is true; evals/planner.py reports agree, changed, tone_neutral repairs, and unchanged-after-mismatch; falsified by reverting max_attempts to 1 (test_critic_retry_recovers_on_attempt_2_or_3 goes red).
- C4 — No internal ids on screen — git log --grep "(c4)" — G1–G14 green bare, 234 passed (+3 tests); internal_id_errors checks free-text fields against bible cast, places, and set_pieces; exact error format 'props.<field>: contains the internal id "<id>" — use the name ("<name>")'; validate_scene wires internal_id_errors into all free-text fields; props.md gains verbatim sentence 'Refer to people, places and objects by their names; never write ids like c1, p2 or v1.'; evals/text_audit.py tracks id_leaks_count and id_leaks with bible integration; falsified by disabling check (tests fail red).
- C5 — Caption word spacing — git log --grep "(c5)" — G1–G14 green bare, 236 passed (+2 tests); each caption word renders as inline-grid with hidden 1.12em sizer and visible word at 1em or 1.12em active; marginRight: 0.3em separates adjacent word boxes; transform: scale removed; gallery fixture and golden captions__long_active added (53 goldens); test_caption_spacing.py checks runs >= 16px in caption band; check_gallery.sh runs spacing test; story_recipe_box preview verified across 27 multi-word caption scenes with min word gap 13px at half scale (26–62px full scale; 16px on s020 vs 4px in Wave B); falsified by restoring scale transform (test fails with widest run 8px <= 16px).
- C6 — Hygiene: generated country codes; a missing input fails loudly — git log --grep "(c6)" — G1–G14 green bare, 237 passed (+1 test); gen-country-bboxes.ts generates renderer/src/generated/countryCodes.ts with DO-NOT-EDIT header and sorted numeric keys; renderer/src/components/countryCodes.ts deleted; MapView.tsx updated to import from generated; check_schema_sync.sh covers countryCodes.ts (13 files checked, G8 green; falsified by hand-editing an entry -> G8 red); compile.py raises ValidationFailed when ingest.music or ingest.sfx_dir is recorded but missing from the job; unit test test_compile_missing_music_fails_loudly validates exit-2 error naming the missing path (red first: previously silently dropped).
- C7 — Re-measure; close-out of Wave C — git log --grep "(c7)" — G1–G14 green bare, 237 passed; cold planner eval passes all §9 bars (8/8 critic regression, 0 id leaks, 0 newlines); re-run E2E passes with Walter Lindqvist quote attributed to Danny (c3) in text_thread containing 'texted me a photo:' and 0 unavailable text-thread critics; cold budget 411.10 s (≤ 600 s) with 0 cache hits.

**Wave D:**

- D1 — Word-budget contracts: removed fields, list maxima, neutral, WORD_CAPS, words module, renderer, gallery — git log --grep "(d1)" — G1–G14 green bare, 242 passed (+5 tests); removed 6 fields restating narration across contracts, validate, audit, and templates; list maxima updated for 6 templates; neutral emotion added to EmotionBeat; WORD_CAPS contract and template classes added; count_words, field_values, and graphic_words implemented in planner/words.py; gallery fixtures and goldens updated with 0 overflows.
- D2 — Planner word budget: validator item 9, writing rules, props.md, 12-word fallback, text audit, critic neutral — git log --grep "(d2)" — G1–G14 green bare, 246 passed (+4 tests), 29 slow passed (+5 tests); validator item 9 word_cap_errors enforces WORD_CAPS limits with rewrite prompt; too_long list error formatted per D2; registry writing_rules updated verbatim across 15 templates; prompts/props.md guidelines 3 & 4 updated and prompts/select.md icon_list rule updated; deterministic kinetic_quote capped at 12 words with ellipsis; critic emotion_beat supports neutral first; text audit tracks and enforces word_cap_violations_count == 0; 9 frozen cases in word_cap_cases.json verified and falsified (timeline events[].label to 99 -> red); 5 real beats in tests/slow/test_word_caps_live.py pass within 3 attempts on gemma4:26b with character_intro descriptor omitting cast member name.
- D3 — Selection rules R6 and R7; deterministic pictures — git log --grep "(d3)" — G1–G14 green bare, 251 passed (+5 tests); timeline <= 1 and comparison <= 1 enforced in selection rule R6 and validate_plan; reaction-shot rhythm rule R7 (run >= 2 non-picture scenes in replaceable templates triggers deterministic rhythm target: narrator emotion_beat, named non-narrator cast member, named set_piece, or named location); kept templates and picture templates never replaced; quoted text excluded from first-person narrator match; Choice gains rhythm_id; props plan_storyboard builds deterministic neutral emotion_beat, set_piece, or location with 0 LLM calls; needs_critic bypasses deterministic rhythm picture scenes; recipe_choices.json exact repairs and choices verified; rhythm_cases.json 7/7 verified and falsified (dropping QUOTED stripping picks c1 -> red; dropping kept-class check replaces R7-e/R7-f -> red).
- D4 — Word-density measurement: eval bar, evals/word_density.py, E2E step 9 — git log --grep "(d4)" — G1–G14 green bare, 254 passed (+3 tests); evals/planner.py computes graphic_words_total, graphic_words_per_narration_word, light_share (scenes after title card with graphic words <= 2 / m), and R6/R7 repairs; light_share >= 1/3 bar enforced in fixture_pass; planner report includes metrics and Wave B baselines; evals/word_density.py CLI loads timeline.json, calculates graphic words/s and light share, exits 1 if per_second > 1.0 or light < m/3; scripts/e2e.sh step 9 checks rendered jobs and logs word density lines to e2e report; unit tests on synthetic timeline pass; falsified by dividing duration_frames by 3 (exit 1 -> red) and light_share bar to 0.9 (eval fails -> red).
- D5 — Re-measure; close-out of Wave D — git log --grep "(d5)" — G1–G14 green bare, 254 passed; cold planner eval passes all §9 bars (8/8 critic regression, 0 word-cap violations, 0 newlines, 0 completeness failures, 0 ID leaks, light share 33.3%–57.1% >= 1/3); G12 E2E step 9 passes with all rendered jobs <= 1.0 graphic word/s and >= 1/3 light share; cold budget 390.16 s (<= 600 s) with 0 cache hits; story_recipe_box stills verified (neutral reaction shot, name-only set piece, 3-event timeline, 3-message text thread, 8-word quote); README updated to Waves A–D delivered; agent execution guide rewritten to Queue Complete.

**Wave E — delivered; independently verified October 4, 2026.** Verdicts: E1 ✓ (`enforce_reading` on the standing scene; the emotion rule; disputed quote speakers dropped) · E2 ✓ (frozen data merged exactly) · E3 ✓ to spec, but the spec covered only years → F1 · E4 ✓ (the block follows any disagreement message; accepted), but it induced instruction text → F2 · E5 ✓ · E6 ✓ (`evals/verify_e2e_scenes.py` reproduces 0/0/0/0/0 on both runs; it is run by hand, not wired into `e2e.sh`).

**Wave E:**

- E1 — Critic findings stick: enforcement after the round, the emotion rule, disputed quote speakers removed — git log --grep "(e1)" — G1–G14 green bare, 255 passed (+1 test), live slow tests pass (6/6 emotion mismatch on seeds 7, 8, 9; critic regression 8/8); critic_mismatches treats unknown emotion against non-neutral as mismatch; enforce_reading repairs unconfirmed dialogue tones to neutral ("tone_neutral"), unconfirmed emotions to neutral ("emotion_neutral"), and disputed kinetic_quote attributions to null ("attribution_dropped"); _evaluate_scene_critic applies enforce_reading to standing scene post-round; CriticReport.repair schema updated; evals/planner.py reports all three repair types; all 7 frozen cases verified; falsified by skipping enforce_reading on successful retry (Rose note sarcastic -> red) and reverting emotion rule (angry vs unknown -> agree -> red).
- E2 — R7 never replaces quoted speech — git log --grep "(e2)" — G1–G14 green bare, 255 passed; R7 condition in planner/select.py updated with not QUOTED.search(beat_text); frozen data updated (rhythm_cases.json R7-b expected null, R7-h added; recipe_choices.json s016 repair removed); test_rhythm_cases asserts 8 cases; falsified by removing QUOTED condition (R7-b, R7-h, and recipe choices exact go red bare).
- E3 — A year is not a stat — git log --grep "(e3)" — G1–G14 green bare, 256 passed (+1 test); stat_callout validator rejects integer values 1000..2100 appearing in beat text without comma/formatting as years; real room 12 2016 scene fails with exact error (red first); falsified by deleting rule (2016 passes -> red) and widening range 0..9999 (312 cards fails -> red).
- E4 — The props prompt lists the allowed icon names — git log --grep "(e4)" — G1–G14 green bare, 257 passed (+1 test), live slow tests pass (2/2 emu_war scenes contain 0 Armchair); props user prompt appends icon allow-list block for stat_callout, icon_list, cause_effect, and comparison; unit tests in tests/test_props_prompt.py assert block presence/absence (red first); falsified by removing block (slow test on emu_war scenes reproduces Armchair in both icon_list and cause_effect -> red).
- E5 — Hygiene: no import-time environment change; stale comments — git log --grep "(e5)" — G1–G14 green bare, 257 passed; deleted HF_HOME override from __init__.py; doctor check 7 Kokoro missing message gains explicit hint (if HF_HOME is set, it must contain hub/models--hexgrad--Kokoro-82M; unset it or export HF_HOME="$HOME/.cache/huggingface"); design_testing_and_validation.md §3 documents battery.sh export; location.tsx and set_piece.tsx comments updated for D1 caption removal; red first verified on mktemp HF_HOME printed vs temporary dir, and doctor exits 4 with hint.
- E6 — Re-measure; close-out of Wave E — git log --grep "(e6)" — G1–G14 green bare, 257 passed, 37 slow passed; cold planner eval passes all §9 bars (8/8 critic regression, 0 word-cap violations, 0 Armchairs, light share 33.3%–57.1% ≥ 1/3); G12 E2E and verify_e2e_scenes pass with 0 unneutral tones, 0 disputed attributions, 0 quoted R7 repairs, 0 year stats, and 0 Armchairs across all 7 rendered jobs; cold budget 407.94 s (≤ 600 s) with 0 cache hits; recipe box and room 12 stills verified (kinetic quote for Rose's note, neutral avatar for online call, book/camera/envelope icons, "3 March" stat); full battery exits 0 bare; queue complete.
**Wave F — delivered; independently verified October 4, 2026.** Verdicts: F1 ✓ (the date regex is verbatim; the frozen case gives its exact error) · F2 ✓ (`placeholder_errors` is wired after item 9; 0 false alarms) · F3 ✓ (normalisation runs before the length check, so "January 15, 1919" now becomes "1919" instead of failing) · F4 ✓ (`verify_e2e_scenes` extended and wired into `e2e.sh` as step 10; falsified on pre-Wave-F output). The design gap was that `design_testing_and_validation.md` §4 did not list step 10; it now does.

**Wave F:**

- F1 — A date is not a stat — git log --grep "(f1)" — G1–G14 green bare, 258 passed (+1 test); stat_callout validator rejects integer values matching month-and-day or day-and-month date patterns in beat text; frozen March 3rd case fails with exact error (red first); 3 soldiers, 20,000 emus, and 312 cards do not error; falsified by removing ordinal group (March 3rd goes red bare).
- F2 — No placeholder or instruction text on screen — git log --grep "(f2)" — G1–G14 green bare, 261 passed (+3 tests); placeholder_errors rejects instruction text matching \bicon\s*: and whole-string placeholder words across WORD_CAPS fields; text audit tracks placeholder_violations_count with bar 0; both frozen junk comparison cases fail with exact errors (red first); "UNKNOWN IDENTITY" and "No Record Found Yet" pass with 0 errors; all frozen storyboards in tests/data/ yield 0 errors except the two frozen junk scenes; falsified by removing "not specified" (frozen case goes red bare).
- F3 — Era stamps show a narration year or nothing — git log --grep "(f3)" — G1–G14 green bare, 264 passed (+3 tests); normalize_era_label normalizes location era_label to a four-digit year from the narration or null; applied to planner location props before validate_scene; all 8 frozen era label cases match expected values (red first); 1960s with 1960 in transcript yields 1960s, absent 1932 yields null; stub backend returning 'Present Day' produces null; falsified by keeping labels with digits (1932 era goes red bare).
- F4 — Re-measure; close-out of Wave F — git log --grep "(f4)" — G1–G14 green bare, 265 passed, 37 slow passed; cold planner eval passes all §9 bars (8/8 critic regression, 0 word-cap violations, 0 placeholder errors, 0 armchairs, light share 33.3%–57.1% ≥ 1/3); G12 E2E step 10 verify_e2e_scenes passes with 0 unneutral tones, 0 disputed attributions, 0 quoted R7 repairs, 0 year stats, 0 date stats, 0 junk text, 0 invented era stamps, and 0 armchairs across all 5 rendered jobs; cold budget 402.81 s (≤ 600 s) with 0 cache hits; room 12, recipe box, and emu war stills verified; full battery exits 0 bare; queue complete.

**Wave G — delivered; independently verified October 6, 2026.** Verdicts:
- G1 ✓ (fixtures and checksums; `af_heart` / `llm` on `story_overdue_book`).
- G2 ✓ (literal byte-identity holds against the frozen baseline).
- G3 ✓ to spec. The spec let a thought aside carry nothing (→ I3) and left motif names unchecked and unspaced (→ I4).
- G4 ✗ in one part: the callback's "seen before" dots are always 2, because `compile` gives `callback` no items and the renderer falls back to `[15, 27]` (→ I1). The overlay layer is ✓ to spec, but the spec anchored the asides on the token and over the avatar, and its test used a hand-kept table (→ I2).
- G5 ✓.
- G6 ✓. G15's "0 overlay overlaps" relied on G4's table (→ I2).

**Wave G:**

- G1 — New fixtures wired in; literal measured on long stories — git log --grep "(g1)" — G1–G14 green bare; shasum CHECKSUMS passes all 28 entries; planner eval passes 6/6 fixtures cold (story_overdue_book af_heart / llm "grandmother", 15 distinct, light 52.5%; history_great_stink am_michael / third_person, 14 distinct, light 39.4%); literal cold budget on story_overdue_book 56.87 s/min new / 79.80 s/min render / 136.67 s/min total (≤ 90 / 80 / 170 s/min), 0 cache hits; literal restatement observed on beats s003/s027, s032, s054.
- G2 — Style contract; --style; literal byte-identity — git log --grep "(g2)" — G1–G14 green bare, 272 passed (+7 tests); StyleSpec and STYLES {literal, creative} in contracts/styles.py exported to schema/styles.schema.json and renderer/src/generated/styles.ts (G8 passed); --style added to new and rerun; ingest.json records style (missing key loads as literal); director inserted into stage list (skipped in literal, writes nothing); rerun --from director supported; literal byte-identity on molasses_flood verified against tests/data/literal_baseline/molasses_flood.sha256 across all 5 files (bible, beats, storyboard, plan_report, timeline); falsified by verifying modified plan_report changes checksum.
- G3 — Director + license stages — git log --grep "(g3)" — G1–G14 green bare, 290 passed (+18 tests), 6 slow passed; director and license stages implemented in planner/director.py and planner/license.py; contracts in contracts/director.py exported to schema/director.schema.json and renderer/src/generated/director.ts (G8 green); all 7 validators tested with failing/passing cases and falsified on payoff before plant; live measurement passed cold on 6/6 fixtures within 2 attempts (bar: ≤ 3); ≥ 1 motif with plant/payoff on 4/4 required fixtures; license critic drops evaluated and recorded in docs/evals/planner_2026-10-06.md; degradation to literal verified on 3 failed attempts without pipeline crash; preview storyboard.md formats plan at top; director.json re-validated by preview.
- G4 — Renderer: metaphor, callback, OverlayLayer, and gallery fixtures — git log --grep "(g4)" — G1–G10, G14 green bare, 290 passed, 19 vitest passed; metaphor and callback templates created and registered (18 total); OverlayLayer implemented per design; overlay bounding boxes disjoint from primary content bounds across all 10 allowed templates; falsification test fails at (540, 240); 16 new goldens cut and verified in check_gallery.sh with 0 overflows, 0.000% diff, and hold motion verified; literal baseline byte-identity holds.
- G5 — Integration: R8, deterministic scenes, metaphor images, overlays — git log --grep "(g5)" — G1–G10, G14 green bare, 299 passed (+9 tests); selection rule R8 orders metaphor and callback with LLM primary as alternate; R2 never rewrites R8 scenes; deterministic metaphor and callback props planned with rationale "director"; metaphor illustration asset generation wired; compute_scene_overlays enforces allowed templates, token displacement <= 2 beats before payoff, aside displacement <= 1 beat, dropped overlays recorded under overlay_dropped; overlays count toward graphic_words in planner/words.py; contact sheet displays M and C badges on metaphor/callback tiles; report.json records director item fates (rendered, moved, license_dropped, overlay_dropped); end-to-end creative run on story_overdue_book reaches awaiting_review with 0 overflows, 4 rendered tokens/callback, 9 license drops, and 0 plan regressions; literal baseline byte-identity holds.
- G6 — Creative E2E (G15), creative long budget, Wave G close-out — git log --grep "(g6)" — G1–G15 green bare, 302 fast passed, 19 vitest passed; scripts/creative_e2e.sh implemented and wired into battery as G15; both creative jobs pass verify.json, word density (0.74 and 0.84 words/s <= 1.0, light share 45.5% and 37.3% >= 33.3%), Wave E/F scene criteria (all 0), and creative bars (every motif planted before payoff, >= 2 metaphors, >= 2 asides, 0 license failures left, 0 overlay overlaps); falsification verified (stub director no motifs -> fails red); cold long creative budget on story_overdue_book measured at 59.62 s/min new / 80.83 s/min render / 140.45 s/min total (<= 110 / 85 / 195 s/min), 0 cache hits; evaluation report docs/evals/creative_2026-10-06.md generated with contact sheets, stills comparisons, and commentary; literal baseline byte-identity holds.

**Wave H — delivered; independently verified October 6, 2026.** Verdicts:
- H1 ✓. Accepted: `num_predict` 2048.
- H2 ✓. Accepted: the presentation profile also skips R1; 0 `title_card` nodes in 4 trees, and I8 makes the second half of R1 an assertion. The creative path skips the license check and the overlays, and degrades silently (→ I7).
- H3 ✓.
- H4 ✓ to spec. The spec's 20-word window is a cause of Issue 8.
- H5 ✓ for the scorer and the oracle. G16 fails open, and its falsification cannot fail (→ I8).
- H6 ✓. Its "all green" did not see 0 generated images in all four presentation runs (→ I6).

**Wave H:**

- H1 — present-sim CLI, presentation job kind, and deck stage — git log --grep "(h1)" — G1–G10, G14 green bare, 314 fast passed (+12 tests); present-sim CLI creates presentation job with kind="presentation" in state.json, recording perturb, seed, and tiebreak in ingest.json; deck stage plans key moments using Ollama gemma4:26b and prompts/deck.md; all 6 validators pass (slide count, 2-4 points, length caps, sentence-id contiguous partition, digit grounding, clean text); falsified by skipping sentence 3 in partition (validator 4 rejects red); live decks generated for history_great_stink (7 slides, 21 points) and story_overdue_book (8 slides, 22 points); preview renders contact sheet with slide cards and bullet points, re-validates human edits to deck.json, and rejects invalid edits with exit 2; num_predict set to 2048 to fit 8-10 slides.
- H2 — deck_bible, tree stage, section_title template, presentation profile, and isolation — git log --grep "(h2)" — G1–G10, G14 green bare, 322 fast passed (+8 tests), 19 vitest passed; section_title template implemented (19 total) with center display text, dots row at y 820, hold motion 0.460% > 0.1%, and 3 goldens verified in check_gallery.sh; presentation profile relaxes R1, R2, R6, R7 while keeping R4, R5, R8; deck_bible plans presentation Bible from deck text; tree stage builds deterministic section nodes with section_title, infographic point nodes with slide context and critic, next/skip/back edges with transition costs, normalized matching text with stopwords and suffix stemming; offline isolation invariant verified bare and falsified; live present-sim runs on history_great_stink (28 nodes, 453 edges, 7 section_title) and story_overdue_book (30 nodes, 521 edges, 8 section_title).
- H3 — perform, speak, and hear simulation stages — git log --grep "(h3)" — G1–G10, G14 green bare, 330 fast passed (+8 tests); perform stage implements isolated seeded RNG streams per op with configured mild/strong rates; paraphrase keeps digit runs, names, and quotes with fallback to verbatim on validation failure; fillers inserted at boundaries/starts, ad-lib tangents between points, back-references across >= 2 slides; retention validator requires >= 70% (mild) / >= 50% (strong); PerformancePlan exported to schema/performance.schema.json and generated performance.ts (G8 verified); speak stage synthesizes audio via Kokoro writing audio/narration.wav and speak_timing.json; hear stage transcribes audio via MLX-Whisper into heard.json (source: "asr"); determinism verified (byte-identical performance.json with warm cache); live run on history_great_stink with --perturb strong --seed 7 applied 36 paraphrases, 54 fillers, 4 drops, 8 swaps, 3 ad-libs, 1 back-ref, 1 skip-point in 22.4s, spoken in 31.7s, transcribed in 10.3s with measured ASR WER of 1.66%.
- H4 — follow and compose simulation stages — git log --grep "(h4)" — G1–G10, G14 green bare, 342 fast passed (+12 tests); follow stage consumes only tree.json and heard.json in isolation; BM25 index with k1=1.2, b=0.75, committed stopwords, and suffix stemming; streaming decision points at gaps >= 300ms or 1500ms intervals; commit rules enforced (2 consecutive tops, score gap >= 1.0, dwell >= 2.0s); simulated latency = decision time + measured compute time; causality verified (identical commits on future-truncated prefix) and falsified (altering future speech); compose stage builds timeline.json merging scenes shorter than 20 frames (ENTER_FRAMES 12 + EXIT_FRAMES 8) and paginating live captions with 300ms lag; live present-sim on history_great_stink with --perturb strong --seed 7 committed across talking points in 422s with back-reference detection at 296s (score 15.29) and short-scene merging; hysteresis falsification verified red bare.
- H5 — score stage, oracle baseline, presentation_sim.sh (G16), and evaluation report — git log --grep "(h5)" — G1–G10, G14, G16 green bare, 350 fast passed (+8 tests), 19 vitest passed; PresentationScore and PresentationMetricResult implemented in contracts/score.py; score stage calculates slide accuracy, point accuracy, median and p90 onset lag, false switches per minute, ad-lib stability, and skip recovery; Pillow strip chart renders ground truth vs shown slide bands; --oracle composes and renders oracle.mp4 baseline achieving 100% (1.0000) slide/point accuracy and 0.0s lag; scripts/presentation_sim.sh verifies all 4 simulation runs, scene criteria (step 10 = 0 clean), graphic word density (<= 1.0 graphic words/s), and LLM tie-break measurement (--tiebreak llm remains OFF by default per §6.4); evaluation report docs/evals/presentation_2026-10-06.md generated with visual strip charts; falsification verified on shuffled speech (fails red bare).

**Wave I:**

- I1 — Callback seen-before dots count real motif appearances — git log --grep "(i1)" — callback_item_count in compile.py counts prior scene motif_token overlays; timing?.item_frames in callback.tsx with dotCount > 0 wrapper and no [15, 27] fallback; 3 callback goldens re-cut and verified (min=1, typical=2, max=5 dots) in check_gallery.sh; G15 verify_creative asserts callback len(item_frames) == earlier token count >= 1; recompiled both creative E2E jobs to 4 dots verified in stills; falsified by restoring [15, 27] (vitest red) and callback_item_count=0 (G15 red).
- I2 — Asides move top-left; overlap is measured on the rendered frame — git log --grep "(i2)" — OVERLAY_BOUNDS updated to [840, 180, 960, 300], [60, 165, 300, 335], [60, 200, 300, 302], [100, 1020, 240, 1160]; fictional TEMPLATE_SLOT_BOUNDS replaced by Gallery DOM getBoundingClientRect probe and overlap.json; data-occupies and data-slot markers added across templates; check_gallery.sh fails closed on missing overlap.json; 20 overlay goldens verified with 0 overlaps and 0 overflows; G8 schema sync verified; falsified on thought back at (840, 260) and missing overlap.json.
- I3 — A thought aside always says something — git log --grep "(i3)" — director rule 7 requires cast_id and (icon or text), raising "asides[<k>]: a thought needs an icon or text"; SceneOverlay validator enforces data completeness per kind; compute_scene_overlays drops incomplete asides into overlay_dropped with reason "incomplete"; renderer removes fallback icons (Sparkle, ChatCircleDots, Package, Aside); G15 verify_creative asserts no empty thought overlays; recompile of story_overdue_book drops empty s001 thought; falsified by removing thought check from rule 7.
- I4 — Motifs named in story words and spaced; director salvage recovers stuck plans — git log --grep "(i4)" — rule 5 validates motif name words against narration with trailing-s allowance; rule 3 validates consecutive appearances >= 3 apart and payoff <= 20 beats after previous appearance; prompt displays rule 6 words from constants; salvage drops item-local errors into director_dropped, waiving counts if >= 1 item remains; 6/6 cold live fixtures produce plans (0 degraded); falsified by dropping trailing-s allowance (pumps red) and payoff spacing 20 -> 40 (overdue spacing red).
- I5 — No name on screen before the narration says it — git log --grep "(i5)" — G1–G10, G14 green bare, 370 fast passed (+27 tests); names_before_narration_errors in validate.py checks kinetic_quote, character_intro, dialogue, and text_thread against spoken narration word tokens up to beat.word_end; names_before_narration column added to verify_e2e_scenes.py and planner eval table (bar = 0); red first verified bare (2, 2, 2, 1 violations across recorded runs); live cold re-planning on story_room_12, history_great_stink, and story_overdue_book all achieved 0 violations bare; 7 former spoiler scenes re-planned (e.g. s019 Sofia -> location, s004 John Snow -> cause_effect, s015 John Snow -> kinetic_quote without cast attribution, s012 Robert Okafor -> kinetic_quote without cast attribution, s017 June Lind -> dialogue without June Lind name); falsified on synthetic spoiler test cases (exit 1 red bare).
- I6 — An execution failure fails the gate — git log --grep "(i6)" — G1–G10, G14 green bare, 375 fast passed (+5 tests); execution_errors in evals/asset_health.py detects manifest failed entries not starting with lettering detected (and fails closed on missing manifest for jobs running assets); asset_execution_errors column added to verify_e2e_scenes.py (must be 0, inherited by G12, G15, G16); red first verified bare (5, 7, 5, 5 execution errors across recorded presentation runs, exiting 1); green verified on current G12 jobs with lettering failure (0 errors, exit 0); stages/assets.py logs asset <id> failed: <err> and execution_errors=<n> in summary; measure_budget.sh asserts 0 execution errors, requires style_degraded=False and >= 2 metaphor images for creative, and archives logs, plan_report, director, and manifest to artifacts/budget/<timestamp>/<span>/ before cleanup; falsified by counting lettering failures as execution errors (exit 1 red bare).
- I7 — Creative presentations get license check, overlays, and honest degradation — git log --grep "(i7)" — G1–G10, G14 green bare, 380 fast passed (+5 tests); presentation tree plans director on creative style with fallback logging director: degraded to literal after <n> attempts: <err> and style_degraded=True; slide passage adapter passed to run_license_checks removing ungrounded metaphors and asides into director.json license_dropped; point scenes run compute_scene_overlays in deck order stored in TreeNode.overlays and propagated to timeline.scenes; R1 second half replaces point title_card with alternate; G8 schema sync verified; live runs history_great_stink (creative, strong) and story_overdue_book (creative, mild) produce director.json, license_calls=4, license_dropped=0, style_degraded=False, >=1 metaphor node, and overlays (7 and 9); falsified bare by skipping license call (assert 0 == 4 red) and empty overlays (assert False red).
- I8 — G16 states its bars in its exit code — git log --grep "(i8)" — G16 exits 3 when follower bars miss while mechanics pass; presentation_sim.sh removes reuse scan, generates jobs in artifacts/presentation_sim/<timestamp>/jobs/, and validates 5 mechanics rules (artefacts exist, step 10 all 0 + word density <= 1.0, oracle §8 bars pass, no point title_card, creative style_degraded=False with >= 1 metaphor, >= 1 overlay, license_calls match); evaluate_presentation_bars in score.py unifies follower and oracle bar checks; scripts/battery.sh refuses to run G16 when PRESENTATION_REUSE_JOBS is set and reports G16 exit code directly; 3 falsifications verified on every run: (a) oracle passes all bars, (b) shuffled heard.json misses accuracy bars, (c) mechanics check on copy without oracle.mp4 fails.
- I9 — Re-measure; close-out of Wave I — git log --grep "(i9)" — full battery G1–G16 bare verified (G1–G15 exit 0, G16 exits 3 as specified); 3 cold budgets measured with 0 cache hits and 0 asset execution errors (primary: 200.52 s / 189.37 s / 389.89 s; long literal: 56.80 / 78.22 / 135.01 s/min; long creative: 76.17 / 79.54 / 155.71 s/min with style_degraded=False and 9 images); cold planner eval 6/6 valid with names_before_narration=0 on all 6; verified visual stills for callback dots, top-left aside + motif token, clean overdue s001 location, 7 former spoiler scenes, and creative metaphor node; Wave I closed out.

**Wave J:**

- J1 — --matcher plumbing, frozen corpus, and replay harness — git log --grep "(j1)" — --matcher added to present-sim (bm25|anticipate|llm, default bm25) with tiebreak and option validation; ingest.json and playback.json record matcher (G8 verified); run_follow_stage fails on unbuilt matchers with exit 2 and logs matcher=<m>; frozen 8-job corpus generated in artifacts/matcher_bakeoff/2026-10-09/corpus/ with corpus.json SHA-256 hashes of 5 key files, 0 asset execution errors, and 0 degraded creative jobs; matcher_bakeoff harness reproduces all 8 jobs' presentation_score.json within 0.000000 <= 0.01 and leaves corpus unmodified; 7/7 tests passed in tests/test_matcher_bakeoff.py including ground-truth PASS, shuffled heard.json MISS, and hash tampering rejection; baseline eval docs/evals/matcher_bakeoff_2026-10-09.md written with decision-set literal jobs agreeing within 0.006 with Issue 8 table and perfect hearing confirming lexical BM25 error is independent of ASR accuracy.
- J2 — Anticipate stage and forward tracker; A1 misses decision set — git log --grep "(j2)" — AnticipationPlan schema (G8 verified); anticipate stage generates 4 sentences per point via Ollama gemma4:26b with length/uniqueness/no-copy validation; AnticipateMatcher evaluates {c, f1, f2, f3, back} with 10-word window, forward commit (gap >= 0.5) and jump commit (gap >= 1.5, 2 steps); bake-off on frozen corpus shows A1 misses all decision-set bars (slide 0.1789-0.2466 vs 0.80-0.90, point 0.1412-0.1946 vs 0.60-0.75); root cause: backward candidate enrichment; proceeds to J3 per §6.6.4 rule 1.
- J3 — Contestant A2 LLM classifier; bake-off evaluation — git log --grep "(j3)" — ClassifierMatcher evaluates current slide points, next 3 points, prior slide titles, and 25 heard words via Ollama gemma4:26b enum schema; single-step f1 commit and two-step jump commit; honest latency measured via last_elapsed_ms; 9/9 tests pass bare; bake-off on frozen corpus shows A2 misses all decision-set bars (slide 0.3390-0.3962 vs 0.80-0.90, point 0.2271-0.2859 vs 0.60-0.75); live-viable confirmed (P90 compute 598.0 ms vs 1.5 s bar); perfect hearing diagnostic confirms tracking error is algorithmic; falsification on empty words collapses point accuracy to 0.0442; per §6.6.4 rule 3 neither contestant adopted; Issue 9 filed.

---

## 4. Deferred features (do not start without a selection)

| Id | Feature | Trigger to start | Notes |
|---|---|---|---|
| DF1 | Video input + PiP of the original speaker | User selects it | The 9:16 PiP placement is an open design question (`design_future_live_and_video.md` §2) |
| DF2 | 16:9 output | User selects it | Roughly doubles template work |
| DF3 | Multi-voice narration (character voices) | User selects it | Needs a dialogue-attribution step (see Issue 5 for how often attribution is wrong today). `voice.json` already records `male` separately from `unknown`. |
| DF4 | **Live mode** (speak in real time, webcam in a corner). *Prepared mode chosen October 5, 2026; Wave H simulates it offline. Slide import and real-time playback remain deferred* | Wave B complete **and** the user answers the three questions in `design_future_live_and_video.md` §4 | The end goal |
| DF5 | Reddit URL fetching | User selects it | Terms-of-service review first |
| DF6 | Public-domain photo sourcing (e.g. Wikimedia) | User selects it | Requires runtime network, which conflicts with the local-only policy as written |
| DF7 | Historical map borders | User selects it | The MVP uses modern borders |
| DF8 | Web editor for the review gate | User selects it | The MVP gate is JSON edit + contact sheet |
| DF9 | Cloud LLM planner backend | Only if the local planner fails its eval bars on both candidate models **and** the user accepts a paid API | Reverses a user decision; needs explicit selection |

---

## 5. Decision log

**September 23, 2026: design grilling (user).** Offline first; template library; history + Reddit-style stories first; MVP inputs text script + audio only; mixed imagery (vector + local illustration + open map data); Python pipeline + TypeScript/Remotion renderer; **fully local**; 9:16 first; word-by-word karaoke captions; flat editorial vector; 1–3 min videos within ~10 min; scenes + persistent cast; single narrator; **mandatory review gate**; music + SFX from a user-supplied pack; live mode later with the webcam in a corner, with some sources (Reddit, history) having no speaker video at all.

**September 23, 2026: design decisions (designer; revisit only through an issue):** cast drawn only as vector avatars; grounding of on-screen numbers, dates and quotes as a hard gate; gazetteer-first geo; Kokoro's own timestamps for the text path; scenes at absolute frames rather than `TransitionSeries`; Python as the contract source of truth; `gemma4:26b` as planner with `qwen3.6:35b` as the measured escalation candidate.

**September 24, 2026: selections (user).** Issue 1 → Options A + B with an automatic rule: female-perspective Reddit story → `af_heart`, else `am_michael`. Issue 2 → Option A, FLUX.2 [klein] 4B. Test stories replaced by two complete, original r/stories-style stories at the user's request.

**September 24, 2026: consequences (designer):** a `voice` stage before narration; "female perspective" = explicit, checkable self-identification (default `am_michael`); `--voice` restricted to the two installed voices; the LLM backend moved ahead of narration (22 items); the evidence rule tightened to two grammatical forms (23 measured cases); a female narrator's avatar gets no facial hair.

**September 25, 2026: verification of Wave A (designer).** All 14 gates reproduced green in an independent session. Defects invisible to the gates were found and specced as Wave B. Design contracts corrected where the design itself was the cause:
- map colours, markers and a lakes layer; the image scrim and a rule for text over images (`design_templates.md` §2.13–2.15, `design_visual_direction.md` §2.1);
- `kinetic_quote` attribution clarified;
- LLM-facing schemas without length limits, a text-completeness validator, scale-word grounding, error classification, and "every call through `run_with_retries`" (`design_planner.md` §1, §6, §8);
- job-local inputs authoritative (`design_system_architecture.md` §4);
- fail-closed gallery gate, an exact purity exemption, E2E music/SFX assertions, cold-budget procedure (`design_testing_and_validation.md`).

Three questions filed for the user (Issues 3–5).

**September 25, 2026: selections (user).**
- Issue 3 → Option A: *"Proceed with Option A. Though, in the example provided, I think that text is fine if the description calls for text like a recipe."*
- Issue 4 → Option A: *"Proceed with Option A."*
- Issue 5 → Option A: *"Option A"*.

**September 25, 2026: consequences (designer, measured before specifying):**
- The text check uses a transcription-style prompt with `num_predict` 96 and a ≥ 3-alphanumeric rule, because a yes/no prompt produced 2 false positives on 4 clean images and an uncapped request hung past 300 s.
- "Description calls for text" is a deterministic word/phrase list; bare "sign" is excluded (it matched "signs of structural weakness").
- The critic is blind, and a speaker it reads as "unknown" never counts as a mismatch, but an unsupported strong tone does. That exact combination is what separated the real errors from correct scenes on seeds 7–9.
- Wave B grows to 17 items, reordered so a single planner-eval re-run covers every planner change and the cold budget run measures the finished system.

**September 26, 2026: verification of Wave B (designer).** All 17 items match their specs and every gate reproduces. Real-output review found the four problems above. Design contracts corrected, each measured before specifying:
- quoted speech is not split, and the colon loses its bonus (`design_audio_and_timing.md` §7);
- critic passage framing, a 3-attempt retry, tone repair, and regression case E (`design_planner.md` §11: five cases 5/5 on seeds 7–9 with the new framing; the old framing answered the narrator on the real case three times out of three);
- the internal-id rule (§6 item 8);
- the caption word-spacing contract plus a measured gap check (`design_visual_direction.md` §8: broken page 4 px, correct pages 12–17 px);
- generated country codes;
- a missing input fails loudly;
- the text-audit bar clarified.

Wave C (C1–C7) specced. Issue 6 filed for the user.

**September 27, 2026: selections and direction (user, in chat).**
- Issue 6: *"I think the paraphrasing is fine."* Recorded as Option D.
- Live presentations: *"For real-time presentations, it makes sense to show timelines and repeated graphics to drive home the point."* Recorded in `design_future_live_and_video.md` §4.
- Stories: *"For these stories, is there a way to show less words in general. Watch the youtube videos of casually explained for inspiration."* Filed as Issue 7.

**September 27, 2026: consequences (designer, measured before specifying):**
- Casually Explained studied frame by frame, and word density measured on the six Wave B E2E renders (Issue 7).
- The text-thread critic now answers one key per message (C2 amended: the array schema left 3 of 8 real threads unchecked) and names the contact (C8: Deb caught on `story_room_12` s018 on 3 of 3 seeds, no false contact reading on 8 threads × 3 seeds).
- Regression cases F, G and H were frozen from real output in `tests/data/critic_text_thread_cases.json`; the critic bar is now 8/8.
- Contracts updated: `design_planner.md` §5, §9 and §11; `design_templates.md` §2.10; `design_testing_and_validation.md` §2; `design_future_live_and_video.md` §4.

**September 27, 2026: selection (user).** Issue 7 → *"Proceed with Option A."*

**September 27, 2026: consequences (designer, measured before specifying, `gemma4:26b`, the Wave B E2E storyboards):**
- **Caps met.** The props stage with the proposed caps passed on 93 of 94 real scenes within the normal 3 attempts, with fewer attempts than Wave B (118 vs 147). The one failure is a 13-word verbatim quote, which the ladder moves to its alternate.
- **Both selection rules are needed.** Caps alone left `story_recipe_box` at 1.13 words/s and 31% light scenes. With R6 (one timeline and one comparison per video) and R7 (rhythm), the four fixtures measure 0.52–0.89 words/s and 39–56%.
- **R7 pictures are deterministic.** A neutral reaction shot, or a named set piece or place: the model invented feelings for plain beats, and the critic's readings were unstable.
- **R7 never replaces kept templates.** Unrestricted, it replaced Meredith's introduction and Deb's reply.
- **Quoted speech never counts as the narrator.** Walt's "I've been waiting…" would otherwise have picked the narrator.
- **The words-per-second bar lives in the E2E.** The planner eval simulates timing at 4 words/s, so it carries the light-share bar only.
- **Relabelled:** the deferred features D1–D9 became **DF1–DF9**, so that Wave D's item ids are unambiguous. `design_future_live_and_video.md` already used F1–F6 for its constraints.
- **New frozen real data:** `tests/data/word_cap_cases.json`, `rhythm_cases.json`, `recipe_choices.json` and `word_caps_live_cases.json`.
- **Contracts updated:**
  - `design_templates.md` §1, §2, §3 and §5 (new);
  - `design_planner.md` §4 (R6, R7), §5, §6 item 9, §9 and §11;
  - `design_testing_and_validation.md` §2 and §4 (step 9);
  - `design_data_contracts.md` §5 and §6.

**October 3, 2026: verification of Waves C and D (designer).**
- Every gate G1–G14 and the cold budget reproduce bare, and all 13 items match their specs.
- **Real-output review found:**
  - the critic's findings do not stick after a retry (35/87 tones, 7/8 quote speakers);
  - unknown emotions never count;
  - R7 replaced quoted speech;
  - a year rendered as "2,016";
  - "Armchair" as the default icon (the prompt never listed the names);
  - an import-time `HF_HOME` override.
- **Each was measured before specifying.**
  - The emotion rule was checked on 13 real beats (4 unsupported feelings read "unknown", none supported).
  - The icon list was checked on 27 real scenes (Armchair 8/54 → 0/56).
  - The critic's readings on the frozen cases were identical across seeds 7–9.
  - A reference implementation reproduced the committed R7 expectations exactly before computing the new ones.
- **Contracts updated:**
  - `design_planner.md` §4 (R7 never replaces quoted speech), §5 (the icon block), §6 item 6 (a year is not a stat) and §11 (the emotion rule; enforcement after the round);
  - `design_templates.md` §5.4;
  - `design_data_contracts.md` §6;
  - `design_testing_and_validation.md` §2.
- **New frozen data:** `tests/data/critic_enforcement_cases.json` and `tests/data/wave_e_expectations.json`.
- Wave E (E1–E6) specced. **No question for the user.**

**October 4, 2026: verification of Wave E (designer).**
- Every gate and the cold budget reproduce bare. All 6 items match their specs, and every Wave E target is fixed in the renders.
- Real-output review found three remaining problems:
  - dates drawn as counters ("3 / rd March"; E3 covered only years);
  - placeholder and instruction text ("Icon: Bullet", "Not specified");
  - invented era stamps (228 of 358 since Wave A have no year).
- **Each was measured before specifying:**
  - the date rule was scanned over every run since Wave A (Wave A, Wave B and Wave E cases), and re-planned live: the scene falls back to quoting its sentence;
  - the junk-text rule was scanned over 9,080 strings (only real junk flagged), and re-planned live: "10 per bird", a real second panel;
  - a retry-based era rule was tried on 11 real scenes and produced worse stamps ("Two days"), so the era rule is a deterministic normalisation.
- **Contracts updated:** `design_planner.md` §5 (era normalisation) and §6 items 6 and 7; `design_templates.md` §2.13; `design_testing_and_validation.md` §2.
- **Relabelled:** the live-mode constraints in `design_future_live_and_video.md` §1 changed from F1–F6 to **LC1–LC6**, so that Wave F's item ids are unambiguous.
- **New frozen data:** `tests/data/wave_f_cases.json`.
- Wave F (F1–F4) specced. **No question for the user.**

**October 4, 2026: verification of Wave F (designer).**
- Every gate and the cold budget reproduce bare. All 4 items match their specs, and every Wave F target is fixed in the renders.
- E2E step 10 was falsified on the pre-Wave-F jobs: it exits 1 on the 3 date stats and the invented stamps.
- `design_testing_and_validation.md` §4 gains step 10, which the guide had specified but no design doc recorded.
- **No new defect needs work;** the guide is rewritten to **Queue Complete** with these watch items:
  - render at 191–200 s against its 210 s bar;
  - `molasses_flood`'s planner-eval light share sitting exactly at 1/3 since Wave D;
  - same-day eval reports overwrite each other by filename; git history keeps every version, and a verifier restores the committed copy after its own runs.
- **Unscheduled behaviours, recorded so no one "fixes" them unasked:**
  - a quotation spanning two sentences can be split between two beats;
  - the critic's emotion-beat *who* reading is noisy;
  - R7 treats reported speech without quotation marks as narration.

**October 5, 2026: direction and selections (user, in chat).**
- **Direction:** *"one of the things I noticed is that the generated animations are very literal to what is being said at any given moment. Lets set up something like a style library. We can keep this as one of the styles but lets have a style that is a bit more creative where the animation adds something to the story (also pick more interesting stories that maybe is longer)."*
- **Direction:** a deck-driven presentation mode with *"a tree of animations that will link each slide to each other as the real time voice is being said"*, simulated by deriving slides from a transcript, perturbing the transcript, generating the video and analysing it (verbatim in `design_presentation_simulation.md`).
- **Creative ingredients:** all four, "Motifs & callbacks, Visual metaphors, Foreshadowing & reveals, Visual gags & asides".
- **License:** "Small embellishments".
- **Slide input:** *"Don't worry about this part for now. I was just explaining the potential future. We do not need to build this out now"*.
- **Story length:** "4–6 minutes (Recommended)".
- **Process:** *"Make sure to not actually perform any coding and just update the docs + execution guide for another agent to implement"*.

**October 5, 2026: consequences (designer).**
- **Two new original fixtures were written:** `story_overdue_book` (756 words; measured cold to `awaiting_review` in 349 s for 5.5 min of narration) and `history_great_stink` (675 words).
- **One finding from the first run:** the library story's original opening ("As the only librarian in Alder Creek, Oregon, and a grandmother of three, I") is rejected by the voice rule's Form B. That is an accepted false negative by design, and it gave `am_michael`. The opening was rewritten into Form B ("As a grandmother of three, I…") so the fixture exercises `af_heart` on a long story. G1 confirms it.
- **No prototypes were written,** per the user's instruction. Every uncertain parameter is specified as an initial decision, with the measurement and bar the implementing agent must run and file against:
  - the director's counts;
  - the license check;
  - the matcher's BM25 / hysteresis / dwell;
  - the presentation bars.
- **New contracts:**
  - `design_styles.md` and `design_presentation_simulation.md`;
  - three templates (`metaphor`, `callback`, `section_title`) in `design_templates.md` §2.17–2.19;
  - rule R8 in `design_planner.md` §4;
  - the new job files in `design_data_contracts.md` §10;
  - the stages and CLI in `design_system_architecture.md`;
  - fixtures, test rows, gates G15/G16 and the long-story budget in `design_testing_and_validation.md`;
  - the DF4 path in `design_future_live_and_video.md` §4.


**October 6, 2026: verification of Waves G and H (designer).**
- **Gates:** G1–G16 and the three cold budgets were re-run bare (`agent_execution_guide.md` §1.3). 11 of the 12 items match their specs. G4's callback dots do not.
- **Real-output review found nine defects the gates could not see** (§1). **Six trace to the designer's specs:**
  - the aside coordinates;
  - the missing thought rule;
  - unchecked, unspaced motifs;
  - "met or filed" for G16, with no "fresh jobs" rule;
  - the one-line "style applies" for presentations;
  - an all-or-nothing director whose prompt never shows rule 6's words.
  
  The rest are the callback dots (code), names before the narration (every style, since Wave A), and the presentation runs' image failures (environment, invisible to every gate). The two cold creative budgets both measured a degraded, literal run.
- **G16 was re-run fresh** at HEAD, building four new jobs. Every Issue 8 number reproduced within 0.05.
- **Each was measured before specifying:**
  - the dot counts (4 tokens shown, 2 dots drawn);
  - the overlay rectangles against each other and the avatar;
  - the spoiler rule replayed on the 7 most recent storyboards (7 of 32 named displays);
  - the manifest error signatures (execution vs lettering);
  - the director's output on the deck;
  - G16's falsification on the real runs (it cannot fail).
- **The matcher (Issue 8) was re-measured** by replaying the agent's `LiveMatcher` with six edge-cost variants on the recorded `heard.json` files. The best variant reaches slide accuracy 0.59; with no back edges at all, 0.45–0.55. So the agent's proposed fix was measured insufficient. The window lag is the designer's spec value. Issue 8 was rewritten with the measurements and five options.
- **Contracts updated:**
  - `design_styles.md` §3.3 (rules 3, 5 and 7), §3.5–3.7 (anchors, geometry, no fallbacks, the rendered overlap probe);
  - `design_presentation_simulation.md` §3 (creative in presentation jobs, the R1 assertion, `tree.json` fields), §6.1 and §8;
  - `design_planner.md` §6 item 6 (the name rule);
  - `design_templates.md` §2.18 (the dot count);
  - `design_data_contracts.md` §7 and §10;
  - `design_testing_and_validation.md` §2 (five rows), §3 (G10, G16), §4 (step 10 columns, G15, §4c exit codes) and §5 (the asset rule);
  - `master_implementation_plan.md` (Wave I).
- **Lessons 2.13–2.16 were added.**
- **Wave I (I1–I9) is specced. One question for the user: Issue 8.**

**October 7, 2026: Issue 8 decided (user, in chat).**
- *"For issue 8, select Option A and write the agent execution guide to reflect that with validation"*.
- **Specced as Wave J (J1–J4)**, after Wave I:
  - a frozen 8-job corpus and a replay harness;
  - contestant A1 (anticipated speech + forward tracker);
  - contestant A2 (LLM point classifier), built only if A1 is not adopted;
  - adoption by the rule.
- **Contract:** `design_presentation_simulation.md` §6.6 (exact prompts, schemas, windows, costs, commit rules and the adoption rule); `design_data_contracts.md` §10 (`ingest.json` → `matcher`, `anticipation.json`, `playback.json` → `matcher`); `design_testing_and_validation.md` §2 (four rows) and §4d.
- **Validation added by the designer:**
  - a held-out seed-11 set, so that no contestant is adopted on numbers it was tuned to;
  - a baseline row proving the harness reproduces `bm25`'s scores;
  - a "perfect hearing" diagnostic separating matcher error from ASR error;
  - harness falsification in both directions;
  - a no-tuning rule.

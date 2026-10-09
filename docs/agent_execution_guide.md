# Agent Execution Guide — Active Build: Wave I (verification fixes, 9 items), then Wave J (Issue 8 → Option A, 4 items) — October 7, 2026

**You are an engineering agent with no memory of this project.** Waves A–H are built, committed and pushed (head `main`).
- **The verification.** Waves G and H were independently verified on October 6, 2026. 11 of their 12 items are true to spec. Real-output review then found **nine defects the gates could not see** (`ongoing_general_errors.md` §1). Six of them come from the designer's specs, not from the code.
- **Wave I (I1–I9) fixes eight of them**, all within approved behaviour.
- **The ninth is the presentation follower's accuracy, Issue 8.** On October 7, 2026 the user selected **Option A**: *"For issue 8, select Option A and write the agent execution guide to reflect that with validation"*. That is **Wave J**: a bake-off of two deck-only followers, adopted by a fixed rule. **Wave J starts only after Wave I is closed,** and during Wave I the matcher is not touched (constraint 15).

**The user's words (October 5, 2026):**
- *"the generated animations are very literal to what is being said at any given moment. Lets set up something like a style library. We can keep this as one of the styles but lets have a style that is a bit more creative where the animation adds something to the story (also pick more interesting stories that maybe is longer)."*
- *"…create a couple of slides from the transcript (key moments) and use that as the power point, then you can create the tree of animations that links each slide together. Then perform some flair on the original transcript … and see what video generates from it. Then we can still run similar analysis that analyzes if the final outputted video was done well."*

**Status:** **Active Build: Wave I** (I1–I9), then **Wave J** (J1–J4), in the §2 order. No user decision is pending. J2 or J3 may end in a filed **Issue 9**, whose `Your selection:` line will belong to the user.

**Every number and literal string in this guide and the design docs is a decision, not a suggestion.**

**The product, in one paragraph.** A local-only CLI that turns a text story (narrated by local TTS) or an audio narration into a 1080×1920 animated explainer video. It has karaoke captions, a persistent avatar cast, checked illustrations, a blind critic, and a mandatory review gate. It has two styles:
- **literal**: the pictures show what is said;
- **creative**: a director adds motifs and callbacks, visual metaphors and small asides, under the user's "small embellishments" license.

An offline **presentation simulation** derives a deck from a script, builds an animation tree from the deck alone, perturbs the script into a "performed" talk, follows it with a causal matcher, and scores the result.

**The lessons that shape this wave** (`ongoing_general_errors.md` §2):
- **2.13: a pipeline that never crashes hides a machine that never ran.** Every image of the four presentation runs failed, and the gates stayed green.
- **2.14: a gate's exit code must state its bars, and a gate builds fresh outputs.** G16 printed "FAIL (Filed)" and exited 0, its falsification could not fail, and it re-scored old jobs instead of running.
- **2.15: a layout test against a hand-kept table tests the table.** Measure the rendered boxes.
- **2.16: a stage reused in a second pipeline leaves its guards behind.**
- **Still binding:** 2.8 (measure the rendered result), 2.10 (enforce rules on the final result) and 2.12 (name the defect class).

---

## 0. Standing constraints (apply to every item)

1. **The battery is the regression bar.** After every item, run the full battery (G1–G16) bare and update §1.3. Read every exit code bare.
   - **Until I8 lands,** G16 exits 0 even though its bars fail; §1.3 records that honestly.
   - **After I8 and until J4,** the expected G16 code is **3** (follower bars missed, Issue 8). A 1 is a regression. A 0 would mean the follower met the bars, which is impossible without touching the matcher, so investigate it.
   - **After J4 adopts a contestant,** G16 must exit **0**.
2. **Fully local at runtime.** No cloud API, and no network except loopback. **Pull no new models**: `gemma4:26b`, Kokoro, mlx-whisper and FLUX.2 klein 4B only.
3. **Python (Pydantic) is the source of truth for every contract.** Generated files are never hand-edited, and G8 covers every contract change (I2, I3, I7).
4. **Templates read time only through the clock.**
5. **The review gate is mandatory** for video and presentation jobs alike. No auto-approve.
6. **The planner never crashes the pipeline.** Every LLM call goes through `run_with_retries`. LLM-facing schemas carry no length constraints; validators enforce limits through retry messages. Every new error string is copied **verbatim** from the design doc that defines it.
7. **Red first, on real inputs.** Before building, run the item's falsifying check against the current code, using the recorded artefacts this guide names, and record the failure.
8. **One item = one Conventional Commit, scope = item id** (`fix(i1): …`, `feat(i2): …`). Put the WHY and the red and green runs in the body. Push after every item. Never amend a pushed commit.
9. **Record each resolution in the same commit** as one line under a new "**Wave I:**" or "**Wave J:**" heading in `ongoing_general_errors.md` §3: `I<n> — <title> — git log --grep "(i<n>)" — <measured result>` (likewise `J<n>`).
10. **When this guide and a design doc disagree, stop and file it.**
11. Every stage log ends in `llm_calls=<n> cache_hits=<m> elapsed_ms=<t>`.
12. **Nothing in the package changes the environment at import.** Export `HF_HOME=$HOME/.cache/huggingface` in your shell if needed. Any run that generates images must show **0 asset execution errors** (I6) to count.
13. **Ids:** waves A–J; deferred features DF1–DF9; live constraints LC1–LC6; issues up to 8 (the next is Issue 9).
14. **Eval reports are named by date.** A second E2E or budget run on the same day overwrites the first. Commit each report in the item that produced it.
15. **The follower changes only in Wave J, and only as `design_presentation_simulation.md` §6.6 says.**
    - **During Wave I:** do not change `presentation/match.py`'s scoring, window, decision points, commit rule, hysteresis, dwell or tie-break, or the edge costs in `presentation/tree.py`. I8 changes how G16 **reports** the bars, not what they are.
    - **In Wave J:** the contestants are **new** classes, and `LiveMatcher` (`bm25`) stays byte-identical as the baseline.
    - **Never:** change the §8 bars or the scorer, regenerate the frozen corpus, or tune a §6.6 constant to pass (§6.6.4 rule 5).

---

## 1. Verified baseline (October 6, 2026; designer's re-run of Waves G and H)

### 1.1 Environment

`doctor`: 22 checks OK.
- M4 Max 64 GB; ffmpeg 8.1; Node v26.5.0; Python 3.12 (uv).
- Ollama with `gemma4:26b`; Kokoro 0.9.4; mlx-whisper 0.4.3.
- mflux (`flux2-klein-4b`); Remotion 4.0.528.

### 1.2 Repository

- Waves A–F: `4df212a` … `c88a69f`.
- Wave G: `afb1b5f` … `e5d590e`.
- Wave H: `0893fc1` … `6150482`.
- Per-item verdicts for all of them: `ongoing_general_errors.md` §3.

### 1.3 Gates (run bare October 6, 2026 by the designer; the regression bar)

| # | Gate | Result |
|---|---|---|
| G1–G3 | ruff / format / mypy | exit 0 (156 files formatted; 81 source files) |
| G4 | `uv run pytest -q -m "not slow"` | exit 0 · **350 passed** |
| G5–G7 | renderer typecheck / lint / vitest | exit 0 · 19 vitest |
| G8 | schema sync | exit 0 · in sync |
| G9 | renderer purity | exit 0 · pure |
| G10 | gallery | exit 0 · 59 goldens, 0 overflows. **It does not measure overlaps yet** (I2) |
| G11 | `uv run pytest -q -m slow` | exit 0 · **43 passed** (238 s) |
| G12 | `./scripts/e2e.sh` | exit 0 · steps 1–10 passed (870 s) · 0.52–0.83 graphic words/s. It reproduces the "Sofia" spoiler (I5) |
| G13 | offline | exit 0 (236 s) |
| G14 | doctor | exit 0 · 22 OK |
| G15 | `./scripts/creative_e2e.sh` | exit 0 (1,211 s) · 0.74 / 0.84 graphic words/s. **Its fresh jobs reproduce I1–I5:** 2 dots for 4 tokens, the empty s001 thought, "Silver Pump Handle" and "Blue ink pen", and 6 spoilers |
| G16 | `./scripts/presentation_sim.sh` | **exit 3: follower bars missed (Issue 8)** · mechanics clean · oracle meets all bars · follower slide 0.32–0.56, point 0.20–0.36 |
| Budget | `story_recipe_box`, cold | 209.13 s / 195.74 s / 404.86 s (≤ 390 / 210 / 600), 0 cache hits, 5 images |
| Budget (long) | `story_overdue_book`, literal cold | 60.47 / **79.23** / 139.71 s/min (≤ 90 / 80 / 170). Render is 0.8 s/min under its bar; watch it |
| Budget (long creative) | `story_overdue_book`, creative cold | exit 0, 59.37 / 78.46 / 137.83 s/min (≤ 110 / 85 / 195). **Not a creative measurement:** 5 images, 3 text checks and 114 LLM calls are the literal signature; a creative run gives 9, 7 and 117. Replayed under the same conditions (`ollama stop`, cold cache), the director failed 3 attempts and degraded (I4). The agent's committed report has the identical signature. **No valid creative budget exists yet** (I9) |

### 1.4 Measurements that shaped Wave I (October 6, 2026)

| What | Result |
|---|---|
| Callback dots | Both creative E2E callbacks (`history-great-stink-20261006-164729` s056, `story-overdue-book-20261006-164040` s051) had **4** earlier motif tokens on screen, `timing.item_frames == []`, and drew **2** dots |
| Overlay geometry | Token [840, 180, 960, 300], thought [720, 175, 960, 345] and label [680, 200, 1000, 260] all overlap one another. Thought and label overlap `character_intro`'s avatar [320, 180, 760, 620] by 40–80 px. The vitest passed, because its table omits the avatar and it never compares two overlays |
| Empty thought | `story-overdue-book-20261006-164040` s001 (`character_intro`): `{"kind": "thought", "icon": null, "text": null}`, drawn as a generic "…" bubble over the avatar |
| Motif names and spacing | "Silver Pump Handle" ("silver" is never said); "Blue ink pen" ("pen" is never said). The ink motif's appearances fall at beats 12, 15, 18, 19 and then 51 |
| Names before the narration | **7 of 32** named displays in the 7 most recent storyboards; all `llm planned` (list in I5) |
| Presentation images | 0 generated in all four of the agent's runs; failures 5, 7, 5, 5. Every one is `mflux exited with code 1` inside `snapshot_download`, ≈ 970 ms, `attempts: []`. A real lettering failure looks different: `lettering detected in 3 attempts`, with 3 attempts recorded |
| Creative presentation | `history-great-stink-20261006-132526` has 2 metaphor nodes that were never license-checked and 0 overlays. `story-overdue-book-20261006-124735` (creative) has **no `director.json`**, and its template counts are identical to the literal run's |
| G16 | `presentation_sim.sh:336` prints "FAIL (Filed)" and `:424` exits 0. The falsification at `:226–268` asserts that shuffled speech scores below the mild bars, and so do the real runs (slide 0.32–0.56). **And `:52–80` re-scores any matching job in `jobs/` instead of running the pipeline.** The designer's battery run re-scored the agent's four jobs and built nothing |
| Director all-or-nothing | After `ollama stop` with a cold cache, all 3 attempts on `story_overdue_book` kept the beat-24 metaphor "A paper book … mailbox flag", which breaks rule 6 ("book"), so the job degraded to literal. The overdue **deck** fails the same way ("…burying a single small book") on every run, so every creative presentation of it has been literal. Warm-loaded, the same story plans 1 motif, 4 metaphors and 5 asides. The attempts are in `docs/evals/assets/2026-10-06/wave_i_director_attempts.json` |
| Matcher (Issue 8 → Wave J) | Oracle 0.98–1.00. Follower: slide 0.32–0.56, point 0.20–0.36, lag median 7.4–10 s. The best edge-cost variant (back 4.0) reaches slide 0.55–0.59 |

---

## 2. Execution order

| # | Item | Why this position |
|---|---|---|
| I1 | Callback dots count real appearances | Self-contained (compile + one template). Its golden changes are independent of I2's |
| I2 | Asides move top-left; overlap measured on the rendered frame | Changes `SceneOverlay` (anchor enum), `OverlayLayer` and the gallery. I3 extends the same validator and component |
| I3 | A thought aside always says something | Extends I2's `SceneOverlay` validator and `OverlayLayer` |
| I4 | Motifs named and spaced; salvage instead of all-or-nothing | Director validators and salvage. I7 reruns the director on decks, and I9's creative budget needs a director that does not degrade |
| I5 | No name on screen before the narration says it | A planner validator, plus the step-10 column that I6 and I8 reuse |
| I6 | An execution failure fails the gate | Adds the asset column to step 10. I8's mechanics need it, and I9's budgets must count it |
| I7 | Creative presentations get the license check, overlays and honest degradation | Needs I2/I3's overlay contract, I1's dot count and I4's director rules |
| I8 | G16 states its bars in its exit code | Its mechanics assert I5, I6 and I7's outputs |
| I9 | Re-measure; close-out of Wave I | Measures the finished system. The corpus J1 freezes must come from it |
| J1 | `--matcher` plumbing, frozen corpus, replay harness | The ruler first. The corpus needs Wave I's trees (I4/I7 change creative trees), honest images (I6) and an honest G16 (I8) |
| J2 | Contestant A1 (anticipate + forward tracker); decide | The rule builds A1 first: no LLM in the live loop, and the cheapest |
| J3 | Contestant A2 (LLM classifier); decide | **Only if J2 ends with "A1 misses the decision set"** |
| J4 | Adopt, gate, close out | Needs the decision |

---

## 3. The items

### I1 — Callback "seen before" dots count the motif's real appearances

**What this means for the user:** the dots are what make a callback read as a callback ("you've seen this 4 times"). Today every callback shows two, whatever the viewer saw.

**The gap:**
- **Compile:** `src/animated_infographics/compile.py:62–79` (`_get_item_count`) has no `callback` branch, so it returns 0, and `compile.py:246–251` writes `item_frames = []`.
- **Renderer:** `renderer/src/templates/callback.tsx:75–77` falls back to `[15, 27]`, and `:78` sets `dotCount = itemFrames.length`, so there are always 2 dots.
- **SFX:** the registry's `ding` cue fires `at="item"` (`contracts/templates.py:724`), so it has no frames to fire on.
- **Contract:** `design_templates.md` §2.18 and `design_styles.md` §3.6: one dot per earlier **rendered** appearance, at `item_frames` (`spread 0.4`), with **no renderer default**.

**Implementation:**
1. **Count in `compile`.** In `compile.py`, the item count of a `callback` scene at index `idx` is the number of scenes with index < `idx` whose overlays, in the **same** `scene_overlays` mapping `compile` writes into the timeline (`compile.py:267`), contain a `motif_token` whose `motif_id` equals the callback's `props.motif_id`. Write it as a helper `callback_item_count(idx, scenes, scene_overlays) -> int`. I7 reuses it in `compose`. Then `item_frames(n, scene_frames, 0.4)` applies as for every other item template.
2. **No renderer default.** In `callback.tsx`, use `const itemFrames = timing?.item_frames ?? [];` and draw `itemFrames.length` dots. With 0 dots there is no row and no empty container.
3. **SFX.** Confirm that the existing item-cue path emits one `ding` per item frame for `callback`. If it skips templates outside a hard-coded list, add `callback` there.
4. **Gallery.** The `callback__min`, `__typical` and `__max` fixtures set `timing.item_frames` explicitly: 1, 2 and 5 dots. Re-cut those three goldens, open each one, and name them in the commit body.

**Validation:**
- **Red first:** the new unit test (`design_testing_and_validation.md` §2, row "callback dots") against the current `compile` gives `len(item_frames) == 0`, not 3. Record it.
- **Green:**
  - the unit row;
  - the renderer test: `item_frames: []` draws 0 dots;
  - **recompile** the two creative E2E jobs (`artifacts/creative_e2e/20261006_094037/jobs/history-great-stink-20261006-164729` and `story-overdue-book-20261006-164040`, with `uv run infographics rerun <job> --from compile --jobs-dir <its jobs dir>` on a copy), and each callback's `len(item_frames)` must be **4**;
  - render the callback scene still and count 4 dots.
- **Add to G15** (`evals/verify_creative.py`): for each `callback` scene, `len(timing.item_frames)` equals the earlier token count and is ≥ 1.
- **Falsify:** restore the `[15, 27]` default → the renderer test goes red. Make `callback_item_count` return 0 → the G15 assertion goes red.

**Blast radius:** `compile.py`, `renderer/src/templates/callback.tsx`, the callback gallery fixtures and 3 goldens, `evals/verify_creative.py`, and tests. The design docs are already updated.

---

### I2 — Asides move top-left; overlap is measured on the rendered frame

**What this means for the user:** today a thought bubble or label is drawn on top of the motif token, and on an intro, over the character's face. The two creative devices hide each other on the scenes they are meant to enrich.

**The gap:**
- **Renderer:** `renderer/src/story/OverlayLayer.tsx` draws:
  - the token at [840, 180, 960, 300] (`:86–95`);
  - the thought at [720, 175, 960, 345] (`:119–128`);
  - the label at [680, 200, 1000, 260] (`:168–177`).
  
  Every pair overlaps; the coordinates came from the designer's spec.
- **The test:** `renderer/src/theme/overlayLayout.ts:68–104` (`TEMPLATE_SLOT_BOUNDS`) omits `character_intro`'s avatar [320, 180, 760, 620], even though the falsification case at `OverlayLayer.test.ts:40–81` cites it. The test never compares one overlay with another.
- **Contract:** `design_styles.md` §3.5–3.6 (revised), `design_data_contracts.md` §7 and `design_testing_and_validation.md` G10.

**Implementation:**
1. **Contract.** `SceneOverlay.anchor` (`contracts/models.py:784`) gains `"top_left"`. A model validator requires `motif_token`→`top_right`, `thought`/`label`→`top_left` and `prop`→`bottom_left`. Regenerate the schema and TypeScript (G8). `compute_scene_overlays` (`compile.py:82`) writes the anchor from the kind.
2. **Geometry** (`design_styles.md` §3.6):
   - **thought:** a cloud 240×170 centred at (180, 250), i.e. the box [60, 165, 300, 335];
   - **label:** a chip with left edge x 60 and top y 200, text body 700 34→26 · **2 lines · 240 px**, within [60, 200, 300, 302];
   - **token and prop:** unchanged.
   
   Update `OVERLAY_BOUNDS` to exactly [840,180,960,300], [60,165,300,335], [60,200,300,302] and [100,1020,240,1160].
3. **Markers:**
   - each overlay root: `data-overlay="<kind>"`;
   - `FitText`'s root (`renderer/src/components/FitText.tsx`): `data-slot="<slotName>"`;
   - `Avatar`'s root (`renderer/src/components/Avatar.tsx`): `data-occupies="avatar_<cast_id>"`;
   - every template icon or node that is part of the layout: `data-occupies="<name>"`. At minimum, everything `TEMPLATE_SLOT_BOUNDS` lists today: `stat_callout`'s icon, `relationship_map`'s nodes and `cause_effect`'s cards.
   - **Illustrations are not marked.**
4. **The probe.** In the gallery composition only (`renderer/src/gallery/Gallery.tsx`), measure after layout on the golden's frame, using the same hook and timing that `FitText` uses to emit `OVERFLOW`:
   - read `getBoundingClientRect()` of every marked element of the scene;
   - for every overlay × overlay pair and every overlay × (`data-slot` or `data-occupies`) pair with an intersection area > 0, log exactly `OVERLAP fixture=<id> overlay=<kind> other=<name> px=<area>`, with the area rounded to an integer;
   - elements inside an overlay root (its own `FitText` and icon) belong to that overlay and are never compared with it.
5. **Collection.**
   - `renderer/scripts/render.ts` parses `OVERLAP` lines next to `OVERFLOW` (`:98–114`) into `logs/overlap.json`, and copies it beside `overflow.json` (`:370–378`).
   - Gallery mode exits 1 on any entry.
   - `scripts/check_gallery.sh` treats a missing or unparseable `overlap.json` as a failure, exactly as `:54–78` does for `overflow.json`.
6. **Fixtures.** For each of the 10 allowed templates:
   - `overlays__<template>` carries a token, a thought and a prop (two asides at once: a probe-only combination);
   - a new `overlays_label__<template>` carries a token and a label.
   
   Use the widest 3-word strings the fixtures use today. Thought and label share the top-left aside slot and are never drawn together. Re-cut the 10 goldens, cut the 10 new ones, open each one, and name them in the commit body.
7. **Vitest** (`OverlayLayer.test.ts`):
   - delete `TEMPLATE_SLOT_BOUNDS` and its two slot cases;
   - keep the allowed/forbidden partition case;
   - add: the four `OVERLAY_BOUNDS` boxes equal the values in step 2, and every pair drawn together is disjoint: token × thought, token × label, token × prop and thought × prop.

**Validation:**
- **Red first:** build steps 3–6 **before** moving anything. G10 with the **old** coordinates must print `OVERLAP` lines:
  - thought × motif_token on every `overlays__*` fixture;
  - label × motif_token on every `overlays_label__*` fixture;
  - thought × avatar and label × avatar on the two `character_intro` fixtures.
  
  It must exit 1. Record the lines.
- **Green:** 0 `OVERLAP` lines and 0 overflows on all 20 overlay fixtures; the goldens cut; G8 in sync.
- **Falsify:**
  - move the thought back to centre (840, 260) → G10 exits 1 naming `motif_token`;
  - delete `overlap.json` after the render → G10 fails closed.
- **Look:** open `overlays__character_intro` and `overlays__relationship_map` and describe where each overlay sits relative to the faces.

**Blast radius:**
- contracts and generated schema/TS;
- `compile.py`;
- `OverlayLayer.tsx`, `overlayLayout.ts`, `OverlayLayer.test.ts`;
- `FitText.tsx`, `Avatar.tsx`, and the marked templates;
- `Gallery.tsx`, `render.ts`, `check_gallery.sh`;
- 20 fixtures and 20 goldens (10 changed, 10 new).

---

### I3 — A thought aside always says something

**What this means for the user:** the overdue story's very first scene carries an empty "…" bubble. An aside with nothing to show should not be drawn.

**The gap:**
- **Director:** the validator in `planner/director.py:429–433` requires only a `cast_id` for a thought.
- **Renderer:** `OverlayLayer.tsx` substitutes `ChatCircleDots` (`:157–158`), `Sparkle` (`:110`) and `Package` (`:228`).
- **Real case:** `artifacts/creative_e2e/20261006_094037/jobs/story-overdue-book-20261006-164040/timeline.json` s001.
- **Contract:** `design_styles.md` §3.3 rule 7 and §3.6 ("No fallback icons"); `design_data_contracts.md` §7.

**Implementation:**
1. **Director rule 7:** a thought needs a `cast_id` **and** an `icon` or a `text`. Error, verbatim: `asides[<k>]: a thought needs an icon or text`.
2. **`SceneOverlay`'s validator** (from I2) also requires:
   - `thought`: an icon or a text;
   - `prop`: an icon;
   - `label`: a text;
   - `motif_token`: an icon and a `motif_id`.
3. **`compute_scene_overlays`** drops an aside lacking its data into `overlay_dropped` with reason `incomplete`. This guards against a hand-edited `director.json` at review.
4. **Renderer:** remove the three fallback icons. An overlay without its data is not drawn.

**Validation:**
- **Red first:**
  - the director unit case `{"kind": "thought", "icon": null, "text": null, "cast_id": "c1"}` passes today's validators;
  - recompiling a copy of `story-overdue-book-20261006-164040` (`rerun --from compile`) keeps s001's empty thought.
- **Green:**
  - the exact error;
  - the recompile records s001's thought under `overlay_dropped` (`incomplete`);
  - the contract cases in the "overlay anchors and completeness" row.
- **Add to G15:** no `thought` overlay lacks both `icon` and `text`.
- **Falsify:** remove the new clause from rule 7 → the unit case goes red.

**Blast radius:** `planner/director.py`, contracts, `compile.py`, `OverlayLayer.tsx`, `evals/verify_creative.py`, and tests.

---

### I4 — Motifs named in the story's words and spaced; one stuck item no longer sinks the plan

**What this means for the user:**
- A callback labelled "Silver Pump Handle" names something the story never mentions.
- The overdue story's callback arrives 2.5 minutes after the viewer last saw the ink, by which time it is forgotten.
- **Most seriously,** one metaphor the model keeps repeating ("a paper book…") silently turns a whole creative video, or a whole creative presentation, into a literal one.

**The gap:**
- **Director:** `planner/director.py:235–246` checks a motif name's word count only. `:298–327` checks plant-before-payoff, but not spacing.
- **Frozen evidence:** `director.json` in `history-great-stink-20261006-164729` (name "Silver Pump Handle") and in `story-overdue-book-20261006-164040` (name "Blue ink pen"; appearances 12, 15, 18, 19, 51).
- **All-or-nothing:** `plan_director` (`director.py:474–481`) returns `None` when the third attempt fails, however small its errors. The recorded attempts are in `docs/evals/assets/2026-10-06/wave_i_director_attempts.json`.
- **The hidden list:** the prompt never shows the model rule 6's word list.
- **Contract:** `design_styles.md` §3.3 rules 3 and 5 (revised), "Show the model rule 6's words" and "Salvage after the last attempt".

**Implementation:**
1. **Rule 5, story words.**
   - Take the words of `name` as `re.findall(r"[A-Za-z']+", name)`, minus `a`, `an`, `the`, `of` and `and`.
   - Each word must occur as a whole word, casefolded, in the narration: the beat texts joined. A trailing `s` may be added or removed.
   - Error, verbatim: `motifs[<k>].name: "<word>" is not in the narration — name the motif with the story's own words`.
2. **Rule 3, spacing.** Sort the appearances by `beat_i`. Consecutive appearances must be ≥ 3 apart, and the payoff ≤ 20 after the previous appearance. Errors, verbatim (§3.3):
   - `motifs[<k>].appearances: beats <a> and <b> are too close — keep appearances at least 3 beats apart`
   - `motifs[<k>].appearances: the payoff at beat <p> is <d> beats after the last appearance at <a> — add an echo or move the payoff within 20 beats`
3. **The prompt** (`planner/prompts/director.md`) gains one sentence, verbatim: `Name each motif with words the narration uses, and spread its appearances: at least 3 beats apart, with the payoff within 20 beats of the appearance before it.` Re-read the whole prompt after the edit (lesson 2.12).
4. **Rule 6's words in the prompt.** The prompt line is verbatim from §3.3, with the list generated from `TEXT_EXPECTED_WORDS` and `TEXT_EXPECTED_PHRASES` (`assets/illustrate.py:44`, `:134`), never copied.
5. **Salvage** (§3.3, verbatim):
   - after the third attempt, if every error is item-local or a count error, remove the erring items into `director_dropped`, waive the counts, and accept the plan if anything remains;
   - otherwise degrade as today.
   
   Add `director_dropped` to `DirectorPlan` (G8). `report.json` and the contact sheet list the dropped items, like `license_dropped`.
6. **Frozen data:** the two `director.json` files above, with their transcripts, and the two cases in `wave_i_director_attempts.json` go into `tests/data/wave_i_director_cases.json`.

**Validation:**
- **Red first:** today's validators pass both frozen plans. Record it.
- **Green:**
  - the history plan fails rule 5 on "silver";
  - the overdue plan fails rule 5 on "pen" and rule 3 twice (18/19 too close; 51 is 32 after 19);
  - the passing cases from the testing row pass ("the pump handle", "pumps"; 19, 35, 42, 48, 56).
- **Salvage:** both recorded cases end in a salvaged plan (testing row "director salvage and prompt"). The cold story keeps 3 metaphors; the deck keeps 1.
- **Live, under the conditions that broke it:** for each of the 6 fixtures, run `ollama stop gemma4:26b`, then the director with a fresh cache.
  - It must end in a plan, valid or salvaged, on **6/6**, never degraded.
  - Record per fixture: the attempts, the `director_dropped` items and every motif name.
  - **If any fixture degrades, or salvage drops a motif on more than 2 fixtures, STOP and file it** with the errors and options. Do not loosen 3 or 20.
- **Add to G15:** every rendered motif name passes rule 5.
- **Falsify:**
  - drop the trailing-`s` allowance → the "pumps" case goes red;
  - set 20 → 40 → the overdue spacing case passes, so the test goes red.

**Blast radius:** `planner/director.py`, `planner/prompts/director.md`, `contracts/director.py` and generated files (G8), `preview.py` (contact sheet and report), `evals/verify_creative.py`, tests and frozen data.

---

### I5 — No name on screen before the narration says it

**What this means for the user:** the video reveals that the anonymous note came from "Robert Okafor" minutes before the story does, and introduces "Sofia" while the narrator still says "a woman walked in". This is in every style.

**The gap:**
- **Code:** `planner/validate.py` has no such rule. The meaning rules sit in `validate_scene` (`:438` onwards, e.g. the "ago" rule at `:664–667`, which already reads `full_transcript`).
- **The contract** is `design_planner.md` §6 item 6, "A name is not shown before the narration says it", which defines the fields, the name tokens and four error strings.
- **Measured:** 7 of 32 named displays.

**Implementation:**
1. **The rule.** Add it to `validate_scene` exactly as specified:
   - **fields:** `kinetic_quote.attribution_cast_id`, `character_intro.cast_id`, each `relationship_map.cast_ids` entry and `text_thread.contact_cast_id`;
   - **exempt:** cast members with `is_narrator`;
   - **narration prefix:** transcript words `0 … beat.word_end`;
   - **match:** the full name, or a name token (letters and apostrophes, ≥ 3 characters, not `the`/`of`/`and`/`mr`/`mrs`/`ms`/`dr`), as a whole word, casefolded;
   - **errors:** the four strings, verbatim.
   - Wire the beat's `word_end` in the same way the existing beat-text rules get `beat_text`.
2. **Frozen data:** `tests/data/spoiler_cases.json`, holding the 7 measured scenes with their props, the bible cast entry, and the transcript up to the beat end:
   - `artifacts/creative_e2e/20261006_094037/jobs/history-great-stink-20261006-164729`: s004 (`relationship_map`, John Snow) and s015 (`character_intro`, John Snow);
   - `…/story-overdue-book-20261006-164040` and `…/story-overdue-book-20261006-165345`: s012 (`kinetic_quote`, Robert Okafor) and s017 (`relationship_map`, June Lind);
   - `artifacts/e2e/20261006_092212/jobs/room12_run/story-room-12-20261006-162927`: s019 (`character_intro`, Sofia).
3. **The step-10 column.** `evals/verify_e2e_scenes.py` gains a `names_before_narration` column over the final storyboard, using the same function, imported rather than copied. Its count must be 0. The planner eval (`evals/planner.py`) reports it with a bar of 0.

**Validation:**
- **Red first:** the new column on the four job directories above reports 2, 2, 2 and 1, and exits 1 (`design_testing_and_validation.md` §4 step 10).
- **Green:**
  - each frozen case gives its exact error;
  - the same scene moved after the name passes;
  - a narrator `character_intro` passes;
  - a `dialogue` with an unnamed speaker passes.
- **Live:** re-plan `story_overdue_book` (creative), `history_great_stink` (creative) and `story_room_12` (literal) cold. The column must be 0. For each of the 7 former scenes, write in the commit body what the final scene shows now. The planner eval's fallback bars must still hold.
- **Falsify:** delete the rule → every frozen case goes red.

**Blast radius:** `planner/validate.py`, `evals/verify_e2e_scenes.py`, `evals/planner.py`, tests, frozen data, and the E2E report columns.

---

### I6 — An execution failure fails the gate

**What this means for the user:** today every illustration in a run can fail to generate, the video quietly ships with icon fallbacks, and every gate says green.

**The gap:**
- **Evidence:** `jobs/history-great-stink-20261006-124512`, `-132526`, `jobs/story-overdue-book-20261006-134157` and `-124735` have `assets/manifest.json` entries with `status: "failed"`: 5, 7, 5 and 5 of them. Each has the error `mflux exited with code 1: … huggingface_hub/_snapshot_download.py …` and `attempts: []`.
- **Logs:** each `logs/assets.log` holds only the summary line written by `stages/assets.py:37`.
- **No gate counts them:** neither step 10 nor G15, G16 nor `measure_budget.sh`.
- **Contract:** `design_testing_and_validation.md` §4 step 10 (the asset execution column) and §5 (a budget run counts only with 0 of them).

**Implementation:**
1. **The health function.** Add `evals/asset_health.py` with `execution_errors(job_dir) -> list[dict]`. It returns the manifest entries with `status == "failed"` whose `error` does not start with `lettering detected`. A job that ran the assets stage but has no `assets/manifest.json` is itself an error (fail closed).
2. **Step 10.** `verify_e2e_scenes.py` gains an `asset_execution_errors` column, which must be 0, so G12, G15 and G16 inherit it.
3. **The budget** (`design_testing_and_validation.md` §5, revised):
   - `scripts/measure_budget.sh` exits 1 when the measured job has any execution error, and writes the count into the budget report.
   - **For `--style creative`,** it also exits 1 unless `plan_report.style_degraded` is false and ≥ 2 metaphor images are in `assets/images/`.
   - Before its cleanup trap deletes the temp dirs, it copies the job's `logs/`, `plan_report.json`, `director.json` and `assets/manifest.json` to `artifacts/budget/<timestamp>/<span>/`.
4. **The assets log.** `stages/assets.py` adds `execution_errors=<n>` to its summary line, and logs one line per failure before it: `asset <id> failed: <first line of the error>`.
5. **Diagnose the agent's environment.** In your normal shell, re-run a copy of `jobs/history-great-stink-20261006-124512` with `rerun --from tree`. Presentation jobs allow only `deck`, `tree`, `perform`, `follow` and `compose` (`cli.py:654`). The assets stage runs after the tree, and a warm LLM cache keeps the tree identical.
   - Record `env | grep -E '^HF_'` and whether images generate.
   - If the cause is in the repository (e.g. a stage that sets `HF_HUB_OFFLINE` without `HF_HOME`), fix it in this item.
   - Otherwise, write the cause in the commit body.

**Validation:**
- **Red first:** the new column on the four jobs above gives 5, 7, 5 and 5, and exits 1.
- **Green:**
  - a unit case: a manifest with one `lettering detected in 3 attempts` entry → 0;
  - one with `mflux exited with code 1` → 1;
  - a missing manifest → an error;
  - the current G12 jobs, which have one lettering failure, → 0.
- **Falsify:** count lettering failures as execution errors → the lettering unit case goes red.

**Blast radius:** `evals/asset_health.py`, `evals/verify_e2e_scenes.py`, `scripts/measure_budget.sh`, `stages/assets.py`, and tests.

---

### I7 — Creative presentations get the license check, overlays, and honest degradation

**What this means for the user:**
- in a creative presentation, metaphors reach the screen without the check that keeps them truthful;
- motif tokens and asides never appear;
- one "creative" run was silently literal.

**The gap:**
- **No license check:** `presentation/tree.py:153–159` calls `plan_director` and writes `director.json`, but never runs the license check (`planner/license.py`).
- **No overlays:** `tree.py:494` and `compose.py:219` hard-code `"overlays": []`.
- **Silent degradation:** when the director returns `None`, nothing is logged or recorded.
- **Evidence:** `jobs/story-overdue-book-20261006-124735` (`style: creative` in `ingest.json`) has no `director.json`, and its template counts are identical to the literal run's.
- **Contract:** `design_presentation_simulation.md` §3, "Creative in a presentation job" (items 1–6), and the R1 assertion above it.

**Implementation:**
1. **The overdue failure is diagnosed.** Case `story_overdue_book_deck` in `docs/evals/assets/2026-10-06/wave_i_director_attempts.json`: all 3 attempts kept a "book" metaphor (rule 6). I4's salvage turns it into a plan with 1 metaphor; this item makes that plan reach the screen. Confirm it by re-running `present-sim` and checking that `director.json` exists with a `director_dropped` entry.
2. **The license check.**
   - After the director, run the license check on every metaphor and aside.
   - `planner/license.py`'s `_build_passage` (`:45`) builds a four-beat passage. Add a parameter, or a presentation adapter, so that the passage is **the point's slide**: its title and all its points.
   - Removed items go into `director.json`'s `license_dropped`.
3. **Overlays.**
   - Run `compute_scene_overlays` over the point scenes in deck order, and store the result in a new node field `overlays: list[SceneOverlay] = []` (G8).
   - `compose` copies a node's `overlays` into every timeline scene it emits for that node.
   - `compose` computes a `callback`'s `item_frames` with I1's `callback_item_count`, applied to the deck-order nodes.
4. **Records.**
   - `TreePlan` gains `style_degraded: bool = False`.
   - `logs/tree.log` ends with `director=<ok|degraded> license_calls=<m> license_dropped=<d> overlays=<o>`.
   - On degradation, also log `director: degraded to literal after <n> attempts: <last validator error>`.
5. **R1's second half.** A point node selected as `title_card` is replaced with its alternate and logged `RuleRepair(rule="R1")`.

**Validation:**
- **Unit:** the "creative presentation" row in `design_testing_and_validation.md` §2.
- **Live:** run `present-sim` on `history_great_stink` (creative, strong) and `story_overdue_book` (creative, mild). Each must have:
  - a `director.json`;
  - `license_calls` equal to its metaphors plus asides;
  - ≥ 1 `metaphor` node;
  - ≥ 1 non-empty `overlays` in `timeline.json`;
  - `style_degraded: false`, or the failure filed per step 1.
  
  Open a metaphor node's still and an overlay node's still, and describe each.
- **Isolation:** the existing isolation test extends to the license call. It may read only the deck.
- **Falsify:**
  - skip the license call → the backend-counter unit case goes red;
  - hard-code `overlays: []` again → the overlay unit case goes red.

**Blast radius:**
- `presentation/tree.py`, `presentation/compose.py`;
- `planner/license.py`;
- `contracts/tree.py` and generated files (G8);
- tests.

---

### I8 — G16 states its bars in its exit code

**What this means for the user:** today the presentation gate says "green" while the follower shows the wrong slide half the time. After this item, the battery says so plainly, and a real regression can no longer hide behind a known miss.

**The gap:**
- **Fail-open exit:** `scripts/presentation_sim.sh:336` labels a missed bar "FAIL (Filed)" and the script ends `exit 0` (`:424`).
- **A falsification that cannot fail:** `:226–268` asserts that shuffled speech scores below the mild bars. The real runs score below them too.
- **It does not run the pipeline when old jobs exist:** `:52–80` scans `jobs/` (git-ignored) for a job with the same fixture, style, level and seed, and re-scores it. The designer's battery run (1,416 s, exit 0) only re-scored the agent's four jobs from October 6, 12:45–13:41; so did H6. The script defines `ARTIFACTS_DIR` (`:26`) but never puts jobs in it.
- **Contract:** `design_testing_and_validation.md` §4c (revised) and the G16 row in §3. The designer's earlier wording, "met or filed", caused this.

**Implementation** (`design_testing_and_validation.md` §4c, verbatim rules):
0. **Fresh jobs, always.**
   - Delete the reuse scan (`:52–80`).
   - Every run creates its jobs in `artifacts/presentation_sim/<timestamp>/jobs/`, and `PRESENTATION_JOBS_DIR` defaults there.
   - Find each new job by the job id that `present-sim` prints, not by sorting directory names (`:101`).
1. **Mechanics, each failing with exit 1:**
   - every artefact exists;
   - step 10 is all 0, including I5's and I6's columns, and the density bar holds;
   - **the oracle meets every §8 bar**, judged by **the same bars function** the follower is judged by;
   - no point node uses `title_card`;
   - each creative run has `style_degraded: false`, ≥ 1 `metaphor` node, a `tree.log` whose `license_calls` equals the metaphors plus asides plus `license_dropped`, and ≥ 1 non-empty `overlays`.
2. **Bars.** Print one `BAR <run> <metric> <value> <bar> PASS|MISS` line per run and metric. If the mechanics pass and any follower bar misses, exit **3**.
3. **Falsification, every invocation:**
   - (a) the bars function on the **oracle** playback must PASS everything (this is the oracle mechanics check, run through the same function);
   - (b) on a **shuffled** `heard.json`, it must MISS the accuracy bars;
   - (c) the mechanics check on a temporary copy of one job with `out/oracle.mp4` deleted must fail.
   
   If any of these behaves otherwise, exit 1.
4. **Reuse for iteration only.** When `PRESENTATION_REUSE_JOBS="<four job dirs>"` is set, the script skips creating jobs and runs everything else on those jobs. The report is then headed `NOT A GATE RUN: re-scored existing jobs`. `battery.sh` refuses to run G16 while the variable is set.
5. **The battery.** `scripts/battery.sh` (`:50`, `:112`, `:142`) reports G16's code as it is. The battery's own exit is non-zero while G16 is non-zero.
6. **The report.** `docs/evals/presentation_<date>.md` shows the BAR table and the line `exit 3: follower bars missed (Issue 8)`.

**Validation:**
- **Red first:**
  - the **current** script, run as the battery runs it, prints `Reusing existing verified job` four times and exits 0 without running `present-sim`;
  - with the agent's four jobs, it exits 0 despite the misses.
  
  Record both.
- **Green:**
  - a battery run creates four new jobs under `artifacts/presentation_sim/<timestamp>/jobs/` (list them in the commit body) and exits **3**;
  - with `PRESENTATION_REUSE_JOBS` set to the agent's four jobs, the MISS lines match Issue 8's table;
  - the oracle lines are all PASS.
- **Falsify each direction:**
  - make the bars function always return MISS → (a) fails → exit 1;
  - make it always return PASS → (b) fails → exit 1;
  - make the mechanics check ignore `oracle.mp4` → (c) fails → exit 1.
- **Also falsify the creative check:** hard-code a creative run's `style_degraded: true` in a copy → exit 1.

**Blast radius:** `scripts/presentation_sim.sh`, the bars function (in `presentation/score.py` if it lives there), `scripts/battery.sh`, the report template, and §1.3 of this guide.

---

### I9 — Re-measure; close-out

**What this means for the user:** the fixes are proven on fresh output, and the follower bake-off (Wave J) starts from a sound pipeline.

1. **The full battery G1–G16, bare.** Expected: everything 0 except **G16 = 3**. Record the BAR table.
2. **The three cold budgets** (`measure_budget.sh`, `--long`, `--long --style creative`), each with 0 cache hits **and 0 asset execution errors**. **The creative one must be creative:** not degraded, with ≥ 2 metaphor images. It is the first valid creative budget, so record its spans against 110 / 85 / 195 s/min, and file any miss.
3. **The cold planner eval** on all 6 fixtures. `names_before_narration` must be 0, and the director must be valid on 6/6.
4. **Regenerate the G15 and G16 reports, and open and describe:**
   - each callback's dots;
   - an overlay scene carrying a token and an aside;
   - the overdue s001 scene;
   - the 7 former spoiler scenes;
   - a creative presentation metaphor node;
   - one illustrated presentation scene (images must now generate).
   
   Give your judgement on each, and say plainly when a creative item misfires.
5. **Update the docs:**
   - `ongoing_general_errors.md`: the Wave I lines, and §1 for Wave I;
   - `master_implementation_plan.md`: the Wave I paragraph already exists; mark it delivered;
   - the README, if commands changed.
6. **Update §1.3** (re-measured) and add Wave I to §5.1. **Do not stop:** continue with J1.

---

### J1 — `--matcher` plumbing, the frozen corpus, and the replay harness

**What this means for the user:** before any new follower is judged, the ruler is proven. The same 8 talks and the same scorer are used, and only the follower is swapped. Swapping in today's follower must change nothing.

**The gap:**
- **No choice of follower:** `present-sim` has `--tiebreak` (`cli.py:277`) but no `--matcher`, and `presentation/follow.py:37` always builds `LiveMatcher`.
- **No frozen corpus:** G16 rebuilds its jobs on every run.
- **No held-out set and no replay harness.**
- **Contract:** `design_presentation_simulation.md` §6.6 (§6.6.3 for this item), `design_data_contracts.md` §10, and `design_testing_and_validation.md` §2 (row "bake-off harness") and §4d.

**Implementation:**
1. **CLI and contracts.**
   - `present-sim --matcher bm25|anticipate|llm`, default `bm25`, validated where `--tiebreak` is (`cli.py:303`). Error, verbatim: `matcher must be one of bm25, anticipate, llm; got '<x>'`.
   - `--tiebreak llm` with any matcher other than `bm25` is an error: `--tiebreak applies only to --matcher bm25`.
   - Record the matcher in `ingest.json` (`matcher`); a presentation `ingest.json` without it loads as `bm25`.
   - `playback.json` gains `matcher` (G8).
   - `rerun --from follow` uses the job's recorded matcher.
2. **Dispatch.**
   - In `follow.py`, `bm25` runs today's `LiveMatcher` **unchanged**. Its `playback.json` must be byte-identical to today's on every corpus job, apart from the new `matcher` key.
   - `anticipate` and `llm` fail with `matcher '<m>' is not built yet` (exit 2) until J2 and J3 build them.
   - `logs/follow.log` adds `matcher=<m>`.
3. **The harness** `src/animated_infographics/evals/matcher_bakeoff.py`, exactly as §6.6.3:
   - it copies each job, then runs the stage functions themselves (not reimplementations): `anticipate` when needed, `follow`, `compose`, and `compute_presentation_score(..., oracle=False)`;
   - it writes `bakeoff.json` and the BAR lines;
   - it exits 0 only when all 8 jobs pass;
   - it offers the "perfect hearing" diagnostic (`--hearing perfect`).
4. **The corpus.** Only after I9 has closed Wave I, create the 8 jobs in `artifacts/matcher_bakeoff/<date>/corpus/`. For each §9 configuration and each seed in {7, 11}:
   ```
   uv run infographics present-sim <fixture> --style <s> --perturb <p> --seed <seed> --matcher bm25 --jobs-dir <corpus>
   uv run infographics score <job id> --jobs-dir <corpus>
   ```
   - **Check each job:**
     - 0 asset execution errors (I6);
     - creative jobs not degraded (I7);
     - `director.json` present on creative jobs.
   - **Freeze it.** Write `<corpus>/corpus.json` listing each job id, its configuration, and the SHA-256 of its `deck.json`, `tree.json`, `performance.json`, `speak_timing.json` and `heard.json`. The harness verifies these hashes before every run and exits 1 on any mismatch. **The corpus is never regenerated during Wave J.**
5. **The baseline.** Run the harness with `--matcher bm25` and write the first `docs/evals/matcher_bakeoff_<date>.md`, the "before": both sets' BAR tables and the "perfect hearing" column.

**Validation:**
- **Red first:** today, `present-sim … --matcher anticipate` fails with typer's `No such option: --matcher`. Record it.
- **Green:**
  - the "bake-off harness" unit row;
  - the `bm25` baseline reproduces every corpus job's own `presentation_score.json` within 0.01 on every metric, on all 8;
  - the corpus hashes are unchanged after a harness run;
  - `bm25` playbacks are byte-identical to today's (step 2).
- **Falsify the harness both ways** (§4d):
  - the test-only ground-truth matcher → PASS on every bar;
  - the shuffled `heard.json` → MISS.
- **Look:** compare the baseline's decision-set numbers with Issue 8's table.
  - **Literal jobs** should agree within 0.05.
  - **Creative jobs** may move, because I4 and I7 changed their trees (salvaged directors, overlays).
  
  Report both, and explain any literal move beyond 0.05.

**Blast radius:**
- `cli.py`;
- the ingest contract and `contracts/playback.py`, with generated schema and TS (G8);
- `presentation/follow.py`;
- `evals/matcher_bakeoff.py`;
- tests;
- the corpus (artifacts, not committed) and the report (committed).

---

### J2 — Contestant A1: the `anticipate` stage and the forward tracker; decide

**What this means for the user:** the follower learns, from the deck alone, how a presenter would actually *say* each point. It steps to the next point as soon as that point is being said, instead of eight seconds later.

**The gap:**
- **No anticipations:** node documents hold only deck text (`presentation/match.py:226`, `normalize_tokens(n.text)`).
- **The window** is the last 20 words (`match.py:361`).
- **Every move,** forward or not, needs 2 consecutive tops and a lead of 1.0 (`match.py:437–446`).
- **Contract:** `design_presentation_simulation.md` §6.6.1, verbatim, and §6.6.4 for the decision.

**Implementation:**
1. **The stage.** Add `presentation/anticipate.py`.
   - Register `anticipate` in `PRESENTATION_STAGES` right after `tree` (`jobs.py:34–47`), with inputs `deck.json` and `tree.json` and output `anticipation.json`, in the output and input maps (`jobs.py:66–72`, `:90–98`).
   - Add it to `rerun`'s presentation stages (`cli.py:654`).
   - Skip it unless the matcher is `anticipate`, logging `anticipate: skipped (matcher=<m>)` and writing nothing.
   - The prompts, schema, validators, error strings, temperature, `num_predict` and the failure rule are **verbatim from §6.6.1**, all through `run_with_retries`.
2. **The contract:** `contracts/anticipation.py` (`AnticipationPlan`), exported to the schema and TS (G8).
3. **The tracker.** Add a **new** class `AnticipateMatcher` in `match.py`; `LiveMatcher` is not edited.
   - `BM25Index` gains an optional `extra_text: dict[str, str] | None = None`, appended to each node's document. With `None` it must behave exactly as today; the J1 byte-identity check guards that.
   - Window, candidates, costs and commit rules exactly as §6.6.1, with holds and reasons like `LiveMatcher`'s, and compute time measured per decision.
4. **Dispatch:** `follow` with `anticipate` reads `anticipation.json` (missing → error `anticipation.json missing — run the anticipate stage`).
5. **Run the bake-off:** the harness with `--matcher anticipate` on the frozen corpus. The `anticipate` stage runs on the copies; jobs that share a deck share their anticipation calls through the LLM cache.
6. **Decide by §6.6.4,** and write the decision and the rule's wording into the report:
   - **A1 passes both sets → adopted.** J3 is not built; record "J3 not built: A1 adopted under Issue 8's rule". Go to J4.
   - **A1 passes the decision set but misses the held-out set → STOP.** File **Issue 9** with both tables, the "perfect hearing" column, and options for the user (e.g. adopt A1 anyway; build A2 as well; …). Wait for the selection.
   - **A1 misses the decision set →** go to J3.

**Validation:**
- **Red first:** the new A1 unit cases fail against the unbuilt code. The J1 baseline is the "before".
- **Green:**
  - the unit rows "anticipate stage" and "anticipate tracker A1";
  - isolation: `anticipate` reads only `deck.json` and `tree.json`, and `follow` reads `anticipation.json` only for this matcher;
  - causality;
  - a warm rerun of the harness gives a byte-identical `bakeoff.json`.
- **Falsify:** with the anticipated sentences left out of the documents (`extra_text=None`), decision-set point accuracy must fall below A1's. That proves the anticipations are what is being measured. Restore.
- **Look:**
  - open `anticipation.json` for one corpus job, and quote 3 nodes' sentences in the report: do they sound like speech, and do they add any fact the slide does not have?
  - open the strip chart of one decision-set job under `bm25` and under A1, and describe where A1 switches and where it still lags.
- **Report:** the full BAR tables (decision and held-out), "perfect hearing", and compute-time percentiles, in `docs/evals/matcher_bakeoff_<date>.md`.

**Blast radius:**
- `presentation/anticipate.py`, `contracts/anticipation.py` and generated files;
- `jobs.py`, `cli.py`;
- `presentation/match.py` (a new class, plus `BM25Index`'s optional argument), `presentation/follow.py`;
- tests, the report, and the Wave J line in `ongoing_general_errors.md` §3.

---

### J3 — Contestant A2: the LLM point classifier; decide

**Build only if J2 ended with "A1 misses the decision set".** If A1 was adopted, or J2 stopped to file, J3 is not started.

**What this means for the user:** if phrasing alone is not enough, the local model reads the last few seconds of speech and says which point the speaker is on.

**The gap:**
- **Nothing exists.** The tie-break (`match.py:391–428`) only arbitrates between two BM25 candidates, and only when they are within 1.0 of each other.
- **Latency on warm reruns:** a cache hit takes ≈ 0 ms (`planner/llm.py:192`), so a warm rerun would understate the latency.
- **Contract:** `design_presentation_simulation.md` §6.6.2, verbatim, and §6.6.4.

**Implementation:**
1. **The classifier.** Add a new class `ClassifierMatcher` in `match.py`. Prompt, candidates, schema enum, temperature 0, `num_predict` 32, no retries, the commit rules, and hold-with-`llm_error` on any exception or invalid answer: all verbatim from §6.6.2.
2. **Honest latency.**
   - `OllamaBackend` exposes the elapsed time of its last call, e.g. `last_elapsed_ms`. On a cache hit it is set to the `elapsed_ms` stored in the cache entry (written at `planner/llm.py:252–267`).
   - The matcher's compute time for a decision is that value, plus its own non-LLM time.
3. **Dispatch:** `follow` with `llm` builds an `OllamaBackend` honouring `--no-llm-cache`.
4. **Run the bake-off:** the harness with `--matcher llm`, cold for the first run (`INFOGRAPHICS_CACHE_DIR` set to a fresh dir), so the recorded call times are real.
5. **Decide by §6.6.4:**
   - **A2 passes both sets → adopted.** Go to J4.
   - **It passes the decision set but misses the held-out set → STOP and file Issue 9** (both tables), and wait.
   - **It misses the decision set → STOP and file Issue 9** with both contestants' tables, the best result per metric, "perfect hearing", and options for the user. Wait for the selection.

**Validation:**
- **Green:**
  - the unit row "LLM classifier A2", including causality through the stub's recorded prompts;
  - a warm rerun reproduces the cold run's commits **and latencies** exactly.
- **Report:**
  - the call time median and p90, and the sentence "live-viable: yes/no (p90 vs 1.5 s)";
  - the LLM calls per job and the total bake-off time.
- **Falsify:** replace the 25 heard words with an empty string in a scratch copy. Decision-set point accuracy must collapse, and ad-lib stability alone must not carry a PASS. Restore.
- **Look:** read 10 decisions sampled across a decision-set job (prompt, answer, ground truth). Describe the error patterns in the report.

**Blast radius:** `presentation/match.py` (a new class), `planner/llm.py` (the elapsed-time accessor), `presentation/follow.py`, tests and the report.

---

### J4 — Adopt, gate, close out

**What this means for the user:** the follower that met the bars becomes the one every presentation uses, and the presentation gate turns honestly green. Or, if neither met them, the user gets the evidence and the next decision.

1. **If a contestant was adopted** (J2 or J3):
   - Make it `present-sim`'s default (`cli.py`) and G16's. G16's falsifications use it too (`design_testing_and_validation.md` §4c).
   - Run G16 bare on fresh jobs: **exit 0**. Record the BAR table. If it is not 0, STOP and file it; never re-tune.
   - Update the docs:
     - `design_presentation_simulation.md` §6.6 gains a short **Result** paragraph (the adopted matcher, its numbers on both sets, its compute p90);
     - `design_future_live_and_video.md` §4 records the adopted matcher and its compute p90, for DF4;
     - `ongoing_general_errors.md`: Issue 8 moves to the resolved index;
     - the README documents `--matcher`.
2. **If none was adopted:** Issue 9 is filed. G16 stays at exit 3. Nothing becomes default.
3. **Full battery, bare** (G1–G16). Update §1.3.
4. **Rewrite this guide** to **Queue Complete** (or **Queue Complete — waiting on Issue 9**). **Then stop. Do not invent work.**


---

## 4. Deferred — do NOT start

- **Wave J before Wave I is closed.** The corpus must come from the fixed pipeline.
- **J3 (A2)** unless J2 ends with "A1 misses the decision set".
- **Issue 8's unselected options:** D (an embedding model; it would lift "no new models") and E (lowering the bars). Do not build them.
- **Using the adopted follower live** (DF4: microphone, streaming ASR, a real-time player) stays deferred. Wave J only records the compute time live use would need.
- **DF1–DF9** (`ongoing_general_errors.md` §4). The real-time parts of DF4 (live mode) stay deferred:
  - slide import (.pptx / PDF / Google Slides), per the user's "We do not need to build this out now";
  - a browser player on a requestAnimationFrame clock;
  - the microphone, streaming ASR and the webcam.
- **Known limitations, unscheduled:**
  - a quotation spanning two sentences can be split between beats;
  - the critic's `emotion_beat` *who* reading is noisy;
  - R7 treats reported speech without quotation marks as narration;
  - the spoiler rule treats a name token that is also a common word ("June") as naming.
- **Not in Wave I:**
  - motif *choice* quality (e.g. "the blue ink" drawn with a `Book` icon), which is judged in I9's report, not legislated;
  - new art styles, new cast-drawing methods, music changes.

---

## 5. Do NOT change

### 5.1 Already delivered

- Waves **A** (verified September 25), **B** (September 26), **C/D** (October 3), **E** and **F** (October 4), and **G** and **H** (October 6, 2026), all independently verified.
- One line per item, with verdicts: `ongoing_general_errors.md` §3. Nothing marked "✓" is reworked beyond what a Wave I item names.

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

**October 7, 2026:**
- **Issue 8 → Option A:** *"For issue 8, select Option A and write the agent execution guide to reflect that with validation"*.
- **Designer's validation, added under that instruction:** a held-out seed-11 set. If it disagrees with the decision set, that is filed for the user, not decided by you.

### 5.4 Invariants and intentional design decisions

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
  - **Removing "book" (or any word) from `TEXT_EXPECTED_WORDS`, or skipping rule 6 for metaphors,** to stop a degradation. A book in a FLUX image grows lettering that the skipped text check would never catch; salvage is the fix.

---

## 6. Where the contracts live

| What | Where |
|---|---|
| Styles, the director (rules 3, 5 and 7 revised), the license, overlays (anchors and geometry revised), creative bars | `design_styles.md` §3.3–3.7 |
| The presentation simulation, incl. creative in presentation jobs, `tree.json`'s `overlays` and `style_degraded`, and the R1 assertion | `design_presentation_simulation.md` §3, §6, §8 |
| `SceneOverlay` (anchor enum, kind rules), the job files | `design_data_contracts.md` §7, §10 |
| The name rule (item 6), R8 and the rule order | `design_planner.md` §4, §6 |
| `callback`'s dot count; templates; word caps | `design_templates.md` §2.18, §5 |
| Test rows (Wave I), G10 overlaps, step 10's new columns, G15 additions, G16's exit codes, the budget's asset rule | `design_testing_and_validation.md` §2–§5 |
| The follower bake-off: A1, A2, the corpus, the harness, the adoption rule | `design_presentation_simulation.md` §6.6; tests in `design_testing_and_validation.md` §2 and §4d |
| `ingest.json` → `matcher`, `anticipation.json`, `playback.json` → `matcher` | `design_data_contracts.md` §10 |
| Issue 8 (decided: Option A), the lessons (2.13–2.16), verdicts, deferred list | `ongoing_general_errors.md` |

---

## 7. Validation standard

- **Red first, on real inputs** (lesson 2.6). Every item names its recorded artefacts.
- **Measure outcomes before and after** (2.7).
- **Measure the rendered result** (2.8, 2.15).
- **Enforce rules on the final result** (2.10).
- **Measure distributions, not just validity** (2.11).
- **Name the defect class** (2.12).
- **A gate must be able to fail, must fail closed, and its exit code must state its bars** (2.13, 2.14). A falsification that passes on the real input proves nothing.
- **For creative output, judgement is part of validation:** open the stills, describe what each creative item adds, and say plainly when it misfires.
- **For the simulation, honesty is part of validation:** isolation and causality tests are gates, not niceties.
- **A decision made on measured numbers needs a held-out check.** Numbers you watched while building can be tuned to without meaning to (Wave J's seed-11 set).
- **Never loosen a bar to pass it.** File it with the measurement and options.

---

## 8. THE LOOP

```
(1) Is there an approved item? Wave I (I1–I9), then Wave J (J1–J4), in §2
    order. J3 only on its trigger. If all are done, STOP. Never start
    DF1–DF9 or anything not in §3. Never fill in a `Your selection:` line.
(2) Read the item and EVERY design section it names. Copy rules, thresholds
    and error strings VERBATIM.
(3) RED FIRST on the recorded artefacts the item names; record the failure.
(4) Build only what the item says. Nothing from §5.5.
(5) GREEN; then falsify (break, see red, restore, see green).
(6) Open every artefact and describe it, with your judgement for creative
    output.
(7) Full battery, bare. Update §1.3.
(8) ONE commit, scope = item id (`fix(i1): …`, `feat(j2): …`). WHY +
    red/green in the body. ONE line under "Wave I" or "Wave J" in
    ongoing_general_errors.md §3. Never amend after pushing.
(9) git push origin main.
(10) Next item. A failed bar or an impossible rule → file it and stop at
    that item until the user selects. In Wave J, §6.6.4 says exactly when
    a contestant's result means "continue" and when it means "stop and
    file".
```

---

## 9. Definition of Done: Waves I and J

**Wave I**

- [ ] I1–I9 each landed as one pushed commit scoped to its id, with red and green runs recorded.
- [ ] Callbacks show one dot per earlier rendered token (4 on both creative E2E stories); no renderer default remains.
- [ ] G10 measures overlaps on the rendered gallery: 0 `OVERLAP` lines, fail-closed, falsified with the old coordinates.
- [ ] No empty thought; motif names pass the story-words rule; motif spacing holds. The director ends in a valid or salvaged plan on 6/6 fixtures after `ollama stop`.
- [ ] 0 names before the narration in every final storyboard; the 7 former cases are described.
- [ ] 0 asset execution errors in every gate and budget run; presentation runs generate images.
- [ ] Creative presentation runs: license-checked, with overlays, not degraded (or filed).
- [ ] G16 builds four fresh jobs on every run and exits 3, with a BAR table. Falsifications (a)–(c) are each shown to bite.
- [ ] §1.3 re-measured bare (G1–G16, three budgets), with the creative budget a real creative run.
- [ ] §1.3 updated and Wave I added to §5.1; continue to Wave J.

**Wave J**
- [ ] J1: `--matcher` exists; `bm25` playbacks are byte-identical to before; the 8-job corpus is frozen with hashes; the harness reproduces each job's `bm25` score within 0.01 and is falsified both ways; the baseline report is written.
- [ ] J2: the `anticipate` stage and `AnticipateMatcher` match §6.6.1 verbatim, with isolation, causality and determinism tested. The bake-off tables cover both sets. The decision is written out with the rule.
- [ ] J3: built only on its trigger. `ClassifierMatcher` matches §6.6.2 verbatim, and latency stays honest on warm reruns. Tables and the decision are written out.
- [ ] J4: the adopted matcher is the default, and G16 on fresh jobs exits **0**. Or Issue 9 is filed and G16 stays at 3.
- [ ] §1.3 re-measured bare (G1–G16).
- [ ] This guide rewritten to **Queue Complete** (or **Queue Complete — waiting on Issue 9**). **Then stop. Do not invent work.**

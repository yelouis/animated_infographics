# Agent Execution Guide — Waves A–H Delivered (Queue Complete) — October 6, 2026

**You are an engineering agent with no memory of this project.** Waves A–H are built, committed, pushed (head `main`), and independently verified across all 16 battery gates (§1).

**The user's words (October 5, 2026):**
- *"the generated animations are very literal to what is being said at any given moment. Lets set up something like a style library. We can keep this as one of the styles but lets have a style that is a bit more creative where the animation adds something to the story (also pick more interesting stories that maybe is longer)."*
- *"…create a couple of slides from the transcript (key moments) and use that as the power point, then you can create the tree of animations that links each slide together. Then perform some flair on the original transcript … and see what video generates from it. Then we can still run similar analysis that analyzes if the final outputted video was done well."*

**The user's selections:**
- creative ingredients: **all four** (motifs & callbacks, visual metaphors, foreshadowing & reveals, visual gags & asides);
- license: **"Small embellishments"**;
- test stories: **4–6 minutes**;
- slide import (.pptx / Google Slides): **not now**.

**Status:** Wave G (G1–G6) and Wave H (H1–H6) are delivered and verified. **Queue Complete.**

**Every number and literal string in this guide and the design docs is a decision, not a suggestion.**

**The product, in one paragraph.** A local-only CLI that turns a text story (narrated by local TTS) or an audio narration into a 1080×1920 animated explainer video, with karaoke captions, a persistent avatar cast, checked illustrations, a blind critic, and a mandatory review gate. Wave G adds a **creative** style beside today's **literal** one. Wave H adds an offline **presentation simulation**: a deck, an animation tree, a "performed" talk, a causal matcher and a score. It is the first step toward live presentations.

**The lessons that shape these waves:**
- Red first on real inputs (2.6).
- Enforce rules on the final result (2.10).
- Measure the distribution of what the model picks (2.11).
- Name the defect class (2.12).
- And for Wave H above all: **the simulation must be honest.** The tree never sees the transcript; the matcher never sees the ground truth. Tests enforce both.

---

## 0. Standing constraints (apply to every item)

1. **The battery is the regression bar.** After every item, run the full battery (G1–G14, plus G15/G16 once they exist) bare, and update §1.3. Read every exit code bare.
2. **Fully local at runtime.** No cloud API, no network except loopback. Pull no new models: `gemma4:26b`, Kokoro, mlx-whisper and FLUX.2 klein 4B only.
3. **Python (Pydantic) is the source of truth for every contract.** Generated files are never hand-edited, and G8 covers every new contract.
4. **Templates read time only through the clock.**
5. **The review gate is mandatory** for video and presentation jobs alike. No auto-approve.
6. **The planner never crashes the pipeline.** Every LLM call goes through `run_with_retries`. LLM-facing schemas carry no length constraints; validators enforce limits with retry messages. Every new on-screen string passes the word caps and the placeholder, id and completeness rules.
7. **Red first, on real inputs.** Before building, run the item's falsifying check against the current code, using real fixture output, and record the failure.
8. **One item = one Conventional Commit, scope = item id** (`feat(g1): …`, `feat(h1): …`). WHY plus red and green runs in the body. Push after every item. Never amend a pushed commit.
9. **Record each resolution in the same commit,** as one line under "Wave G" or "Wave H" in `ongoing_general_errors.md` §3: `G<n> — <title> — git log --grep "(g<n>)" — <measured result>`.
10. **When this guide and a design doc disagree, stop and file it.**
11. Every stage log ends in `llm_calls=<n> cache_hits=<m> elapsed_ms=<t>`.
12. **Nothing in the package changes the environment at import.** Export `HF_HOME=$HOME/.cache/huggingface` in your shell if needed.
13. **Ids:** waves A–H; deferred features DF1–DF9; live constraints LC1–LC6.
14. **Eval reports are named by date.** If you run the E2E or the budget twice on one day, the second run overwrites the first; commit each report in the item that produced it.

---

## 1. Verified baseline (October 6, 2026, close-out of Waves G and H)

### 1.1 Environment

`doctor`: 22 checks OK.
- M4 Max 64 GB; ffmpeg 8.1; Node v26.5.0; Python 3.12 (uv).
- Ollama with `gemma4:26b`; Kokoro 0.9.4; mlx-whisper 0.4.3.
- mflux (`flux2-klein-4b`); Remotion 4.0.528.

### 1.2 Repository

- Waves A–F: `4df212a` … `c88a69f`. Per-item verdicts: `ongoing_general_errors.md` §3.
- Wave G: `afb1b5f` … `e5d590e`. Per-item verdicts: `ongoing_general_errors.md` §3.
- Wave H: `0893fc1` … `main`. Per-item verdicts: `ongoing_general_errors.md` §3.

### 1.3 Gates (run bare October 6, 2026; the regression bar)

| # | Gate | Result |
|---|---|---|
| G1–G3 | ruff / format / mypy | exit 0 (156 files formatted; 81 source files) |
| G4 | `uv run pytest -q -m "not slow"` | exit 0 · **350 passed** |
| G5–G7 | renderer typecheck / lint / vitest | exit 0 · 19 vitest |
| G8 | schema sync | exit 0 · in sync |
| G9 | renderer purity | exit 0 · pure |
| G10 | gallery | exit 0 · 59 goldens, 0 overflows |
| G11 | `uv run pytest -q -m slow` | exit 0 · **43 passed** |
| G12 | `./scripts/e2e.sh` | exit 0 · steps 1–10 passed |
| G13 | offline | exit 0 · passed |
| G14 | doctor | exit 0 · 22 OK |
| G15 | `./scripts/creative_e2e.sh` | exit 0 · steps 1–5 passed |
| G16 | `./scripts/presentation_sim.sh` | exit 0 · 4 simulation runs, 4 oracle baselines, falsification passed |
| Budget | `story_recipe_box`, cold | 205.8 s / 191.3 s / 397.1 s (≤ 390 / 210 / 600), 0 cache hits |
| Budget (long) | `story_overdue_book`, literal cold | 56.87 s/min / 79.80 s/min / 136.67 s/min (≤ 90 / 80 / 170 s/min), 0 cache hits |
| Budget (long creative) | `story_overdue_book`, creative cold | 59.62 s/min / 80.83 s/min / 140.45 s/min (≤ 110 / 85 / 195 s/min), 0 cache hits |

### 1.4 Measurements that shaped Waves G and H (October 5, 2026)

| What | Result |
|---|---|
| `story_overdue_book` (first version), `new` cold, literal | **349 s** to `awaiting_review`; narration **329.7 s** (5.5 min), 755 words, **64 beats**. Stage timings: voice 31.9 s, narrate 26.2 s, bible 10.3 s, segment 3.6 s, storyboard 140.6 s, assets 114.1 s, preview 19.2 s. That is 63 s per narration minute, against `story_recipe_box`'s 79 s/min. |
| `history_great_stink`, `new` cold, literal | **331 s** to `awaiting_review` (65 s per narration minute); narration **303.6 s** (5.1 min), **60 beats**; voice `am_michael` / `third_person`; cast John Snow, Joseph Bazalgette, Members of Parliament, Londoners; places London (gazetteer), River Thames (llm), Soho (gazetteer). Its expected facts hold so far |
| Voice stage on that first version | `am_michael` / `no_evidence`: "As the only librarian in Alder Creek, Oregon, and a grandmother of three, I" fails Form B, an accepted false negative (`design_planner.md` §10). The opening was rewritten to "As a grandmother of three, I…". **G1 confirms `af_heart` / `llm`.** |
| Bible of that run | cast: Me (narrator), June Lind, Robert Okafor, Marisol. Places: Alder Creek (llm geo), Portland (gazetteer). Set pieces: The Long Way Home, The Late Fee Stack, The Reading Nook. |
| Everything else in these waves | **Not measured by the designer** (no code was written, per the user). Each item states the measurement you run first, and the bar it must meet. |

---

## 2. Execution order

| # | Item | Why this position |
|---|---|---|
| G1 | New fixtures wired in; literal measured on long stories | Every later item measures on these stories. The literal numbers are the "before" for creative |
| G2 | Style contract; `--style`; literal byte-identity | Every creative change branches on it. The identity baseline must be frozen **before** anything changes |
| G3 | Director + license stages | They produce the plan that G4 and G5 render |
| G4 | Renderer: `metaphor`, `callback`, `OverlayLayer`, gallery | G5 needs the templates and the overlay contract |
| G5 | Integration: R8, deterministic scenes, metaphor images, overlays in compile, report | Joins G3's plan and G4's renderer |
| G6 | Creative E2E (G15), creative long budget, Wave G close-out | Measures the finished Wave G before Wave H depends on it |
| H1 | `present-sim` job kind + `deck` stage | The deck is the only input of everything after it |
| H2 | `deck_bible` + `tree` + `section_title` + presentation profile + isolation | Needs H1's deck; G2's styles |
| H3 | `perform` + `speak` + `hear` | Needs the deck's ground truth; independent of H2's tree |
| H4 | `follow` + `compose` | Needs H2's tree and H3's heard words |
| H5 | `score` + oracle + `presentation_sim.sh` (G16) + report | Needs H4's playback and the render |
| H6 | Re-measure everything; close-out | Measures the finished system |

---

## 3. The items

### G1 — New fixtures wired in; literal measured on long stories

**What this means for the user:** two longer, more interesting stories become part of every evaluation, and we know what today's literal style does with them.

**The gap:**
- The two new scripts exist, but nothing knows them:
  - no `fixtures/CHECKSUMS` lines;
  - no `fixtures/expected/*.json`;
  - not in the planner eval (`evals/planner.py`, four fixtures);
  - no long-story budget mode.

**Implementation:**
1. Add both scripts to `fixtures/CHECKSUMS`. Verify that the SHA-256s equal `design_testing_and_validation.md` §1.
2. Write `fixtures/expected/story_overdue_book.json` and `history_great_stink.json` with the expected facts of §1 there.
3. Add both fixtures to `evals/planner.py`, with the same bars as the stories (distinct templates ≥ 7).
4. `scripts/measure_budget.sh --long`: the same procedure on `story_overdue_book`, reporting each span as seconds **per narration minute** (narration duration from `transcript.json`) against the literal row of the long-story budget.

**Validate:**
- **Red first:** the planner eval runs only 4 fixtures; `CHECKSUMS` verification ignores the new scripts.
- **Voice:** the eval's voice check on `story_overdue_book` must give `af_heart` / `llm`, evidence containing "grandmother". If it does not, **file it; do not edit the story.**
- **Cold planner eval** on all 6 fixtures (`docs/evals/planner_<date>.md`): every §9 bar on the new fixtures too. Record each new fixture's light share, graphic words per narration word, R6/R7 counts, and critic outcomes.
- **Long budget, literal,** cold → `docs/evals/budget_<date>.md`: ≤ 90 / 80 / 170 s per narration minute.
- **Open and describe:** `story_overdue_book`'s literal contact sheet. Name three beats where the literal style restates the narration; these are the "before" for G6.

**Blast radius:** `fixtures/CHECKSUMS`, `fixtures/expected/`, `evals/planner.py`, `scripts/measure_budget.sh`, `design_testing_and_validation.md` (only if a measured number must be recorded there).

---

### G2 — Style contract; `--style`; literal byte-identity

**What this means for the user:** they can choose a style per video, and choosing `literal` gives exactly the videos they have today.

**The gap:** there is no style concept. `new` has no `--style`; `ingest.json` has no `style`.

**Implementation:**
1. **Before any other change,** freeze the literal baseline. Run `new fixtures/scripts/molasses_flood.txt` with a warm cache and record the SHA-256 of `bible.json`, `beats.json`, `storyboard.json`, `plan_report.json` and `timeline.json` in `tests/data/literal_baseline/molasses_flood.sha256`. Commit it in this item.
2. Add `contracts/styles.py`: `StyleSpec` and `STYLES = {literal, creative}` exactly as in `design_styles.md` §1–3. Export them (G8).
3. Add `--style` to `new` and `rerun`. Record `style` in `ingest.json`, where a missing key loads as `literal`. Record `style` and `style_degraded` in `plan_report.json`.
4. Insert the `director` stage into the stage list. For `literal` it is recorded as skipped and writes nothing. `rerun --from director` is valid.

**Validate:**
- The "styles" row in `design_testing_and_validation.md` §2.
- **The falsifying assertion:** literal byte-identity against `tests/data/literal_baseline/`.
- **Falsify:** let `literal` write an empty `director.json` → `plan_report.json` or the stage list changes → red.

**Blast radius:** `contracts/styles.py` (new), `contracts/export.py` outputs, `cli.py`, `ingest.py`, `jobs.py`, the stage runner, `planner/props.py` (`plan_report` fields), tests, `tests/data/literal_baseline/`.

---

### G3 — Director + license stages

**What this means for the user:** a creative video starts from a plan for the whole story: what recurs, what gets a metaphor, what is planted early and what pays off, where a small gag goes. Nothing in the plan invents events, dialogue or facts.

**The gap:** nothing plans across a whole story. Every scene is chosen beat by beat (`planner/select.py`, `planner/props.py`).

**Implementation:**
1. **`planner/director.py`** and **`prompts/director.md`**, per `design_styles.md` §3.3. The prompt must contain:
   - the four ingredients with the one-line definitions of §3.1;
   - the counts formula, with the computed numbers filled in;
   - the license table of §3.2 **verbatim**;
   - the rule that plants show only the object, never its meaning;
   - the beat list as `[i] text`, the compact bible and the icon block;
   - "JSON only".
2. **Validators 1–7 of §3.3,** with retry messages in the style of `design_planner.md` §6. For example: `motifs[0].appearances: the payoff (beat 12) must come at least 3 beats after every plant (beat 10)`.
3. **The license check of §3.4,** with the question text verbatim. Removals go into `license_dropped`, and a failed call removes the item.
4. **Degradation:** if the director fails every attempt, the job runs as literal with `style_degraded: true` and a `report.json` warning.
5. **Review:** `director.json` is human-editable and re-validated by `preview`, like `storyboard.json`. `preview/storyboard.md` lists the plan at the top: motifs with their appearances, metaphors, asides.

**Validate:**
- The "director" and "license check" rows of `design_testing_and_validation.md` §2 (stub backend).
- **Red first:** none of these modules exist; record that the tests fail on import.
- **Live measurement** (`tests/slow/test_director_live.py` plus a report section in `docs/evals/planner_<date>.md`): run the director cold on **all six** fixtures, then the license check. Report per fixture:
  - attempts used;
  - each item;
  - each license verdict;
  - and, for every metaphor and aside, one sentence of your own judgement: does it add something, and does it respect the license?
- **Bars:**
  - a valid plan within 3 attempts on **6 of 6** fixtures;
  - ≥ 1 motif with a plant and a payoff on each of `story_overdue_book`, `history_great_stink`, `story_recipe_box` and `story_room_12`;
  - license drops are reported, with no bar.
- If any bar fails, file it with the outputs.
- **Falsify:** remove validator 3 (plant before payoff) → the stub case with a payoff before its plant passes → red.

**Blast radius:** `planner/director.py` (new), `planner/license.py` (new), `prompts/director.md` (new), `contracts/` (director models), `preview.py`, tests.

---

### G4 — Renderer: `metaphor`, `callback`, `OverlayLayer`, gallery

**What this means for the user:** the creative style has pictures to draw with: a metaphor scene, a payoff scene that visibly calls back, and small tokens and gags on top of ordinary scenes.

**The gap:** the renderer has 16 templates and no overlay layer.

**Implementation:**
1. **Contracts:**
   - add `metaphor` and `callback` to the registry and props models exactly as in `design_templates.md` §2.17–2.18, including WORD_CAPS (`label` 3) and the template classes (picture);
   - add `overlays` to the timeline scene contract (`design_data_contracts.md` §7), defaulting to `[]` and **serialised only when non-empty**, so literal timelines stay byte-identical.
2. **Templates:** `renderer/src/templates/metaphor.tsx` and `callback.tsx`.
3. **Overlays:** `renderer/src/story/OverlayLayer.tsx`, per `design_styles.md` §3.6.
4. **Gallery:**
   - `min`/`typical`/`max` fixtures for both templates;
   - `overlays__<template>` fixtures for each of the 10 allowed templates;
   - goldens re-cut for new fixtures only.
5. **Overlap test:** a vitest case asserts that every overlay rectangle is disjoint from every text-slot rectangle of that template at its `max` layout. Use the layout constants; do not hard-code numbers twice.

**Validate:**
- G5, G8 and G10 green, with 0 overflows.
- The overlap test passes.
- Literal byte-identity (G2) still holds.
- **Falsify:** move the motif token to (540, 240) → the overlap test fails against `kinetic_quote`'s or `character_intro`'s slots.
- Open and describe `metaphor__typical`, `callback__typical` (the "seen before" dots) and `overlays__location`.

**Blast radius:** `contracts/templates.py`, `contracts/models.py`, generated schema/TS, `renderer/src/templates/`, `renderer/src/story/`, gallery fixtures and goldens, vitest.

---

### G5 — Integration: R8, deterministic scenes, metaphor images, overlays

**What this means for the user:** the plan actually reaches the screen. A metaphor beat shows the metaphor, a payoff shows a callback, and the plants and gags appear where they were planned.

**The gap:** nothing consumes `director.json`.

**Implementation:**
1. **`select.py`:** rule R8 per `design_planner.md` §4 (order R1, R8, R6, R2, R4, R5, R7). R2 never rewrites an R8 scene.
2. **`props.py`:** build `metaphor` and `callback` scenes deterministically with `rationale: "director"`, no LLM and no critic. A failing scene falls back through the ladder to its alternate.
3. **`assets.py`:** generate metaphor illustrations like set pieces. The cache key includes the metaphor id and image text; the text check runs with its retries. A failed image leaves the template's no-image fallback in place, and is recorded.
4. **`compile.py`:**
   - write overlays per `design_styles.md` §3.5, including the moves and drops, recorded under `overlay_dropped`;
   - overlay text counts toward graphic words (`planner/words.py`; update `graphic_words` and E2E step 9 accordingly).
5. **`preview`:** contact-sheet tiles show their overlays. Tiles of metaphor and callback scenes carry a small "M" / "C" badge.
6. **`report.json`:** every director item with its fate (rendered, moved, `license_dropped`, `overlay_dropped`).

**Validate:**
- The "R8 and overlays" row of `design_testing_and_validation.md` §2.
- **Red first:** a creative job today renders no metaphor.
- An end-to-end creative run on `story_overdue_book` reaches `awaiting_review`. Open its contact sheet and describe every metaphor, callback, token and aside, and whether each respects the license.
- **Falsify:** skip R8 → 0 metaphor scenes → the G6 bar would fail; record the count.

**Blast radius:** `planner/select.py`, `planner/props.py`, `assets/`, `compile.py`, `planner/words.py`, `evals/word_density.py`, `preview.py`, `report.json` writer, tests.

---

### G6 — Creative E2E (G15), creative long budget, Wave G close-out

**What this means for the user:** measured proof that the creative videos add something, stay within the license, keep the word budget, and finish in reasonable time.

**Implementation:**
1. Write `scripts/creative_e2e.sh` per `design_testing_and_validation.md` §4b, and add it to the battery as G15.
2. Run `scripts/measure_budget.sh --long --style creative`, cold.
3. Write `docs/evals/creative_<date>.md`, containing:
   - the per-item fates;
   - the stills, side by side with the literal control at the same beat;
   - for each story, a short paragraph: what the creative version adds that the literal one does not, and anything that misfires.

**Validate:**
- **G15 green,** meaning all of these hold on both creative jobs:
  - every motif planted before its rendered payoff;
  - ≥ 2 metaphors and ≥ 2 asides;
  - 0 license failures left and 0 overlay overlaps;
  - step 9 density and step 10 criteria.
- **Long creative budget:** ≤ 110 / 85 / 195 s per narration minute.
- **Falsify:** stub the director to return no motifs → G15 red.

**Close-out of Wave G (not of this guide):**
1. Full battery, bare; update §1.3.
2. Move Wave G to §5.1.
3. Update `ongoing_general_errors.md` §1.
4. **Continue with H1.**

**Blast radius:** `scripts/creative_e2e.sh` (new), `scripts/battery.sh`, `scripts/measure_budget.sh`, `docs/evals/`.

---

### H1 — `present-sim` job kind + `deck` stage

**What this means for the user:** a story becomes a "PowerPoint" of key moments: the input every live presentation will start from.

**The gap:** there is no presentation job kind, no `present-sim` command and no deck.

**Implementation:**
1. Add `state.json.kind` (`"video"` | `"presentation"`, default `"video"`) and the presentation stage list (`design_system_architecture.md` §4).
2. Add the `present-sim` CLI per §6 there, recording `perturb`, `seed` and `tiebreak` in `ingest.json`.
3. Add the `deck` stage per `design_presentation_simulation.md` §2: prompt `prompts/deck.md`, validators 1–6, and `deck.json`.
4. **Review:** the contact sheet's first page lists the slides and points. `deck.json` is human-editable and re-validated by `preview`.

**Validate:**
- The "deck" row in `design_testing_and_validation.md` §2.
- **Red first:** `present-sim` does not exist.
- **Live:** decks for `history_great_stink` and `story_overdue_book`. The slide counts must be `round(words / 100)`, clamped: 7 and 8. Open and describe both decks. Are the slides the story's key moments? Would a presenter recognise them as a deck?
- **Falsify:** let the partition skip one sentence → validator 4 rejects it.

**Blast radius:** `cli.py`, `jobs.py`, `contracts/` (deck models), `presentation/deck.py` (new), `prompts/deck.md` (new), `preview.py`, tests.

---

### H2 — `deck_bible` + `tree` + `section_title` + presentation profile + isolation

**What this means for the user:** every slide gets its animations planned before the talk, with a repeated section graphic, and links between them for going forward, skipping and going back.

**The gap:** nothing plans from a deck.

**Implementation:**
1. **`deck_bible`:** run the existing bible stage on the deck text only (titles and points as paragraphs), writing `deck_bible.json`.
2. **Template:** `section_title` per `design_templates.md` §2.19 (contract, renderer, gallery fixtures).
3. **Presentation profile:** R2, R6 and R7 off; everything else on. The style applies; creative runs the director over the point list.
4. **`tree`** per `design_presentation_simulation.md` §3:
   - section nodes are deterministic;
   - point nodes are planned with each point as a beat, using a synthetic one-beat-per-point transcript built from the deck for grounding;
   - edges use the costs of the table there;
   - `tree.json` is written, and `assets` runs over its scenes.
5. **Isolation** per `design_data_contracts.md` §10: patch file access during `tree` and fail on any read outside `deck.json`, `deck_bible.json` and the style.

**Validate:**
- The "tree isolation" row.
- **Red first:** no `tree` stage.
- **Live:** trees for both fixtures. Open the contact sheet of each tree's node scenes and describe them. Count templates per node kind, and confirm the section graphic appears once per slide.
- **Falsify:** let `tree` read the script → the isolation test fails.

**Blast radius:** `presentation/tree.py` (new), `planner/select.py` (profile switch), `contracts/` (tree, `section_title`), renderer template and gallery, tests.

---

### H3 — `perform` + `speak` + `hear`

**What this means for the user:** a realistic "presenter" who paraphrases, says "um", skips things, goes off on tangents and refers back, plus the exact ground truth of what they meant at every moment.

**The gap:** nothing perturbs a script, and nothing simulates live ASR.

**Implementation:**
1. **`perform`** per `design_presentation_simulation.md` §4:
   - the operation table with its rates;
   - seeded RNG (`random.Random(seed)`, one stream per operation, so adding an operation does not shift the others);
   - paraphrase, ad-lib and back-reference prompts (`prompts/perform_*.md`): paraphrase keeps numbers, names and quotes;
   - labels and validators;
   - `performance.json` and the `op_counts`.
2. **`speak`:** Kokoro with the job's voice → narration plus `speak_timing.json`, from sentence offsets.
3. **`hear`:** mlx-whisper on that audio → `heard.json` (the transcript contract, `source: "asr"`).

**Validate:**
- The "perform" row (stub backend).
- **Red first:** no module.
- **Live, on `history_great_stink` with `--perturb strong --seed 7`:** list every operation applied. Read the performed text aloud in your head; does it sound like a person presenting? Quote three examples. Report the ASR word error rate against the performed text (normalised as in the Whisper WER test); no bar, recorded.
- **Determinism:** the same seed reproduces a byte-identical `performance.json`, with the LLM cache warm.
- **Falsify:** let the paraphrase drop a number → the validator falls back to verbatim. Test it.

**Blast radius:** `presentation/perform.py` (new), prompts, `audio/` reuse, `contracts/`, tests.

---

### H4 — `follow` + `compose`

**What this means for the user:** the animation follows the talk as it is heard, the way it would live: forward, skipping and returning, holding through tangents.

**The gap:** nothing follows speech through a tree.

**Implementation:**
1. **`presentation/match.py`** per `design_presentation_simulation.md` §6:
   - streaming decision points (gap ≥ 300 ms, or 1.5 s), a 20-word window;
   - normalisation with the committed stopword list and stemming;
   - BM25 (k1 1.2, b 0.75) with document frequencies over the tree's node texts, plus edge costs;
   - commit rules: 2 consecutive tops, margin ≥ 1.0, dwell ≥ 2.0 s;
   - the first section node is shown from 0;
   - latency = decision time + measured compute time;
   - optional `--tiebreak llm`, off by default.
2. **`compose`** per §7:
   - timeline from playback, no `LEAD_MS`;
   - narration audio;
   - captions from ASR words with a 300 ms lag;
   - short scenes merged.

**Validate:**
- The "follow" row (causality, hysteresis, dwell, edges, IDF source, latency).
- **Red first:** no module.
- **Live:** run `follow` on H3's strong `history_great_stink` performance. Print the commit list beside the ground-truth points; describe every wrong commit and its cause.
- **Falsify:** remove the hysteresis → one strong window commits → red.

**Blast radius:** `presentation/match.py` (new), `presentation/compose.py` (new), `contracts/` (playback), tests.

---

### H5 — `score` + oracle + `presentation_sim.sh` (G16) + report

**What this means for the user:** a number, and a picture, for how well the video followed the talk, compared with a perfect follower.

**The gap:** nothing scores a presentation video.

**Implementation:**
1. **`presentation/score.py`** per `design_presentation_simulation.md` §8:
   - every metric, exactly as defined;
   - the strip chart PNG, drawn with Pillow (already a dependency; add no new library);
   - `--oracle` composes from ground truth and renders `oracle.mp4`.
2. **`scripts/presentation_sim.sh`** per `design_testing_and_validation.md` §4c, added to the battery as G16. It covers the four runs of §9 and writes `docs/evals/presentation_<date>.md`.
3. **The tie-break measurement** (§6.4): run all four with `--tiebreak llm` too, and apply the stated rule for making it default. Record the numbers and the decision.

**Validate:**
- The "score" row (synthetic playbacks).
- **G16:** every §8 bar on every run. **A failing bar is filed with the measurement and options; it is never tuned.**
- Open and describe each strip chart and the two `present-sim` videos with the worst score.
- **Falsify:** a shuffled `heard.json` → the accuracy bars fail → G16 red.

**Blast radius:** `presentation/score.py` (new), `scripts/presentation_sim.sh` (new), `scripts/battery.sh`, `docs/evals/`.

---

### H6 — Re-measure; close-out — COMPLETED

**Delivered and verified October 6, 2026:**
1. Full battery G1–G16 passed bare (all 16 gates exit 0; 350 fast tests, 43 slow tests, 19 vitest, 59 goldens with 0 overflows, G12 E2E, G13 offline, G14 doctor, G15 creative E2E, G16 presentation simulation).
2. Cold planner eval on 6 fixtures recorded in `docs/evals/planner_2026-10-06.md`.
3. Performance budgets measured and verified cold: `story_recipe_box` (primary, 397.1s <= 600s), long literal (`story_overdue_book`, 136.67 s/min <= 170 s/min), and long creative (`story_overdue_book`, 140.45 s/min <= 195 s/min).
4. G15 (`docs/evals/creative_2026-10-06.md`) and G16 (`docs/evals/presentation_2026-10-06.md`) reports generated and verified.
5. README updated with `--style`, `present-sim`, and `score` documentation and scope boundaries.
6. Execution guide updated to Queue Complete; §1.3 baseline updated; §5.1 includes Waves G and H.

---

## 4. Deferred — do NOT start

- **DF1–DF9** (`ongoing_general_errors.md` §4). DF4 (live mode) is the destination of Wave H, but its real-time parts are **not** in these waves:
  - slide import (.pptx / PDF / Google Slides), per the user's "We do not need to build this out now";
  - a browser player on a requestAnimationFrame clock;
  - the microphone, streaming ASR and the webcam.
- **Known limitations, unscheduled:**
  - a quotation spanning two sentences can be split between beats;
  - the critic's `emotion_beat` *who* reading is noisy;
  - R7 treats reported speech without quotation marks as narration.
- **Not in Wave G:** new art styles (`design_visual_direction.md` §7's `STYLE` string is unchanged), new cast-drawing methods, music changes.

---

## 5. Do NOT change

### 5.1 Already delivered

- Waves **A** (verified September 25), **B** (September 26), **C/D** (October 3), **E** and **F** (October 4, 2026), and **G** and **H** (October 6, 2026), all independently verified.
- One line per item, with verdicts: `ongoing_general_errors.md` §3. Nothing marked "✓" is reworked.

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
- `num_predict=2048` in deck stage (`design_presentation_simulation.md` §2 suggested 1536, but 8–10 slides with indentation and sentence lists require ~1520–1600 tokens).

### 5.3 User decisions

**September 23, 2026:**
- Offline first; a template library.
- History + Reddit-style stories; text + audio inputs.
- Mixed imagery; Python + TypeScript/Remotion; fully local.
- 9:16; karaoke captions; flat editorial vector; 1–3 min videos in about 10 min. *For the long fixtures, the budget is restated per minute, as the user's 4–6-minute choice stated.*
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

### 5.4 Invariants and intentional design decisions

**New (October 5, 2026):**
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
- **New, October 5, 2026:**
  - **Slide import in these waves**, per the user.
  - **A real-time player in these waves.**
  - **Letting the tree or the matcher see the script, the performance or the ground truth.** It makes the simulation meaningless.
  - **Embeddings or a new model for matching.** No new models; BM25 plus edge costs first; the LLM tie-break only by its measured rule.
  - **Creative embellishments beyond the license:** new events, dialogue, facts, contradictions, or plants that reveal the twist.
  - **Raising word caps for creative scenes.**
  - **A creative style that changes the cast's look or the illustration `STYLE`.**

---

## 6. Where the contracts live

| What | Where |
|---|---|
| Styles, the director, the license, overlays, creative bars | `design_styles.md` |
| The presentation simulation: deck, tree, perform/speak/hear, follow, compose, score, fixtures | `design_presentation_simulation.md` |
| Pipeline stages (incl. `director`, presentation jobs), CLI (`--style`, `present-sim`, `score`) | `design_system_architecture.md` |
| New job files (`director.json`, `deck.json`, `tree.json`, `performance.json`, `speak_timing.json`, `heard.json`, `playback.json`, `presentation_score.json`), `overlays`, `kind`, `style` | `design_data_contracts.md` §7, §10 |
| R8 and the rule order; the presentation profile; style-dependent stages | `design_planner.md` §4, §8b |
| Templates incl. `metaphor`, `callback`, `section_title`; word caps and classes | `design_templates.md` §2.17–2.19, §5 |
| Fixtures incl. the two new stories; test rows; G15/G16; the long-story budget | `design_testing_and_validation.md` |
| The live-mode path (prepared mode) and what stays deferred | `design_future_live_and_video.md` §4 |
| Decisions, lessons, the resolved index, the deferred list | `ongoing_general_errors.md` |

---

## 7. Validation standard

- **Red first, on real inputs** (lesson 2.6).
- **Measure outcomes before and after** (2.7).
- **Measure the rendered result** (2.8).
- **Enforce rules on the final result** (2.10).
- **Measure distributions, not just validity** (2.11).
- **Name the defect class** (2.12).
- **For creative output, judgement is part of validation:** open the stills, describe what each creative item adds, and say plainly when it misfires.
- **For the simulation, honesty is part of validation:** isolation and causality tests are gates, not niceties.
- A gate must be able to fail, and must fail closed. Read exit codes bare. Open every artefact.
- **Never loosen a bar to pass it.** File it with the measurement and options.

---

## 8. THE LOOP

```
(1) Is there an approved item? Wave G (G1–G6), then Wave H (H1–H6), in §2
    order. If all are done, STOP. Never start DF1–DF9 or anything not in §3.
    Never fill in a `Your selection:` line.
(2) Read the item and EVERY design section it names. Copy prompts, rules,
    thresholds and error strings VERBATIM.
(3) RED FIRST on real fixture output; record the failure.
(4) Build only what the item says. Nothing from §5.5.
(5) GREEN; then falsify (break, see red, restore, see green).
(6) Open every artefact and describe it, with your judgement for creative
    output.
(7) Full battery, bare. Update §1.3.
(8) ONE commit, scope = item id (`feat(g1): …`). WHY + red/green in the
    body. ONE line under "Wave G"/"Wave H" in ongoing_general_errors.md §3.
    Never amend after pushing.
(9) git push origin main.
(10) Next item. A failed bar → file it and stop at that item until the user
    selects.
```

---

## 9. Definition of Done: Waves G and H

**Wave G**
- [x] G1–G6 each landed as one pushed commit scoped to its id, with red and green runs recorded.
- [x] Six fixtures in the planner eval, all bars met; `story_overdue_book` voice = `af_heart` / `llm` (or filed).
- [x] Literal byte-identity holds against `tests/data/literal_baseline/`.
- [x] The director gives a valid plan on 6/6 fixtures; the license check is in place; degradation is tested.
- [x] `metaphor`, `callback` and the overlay layer are in the gallery with 0 overlaps.
- [x] G15 green on both long stories; the long budgets (literal and creative) are met or filed.
- [x] `docs/evals/creative_<date>.md` with stills and judgement.

**Wave H**
- [ ] H1–H6 each landed as one pushed commit scoped to its id.
- [ ] The deck, tree, perform, follow and score tests green, including **isolation** and **causality**.
- [ ] G16: all four runs scored, every §8 bar met or filed; the oracle compared; the tie-break measured and decided by its rule.
- [ ] `docs/evals/presentation_<date>.md` with strip charts and descriptions.

**Both**
- [ ] §1.3 re-measured bare (G1–G16, three budgets).
- [ ] This guide rewritten to **Queue Complete**. **Then stop. Do not invent work.**

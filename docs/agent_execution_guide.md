# Agent Execution Guide — Status: Queue Complete — October 4, 2026

**You are an engineering agent with no memory of this project.** Waves A (A1–A22), B (B1–B17), C (C1–C8), D (D1–D5), and E (E1–E6) are built, committed and pushed. All items in the queue are complete.

On October 3, 2026 an independent pass identified six verification fixes (Wave E, E1–E6). All six have been implemented, tested, verified on real outputs, and pushed.

Wave E fixes delivered:
- **The critic's findings stick (E1):** Rose's note tone enforced to neutral, unconfirmed dialogue and emotions repaired to neutral, disputed kinetic quote speakers removed.
- **R7 never replaces quoted speech (E2):** Rose's quoted note stays on screen as kinetic quote; R7 respects quotes.
- **A year is not a stat (E3):** Integer years 1000..2100 in beat text are rejected by stat_callout validator.
- **The props prompt lists allowed icon names (E4):** 157-icon allow list included in prompt; 0 Armchair icons across all fixtures and rendered jobs.
- **Hygiene (E5):** Import-time HF_HOME override removed; doctor hint added; comments refreshed.
- **Re-measure and close-out (E6):** Planner eval, E2E steps 1–9 with verify_e2e_scenes, cold performance budget, and rendered stills verified.

**Queue Status:** All Wave E items E1–E6 are complete. The queue is empty. Do not invent work.

**Every number and literal string in this document and in the design docs is a decision, not a suggestion.** Implement as written; that includes prompts, thresholds, regexes, seeds and error strings. If a value is genuinely impossible, keep the *intent*, deviate minimally, say so in the commit body, and add it to §5.2. If the design itself cannot work, **STOP and file it in `docs/ongoing_general_errors.md` with options and a `Your selection: _____` line. Do not improvise, and never fill in a selection line yourself.**

**What the product is, in one paragraph.** A local-only CLI that turns a **text story** (narrated by local TTS in an automatically chosen voice) or an **audio narration** into a **1080×1920 animated explainer video**. It uses flat editorial vector scenes chosen from 16 templates, with word-by-word karaoke captions and few words on the graphics (Issue 7). It has a persistent cast of vector avatars, locally generated illustrations checked for stray lettering, a blind critic for people scenes, and optional music and SFX. Every video **stops for human review** before the final render. The long-term goal is live mode, so the renderer is clock-agnostic.

**The lesson that shaped this wave.** A rule that a model may decline is not a rule (lesson 2.10). Every item here **enforces its rule on the final result**, and its validation uses a frozen case taken from the real Wave D output, which you run against the unfixed code first and see fail.

---

## 0. Standing constraints (apply to every item)

1. **The battery is the regression bar.** After every item, run the full battery and update §1.3. **Read every exit code bare.**
2. **Fully local at runtime.** No cloud API, no network except loopback. Pull no new models.
3. **Python (Pydantic) is the source of truth for every contract.** Generated files are never hand-edited.
4. **Templates read time only through the clock.**
5. **The review gate is mandatory.** No auto-approve under any name.
6. **The planner never crashes the pipeline and never shows an ungrounded, truncated or id-bearing text, or one over its word cap. Every LLM call goes through `run_with_retries`.**
7. **Red first, on real inputs.** Before fixing, run the item's falsifying check against the *current* code using the frozen real case, and record the failure.
8. **One item = one Conventional Commit, scope = item id** (`fix(e1): …`). WHY plus red and green runs in the body. **Push after every item.** **Never amend a pushed commit.**
9. **Record the resolution in the same commit:** one line under "Wave E" in `ongoing_general_errors.md` §3, in the form `E<n> — <title> — git log --grep "(e<n>)" — <measured result>`, never a hash.
10. **When this guide and a design doc disagree, stop and file it.**
11. Every stage log ends in `llm_calls=<n> cache_hits=<m> elapsed_ms=<t>`; the call counter is incremented at the backend's entry point.
12. **Nothing in the package changes the process environment at import time** (E5). If your shell's `HF_HOME` lacks the Kokoro weights, export a correct `HF_HOME` in the shell; never in code.

---

## 1. Verified baseline (October 3, 2026, independent verification session)

### 1.1 Environment

Unchanged and re-verified by `doctor` (22 checks OK):
- M4 Max 64 GB; ffmpeg 8.1; Node v26.5.0; Python 3.12 (uv).
- Ollama with `gemma4:26b`; Kokoro 0.9.4; mlx-whisper 0.4.3.
- mflux via `mflux-generate-flux2 --model flux2-klein-4b`; Remotion 4.0.528.

The battery was run with `HF_HOME=$HOME/.cache/huggingface` exported in the shell.

### 1.2 Repository

- Wave A `4df212a`…`e374a15`; Wave B `cad065d`…`beb4c4f`; Waves C and D `12209d2`…`98db684` (13 commits scoped `(c1)`…`(c8)` and `(d1)`…`(d5)`).
- Design contracts revised October 3, 2026 for Wave E (list in `ongoing_general_errors.md` §5).
- New frozen test data:
  - `tests/data/critic_enforcement_cases.json`: seven real Wave D scenes (3 dialogue, 2 kinetic_quote, 2 emotion_beat). Each has its bible, its four passage beats, its props, and **the critic's readings on seeds 7, 8 and 9**, identical across seeds.
  - `tests/data/wave_e_expectations.json`: the new rhythm case R7-h (Rose's note), R7-b's new expectation, and the exact new expected output of `recipe_choices.json`. No test reads it directly; E2 merges it.
  - `tests/data/icon_prompt_cases.json`: two real `emu_war` scenes whose Wave D icons were `Armchair`, with bible, sentence texts and beats, for E4's slow test.

### 1.3 Gates (run bare in the verification session)

| # | Gate | Result |
|---|---|---|
| G1 | `uv run ruff check .` | exit 0 · All checks passed |
| G2 | `uv run ruff format --check .` | exit 0 · 118 files |
| G3 | `uv run mypy src` | exit 0 · 59 source files |
| G4 | `uv run pytest -q -m "not slow"` | exit 0 · **257 passed** |
| G5 | `npm --prefix renderer run typecheck` | exit 0 · 0 errors |
| G6 | `npm --prefix renderer run lint` | exit 0 · 0 errors |
| G7 | `npm --prefix renderer test` | exit 0 · **16 passed** (4 files) |
| G8 | `./scripts/check_schema_sync.sh` | exit 0 · in sync |
| G9 | `./scripts/check_renderer_purity.sh` | exit 0 · pure |
| G10 | `./scripts/check_gallery.sh` | exit 0 · 37 s · 53 goldens, 0 overflows, caption spacing verified |
| G11 | `uv run pytest -q -m slow` | exit 0 · **37 passed** · 190 s |
| G12 | `./scripts/e2e.sh` | exit 0 · steps 1–9 pass; sync probe 9/9; word density 0.54–0.83 words/s; light share 4/9–15/28; verify_e2e_scenes 7/7 jobs pass (0 unneutral tones, 0 disputed attributions, 0 quoted R7, 0 years, 0 Armchairs) |
| G13 | `./scripts/check_offline.sh` | exit 0 · 239 s |
| G14 | `uv run infographics doctor` | exit 0 · 22 checks OK |
| Budget | `./scripts/measure_budget.sh` (cold, `story_recipe_box`) | exit 0 · **0 cache hits** · `new`→review **209.7 s** (≤ 390) · render **198.2 s** (≤ 210) · total **407.9 s** (≤ 600) · 58 LLM calls |

### 1.4 Measurements that shaped Wave E (October 3, 2026, `gemma4:26b`; Wave C/D E2E output)

| What | Result |
|---|---|
| Dialogue lines whose tone the critic flagged as `X vs unknown`, then retried (48 E2E jobs) | **35 of 87** kept the flagged tone. The retry "succeeded" by keeping it, so C3's repair (which runs only when every attempt fails) never fired. Final run: Rose's note **sarcastic** ×2; "It's a joke." sarcastic; "It must stay in the family." sarcastic |
| Who-mismatch retries that left an unverified strong tone | "Rose?" said **angry**, written by a retry triggered by a speaker mismatch and never re-checked (Wave A's regression case B, back in production) |
| `kinetic_quote` attributions the critic disputed | **7 of 8** kept: each retry returned identical props. "The first attack came on November 2." → The Soldiers (reading `narration`); "Stay in room 12 on March 3rd…" → Sofia (reading `c2`, Mr. Alvarez, who wrote the list) |
| The current critic on the 13 model-planned emotion beats, seeds 7–9 | Identical across seeds. **4** read `unknown` while the props show a strong feeling: "angry" for "Meredith was impressed by his opponent."; "angry" for "I called the number I found online, expecting nothing."; "shocked" and "angry" for "…he was quiet for a long time." All 4 pass as "agree" today, and all 4 are unsupported. No supported feeling was read as `unknown` |
| R7 repairs on beats containing quoted speech (26 Wave D jobs) | **2 of 10**, both Rose's note (the climax) → a neutral face of Grandma Rose |
| Year-like stats (every run since Wave A) | 1: `story_room_12` "She had died in 2016…" → value 2016, suffix `""`, rendered **"2,016"** (frame checked). With a unit field, the model wrote suffix "Year died" |
| Icon distribution | "Armchair", second in the 157-name allow-list, was the most-used icon in every wave: 9% (A), 9% (B), 15% (C), **18%** (D final run). The props prompt never lists the names |
| All 27 icon-bearing scenes of the final E2E, re-planned with and without the allowed names in the prompt | Armchair **8 of 54 → 0 of 56**. "Rescuers" `Users`, "Trampled crops" `Plant`, "Machine Guns" `Bomb`, "deaths" `Skull`, "emus" `Bird` |
| A reference implementation of R1/R6/R2/R4/R5/R7 | Reproduces the committed `recipe_choices.json` expectation **exactly**. With the quoted-speech exclusion, R7 s016 disappears (that beat is Walt's quote) and everything else is unchanged |
| `src/animated_infographics/__init__.py:3-11` (added in `(d1)`, not in any spec, not in the commit message) | Sets `HF_HOME` on import whenever the configured one lacks Kokoro. `doctor` check 7 exists to report exactly that misconfiguration, and now cannot |

---

## 2. Execution order

| # | Item | Why this position |
|---|---|---|
| E1 | Critic findings stick: tone and emotion enforcement after the round; the emotion rule; disputed quote speakers removed | The most visible meaning errors. It changes critic outcomes that E6 measures, and it extends `CriticReport` (G8). |
| E2 | R7 never replaces quoted speech | Selection-only; independent of E1. Its frozen expectations must be updated in the same commit. |
| E3 | A year is not a stat | A validator meaning rule; independent. Before E4, so E4's re-measure sees it. |
| E4 | The props prompt lists the allowed icon names | A prompt change. It changes every icon-bearing scene, so it comes after the validators are settled. |
| E5 | Hygiene: no import-time environment change; stale comments | Small; independent. Before E6, so the final battery runs on the cleaned package. |
| E6 | Re-measure: planner eval, E2E, cold budget, rendered stills; close-out | Measures the finished system. |

---

## 3. The items

### E1 — Critic findings stick: enforcement after the round, the emotion rule, disputed quote speakers removed

**What this means for the user:** once the critic has caught a tone, feeling or speaker the story doesn't support, it never reaches the screen. Rose's note is no longer sarcastic, and the narration is no longer a quote from The Soldiers.

**The gap:**
- `planner/props.py:395-537` `_evaluate_scene_critic`:
  - A **successful** critic-triggered retry replaces the scene unchecked (`:461-490`).
  - The deterministic tone repair (`:495-520`) runs only when every retry attempt fails.
  - The model is told "otherwise keep yours", and kept the flagged tone in 35 of 87 cases and the disputed quote speaker in 7 of 8 (§1.4).
- `planner/critic.py:324` and following, `critic_mismatches` for `emotion_beat`: `unknown` is never a mismatch. That rule predates `neutral` (D1).
- `contracts/models.py:606`: `CriticReport.repair: Literal["tone_neutral"] | None`.
- Contract: `design_planner.md` §11 (the revised **Emotion** rule; "Enforcement after the round"); `design_data_contracts.md` §6.

**Implementation:**
1. **Emotion rule** (`critic_mismatches`): a mismatch iff (critic emotion ≠ `unknown` and ≠ props) **or** (critic emotion = `unknown` and props emotion ≠ `neutral`). The string is unchanged: `emotion: <props> vs <critic>`.
2. **`enforce_reading(scene, reading, bible) -> tuple[Scene, str | None]`** in `planner/critic.py`. `reading` is the **normalised critic answer that produced the mismatch**: the original call's answer, never a new call. It returns the possibly modified scene and the repair name:
   - **`dialogue`:** for every line `i` with tone ≠ `neutral`, keep the tone only if `i < len(reading["lines"])` and `reading["lines"][i]["tone"]` equals it; otherwise set it to `neutral`. Any change → `"tone_neutral"`.
   - **`emotion_beat`:** if emotion ≠ `neutral` and ≠ `reading["emotion"]` → `neutral`, `"emotion_neutral"`.
   - **`kinetic_quote`:** let `r = reading["speaker"]`. If `attribution_cast_id` is not null and (`r` is a cast id ≠ the attribution, or `r == "narration"` and the attribution ≠ the narrator's id), set `attribution_cast_id = None`, `"attribution_dropped"`. If `r == "unknown"`, nothing changes.
   - **`text_thread`:** unchanged; nothing is enforced.
3. In `_evaluate_scene_critic`, after a mismatch:
   - take the scene that stands (the retry's result if it validated, else the original);
   - apply `enforce_reading` to it;
   - re-run `validate_scene`. It must pass, because these fields carry no text; if it somehow fails, keep the un-enforced scene and add the errors to `retry_errors`.
   - `changed` = final props ≠ original props (dict comparison). `repair` = the returned name, or null.
   - **Delete the old "every mismatch is tone vs unknown, and all attempts failed" branch** (`:495-520`); `enforce_reading` subsumes it.
4. `CriticReport.repair: Literal["tone_neutral", "emotion_neutral", "attribution_dropped"] | None`. Regenerate the schema (G8).
5. `evals/planner.py`: report per fixture the counts of each repair, next to the existing critic columns.

**Validate:**
- The "critic enforcement" row in `design_testing_and_validation.md` §2. It is a stub backend that returns each frozen case's recorded reading (`critic_readings_seeds_7_8_9[0]`) and a stub retry that returns the **same props**, which is what the real model did.
- **Red first:** on today's code:
  - Rose's note keeps `sarcastic` on both lines;
  - "The first attack…" keeps `c2`;
  - both angry emotion beats report **agree**.

  Record all three.
- **After:**
  - Rose's note → both lines `neutral`, `repair: "tone_neutral"`, `changed: true`;
  - "It's a joke." → `neutral`, and the second line is unchanged;
  - "Rose?" → `neutral`;
  - "The first attack…" and "Stay in room 12…" → `attribution_cast_id: null`, `"attribution_dropped"`;
  - both emotion beats → status `mismatch_retried`, final `neutral`, `"emotion_neutral"`.
- **Slow test (real model)**, `tests/slow/test_critic_enforcement_live.py`: the two `emotion_beat` cases through the real critic on seeds 7, 8 and 9 → `emotion` is `unknown`, so the new rule reports a mismatch (6/6). The critic regression set (A, B, B′, C, E, F, G, H) stays **8/8** on seeds 7, 8 and 9.
- **Falsify:**
  - skip `enforce_reading` when the retry succeeded → the Rose's-note case is red;
  - restore the old emotion rule → the emotion cases are red.

**Blast radius:** `planner/critic.py`, `planner/props.py`, `contracts/models.py` and its generated schema/TS, `evals/planner.py`, `tests/test_critic.py`, `tests/slow/`, tests that assert the old `repair` literal.

---

### E2 — R7 never replaces quoted speech

**What this means for the user:** the story's quoted lines, like Rose's note, stay on screen as words; the rhythm rule only replaces scenes that restate the narration.

**The gap:**
- `planner/select.py:174`: `if run >= 2 and t in REPLACEABLE_TEMPLATES:` ignores whether the beat is someone's quoted words.
- Measured: 2 of 10 Wave D R7 repairs replaced Rose's note, the climax, with a neutral face (§1.4).
- The frozen expectation R7-b (Walt's line → blueberry pie) encoded the same mistake.
- Contract: `design_planner.md` §4 ("R7", the quoted-speech bullet); `design_templates.md` §5.4.

**Implementation:**
1. `select.py`: the R7 condition becomes `run >= 2 and t in REPLACEABLE_TEMPLATES and not QUOTED.search(beats[i].text)`, using `QUOTED` from `planner/rhythm.py`. A beat with quoted speech is not replaced, and still counts as worded.
2. **Update the frozen data in the same commit**, from `tests/data/wave_e_expectations.json`:
   - in `tests/data/rhythm_cases.json`, set R7-b's `expected` to `null` and its `why` to the value given under `rhythm_cases_changes.R7-b`;
   - append the R7-h case under `rhythm_cases_changes.add`;
   - in `tests/data/recipe_choices.json`, replace `expected` with `recipe_choices_expected`. The only differences: choice 16 becomes `{"primary": "kinetic_quote", "alternate": "reveal"}`, and the R7 repair for `s016` disappears.
3. Rename `test_rhythm_cases_all_seven` to `test_rhythm_cases` and assert **8** cases.

**Validate:**
- **Red first:** with the updated data files and today's `select.py`, R7-b, R7-h and the recipe expectation are red.
- After: all green. R7-a, R7-c and R7-d…g are unchanged.
- **Falsify:** remove the `QUOTED` condition → R7-b and R7-h are red.

**Blast radius:** `planner/select.py`, `tests/data/rhythm_cases.json`, `tests/data/recipe_choices.json`, `tests/test_select_rules.py`.

---

### E3 — A year is not a stat

**What this means for the user:** a date is never drawn as a counter like "2,016".

**The gap:**
- `planner/validate.py:437` and the meaning rules around it check the stat's currency suffix, but nothing stops a year being used as a quantity.
- In the final `story_room_12` render, "She had died in 2016, and March 3rd was her birthday." is a `stat_callout`: value 2016, rendered "2,016", counting up from 0 (§1.4). It arrived through R6, which demoted the story's second timeline to its alternate.
- Contract: `design_planner.md` §6 item 6 ("A year is not a stat").

**Implementation:**
1. In `validate_scene`'s `stat_callout` branch: if `props.decimals == 0` and `props.display_scale == "none"` and `props.value` is an integer `v` with `1000 <= v <= 2100`, and `re.search(rf"(?<![\d,.]){v}(?![\d]|,\d)", beat_text)` matches, add exactly `f"props.value: {v} is a year in this beat; a year belongs in a timeline or an era label, not a stat"`.
2. Nothing else changes; the ladder handles the rest.

**Validate:**
- The "quoted beats and years" row in `design_testing_and_validation.md` §2: 2016 with suffix `""` and `"Year died"` → error; 1932 in "In 1932, …" → error; 20,000, 312, and 1,500 written with a comma → no error.
- **Red first:** the real room 12 scene validates today.
- **Falsify:**
  - delete the rule → the 2016 case is red;
  - widen the range to 0–9999 → the 312 case ("The box held 312 handwritten cards") is red.

**Blast radius:** `planner/validate.py`, `tests/test_validate.py`.

---

### E4 — The props prompt lists the allowed icon names

**What this means for the user:** icons depict their labels (a bomb for machine guns, a plant for crops) instead of an armchair.

**The gap:**
- `planner/props.py:312-323` builds the props prompt without the icon allow-list. `contracts/icons.py` has 157 names, but the model only ever sees them as a schema `enum`, so its guesses are snapped to an early name.
- "Armchair" was 18% of icons in the final run (§1.4).
- Contract: `design_planner.md` §5 ("Allowed icon names in the props prompt").

**Implementation:**
1. In `plan_single_template_props`, when the template's props model has an `icon` field at any depth (`stat_callout`, `icon_list`, `cause_effect`, `comparison`), append to the user prompt, after `extra_user_prompt` handling and **before** any retry text, exactly:
   ```
   \n\n# Icons\nEvery icon field must be one of these names. Pick the one that depicts the label; if none does and the field is optional, leave it out.\n<names>
   ```
   `<names>` is every member of `IconName` in `contracts/icons.py` order, joined by `", "`.
2. Compute the block once at import (a module constant), from `typing.get_args(IconName)`. No other template's prompt gets it.
3. Record the new prompt SHA-256s in E6's eval. `props.md` itself is unchanged; the block is code-built.

**Validate:**
- The "icon prompt" row in `design_testing_and_validation.md` §2.
- **Red first:** a unit test asserting the block in the `icon_list` prompt fails today.
- **Slow test (real model)**, `tests/slow/test_icon_prompt_live.py`, on the two scenes frozen in `tests/data/icon_prompt_cases.json` (`emu_war` bible, sentence texts, neighbouring beats, and the Wave D props, both containing `Armchair`):
  - the `icon_list` "The birds trampled crops and flattened fences, letting rabbits in behind them.";
  - the `cause_effect` "The government gave up on machine guns and paid farmers a bounty instead."

  Re-plan each through the real props stage; neither result contains `Armchair`. Build the `Transcript` from the sentence texts as `evals/planner.py` does.
- **Falsify:** remove the block → re-run the slow test and record whether Armchair returns (a measurement for the commit body, not a gate).

**Blast radius:** `planner/props.py`, `tests/test_props_prompt.py` (new), `tests/slow/`.

---

### E5 — Hygiene: no import-time environment change; stale comments

**What this means for the user:** a misconfigured model cache is reported by `doctor`, not silently papered over; the code says what it does.

**The gap:**
- `src/animated_infographics/__init__.py:3-11`, added in `(d1)` but in no spec and no commit message, rewrites `os.environ["HF_HOME"]` on import whenever the configured `HF_HOME` lacks Kokoro. `doctor` check 7 (`doctor.py:192-208`) exists to report exactly that, and now cannot.
- `renderer/src/templates/location.tsx:208` and `set_piece.tsx:142` still say "caption directly above name". The caption was removed in D1.

**Implementation:**
1. Delete the `HF_HOME` block from `__init__.py`; it returns to its pre-`(d1)` content.
2. `doctor.py`: the Kokoro "missing" message gains, verbatim: ` (if HF_HOME is set, it must contain hub/models--hexgrad--Kokoro-82M; unset it or export HF_HOME="$HOME/.cache/huggingface")`.
3. `scripts/battery.sh` keeps its explicit `HF_HOME` export. That is a script setting its own environment, which is allowed. Document it in `design_testing_and_validation.md` §3 with one sentence.
4. Fix the two comments to "place name bottom-aligned at y 1080; no caption (removed in D1)" and "name bottom-aligned at y 1080; no caption (removed in D1)".

**Validate:**
- **Red first:** `HF_HOME=$(mktemp -d) uv run python -c "import os, animated_infographics; print(os.environ['HF_HOME'])"` prints `~/.cache/huggingface` today.
- After: it prints the temporary directory, and `HF_HOME=$(mktemp -d) uv run infographics doctor` exits **4** with the new hint.
- The full battery stays green with `HF_HOME` exported in the shell.

**Blast radius:** `src/animated_infographics/__init__.py`, `src/animated_infographics/doctor.py`, `docs/design_testing_and_validation.md` §3, the two renderer comments.

---

### E6 — Re-measure; close-out

**What this means for the user:** measured confirmation, on the four stories, that the scenes now say what the story says, and that the word budget and time budget still hold.

**Implementation:**
1. **Planner eval**, cold (`--no-llm-cache`) → `docs/evals/planner_<date>.md`. Every `design_planner.md` §9 bar on every fixture, including:
   - light share ≥ 1/3;
   - 0 word-cap violations;
   - critic regression 8/8.

   Report the E1 repair counts and **"Armchair" occurrences (must be 0 across the four fixtures; no fixture mentions a chair)**. `molasses_flood` sat exactly on the light-share bar in Wave D (2/6). If it falls below, file it with the numbers; do not tune.
2. **G12**, including step 9. Then, over every rendered job:
   - 0 dialogue lines whose tone the critic flagged as `vs unknown` remain non-neutral;
   - 0 `kinetic_quote` scenes keep a disputed attribution;
   - 0 R7 repairs on beats with quoted speech;
   - 0 year-like stats;
   - Armchair count.

   Write a short script under `scripts/` or `evals/` that reads `plan_report.json` and `storyboard.json`, and commit it.
3. **Cold budget** → `docs/evals/budget_<date>.md`; bars ≤ 390 / 210 / 600 s.
4. Open the `story_recipe_box` stills and describe each:
   - the scene of Rose's note (words on screen, no sarcastic tone);
   - the "I called the number…" scene (the face's expression);
   - one icon list (each icon);
   - and, in `story_room_12`, the "She had died in 2016" scene (the template now used).

**Validate:** the bars above. Exceeding one is filed with numbers, never tuned away.

**Close-out:**
1. Full battery, bare; update §1.3.
2. Rewrite this guide to **Queue Complete**.
3. Move Wave E to §5.1.
4. Update `ongoing_general_errors.md` §1.
5. Stop.

---

## 4. Deferred — do NOT start

- **DF1–DF9** (`ongoing_general_errors.md` §4): video input + PiP, 16:9, multi-voice, live mode, Reddit URL fetch, public-domain photos, historical borders, web editor, cloud LLM.
- **Known limitation, not scheduled:** quote tracking in beat splitting resets at each sentence, so a quotation spanning two sentences can be split between them (C1 verdict). Do not change it without a new spec.
- **Not scheduled:** the critic's `emotion_beat` *who* reading is noisy. It named a different person than the props on 7 of 13 real beats, several of them wrongly. No deterministic who-repair is allowed (§5.5); E1 does not touch it.

---

## 5. Do NOT change

### 5.1 Already delivered

- **Wave A (A1–A22)**, verified September 25, 2026; **Wave B (B1–B17)**, verified September 26, 2026; **Waves C (C1–C8) and D (D1–D5)**, independently verified October 3, 2026; **Wave E (E1–E6)**, verified October 4, 2026. One line per item, with verdicts, is in `ongoing_general_errors.md` §3.
- Items marked "✓" are not reworked.

### 5.2 Accepted equivalents (checked; do not "fix" these back)

- The sync probe is drawn inside each scene's layer, not a separate Story layer.
- The geo bbox check handles antimeridian-crossing countries (`planner/geo.py`).
- `image_prompt` strips a trailing period from `visual_description`.
- `FitText` gives multi-line boxes 0.35 of a line of extra height for ascenders.
- The gallery computes fixture timing with a TypeScript port of `item_frames`, gallery-only.
- `fixtures/CHECKSUMS` paths are relative to `fixtures/`.
- `plan_report.json.llm_calls` counts the storyboard stage's calls only (select + props + critic).
- Node 26 works; the Node 22 fallback was not needed.
- B7's at-limit strings are reported, not failed (`design_planner.md` §9).
- Remotion `AudioLayer` clamps volume to ≥ 0.001 and passes `loopVolumeCurveBehavior="extend"`.
- `renderer/public/geo/lakes-50m.json` is pretty-printed (1.5 MB).
- **(Oct 3)** The critic's user message lists the cast without a `Cast:` label above it. The regression set is 8/8 with it.
- **(Oct 3)** `scripts/battery.sh` exports `HF_HOME` for its own run (documented in E5); the package itself never does.

### 5.3 User decisions

**September 23, 2026:**
- Offline first; a template library.
- History + Reddit-style stories; text + audio inputs.
- Mixed imagery; Python + TypeScript/Remotion; fully local.
- 9:16; karaoke captions; flat editorial vector; 1–3 min videos in about 10 min.
- Scenes + a persistent cast; single narrator; a mandatory review gate; music + SFX from a user-supplied pack.
- Live mode later, with the webcam in a corner.

**September 24, 2026:**
- **Issue 1 → A + B:** "If the story from reddit seems to be from a female's perspective then use af_heart, else use am_michael."
- **Issue 2 → A:** FLUX.2 [klein] 4B.
- Test stories must be complete stories.

**September 25, 2026:**
- **Issue 3 → A:** "Proceed with Option A. Though, in the example provided, I think that text is fine if the description calls for text like a recipe."
- **Issue 4 → A:** "Proceed with Option A."
- **Issue 5 → A:** "Option A".

**September 27, 2026:**
- **Issue 6 → D (keep as is):** "I think the paraphrasing is fine."
- **Live presentations:** "For real-time presentations, it makes sense to show timelines and repeated graphics to drive home the point." (`design_future_live_and_video.md` §4.)
- **Issue 7 → A:** "Proceed with Option A." (Wave D.)

### 5.4 Invariants and intentional design decisions

**New (October 3, 2026, Wave E):**
- **A rule is enforced on the final scene, not on the retry path** (E1). After a critic mismatch, a non-neutral tone or emotion survives only if the critic read the same one. A disputed `kinetic_quote` speaker is removed. These repairs only ever **remove** a claim; they never write in the critic's reading.
- **An `unknown` emotion reading counts against a strong feeling**, as an `unknown` tone does (E1). An `unknown` *speaker* still never counts.
- **R7 never replaces a beat containing quoted speech or writing** (E2).
- **A bare four-digit year is never a stat** (E3).
- **The props prompt shows the icon allow-list** for templates with icon fields (E4).
- **The package never changes the environment at import** (E5).

**From Waves C and D:**
- Quoted speech is never split from its introducing words (unless the sentence exceeds 16 s); the colon earns no split bonus.
- The critic reads one continuous passage. Text-thread answers are keyed; the critic names the contact. A null `contact_cast_id` is filled only on an exact, unique name match.
- The critic-triggered retry gets 3 attempts; `changed` means the props differ.
- No bible entity id appears in on-screen text. Caption words are laid out at their active size.
- A recorded job-local input that is missing is an error.
- `dialogue` and `text_thread` may paraphrase (Issue 6 → D).
- `WORD_CAPS` is the single source of word caps and the density metric. The removed fields stay removed.
- R7 pictures are deterministic. R7 never replaces a kept template.
- At most one `timeline` and one `comparison` per offline video.
- Karaoke captions are unchanged.

**Unchanged:**
- Job-local inputs are authoritative.
- Every LLM call goes through `run_with_retries`.
- LLM-facing schemas carry no length constraints.
- Text over images only where the scrim is ≥ 85%.
- The text check never runs on text-expected descriptions.
- The critic is blind and makes at most one critic call per scene.
- Timeline labels are a grounded date or one of 17 phrases.
- The voice-rule asymmetry.
- Cast = vector avatars only.
- No auto-approve.
- Scenes lead by 200 ms.
- Absolute-frame scenes.
- Timings are computed once, in Python.
- Grounding is a hard gate.
- Navy text on cast colours.
- FLUX.2 klein 9B is never used.
- Beat boundaries are not human-editable.
- The offline gate stays.
- Fixtures are original texts.
- Commit scope = item id.

### 5.5 Assessed and rejected — do NOT re-propose

**Carried over:**
- Live-first; LLM-written scene code; generated video.
- Video input or URL fetching in the MVP.
- Vector-only or illustration-heavy imagery; generated cast portraits.
- Any cloud API.
- Both aspects at once; subtitles or no captions.
- Other art styles.
- Multi-voice in the MVP; an optional gate or a web editor.
- `TransitionSeries`; TypeScript as the schema source.
- Voices `bm_george`/`af_bella`; Z-Image-Turbo.
- Inferring narrator gender from stereotypes.
- Raising `maxLength` to "fix" truncation; relaxing the fallback bar.
- Issue 3 B/C; Issue 4 B/C; Issue 5 B/C/D; Issue 6 A/B/C; Issue 7 B/C/D.
- The naive yes/no text-check prompt.
- Counting an `unknown` speaker as a mismatch; **a second critic call per scene**.
- Removing or skipping the critic or text check to meet the budget.
- Keeping the "context only" framing.
- **Assigning the critic's speaker to a scene** (it can be wrong: case C). *Removing* a disputed `kinetic_quote` speaker is allowed from E1 and is different: it asserts nothing.
- Lowering the active caption scale; treating at-limit strings as failures.
- An array schema for per-message answers.
- LLM-chosen emotions for R7 reaction shots.
- Letting R7 replace kept templates.
- Raising `kinetic_quote` above 12 words.
- A words-per-second bar in the simulated-timing planner eval.

**New, October 3, 2026:**
- Re-asking the critic after a retry: it breaks "one critic call per scene" and doubles critic cost. E1's enforcement needs no new call.
- Fixing the armchair by removing or reordering it in the allow-list: that moves the default without fixing the cause. E4 shows the names.
- Rendering four-digit integers without a thousands separator: a year would still be a counter. E3 rejects the stat instead.
- Loosening the light-share bar if `molasses_flood` drops below 1/3: file it.

---

## 6. Where the contracts live

| What | Where |
|---|---|
| Pipeline, job layout, job-local inputs, CLI, review gate, local-only policy, pinned models | `design_system_architecture.md` |
| JSON shapes (**`plan_report.critic.repair`: `tone_neutral` / `emotion_neutral` / `attribution_dropped`**), generated files, sync gate | `design_data_contracts.md` |
| Ingest, TTS, ASR, loudness, frame math, beat splitting with quoted speech (§7), captions, SFX | `design_audio_and_timing.md` |
| LLM backend; **R6/R7 incl. the quoted-speech exclusion (§4)**; **the props prompt incl. the icon block (§5)**; validators incl. **a year is not a stat (§6 item 6)** and word caps (item 9); eval bars (§9); **critic §11 incl. the emotion rule and enforcement after the round** | `design_planner.md` |
| The 16 templates; the word budget (§5, template classes in §5.4) | `design_templates.md` |
| Palette, composited contrast, captions, illustration + text check | `design_visual_direction.md` |
| Remotion, clock, render CLI, preview, verification | `design_rendering.md` |
| Fixtures, test rows (**critic enforcement, quoted beats and years, icon prompt**), gates, E2E incl. step 9, offline, cold budget | `design_testing_and_validation.md` |
| Resolved index (Wave C/D verdicts), lessons 2.1–2.11, deferred items DF1–DF9, decision log | `ongoing_general_errors.md` |
| Live mode and the user's direction for it | `design_future_live_and_video.md` |

---

## 7. Validation standard

- **Red first, on real inputs.** A regression set built only from tidy cases can pass while production fails (lesson 2.6).
- **Measure outcomes by comparing before and after**, and record why a repair did not happen (lesson 2.7).
- **Measure the rendered result, not the style values** (lesson 2.8).
- **Enforce a rule on the final result, not on the path that produced it** (lesson 2.10).
- **Measure the distribution of what the model picks, not just its validity** (lesson 2.11).
- A gate must be able to fail, and must fail closed. A perfect score is a reason to look harder. Warm caches measure nothing about a cold budget.
- Read exit codes bare. A gate that did not run is not a pass. Open every artefact and describe it.
- **Never loosen a bar to pass it.** File it with the measurement.

---

## 8. THE LOOP

```
(1) Is there an approved item? Wave E, E1–E6, in §2 order. If all are done,
    STOP. Never start DF1–DF9 or anything not in §3 without a user
    selection. Never fill in a `Your selection:` line.
(2) Read the item and EVERY design section it names. Copy prompts, regexes,
    thresholds and error strings VERBATIM.
(3) RED FIRST on the frozen real case; record the failure.
(4) Build only what the item says. Nothing from §5.5.
(5) GREEN; then falsify (break, see red, restore, see green).
(6) Open every artefact and describe it.
(7) Full battery, bare (HF_HOME exported in the shell). Update §1.3.
(8) ONE commit, scope = item id (`fix(e1): …`). WHY + red/green in the
    body. ONE line under "Wave E" in ongoing_general_errors.md §3,
    citing `git log --grep "(e1)"`. Never amend after pushing.
(9) git push origin main.
(10) Next item.
```

---

## 9. Definition of Done: Wave E

- [x] E1–E6 each landed as one pushed commit scoped to its id, with red and green runs recorded.
- [x] The seven frozen enforcement cases give their exact expected outcomes; the emotion cases are mismatches on the real critic 6/6; the critic regression set is 8/8.
- [x] R7-b and R7-h are never replaced; `recipe_choices.json` matches the new expectation exactly.
- [x] The 2016 case is rejected with the exact error string; counts written with separators are not.
- [x] The icon block is in every icon-bearing props prompt; 0 Armchair in the planner eval's four fixtures.
- [x] Importing the package leaves `HF_HOME` unchanged; `doctor` reports a bad `HF_HOME` with the new hint.
- [x] E6: every planner-eval bar, every E2E step including step 9, and the cold budget bars met or filed, with the E6 counts reported (0 surviving flagged tones, 0 disputed quote speakers, 0 quoted beats replaced, 0 year stats).
- [x] §1.3 re-measured this session, read bare.
- [x] This guide rewritten to **Queue Complete**. **Then stop. Do not invent work.**

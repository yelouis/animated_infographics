# Agent Execution Guide — Active Build: Wave F (verification fixes, 4 items) — October 4, 2026

**You are an engineering agent with no memory of this project.** Waves A–E are built, committed and pushed (head `66b377f`).

On October 4, 2026 an independent pass did three things:
- re-ran every gate and the cold budget bare: all green;
- read every Wave E item against its spec: all 6 do what their specs say;
- read the rendered stories as a viewer would.

Every Wave E target is fixed on screen: Rose's note is her quote again, unsupported tones and feelings are neutral, disputed speakers are gone, and the icons depict their labels. Three problems remain:
- **A date is drawn as a counter.** "She had died in 2016, and March 3rd was her birthday." shows a big **3** over "rd March". One fresh `story_room_12` render has three such scenes. E3's rule covered only four-digit years.
- **Junk text reaches the screen.** "Icon: Bullet" and "Icon: Bird" appeared as comparison points (a side effect of E4 showing the icon names), and a comparison side read "Not specified".
- **Era stamps are invented.** "Present Day" is stamped on "Last spring, Danny finally sold the house."; "Modern Era" on a 1990s motel. Since Wave A, 228 of 358 stamps contained no year at all.

Wave F fixes these. Each fix was measured on real output first (§1.4).

**What is approved:** Wave F, items **F1–F4** in §3, in the order of §2. **Nothing else.** **What NOT to touch:** everything in §5. **What must not be started:** everything in §4.

**Every number and literal string in this document and in the design docs is a decision, not a suggestion.** Implement as written; that includes regexes, word lists and error strings. If a value is genuinely impossible, keep the *intent*, deviate minimally, say so in the commit body, and add it to §5.2. If the design itself cannot work, **STOP and file it in `docs/ongoing_general_errors.md` with options and a `Your selection: _____` line. Do not improvise, and never fill in a selection line yourself.**

**What the product is, in one paragraph.** A local-only CLI that turns a **text story** (narrated by local TTS in an automatically chosen voice) or an **audio narration** into a **1080×1920 animated explainer video**. It uses flat editorial vector scenes chosen from 16 templates, with word-by-word karaoke captions and few words on the graphics (Issue 7). It has a persistent cast of vector avatars, locally generated illustrations checked for stray lettering, a blind critic for people scenes, and optional music and SFX. Every video **stops for human review** before the final render. The long-term goal is live mode, so the renderer is clock-agnostic.

**The lesson that shaped this wave.** A fix written for one example misses its siblings (lesson 2.12). Each rule here names a **class** (a date, a placeholder, a year), and was checked against every run since Wave A before it was written down.

---

## 0. Standing constraints (apply to every item)

1. **The battery is the regression bar.** After every item, run the full battery and update §1.3. **Read every exit code bare.**
2. **Fully local at runtime.** No cloud API, no network except loopback. Pull no new models.
3. **Python (Pydantic) is the source of truth for every contract.** Generated files are never hand-edited.
4. **Templates read time only through the clock.**
5. **The review gate is mandatory.** No auto-approve under any name.
6. **The planner never crashes the pipeline and never shows an ungrounded, truncated, id-bearing, over-cap, placeholder or instruction text. Every LLM call goes through `run_with_retries`.**
7. **Red first, on real inputs.** Before fixing, run the item's falsifying check against the *current* code using the frozen real case, and record the failure.
8. **One item = one Conventional Commit, scope = item id** (`fix(f1): …`). WHY plus red and green runs in the body. **Push after every item.** **Never amend a pushed commit.**
9. **Record the resolution in the same commit:** one line under "Wave F" in `ongoing_general_errors.md` §3, in the form `F<n> — <title> — git log --grep "(f<n>)" — <measured result>`, never a hash.
10. **When this guide and a design doc disagree, stop and file it.**
11. Every stage log ends in `llm_calls=<n> cache_hits=<m> elapsed_ms=<t>`.
12. **Nothing in the package changes the process environment at import time.** Export `HF_HOME` in your shell if needed (`HF_HOME=$HOME/.cache/huggingface`).
13. **Ids:** Wave F items are F1–F4. The live-mode constraints in `design_future_live_and_video.md` §1 are now LC1–LC6, and deferred features are DF1–DF9. Do not confuse them.

---

## 1. Verified baseline (October 4, 2026, independent verification session)

### 1.1 Environment

Unchanged; `doctor` 22 checks OK. M4 Max 64 GB; ffmpeg 8.1; Node v26.5.0; Python 3.12 (uv); Ollama with `gemma4:26b`; Kokoro 0.9.4; mlx-whisper 0.4.3; mflux (`flux2-klein-4b`); Remotion 4.0.528. The battery was run with `HF_HOME=$HOME/.cache/huggingface` exported in the shell.

### 1.2 Repository

- Waves A `4df212a`…`e374a15`; B `cad065d`…`beb4c4f`; C/D `12209d2`…`98db684`; E `26e0f2c`…`66b377f` (6 commits scoped `(e1)`…`(e6)`).
- Design contracts revised October 4, 2026 for Wave F (list in `ongoing_general_errors.md` §5).
- **New frozen test data:** `tests/data/wave_f_cases.json`, from the Wave E E2E. It holds:
  - the "March 3rd" stat (`stat_dates`), with its beat and exact expected error;
  - the two comparisons with "Icon: Bullet"/"Icon: Bird" and "Not specified" (`placeholder_scenes`), with their exact expected errors;
  - the eight real location era stamps (`era_labels`), with their expected normalised values and each job's transcript sentences (`transcripts`).

### 1.3 Gates (run bare in the verification session)

| # | Gate | Result |
|---|---|---|
| G1 | `uv run ruff check .` | exit 0 |
| G2 | `uv run ruff format --check .` | exit 0 |
| G3 | `uv run mypy src` | exit 0 |
| G4 | `uv run pytest -q -m "not slow"` | exit 0 · **257 passed** |
| G5 | `npm --prefix renderer run typecheck` | exit 0 |
| G6 | `npm --prefix renderer run lint` | exit 0 |
| G7 | `npm --prefix renderer test` | exit 0 · 16 passed |
| G8 | `./scripts/check_schema_sync.sh` | exit 0 |
| G9 | `./scripts/check_renderer_purity.sh` | exit 0 |
| G10 | `./scripts/check_gallery.sh` | exit 0 · 37 s · 0 overflows |
| G11 | `uv run pytest -q -m slow` | exit 0 · **37 passed** · 188 s |
| G12 | `./scripts/e2e.sh` | exit 0 · 1,033 s · steps 1–9 pass; sync probe 9/9; word density per job 0.54–0.83 graphic words/s, light share 4/9–16/32. `evals/verify_e2e_scenes.py` on its jobs: 0 surviving flagged tones, 0 disputed quote speakers, 0 quoted beats replaced, 0 year stats, 0 armchairs. **But** see §1.4 |
| G13 | `./scripts/check_offline.sh` | exit 0 · 226 s |
| G14 | `uv run infographics doctor` | exit 0 · 22 checks OK |
| Budget | `./scripts/measure_budget.sh` (cold, `story_recipe_box`) | exit 0 · **0 cache hits** · `new`→review **202.8 s** (≤ 390) · render **200.2 s** (≤ 210) · total **403.0 s** (≤ 600) · 58 LLM calls. **Watch:** render has 10 s of headroom (the agent's run: 198.2 s). Wave F changes no rendering, so a render over 210 s in F4 is filed, not tuned |

### 1.4 Measurements that shaped Wave F (October 4, 2026, `gemma4:26b`)

| What | Result |
|---|---|
| `stat_callout` scenes whose value is the day of a "<Month> <day>" date in the beat, every E2E run since Wave A | Wave A: "March 3rd" → 3 + "rd". Wave B: the same. Wave E agent run: "3" + "March". **My fresh Wave E run: 3 scenes in one `story_room_12`** ("3 / March", "3 / rd March" ×2). Frame checked: a big **3** over "rd March" beside a calendar icon |
| The date rule, re-planning the real "2016 / March 3rd" scene through the real props stage | All 3 attempts rejected → the ladder's deterministic quote of the sentence ("She had died in 2016, and March 3rd was her birthday.") |
| Placeholder and instruction rule, scanned over all 9,080 on-screen strings of every E2E run since Wave A | Flags only real junk: "N/A" ×15 (Wave A timeline labels), "Icon: Bullet", "Icon: Bird", "Not specified". **0 false alarms** ("UNKNOWN IDENTITY" is not a whole-string placeholder) |
| The same rule, re-planning the two real comparison scenes | "Icon: Bullet" → "10 per bird" (2 attempts); "Not specified" → a real second panel (3 attempts) |
| Location era stamps, all 358 location scenes since Wave A | **4** already a bare narration year · **115** contain one ("1932 Era", "1919 Boston") · **228** contain none ("Present Day", "Modern Era", "40 Years", "6 years", "N/A") |
| A retry-based era rule (stamp must be a year or words from the beat), re-planning 11 real location scenes | Worse: "Two days" (for "Two days later…"), "forty years"; the 1919 molasses location failed all 3 attempts. → **deterministic normalisation instead** |

---

## 2. Execution order

| # | Item | Why this position |
|---|---|---|
| F1 | A date is not a stat | It extends E3's rule in the same validator branch; independent of F2 and F3. |
| F2 | No placeholder or instruction text on screen | A validator rule over `WORD_CAPS` fields; independent. |
| F3 | Era stamps show a narration year or nothing | A deterministic normalisation in props planning; independent. Last of the code items, because it changes the most rendered scenes. |
| F4 | Re-measure: planner eval, E2E, cold budget, rendered stills; close-out | Measures the finished system. |

---

## 3. The items

### F1 — A date is not a stat

**What this means for the user:** "March 3rd" is never drawn as a counter reading "3 / rd March".

**The gap:**
- `planner/validate.py:~440-452` (E3) rejects only a bare four-digit year from 1000 to 2100.
- With "2016" blocked, the model put the day of the date into the stat instead. This happened in 3 scenes of one fresh `story_room_12` render, and in Wave A and Wave B runs (§1.4).
- Contract: `design_planner.md` §6 item 6 ("A day of a date is not a stat either").

**Implementation:**
1. In the same `stat_callout` branch, after the year check, add the date check exactly as specified in `design_planner.md` §6 item 6:
   - `MONTHS = "january|february|march|april|may|june|july|august|september|october|november|december"`;
   - for an integer value `v` (`decimals == 0`, `display_scale == "none"`), test `re.search(rf"\b(?:{MONTHS})\.?\s+{v}(?:st|nd|rd|th)?\b|\b{v}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:{MONTHS})\b", beat_text, re.IGNORECASE)`;
   - on a match, add exactly `f"props.value: {v} is a day of a date in this beat; a date belongs in a timeline or an era label, not a stat"`.
2. Nothing else changes; the ladder handles the rest.

**Validate:**
- The "dates, placeholders, era stamps" row in `design_testing_and_validation.md` §2.
- **Red first:** `tests/data/wave_f_cases.json` `stat_dates[0]` (value 3, beat "She had died in 2016, and March 3rd was her birthday.") validates today. After the fix, it yields exactly its `expected_error`.
- These must **not** error:
  - 3 in "3 soldiers";
  - 20,000 in "about 20,000 emus";
  - 312 in "The box held 312 handwritten cards".
- **Falsify:** drop the `(?:st|nd|rd|th)?` group → "March 3rd" is red again.

**Blast radius:** `planner/validate.py`, `tests/test_validate.py`.

---

### F2 — No placeholder or instruction text on screen

**What this means for the user:** viewers never see "Icon: Bullet", "Not specified" or "N/A" on a graphic.

**The gap:**
- Nothing rejects meta text.
- The Wave E agent run drew "Icon: Bullet" and "Icon: Bird" as `comparison` points (`emu_war` s017), after E4 put icon names in the prompt.
- It also drew "Not specified" as a comparison side (`story_room_12` s008).
- Wave A had "N/A" ×15 as timeline labels.
- Contract: `design_planner.md` §6 item 7 ("No placeholders or instructions on screen").

**Implementation:**
1. In `planner/validate.py`, add `placeholder_errors(template, props) -> list[str]`. For every `WORD_CAPS[template]` path, in table order and then index order (use `planner/words.field_values`):
   - if `re.search(r"\bicon\s*:", v, re.IGNORECASE)`, emit `f'props.{path}: "{v}" is an instruction, not on-screen text — put icons only in icon fields'`;
   - otherwise, if `re.sub(r"[^\w/ ]", "", v).strip().casefold()` is in `{"not specified", "unspecified", "not mentioned", "n/a", "na", "none", "unknown", "tbd", "no data", "not applicable"}`, emit `f'props.{path}: "{v}" is a placeholder — show only what the beat says'`.
2. Wire it into `validate_scene` after item 9 (word caps), so it applies to LLM output and to `preview` edits alike.
3. `evals/text_audit.py` counts placeholder and instruction errors per fixture; the bar is 0 (`design_planner.md` §9).

**Validate:**
- **Red first:** the two frozen `placeholder_scenes` validate today. After the fix, each yields exactly its `expected_errors`, in order.
- "UNKNOWN IDENTITY" and "No Record Found Yet" yield no error.
- A unit test runs `placeholder_errors` over every scene of every frozen storyboard in `tests/data/` and asserts **0** errors except the two frozen junk scenes. This guards against false alarms.
- **Falsify:** remove `"not specified"` from the set → that case is red.

**Blast radius:** `planner/validate.py`, `evals/text_audit.py`, tests.

---

### F3 — Era stamps show a narration year or nothing

**What this means for the user:** the stamp on a place image is a real year from the story ("1932"), or absent — never "Present Day" on "Last spring" or "Modern Era" on the 1990s.

**The gap:**
- `location.era_label` is free text. Its only checks are digit grounding and "ago" (`planner/validate.py`, `LocationProps` branch).
- 228 of 358 stamps since Wave A contained no year, and were invented. 115 wrapped a real year in extra words ("1932 Era", "1919 Boston").
- A retry-based rule made things worse (§1.4).
- Contract: `design_planner.md` §5 ("Era stamps show a year from the narration, or nothing"); `design_templates.md` §2.13.

**Implementation:**
1. `planner/props.py`: add `normalize_era_label(era: str | None, transcript_text: str) -> str | None`:
   - `None` or empty → `None`;
   - `m = re.search(r"\b(1[0-9]{3}|20[0-9]{2})s?\b", era)`; if `m` and `re.search(rf"\b{m.group(1)}", transcript_text)` → `m.group(0)`;
   - else → `None`.
2. Apply it to every `location` props object the planner produces (primary, alternate, critic retry), **after** text normalisation and **before** `validate_scene`, the same way C8's contact fill is applied. `transcript_text` = the sentence texts joined by single spaces.
3. **Do not** apply it to human edits in `preview`. Deterministic R7 `location` pictures already use `era_label: None`.

**Validate:**
- **Red first:** for every `era_labels` case in `tests/data/wave_f_cases.json`, `normalize_era_label(case.era_label, transcript)` must equal `case.expected`. Expected values:
  - "Present Day" ×3 → null;
  - "Modern Era" → null;
  - "1932 era" ×2 → "1932";
  - "1919 Boston" → "1919";
  - the null stamp stays null.

  The function does not exist today; record the failing test.
- Also: "1960s" with 1960 in the transcript → "1960s"; "1932 era" when 1932 is not in the transcript → null.
- An integration test with a stub backend that returns `era_label: "Present Day"` for a location → the accepted scene has `era_label: null`.
- **Falsify:** apply it only when the label has no digits → "1919 Boston" stays → red.

**Blast radius:** `planner/props.py`, `tests/test_props.py` (or a new test file).

---

### F4 — Re-measure; close-out

**What this means for the user:** measured confirmation, on the four stories, that dates, junk text and invented stamps are gone, and that nothing else regressed.

**Implementation:**
1. **Planner eval**, cold (`--no-llm-cache`) → `docs/evals/planner_<date>.md`. Every `design_planner.md` §9 bar on every fixture:
   - light share ≥ 1/3 (`molasses_flood` has sat exactly at 2/6; if it falls below, file it with numbers);
   - 0 word-cap violations;
   - **0 placeholder/instruction errors**;
   - critic regression 8/8;
   - 0 armchairs.
2. **G12**, including step 9. Extend `evals/verify_e2e_scenes.py` with three columns, each of which must be 0:
   - **date stats** (the F1 condition);
   - **junk text** (the F2 condition);
   - **invented era stamps**: a non-null `era_label` that is not exactly a narration year token.

   **Wire it into `scripts/e2e.sh` as step 10**, failing on any non-zero column, so these checks run every time instead of by hand.
3. **Cold budget** → `docs/evals/budget_<date>.md`; bars ≤ 390 / 210 / 600 s.
4. Open and describe, from the E2E renders:
   - `story_room_12`'s "She had died in 2016, and March 3rd was her birthday." scene and every other "March 3rd" scene (what template and what text now);
   - `story_recipe_box`'s "Last spring, Danny finally sold the house." location (the stamp);
   - `emu_war`'s "That is about ten bullets for every bird." comparison.

**Validate:** the bars above. Exceeding one is filed with numbers, never tuned away.

**Close-out:**
1. Full battery, bare; update §1.3.
2. Rewrite this guide to **Queue Complete**.
3. Move Wave F to §5.1.
4. Update `ongoing_general_errors.md` §1.
5. Stop.

---

## 4. Deferred — do NOT start

- **DF1–DF9** (`ongoing_general_errors.md` §4): video input + PiP, 16:9, multi-voice, live mode, Reddit URL fetch, public-domain photos, historical borders, web editor, cloud LLM.
- **Known limitation, not scheduled:** quote tracking in beat splitting resets at each sentence, so a quotation spanning two sentences can be split between them (C1 verdict).
- **Not scheduled:** the critic's `emotion_beat` *who* reading is noisy. No deterministic who-repair is allowed (§5.5).
- **Not scheduled:** R7 treats reported speech without quotation marks as narration. For example, "He laughed and said I was the closest thing to family that recipe had left." became a neutral narrator reaction shot. This is within R7 as specified; do not change it without a new spec.

---

## 5. Do NOT change

### 5.1 Already delivered

- **Wave A (A1–A22)**, verified September 25, 2026; **Wave B (B1–B17)**, September 26; **Waves C (C1–C8) and D (D1–D5)**, October 3; **Wave E (E1–E6)**, independently verified October 4, 2026. One line per item, with verdicts, is in `ongoing_general_errors.md` §3.
- Items marked "✓" are not reworked. Items marked "→ F<n>" are touched only as that item specifies.

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
- The critic's user message lists the cast without a `Cast:` label; the regression set is 8/8 with it.
- `scripts/battery.sh` exports `HF_HOME` for its own run; the package itself never does.
- **(Oct 4)** E4's icon block is appended after a critic disagreement message when there is one. It reaches the model either way.
- **(Oct 4)** R6 keeps the demoted scene's original alternate even when it equals the new primary (e.g. `stat_callout`/`stat_callout`). A failing scene then falls to the deterministic quote, which is acceptable.

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

**New (October 4, 2026, Wave F):**
- **A date (a year, or a month and day) is never a stat** (E3 + F1).
- **On-screen text is never a placeholder or an instruction** (F2).
- **An era stamp is a narration year or nothing**, normalised deterministically. Human edits are not normalised (F3).

**From Wave E:**
- A rule is enforced on the final scene, not on the retry path. After a critic mismatch, a non-neutral tone or emotion survives only if the critic read the same one. A disputed `kinetic_quote` speaker is removed. These repairs only ever remove a claim.
- An `unknown` emotion reading counts against a strong feeling; an `unknown` *speaker* never counts.
- R7 never replaces a beat containing quoted speech or writing.
- The props prompt shows the icon allow-list for templates with icon fields.
- The package never changes the environment at import.

**From Waves C and D:**
- Quoted speech is never split from its introducing words (unless the sentence exceeds 16 s).
- The critic reads one continuous passage. Text-thread answers are keyed; the critic names the contact. A null `contact_cast_id` is filled only on an exact, unique name match.
- The critic-triggered retry gets 3 attempts; `changed` means the props differ.
- No bible entity id appears in on-screen text. Caption words are laid out at their active size.
- A recorded job-local input that is missing is an error.
- `dialogue` and `text_thread` may paraphrase (Issue 6 → D).
- `WORD_CAPS` is the single source of word caps, the density metric and (from F2) the placeholder scan. The removed fields stay removed.
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
- Counting an `unknown` speaker as a mismatch; a second critic call per scene; re-asking the critic after a retry.
- Removing or skipping the critic or text check to meet the budget.
- Keeping the "context only" framing.
- Assigning the critic's speaker to a scene. (Removing a disputed `kinetic_quote` speaker is allowed and different.)
- Lowering the active caption scale; treating at-limit strings as failures.
- An array schema for per-message answers.
- LLM-chosen emotions for R7 reaction shots; letting R7 replace kept templates.
- Raising `kinetic_quote` above 12 words.
- A words-per-second bar in the simulated-timing planner eval.
- Fixing the armchair by removing or reordering it in the allow-list.
- Rendering four-digit integers without a thousands separator.
- Loosening the light-share bar if `molasses_flood` drops below 1/3.

**New, October 4, 2026:**
- A retry-based era-stamp rule ("a year or words from the beat"). Measured worse: "Two days", "forty years", and a failed 1919 location.
- Removing the icon block to stop "Icon:" text. That brings the armchair back; F2 rejects the text instead.
- A calendar-style counter for dates. A date is not a quantity, and a date-shaped template is new work no user has asked for.

---

## 6. Where the contracts live

| What | Where |
|---|---|
| Pipeline, job layout, job-local inputs, CLI, review gate, local-only policy, pinned models | `design_system_architecture.md` |
| JSON shapes (`plan_report.critic.repair`), generated files, sync gate | `design_data_contracts.md` |
| Ingest, TTS, ASR, loudness, frame math, beat splitting with quoted speech (§7), captions, SFX | `design_audio_and_timing.md` |
| LLM backend; R6/R7 (§4); the props prompt incl. the icon block and **era normalisation (§5)**; validators incl. **a date is not a stat (§6 item 6)**, **no placeholders or instructions (item 7)** and word caps (item 9); eval bars (§9); critic §11 | `design_planner.md` |
| The 16 templates (**§2.13: the era stamp**); the word budget (§5) | `design_templates.md` |
| Palette, composited contrast, captions, illustration + text check | `design_visual_direction.md` |
| Remotion, clock, render CLI, preview, verification | `design_rendering.md` |
| Fixtures, test rows (**dates, placeholders, era stamps**), gates, E2E incl. step 9, offline, cold budget | `design_testing_and_validation.md` |
| Resolved index (Wave E verdicts), lessons 2.1–2.12, deferred items DF1–DF9, decision log | `ongoing_general_errors.md` |
| Live mode, constraints LC1–LC6, and the user's direction for it | `design_future_live_and_video.md` |

---

## 7. Validation standard

- **Red first, on real inputs.** A regression set built only from tidy cases can pass while production fails (lesson 2.6).
- **Measure outcomes by comparing before and after**, and record why a repair did not happen (lesson 2.7).
- **Measure the rendered result, not the style values** (lesson 2.8).
- **Enforce a rule on the final result, not on the path that produced it** (lesson 2.10).
- **Measure the distribution of what the model picks, not just its validity** (lesson 2.11).
- **Name the defect class, test it against every past run, and re-read every template a prompt change reaches** (lesson 2.12).
- A gate must be able to fail, and must fail closed. A perfect score is a reason to look harder. Warm caches measure nothing about a cold budget.
- Read exit codes bare. A gate that did not run is not a pass. Open every artefact and describe it.
- **Never loosen a bar to pass it.** File it with the measurement.

---

## 8. THE LOOP

```
(1) Is there an approved item? Wave F, F1–F4, in §2 order. If all are done,
    STOP. Never start DF1–DF9 or anything not in §3 without a user
    selection. Never fill in a `Your selection:` line.
(2) Read the item and EVERY design section it names. Copy regexes, word
    lists, thresholds and error strings VERBATIM.
(3) RED FIRST on the frozen real case; record the failure.
(4) Build only what the item says. Nothing from §5.5.
(5) GREEN; then falsify (break, see red, restore, see green).
(6) Open every artefact and describe it.
(7) Full battery, bare (HF_HOME exported in the shell). Update §1.3.
(8) ONE commit, scope = item id (`fix(f1): …`). WHY + red/green in the
    body. ONE line under "Wave F" in ongoing_general_errors.md §3,
    citing `git log --grep "(f1)"`. Never amend after pushing.
(9) git push origin main.
(10) Next item.
```

---

## 9. Definition of Done: Wave F

- [ ] F1–F4 each landed as one pushed commit scoped to its id, with red and green runs recorded.
- [ ] The frozen "March 3rd" stat yields its exact error; "3 soldiers", "about 20,000 emus" and "312 handwritten cards" do not.
- [ ] Both frozen junk-text comparisons yield their exact errors, and no other frozen scene in `tests/data/` errors.
- [ ] All eight frozen era stamps normalise to their expected values; the stub integration shows "Present Day" → null.
- [ ] F4: every planner-eval bar (incl. 0 placeholder errors), every E2E step **including the new step 10** (0 date stats, 0 junk text, 0 invented era stamps, plus Wave E's five zeros), and the cold budget bars met or filed.
- [ ] The F4 stills opened and described.
- [ ] §1.3 re-measured this session, read bare.
- [ ] This guide rewritten to **Queue Complete**. **Then stop. Do not invent work.**

# Agent Execution Guide — Queue Complete — independently verified October 4, 2026

**You are an engineering agent with no memory of this project.** Waves A–F are built, committed and pushed (head `c88a69f`), and each has been independently verified. **Nothing is approved to start. Do not invent work.**

On October 4, 2026 a separate session verified Wave F (F1–F4):
- It re-ran every gate and the cold budget bare: all green (§1.3).
- It read every item against its spec: all 4 do what their specs say.
- It read the rendered stories as a viewer. Dates are no longer counters, no placeholder or instruction text reaches the screen, and every era stamp is a narration year or absent.
- The new E2E step 10 was falsified on older output and fails as it should.

Nothing found in that review needs work. §2 lists the watch items; §4 lists the behaviours deliberately left as they are.

**The only legitimate triggers for further work:**
1. the user selects a deferred feature (DF1–DF9, §4) or files a new request;
2. a gate in §1.3 goes red, or a watch item in §2 crosses its bar;
3. a new verification pass files an issue in `docs/ongoing_general_errors.md`.

Absent one of these, **stop**. Never fill in a `Your selection: _____` line.

**Every number and literal string in this document and in the design docs is a decision, not a suggestion.** If you are later given work and a value is genuinely impossible, keep the *intent*, deviate minimally, say so in the commit body, and add it to §5.2. If the design itself cannot work, **STOP and file it in `docs/ongoing_general_errors.md` with options and a `Your selection: _____` line.**

**What the product is, in one paragraph.** A local-only CLI that turns a **text story** (narrated by local TTS in an automatically chosen voice) or an **audio narration** into a **1080×1920 animated explainer video**. It uses flat editorial vector scenes chosen from 16 templates, with word-by-word karaoke captions and few words on the graphics (Issue 7). It has a persistent cast of vector avatars, locally generated illustrations checked for stray lettering, a blind critic for people scenes whose findings are enforced on the final scene, and optional music and SFX. Every video **stops for human review** before the final render. The long-term goal is live mode, so the renderer is clock-agnostic.

---

## 0. Standing constraints (apply to any future item)

1. **The battery is the regression bar.** After every change, run the full battery and update §1.3. **Read every exit code bare.**
2. **Fully local at runtime.** No cloud API, no network except loopback. Pull no new models.
3. **Python (Pydantic) is the source of truth for every contract.** Generated files are never hand-edited.
4. **Templates read time only through the clock.**
5. **The review gate is mandatory.** No auto-approve under any name.
6. **The planner never crashes the pipeline, and never shows text that is:** ungrounded, truncated, id-bearing, over its word cap, a placeholder, an instruction, or a date drawn as a stat. Every LLM call goes through `run_with_retries`.
7. **Red first, on real inputs.** Every change's validation includes a case frozen from real pipeline output, run against the unfixed code first.
8. **One item = one Conventional Commit, scope = item id.** WHY plus red and green runs in the body. Push after every item. Never amend a pushed commit.
9. **Record each resolution in the same commit,** as one line in `ongoing_general_errors.md` §3 citing `git log --grep "(<id>)"`, never a hash.
10. **When a guide and a design doc disagree, stop and file it.**
11. **Nothing in the package changes the process environment at import.** Export `HF_HOME=$HOME/.cache/huggingface` in your shell if needed.
12. **Ids in use:** waves A–F (items A1…F4); deferred features **DF1–DF9**; live-mode constraints **LC1–LC6**. A new wave takes the next letter (G) and must not collide with these.

---

## 1. Verified baseline (October 4, 2026, independent verification session)

### 1.1 Environment

`doctor`: 22 checks OK.
- M4 Max 64 GB; ffmpeg 8.1; Node v26.5.0; Python 3.12 (uv).
- Ollama with `gemma4:26b`; Kokoro 0.9.4; mlx-whisper 0.4.3.
- mflux (`flux2-klein-4b`); Remotion 4.0.528.

The battery was run with `HF_HOME=$HOME/.cache/huggingface` exported in the shell.

### 1.2 Repository

Waves:
- A `4df212a`…`e374a15`
- B `cad065d`…`beb4c4f`
- C/D `12209d2`…`98db684`
- E `26e0f2c`…`66b377f`
- F `084d666`…`c88a69f`

Per-item verdicts: `ongoing_general_errors.md` §3.

### 1.3 Gates (run bare in the verification session; this is the regression bar)

| # | Gate | Result |
|---|---|---|
| G1 | `uv run ruff check .` | exit 0 |
| G2 | `uv run ruff format --check .` | exit 0 · 119 files |
| G3 | `uv run mypy src` | exit 0 · 59 source files |
| G4 | `uv run pytest -q -m "not slow"` | exit 0 · **265 passed** |
| G5 | `npm --prefix renderer run typecheck` | exit 0 |
| G6 | `npm --prefix renderer run lint` | exit 0 |
| G7 | `npm --prefix renderer test` | exit 0 · 16 passed |
| G8 | `./scripts/check_schema_sync.sh` | exit 0 |
| G9 | `./scripts/check_renderer_purity.sh` | exit 0 |
| G10 | `./scripts/check_gallery.sh` | exit 0 · 36 s · 53 goldens, 0 overflows, caption spacing verified |
| G11 | `uv run pytest -q -m slow` | exit 0 · **37 passed** · 205 s |
| G12 | `./scripts/e2e.sh` | exit 0 · 859 s · **steps 1–10 pass**. Sync probe 9/9. Step 9: 0.52–0.83 graphic words/s, light share 4/9–15/28. Step 10: 0 in every column (flagged tones, disputed quote speakers, quoted beats replaced, year stats, date stats, junk text, invented era stamps, armchairs) |
| G13 | `./scripts/check_offline.sh` | exit 0 · 235 s |
| G14 | `uv run infographics doctor` | exit 0 · 22 checks OK |
| Budget | `./scripts/measure_budget.sh` (cold, `story_recipe_box`) | exit 0 · **0 cache hits** · `new`→review **205.8 s** (≤ 390) · render **191.3 s** (≤ 210) · total **397.1 s** (≤ 600) · 57 LLM calls |

---

## 2. Watch items (no work; act only if one crosses its bar)

| Watch item | Current | Bar | If it crosses |
|---|---|---|---|
| Cold-budget render span | 191.3 s here; 196.2–200.2 s in other October 4 runs | ≤ 210 s | File it in `ongoing_general_errors.md` with the numbers; do not raise the bar or cut frames |
| `molasses_flood` light share in the planner eval (simulated timing) | 2/6 = exactly 1/3 in every eval since Wave D | ≥ 1/3 | File it; do not loosen the bar (§5.5) |
| Same-day eval reports | `docs/evals/<kind>_<date>.md` is overwritten when two runs land on one date | — | Git history keeps every committed version. A verifier who runs the E2E or budget must restore the committed reports afterwards (`git checkout -- docs/evals/`) and record their own numbers in this guide |

---

## 3. The items

**None.** The queue is empty. Do not start anything without one of the triggers above.

---

## 4. Deferred and deliberately unscheduled — do NOT start

- **DF1–DF9** (`ongoing_general_errors.md` §4): video input + PiP, 16:9, multi-voice, live mode, Reddit URL fetch, public-domain photos, historical borders, web editor, cloud LLM. Each needs a user selection.
- **Known limitation:** quote tracking in beat splitting resets at each sentence, so a quotation spanning two sentences can be split between two beats (C1 verdict).
- **Known limitation:** the critic's `emotion_beat` *who* reading is noisy. It named a different person on 7 of 13 real beats. No deterministic who-repair is allowed (§5.5).
- **Known limitation:** R7 treats reported speech without quotation marks as narration. For example, "He laughed and said I was the closest thing to family that recipe had left." becomes a neutral narrator reaction shot. This is within R7 as specified.
- **Observed, not a defect:** a comparison can infer an unstated side, e.g. "Today: Higher price" for "which was our price in the 1990s". Numbers are grounded; the inference is the planner's. Leave it unless a new spec asks.

---

## 5. Do NOT change

### 5.1 Already delivered

- **Wave A (A1–A22)**, verified September 25, 2026.
- **Wave B (B1–B17)**, September 26.
- **Waves C (C1–C8) and D (D1–D5)**, October 3.
- **Wave E (E1–E6)** and **Wave F (F1–F4)**, October 4.
- All were independently verified. One line per item, with verdicts, is in `ongoing_general_errors.md` §3. Nothing marked "✓" is reworked.

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
- E4's icon block is appended after a critic disagreement message when there is one.
- R6 keeps the demoted scene's original alternate even when it equals the new primary. A failing scene then falls to the deterministic quote of its sentence, as "She had died in 2016, and March 3rd was her birthday." does.
- **(Oct 4)** F3's era normalisation runs before the length check. So "January 15, 1919" becomes "1919" instead of failing, which is better than the spec's minimum.

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

**Wave F (October 4, 2026):**
- A date (a year, or a month and day) is never a stat.
- On-screen text is never a placeholder or an instruction.
- An era stamp is a narration year or nothing, normalised deterministically; human edits are not normalised.
- E2E step 10 enforces these and Wave E's criteria on every run.

**Wave E:**
- A rule is enforced on the final scene, not on the retry path. After a critic mismatch, a non-neutral tone or emotion survives only if the critic read the same one. A disputed `kinetic_quote` speaker is removed. These repairs only ever remove a claim.
- An `unknown` emotion reading counts against a strong feeling; an `unknown` *speaker* never counts.
- R7 never replaces a beat containing quoted speech or writing.
- The props prompt shows the icon allow-list for templates with icon fields.
- The package never changes the environment at import.

**Waves C and D:**
- Quoted speech is never split from its introducing words (unless the sentence exceeds 16 s).
- The critic reads one continuous passage. Text-thread answers are keyed; the critic names the contact. A null `contact_cast_id` is filled only on an exact, unique name match.
- The critic-triggered retry gets 3 attempts; `changed` means the props differ.
- No bible entity id appears in on-screen text. Caption words are laid out at their active size.
- A recorded job-local input that is missing is an error.
- `dialogue` and `text_thread` may paraphrase (Issue 6 → D).
- `WORD_CAPS` is the single source of word caps, the density metric and the placeholder scan. The removed fields stay removed.
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
- Fixing the armchair by removing or reordering it in the allow-list; removing the icon block to stop "Icon:" text.
- Rendering four-digit integers without a thousands separator; a calendar-style counter for dates.
- A retry-based era-stamp rule.
- Loosening the light-share bar or the render bar to pass.

---

## 6. Where the contracts live

| What | Where |
|---|---|
| Pipeline, job layout, job-local inputs, CLI, review gate, local-only policy, pinned models | `design_system_architecture.md` |
| JSON shapes (`plan_report.critic.repair`), generated files, sync gate | `design_data_contracts.md` |
| Ingest, TTS, ASR, loudness, frame math, beat splitting with quoted speech (§7), captions, SFX | `design_audio_and_timing.md` |
| LLM backend; R6/R7 (§4); the props prompt, icon block and era normalisation (§5); validators incl. dates (§6 item 6), placeholders and instructions (item 7), ids (item 8), word caps (item 9); eval bars (§9); critic §11 | `design_planner.md` |
| The 16 templates; the word budget (§5) | `design_templates.md` |
| Palette, composited contrast, captions, illustration + text check | `design_visual_direction.md` |
| Remotion, clock, render CLI, preview, verification | `design_rendering.md` |
| Fixtures, test rows, gates, **E2E steps 1–10**, offline, cold budget | `design_testing_and_validation.md` |
| Resolved index (all verdicts), lessons 2.1–2.12, deferred items DF1–DF9, decision log | `ongoing_general_errors.md` |
| Live mode, constraints LC1–LC6, and the user's direction for it | `design_future_live_and_video.md` |

---

## 7. Validation standard (for any future work)

- **Red first, on real inputs** (lesson 2.6).
- **Measure outcomes by comparing before and after** (lesson 2.7).
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
(1) Is there an approved item? NO: the queue is empty. STOP.
    Only a trigger at the top of this guide starts new work, and new work
    first gets a spec (a new wave in this guide) before any code.
    Never start DF1–DF9 without a user selection.
    Never fill in a `Your selection:` line.
(2)–(10) For future waves: read the item and every design section it
    names; red first on a frozen real case; build only what it says;
    green, then falsify; open every artefact; full battery bare; one
    commit scoped to the item id with WHY + red/green; one resolution
    line in ongoing_general_errors.md §3; push.
```

---

## 9. Status

- [x] Waves A–F delivered, each as one commit per item, and independently verified.
- [x] §1.3 measured bare in the October 4, 2026 verification session.
- [x] No open issue and no pending user selection in `ongoing_general_errors.md`.
- [x] Queue Complete. **Stop. Do not invent work.**

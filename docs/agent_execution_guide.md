# Agent Execution Guide — Active Build: Wave B (verification fixes + Issues 3–5, 17 items) — September 25, 2026

**You are an engineering agent with no memory of this project.** The offline MVP (Wave A, A1–A22) is built, committed and pushed (head `e374a15`). On September 25, 2026 an independent verification pass re-ran every gate and read the source against the design. **All 14 gates reproduce green — and the product still has defects that no gate could see.** The worst:
- every reviewed-and-edited video loses its music and sound effects;
- about one scene in five shows text cut off mid-word;
- two planner crash paths exist;
- captions over light illustrations and the map are unreadable.

The same day, the user selected fixes for three quality issues:
- **Issue 3:** a local check for fake writing in illustrations, which tolerates text when the description calls for it;
- **Issue 4:** real dates or a fixed list of relative-time phrases on timelines;
- **Issue 5:** two meaning rules plus a blind "critic" for people scenes.

All three designs were **measured before being specced** (numbers in §1.4).

**What is approved:** Wave B, items **B1–B17** in §3, in the order of §2. **What NOT to touch:** everything in §5. **What must not be started:** everything in §4.

**Every number and literal string in this document and in the design docs is a decision, not a suggestion.** Implement as written; do not substitute your own values. That includes prompts, word lists, thresholds and seeds. If a value is genuinely impossible, keep the *intent*, deviate minimally, say so in the commit body, and add it to §5.2. If the design itself cannot work, **STOP and file it in `docs/ongoing_general_errors.md` with options and a `Your selection: _____` line. Do not improvise, and never fill in a selection line yourself.**

**What the product is, in one paragraph.** A local-only CLI that turns a **text story** (narrated by local TTS in an automatically chosen voice) or an **audio narration** into a **1080×1920 animated explainer video**. It uses flat editorial vector scenes chosen from 16 templates, in sync with the voice, with word-by-word karaoke captions, a persistent cast of vector avatars, locally generated illustrations, and optional music and SFX. Every video **stops for human review** before the final render. The long-term goal is live mode, so the renderer is clock-agnostic.

**The lesson that shaped this wave.** Green gates were not evidence of correctness: every defect above passed every gate. **For every item, the validation includes the check that would have caught the original defect**, and you run it against the unfixed code first and see it fail.

---

## 0. Standing constraints (apply to every item)

1. **The battery is the regression bar.** After every item, run `scripts/battery.sh` (full) and update §1.3. **Read every exit code bare.**
2. **Fully local at runtime.** No cloud API, no network except loopback (`design_system_architecture.md` §7). The critic and the text check use the **already-installed** `gemma4:26b`; pull nothing new.
3. **Python (Pydantic) is the source of truth for every contract.** Generated files (`schema/`, `renderer/src/generated/`, `data/geo/country_bboxes.json`, and from B12 `renderer/public/geo/lakes-50m.json`) are never hand-edited.
4. **Templates read time only through the clock** (`design_rendering.md` §3).
5. **The review gate is mandatory.** No auto-approve under any name.
6. **The planner never crashes the pipeline and never shows an ungrounded or truncated fact.** **Every LLM call goes through `run_with_retries`**: voice, bible, segment, select, props, critic, text_check.
7. **Red first.** Before fixing an item, write or run its falsifying check against the *current* code and record the failure. For new capabilities (B5, B6, B10), write the tests first and record them failing.
8. **One item = one Conventional Commit whose scope is the item id**, e.g. `fix(b1): keep music and sfx across preview and rerun`. The WHY goes in the body, with the red and green runs. **Push after every item** (`git push origin main`). **Never amend a pushed commit.**
9. **Record the resolution in the same commit:** one line under "Wave B" in `ongoing_general_errors.md` §3, in the form `B<n> — <title> — git log --grep "(b<n>)" — <measured result>`, **never a hash** (tracking doc §2.5). When B5, B6 or B10 lands, also collapse Issue 4, 5 or 3 (the "Selected, specced" blocks in §1 of the tracking doc) into one §3 line that keeps the user's selection text verbatim.
10. **When this guide and a design doc disagree, stop and file it.**
11. Every stage writes `logs/<stage>.log` ending in `llm_calls=<n> cache_hits=<m> elapsed_ms=<t>`; the LLM call counter is incremented at the backend's entry point.

---

## 1. Verified baseline (September 25, 2026)

### 1.1 Environment (verified)

| Fact | Value |
|---|---|
| Machine | Apple **M4 Max**, **64 GB**, macOS (Darwin 25.6.0) |
| ffmpeg / Node / Python | 8.1 · **v26.5.0** (Remotion works on it) · project **3.12** via uv |
| Ollama | 0.33.0 · **`gemma4:26b`** (id `08ae7ec1744b`, 18 GB); accepts image input (used by B10) |
| Kokoro / mlx-whisper / pydantic / espeak-ng | 0.9.4 / 0.4.3 / 2.13.5 / 1.52.0 |
| mflux | **0.20.0**. It ships `mflux-generate-flux2` (`--model flux2-klein-4b`), and **no `mflux-generate-flux2-klein` executable**. Wave A's `setup.sh` symlinked that name in `~/.local/bin` (removed by B9). Only **4B** klein weights are on the machine. |
| Remotion | 4.0.528 (all packages identical) |

### 1.2 Repository

- Wave A: 22 commits `4df212a`…`e374a15`.
- Verification docs: `5381de7`.
- Design contracts were revised twice on September 25, 2026: once for the verification findings, once for the Issue 3–5 selections. The list is in `ongoing_general_errors.md` §5.
- New frozen fixtures: `fixtures/vision/` (7 labelled images + `labels.json`), included in `fixtures/CHECKSUMS`.

### 1.3 Gates (run bare in the verification session)

| # | Gate | Result |
|---|---|---|
| G1 | `uv run ruff check .` | exit 0 |
| G2 | `uv run ruff format --check .` | exit 0 · 99 files |
| G3 | `uv run mypy src` | exit 0 · 53 source files |
| G4 | `uv run pytest -q -m "not slow"` | exit 0 · **171 passed** |
| G5 | `npm --prefix renderer run typecheck` | exit 0 |
| G6 | `npm --prefix renderer run lint` | exit 0 |
| G7 | `npm --prefix renderer test` | exit 0 · **15 passed** (4 files) |
| G8 | `./scripts/check_schema_sync.sh` | exit 0 |
| G9 | `./scripts/check_renderer_purity.sh` | exit 0 (the exemption is too broad → B13) |
| G10 | `./scripts/check_gallery.sh` | exit 0 · 35 s · 51 goldens, hold motion on 17 entries (the overflow check fails open → B13) |
| G11 | `uv run pytest -q -m slow` | exit 0 · **18 passed** · 178 s |
| G12 | `./scripts/e2e.sh` | exit 0 · 847 s (asserts neither music/SFX nor a computed sync count → B1, B16; timings are warm-cache → B17) |
| G13 | `./scripts/check_offline.sh` | exit 0 · 198 s · self-checks pass; fresh-cache `molasses_flood` reached review in **122.5 s** (planning 27 s, 4 images 83 s) |
| G14 | `uv run infographics doctor` | exit 0 · 21 checks OK |

### 1.4 Design-time measurements for the selected issues (September 25, 2026, `gemma4:26b`)

These are the numbers the specs were built from. Your slow tests must reproduce them; if they do not, **file it**, do not tune the thresholds.

| What | Result |
|---|---|
| Text check, **final prompt** (`design_visual_direction.md` §7.1), on `fixtures/vision/` | **7/7 correct on seed 7 and on seed 8**; max 0.9 s per image |
| Text check, naive yes/no prompt (**rejected**) | flagged **2 of 4** clean place images ("a symbol ∕") |
| Text check without an output cap (**rejected**) | one request exceeded a 300 s timeout |
| "Description calls for text" list, on the 145 descriptions from Wave A's E2E runs | exempts recipe cards, a handwritten note, envelopes, a crossword book; bare "sign" had to be removed (it matched "showing **signs** of structural weakness") |
| Critic regression set (`design_planner.md` §11), seeds 7, 8, 9 | **4/4 on every seed**; ~0.5 s per call |

---

## 2. Execution order

| # | Item | Why this position |
|---|---|---|
| B1 | Music and SFX survive the review journey | The most visible defect; independent. |
| B2 | LLM error classification | Small; B3–B7 run the planner many times, and a spurious "missing model" crash would waste those runs. |
| B3 | Planner crash containment | Every later planner item (critic retries, eval re-run) relies on `run_with_retries` being the only call path. |
| B4 | Grounding: scale words | Changes which props validate; must precede the B7 eval. |
| B5 | Timeline date labels (**Issue 4**) | A validator change; must precede the B7 eval. |
| B6 | Meaning rules + people-scene critic (**Issue 5**) | Needs B3's retry path and adds `num_predict`; must precede the B7 eval so it measures the critic. |
| B7 | LLM-facing schemas without length limits + text completeness + **planner eval re-run** | Changes every planner output. The one expensive eval re-run covers B3–B7. |
| B8 | Contact sheet flags failed images | B10's "failed after 3 attempts" images must be visible at review. |
| B9 | Invoke mflux directly; drop the `~/.local/bin` symlink | B10 regenerates with explicit seeds through this call; fix the invocation first. |
| B10 | Illustration text check with retry (**Issue 3**) | Needs B2/B3 (retry path), B8 (flags), B9 (invocation, seed parameter). |
| B11 | Legible text over images; captions through FitText | Changes goldens. Back to back with B12. |
| B12 | Map legibility; `kinetic_quote` attribution avatar | Changes goldens; adds a generated geo file (G8). |
| B13 | Gates fail closed; bundle hygiene | Hardens G9/G10 after the goldens settle. |
| B14 | Remove the dead SFX scheduler | Cleanup; changes the G4 count exactly. |
| B15 | README accuracy | Describes the behaviour B1–B14 produced (including the critic and the text check). |
| B16 | E2E: computed counts, audible music | Final E2E shape. |
| B17 | Cold-cache performance budget; close-out | Measures the finished system, **including the critic and text-check costs**; closes the wave. |

---

## 3. The items

### B1 — Music and SFX survive the review journey

**What this means for the user:** today, if they change anything at the review gate, the final video silently loses its music and every sound effect.

**The gap:**
- `src/animated_infographics/stages/compile.py:36-55` takes music and SFX from `ctx.music_path` / `ctx.sfx_dir`, with an "already exists" fallback.
- `jobs.py:41` registers `audio/music.wav` and `audio/sfx` as compile outputs, so `invalidate_after()` deletes them.
- `cli.py:286` (`preview`) and `:429` (`rerun`) build a bare `RunContext()`.
- Reproduced: after `preview`, the final `timeline.audio.music == null` and `sfx == []`, while `input/test_bed.wav` and `input/sfx/` exist.
- Contract: `design_system_architecture.md` §4, `design_audio_and_timing.md` §1.

**Implementation:**
1. Add `music: str | None` and `sfx_dir: str | None` (job-relative) to the ingest record model in `contracts/models.py`; export (G8).
2. `stages/ingest.py` records `"input/<music filename>"` / `"input/sfx"` when the run context carries them (only `new` does), else `null`.
3. `stages/compile.py` reads `ingest.json` and on **every** run calls `prepare_music(job.dir / music, audio/music.wav)` and `prepare_sfx(job.dir / sfx_dir, audio/sfx)` when set. Delete the `ctx` reads and the "already exists" fallbacks.
4. A unit test greps `src/animated_infographics/` for `music_path` / `sfx_dir` attribute reads on a `RunContext`, allowing only `cli.py` and `stages/ingest.py`.
5. `jobs.py:55`: add `"ingest.json"` to `STAGE_INPUT_DEPENDENCIES["compile"]`.
6. `scripts/e2e.sh` step 4: after `render`, assert `timeline.audio.music` non-null, `audio.sfx` non-empty, and that `audio/music.wav` and ≥ 1 `audio/sfx/*.wav` exist.

**Validate:**
- **Red first** (unit test + E2E assertion on the unfixed code).
- Unit: build a job whose `ingest.json` names music and SFX → compile → `invalidate_after("storyboard")` → compile with `RunContext()` → music non-null, SFX non-empty.
- The journey `new … --music … --sfx-dir …` → edit → `preview` → `approve` → `render` holds step 6's assertions.
- **Falsify:** restore the `ctx.music_path` read → red.

**Blast radius:** `contracts/models.py`, `schema/`, `renderer/src/generated/`, `stages/ingest.py`, `stages/compile.py`, `jobs.py`, `scripts/e2e.sh`, tests.

---

### B2 — LLM error classification

**What this means for the user:** today, a caption like "the recipe card was not found" makes the tool claim the planner model is missing and quit.

**The gap:** `planner/llm.py:161` raises `DependencyMissing` when the response text contains "not found", even on a 200 response. Reproduced with `httpx.MockTransport`. Contract: `design_planner.md` §1 ("Error classification").

**Implementation:**
- Only when `status != 200`: a 404, or a JSON `error` naming a missing model → `DependencyMissing` (exit 4); any other non-200 → `LLMResponseError(ValueError)`, which is a failed attempt inside `run_with_retries`.
- A 200 response is never inspected beyond `message.content`.

**Validate:** the `planner/llm.py` rows in `design_testing_and_validation.md` §2 (a 200 containing "not found" → parsed JSON; 404 → exit 4; 500 → failed attempt). **Red first** with the 200 case. **Falsify:** re-add the substring check → red.

**Blast radius:** `planner/llm.py`, `tests/test_llm.py`.

---

### B3 — Planner crash containment

**What this means for the user:** today, one malformed reply from the model crashes planning instead of falling back.

**The gap:** `planner/props.py:223-260` and `planner/select.py:246-300` run their own retry loops, calling `backend.generate_json` (`props.py:233`, `select.py:256`) outside any try. Reproduced: truncated JSON → `JSONDecodeError` escapes. They also omit the previous output as an `assistant` message (`design_planner.md` §1).

**Implementation:**
1. `plan_single_template_props` and each selection window call `run_with_retries(...)`. Their existing checks become the `validate` callables, returning `(dict, errors)`. `attempts` for `plan_report.json` come from the returned list.
2. The fallbacks stay exactly as they are.
3. A unit test asserts `generate_json(` appears under `src/animated_infographics/planner/` only in `llm.py`. Corroborate with the count of `run_with_retries(` call sites: **5** after B3 (voice, bible, segment, select, props); **6** after B6 adds the critic; **7** after B10 adds `text_check`, which lives in `assets/`, so count it there. Each of those items updates the number.

**Validate:** the "planner crash containment" row (every reply truncated → the storyboard completes with `fallback_level: 2`). **Red first.** **Falsify:** one direct `generate_json` → the grep test is red. Scene-count parity: one scene per beat on all four fixtures.

**Blast radius:** `planner/props.py`, `planner/select.py`, tests.

---

### B4 — Grounding: scale words are not numbers on their own

**What this means for the user:** today, a wrong "1 million" could appear on screen and pass the fact check.

**The gap:** `planner/grounding.py:101` treats `thousand`/`million`/`billion` as standalone numbers. `numbers("holding 2.3 million gallons")` returns `[2.3, 2300000.0, 1000000.0]`. Contract: `design_planner.md` §8.

**Implementation:** a scale word contributes a value only inside a spelled run (`two million`) or after a leading `a` (`a million`); after a digit number it only scales it.

**Validate:** the "grounding scale words" row, **red first**; all existing grounding tests still pass. **Falsify:** revert → red.

**Blast radius:** `planner/grounding.py`, `tests/test_grounding.py`.

---

### B5 — Timeline date labels (Issue 4 → Option A)

**What this means for the user:** timelines show real dates from the story, or a clear "when" phrase ("Last spring", "Months later"), never nonsense like "No Record", three copies of "2013", or years running backwards.

**The gap:**
- `planner/validate.py:281-286` only checks that the digits a label contains are grounded (`grounding.py:216` `digits_grounded`). A label with no digits passes, and nothing checks distinctness or order.
- Wave A's `story_recipe_box` shipped `2013 / 2013 / 2013`, `50+ Years / No Record / Memory Only` and `Last Spring / Present / Now`.
- Contract: the date-label row of `design_planner.md` §8; `design_templates.md` §2.16.

**Implementation:**
1. `planner/validate.py`: add `RELATIVE_TIME_LABELS: Final[frozenset[str]]` with **exactly** these 17 strings: `today`, `now`, `present day`, `that night`, `that weekend`, `the next day`, `days later`, `weeks later`, `months later`, `years later`, `last spring`, `last summer`, `last fall`, `last winter`, `last year`, `earlier`, `later`.
2. `normalize_date_label(s)`: casefold, collapse whitespace, strip, then strip trailing `.`, `,`, `!` and `:`.
3. `timeline_label_errors(events, transcript_text) -> list[str]`:
   - (a) per label: it must contain ≥ 1 digit run with `digits_grounded(...)` true, **or** its normalised form must be in `RELATIVE_TIME_LABELS`;
   - (b) normalised labels are pairwise distinct;
   - (c) the first four-digit year per label (`\b(1[0-9]{3}|20[0-9]{2})\b`), in event order, is non-decreasing.
   - Error strings:
     - `props.events[1].date_label: "No Record" is not a date from the narration or an allowed phrase`
     - `props.events: date labels repeat ("2013")`
     - `props.events: years go backwards (1934 → 1932)`
4. Replace the digits-only check at `validate.py:284` with a call to it (the same function serves the planner and `preview`).
5. Update `timeline`'s `writing_rules` in `contracts/templates.py` to state: `date_label is a date or year said in the narration, or exactly one of: Today, Now, Present day, That night, That weekend, The next day, Days later, Weeks later, Months later, Years later, Last spring, Last summer, Last fall, Last winter, Last year, Earlier, Later`, and `labels all differ and run forward in time`. Re-export (G8).

**Validate:**
- The "timeline labels" row in `design_testing_and_validation.md` §2: every listed reject and accept case, including the three Wave A examples.
- **Red first:** the three Wave A examples are accepted by the current validator; record that.
- **Falsify:** remove the distinctness check → `["2013","2013","2013"]` is accepted → red.
- The planner-eval effect is measured in B7.
- **Collapse Issue 4** into §3 of the tracking doc in this commit.

**Blast radius:** `planner/validate.py`, `contracts/templates.py` + exports, tests.

---

### B6 — Meaning rules + people-scene critic (Issue 5 → Option A)

**What this means for the user:** the video stops crediting a line to the wrong person, giving a plain "Rose?" an angry tone, calling a 40-year-old diner "40 years ago", or putting "$" after a number.

**The gap:**
- No validator can see meaning errors. In the Wave A E2E job `story-recipe-box-20260925-180627`: `s012` credits Danny's text to the narrator; `s015` makes "Rose?" angry; `s004` stamps "40 years ago"; one `stat_callout` elsewhere used suffix `$`.
- Contract: `design_planner.md` §6 item 6 (rules) and §11 (critic); `design_data_contracts.md` §6 (`plan_report` `critic` field).

**Implementation:**
1. **Rules** in `planner/validate.py` (inside `validate_scene`, so human edits get them too):
   - `stat_callout.suffix` containing `$`, `£` or `€` → `props.suffix: currency symbols belong in prefix`;
   - `location.era_label` containing the whole word "ago" when the transcript does not → `props.era_label: "ago" is not in the narration`.
2. **Backend:** `generate_json` and `run_with_retries` gain `num_predict: int | None`, which overrides 2048 and is part of the cache key (`design_planner.md` §1).
3. **`planner/critic.py`:**
   - `needs_critic(scene) -> bool`: `dialogue`, `text_thread`, `emotion_beat`; `kinetic_quote` only with an `attribution_cast_id`.
   - `build_critic_request(scene, beat, prev_beat, next_beat, bible) -> (system, user, schema)`: the system line, cast-list format, context labels, the four questions **verbatim** and the four schemas from §11, with id enums narrowed to the bible's cast. **Blind:** never include the proposed speaker, sender, tone or emotion.
   - `validate_critic_answer(scene, answer) -> (answer, errors)`: `lines` / `messages` length must equal the props' length.
   - `critic_mismatches(scene, answer, bible) -> list[str]`: exactly the three rules in §11 (`unknown` who → never a mismatch; `narration` agrees only with the narrator's id; dialogue tone `unknown` → mismatch unless the props say `neutral`; emotion `unknown` → no mismatch). Strings look like `lines[0].tone: angry vs unknown`.
4. **`planner/props.py`:** after a candidate passes `validate_scene` (level 0 or 1) and `needs_critic` is true:
   - Run `run_with_retries(stage="critic", num_predict=256, …)` with `temperature` 0.
   - On mismatches, re-request the **same template's** props through `run_with_retries(stage="props", …)` with the §11 disagreement message appended **verbatim**, filled with the mismatch list.
   - If the new props pass `validate_scene`, they replace the scene (`changed: true`); otherwise keep the original.
   - **Never call the critic twice for one scene.** A critic that fails entirely → accept, `status: "unavailable"`.
5. **`contracts/models.py`:** `PlanReportScene.critic` = `{status, mismatches, changed}` per `design_data_contracts.md` §6; export (G8).
6. **`preview/storyboard.md`** flags column: add `critic changed` or `critic unavailable` where applicable. Informational only; the contact-sheet strip colour is unchanged.
7. **`evals/planner.py`:**
   - Per fixture: critic calls, mismatches, `changed` count.
   - A **regression-set** section that runs the four cases of §11 (cast `c1 Me (narrator)`, `c2 Danny`, `c3 Walt`, `c4 Deb`, and the beat texts from the §11 table) and prints each result.

**Validate:**
- **Red first:** a unit test feeding Wave A's `s012` props (Danny's text attributed to `c1`) through the current planner path with a stub critic answering `c2` must fail today. It fails because no critic exists and the scene is accepted.
- Unit: the "meaning rules" and "critic rules" rows in `design_testing_and_validation.md` §2, including the call-count assertions (one retry, no second critic call).
- Slow: the regression set is 4/4 (the §1.4 measurement).
- **Falsify:** make the tone rule ignore `unknown` → case B is accepted → red. Make `unknown` who count as a mismatch → case C is flagged → red.
- **Collapse Issue 5** in this commit.

**Blast radius:** `planner/validate.py`, `planner/critic.py` (new), `planner/props.py`, `planner/llm.py`, `contracts/models.py` + exports, `preview.py`, `evals/planner.py`, tests. The B3 grep count becomes 6.

---

### B7 — LLM-facing schemas without length limits; text completeness; planner eval re-run

**What this means for the user:** today, about one scene in five shows text chopped off mid-word ("Rescuers wade through waist-", "Modern Era (").

**The gap:**
- `planner/props.py:194`, `planner/bible.py:22` and `planner/voice.py:101` send schemas with `maxLength` as the Ollama `format`. Constrained decoding force-closes the strings.
- Measured over the 177 unique scenes in `artifacts/e2e/*`: **34 of 701 strings sit at their `maxLength` with no terminal punctuation; 21 contain newlines.**
- This is why `docs/evals/planner_2026-09-25.md` shows a 0.0% fallback rate.
- Contract: `design_planner.md` §1 (LLM-facing schemas) and §6 item 7 (text completeness).

**Implementation:**
1. `planner/llm.py`: `llm_facing_schema(schema)` recursively removes `maxLength`, `minLength`, `maxItems`, `minItems` and `pattern` (properties, `items`, `$defs`, `anyOf`/`oneOf`); `enum`, `type`, `required` and `additionalProperties` stay. Apply it **inside `OllamaBackend.generate_json`**, before the payload and the cache key.
2. Retry messages name the field, its length and its limit, and ask for "a complete phrase".
3. `planner/validate.py`:
   - `normalize_text(s)` (collapse whitespace incl. `\n`, strip), applied to free-text fields before validation in `props.py` and again in `compile.py` before writing `timeline.json`;
   - `text_complete_errors(path, s)` per §6 item 7, on `title`, `subtitle`, `text`, `caption`, `descriptor`, `traits[]`, `label`, `heading`, `points[]`, `kicker`, `contact_name`, `messages[].text`, `lines[].text`, `events[].label`, `markers[].label`, `edges[].label` and a non-empty `suffix`. Not on ids, enums, `prefix`, `date_label` (B5 owns it) or `era_label`.
4. `evals/text_audit.py`: over a set of `storyboard.json` files, count strings at exactly their `maxLength` without terminal punctuation, strings containing `\n`, and completeness failures. Print JSON.
5. **Re-run the planner eval** (`--no-llm-cache`) → a new `docs/evals/planner_<date>.md` that includes the text-audit section, the critic section (B6) and the regression set.

**Validate:**
- **Red first:** `text_audit.py` over the existing `artifacts/e2e/*/jobs/**/storyboard.json` reproduces the 34 / 21 counts.
- Unit: the "text completeness" row, and a schema-walk test proving no length keys survive for any template, the bible, voice, critic or text-check schema.
- After the eval: **0 newline strings, 0 completeness failures**, and 0 timeline-label violations (B5). Record the at-limit count; each remaining one must end in punctuation.
- Every `design_planner.md` §9 bar holds, including the critic regression set 4/4. **A rise in fallbacks is honest; if a bar fails, file it with the numbers. Never loosen it.**
- **Falsify:** bypass `llm_facing_schema` → the schema-walk test is red.

**Blast radius:** `planner/llm.py`, `planner/validate.py`, `planner/props.py`, `compile.py`, `evals/text_audit.py`, `docs/evals/planner_<date>.md`, tests. Record the prompt SHA-256s in the eval report.

---

### B8 — The contact sheet flags failed images

**What this means for the user:** a scene whose illustration failed (including B10's "lettering in 3 attempts") is marked red at review, not hidden in a JSON file.

**The gap:** `stages/preview.py:52-64` flags only overflow ∪ fallback. `design_rendering.md` §7 also requires failed images; `report.json` lists them (`preview.py:322-336`) but nothing uses them.

**Implementation:**
- Flagged scenes = overflow ∪ `fallback_level 2` ∪ scenes whose `place_id`/`set_piece_id` names a manifest entity with `status: "failed"`.
- `storyboard.md` flags gain `image failed`.
- `report.json` also carries B10's `text_check: "unavailable"` entities under `warnings`, not as failures.

**Validate:** a unit test with a manifest marking `v1` failed and a `set_piece` scene on `v1`: that tile's label strip pixel is `#FF6B8B`, and its row says `image failed`. **Red first**; **falsify** by removing the new set → red.

**Blast radius:** `stages/preview.py`, `preview.py`, tests.

---

### B9 — Invoke mflux directly; drop the symlink

**What this means for the user:** setup stops writing into their home directory, and image generation calls the tool that actually exists.

**The gap:**
- `scripts/setup.sh:35-38` symlinks `~/.local/bin/mflux-generate-flux2-klein` → `mflux-generate-flux2`.
- `assets/illustrate.py:34` (`TOOL_NAME`) and `:182-183` rely on that name and claim it was "verified with `mflux-generate-flux2-klein --help`".
- `doctor.py:164-170` accepts either name.
- `generate()` (`illustrate.py:131`, `:178`) always derives its seed from the prompt, so B10 cannot request seed + 1.

**Implementation:**
1. `TOOL_NAME = "mflux-generate-flux2"`, invoked with `--model flux2-klein-4b` (unchanged `MODEL_NAME`).
2. `generate(prompt, out, *, seed: int | None = None, timeout_s)`: `None` means `image_seed(prompt)`. **The seed actually used is part of the cache key.**
3. `setup.sh`: stop creating the symlink; remove it if it exists and points at `mflux-generate-flux2`.
4. `doctor`: `mflux-generate-flux2` on PATH **and** its `--help` output contains `flux2-klein-4b`.
5. Update `design_visual_direction.md` §7's `Tool` row and `design_system_architecture.md` §8 to say mflux 0.20.0 exposes klein through `mflux-generate-flux2 --model flux2-klein-4b`.

**Validate:**
- `doctor` with a PATH lacking mflux → exit 4.
- A unit test: `cache_key` differs for seeds s and s+1 with the same prompt.
- Slow: one generation succeeds through the new command. Caches invalidate once; expected.
- After `setup.sh`, `~/.local/bin/mflux-generate-flux2-klein` does not exist.
- **Falsify:** drop the seed from the cache key → the unit test is red.

**Blast radius:** `assets/illustrate.py`, `scripts/setup.sh`, `doctor.py`, two design docs, tests.

---

### B10 — Illustration text check with automatic retry (Issue 3 → Option A)

**What this means for the user:** illustrations no longer show fake lettering, except where the story calls for writing (recipe cards, a handwritten note), which the user explicitly allowed.

**The gap:** nothing checks generated images. Wave A's recipe-box image carries pseudo-handwriting ("Peclpte De fonts ann"). The contract is `design_visual_direction.md` §7.1, which is authoritative for every literal below.

**Implementation:**
1. **Backend** (`planner/llm.py`): `generate_json`/`run_with_retries` gain `images: list[bytes] | None`. Each image is base64-encoded into the user message's `images` field. The cache key includes each image's **SHA-256** (never the base64). Per-stage HTTP timeout: `text_check` **60 s**.
2. **`assets/illustrate.py`:** `TEXT_EXPECTED_WORDS` and `TEXT_EXPECTED_PHRASES` **verbatim** from §7.1 (bare "sign" excluded), and `text_expected(description) -> bool` (casefold; whole words; phrases at word boundaries).
3. **`assets/text_check.py`:**
   - `TEXT_CHECK_PROMPT` verbatim from §7.1 and the schema `{"kind": "letters_or_words"|"none", "sample": string}`.
   - `check_image_for_text(png_path, backend) -> TextCheckResult(kind, sample, has_text, elapsed_ms)`. It resizes to 512×512 with Lanczos, encodes PNG, and calls `run_with_retries(stage="text_check", images=[…], num_predict=96)` with `temperature` 0.
   - `has_text = kind == "letters_or_words" and count of [A-Za-z0-9] in sample ≥ 3`.
   - Verdicts are cached at `cache/text_check/<sha256(png bytes + model + prompt)>.json`.
4. **`run_assets`** (`illustrate.py:299`), per entity:
   - If `text_expected`: generate once; `text_check: "skipped"`.
   - Else: generate with seed s = `image_seed(prompt)`, then check. If it has text, regenerate with s + 1, check, then s + 2, check. The first clean image wins (`"clean"` if it was the first, `"regenerated"` otherwise). Three texty images → `status: "failed"`, `error: "lettering detected in 3 attempts"`.
   - A check that fails → keep the image, `text_check: "unavailable"`.
   - Manifest fields per §7.1: `text_expected`, `text_check`, `attempts: [{seed, kind, sample, elapsed_ms}]`.
5. `logs/assets.log`'s final line adds `text_checks=<n> regenerations=<m>`.

**Validate:**
- **Red first:** write the unit tests (the "text check" row in `design_testing_and_validation.md` §2: text-expected cases, the ≥ 3-alphanumeric rule, the seed sequence s, s+1, s+2, the `failed`/`regenerated`/`unavailable` paths, 0 backend calls when skipped) and record them failing.
- Slow: `fixtures/vision/` classifies **7/7 on seeds 7 and 8** (§1.4).
- **Falsify:** swap in the **rejected naive prompt** (verbatim in `design_visual_direction.md` §7.1, with its own schema) → the two waterfront images become false positives (measured 5/7) → red. That proves the eval discriminates between prompts. Restore → 7/7.
- **Look:** run `new` on `story_recipe_box`. The recipe-card entity must show `text_check: "skipped"` (its description contains "recipe", "cards" and "handwritten"); every other entity `clean` or `regenerated`. Open every image and describe it.
- **Collapse Issue 3** in this commit.

**Blast radius:** `planner/llm.py`, `assets/illustrate.py`, `assets/text_check.py` (new), `stages/assets.py`, tests. The B3 grep count becomes 7.

---

### B11 — Legible text over images; captions through FitText

**What this means for the user:** today, captions on place and object illustrations are unreadable (pale text on pale images), and a very long caption word can overflow.

**The gap:**
- `renderer/src/templates/location.tsx:147-157` and `set_piece.tsx:125-135` implement the old 320 px 0→85% scrim, as the design said. The design was wrong: 1.95 : 1 over white (tile `s006` of `docs/evals/assets/2026-09-25/e2e_recipe_box_contact_sheet.png`).
- `renderer/src/story/Captions.tsx:66` uses a fixed `fontSize: 76` with no FitText.
- Contracts: `design_templates.md` §2.13 and §2.14, `design_visual_direction.md` §2.1 and §8.

**Implementation:**
1. `theme/layout.ts` exports `IMAGE_SCRIM = { stops: [[640, 0], [800, 0.85], [1120, 0.92]] }` and `IMAGE_TEXT_MIN_TOP = 807`.
2. `components/ImageScrim.tsx` is used by `location` and `set_piece`. The caption sits 12 px above the name, which is bottom-aligned at y 1080.
3. Commit `renderer/public/gallery/white.png` (solid white, 1024²) and add gallery variant **`location__worst`** (max-length name and caption over it).
4. `tests/test_contrast.py` parses the scrim and palette, interpolates the alpha at y 807 (≥ 0.85), composites over white, and asserts `ink` and `inkMuted` ≥ 4.5 : 1.
5. Captions render through `FitText` with the slot `{display, 800, 76→60, 2 lines, 900}`, defined once in `theme/type.ts`; overflow logs use scene id `captions`.

**Validate:**
- **Red first:** the contrast test on the current values fails (≈ 0.53 → 1.95 : 1).
- G10 with regenerated goldens for `location`, `set_piece` and `location__worst`. Open each and describe it.
- Re-preview a `story_recipe_box` job and describe the `set_piece` tiles.
- **Falsify:** set the 800 stop to 0.53 → red.

**Blast radius:** those templates and components, `layout.ts`, `type.ts`, `Captions.tsx`, gallery fixtures and goldens, `tests/test_contrast.py`.

---

### B12 — Map legibility; `kinetic_quote` attribution avatar

**What this means for the user:** today, the map is a dark rectangle with hidden markers, and quoted lines show a letter in a circle instead of the character.

**The gap:**
- `renderer/src/components/MapView.tsx:139,150,153,167` use the old colours (land/sea 1.30 : 1; a design error).
- `:209` draws a radius-8 dot, and `:218` puts the chip at `m.y − 48`, over the dot.
- There are no lakes, so Lake Superior is drawn as land.
- `renderer/src/templates/kinetic_quote.tsx:170` renders `cast.name[0]`, a deviation from §2.2.
- Contracts: `design_templates.md` §2.2 and §2.15, `design_visual_direction.md` §2.1.

**Implementation:**
1. `theme/palette.ts`: `mapSea #0B1326`, `mapLand #4466A0`, `mapRegion #7C9FDB`, `mapBorder #0B1326`.
2. Markers: radius 14, `highlight` fill, 4 px `bgDeep` stroke; pulse ring radius 14→48, 4 px, opacity 0.6→0, period 30.
3. Chips: `bgDeep` fill, `ink` text, bottom edge at y − 26 (or top edge at y + 26 within 120 px of the panel top). The placement math lives in a pure function in `mapFraming.ts`.
4. Lakes:
   - `setup.sh` downloads Natural Earth `geojson/ne_50m_lakes.geojson` (`nvkelso/natural-earth-vector`, public domain) into `data/vendor/`, pinned in `CHECKSUMS`.
   - `renderer/scripts/gen-lakes.ts` writes `renderer/public/geo/lakes-50m.json` (a DO-NOT-EDIT `$comment`, coordinates rounded to 3 decimals). It is committed and regenerated/diffed by `check_schema_sync.sh`.
   - Lakes are drawn above land in `mapSea`; `doctor` checks the file.
5. `kinetic_quote` attribution: `<Avatar>` at 120 px (`neutral`) with a name chip below.
6. `tests/test_contrast.py` asserts every map row in `design_visual_direction.md` §2.1.

**Validate:**
- **Red first:** the map contrast assertions fail today.
- vitest: the chip rectangle and dot circle are disjoint for both placements (**falsify** with −48 → red).
- G10 goldens for `map_focus` and `kinetic_quote`, opened and described.
- Re-preview `story_recipe_box`: the map must show Lake Superior as water between the Duluth and Thunder Bay markers, both dots visible; describe it.
- **Falsify:** set `mapLand` back to `#1F2F52` → red.

**Blast radius:** `MapView.tsx`, `mapFraming.ts` (+ tests), `palette.ts`, `kinetic_quote.tsx`, `gen-lakes.ts`, `renderer/public/geo/`, `setup.sh`, `data/vendor/CHECKSUMS`, `check_schema_sync.sh`, `doctor.py`, goldens, `tests/test_contrast.py`.

---

### B13 — Gates fail closed; bundle hygiene

**What this means for the user:** two safety checks stop being able to pass without checking anything, and renders stop carrying the test fixtures.

**The gap:**
- `scripts/check_gallery.sh:60` skips the overflow check when `overflow.json` is absent, and counts an unparseable file as 0; `:40-41` never clean the output directories.
- `scripts/check_renderer_purity.sh:9` exempts any directory named `remotion`.
- `renderer/scripts/render.ts:74-77` copies `fixtures/` into every job's `render_public/`.

**Implementation:**
1. `check_gallery.sh`: `rm -rf` both output dirs first; a missing or unparseable `overflow.json` → fail.
2. Purity: grep all of `renderer/src/`, then drop only paths starting with `renderer/src/clock/remotion/`.
3. `render.ts`: no fixtures copy. The smoke test builds its own temporary job dir with `fixtures/music/test_bed.wav` at `audio/narration.wav`.

**Validate:** the G9/G10 falsifications in `design_testing_and_validation.md` §3 (a new `renderer/src/templates/remotion/x.tsx` using `useCurrentFrame` → G9 red; deleting `overflow.json` after the render → G10 red). After a render, `render_public/fixtures` does not exist.

**Blast radius:** the two scripts, `render.ts`, the smoke test.

---

### B14 — Remove the dead SFX scheduler

**What this means for the user:** nothing visible; it removes a tested-but-unused copy of the SFX rules.

**The gap:** `timing/sfx.py` (`schedule_sfx`, duplicate constants, paths without `job/`), exported at `timing/__init__.py:14,29` and tested by `tests/test_timing_sfx.py`, is never called. `compile.py:155-185` schedules SFX inline and is tested (`tests/test_compile.py:203,256`).

**Implementation:** delete the module, its exports and its tests.

**Validate:** `grep -rn "schedule_sfx\|timing.sfx" src tests` → nothing. G4 drops by exactly **3**. `test_compile.py`'s SFX tests pass.

**Blast radius:** those files; the §1.3 G4 count.

---

### B15 — README accuracy

**What this means for the user:** the README stops telling them things that are not true, and explains the new automatic checks.

**The gap:**
- `README.md:7` claims completion as if defect-free.
- `:52` and `:95` say music is "ducked to −20 dBFS". It is normalised to −16 LUFS and played at −18 dB (volume 0.126), 1 s fade-in, 2 s fade-out, no ducking (`audio/mix_prep.py:80-93`, `AudioLayer.tsx:14`).
- `:97-100` describe SFX roles that don't match the registry.
- `:129` credits four fonts that are not shipped and omits Inter.

**Implementation:**
- Status: "Wave A delivered; Wave B in progress" (B17 updates it).
- The music sentence, exactly.
- SFX roles per `design_templates.md` §2: `whoosh` at the starts of `title_card`, `comparison`, `location` and `set_piece`; `pop` on item entrances and the `character_intro`/`relationship_map` starts; `ding` at a stat's count end; `hit` at a `reveal`'s start.
- Fonts: Poppins (Google Fonts, OFL) and Inter (rsms/inter, OFL); add Natural Earth lakes.
- A new short **"Automatic checks"** section:
  - illustrations are checked locally for stray lettering and regenerated, except when the description calls for writing;
  - people scenes get a second, blind reading of who says what;
  - timelines use real dates or a fixed list of phrases.
  - State the review-gate flags (`image failed`, `critic changed`).

**Validate:** `grep -nE "Outfit|JetBrains|Space Grotesk|Fraunces|20 dBFS" README.md` → nothing; the font credits equal the TTF families in `renderer/public/fonts`.

**Blast radius:** `README.md`.

---

### B16 — E2E: computed counts, audible music

**What this means for the user:** the proof that sync and music work becomes a measurement.

**The gap:** `scripts/e2e.sh:502` types "Checked: 9 scene boundaries" into the report. Voice lines are hard-coded. Nothing proves music is *audible* in the mix.

**Implementation:**
1. `check-sync` prints JSON `{"checked", "expected": len(scenes) − 1, "failures"}`. The script asserts equality and no failures, and writes the numbers into the report.
2. Voice lines are read from `voice.json`.
3. For the step-4 job, the RMS of the final MP4's audio in [duration − 1.4 s, duration − 1.0 s] (ffmpeg `atrim` + `astats`) must be > −60 dBFS; record it.
4. The report also lists, per fixture, the B6 critic counts and the B10 `text_check` statuses from `plan_report.json` / `assets/manifest.json`.

**Validate:**
- **Falsify:** skip one boundary in `check-sync` → red.
- **Falsify:** re-render the step-4 job from a timeline copy with music removed → the RMS check is red (expect < −80 dBFS).

**Blast radius:** `scripts/e2e.sh`, `evals/e2e.py`, the report.

---

### B17 — Cold-cache performance budget; close-out

**What this means for the user:** they learn, measured, whether a 3-minute story stays within their 10-minute tolerance **with** the new critic and text checks.

**The gap:** `docs/evals/e2e_2026-09-25.md` shows `bible`/`segment`/`storyboard` at 0.0–0.2 s and `assets` at 0.1 s, i.e. warm caches. No `scripts/measure_budget.sh` exists. Procedure: `design_testing_and_validation.md` §5.

**Implementation:**
- `scripts/measure_budget.sh` exactly per §5: `ollama stop gemma4:26b`; a fresh `INFOGRAPHICS_CACHE_DIR` (so LLM, image **and text-check** caches are empty); a fresh jobs dir; timed `new` / `approve` / `render` on `story_recipe_box` with music and SFX.
- The report includes critic calls, text checks and regenerations; `cache_hits` must total 0.
- Commit `docs/evals/budget_<date>.md`.

**Validate:** `new` → review ≤ **6.5 min**, `render` ≤ **3.5 min**, total ≤ **10 min**. **Exceeding a bar is filed with per-stage timings.** The critic and text check are user-selected features, so they are not removed or skipped to fit the budget.

**Close-out:**
1. Full battery, bare; update §1.3.
2. Rewrite this guide to **Queue Complete**.
3. Move Wave B to §5.1.
4. Update `ongoing_general_errors.md` §1.
5. Stop.

---

## 4. Deferred — do NOT start

**D1–D9** (`ongoing_general_errors.md` §4): video input + PiP, 16:9, multi-voice, live mode, Reddit URL fetch, public-domain photos, historical borders, web editor, cloud LLM. Each needs a user selection. There are no open issues awaiting selection.

---

## 5. Do NOT change

### 5.1 Already delivered

**Wave A (A1–A22), verified September 25, 2026.** One line per item, with its correct commit and verification result, is in `ongoing_general_errors.md` §3. Items marked "✓" are not reworked; items marked "→ B<n>" are touched only as that item specifies.

### 5.2 Accepted equivalents (checked September 25, 2026)

- The sync probe is drawn inside each scene's layer, not a separate Story layer; it gives the same "current scene" colour, and G12 proves the flips frame-accurate.
- The geo bbox check handles antimeridian-crossing countries (`planner/geo.py:191`); recorded in `design_planner.md` §2.
- `image_prompt` strips a trailing period from `visual_description`.
- `FitText` gives multi-line boxes 0.35 of a line of extra height for ascenders; it cannot hide a whole extra line.
- The gallery computes fixture timing with a TypeScript port of `item_frames` (`renderer/src/story/timing.ts`), gallery-only.
- `fixtures/CHECKSUMS` paths are relative to `fixtures/`; verify with `(cd fixtures && shasum -a 256 -c CHECKSUMS)`.
- `plan_report.json.llm_calls` counts the storyboard stage's calls only (select + props, and from B6 the critic).
- Node 26 works; the Node 22 fallback was not needed.

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

### 5.4 Invariants and intentional design decisions

**New (September 25, 2026):**
- Job-local inputs are authoritative (B1).
- Every LLM call goes through `run_with_retries` (B3, B6, B10).
- LLM-facing schemas carry no length constraints, and **`num_predict` bounds short answers** (critic 256, text check 96) (B7).
- Text over images only where the scrim is ≥ 85% (B11).
- Commit scope = item id; resolved lines cite the id, never a hash.
- **The text check never runs on text-expected descriptions**; the word/phrase lists are verbatim and bare "sign" is excluded (B10).
- **The critic is blind** (it never sees the proposed who/tone), makes **at most one call per scene**, and triggers **at most one props retry**; an `unknown` speaker is never a mismatch; an unsupported strong tone is (B6).
- **Timeline labels:** a grounded date or one of exactly 17 phrases; distinct; years non-decreasing (B5).

**Unchanged:**
- The voice rule's asymmetry; the voice is decided before narration; `--voice` accepts only `af_heart` and `am_michael`.
- Cast = vector avatars only.
- No auto-approve; `approve` refuses on overflow.
- Scenes lead the voice by 200 ms; captions never lead.
- Absolute-frame scenes, never `TransitionSeries`.
- Item and count timings are computed once, in Python.
- Grounding is a hard gate; gazetteer-first geo.
- Navy text on cast colours and on `highlight`.
- Python is the contract source; `kinetic_quote` is the universal fallback.
- FLUX.2 klein **9B is never used**, and neither is Z-Image-Turbo.
- Beat boundaries are not human-editable.
- The `sandbox-exec` offline gate stays.
- Fixtures are original texts.

### 5.5 Assessed and rejected — do NOT re-propose

**Unchanged from Wave A:**
- Live-first or parallel tracks; LLM-written scene code; generated video.
- Video input or URL fetching in the MVP.
- Vector-only or illustration-heavy imagery; generated cast portraits.
- Single-language stacks; any cloud API.
- Both aspects, or 16:9 first; subtitles, no captions, or a caption toggle.
- Other art styles; a persistent stage or a pure slideshow.
- Multi-voice in the MVP; an optional gate or a web editor; music-only or no audio bed.
- `TransitionSeries`; TypeScript as the schema source; unchecked LLM coordinates; Whisper re-timing of TTS audio.
- Voices `bm_george`/`af_bella`; a voice bake-off; Z-Image-Turbo or an image bake-off; inferring narrator gender from stereotypes.

**New, September 25, 2026 (verification):**
- Raising `maxLength` to "fix" truncation.
- Relaxing the fallback bar.
- Keeping the mflux symlink.

**New, September 25, 2026 (selections):**
- Issue 3 options B (steer subjects away from writing) and C (review gate + a regenerate command only).
- Issue 4 options B (digits only) and C (any distinct label).
- Issue 5 options B (rules only), C (no change) and D (switch to `qwen3.6:35b`).
- The naive yes/no text-check prompt (2 false positives in 4).
- An uncapped text-check call.
- Counting an `unknown` speaker as a mismatch.
- A second critic call after a retry.
- Bare "sign" in the text-expected list.
- Removing or skipping the critic or text check to meet the budget.

---

## 6. Where the contracts live

| What | Where |
|---|---|
| Product, pipeline, job layout, **job-local inputs (§4)**, CLI, env vars, review gate, local-only policy, pinned models (incl. the critic/text-check model) | `design_system_architecture.md` |
| JSON shapes (**`plan_report.critic`**), source of truth, generation, sync gate | `design_data_contracts.md` |
| Ingest (**music/SFX fields**), TTS, ASR, loudness, frame math, beats, captions, SFX scheduling | `design_audio_and_timing.md` |
| LLM backend (**errors, `run_with_retries` everywhere, schemas, images, `num_predict`**), voice §10, bible, segmentation, selection, props, validators (**meaning rules §6.6, completeness §6.7**), grounding (**scale words, timeline labels §8**), **critic §11**, eval | `design_planner.md` |
| The 16 templates (**§2.2, §2.3, §2.9–2.11, §2.13–2.16 revised**) | `design_templates.md` |
| Palette, **composited contrast §2.1**, type, layout, motion, avatars, captions, illustration, **text check §7.1** | `design_visual_direction.md` |
| Remotion, clock, spans, overflow, render CLI (bundle contents), preview, verification | `design_rendering.md` |
| Fixtures (**`vision/`**), test rows (**timeline, meaning, critic, text check**), gates (**fail-closed G10, exact G9**), E2E, offline gate, **cold budget §5**, artefacts | `design_testing_and_validation.md` |
| Selected issues 3–5 (to collapse on delivery), resolved index, lessons, deferred items, decision log | `ongoing_general_errors.md` |

---

## 7. Validation standard

- **Red first.** Run the falsifying check against the unfixed code and record the failure before fixing.
- **A gate must be able to fail, and must fail closed.**
- **A perfect score is a reason to look harder** (Wave A's 0% fallback came from truncation).
- **Measure what the viewer sees, composited**: contrast against the real background, including a worst-case white image.
- **Invocation options are not state.**
- **Warm caches measure nothing about a cold budget.**
- **A model-based check needs a labelled set and a falsification that proves it discriminates.** The text check's eval must go red when the rejected naive prompt is swapped in; the critic's must go red when its rules are loosened.
- **Read exit codes bare. A gate that did not run is not a pass. Open every artefact and describe it.**
- **Never loosen a bar to pass it.** File it with the measurement.

---

## 8. THE LOOP

```
(1) Is there an approved item? Wave B, B1–B17, in §2 order. If all are done,
    STOP. Never start D1–D9 without a user selection.
    Never fill in a `Your selection:` line.
(2) Read the item and EVERY design section it names before writing code.
    Prompts, word lists, thresholds and seeds are copied VERBATIM.
(3) RED FIRST: run the item's falsifying check on the unfixed code (or write
    the new tests and see them fail); record it. If a check passes on unfixed
    code, the check is wrong: fix the check.
(4) Build only what the item says. Nothing from §5.5.
(5) GREEN: run the item's checks; then the falsification (break it again,
    see red, restore, see green). Model-based checks reproduce §1.4's numbers.
(6) Open every artefact the item produces and describe what it shows.
(7) Full battery, bare. Update §1.3. NOT RUN is legal; blank is not.
(8) ONE commit, scope = item id: `fix(bN): …` or `feat(bN): …`. WHY + red/green
    runs in the body. ONE line under "Wave B" in ongoing_general_errors.md §3
    citing `git log --grep "(bN)"`, never a hash. B5/B6/B10 also collapse
    Issue 4/5/3. Do not amend after pushing.
(9) git push origin main.
(10) Next item.
```

---

## 9. Definition of Done: Wave B

- [ ] B1–B17 each landed as one pushed commit scoped to its id, with its red and green runs recorded.
- [ ] §1.3: every gate G1–G14 green, measured this session, read bare.
- [ ] Music and SFX survive the review journey and are **audible** in the final MP4.
- [ ] The new planner eval: 0 newline strings, 0 completeness failures, 0 timeline-label violations, critic regression set 4/4, every §9 bar met or filed.
- [ ] The text check reproduces 7/7 on `fixtures/vision/` (seeds 7 and 8), and the naive-prompt falsification was run and recorded.
- [ ] The contrast test covers the image scrim (worst case, white) and every map pair.
- [ ] `docs/evals/budget_<date>.md` is committed from a cold run with `cache_hits = 0`, including critic and text-check costs, bars met or filed.
- [ ] Issues 3, 4 and 5 collapsed into §3 lines with the user's selection text verbatim.
- [ ] README states only what is true, including the automatic checks.
- [ ] This guide rewritten to **Queue Complete**. **Then stop. Do not invent work.** The only legitimate triggers for new work are a user selection on D1–D9, or a gate going red (investigate and **file** it).

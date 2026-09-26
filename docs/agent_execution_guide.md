# Agent Execution Guide — Active Build: Wave B (verification fixes, 13 items) — September 25, 2026

**You are an engineering agent with no memory of this project.** The offline MVP (Wave A, A1–A22) is built, committed and pushed (head `e374a15`). On September 25, 2026 an independent verification pass re-ran every gate and read the source against the design. **All 14 gates reproduce green — and the product still has defects that no gate could see.** The worst:
- every reviewed-and-edited video loses its music and sound effects;
- about one scene in five shows text cut off mid-word;
- two planner crash paths exist;
- captions over light illustrations and the map are unreadable.

**Wave B fixes them. That is the only approved work.**

**What is approved:** Wave B, items **B1–B13** in §3, in the order of §2. **What NOT to touch:** everything in §5 (delivered work, accepted equivalents, user decisions, invariants, rejected options). **What must not be started:** everything in §4, including **Issues 3–5**, which await the user's selection in `docs/ongoing_general_errors.md`.

**Every number and literal string in this document and in the design docs is a decision, not a suggestion.** Implement as written; do not substitute your own values. If a value is genuinely impossible, keep the *intent*, deviate minimally, say so in the commit body, and add it to §5.2. If the design itself cannot work, **STOP and file it in `docs/ongoing_general_errors.md` with options and a `Your selection: _____` line. Do not improvise, and never fill in a selection line yourself.**

**What the product is, in one paragraph.** A local-only CLI that turns a **text story** (narrated by local TTS in an automatically chosen voice) or an **audio narration** into a **1080×1920 animated explainer video**. It uses flat editorial vector scenes chosen from 16 templates, in sync with the voice, with word-by-word karaoke captions, a persistent cast of vector avatars, locally generated illustrations, and optional music and SFX. Every video **stops for human review** before the final render. The long-term goal is live mode, so the renderer is clock-agnostic.

**The lesson that shaped this wave.** Green gates were not evidence of correctness here: every one of the defects above passed every gate. **For every item, the validation must include the check that would have caught the original defect**, and you must run it against the unfixed code first and see it fail.

---

## 0. Standing constraints (apply to every item)

1. **The battery is the regression bar.** After every item, run `scripts/battery.sh` (full) and update §1.3. **Read every exit code bare.** `cmd | tail` reports `tail`'s status.
2. **Fully local at runtime.** No cloud API, no network except loopback (`design_system_architecture.md` §7).
3. **Python (Pydantic) is the source of truth for every contract.** Generated files (`schema/`, `renderer/src/generated/`, `data/geo/country_bboxes.json`, and from B8 `renderer/public/geo/lakes-50m.json`) are never hand-edited.
4. **Templates read time only through the clock** (`design_rendering.md` §3).
5. **The review gate is mandatory.** No auto-approve under any name.
6. **The planner never crashes the pipeline and never shows an ungrounded or truncated fact** (`design_planner.md` §1, §6, §8). **Every planner LLM call goes through `run_with_retries`.**
7. **Red first.** Before fixing an item, write or run its falsifying check against the *current* code and record the failure. Then fix, then record the pass. A check you never saw fail is not evidence.
8. **One item = one Conventional Commit whose scope is the item id**, e.g. `fix(b1): keep music and sfx across preview and rerun`. The WHY goes in the body, including the red and green runs. **Push after every item:** `git push origin main`. **Never amend a pushed commit.**
9. **Record the resolution in the same commit:** one line under "Wave B" in `ongoing_general_errors.md` §3 in the form `B<n> — <title> — git log --grep "(b<n>)" — <measured result>`. Do **not** write a hash: a commit cannot contain its own hash, and Wave A's index ended up citing 14 pre-amend commits and one that never existed (tracking doc §2.5).
10. **When this guide and a design doc disagree, stop and file it.**
11. Every stage writes `logs/<stage>.log` ending in `llm_calls=<n> cache_hits=<m> elapsed_ms=<t>`; the LLM call counter is incremented at the backend's entry point.

---

## 1. Verified baseline (September 25, 2026, independent verification session)

### 1.1 Environment (verified)

| Fact | Value |
|---|---|
| Machine | Apple **M4 Max**, **64 GB**, macOS (Darwin 25.6.0) |
| ffmpeg / ffprobe | 8.1 · Node **v26.5.0** (Remotion works on it; no Node 22 fallback was needed) · project Python **3.12** via uv |
| Ollama | 0.33.0 · planner **`gemma4:26b`** present (id `08ae7ec1744b`, 18 GB) |
| Kokoro / mlx-whisper / pydantic | 0.9.4 / 0.4.3 / 2.13.5 |
| espeak-ng | 1.52.0 |
| mflux | **0.20.0**. It ships `mflux-generate-flux2` (`--model flux2-klein-4b`); **there is no `mflux-generate-flux2-klein` executable.** Wave A's `setup.sh` created a symlink of that name in `~/.local/bin` (removed by B9). The only FLUX.2 klein weights on the machine are **4B** (`black-forest-labs/FLUX.2-klein-4B`); no 9B. |
| Remotion | 4.0.528 (all packages identical) |

### 1.2 Repository

Wave A: 22 commits, `4df212a`…`e374a15` on `main`, pushed. The correct per-item hashes are in `ongoing_general_errors.md` §3. The design docs were revised on September 25, 2026 (contract changes listed in `ongoing_general_errors.md` §5).

### 1.3 Gates (run bare in this verification session)

| # | Gate | Result |
|---|---|---|
| G1 | `uv run ruff check .` | exit 0 |
| G2 | `uv run ruff format --check .` | exit 0 · 99 files |
| G3 | `uv run mypy src` | exit 0 · 53 source files |
| G4 | `uv run pytest -q -m "not slow"` | exit 0 · **169 passed** |
| G5 | `npm --prefix renderer run typecheck` | exit 0 |
| G6 | `npm --prefix renderer run lint` | exit 0 |
| G7 | `npm --prefix renderer test` | exit 0 · **15 passed** (4 files) |
| G8 | `./scripts/check_schema_sync.sh` | exit 0 |
| G9 | `./scripts/check_renderer_purity.sh` | exit 0 (but the exemption is too broad → B9) |
| G10 | `./scripts/check_gallery.sh` | exit 0 · 35 s · 51 goldens compared, hold motion on 17 entries (but the overflow check fails open → B9) |
| G11 | `uv run pytest -q -m slow` | exit 0 · **18 passed** · 178 s |
| G12 | `./scripts/e2e.sh` | exit 0 · 847 s · steps 1–8 pass (but it asserts neither music/SFX survival nor a computed sync count → B1, B12; its timings are warm-cache → B13) |
| G13 | `./scripts/check_offline.sh` | exit 0 · 198 s · self-checks pass (external network denied, loopback allowed); fresh-cache `molasses_flood` reached review in **122.5 s** (planning 27 s, 4 images 83 s): a cold data point, not the budget run |
| G14 | `uv run infographics doctor` | exit 0 · 21 checks OK |

**Known, reproduced defects under a green battery** (each is an item below): music/SFX lost after `preview` (verification run `artifacts/e2e/20260925_203215`: final `timeline.audio.music == null`, `sfx == []`, while `input/test_bed.wav` and `input/sfx/` exist) · a "not found" string in a valid reply crashes as a missing model (reproduced with a mock transport) · truncated JSON crashes props planning (reproduced with a stub backend) · 34/701 storyboard strings truncated mid-word · a stray 1,000,000 extracted from "2.3 million" · captions over light images at 1.95 : 1 · map land/sea at 1.30 : 1.

---

## 2. Execution order

| # | Item | Why this position |
|---|---|---|
| B1 | Music and SFX survive the review journey | The most visible defect: every edited video ships silent of music/SFX. Independent of everything else. |
| B2 | LLM error classification | Small, and B3–B5 run the planner many times. A spurious "missing model" crash would waste those runs. |
| B3 | Planner crash containment | B5's eval re-run must not be killable by one malformed reply. |
| B4 | Grounding: scale words | A grounding change alters which props validate; it must land before B5 re-runs the eval. |
| B5 | LLM-facing schemas without length limits + text completeness + eval re-run | Changes every planner output; the one expensive eval re-run happens here, after B2–B4. |
| B6 | Contact sheet flags failed images | Preview-only; before the renderer items so their preview checks show flags correctly. |
| B7 | Legible text over images; captions through FitText | Changes goldens. Done back to back with B8, so goldens are regenerated in one reviewed batch per item. |
| B8 | Map legibility; `kinetic_quote` attribution avatar | Changes goldens and adds a generated geo file (G8). |
| B9 | Gates fail closed; bundle and setup hygiene | Hardens G9/G10 **after** the goldens settle, so the stricter gate validates the final images. |
| B10 | Remove the dead SFX scheduler | Cleanup; changes the G4 test count, recorded exactly. |
| B11 | README accuracy | Describes the behaviour B1–B10 produced. |
| B12 | E2E: computed counts, audible music | Final E2E shape before the last measurement. |
| B13 | Cold-cache performance budget; close-out | Measures the finished system; closes the wave. |

---

## 3. The items

### B1 — Music and SFX survive the review journey

**What this means for the user:** today, if they change anything at the review gate, the final video silently loses its music and every sound effect.

**The gap:**
- `src/animated_infographics/stages/compile.py:36-55` takes music and SFX from `ctx.music_path` / `ctx.sfx_dir`. It falls back to `audio/music.wav` and `audio/sfx/` only if those still exist.
- `src/animated_infographics/jobs.py:41` registers `audio/music.wav` and `audio/sfx` as **compile outputs**, so `invalidate_after()` deletes them before every recompile.
- `src/animated_infographics/cli.py:286` (`preview`) and `:429` (`rerun`) build a bare `RunContext()`.
- Net effect: after `preview`, compile runs with no context paths and no files, so `timeline.audio.music = null`, `sfx = []`.
- The E2E never asserted otherwise. Contract: `design_system_architecture.md` §4 ("Job-local inputs are authoritative"), `design_audio_and_timing.md` §1 (`ingest.json` fields).

**Implementation:**
1. Add `music: str | None` and `sfx_dir: str | None` (job-relative) to the ingest record model in `contracts/models.py`. Export (G8).
2. `stages/ingest.py`: when the run context carries music/SFX (only `new` sets them), record `"input/<music filename>"` and `"input/sfx"` in `ingest.json`; otherwise record `null`.
3. `stages/compile.py`: read `ingest.json`. If `music` is set, run `prepare_music(job.dir / music, audio/music.wav)` **on every run**. If `sfx_dir` is set, run `prepare_sfx(job.dir / sfx_dir, audio/sfx)` on every run. Delete both `ctx` reads and both "already exists" fallbacks.
4. **Only `stages/ingest.py` may read `ctx.music_path` / `ctx.sfx_dir`.** Add a unit test that greps `src/animated_infographics/` for those attribute names and asserts they appear only in `cli.py` (where `new` sets them) and `stages/ingest.py`.
5. `jobs.py:55`: add `"ingest.json"` to `STAGE_INPUT_DEPENDENCIES["compile"]`.
6. `scripts/e2e.sh` step 4: after `render`, assert `timeline.audio.music` non-null, `audio.sfx` non-empty, and that `audio/music.wav` and ≥ 1 `audio/sfx/*.wav` exist (`design_testing_and_validation.md` §4).

**Validate:**
- **Red first:** add the unit test below and the E2E assertion, run them on the unfixed code, and record both failures.
- **Unit:** build a job with `ingest.json` naming music and SFX; run compile; `invalidate_after("storyboard")`; run compile again with `RunContext()`. `timeline.audio.music` must be non-null and `sfx` non-empty.
- **Journey:** `new … --music … --sfx-dir …` → edit `storyboard.json` → `preview` → `approve` → `render`. The assertions from step 6 must hold.
- **Falsify:** restore the `ctx.music_path` read in compile → the unit test is red; restore.

**Blast radius:** `contracts/models.py`, `schema/`, `renderer/src/generated/` (regenerate), `stages/ingest.py`, `stages/compile.py`, `jobs.py`, `scripts/e2e.sh`, tests.

---

### B2 — LLM error classification

**What this means for the user:** today, a caption like "the recipe card was not found" makes the tool claim the planner model is missing and quit.

**The gap:** `src/animated_infographics/planner/llm.py:161` raises `DependencyMissing` whenever the lowercase response text contains "not found", including in successful 200 replies. Reproduced September 25 with `httpx.MockTransport`: a 200 reply whose JSON content was `{"caption": "The last recipe card was not found"}` raised "Ollama model 'gemma4:26b' not found". Contract: `design_planner.md` §1 ("Error classification").

**Implementation:**
1. Only when `resp.status_code != 200`:
   - 404, or a JSON `error` field naming a missing model → `DependencyMissing` (exit 4);
   - any other non-200 → raise `LLMResponseError(ValueError)`, which `run_with_retries` counts as a failed attempt.
2. A 200 response is never inspected beyond `message.content`.

**Validate:**
- The `planner/llm.py` unit rows in `design_testing_and_validation.md` §2: 200 containing "not found" → parsed JSON returned; 404 → exit-4 error; 500 → failed attempt, then fallback.
- **Red first** with the 200 case on the unfixed code.
- **Falsify:** re-add the substring check → red.

**Blast radius:** `planner/llm.py`, `tests/test_llm.py`.

---

### B3 — Planner crash containment

**What this means for the user:** today, one malformed or truncated reply from the model crashes the whole planning stage instead of falling back.

**The gap:**
- `src/animated_infographics/planner/props.py:223-260` and `planner/select.py:246-300` run their own retry loops. They call `backend.generate_json(...)` (`props.py:233`, `select.py:256`) **outside any try**.
- `generate_json` raises `json.JSONDecodeError` on unparseable content. Reproduced September 25: a stub backend returning truncated JSON made `plan_single_template_props` raise `JSONDecodeError`.
- Their retries also omit the previous output as an `assistant` message, which `design_planner.md` §1 requires.

**Implementation:**
1. Rewrite `plan_single_template_props` to call `run_with_retries(backend, stage="props", system=…, user=…, schema=…, validate=…)`. The `validate` callable builds the `Scene` from the dict, runs `validate_scene`, and returns `(dict, errors)`. Take `attempts` for `plan_report.json` from the returned list.
2. Do the same for each selection window in `select.py` (`stage="select"`); the existing checks become its `validate`.
3. The fallbacks stay exactly as they are: select → `kinetic_quote` choices; props → alternate, then deterministic `kinetic_quote`.
4. Add a unit test: `generate_json(` may appear under `src/animated_infographics/planner/` only in `llm.py`. Corroborate that absence with the count of `run_with_retries(` call sites, which must be **5**: voice, bible, segment, select, props.

**Validate:** the "planner crash containment" row in `design_testing_and_validation.md` §2 (every reply truncated → storyboard completes, `fallback_level: 2` recorded). **Red first** on the unfixed code (the stage raises). **Falsify:** put one direct `generate_json` back → the grep test is red.

**Blast radius:** `planner/props.py`, `planner/select.py`, tests. Scene-count parity: the four fixtures must still produce exactly one scene per beat.

---

### B4 — Grounding: scale words are not numbers on their own

**What this means for the user:** today, a wrong "1 million" could appear on screen and pass the fact check.

**The gap:** `src/animated_infographics/planner/grounding.py:101` treats `thousand`/`million`/`billion` as spelled numbers by themselves. Reproduced September 25: `numbers("holding 2.3 million gallons")` returns `[2.3, 2300000.0, 1000000.0]`. Contract: `design_planner.md` §8 (new scale-word bullet).

**Implementation:** a scale word contributes a value only inside a spelled run (`two million`) or after a leading `a` (`a million`). After a digit number it only scales that number (already handled by the `DIGIT_SCALE_MAP` path).

**Validate:** the "grounding scale words" unit row (`design_testing_and_validation.md` §2), **red first**. All existing grounding tests still pass, including "about 150" rejecting a stat of 1,500. **Falsify:** revert → the "not 1,000,000" case is red.

**Blast radius:** `planner/grounding.py`, `tests/test_grounding.py`.

---

### B5 — LLM-facing schemas without length limits; text completeness; planner eval re-run

**What this means for the user:** today, about one scene in five shows text chopped off mid-word ("Rescuers wade through waist-", "Modern Era (").

**The gap:**
- The schemas sent as Ollama `format` carry Pydantic's `maxLength`: `planner/props.py:194` (`spec.props_model.model_json_schema()`), `planner/bible.py:22` (`BIBLE_SCHEMA`) and `planner/voice.py:101` (`maxLength: 160`).
- Constrained decoding enforces them by **force-closing the string**, so truncated text is always "valid".
- Measured September 25 over the 177 unique scenes in `artifacts/e2e/*`: **34 of 701 strings sit exactly at their `maxLength` with no terminal punctuation; 21 contain raw newlines.**
- This is also why the committed planner eval (`docs/evals/planner_2026-09-25.md`) shows a 0.0% fallback rate.
- Contract: `design_planner.md` §1 (LLM-facing schemas), §6 item 6 (text completeness).

**Implementation:**
1. `planner/llm.py`: `llm_facing_schema(schema: dict) -> dict` recursively removes `maxLength`, `minLength`, `maxItems`, `minItems` and `pattern` everywhere (properties, `items`, `$defs`, `anyOf`/`oneOf`); `enum`, `type`, `required` and `additionalProperties` stay. **Apply it inside `OllamaBackend.generate_json`, before building the payload and before computing the cache key**, so no caller can bypass it. The caches invalidate once; that is expected.
2. Validation still enforces every limit, through Pydantic plus the text-fit check. Retry messages name the field, its length and its limit, and ask for "a complete phrase".
3. `planner/validate.py`:
   - `normalize_text(s)`: collapse whitespace, including `\n`, to single spaces and strip. Apply it to every free-text field **before** validation in `props.py`, and again in `compile.py` before writing `timeline.json` (so hand-edited newlines never reach the renderer).
   - `text_complete_errors(path, s)` implements `design_planner.md` §6 item 6 for the free-text fields: `title`, `subtitle`, `text`, `caption`, `descriptor`, `traits[]`, `label`, `heading`, `points[]`, `kicker`, `contact_name`, `messages[].text`, `lines[].text`, `events[].label`, `markers[].label`, `edges[].label`, and a non-empty `suffix`. It is **not** applied to ids, enums, `prefix`, `date_label` or `era_label`; those wait on Issue 4.
4. `evals/text_audit.py`: over a set of `storyboard.json` files, count strings at exactly their `maxLength` without terminal punctuation, strings containing `\n`, and strings failing `text_complete_errors`. Print JSON.
5. Re-run the planner eval (`--no-llm-cache`) → a new `docs/evals/planner_<date>.md`. Add a "text audit" section from step 4 over the eval's storyboards.

**Validate:**
- **Red first:** run `evals/text_audit.py` over the existing `artifacts/e2e/*/jobs/**/storyboard.json` and record the counts. Expect the 34 at-limit and 21 newline strings measured above.
- Unit: every row of the "text completeness" test, and a schema-walk test proving no length keys survive `llm_facing_schema` for any template, the bible or voice, while `enum` does.
- After the eval: **0 newline strings, 0 completeness failures**. Record the at-limit count (expected near 0; each remaining one must end with punctuation).
- All `design_planner.md` §9 bars still hold (fallback L2 ≤ 15%, distinct templates, 0 violations, `story_recipe_box` planner wall time ≤ 240 s, voice 4/4). **A rise in fallbacks is honest and expected. If a bar fails, file it with the numbers; never loosen it.**
- **Falsify:** skip `llm_facing_schema` in `generate_json` → the schema-walk test is red.

**Blast radius:** `planner/llm.py`, `planner/validate.py`, `planner/props.py`, `compile.py`, `evals/text_audit.py`, `docs/evals/planner_<date>.md`, tests. Prompt changes, if any, are recorded with their SHA-256 in the eval report.

---

### B6 — The contact sheet flags failed images

**What this means for the user:** today, a scene whose illustration failed looks normal on the contact sheet. The reviewer only learns about it from `report.json`.

**The gap:** `src/animated_infographics/stages/preview.py:52-64` flags only overflow ∪ fallback. `design_rendering.md` §7 steps 3–4 also require scenes whose image failed. `report.json` already lists `failed_images` (`preview.py:322-336`) but nothing uses it for flags.

**Implementation:** flagged scenes = overflow ∪ `fallback_level 2` ∪ scenes whose `place_id` / `set_piece_id` names an entity with manifest `status: "failed"`. `storyboard.md`'s flags column adds `image failed`.

**Validate:** a unit test with a manifest marking `v1` failed and a `set_piece` scene on `v1`: that tile's label strip pixel is `danger` (`#FF6B8B`), and its `storyboard.md` row contains `image failed`. **Red first**; **falsify** by removing the new set → red. **Look:** run a job with `INFOGRAPHICS_IMAGE_TIMEOUT_S=1` and describe the contact sheet.

**Blast radius:** `stages/preview.py`, `preview.py`, tests.

---

### B7 — Legible text over images; captions through FitText

**What this means for the user:** today, captions on place and object illustrations are unreadable (pale text on a pale image), and a very long caption word can overflow the caption band.

**The gap:**
- `renderer/src/templates/location.tsx:147-157` and `set_piece.tsx:125-135` implement the old 320 px 0→85% scrim, **as the design said**. The design was wrong: over a white pixel the caption measured **1.95 : 1** (tile `s006` of `docs/evals/assets/2026-09-25/e2e_recipe_box_contact_sheet.png`).
- `renderer/src/story/Captions.tsx:66` uses a fixed `fontSize: 76` with no FitText (the spec is 76→60 px, max 2 lines).
- Contracts (revised): `design_templates.md` §2.13 and §2.14, `design_visual_direction.md` §2.1 and §8.

**Implementation:**
1. `renderer/src/theme/layout.ts`: export `IMAGE_SCRIM = { stops: [[640, 0], [800, 0.85], [1120, 0.92]] }` (y in canvas px, alpha of `bg`) and `IMAGE_TEXT_MIN_TOP = 807`.
2. `renderer/src/components/ImageScrim.tsx` draws that gradient; `location` and `set_piece` both use it. The caption sits 12 px above the name; the name is bottom-aligned at y 1080.
3. Commit `renderer/public/gallery/white.png` (solid `#FFFFFF`, 1024²) and add gallery fixture variant **`worst`** for `location` (max-length name and caption over `white.png`).
4. `tests/test_contrast.py`: parse `IMAGE_SCRIM` and the palette. Interpolate the alpha at `IMAGE_TEXT_MIN_TOP` (must be ≥ 0.85), composite `bg` over white, and assert `ink` and `inkMuted` ≥ 4.5 : 1.
5. Captions: render every caption page through `FitText` with a caption slot `{font: display, weight 800, size_max 76, size_min 60, max_lines 2, box_width 900}` defined once in `theme/type.ts`. The overflow log uses scene id `captions`.

**Validate:**
- **Red first:** the new contrast test against the current scrim values must fail (alpha ≈ 0.53 at y 807 → 1.95 : 1).
- G10 with regenerated goldens for `location`, `set_piece` and the new `location__worst`. **Open each regenerated golden and describe it in the commit body**: the text must be plainly readable on white.
- Re-run `preview` on a `story_recipe_box` job and describe the `set_piece` tiles.
- **Falsify:** set the 800 stop to 0.53 → the contrast test is red.

**Blast radius:** `location.tsx`, `set_piece.tsx`, `ImageScrim.tsx`, `layout.ts`, `type.ts`, `Captions.tsx`, gallery fixtures and goldens, `tests/test_contrast.py`.

---

### B8 — Map legibility; `kinetic_quote` attribution avatar

**What this means for the user:** today, the map is a dark rectangle with an invisible coastline and hidden markers, and quoted lines show a letter in a circle instead of the character.

**The gap:**
- `renderer/src/components/MapView.tsx:139,150,153,167` use the old colours, again **as the design said**. The design was wrong: land/sea measured **1.30 : 1**.
- `:209` draws a radius-8 dot, and `:218` puts the label chip at `m.y − 48`, over the dot.
- There is no lakes layer, so Lake Superior (the setting of `story_recipe_box`) is drawn as land.
- `renderer/src/templates/kinetic_quote.tsx:170` renders `cast.name[0]` in a circle instead of the `Avatar`. That is a deviation from `design_templates.md` §2.2.
- Contracts: `design_templates.md` §2.2 and §2.15, `design_visual_direction.md` §2.1.

**Implementation:**
1. `theme/palette.ts`: add `mapSea #0B1326`, `mapLand #4466A0`, `mapRegion #7C9FDB`, `mapBorder #0B1326`. `MapView` uses only these.
2. Markers: radius 14, `highlight` fill, 4 px `bgDeep` stroke. Pulse ring radius 14→48, 4 px `highlight`, opacity 0.6→0, period 30. Chips: `bgDeep` fill, `ink` text, bottom edge at marker y − 26 (or top edge at y + 26 within 120 px of the panel top). Put the chip-placement math in a pure function in `mapFraming.ts`.
3. Lakes:
   - `scripts/setup.sh` downloads Natural Earth `geojson/ne_50m_lakes.geojson` from the `nvkelso/natural-earth-vector` repository (public domain) into `data/vendor/`, pinned in `data/vendor/CHECKSUMS`.
   - A new `renderer/scripts/gen-lakes.ts` writes `renderer/public/geo/lakes-50m.json` (GeoJSON with a `"$comment"` DO-NOT-EDIT header, coordinates rounded to 3 decimals). It is committed, and `check_schema_sync.sh` regenerates and diffs it.
   - `MapView` draws the lakes above land in `mapSea`.
   - `doctor` checks the file.
4. `kinetic_quote`: the attribution renders `<Avatar>` at 120 px (expression `neutral`) with a name chip below, per §2.2.
5. `tests/test_contrast.py` asserts every map row in `design_visual_direction.md` §2.1 from the parsed palette.

**Validate:**
- **Red first:** the new map contrast assertions fail on the current colours.
- vitest: the chip rectangle and dot circle are disjoint for both placements (**falsify** with the old −48 offset → red).
- G10 with regenerated `map_focus` and `kinetic_quote` goldens; open each and describe it.
- Re-run `preview` on `story_recipe_box`. The `map_focus` tile must show Lake Superior as water between the Duluth and Thunder Bay markers, both dots visible; describe it.
- **Falsify:** set `mapLand` back to `#1F2F52` → the contrast test is red.

**Blast radius:** `MapView.tsx`, `mapFraming.ts` (+ tests), `palette.ts`, `kinetic_quote.tsx`, `gen-lakes.ts`, `renderer/public/geo/`, `setup.sh`, `data/vendor/CHECKSUMS`, `check_schema_sync.sh`, `doctor.py`, goldens, `tests/test_contrast.py`.

---

### B9 — Gates fail closed; bundle and setup hygiene

**What this means for the user:** today, two safety checks can pass without checking anything, every render copies the whole test-fixture folder into the video bundle, and setup writes into their home directory.

**The gap:**
- `scripts/check_gallery.sh:60` skips the overflow check when `overflow.json` is absent, and treats an unparseable file as 0 overflows. `:40-41` never clean the output directories, so stale stills can satisfy the comparison.
- `scripts/check_renderer_purity.sh:9` exempts **any** directory named `remotion`, not only `renderer/src/clock/remotion/`.
- `renderer/scripts/render.ts:74-77` copies the repository's `fixtures/` into every job's `render_public/`, contrary to `design_rendering.md` §2 (revised).
- `scripts/setup.sh:35-38` symlinks `~/.local/bin/mflux-generate-flux2-klein` → `mflux-generate-flux2` to match a command name that mflux 0.20.0 does not ship. `assets/illustrate.py:182-183` then claims it was "verified with `mflux-generate-flux2-klein --help`".

**Implementation:**
1. `check_gallery.sh`: `rm -rf` both output dirs first; a missing or unparseable `overflow.json` → `fail`.
2. `check_renderer_purity.sh`: grep all of `renderer/src/`, then drop only lines whose path starts with `renderer/src/clock/remotion/`.
3. `render.ts`: remove the fixtures copy. The smoke test builds its own temporary job dir with `fixtures/music/test_bed.wav` at `audio/narration.wav`.
4. mflux:
   - `illustrate.py` invokes **`mflux-generate-flux2 --model flux2-klein-4b`**, and `TOOL_NAME` becomes `mflux-generate-flux2`. The cache key changes; images regenerate once.
   - `setup.sh` stops creating the symlink and removes it if it points at `mflux-generate-flux2`.
   - `doctor` checks `mflux-generate-flux2` on PATH **and** that its `--help` output lists `flux2-klein-4b`.
   - Record in the design that mflux 0.20.0 exposes klein through `mflux-generate-flux2 --model` (`design_visual_direction.md` §7 and `design_system_architecture.md` §8, in this item's commit).

**Validate:** the G9 and G10 falsifications in `design_testing_and_validation.md` §3: a new `renderer/src/templates/remotion/x.tsx` using `useCurrentFrame` → G9 red; deleting `overflow.json` after the render → G10 red. After a render, `render_public/fixtures` does not exist. `doctor` with `PATH` lacking mflux → exit 4.

**Blast radius:** the three scripts, `render.ts`, `illustrate.py`, `doctor.py`, `setup.sh`, two design docs, tests.

---

### B10 — Remove the dead SFX scheduler

**What this means for the user:** nothing visible; it removes a tested-but-unused copy of the SFX rules that could drift from the real one.

**The gap:** `src/animated_infographics/timing/sfx.py` (`schedule_sfx`, its own copies of `SFX_MIN_GAP_FRAMES`/`SFX_VOLUME`, and a path format lacking `job/`) is exported by `timing/__init__.py:14,29` and tested by `tests/test_timing_sfx.py`, but **never called**: `compile.py:155-185` schedules SFX inline and is itself tested (`tests/test_compile.py:203,256`).

**Implementation:** delete `timing/sfx.py`, its exports and `tests/test_timing_sfx.py`.

**Validate:** `grep -rn "schedule_sfx\|timing.sfx" src tests` returns nothing. Corroborate the absence with the count: G4 drops by exactly the number of deleted tests (**3**), and `test_compile.py`'s SFX tests still pass.

**Blast radius:** those three files; §1.3 G4 count.

---

### B11 — README accuracy

**What this means for the user:** the README currently tells them things that are not true.

**The gap:**
- `README.md:7` claims the MVP is complete and verified by all gates, as if defect-free.
- `:52` and `:95` say music is "ducked to −20 dBFS". The code (`audio/mix_prep.py:80-93`, `renderer/src/story/AudioLayer.tsx:14`) normalises music to −16 LUFS and plays it at volume 0.126 (−18 dB), with a 1 s fade-in and a 2 s fade-out, and no ducking.
- `:97-100` describe SFX roles that do not match the registry cues.
- `:129` credits Outfit, JetBrains Mono, Space Grotesk and Fraunces (none are shipped; `ls renderer/public/fonts`) and omits Inter.

**Implementation:**
- Status line: "Wave A delivered; Wave B (verification fixes) in progress" (the close-out in B13 updates it again).
- Music: the sentence above, stated exactly.
- SFX roles per `design_templates.md` §2: `whoosh` at the start of `title_card`, `comparison`, `location` and `set_piece`; `pop` on item entrances and the `character_intro`/`relationship_map` starts; `ding` at a stat's count end; `hit` at a `reveal`'s start.
- Fonts: Poppins (Google Fonts, OFL) and Inter (rsms/inter, OFL).
- Add Natural Earth lakes to the credits (B8).

**Validate:** `grep -nE "Outfit|JetBrains|Space Grotesk|Fraunces|20 dBFS" README.md` returns nothing, and the font credits equal the TTF families in `renderer/public/fonts`.

**Blast radius:** `README.md`.

---

### B12 — E2E: computed counts, audible music

**What this means for the user:** the proof that sync and music work becomes a measurement instead of a sentence typed into a report.

**The gap:**
- `scripts/e2e.sh:502` writes "Checked: 9 scene boundaries" into the report as literal text. `evals/e2e.py check-sync`'s result is printed but never parsed.
- The per-fixture voice lines in the report template are hard-coded strings.
- No check proves music is actually **audible** in the mix, only (from B1) that it is referenced.

**Implementation:**
1. `check-sync` prints JSON `{"checked": n, "expected": len(scenes) − 1, "failures": [...]}`. `e2e.sh` parses it, asserts `checked == expected` and no failures, and writes the numbers into the report.
2. Report voice lines are read from each job's `voice.json`.
3. **Audible music:** for the step-4 job (rendered with music), measure the RMS of the final MP4's audio in the window [duration − 1.4 s, duration − 1.0 s] with ffmpeg `atrim` + `astats`. Narration is silent there (end hold) while music is fading out. Assert RMS > −60 dBFS, and record the value.

**Validate:**
- **Falsify:** make `check-sync` skip one boundary → the count assertion is red.
- **Falsify:** render the step-4 job with music removed from its timeline (a copy) → the RMS assertion is red (expect below −80 dBFS, i.e. digital silence).
- Record both.

**Blast radius:** `scripts/e2e.sh`, `evals/e2e.py`, the E2E report.

---

### B13 — Cold-cache performance budget; close-out

**What this means for the user:** today, nobody knows whether a 3-minute story really stays within their 10-minute tolerance. The claim that it did was measured with warm caches.

**The gap:** `docs/evals/e2e_2026-09-25.md`'s stage timings show `bible`, `segment` and `storyboard` at 0.0–0.2 s, meaning a warm LLM cache (and warm image cache: `assets` 0.1 s). The procedure is in `design_testing_and_validation.md` §5; no `scripts/measure_budget.sh` exists.

**Implementation:** write `scripts/measure_budget.sh` exactly per §5 (unload the model, fresh cache dir, fresh jobs dir, timed `new` / `approve` / `render` on `story_recipe_box` with music and SFX, `cache_hits` must total 0). Commit `docs/evals/budget_<date>.md`.

**Validate:** bars from §5: `new` → review ≤ 6.5 min, `render` ≤ 3.5 min, total ≤ 10 min. **Exceeding a bar is filed with per-stage timings, not tuned away.** The report must show `cache_hits = 0`, or the run does not count.

**Close-out:**
1. Full battery, bare; update §1.3.
2. Rewrite this guide to **Queue Complete** (or to the next wave, if the user has selected on Issues 3–5).
3. Move Wave B to §5.1.
4. Update `ongoing_general_errors.md` §1.
5. Stop.

---

## 4. Deferred — do NOT start

- **Issues 3, 4, 5** (`ongoing_general_errors.md`): fake writing in illustrations; timeline labels that are not dates; meaning errors in planner output. Each awaits `Your selection`. They become a wave only after the user selects.
- **D1–D9** (`ongoing_general_errors.md` §4): video input + PiP, 16:9, multi-voice, live mode, Reddit URL fetch, public-domain photos, historical borders, web editor, cloud LLM.

---

## 5. Do NOT change

### 5.1 Already delivered

**Wave A (A1–A22), verified September 25, 2026.** One line per item, with its correct commit and verification result, is in `ongoing_general_errors.md` §3. Items marked "✓" there are not to be reworked. Items marked "→ B<n>" are touched only as that B item specifies.

### 5.2 Accepted equivalents (checked September 25, 2026; do not "fix" these back)

- **The sync probe is drawn inside each scene's layer** (`SceneLayer.tsx`), not as a separate Story layer. The top-most mounted scene draws it, which gives exactly the spec's "current scene" colour, and G12 step 5 proves the flips frame-accurate.
- **The geo bbox check handles antimeridian-crossing countries** (`planner/geo.py:191`; USA, RUS, NZL, KIR). Recorded in `design_planner.md` §2.
- **`image_prompt` strips a trailing period** from `visual_description` before appending ". Wide establishing view…", avoiding "..".
- **`FitText` gives multi-line boxes 0.35 of a line of extra height** for glyph ascenders. It cannot hide a whole extra line, so real overflow is still detected.
- **The gallery computes fixture timing with a TypeScript port of `item_frames`** (`renderer/src/story/timing.ts`), because gallery fixtures have no Python compile step. It is used by the gallery only, never by `Story`.
- **`fixtures/CHECKSUMS` uses paths relative to `fixtures/`**; verify with `(cd fixtures && shasum -a 256 -c CHECKSUMS)`.
- **`plan_report.json.llm_calls` counts the storyboard stage's calls only** (select + props); voice, bible and segment report theirs in their own stage logs.
- **Node 26** works for Remotion 4.0.528; the Node 22 fallback in `design_rendering.md` §1 was not needed.

### 5.3 User decisions

**September 23, 2026 (design grilling):**
- Offline first; a template library.
- History + Reddit-style stories; text + audio inputs.
- Mixed imagery; Python + TypeScript/Remotion; fully local.
- 9:16; word-by-word karaoke captions; flat editorial vector; 1–3 min videos in about 10 min.
- Scenes + a persistent cast; single narrator; a mandatory review gate; music + SFX from a user-supplied pack.
- Live mode later, with the webcam in a corner.

**September 24, 2026:**
- **Issue 1 → A + B:** "If the story from reddit seems to be from a female's perspective then use af_heart, else use am_michael."
- **Issue 2 → A:** FLUX.2 [klein] 4B.
- Test stories must be complete stories.

### 5.4 Invariants and intentional design decisions

**New, September 25, 2026:**
- **Job-local inputs are authoritative.** No stage reads music or SFX from command-line options (B1).
- **Every planner LLM call goes through `run_with_retries`** (B3).
- **LLM-facing schemas carry no length constraints**; limits are enforced by validators and retries (B5).
- **Text over an image only where the scrim is ≥ 85%** (B7).
- **Commit scope is the item id; resolved lines cite the id, never a hash.**

**Unchanged:**
- The voice rule's asymmetry: `af_heart` only with first person **and** checkable self-identification; `am_michael` otherwise.
- The voice is decided before narration; `--voice` accepts only `af_heart` and `am_michael`.
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
- Fixtures are original texts; never commit third-party posts.

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

**New, September 25, 2026:**
- **Fixing truncation by raising `maxLength`**: the model would still be cut off at the new limit.
- **Relaxing the fallback bar** if B5 raises the fallback rate.
- **Keeping the `mflux-generate-flux2-klein` symlink.**

---

## 6. Where the contracts live

| What | Where |
|---|---|
| Product, pipeline, repo/job layout, **job-local inputs (§4)**, CLI, env vars, review gate, local-only policy, pinned models | `design_system_architecture.md` |
| JSON file shapes, source of truth, generation, sync gate | `design_data_contracts.md` |
| Ingest (**`ingest.json` music/SFX fields**), TTS, ASR, loudness, frame math, beats, captions paging, SFX scheduling | `design_audio_and_timing.md` |
| LLM backend (**error classification, `run_with_retries` everywhere, LLM-facing schemas**), voice selection §10, bible, segmentation, selection, props, validators (**text completeness**), grounding (**scale words**), fallback, eval | `design_planner.md` |
| The 16 templates (**revised §2.2, §2.13–2.15**) | `design_templates.md` |
| Palette, **composited contrast §2.1**, type, layout zones, motion, avatars, captions, illustration | `design_visual_direction.md` |
| Remotion, clock, spans, overflow, render CLI (**bundle contents**), preview, verification, sync probe | `design_rendering.md` |
| Fixtures, unit/integration rows (**new rows**), gates and falsifications (**fail-closed G10, exact G9**), E2E (**music/SFX + computed counts**), offline gate, **cold budget procedure §5**, artefacts | `design_testing_and_validation.md` |
| Live mode, video input, 16:9 | `design_future_live_and_video.md` |
| Open issues (**3–5**), resolved index (**corrected**), lessons, deferred items, decision log | `ongoing_general_errors.md` |

---

## 7. Validation standard

- **Red first.** Run the falsifying check against the unfixed code and record the failure before fixing.
- **A gate must be able to fail**, and must **fail closed**: a missing input to a check is a failure, not a skip.
- **A perfect score is a reason to look harder.** Wave A's 0.0% fallback rate was produced by truncation.
- **Measure what the viewer sees, composited.** Contrast is computed against the real background, including a worst-case white image, not only between flat tokens.
- **Invocation options are not state.** If a later stage needs it, it lives in the job.
- **Warm caches measure nothing about a cold budget.**
- **Read exit codes bare. A gate that did not run is not a pass. Open every artefact and describe it.**
- **A check over a hand-written list only verifies the list**; pair it with a containment check.
- **Never loosen a bar to pass it.** File it with the measurement.

---

## 8. THE LOOP

```
(1) Is there an approved item? Wave B, B1–B13, in §2 order. If all are done,
    STOP. Never start Issues 3–5 or D1–D9 without a user selection.
    Never fill in a `Your selection:` line.
(2) Read the item and EVERY design section it names before writing code.
(3) RED FIRST: run the item's falsifying check on the unfixed code; record
    the failure. If it passes on unfixed code, the check is wrong: fix the check.
(4) Build only what the item says. Nothing from §5.5.
(5) GREEN: run the item's checks; then the falsification (break it again,
    see red, restore, see green).
(6) Open every artefact the item produces and describe what it shows.
(7) Full battery, bare. Update §1.3. NOT RUN is legal; blank is not.
(8) ONE commit, scope = item id: `fix(bN): …`. WHY + red/green runs in the
    body. Add ONE line under "Wave B" in ongoing_general_errors.md §3, citing
    `git log --grep "(bN)"`, never a hash. Do not amend after pushing.
(9) git push origin main.
(10) Next item.
```

---

## 9. Definition of Done: Wave B

- [ ] B1–B13 each landed as one pushed commit scoped to its id, each with its red run and green run recorded.
- [ ] §1.3: every gate G1–G14 green, measured this session, read bare.
- [ ] Music and SFX survive the review journey (E2E step 4 assertions) and are **audible** in the final MP4 (B12 RMS check).
- [ ] The new planner eval shows 0 newline strings and 0 completeness failures, and every §9 bar is met or filed.
- [ ] The contrast test covers the image scrim (worst case, white) and every map pair.
- [ ] `docs/evals/budget_<date>.md` is committed from a cold run with `cache_hits = 0`, bars met or filed.
- [ ] README states only what is true.
- [ ] This guide rewritten to **Queue Complete** (or to the user-selected next wave). **Then stop. Do not invent work.** The only legitimate triggers for new work are a user selection on Issues 3–5 or D1–D9, or a gate going red (investigate and **file** it).

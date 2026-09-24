# Agent Execution Guide — Active Build: Wave A (Offline MVP, 21 items) — September 23, 2026

**You are an engineering agent with no memory of this project.** Nothing has been built yet. This repository contains a complete design (`docs/design_*.md`), three frozen fixture stories, and this guide. Your job is to **build and validate** the offline MVP described below, one item at a time, in order.

**What is approved:** Wave A, items **A1–A21** in §3, in the order of §2. **What NOT to touch:** everything in §5 (delivered work, accepted equivalents, user decisions, invariants, rejected options). Every one of them was made by the user or deliberately by the designer. **What does not exist yet and must not be started:** everything in §4 (deferred).

**Every number and literal string in this document and in the design docs is a decision, not a suggestion.** Implement as written; do not substitute your own values. If a value is genuinely impossible, keep the *intent*, deviate minimally, say so in the commit body, and add it to §5.2 (accepted equivalents). If the design itself cannot work, **STOP and file it in `docs/ongoing_general_errors.md` with options and a `Your selection: _____` line. Do not improvise, and never fill in a selection line yourself.**

**What the product is, in one paragraph.** A local-only CLI that turns a **text story** (narrated by local TTS) or an **audio narration** into a **1080×1920 animated explainer video**: flat editorial vector scenes chosen from a library of 16 templates, in sync with the voice, with word-by-word karaoke captions, a persistent cast of vector avatars, locally generated illustrations of places and objects, and optional music and SFX. Every video **stops for human review** before the final render. The long-term goal is live mode (speak in real time and the visuals follow), so the renderer is built to be clock-agnostic from day one.

---

## 0. Standing constraints (apply to every item)

1. **The battery is the regression bar.** After every item, run `scripts/battery.sh` (full, not `--fast`, once G11 exists) and record the numbers in §1. **Read every exit code bare.** `cmd | tail` reports `tail`'s exit status, always 0.
2. **Fully local at runtime.** No cloud API, no network except loopback, ever, at runtime (`design_system_architecture.md` §7). Setup may download.
3. **Python (Pydantic) is the source of truth for every contract.** TypeScript types, JSON Schemas, the template registry JSON and the icon map are **generated**. Never hand-edit `renderer/src/generated/`, `schema/`, or `data/geo/country_bboxes.json`.
4. **Templates read time only through the clock** (`design_rendering.md` §3).
5. **The review gate is mandatory.** There is no auto-approve, and none may be added under any name (`design_system_architecture.md` §5).
6. **The planner never crashes the pipeline and never shows an ungrounded fact** (`design_planner.md`).
7. **One item = one Conventional Commit** (see `.agents/skills/commit_message_guidelines/SKILL.md`), with the WHY in the body, including the falsification runs (red, then green). **Push after every item** (`git push origin main`). The remote is the private GitHub repo `yelouis/animated_infographics`.
8. **Record the resolution as part of the item:** one line in `ongoing_general_errors.md` §3 (Resolved index) and any new gate numbers in §1 below, **in the same commit**.
9. Detailed behaviour lives in the design docs. This guide points at them and does not restate them. **When this guide and a design doc disagree, stop and file it.** Do not pick one.

---

## 1. Verified baseline (September 23, 2026, before any code)

### 1.1 Environment (verified by the design session)

| Fact | Value |
|---|---|
| Machine | Apple **M4 Max**, **64 GB** unified memory, macOS (Darwin 25.6.0) |
| Free disk | 118 GiB. Models need ≈ 35 GB (planner 19 GB, image model, Whisper, Kokoro). |
| ffmpeg / ffprobe | **8.1** (Homebrew) |
| Node | **v26.5.0** (see `design_rendering.md` §1 for the Node 22 fallback rule) |
| System Python | 3.14.6. **Not used.** The project pins **3.12** through uv. |
| uv | present (`~/.local/bin/uv`) |
| Ollama | **0.33.0**. Installed: `glm4`, `gemma4:latest` (8B), `qwen2.5vl:7b`, `moondream`, `tinyllama`. ⚠️ **The planner model `gemma4:26b` is NOT pulled.** A2 pulls it. |
| espeak-ng | ⚠️ **NOT installed.** A2 installs it (Kokoro's fallback phonemiser). |
| mflux | ⚠️ **NOT installed.** A2 installs it. |
| macOS `say` | present (fixture generation) |
| gh | 2.98.0, logged in as `yelouis` |

### 1.2 Repository

The design commit contains `docs/`, `fixtures/scripts/*.txt` (three frozen stories; SHA-256 in `design_testing_and_validation.md` §1), `AGENTS.md`, `CLAUDE.md`, `README.md`, `.gitignore`, `.agents/skills/`. **No code, no gates.**

### 1.3 Gates

Each gate is created by the item named. **Replace "NOT BUILT" with the measured result in the commit that creates the gate, and keep this table current thereafter.** Definitions and falsifications: `design_testing_and_validation.md` §3.

| # | Gate | Result |
|---|---|---|
| G1 | `uv run ruff check .` | NOT BUILT (A1) |
| G2 | `uv run ruff format --check .` | NOT BUILT (A1) |
| G3 | `uv run mypy src` | NOT BUILT (A1) |
| G4 | `uv run pytest -q -m "not slow"` | NOT BUILT (A1) |
| G5 | `npm --prefix renderer run typecheck` | NOT BUILT (A1) |
| G6 | `npm --prefix renderer run lint` | NOT BUILT (A1) |
| G7 | `npm --prefix renderer test` | NOT BUILT (A1) |
| G8 | `./scripts/check_schema_sync.sh` | NOT BUILT (A4) |
| G9 | `./scripts/check_renderer_purity.sh` | NOT BUILT (A9) |
| G10 | `./scripts/check_gallery.sh` | NOT BUILT (A16) |
| G11 | `uv run pytest -q -m slow` | NOT BUILT (A7) |
| G12 | `./scripts/e2e.sh` | NOT BUILT (A15; completed in A21) |
| G13 | `./scripts/check_offline.sh` | NOT BUILT (A21) |
| G14 | `uv run infographics doctor` | NOT BUILT (A2) |

⚠️ **A gate that could not run is recorded as NOT RUN with the reason, never left blank and never marked green.**

---

## 2. Execution order

| # | Item | Why this position |
|---|---|---|
| A1 | Bootstrap | Nothing can be verified without toolchains and a battery. |
| A2 | Setup script + `doctor` | Every later item needs models, fonts and geodata on disk, and a single command that says what is missing. |
| A3 | Fixtures | Every test from A6 on runs against them. |
| A4 | Data contracts + schema sync | Both runtimes code against these types. Changing them later costs a cross-language refactor. |
| A5 | Job store, CLI, review gate | Locks the gate's invariants **before** anything can render. A gate retrofitted after a working render gets bypassed "temporarily". |
| A6 | Timing core (pure) | Beats, captions and frame math are the sync guarantee. Pure functions, fully testable without models. |
| A7 | Narration (Kokoro) | The primary input path. Produces the ground-truth timings A8 is measured against. |
| A8 | Transcription (Whisper) | The second input path, measured against A7's ground truth. |
| A9 | Renderer foundation + `kinetic_quote` | The spine: clock, Story, captions, audio, sync probe, overflow detection. `kinetic_quote` first because it is the planner's universal fallback. |
| A10 | LLM backend | Everything in the planner goes through it. |
| A11 | Bible + geo | Segmentation, selection and props all need the cast/places. |
| A12 | Segmentation | Needs A6's rules and A11's context. |
| A13 | Storyboard + planner eval | Needs A4's props models (not the drawn templates). Unimplemented templates render as placeholders until A19. |
| A14 | Compile + preview | Closes the plan→review loop. |
| A15 | Final render + verification → **walking skeleton** | Proves text → MP4 end to end, with sync verified in the encoded file, before the visual library grows. |
| A16 | Visual primitives + gallery gate | The shared parts every template uses, and the gate that holds them. |
| A17 | Templates: statement set (6) | |
| A18 | Templates: people set (5) | Needs A16's Avatar. |
| A19 | Templates: place & time set (4) + delete placeholder | Needs A16's MapView. The last template removes the placeholder. |
| A20 | Illustrations | Needs A19's `location`/`set_piece` to show them; last because every template already has an icon fallback. |
| A21 | E2E, offline gate, performance budget, README | Proof over the whole system; closes the wave. |

---

## 3. The items

Each item lists what it means for the user, what to build (pointing at the governing design sections), how to validate it (with the falsification that proves the check can fail), and the blast radius.

### A1 — Bootstrap

**What this means for the user:** a repository another agent can build in and a battery that says whether it is healthy.

**Build:**
1. The repo already exists locally and on GitHub with one design commit. **Do not rewrite history.**
2. `pyproject.toml` (src layout, package `animated_infographics`, distribution `animated-infographics`, `requires-python = ">=3.12,<3.13"`, script `infographics = "animated_infographics.cli:app"`); `.python-version` = `3.12`. Runtime deps now: `typer`, `pydantic>=2.8`, `httpx`, `numpy`, `soundfile`, `pysbd`, `pillow`, `rich`. Dev: `pytest`, `ruff`, `mypy`. ML deps are added in the items that use them (A7 `kokoro>=0.9.4`, A8 `mlx-whisper` and `jiwer`).
3. Ruff: line-length 100; rules `E,F,I,B,UP`. Mypy: `disallow_untyped_defs = true` for `src/`; `ignore_missing_imports` only for `kokoro`, `mlx_whisper`, `pysbd`, `soundfile`, `misaki`. Pytest: register the `slow` marker.
4. `renderer/`: a TypeScript Remotion project created by hand (not an interactive generator). Dependencies: `remotion`, `@remotion/cli`, `@remotion/bundler`, `@remotion/renderer`, `@remotion/fonts`, `@remotion/layout-utils`, **all pinned to the same exact version** (`npx remotion versions` must report no mismatch), plus `react`, `react-dom`, `typescript`, `tsx`, `vitest`, `eslint` + `@remotion/eslint-plugin`, `ajv`, `d3-geo`, `topojson-client`, `world-atlas@2`, `@phosphor-icons/react`, `json-schema-to-typescript`. Scripts: `typecheck` (`tsc --noEmit`), `lint`, `test` (`vitest run`, **without** `--passWithNoTests`).
5. One smoke test on each side (`tests/test_import.py`; `renderer/src/smoke.test.ts`), so G4 and G7 can be green *and* red.
6. `scripts/battery.sh` per `design_testing_and_validation.md` §3: runs every gate that exists, bare, prints `gate | exit | key number`, shows `NOT BUILT (A#)` for the rest, and exits non-zero if any built gate fails. `--fast` flag.

**Validate:** `uv sync` → 0; `npm --prefix renderer ci` → 0; `npx remotion versions` (in `renderer/`) → no mismatch; G1–G7 green; `scripts/battery.sh` → 0. **Falsify:** add an unused import → G1 red and `battery.sh` non-zero; revert → green. Record both.

**Blast radius:** §1.3 rows G1–G7.

---

### A2 — Setup script and `doctor`

**What this means for the user:** one command prepares a fresh Mac, and one command says exactly what is missing.

**Build:**
1. `scripts/setup.sh` (idempotent): `brew install espeak-ng` if absent · `uv sync` · `npm --prefix renderer ci` · `ollama pull gemma4:26b` · `uv tool install mflux` · pre-download `mlx-community/whisper-large-v3-turbo`, Kokoro-82M plus voice `af_heart`, and the FLUX.2 klein **4B** weights · `npx remotion browser ensure` in `renderer/` · fonts (§3 of `design_visual_direction.md`): Poppins Bold/ExtraBold + `OFL.txt` from the `google/fonts` repository (`ofl/poppins/`), Inter Medium/SemiBold/Bold static TTFs from the official `rsms/inter` release archive (`extras/ttf/`) + its licence → `renderer/public/fonts/` (**committed**) · GeoNames `cities15000.zip` (unzipped) and `countryInfo.txt` → `data/vendor/` (**gitignored**), verified against `data/vendor/CHECKSUMS` (**committed**; written on the first download in this item).
2. `renderer/scripts/gen-country-bboxes.ts`: `world-atlas` `countries-50m.json` + `countryInfo.txt` (ISO-numeric → ISO3) → `data/geo/country_bboxes.json` (`{ISO3: [minLon, minLat, maxLon, maxLat]}`, from `d3.geoBounds`). Features without an id are skipped and listed in the script's output. Committed; generated (header comment).
3. `infographics doctor` (`doctor.py`): one line per check, `OK` or `MISSING <what> — run: <fix>`. Checks: Python 3.12; ffmpeg; ffprobe; espeak-ng; Ollama reachable at `127.0.0.1:11434`; the planner model (default `gemma4:26b`, overridable by `INFOGRAPHICS_PLANNER_MODEL`) listed by `/api/tags`; `mflux-generate-flux2-klein` on PATH; Whisper, Kokoro and klein-4B weights in the HF cache; `renderer/node_modules`; the Remotion headless browser (find where `ensure` installs it and check that path; name it in a code comment); the five font files; `data/vendor/*` checksums; `data/geo/country_bboxes.json`. Exit **4** if any is missing.

**Validate:** `setup.sh` twice → both 0 (idempotent); `doctor` → 0. **Falsify:** `INFOGRAPHICS_PLANNER_MODEL=gemma4:not-a-model uv run infographics doctor` → exit 4 naming it; temporarily rename one font → exit 4 naming it; restore → 0. Record the installed version of **every** tool and model (Ollama model digest, mflux version, Remotion version, kokoro version, mlx-whisper version) in §1.1.

**Blast radius:** §1.1, §1.3 G14; `README.md` gains a Setup section.

---

### A3 — Fixtures

**What this means for the user:** every claim about quality is measured on the same inputs, including the audio path and the music/SFX mix.

**Build:** per `design_testing_and_validation.md` §1: `scripts/make_fixtures.sh` generates `fixtures/audio/molasses_flood_say.m4a`, `fixtures/music/test_bed.wav`, and the five SFX files including the unknown-role `clap_test.wav`. Write `fixtures/expected/*.json` exactly as listed there. Write `fixtures/CHECKSUMS` over every fixture file.

**Validate:** the three scripts' SHA-256 values equal the frozen values in the testing doc (**if not, stop: the fixtures were edited**). `shasum -a 256 -c fixtures/CHECKSUMS` → 0. ffprobe every generated file: durations as specified (±10 ms), sample rates as specified. **Falsify:** checksum-verify a copy with one changed byte → non-zero.

**Blast radius:** none beyond `fixtures/`, `scripts/make_fixtures.sh`.

---

### A4 — Data contracts and schema sync

**What this means for the user:** the plan they review and the video that renders are guaranteed to describe the same thing.

**Build:** every model in `design_data_contracts.md` §2–7; the template registry (§8) with all **16** templates' props models, slots, SFX cues, `spread` values and requirements, transcribed from `design_templates.md` §2; the icon allow-list (`design_templates.md` §4); `contracts/export.py` producing every generated file in `design_data_contracts.md` §1 (including `iconMap.ts` with explicit named imports); `scripts/check_schema_sync.sh`, which also covers `data/geo/country_bboxes.json` (regenerate and diff).

**Validate:** G8 green. Unit tests: an unknown key is rejected; `schema_version: 2` is rejected; one valid and one invalid props example per template (`tests/data/props_examples.json`). G5 compiles `iconMap.ts`. **Falsify (all three):** hand-edit one generated file → G8 exit 1; **empty** one generated file → G8 exit 1 (not a vacuous pass); misspell one icon in the allow-list and re-export → G5 red.

**Blast radius:** §1.3 G8.

---

### A5 — Job store, CLI and the review gate

**What this means for the user:** nothing ever renders without their approval of exactly the plan that renders.

**Build:** `jobs.py` and `cli.py` per `design_system_architecture.md` §4–6: job ids, directory layout, `state.json`, stage runner with `stage_input_sha256` skip logic and downstream invalidation, `plan_sha256`, every command and exit code. Stages that do not exist yet raise a clear `stage not implemented: <name>` (exit 1). Tests drive the state machine with **fake stage functions** that write minimal valid files.

**Validate:** unit tests for every refusal in §5 of the architecture doc (exit **3**) and for invalidation (re-running `segment` deletes `storyboard.json`, `timeline.json` and `preview/`). **Falsify:** delete the `approval.plan_sha256 == plan_sha256(now)` comparison → the "edit after approval" test must fail; restore.

**Blast radius:** none beyond these modules.

---

### A6 — Timing core

**What this means for the user:** the visuals and the highlighted caption word land on the spoken word, and scene pacing stays watchable.

**Build:** `timing/frames.py`, `timing/beats.py`, `timing/captions.py` per `design_audio_and_timing.md` §6–8; the SFX scheduler (§9) and `item_frames`/`count_frames` (`design_templates.md` §1 rule 5) as pure functions. No I/O and no models.

**Validate:** every unit case listed for these modules in `design_testing_and_validation.md` §2, including the 500-stream property test. **Falsify:** replace round-half-up with Python's `round` → the `ms_to_frame(550) == 17` test fails; change `CAPTION_MAX_WORDS` to 4 → the paging test fails.

**Blast radius:** §1.3 G4 count.

---

### A7 — Narration (Kokoro)

**What this means for the user:** a pasted story becomes a clean, consistent narration with exact word timings.

**Build:** `ingest.py`, `audio/narrate.py`, `audio/loudness.py` per `design_audio_and_timing.md` §1, §2, §5. Add `kokoro>=0.9.4`. Wire the `ingest` and `narrate` stages into the runner. Produce **Issue 1's evidence**: the first paragraph of `molasses_flood.txt` in `af_heart`, `af_bella`, `am_michael`, `bm_george` → `docs/evals/voices/<voice>.wav`.

**Validate (slow tests, G11 created here):** on all three fixtures, `transcript.json` satisfies every invariant; `narration.json` offsets are exact (the sum of segment samples plus inserted silence equals the pre-resample WAV length **to the sample**); `audio/narration.wav` is 48 kHz mono s16 at −16 ± 0.5 LUFS integrated (ebur128). Record `narrate` wall time on `emu_war` (bar ≤ 60 s) and its narration duration. **Falsify:** drop `PAUSE_BETWEEN_SENTENCES_MS` from the offset sum only → the exact-offset test fails.

**Blast radius:** §1.3 G11; Issue 1 in `ongoing_general_errors.md` gets "evidence ready: `docs/evals/voices/`".

---

### A8 — Transcription (Whisper)

**What this means for the user:** their own recordings work, and we know how far ASR timing can be trusted, which live mode will depend on.

**Build:** `audio/transcribe.py` per `design_audio_and_timing.md` §3, §5. Add `mlx-whisper` and dev dep `jiwer`. Wire the `transcribe` stage.

**Validate (slow):** WER ≤ **8%** on `molasses_flood_say.m4a` vs the source text; word-start error of Whisper on **Kokoro's** `molasses_flood` narration vs Kokoro's own timestamps: median ≤ **80 ms**, p95 ≤ **250 ms**; `transcribe` of the 2-minute `emu_war` narration ≤ **45 s**. **Record the measured values.** **Falsify:** compute WER against `aita_wedding_cake.txt` instead → the bar fails.

**Blast radius:** §1.3 G11 count.

---

### A9 — Renderer foundation (+ `kinetic_quote`)

**What this means for the user:** the look, the captions, the sound and the sync exist, before any intelligence is attached.

**Build:** theme tokens (`design_visual_direction.md` §2–5, 8); font loading; the clock (`design_rendering.md` §3); `Story` (§1, §4, §5) with Ajv validation, background, scene spans, captions layer, audio, sync probe; `FitText` with overflow detection (§6); `render.ts` with `stills`/`media`/`gallery` modes (§2); `kinetic_quote` (`design_templates.md` §2.2) with its three gallery fixtures; a **placeholder** component for every other template (a `bgRaised` card showing the template name and `NOT YET IMPLEMENTED`); `scripts/check_renderer_purity.sh` (G9). A hand-written smoke timeline at `renderer/test-data/timeline_smoke.json` (3 scenes, captions, `fixtures/music/test_bed.wav` standing in for narration).

**Validate:** G9 green; **falsify** it with `useCurrentFrame()` in `kinetic_quote` → exit 1; revert → 0. Render the smoke timeline (`media`) → ffprobe dimensions, fps, frame count = `duration_frames`; `--sync-probe` flips at both scene boundaries (±0 frames). `gallery` for `kinetic_quote` → zero overflow on `max`. **Open the three stills and look at them.** Describe in the commit body what they show.

**Blast radius:** §1.3 G9.

---

### A10 — LLM backend

**What this means for the user:** planning runs locally, deterministically on re-runs, and survives bad model output.

**Build:** `planner/llm.py` per `design_planner.md` §1: Ollama backend, response cache (`cache/llm/`, relocatable with `INFOGRAPHICS_CACHE_DIR`), retry protocol, `INFOGRAPHICS_PLANNER_MODEL` override, a `DependencyError` (exit 4) when Ollama is down or the model is not pulled.

**Validate:** unit tests with `httpx.MockTransport` (retry messages, seed per attempt, cache key stability). Slow: **20/20** schema-conforming responses from `gemma4:26b` on a toy schema with an `enum` and a `maxLength`; confirm `think: false` is honoured (no thinking content in the response; record mean latency). **Falsify:** a non-existent model → exit 4 with its name.

**Blast radius:** none.

---

### A11 — Bible and geo resolution

**What this means for the user:** the same person looks the same all video long, and places land on the map where they really are.

**Build:** `planner/prompts/bible.md`, `planner/bible.py`, `planner/geo.py` per `design_planner.md` §2 (post-processing repairs, gazetteer matching with `alternatenames`, bbox check with a 0.5° margin, the fallback bible). Wire the `bible` stage.

**Validate:** unit: Boston resolves to USA by gazetteer; `Constantinople` resolves to Istanbul through `alternatenames`; LLM coordinates outside the country bbox are nulled (`geo_source: "none"`); duplicate colour slots are repaired deterministically. Slow: the three fixtures' expectation checks (`design_testing_and_validation.md` §1): Boston by gazetteer; `Maya` plus a narrator; Meredith plus an `AUS` place. A warm-cache re-run is byte-identical. **Falsify:** remove the bbox check → the out-of-bbox unit test fails.

**Blast radius:** none.

---

### A12 — Segmentation

**What this means for the user:** each scene carries one idea and stays on screen long enough to read.

**Build:** `planner/prompts/segment.md`, `planner/segment.py` per `design_planner.md` §3, then `timing/beats.py` (A6) on every result. Wire the `segment` stage.

**Validate:** unit: the partition validator rejects a gap, a duplicate, an out-of-order index; the fallback yields one group per sentence. Slow: every fixture's `beats.json` tiles the narration; every beat k ≥ 1 is within [1,500, 8,000] ms (or logged "no valid split"); record beat counts and the duration histogram. **Falsify:** skip the merge pass → the bounds assertion fails on at least one fixture (if it does not, construct a synthetic transcript where it must, and say so).

**Blast radius:** none.

---

### A13 — Storyboard planning and the planner eval

**What this means for the user:** every beat gets a fitting visual, numbers on screen are exactly the numbers said, and nothing breaks when the model misbehaves.

**Build:** `select.md`, `props.md`, `planner/select.py`, `planner/props.py`, `planner/validate.py`, `planner/grounding.py`, `textfit.py` per `design_planner.md` §4–8 (allowed-template computation, 6-beat windows, rules R1–R5, the per-scene fallback ladder, deterministic `title_card` and `kinetic_quote`, `plan_report.json`); `evals/planner.py` (§9). Wire the `storyboard` stage.

**Validate:** unit cases for grounding, validators and rules per the testing doc §2. **Falsify:** stub `numbers()` to return every number times 10 → the `1500`-vs-`150` rejection test must go **red** (1500 now matches) and the correct-stat test must go **red** (it no longer matches). That proves the tests exercise extraction rather than passing vacuously. Restore → green. Run the planner eval → `docs/evals/planner_<date>.md` committed, **all bars in `design_planner.md` §9 met**, and the independent re-validation of the final storyboards shows 0 violations. If a bar fails: iterate on prompts (each change re-runs the eval). If it still fails, run the eval on `qwen3.6:35b` and **file the model choice as an issue**. Do not loosen a bar.

**Blast radius:** §1.3 G4/G11 counts.

---

### A14 — Compile and preview

**What this means for the user:** after `new`, they get a contact sheet and a readable storyboard to judge the whole video in a minute, and a way to fix what they don't like.

**Build:** `compile.py` (`design_data_contracts.md` §7, `design_audio_and_timing.md` §6–9, `design_templates.md` §1 rule 5); `audio/mix_prep.py` (music/SFX normalisation, role parsing, unknown roles ignored with a warning); an `assets` stage that, until A20, writes a manifest with every image `null`; `preview.py` (`design_rendering.md` §7). Wire `compile`, `preview`, `approve`'s overflow refusal, and `new` end-to-end to `awaiting_review`.

**Validate:** every compiled timeline validates in Python **and** in the renderer (Ajv); unit tests for tiling, hidden captions on the narrated title only, the 24-frame SFX gap, round-robin SFX files. `infographics new fixtures/scripts/molasses_flood.txt --music … --sfx-dir …` → exit 0, `awaiting_review`. **Open `contact_sheet.png` and `storyboard.md` and look at them.** Commit a copy of the contact sheet to `docs/evals/assets/<date>/a14_molasses_contact_sheet.png`. **Falsify:** a unit test with a `report.json` whose `overflow` is non-empty → `approve` exits 3; an edited storyboard with an ungrounded `stat_callout` → `preview` exits 2 and names the field.

**Blast radius:** none beyond the modules.

---

### A15 — Final render and output verification (walking skeleton)

**What this means for the user:** the first real MP4. Placeholders stand in for unbuilt templates, but timing, captions, sound and the review gate are all proven.

**Build:** `render.py` per `design_rendering.md` §8 (settings, `verify.json`); `scripts/e2e.sh` steps 1–6 of `design_testing_and_validation.md` §4 (G12).

**Validate:** G12 green: exit codes exactly as specified at every step, `verify.json` all true for both the text and the audio input, the sync probe flipping at every scene boundary. **Falsify:** render with a timeline whose `duration_frames` was altered in a copy → the frame-count check fails; remove the `approve` step from the script → step 2's expected-3 assertion catches it. **Open three frames** of `final.mp4` (start, middle, end, extracted with ffmpeg) and describe them in the commit body.

**Blast radius:** §1.3 G12.

---

### A16 — Visual primitives and the gallery gate

**What this means for the user:** a consistent cast and a consistent look, held in place by a gate that catches visual regressions.

**Build:** `Avatar` (`design_visual_direction.md` §6, all parameters, all 8 expressions), `Icon` (via the generated `iconMap.ts`), `Chip`, `Panel`, `Bubble`, `MapView` framing math (`design_templates.md` §2.15) with vitest tests; an `avatar_sheet` gallery entry (all 8 expressions × 4 parameter combinations); `scripts/check_gallery.sh` with golden diff, overflow check and hold-motion check, plus `--update` (`design_testing_and_validation.md` §3); the contrast pytest (`design_visual_direction.md` §2).

**Validate:** G10 green over `kinetic_quote` and `avatar_sheet`. **Open the avatar sheet**: every expression must be recognisable at 140 px, so check the downscaled view as well. **Falsify:** change one palette colour → golden diff red; freeze `kinetic_quote`'s hold motion → the motion check red; make `ink`-on-cast legal in a test copy of the palette → the forbidden-pair assertion red.

**Blast radius:** §1.3 G10.

---

### A17 — Templates: statement set

`title_card`, `stat_callout`, `icon_list`, `reveal`, `cause_effect`, `comparison` (`design_templates.md` §2.1, 2.3–2.7).

**What this means for the user:** numbers, lists, twists and cause-and-effect stop looking like placeholders.

**Build:** each template exactly per its section, with its three gallery fixtures and goldens. **Validate:** G10 green with zero overflow on every `max` fixture (if `max` cannot fit, lower the limit in `design_templates.md` **and** the registry in the same commit; never shrink below `size_min`). **Open every golden** and state in the commit body that it matches its layout spec (positions, colours, text on cast colour is navy). Re-render the molasses E2E and look at the contact sheet: the placeholders for these six are gone.

---

### A18 — Templates: people set

`character_intro`, `dialogue`, `text_thread`, `emotion_beat`, `relationship_map` (§2.8–2.12).

**What this means for the user:** Reddit-style stories come alive: who said what, the text thread, the reaction, who is related to whom.

**Build/Validate:** as A17. Additionally: the `aita_wedding_cake` contact sheet shows `text_thread` or `dialogue` for the texted quote. If the planner chose neither, file it with the plan report attached rather than forcing it.

---

### A19 — Templates: place & time set, and delete the placeholder

`location`, `set_piece`, `map_focus`, `timeline` (§2.13–2.16).

**What this means for the user:** history stories get their maps, timelines and places.

**Build/Validate:** as A17, with the icon fallback path (image `null`) as the `typical` fixture until A20. Then **delete the placeholder component.** Add a vitest **containment test** in both directions: every template name in `templateRegistry.json` has a component file, and every component file in `src/templates/` is in the registry. **Falsify:** remove one component → red. `grep -rnF "NOT YET IMPLEMENTED" renderer/src` returns nothing; corroborate that absence with the containment test count (16).

---

### A20 — Illustrations

**What this means for the user:** places and key objects get real illustrations in one consistent style, and a failure never breaks a video.

**Build:** `assets/illustrate.py` and the `assets` stage per `design_visual_direction.md` §7 (4B only, prompts, seed, cache, manifest, 180 s timeout, icon fallback on failure). Produce **Issue 2's evidence**: every place and set-piece prompt from the three fixture bibles, rendered with FLUX.2 klein 4B and with Z-Image-Turbo (same seeds) → `docs/evals/image_models_<date>.png` (side by side, labelled) plus `docs/evals/image_models_<date>.md` (per-image wall time, total). Swap `location`/`set_piece` `typical` fixtures to use a real generated image and update their goldens.

**Validate:** slow: second generation of the same prompt is a cache hit in < 1 s; with `INFOGRAPHICS_IMAGE_TIMEOUT_S=1` every image fails, the manifest says `failed`, `preview/report.json` lists them, and the preview still completes with icon fallbacks. **Falsify:** that timeout run *is* the falsification of the fallback path. **Open the molasses and emu_war contact sheets**: images must be flat vector, text-free and on-palette. If they are not, file it with the images; do not silently change the style prompt beyond small wording fixes noted in the commit.

**Blast radius:** Issue 2 gets "evidence ready".

---

### A21 — E2E, offline gate, performance budget, README

**What this means for the user:** proof the whole thing works, locally, within their 10-minute tolerance, and instructions to use it.

**Build:** complete `scripts/e2e.sh` (steps 7–8 and the committed report, `design_testing_and_validation.md` §4); `scripts/check_offline.sh` + `scripts/offline.sb` (§6); re-run the planner eval with all 16 templates live; measure the performance budget (§5); write the README Usage section (`new` → look at the contact sheet → edit → `preview` → `approve` → `render`; the music/SFX role naming convention; credits: GeoNames CC BY 4.0, fonts OFL, Phosphor MIT, Natural Earth, and the Remotion licence note).

**Validate:** G12 and G13 green; G13's self-check falsified once (remove the `deny` line → the self-check must fail) and restored; `docs/evals/e2e_<date>.md` and `docs/evals/planner_<date>.md` committed; performance bars met **or filed with per-stage timings**; **the full battery green**, every number recorded in §1.3.

**Close-out:** rewrite this guide's title and §2–§3 to **Queue Complete** mode, move Wave A to "Already delivered" (§5.1) with one line per item, and update `ongoing_general_errors.md` §1. **Then stop. Do not invent work** (§9).

---

## 4. Deferred — do NOT start

Each needs the user's selection in `ongoing_general_errors.md` §4 first: **D1** video input + PiP · **D2** 16:9 output · **D3** multi-voice narration · **D4** live mode · **D5** Reddit URL fetch · **D6** public-domain photo sourcing · **D7** historical map borders · **D8** web editor · **D9** a cloud LLM backend. Their design constraints are in `design_future_live_and_video.md`. Honouring those constraints (F1–F6) is in scope now; building the features is not.

---

## 5. Do NOT change

### 5.1 Already delivered

Nothing yet. Items move here, one line each, as they land.

### 5.2 Accepted equivalents

None yet. When an implementation reaches a spec's intent by a different structure, record it here with the reason, so the next pass does not "fix" it back.

### 5.3 User decisions (September 23, 2026, design grilling)

Offline first · template library (not generated code or generated video) · first content: **history + Reddit-style stories** · MVP inputs: **text script + audio only** · imagery: vector + local illustrations + open map data · **Python pipeline + TypeScript/Remotion renderer** · **fully local** (no paid or cloud APIs) · **9:16 first** · **word-by-word karaoke captions** · **flat editorial vector** style · 1–3 min videos in ~10 min · **scenes + persistent cast** · **single narrator** · **mandatory review gate** · **music + SFX from a user-supplied pack** · live mode later with **webcam in a corner**.

### 5.4 Invariants and intentional design decisions

- **Cast members are vector avatars only**, never generated images: a persistent look with changeable expressions. Illustrations are for places and set pieces only.
- **No auto-approve**, under any name. Tests use the real `approve`.
- **`approve` refuses while any text overflows.**
- **Scenes lead the voice by 200 ms; captions never lead.**
- **Scenes are placed at absolute frames. Do not switch to `TransitionSeries`**: it shortens the timeline and desyncs every later scene.
- **Item and count timings are computed once, in Python**, and shared by SFX and visuals.
- **Grounding is a hard gate**: numbers, dates and quotes on screen must come from the narration.
- **Place coordinates come from the gazetteer first**; LLM coordinates are accepted only inside the country bbox (+0.5°).
- **Text on cast colours and `highlight` is navy `bg`**, never `ink` (1.52–3.21 : 1, measured).
- **Python is the contract source of truth**; generated files are never hand-edited.
- **`kinetic_quote` is the universal fallback** and must always validate by construction.
- **Captions are hidden only during a `title_card` whose beat is the narrated title.**
- **The FLUX.2 klein 9B is non-commercial: never use it.**
- **Beat boundaries are not human-editable** in the MVP.
- **`sandbox-exec` offline gate stays**, even though the tool is deprecated. If it breaks, file it.

### 5.5 Assessed and rejected — do NOT re-propose

Live-first or parallel offline/live tracks · LLM-written code per scene (hybrid or pure) · text-to-video/image-generated scenes · video input in the MVP · Reddit URL fetching in the MVP · vector-only imagery · illustration-heavy scenes · generated portraits for cast · TypeScript-only or Python-only (Manim/MoviePy) stacks · Claude or any cloud API · both aspects at once, or 16:9 first · sentence subtitles, no captions, or a caption toggle · paper-cutout, whiteboard or dark-cinematic styles · a persistent continuous stage or a pure slideshow · multi-voice in the MVP · an optional review gate or a web editor · music-only or no audio bed · `TransitionSeries` for transitions · TypeScript as the schema source · trusting LLM coordinates without a check · re-transcribing TTS audio with Whisper for timings (Kokoro's own timestamps are exact).

---

## 6. Where the contracts live

| What | Where |
|---|---|
| Product, pipeline, repo/job layout, CLI, exit codes, review gate, local-only policy, pinned models | `design_system_architecture.md` |
| JSON file shapes, source of truth, generation, sync gate | `design_data_contracts.md` |
| Ingest, TTS, ASR, loudness, frame math, beats, captions paging, SFX scheduling | `design_audio_and_timing.md` |
| LLM backend, prompts, bible, segmentation, selection, props, validators, grounding, fallback, planner eval | `design_planner.md` |
| The 16 templates | `design_templates.md` |
| Palette (with measured contrast), type, layout zones, motion, background, avatars, captions style, illustration | `design_visual_direction.md` |
| Remotion project, clock, spans, overflow, render CLI, preview, final render, verification, sync probe | `design_rendering.md` |
| Fixtures, unit/integration layers, the 14 gates and their falsifications, E2E, offline gate, budget, artefacts | `design_testing_and_validation.md` |
| Live mode, video input, 16:9: constraints now, sketches later | `design_future_live_and_video.md` |
| Phase overview | `master_implementation_plan.md` |
| Open issues, selections, deferred items, resolved index | `ongoing_general_errors.md` |

---

## 7. Validation standard

- **A gate must be able to fail.** Before trusting a gate, name the input that turns it red, run it, and record the red run next to the green one.
- **Read exit codes bare.**
- **A gate that did not run is not a pass.**
- **Open the artefact and ask what it shows.** A still, a contact sheet or a frame you did not look at is not evidence. Describe what you saw in the commit body.
- **Measure; do not estimate.** Record numbers, not "pass".
- **A check over a hand-written list only verifies the list.** Pair it with a containment check against what is actually used (the icon map compiles against the real package; the template registry and the component files are checked in both directions).
- **A search used to prove absence must not encode an incidental convention**, and should be corroborated a second way.
- **Write the test for the journey, not only the defence.** The review-gate tests run `new → approve → edit → render` in sequence, the way a person uses it.
- **A rename that breaks a test means updating the assertion.** Never add production code whose only consumer is a matcher.
- **Never loosen a bar to pass it.** File it with the measurement.

---

## 8. THE LOOP

```
(1) Is there an approved item? Wave A, A1–A21, in §2 order. If all are done,
    STOP. Never start a deferred item (§4). Never fill in a `Your selection:` line.
(2) Read the item, then EVERY design section it points to, before writing code.
(3) If the guide and a design doc disagree, or a spec is impossible: STOP and
    file it in ongoing_general_errors.md with options. Minimal deviations that
    keep the intent go in the commit body AND §5.2.
(4) Build it. Only what the item says. Nothing from §5.5.
(5) Validate: the item's checks, then its FALSIFICATION (red, then green).
    A gate that cannot go red is not a gate.
(6) Open every artefact the item produces and describe what it shows.
(7) Run the full battery, bare. Update §1.3 with measured numbers.
    NOT RUN is a legal result; blank is not.
(8) One item = one Conventional Commit, WHY in the body, including the red and
    green runs. Add ONE line to ongoing_general_errors.md §3 in the same commit.
(9) git push origin main.
(10) Next item.
```

---

## 9. Definition of Done: Wave A

- [ ] A1–A21 each landed as one pushed commit, each with its falsification recorded.
- [ ] §1.3: every gate G1–G14 green, measured this session, read bare.
- [ ] `docs/evals/planner_<date>.md` and `docs/evals/e2e_<date>.md` committed, all bars met or filed.
- [ ] Performance budget on `emu_war` met or filed with per-stage timings.
- [ ] Issue 1 and Issue 2 have their evidence committed and are waiting on the user's selection.
- [ ] No placeholder template remains; the 16-template containment test is green.
- [ ] README has Setup, Usage and Credits.
- [ ] This guide rewritten to **Queue Complete** mode. **Then stop. The queue is empty; do not invent work.** The only legitimate triggers for new work are a user selection on an open issue or a deferred item, or a gate going red (investigate and **file** it).

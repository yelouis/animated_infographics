# Agent Execution Guide — Active Build: Wave A (Offline MVP, 22 items) — revised September 24, 2026

**You are an engineering agent with no memory of this project.** Nothing has been built yet. This repository contains a complete design (`docs/design_*.md`), four frozen fixture stories, and this guide. Your job is to **build and validate** the offline MVP, one item at a time, in the order of §2.

**What changed on September 24, 2026.** The user selected **Issue 1**: the narrator voice is chosen automatically. `af_heart` is used when a first-person (Reddit-style) story is told by a narrator who identifies as female; `am_michael` is used otherwise. That is specced as the new **A8** plus changes to A9. The user also selected **Issue 2 → Option A**: FLUX.2 [klein] 4B is the only image model, specced in A21. Because voice selection needs the LLM **before** narration, the LLM backend moved up to **A7** and every later item was renumbered. There is no earlier item numbering to reconcile, because nothing has been built.

At the user's request, the two short Reddit-style fixtures were also **replaced by two complete r/stories-style stories** (`story_recipe_box`, `story_room_12`, ~2.5–3 min each). The end-to-end performance budget is now measured on the longest of them (`design_testing_and_validation.md` §1, §5).

**What is approved:** Wave A, items **A1–A22** in §3. **What NOT to touch:** everything in §5 (delivered work, accepted equivalents, user decisions, invariants, rejected options). **What must not be started:** everything in §4 (deferred).

**Every number and literal string in this document and in the design docs is a decision, not a suggestion.** Implement as written; do not substitute your own values. If a value is genuinely impossible, keep the *intent*, deviate minimally, say so in the commit body, and add it to §5.2 (accepted equivalents). If the design itself cannot work, **STOP and file it in `docs/ongoing_general_errors.md` with options and a `Your selection: _____` line. Do not improvise, and never fill in a selection line yourself.**

**What the product is, in one paragraph.** A local-only CLI that turns a **text story** (narrated by local TTS in an automatically chosen voice) or an **audio narration** into a **1080×1920 animated explainer video**. It uses flat editorial vector scenes chosen from a library of 16 templates, in sync with the voice, with word-by-word karaoke captions, a persistent cast of vector avatars, locally generated illustrations of places and objects, and optional music and SFX. Every video **stops for human review** before the final render. The long-term goal is live mode (speak in real time and the visuals follow), so the renderer is clock-agnostic from day one.

---

## 0. Standing constraints (apply to every item)

1. **The battery is the regression bar.** After every item, run `scripts/battery.sh` (full, not `--fast`, once G11 exists) and record the numbers in §1.3. **Read every exit code bare.** `cmd | tail` reports `tail`'s exit status, always 0.
2. **Fully local at runtime.** No cloud API and no network except loopback, ever, at runtime (`design_system_architecture.md` §7). Setup may download.
3. **Python (Pydantic) is the source of truth for every contract.** JSON Schemas, TypeScript types, the template-registry JSON, the icon map and the country bboxes are **generated**. Never hand-edit `schema/`, `renderer/src/generated/` or `data/geo/country_bboxes.json`.
4. **Templates read time only through the clock** (`design_rendering.md` §3).
5. **The review gate is mandatory.** There is no auto-approve under any name (`design_system_architecture.md` §5).
6. **The planner never crashes the pipeline and never shows an ungrounded fact** (`design_planner.md`). **The voice stage never guesses a gender**: `af_heart` requires evidence (`design_planner.md` §10).
7. **One item = one Conventional Commit** (`.agents/skills/commit_message_guidelines/SKILL.md`), with the WHY in the body, including every falsification (the red run, then the green run). **Push after every item:** `git push origin main`. The remote is the private GitHub repo `yelouis/animated_infographics`.
8. **Record the resolution in the same commit:** one line in `ongoing_general_errors.md` §3 (Resolved index), any new gate numbers in §1.3 below, and, for A8/A9 and A21, collapse Issue 1 / Issue 2 in `ongoing_general_errors.md` §1 into their §3 lines when the *last* item delivering them lands (Issue 1 → with A9; Issue 2 → with A21).
9. **When this guide and a design doc disagree, stop and file it.** Do not pick one.
10. **Every stage writes `logs/<stage>.log`, whose last line is `llm_calls=<n> cache_hits=<m> elapsed_ms=<t>`.** Several validations below read these counters. The LLM call counter is incremented **at the backend's entry point**, before any cache lookup or early return. A counter placed beside the work only counts some of the paths.

---

## 1. Verified baseline (re-verified September 24, 2026, before any code)

### 1.1 Environment

| Fact | Value |
|---|---|
| Machine | Apple **M4 Max**, **64 GB** unified memory, macOS (Darwin 25.6.0) |
| Free disk | 118 GiB. Models need ≈ 35 GB (planner 19 GB, klein 4B, Whisper, Kokoro). |
| ffmpeg / ffprobe | **8.1** (Homebrew) |
| Node | **v26.5.0** (see `design_rendering.md` §1 for the Node 22 fallback rule) |
| System Python | 3.14.6. **Not used.** The project pins **3.12** through uv. |
| uv | present (`~/.local/bin/uv`) |
| Ollama | **0.33.0**. Installed: `glm4`, `gemma4:latest` (8B), `qwen2.5vl:7b`, `moondream`, `tinyllama`, **`gemma4:26b`** (digest `08ae7ec1744bd7f451c4a530afb39d2673ad9d07a8369b8a33a3613b41212a68`). |
| espeak-ng | **1.52.0** (Homebrew). |
| mflux | **0.20.0** (installed via uv tool). Remotion **4.0.528**. |
| macOS `say` | present (fixture generation) |
| gh | 2.98.0, logged in as `yelouis` |

### 1.2 Repository

Two commits' worth of design: `docs/`, `fixtures/scripts/*.txt` (**four** frozen stories; SHA-256 in `design_testing_and_validation.md` §1), `AGENTS.md`, `CLAUDE.md`, `README.md`, `.gitignore`, `.agents/skills/`. **No code, no gates.**

### 1.3 Gates

Each gate is created by the item named. **Replace "NOT BUILT" with the measured result in the commit that creates the gate, and keep this table current.** Definitions and falsifications: `design_testing_and_validation.md` §3.

| # | Gate | Result |
|---|---|---|
| G1 | `uv run ruff check .` | exit 0 (All checks passed) |
| G2 | `uv run ruff format --check .` | exit 0 (59 files already formatted) |
| G3 | `uv run mypy src` | exit 0 (Success: no issues found in 31 source files) |
| G4 | `uv run pytest -q -m "not slow"` | exit 0 (100 passed) |
| G5 | `npm --prefix renderer run typecheck` | exit 0 (0 errors) |
| G6 | `npm --prefix renderer run lint` | exit 0 (0 errors) |
| G7 | `npm --prefix renderer test` | exit 0 (1 passed) |
| G8 | `./scripts/check_schema_sync.sh` | exit 0 (11 files in sync) |
| G9 | `./scripts/check_renderer_purity.sh` | exit 0 (pure) |
| G10 | `./scripts/check_gallery.sh` | NOT BUILT (A17) |
| G11 | `uv run pytest -q -m slow` | exit 0 (11 passed) |
| G12 | `./scripts/e2e.sh` | NOT BUILT (A16; completed in A22) |
| G13 | `./scripts/check_offline.sh` | NOT BUILT (A22) |
| G14 | `uv run infographics doctor` | exit 0 (21 checks OK) |

⚠️ **A gate that could not run is recorded as NOT RUN with the reason, never left blank and never marked green.**

---

## 2. Execution order

| # | Item | Why this position |
|---|---|---|
| A1 | Bootstrap | Nothing can be verified without toolchains and a battery. |
| A2 | Setup script + `doctor` | Every later item needs models, voices, fonts and geodata on disk, and one command that says what is missing. |
| A3 | Fixtures | Every test from A6 on runs against them, including the four voice expectations. |
| A4 | Data contracts + schema sync | Both runtimes code against these types; changing them later is a cross-language refactor. |
| A5 | Job store, CLI, review gate | Locks the gate's invariants **before** anything can render. A gate retrofitted after a working render gets bypassed "temporarily". |
| A6 | Timing core (pure) | Beats, captions and frame math are the sync guarantee; pure functions, testable without models. |
| A7 | LLM backend | **Moved up September 24:** voice selection (A8) must call the LLM before any audio exists. |
| A8 | Narrator voice selection | Narration (A9) cannot start without a voice. |
| A9 | Narration (Kokoro) | The primary input path; produces the ground-truth timings A10 is measured against. |
| A10 | Transcription (Whisper) | The second input path, measured against A9's ground truth. |
| A11 | Renderer foundation + `kinetic_quote` | The spine: clock, Story, captions, audio, sync probe, overflow detection. `kinetic_quote` first because it is the planner's universal fallback. |
| A12 | Bible + geo | Segmentation, selection and props all need the cast and places; the narrator-avatar repair needs A8's `voice.json`. |
| A13 | Segmentation | Needs A6's rules and A12's context. |
| A14 | Storyboard + planner eval | Needs A4's props models, not the drawn templates. Unbuilt templates render as placeholders until A20. |
| A15 | Compile + preview | Closes the plan → review loop. |
| A16 | Final render + verification → **walking skeleton** | Proves text → MP4 end to end, sync verified in the encoded file, before the visual library grows. |
| A17 | Visual primitives + gallery gate | The shared parts and the gate that holds every template. |
| A18 | Templates: statement set (6) | |
| A19 | Templates: people set (5) | Needs A17's Avatar. |
| A20 | Templates: place & time set (4) + delete placeholder | Needs A17's MapView; the last template removes the placeholder. |
| A21 | Illustrations (FLUX.2 klein 4B) | Needs A20's `location`/`set_piece` to show them. Last, because every template already has an icon fallback. |
| A22 | E2E, offline gate, performance budget, README | Proof over the whole system; closes the wave. |

---

## 3. The items

Each item has: **what it means for the user** · **Files** · **Interfaces** (where they matter) · **Build** steps · **Validate** (checks, then the falsification that proves the check can fail, then what to open and look at) · **Blast radius**. The design sections named in each item are part of its spec: read them before writing code.

### A1 — Bootstrap

**What this means for the user:** a repository another agent can build in and a battery that says whether it is healthy.

**Files:** `pyproject.toml` · `.python-version` · `uv.lock` · `src/animated_infographics/{__init__.py,config.py}` · `tests/test_import.py` · `tests/conftest.py` · `renderer/{package.json,package-lock.json,tsconfig.json,remotion.config.ts,eslint.config.mjs,vitest.config.ts}` · `renderer/src/{index.ts,Root.tsx,smoke.test.ts}` · `scripts/battery.sh`

**Build:**
1. The repo exists locally and on GitHub. **Do not rewrite history.**
2. `pyproject.toml`: src layout; distribution `animated-infographics`, package `animated_infographics`; `requires-python = ">=3.12,<3.13"`; `[project.scripts] infographics = "animated_infographics.cli:app"`. `.python-version` = `3.12`. Runtime deps now: `typer`, `pydantic>=2.8`, `httpx`, `numpy`, `soundfile`, `pysbd`, `pillow`, `rich`. Dev: `pytest`, `ruff`, `mypy`. ML deps arrive with the items that use them (A9 `kokoro>=0.9.4`; A10 `mlx-whisper`, `jiwer`).
3. Ruff: line-length 100; rules `E,F,I,B,UP`. Mypy: `disallow_untyped_defs = true` for `src/`; `ignore_missing_imports` only for `kokoro`, `mlx_whisper`, `pysbd`, `soundfile`, `misaki`. Pytest: register marker `slow`; `tests/conftest.py` marks every test under `tests/slow/` as `slow` automatically.
4. `config.py` starts as a module of `Final` constants; every constant named in a design doc is added here, under the same name, by the item that first needs it.
5. `renderer/` is created by hand, not with an interactive generator. Deps: `remotion`, `@remotion/cli`, `@remotion/bundler`, `@remotion/renderer`, `@remotion/fonts`, `@remotion/layout-utils`, **all pinned to one identical exact version**, plus `react`, `react-dom`, `typescript`, `tsx`, `vitest`, `eslint`, `@remotion/eslint-plugin`, `ajv`, `d3-geo`, `topojson-client`, `world-atlas@2`, `@phosphor-icons/react`, `json-schema-to-typescript`. `tsconfig`: `strict: true`. Scripts: `typecheck` = `tsc --noEmit`; `lint` = `eslint src scripts`; `test` = `vitest run` (**never** `--passWithNoTests`). `Root.tsx` registers a trivial 1-frame composition until A11.
6. `scripts/battery.sh` (bash, `set -u`, not `set -e`): a static table of G1–G14 → command → creating item. A gate is *built* when its artefact exists: its script file; `tests/slow/*.py` for G11; `src/animated_infographics/doctor.py` for G14; G1–G7 always after A1. Each built gate runs **bare**, with stdout/stderr redirected to `artifacts/battery/<gate>.log`; the exit code is read from `$?` immediately. The key number (e.g. `N passed`) is grepped from the log afterwards. The script prints `gate | exit | key number` and `NOT BUILT (A#)` rows, and exits 1 if any built gate failed. `--fast` skips G11–G13.

**Validate:** `uv sync` → 0; `npm --prefix renderer ci` → 0; `npx remotion versions` (in `renderer/`) → no mismatch; G1–G7 green; `scripts/battery.sh` → 0. **Falsify:** add an unused import → G1 red **and** `battery.sh` exits 1; revert → green. Delete `tests/test_import.py` temporarily → G4 exits non-zero (pytest exit 5, "no tests"), proving an empty suite is not a pass; restore.

**Blast radius:** §1.3 rows G1–G7.

---

### A2 — Setup script and `doctor`

**What this means for the user:** one command prepares a fresh Mac, and one command says exactly what is missing and how to fix it.

**Files:** `scripts/setup.sh` · `src/animated_infographics/doctor.py` · `renderer/scripts/gen-country-bboxes.ts` · `data/vendor/CHECKSUMS` · `data/geo/country_bboxes.json` · `renderer/public/fonts/*` (5 TTF + licences)

**Build:**
1. `scripts/setup.sh` (idempotent; the only place network is used):
   - `brew install espeak-ng` if absent · `uv sync` · `npm --prefix renderer ci`
   - `ollama pull gemma4:26b`
   - `uv tool install mflux` (record the version)
   - Pre-download: `mlx-community/whisper-large-v3-turbo`; Kokoro-82M **and the two voices `af_heart` and `am_michael`** (instantiate `KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")` and load each voice once); the FLUX.2 klein **4B** weights, by running one tiny generation (e.g. 256×256, 1 step) and deleting its output. **Verify from mflux's download path that the 4B, not the 9B, was fetched.**
   - `npx remotion browser ensure` in `renderer/`
   - Fonts (`design_visual_direction.md` §3): `Poppins-Bold.ttf`, `Poppins-ExtraBold.ttf` + `OFL.txt` from the `google/fonts` repository (`ofl/poppins/`); `Inter-Medium.ttf`, `Inter-SemiBold.ttf`, `Inter-Bold.ttf` + licence from the official `rsms/inter` release archive (`extras/ttf/`) → `renderer/public/fonts/` (**committed**).
   - GeoNames `cities15000.zip` (unzipped to `cities15000.txt`) and `countryInfo.txt` → `data/vendor/` (**gitignored**), verified against `data/vendor/CHECKSUMS` (**committed**; written on the first download in this item, verified on every later run).
2. `renderer/scripts/gen-country-bboxes.ts`: `world-atlas` `countries-50m.json` + `countryInfo.txt` (ISO-numeric → ISO3) → `data/geo/country_bboxes.json` = `{ISO3: [minLon, minLat, maxLon, maxLat]}` from `d3.geoBounds`, keys sorted, with the header `"$comment": "GENERATED … DO NOT EDIT"`. Features without an id are skipped and listed on stdout. Committed.
3. `infographics doctor` (`doctor.py`): one line per check, `OK   <what>` or `MISSING <what> — run: <fix>`; exit **4** if any is missing. Checks:
   - Python 3.12; `ffmpeg`; `ffprobe`; `espeak-ng`
   - Ollama reachable at `127.0.0.1:11434`; the planner model (default `gemma4:26b`, overridable by `INFOGRAPHICS_PLANNER_MODEL`) present in `/api/tags`
   - `mflux-generate-flux2-klein` on PATH
   - In the HF cache (use `huggingface_hub.try_to_load_from_cache` or `scan_cache_dir`, never the network): the Whisper model, the Kokoro model, **`voices/af_heart.pt` and `voices/am_michael.pt`**, and the klein-4B weights (name the repo id mflux uses in a code comment)
   - `renderer/node_modules`; the Remotion headless browser (find where `ensure` installs it; name the path in a code comment)
   - the five font files; `data/vendor/*` against `CHECKSUMS`; `data/geo/country_bboxes.json`

**Validate:** `setup.sh` twice → both 0 (idempotent); `doctor` → 0. **Falsify:** `INFOGRAPHICS_PLANNER_MODEL=gemma4:not-a-model uv run infographics doctor` → exit 4 naming it. Temporarily rename `voices/am_michael.pt` in the cache (or point `HF_HOME` at an empty dir) → exit 4 naming the voice. Rename one font → exit 4 naming it. Restore everything → 0. Record in §1.1 the installed version of **every** tool and model: the Ollama model digest from `ollama show`, and the versions of mflux, Remotion, kokoro and mlx-whisper.

**Blast radius:** §1.1, §1.3 G14; `README.md` gains a Setup section.

---

### A3 — Fixtures

**What this means for the user:** every claim about quality, including "the right voice was chosen", is measured on the same inputs.

**Files:** `scripts/make_fixtures.sh` · `fixtures/audio/molasses_flood_say.m4a` · `fixtures/music/test_bed.wav` · `fixtures/sfx/{whoosh,pop,ding,hit,clap}_test.wav` · `fixtures/expected/{molasses_flood,emu_war,story_recipe_box,story_room_12}.json` · `fixtures/CHECKSUMS`

**Build:**
1. `scripts/make_fixtures.sh` per `design_testing_and_validation.md` §1. `say -v Samantha` (if absent from `say -v '?'`, use the first `en_US` voice and record which) on `molasses_flood.txt` → AIFF → ffmpeg AAC 128 kbps mono → `.m4a`. Music and SFX come from ffmpeg `lavfi` (`sine`, `anoisesrc=color=pink`) plus `afade`, at 48 kHz stereo s16, with the durations and frequencies in that table. The music peaks at −20 dBFS ± 1 dB (verify with `volumedetect`).
2. `fixtures/expected/<name>.json`, **exactly these keys**:

   ```json
   {"numbers": [1919, 15, 2300000, 25, 35, 21, 150],
    "cast_names": [], "narrator": false,
    "places": [{"name": "Boston", "country_iso3": "USA", "lat": 42.36, "lon": -71.06, "tol_deg": 0.1, "geo_source": "gazetteer"}],
    "voice": "am_michael", "voice_reason": "third_person",
    "evidence_contains": null, "narrator_facial_hair": null}
   ```

   Values per fixture are those in `design_testing_and_validation.md` §1 and the table in `design_planner.md` §10. Details:
   - `emu_war` has `places: [{"country_iso3": "AUS"}]` (name and coordinates not asserted).
   - `story_recipe_box` lists Duluth and Thunder Bay; `story_room_12` lists Amarillo.
   - Both story files have `narrator: true`.
   - `story_recipe_box` has `evidence_contains: "granddaughter"` and `narrator_facial_hair: "none"`.
   - A place entry asserts only the keys it contains.
3. `fixtures/CHECKSUMS`: SHA-256 of every fixture file (scripts, audio, music, sfx, expected).

**Validate:** the four scripts' SHA-256 values equal the frozen values in the testing doc. **If one does not, stop: a fixture was edited.** `shasum -a 256 -c fixtures/CHECKSUMS` → 0. ffprobe every generated file: durations as specified (±10 ms), sample rates as specified. **Falsify:** verify a copy with one changed byte → non-zero.

**Blast radius:** `fixtures/`, `scripts/make_fixtures.sh` only.

---

### A4 — Data contracts and schema sync

**What this means for the user:** the plan they review and the video that renders are guaranteed to describe the same thing.

**Files:** `src/animated_infographics/contracts/{models.py,templates.py,icons.py,export.py}` · `schema/*.schema.json` · `renderer/src/generated/{contracts.ts,templateRegistry.json,iconNames.json,iconMap.ts}` · `scripts/check_schema_sync.sh` · `tests/data/props_examples.json` · `tests/test_contracts.py`

**Build:**
1. `models.py`: every model in `design_data_contracts.md` §2–7 and §9, as frozen Pydantic v2 models with `extra="forbid"`. The **`VoiceDecision`** model (§9) enforces its invariants with a `model_validator`. Every top-level model has `schema_version: Literal[1]`.
2. `templates.py`: `TextSlot`, `SfxCue`, `TemplateSpec` and `REGISTRY: dict[str, TemplateSpec]` with **all 16** templates. Transcribe every props limit, slot row, SFX cue, `spread` and requirement from `design_templates.md` §2. `Scene.props` is a discriminated union keyed on `template`.
3. `icons.py`: the allow-list (`design_templates.md` §4; 120–200 names; must include the seven emotion glyphs of §2.11).
4. `export.py` (`uv run python -m animated_infographics.contracts.export [--out DIR]`): writes every generated file in `design_data_contracts.md` §1, with the DO-NOT-EDIT header, deterministically (sorted keys, stable ordering). `iconMap.ts` uses **explicit named imports** in whichever export form the installed `@phosphor-icons/react` provides. TS types come from `json-schema-to-typescript`, invoked by `export.py` through `npx`.
5. `scripts/check_schema_sync.sh`: export into a temp dir; `diff -r` against the committed files **and** `data/geo/country_bboxes.json` (regenerated by A2's script); exit 1 on any difference; **exit 1 if any compared file is missing or empty on either side.**

**Validate:** G8 green. Unit tests: an unknown key is rejected; `schema_version: 2` is rejected; each `VoiceDecision` invariant has one violating example rejected; one valid and one invalid props example per template load from `tests/data/props_examples.json` as expected. G5 compiles `iconMap.ts`. **Falsify (all three, red then green):** hand-edit one generated file → G8 exit 1; **empty** one generated file → G8 exit 1 (not a vacuous pass); misspell one icon in the allow-list and re-export → G5 red.

**Blast radius:** §1.3 G8.

---

### A5 — Job store, CLI and the review gate

**What this means for the user:** nothing ever renders without their approval of exactly the plan that renders.

**Files:** `src/animated_infographics/{jobs.py,cli.py,errors.py}` · `tests/test_jobs.py` · `tests/test_cli.py`

**Interfaces:**

```python
STAGES = ("ingest", "voice", "narrate", "transcribe", "bible", "segment",
          "storyboard", "assets", "compile", "preview")
# text path skips "transcribe"; audio path skips "voice" and "narrate"
class ValidationFailed(Exception): ...     # → exit 2
class GateRefused(Exception): ...          # → exit 3
class DependencyMissing(Exception): ...    # → exit 4
StageFn = Callable[["Job", "RunContext"], None]
class Job:
    @classmethod
    def create(cls, input_path: Path, jobs_dir: Path, now: datetime) -> "Job": ...
    @classmethod
    def open(cls, ref: str, jobs_dir: Path) -> "Job": ...
    def plan_sha256(self) -> str: ...
    def run(self, stages: Sequence[str], registry: Mapping[str, StageFn], ctx: RunContext) -> None: ...
    def invalidate_after(self, stage: str) -> None: ...
```

**Build:** everything in `design_system_architecture.md` §4–6: job ids, layout, `state.json`, the stage runner with `stage_input_sha256` skip logic and downstream invalidation, `plan_sha256`, every command, option and exit code, and the environment-variable table. The CLI maps the three exception types to exit codes 2/3/4 and anything else to 1 (with the traceback in `logs/<stage>.log`). Stages that do not exist yet raise `NotImplementedError("stage not implemented: <name>")` → exit 1. Option validation happens **before** a job directory is created: `--voice` with audio input or a voice outside `af_heart`/`am_michael` → exit 2.

**Validate:** tests drive the state machine with **fake stage functions** that write minimal valid files. There is a test for every refusal in architecture §5 (exit 3), for invalidation (re-running `segment` deletes `storyboard.json`, `timeline.json` and `preview/`), and for the two `--voice` rejections (exit 2, and no job directory created). At least one test is the **journey**: `new → approve → edit storyboard.json → render (3) → preview → approve → render (0)`, in sequence on one job, without rebuilding state between steps. **Falsify:** delete the `approval.plan_sha256 == plan_sha256(now)` comparison → the journey test fails at the post-edit render; restore.

**Blast radius:** none beyond these modules.

---

### A6 — Timing core

**What this means for the user:** visuals and the highlighted caption word land on the spoken word, and pacing stays watchable.

**Files:** `src/animated_infographics/timing/{frames.py,beats.py,captions.py,items.py,sfx.py}` · `tests/test_timing_*.py`

**Interfaces:**

```python
def ms_to_frame(ms: int) -> int
def scene_start_frames(beats: Sequence[Beat]) -> list[int]
def duration_frames(transcript: Transcript) -> int
def build_beats(transcript: Transcript, groups: Sequence[Sequence[int]]) -> list[Beat]
def paginate(transcript: Transcript) -> list[CaptionPage]         # ms; frames applied in compile
def item_frames(n: int, scene_frames: int, spread: float) -> list[int]
def count_frames(scene_frames: int) -> int
def schedule_sfx(cues: Sequence[SfxCue], available: Mapping[str, int], muted: set[str]) -> list[SfxEvent]
```

**Build:** exactly `design_audio_and_timing.md` §6–9 and `design_templates.md` §1 rule 5. No I/O, no models, no randomness.

**Validate:** every case for these modules in `design_testing_and_validation.md` §2, including the 500-stream property test (seeded) and `ms_to_frame(550) == 17`, `ms_to_frame(516) == 15`, and start frame **144** for a beat at 5,000 ms. **Falsify:** replace round-half-up with Python's `round` → the 550 case fails; set `LEAD_MS = 0` → the 144 case fails; set `CAPTION_MAX_WORDS = 4` → the paging case fails.

**Blast radius:** §1.3 G4 count.

---

### A7 — LLM backend

**What this means for the user:** planning runs locally, is deterministic on re-runs, and survives bad model output.

**Files:** `src/animated_infographics/planner/{__init__.py,llm.py}` · `tests/test_llm.py` · `tests/slow/test_llm_slow.py`

**Interfaces:**

```python
class LLMBackend(Protocol):
    calls: int          # incremented at entry, before cache lookup
    cache_hits: int
    def generate_json(self, *, stage: str, messages: list[dict], schema: dict, attempt: int) -> dict: ...
@dataclass
class Attempt: output: dict | None; errors: list[str]
def run_with_retries(backend: LLMBackend, *, stage: str, system: str, user: str, schema: dict,
                     validate: Callable[[dict], tuple[dict, list[str]]], max_attempts: int = 3
                     ) -> tuple[dict | None, list[Attempt]]
```

`validate` returns a possibly repaired output plus errors; empty errors means accept.

**Build:** `design_planner.md` §1 exactly: `OllamaBackend` with every setting in the table, the canonical-JSON cache key, `cache/llm/` relocatable by `INFOGRAPHICS_CACHE_DIR`, the retry transcript format, and `INFOGRAPHICS_PLANNER_MODEL`. Ollama down, or the model absent → `DependencyMissing` (exit 4). A JSON parse failure is a failed attempt, never an exception. `run_with_retries` returns `(None, attempts)` after the last failure, so callers own their fallback. Create `tests/slow/` here (this creates **G11**).

**Validate:** unit tests with `httpx.MockTransport`: the second attempt carries the previous output and the error lines; the seed is 7, 8, 9 across attempts; the cache key is identical for dicts with different key order; a cache hit still increments `calls` (entry-point counter) and `cache_hits`. Slow: **20/20** schema-conforming responses from `gemma4:26b` on a toy schema with an `enum` and a `maxLength`; the response carries no thinking content (`think: false` honoured); record the mean latency. **Falsify:** a non-existent model → exit 4 with its name; move the `calls += 1` below the cache check → the cache-hit counting test fails.

**Blast radius:** §1.3 G11.

---

### A8 — Narrator voice selection (NEW, Issue 1)

**What this means for the user:** a Reddit story told by a woman is read by a female voice. Everything else (history, men's stories, stories where the narrator's gender is never stated) is read by a male voice. The system never guesses a gender from stereotypes.

**Read first:** `design_planner.md` §10 (the rule, constants, lexicons, the `voice.json` shape, the fixture table) and `design_data_contracts.md` §9.

**Files:** `src/animated_infographics/planner/voice.py` · `src/animated_infographics/planner/prompts/voice.md` · `src/animated_infographics/stages/voice.py` (stage wrapper) · `tests/test_voice.py` · `tests/slow/test_voice_slow.py`

**Interfaces:**

```python
FIRST_PERSON_TOKENS: Final[frozenset[str]]
FEMALE_TOKENS: Final[frozenset[str]]
MALE_TOKENS: Final[frozenset[str]]
POSSESSIVES: Final[frozenset[str]] = frozenset({"my", "our", "your", "his", "her", "their", "its"})
NARRATOR_TAG_RE: Final[re.Pattern[str]]            # the pattern in design_planner.md §10 step 3, re.IGNORECASE

def strip_quoted(text: str) -> str                  # curly→straight quotes, then drop every "…" span
def first_person_rate(text: str) -> float           # on strip_quoted(text); round(…, 2)
def find_narrator_tag(text: str) -> tuple[Literal["female", "male"], str] | None
def self_identifying_token(evidence: str, gender: Literal["female", "male"]) -> str | None
def validate_gender_answer(text: str, answer: dict) -> tuple[dict, list[str]]
def decide_voice(perspective: str, gender: str) -> str
def select_voice(title: str | None, body: str, *, flag_voice: str | None,
                 backend: LLMBackend) -> VoiceDecision
```

**Build:**
1. Constants into `config.py`/`voice.py` **verbatim** from `design_planner.md` §10 (`VOICE_DEFAULT`, `VOICE_FEMALE_NARRATOR`, `INSTALLED_VOICES`, the token sets, `FIRST_PERSON_RATE_MIN = 2.0`).
2. `select_voice` runs the five steps of §10 **in order**, returning at the first step that decides:
   - (1) flag → `source="flag"`, `reason="flag"`, all analysis fields `None`, **no backend call**;
   - (2) `first_person_rate(title + "\n" + body) < 2.0` → `third_person`, `am_michael`, no backend call;
   - (3) `find_narrator_tag(title + "\n" + body)` on the **unstripped** text → `reason="tag"`, evidence = the matched text, no backend call;
   - (4) one `run_with_retries(stage="voice", …, validate=partial(validate_gender_answer, text))` → accepted `female`/`male` gives `reason="llm"`; `None` (all attempts failed) or `unknown` gives `narrator_gender="unknown"`, `reason="no_evidence"`;
   - (5) `voice = decide_voice(...)`.
3. `validate_gender_answer`: rule a (repair `unknown`+evidence → evidence `None`), rule b (verbatim span via `planner/grounding.py`'s `norm` + word-boundary substring; **if A14's `grounding.py` does not exist yet, create `norm()` and `is_verbatim_span()` there now**, exactly per `design_planner.md` §8, and A14 reuses them), rule c (`self_identifying_token` must return non-`None` for the claimed gender).
4. `self_identifying_token` implements rule c of `design_planner.md` §10 **exactly**:
   - split into clauses on `. ! ? ; :`; tokenise with `[A-Za-z0-9'\-éÉ]+`, **keeping case**;
   - scan for Form A openers (`I'm`, or `I` + `am|was|became`, or `I've` + `been`), then check the next 4 tokens as candidates;
   - scan for Form B anchors (`as`/`being`, any case), then check the next 4 tokens as candidates, each also requiring a `SUBJ` token within the 4 tokens after it;
   - a candidate must pass the four checks (lowercase as written; lexicon or hyphen-head; no possessive or `'s` before; no capitalised non-`SUBJ` token after);
   - return the first passing candidate, else `None`.

   Implement the four checks as four separately named helpers, so each falsification below removes exactly one.
5. `prompts/voice.md`: the substance listed in §10 step 4, with the full text given as `{text}` and the instruction to return JSON only. It includes two short in-prompt examples: one `female` with evidence copied exactly, and one `unknown` with `null`. **The examples must not use the fixtures' sentences**; that would teach to the test.
6. Stage wrapper `stages/voice.py`: reads `ingest.json` (title + paragraphs joined by `\n\n`), reads the `--voice` flag from the run context, writes `voice.json`, and writes `logs/voice.log` ending in the counters line (§0 rule 10). Register it in the stage registry for text inputs only.

**Validate:**
- **Unit** (fake backend; every case in `design_testing_and_validation.md` §2's `planner/voice.py` row). In particular:
  - the four fixtures' rates equal 5.45 (`story_recipe_box`) / 3.67 (`story_room_12`) / 0.00 / 0.00 (±0.01);
  - the tag cases; **all 23 evidence cases** in `design_planner.md` §10's table, each its own parametrised test id;
  - the 6-row `decide_voice` truth table;
  - `--voice am_michael` → `backend.calls == 0`;
  - a backend that fails three times → `unknown` / `no_evidence` / `am_michael` with no exception.
- **Slow** (real `gemma4:26b`, `--no-llm-cache`):
  - all four fixtures match `fixtures/expected/*.json` (`voice`, `voice_reason`, `evidence_contains`);
  - `molasses_flood` and `emu_war` have `calls == 0` for this stage;
  - the two inline snippets in the testing doc give `unknown`/`am_michael` and `male`/`am_michael`.
- **Falsify, each red then green:**
  - (a) remove the possessive check → `I'm her daughter` is accepted → red;
  - (a2) remove the lowercase check → `I am the Queen of this house` is accepted → red;
  - (a3) remove the name-after check → `I'm sister Maya's favourite` is accepted → red;
  - (a4) remove Form B's following-`I` requirement → `She treated me as a sister for years` is accepted → red;
  - (b) drop the first-person prefix group from `NARRATOR_TAG_RE` → `My sister (22F) said` is detected as a narrator tag → red;
  - (c) remove `strip_quoted` from `first_person_rate` → the "I only inside quotes" case becomes first person → red;
  - (d) call the backend before checking the flag → the zero-calls test → red.
- **Look:** paste the four fixtures' `voice.json` contents into the commit body.

**Blast radius:** `ongoing_general_errors.md` Issue 1 status gets "A8 delivered; A9 pending". Nothing else.

---

### A9 — Narration (Kokoro)

**What this means for the user:** a pasted story becomes a clean narration in the selected voice, with exact word timings.

**Files:** `src/animated_infographics/{ingest.py,audio/narrate.py,audio/loudness.py,stages/ingest.py,stages/narrate.py}` · `tests/slow/test_narrate_slow.py`

**Interfaces:**

```python
def ingest(input_path: Path, title_override: str | None) -> IngestRecord
def narrate(ingest: IngestRecord, voice: VoiceDecision, out_dir: Path) -> tuple[Transcript, NarrationOffsets]
def loudnorm_two_pass(src: Path, dst: Path, *, target_lufs: float, true_peak: float, lra: float,
                      sample_rate: int, channels: int) -> LoudnessReport
def measure_loudness(path: Path) -> LoudnessReport    # ffmpeg ebur128=peak=true
```

**Build:** `design_audio_and_timing.md` §1, §2, §5:
- One `KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M", device="cpu")` per job; one call per sentence with `voice=voice.voice`, `speed=1.0`.
- Concatenate `Result.audio` in order; insert the pause constants as zero samples; write `audio/narration_24k_raw.wav` (float32).
- Build words from `Result.tokens` with the four token→word rules. Build sentences and paragraphs (title = sentence 0, `is_title: true`).
- Two-pass `loudnorm` → `audio/narration.wav` (48 kHz mono s16).
- `narration.json.voice` = `voice.json.voice`. Add `kokoro>=0.9.4`. Wire `ingest` and `narrate`.

**Validate (slow, all four fixtures):**
- `transcript.json` satisfies every invariant in `design_data_contracts.md` §2.
- `narration.json` offsets are **exact**: segment samples plus inserted silence equal `narration_24k_raw.wav`'s length **to the sample**.
- `narration.wav` is 48 kHz mono s16 at −16 ± 0.5 LUFS integrated.
- `narration.json.voice == voice.json.voice`; `story_recipe_box` is `af_heart`, the other three `am_michael`.
- **The voice parameter really reaches Kokoro:** synthesise the first sentence of `molasses_flood` with each voice. The two raw arrays must not be equal. Record the median spectral centroid (numpy FFT over 2,048-sample frames whose RMS exceeds −40 dBFS) for each voice. **Expectation:** `af_heart`'s is higher. If it is not, investigate whether the voice argument is being ignored before accepting it, and record the finding.
- Record `narrate` wall time on `emu_war` (bar ≤ 60 s) and the narration duration.

**Falsify:** drop `PAUSE_BETWEEN_SENTENCES_MS` from the offset sum only → the exact-offset test fails; hard-code `voice="af_heart"` in `narrate` → the per-fixture voice assertion fails.

**Blast radius:** §1.3 G11 count. **Issue 1 collapses** into one §3 line (A8 + A9 together).

---

### A10 — Transcription (Whisper)

**What this means for the user:** their own recordings work, and we know how far ASR timing can be trusted, which live mode will depend on.

**Files:** `src/animated_infographics/{audio/transcribe.py,stages/transcribe.py}` · `tests/slow/test_transcribe_slow.py`

**Build:** `design_audio_and_timing.md` §3, §5. Add `mlx-whisper` and dev dep `jiwer`. Wire `transcribe` (audio path: `ingest` → `transcribe`; no `voice`, no `narrate`).

**Validate (slow):**
- WER ≤ **8%** on `molasses_flood_say.m4a` vs the source text (normalise: lowercase, strip punctuation).
- Whisper on **Kokoro's** `molasses_flood` narration vs Kokoro's own timestamps: word-start error median ≤ **80 ms**, p95 ≤ **250 ms**. Align words by `difflib.SequenceMatcher` over normalised tokens and compare matched pairs only; record the match rate.
- `transcribe` of the `emu_war` narration ≤ **45 s**.

**Record the measured values.** **Falsify:** compute WER against `story_room_12.txt` instead → the bar fails.

**Blast radius:** §1.3 G11 count.

---

### A11 — Renderer foundation (+ `kinetic_quote`)

**What this means for the user:** the look, the captions, the sound and the sync exist, before any intelligence is attached.

**Files:**
- `renderer/src/theme/{palette.ts,type.ts,motion.ts,layout.ts}`
- `renderer/src/clock/{types.ts,SceneClockContext.tsx,GlobalClockContext.tsx}`
- `renderer/src/clock/remotion/{RemotionSceneClock.tsx,RemotionGlobalClock.tsx}`
- `renderer/src/story/{Story.tsx,calculateMetadata.ts,Background.tsx,SceneLayer.tsx,Captions.tsx,AudioLayer.tsx,SyncProbe.tsx,entities.tsx}`
- `renderer/src/components/FitText.tsx`
- `renderer/src/templates/{index.ts,kinetic_quote.tsx,Placeholder.tsx}`
- `renderer/src/gallery/{Gallery.tsx,fixtures/kinetic_quote.ts}`
- `renderer/scripts/render.ts` · `renderer/test-data/timeline_smoke.json` · `scripts/check_renderer_purity.sh`

**Build:**
- Theme tokens from `design_visual_direction.md` §1–5 and §8 (the only place hex codes and sizes live).
- The clock per `design_rendering.md` §3: the Remotion adapter is the only code touching `useCurrentFrame`/`useVideoConfig`/`<Sequence>`.
- `Story` per `design_rendering.md` §1, §4, §5:
  - Ajv validation in `calculateMetadata`;
  - the background;
  - `SceneLayer` mounting each scene from `start_frame` for `min(end_frame + EXIT_FRAMES, duration_frames) − start_frame` frames, later scenes on top;
  - `Captions` on the global clock, respecting `hide_captions`;
  - `AudioLayer` for narration, music and SFX;
  - `SyncProbe` when `debug.sync_probe`;
  - `entities.tsx` exposing `useCast(id)`, `usePlace(id)`, `useSetPiece(id)` from the timeline dictionaries.
- `FitText` per §6, with fonts awaited through `delayRender`.
- `templates/index.ts` maps every one of the 16 registry names to a component: `kinetic_quote` real (`design_templates.md` §2.2), **the other 15 → `Placeholder`** (a `bgRaised` card with the template name and `NOT YET IMPLEMENTED`).
- `render.ts` with `stills` / `media` / `gallery` modes, public-dir assembly, one bundle + one browser per invocation, `onBrowserLog` capture, and the exit codes of `design_rendering.md` §2.
- `check_renderer_purity.sh` (**G9**) with `grep -rnF` over all `.ts`/`.tsx` under `renderer/src/` except `src/clock/remotion/`.
- `timeline_smoke.json`: 3 `kinetic_quote` scenes, 2 caption pages, `fixtures/music/test_bed.wav` standing in for narration, `debug.sync_probe: true`.

**Validate:**
- G9 green.
- Render the smoke timeline in `media` mode → ffprobe 1080×1920, 30/1, frame count = `duration_frames`; the sync probe flips at both scene boundaries (pixel (24, 24) at `start − 1` / `start + 1`; luma < 40 vs > 215).
- `gallery` for `kinetic_quote`: three stills, zero overflow on `max`.

**Falsify:** add `useCurrentFrame()` to `kinetic_quote` → G9 exit 1, revert → 0; shift `SceneLayer`'s mount by one frame → the sync-probe check fails. **Look:** open the three gallery stills and the middle frame of the smoke render, and describe them in the commit body.

**Blast radius:** §1.3 G9.

---

### A12 — Bible and geo resolution

**What this means for the user:** the same person looks the same all video long, places land on the map where they really are, and a female narrator's avatar matches her voice.

**Files:** `src/animated_infographics/planner/{bible.py,geo.py,prompts/bible.md}` · `src/animated_infographics/stages/bible.py` · `tests/test_geo.py` · `tests/test_bible.py` · `tests/slow/test_bible_slow.py`

**Interfaces:**

```python
class Gazetteer:
    @classmethod
    def load(cls, cities: Path, country_info: Path) -> "Gazetteer": ...  # index built once, pickled under the cache dir keyed by the files' SHA-256
    def resolve(self, name: str, country_iso3: str | None) -> tuple[float, float] | None: ...
def plan_bible(transcript: Transcript, voice: VoiceDecision | None, backend: LLMBackend,
               gazetteer: Gazetteer, bboxes: Mapping[str, tuple[float, float, float, float]]) -> Bible
def repair_bible(raw: Bible, voice: VoiceDecision | None, gazetteer: Gazetteer, bboxes: ...) -> Bible   # pure
```

**Build:** `design_planner.md` §2: the prompt (including the narrator's gender when `voice.json` knows it), the schema with enums, the five deterministic repairs (**repair 5 is new: female narrator → `facial_hair: "none"`**), gazetteer matching with `alternatenames`, the bbox check with a 0.5° margin, and the fallback bible. Wire the `bible` stage; for audio inputs `voice` is `None`.

**Validate:**
- **Unit:**
  - Boston resolves to USA by gazetteer; `Constantinople` resolves to Istanbul through `alternatenames`;
  - LLM coordinates outside the country bbox → `geo_source: "none"`;
  - duplicate colour slots repaired deterministically;
  - **repair 5:** a bible whose narrator has `facial_hair: "beard"` with `narrator_gender: "female"` comes out `"none"`; the same bible with `male`, `unknown` or `voice=None` is unchanged.
- **Slow:** the expectation checks for all four fixtures:
  - Boston by gazetteer;
  - Meredith + an `AUS` place;
  - `Rose`, `Danny`, `Walt` + narrator with `facial_hair: "none"` + Duluth (Minnesota, not Georgia) and Thunder Bay by gazetteer;
  - `Alvarez`, `Deb`, `Sofia` + narrator + Amarillo by gazetteer.

  A warm-cache re-run is byte-identical.

**Falsify:** remove the bbox check → the out-of-bbox unit test fails; remove repair 5 → its unit test fails.

**Blast radius:** none.

---

### A13 — Segmentation

**What this means for the user:** each scene carries one idea and stays on screen long enough to read.

**Files:** `src/animated_infographics/planner/{segment.py,prompts/segment.md}` · `src/animated_infographics/stages/segment.py` · `tests/test_segment.py` · `tests/slow/test_segment_slow.py`

**Build:** `design_planner.md` §3, then A6's `build_beats` on every result, including the fallback. Wire `segment`.

**Validate:** unit: the partition validator rejects a gap, a duplicate and an out-of-order index; the fallback gives one group per sentence. Slow: every fixture's `beats.json` tiles the narration; every beat k ≥ 1 is within [1,500, 8,000] ms (or logged "no valid split"); record beat counts and the duration histogram. **Falsify:** skip the merge pass → the bounds assertion fails on at least one fixture. If it does not, construct a synthetic transcript where it must, and say so.

**Blast radius:** none.

---

### A14 — Storyboard planning and the planner eval

**What this means for the user:** every beat gets a fitting visual, numbers on screen are exactly the numbers said, and nothing breaks when the model misbehaves.

**Files:** `src/animated_infographics/planner/{select.py,props.py,validate.py,grounding.py,prompts/select.md,prompts/props.md}` · `src/animated_infographics/textfit.py` · `src/animated_infographics/stages/storyboard.py` · `src/animated_infographics/evals/planner.py` · `tests/test_grounding.py` · `tests/test_validate.py` · `tests/test_select_rules.py` · `tests/test_textfit.py`

**Interfaces:**

```python
def norm(s: str) -> str
def numbers(s: str) -> list[float]
def is_verbatim_span(needle: str, haystack: str) -> bool
def digits_grounded(label: str, transcript_text: str) -> bool
def fits(text: str, slot: TextSlot) -> FitResult                        # Pillow, size_min, box_width × 0.95
def validate_scene(scene: Scene, ctx: PlanContext) -> list[str]         # shared by planner and `preview`
def validate_plan(bible: Bible, storyboard: Storyboard, ctx: PlanContext) -> list[str]
def allowed_templates(bible: Bible) -> list[str]
def apply_rules(choices: list[Choice], n_scenes: int) -> tuple[list[Choice], list[RuleRepair]]
def plan_storyboard(transcript, beats, bible, backend) -> tuple[Storyboard, PlanReport]
```

**Build:** `design_planner.md` §4–8:
- The allowed-template computation; 6-beat windows with 2 beats of context; rules R1–R5 (R3 after props).
- The per-scene fallback ladder; the deterministic `title_card` and `kinetic_quote`; `plan_report.json`.
- `norm`/`is_verbatim_span` already exist from A8. Extend `grounding.py`, don't duplicate.
- `evals/planner.py` per §9 on **all four** fixtures, including the voice-decision column. Wire the `storyboard` stage.

**Validate:** unit cases per the testing doc §2 (grounding, validators, rules, textfit). **Falsify:** stub `numbers()` to return every number × 10 → the `1500`-vs-`150` rejection test goes **red** (1500 now matches) and the correct-stat test goes **red** (it no longer matches); restore → green.

Run the planner eval → `docs/evals/planner_<date>.md` committed, **every bar in `design_planner.md` §9 met**, including voice 4/4. The independent re-validation of the final storyboards shows 0 violations. If a bar fails:
1. Iterate on prompts; every change re-runs the eval.
2. If it still fails, run the eval on `qwen3.6:35b` and **file the model choice as an issue**.
3. Never loosen a bar.

**Blast radius:** §1.3 G4/G11 counts.

---

### A15 — Compile and preview

**What this means for the user:** after `new`, they get a contact sheet and a readable storyboard, headed by the voice decision, so they can judge the whole video in a minute, plus a way to fix what they don't like.

**Files:** `src/animated_infographics/{compile.py,preview.py,audio/mix_prep.py}` · `src/animated_infographics/stages/{assets.py,compile.py,preview.py}` · `tests/test_compile.py` · `tests/test_preview.py`

**Build:**
- `compile.py`: `design_data_contracts.md` §7; `design_audio_and_timing.md` §6–9; `design_templates.md` §1 rule 5.
- `mix_prep.py`: music/SFX normalisation and role parsing; unknown roles are ignored with a warning naming the file.
- An interim `assets` stage (until A21) writing a manifest with every image `null`.
- `preview.py` per `design_rendering.md` §7, with the **voice line first** in `storyboard.md` (exact formats in `design_planner.md` §10; audio inputs print `Voice: (recorded audio)`).
- Wire `compile`, `preview`, `approve`'s overflow refusal, and `new` end-to-end to `awaiting_review`.

**Validate:**
- Every compiled timeline validates in Python **and** in the renderer (Ajv).
- Unit tests:
  - tiling;
  - hidden captions on the narrated title only;
  - the 24-frame SFX gap;
  - round-robin SFX files;
  - the four voice-line formats.
- `infographics new fixtures/scripts/molasses_flood.txt --music fixtures/music/test_bed.wav --sfx-dir fixtures/sfx` → exit 0, `awaiting_review`.
- **Open `contact_sheet.png` and `storyboard.md` and look at them.** Commit a copy of the contact sheet to `docs/evals/assets/<date>/a15_molasses_contact_sheet.png`.

**Falsify:** a `report.json` with non-empty `overflow` → `approve` exits 3; an edited storyboard with an ungrounded `stat_callout` → `preview` exits 2 and names the field.

**Blast radius:** none beyond the modules.

---

### A16 — Final render and output verification (walking skeleton)

**What this means for the user:** the first real MP4. Placeholders stand in for unbuilt templates, but timing, captions, sound, voice and the review gate are all proven.

**Files:** `src/animated_infographics/{render.py,stages/render.py}` · `src/animated_infographics/evals/e2e.py` · `scripts/e2e.sh`

**Build:** `render.py` per `design_rendering.md` §8 (settings, every `verify.json` check); `scripts/e2e.sh` steps 1–6 of `design_testing_and_validation.md` §4, **including step 1's voice assertions** (**G12**). The script asserts every exit code explicitly (`[ $? -eq 3 ] || fail "…"`), never through a pipe.

**Validate:** G12 green:
- exit codes exactly as specified at every step;
- `verify.json` all true for the text input and the audio input;
- the sync probe flips at every scene boundary (record the count);
- `molasses_flood`'s `voice.json` is `am_michael` / `third_person`.

**Falsify:** render a copy of the timeline with `duration_frames` altered → the frame-count check fails; remove the `approve` call from the script → step 2's expected-3 assertion catches it. **Look:** extract three frames of `final.mp4` (start, middle, end) with ffmpeg and describe them in the commit body.

**Blast radius:** §1.3 G12.

---

### A17 — Visual primitives and the gallery gate

**What this means for the user:** a consistent cast and a consistent look, held in place by a gate that catches visual regressions.

**Files:** `renderer/src/components/{Avatar.tsx,Icon.tsx,Chip.tsx,Panel.tsx,Bubble.tsx,MapView.tsx,mapFraming.ts}` · `renderer/src/components/*.test.ts` · `renderer/src/gallery/fixtures/avatar_sheet.ts` · `renderer/goldens/` · `scripts/check_gallery.sh` · `tests/test_contrast.py`

**Build:**
- `Avatar` per `design_visual_direction.md` §6: all parameters, all 8 expressions, `age` scaling, and the elder hair rule.
- `Icon` via the generated `iconMap.ts`.
- `Chip`, `Panel`, `Bubble`.
- `MapView` framing math as a pure `mapFraming.ts` (`design_templates.md` §2.15: min span, 25% padding, projection choice) with vitest tests.
- An `avatar_sheet` gallery entry: 8 expressions × 4 parameter combinations, including an `elder` with `crown` and a `child`.
- `scripts/check_gallery.sh` with overflow, golden diff and hold-motion checks, plus `--update`, per `design_testing_and_validation.md` §3.
- The contrast test per `design_visual_direction.md` §2.

**Validate:** G10 green over `kinetic_quote` and `avatar_sheet`. **Look at the avatar sheet**, including at 140 px: every expression must be recognisable. **Falsify:** change one palette colour → golden diff red; freeze `kinetic_quote`'s hold motion → motion check red; make `ink`-on-cast legal in a test copy of the palette → the forbidden-pair assertion red.

**Blast radius:** §1.3 G10.

---

### A18 — Templates: statement set

`title_card`, `stat_callout`, `icon_list`, `reveal`, `cause_effect`, `comparison` (`design_templates.md` §2.1, §2.3–2.7).

**What this means for the user:** numbers, lists, twists and cause-and-effect stop looking like placeholders.

**Files:** `renderer/src/templates/<name>.tsx` and `renderer/src/gallery/fixtures/<name>.ts` for each, plus goldens.

**Build:** each template exactly per its section: layout coordinates, slots from the registry, motion, and hold motion. Entrances use `timing.item_frames` and `timing.count_frames` from the timeline, never a local formula. Three fixtures each (`min`, `typical`, `max`).

**Validate:** G10 green with zero overflow on every `max` fixture. If `max` cannot fit, lower the limit in `design_templates.md` **and** the registry in the same commit; never go below `size_min`. **Open every golden** and state in the commit body that it matches its layout spec: positions, colours, and navy text on cast colours. Re-run `new` on `molasses_flood` and check that these six templates are no longer placeholders on the contact sheet.

---

### A19 — Templates: people set

`character_intro`, `dialogue`, `text_thread`, `emotion_beat`, `relationship_map` (§2.8–2.12).

**What this means for the user:** Reddit-style stories come alive: who said what, the text thread, the reaction, who is related to whom.

**Build/Validate:** as A18. Additionally:
- The `story_recipe_box` and `story_room_12` contact sheets both show `text_thread` or `dialogue` for their texted exchanges (Danny's photo text; the Deb exchange). If the planner chose neither, file it with the plan report rather than forcing it.
- The narrator avatar in `story_recipe_box` has no facial hair (repair 5, now visible).
- `story_recipe_box` shows a `map_focus` with a path from Duluth to Thunder Bay, or files why not.

---

### A20 — Templates: place & time set, and delete the placeholder

`location`, `set_piece`, `map_focus`, `timeline` (§2.13–2.16).

**What this means for the user:** history stories get their maps, timelines and places.

**Build/Validate:** as A18, with the icon fallback path (image `null`) as the `typical` fixture until A21. Then **delete `Placeholder.tsx`** and its mapping. Add a vitest **containment test in both directions**: every name in `templateRegistry.json` has a component file, and every component file in `src/templates/` (except `index.ts`) is in the registry. **Falsify:** remove one component → red. Check `grep -rnF "NOT YET IMPLEMENTED" renderer/src` → nothing, and corroborate that absence with the containment test's count (**16**).

---

### A21 — Illustrations (FLUX.2 klein 4B; Issue 2)

**What this means for the user:** places and key objects get real illustrations in one consistent style, and a failure never breaks a video.

**Files:** `src/animated_infographics/assets/illustrate.py` · `src/animated_infographics/stages/assets.py` (replaces the interim) · `tests/test_illustrate.py` · `tests/slow/test_illustrate_slow.py`

**Interfaces:**

```python
def image_prompt(kind: Literal["place", "set_piece"], visual_description: str) -> str
def image_seed(prompt: str) -> int
def cache_key(prompt: str, *, mflux_version: str) -> str
def generate(prompt: str, out: Path, *, timeout_s: int) -> ImageResult     # subprocess; never raises on tool failure
def run_assets(bible: Bible, job: Job) -> AssetManifest
```

**Build:** `design_visual_direction.md` §7 exactly:
- **4B only**: the prompts and the `STYLE` string verbatim, the seed formula, the cache key, 1024×1024, 4 steps, quantize 8.
- The per-image timeout (`INFOGRAPHICS_IMAGE_TIMEOUT_S`, default 180), the manifest, and the icon fallback.
- `generate` builds an argument list, **never a shell string**. It passes the model-selection flag the installed mflux needs for the 4B (verified with `--help` and recorded in a code comment).
- Output goes to a temp file, is validated with Pillow (opens, `verify()`, exactly 1024×1024), then renamed atomically into `cache/images/<key>.png` and copied into the job.
- Swap the `location`/`set_piece` `typical` gallery fixtures to a real generated image and update their goldens.
- **There is no Z-Image-Turbo code path, flag or benchmark** (Issue 2 → Option A).

**Validate:**
- Unit: `image_seed` is stable and in `[0, 2**31)`; `cache_key` changes when any keyed field changes; the prompt strings match the doc byte for byte.
- Slow: the second generation of the same prompt is a cache hit in < 1 s; with `INFOGRAPHICS_IMAGE_TIMEOUT_S=1` every image fails, the manifest says `failed`, `preview/report.json` lists them, and the preview still completes with icon fallbacks. **That timeout run is the falsification of the fallback path.**
- Record images per fixture and total `assets` wall time on `story_recipe_box` (the budget fixture).
- **Look:** open the `molasses_flood`, `emu_war` and `story_recipe_box` contact sheets. Images must be flat vector, text-free and on-palette. If they are not, file it with the images attached. Small wording fixes to `STYLE` are allowed if noted in the commit; changing the model is not.

**Blast radius:** **Issue 2 collapses** into one §3 line.

---

### A22 — E2E, offline gate, performance budget, README

**What this means for the user:** proof the whole thing works, locally, within their 10-minute tolerance, and instructions to use it.

**Files:** `scripts/e2e.sh` (completed) · `scripts/check_offline.sh` · `scripts/offline.sb` · `README.md` · `docs/evals/{e2e,planner}_<date>.md`

**Build:**
- `scripts/e2e.sh` steps 7, 7b and 8, plus the committed report (`design_testing_and_validation.md` §4). **Step 7 covers all three other fixtures through render with their voice assertions; step 7b checks the `--voice` override with zero voice-stage LLM calls.**
- `scripts/check_offline.sh` + `scripts/offline.sb` (§6).
- Re-run the planner eval with all 16 templates live.
- Measure the performance budget (§5).
- README Usage section: `new` → read the voice line and look at the contact sheet → edit → `preview` → `approve` → `render`. Explain automatic voice selection and `--voice af_heart|am_michael`, and the music/SFX role naming convention.
- README Credits: GeoNames CC BY 4.0, fonts OFL, Phosphor MIT, Natural Earth, Kokoro, FLUX.2 [klein] 4B, Gemma 4, and the Remotion licence note.

**Validate:**
- G12 and G13 green.
- G13's self-check falsified once: remove the `deny` line → the self-check must fail; restore.
- `docs/evals/e2e_<date>.md` and `docs/evals/planner_<date>.md` committed.
- Performance bars met **or filed with per-stage timings** (the `voice` stage included).
- **The full battery green**, every number recorded in §1.3.

**Close-out:**
1. Rewrite this guide's title and §2–§3 to **Queue Complete** mode.
2. Move Wave A to §5.1 with one line per item.
3. Update `ongoing_general_errors.md` §1.
4. **Stop. Do not invent work** (§9).

---

## 4. Deferred — do NOT start

Each needs the user's selection in `ongoing_general_errors.md` §4:
- **D1** video input + PiP
- **D2** 16:9 output
- **D3** multi-voice narration
- **D4** live mode
- **D5** Reddit URL fetch
- **D6** public-domain photo sourcing
- **D7** historical map borders
- **D8** web editor
- **D9** a cloud LLM backend

Honouring the constraints in `design_future_live_and_video.md` (F1–F6) is in scope now; building these features is not.

---

## 5. Do NOT change

### 5.1 Already delivered

Nothing yet. Items move here, one line each, as they land.

### 5.2 Accepted equivalents

None yet. When an implementation reaches a spec's intent by a different structure, record it here with the reason, so the next pass does not "fix" it back.

### 5.3 User decisions

**September 23, 2026 (design grilling):**
- Offline first; a template library (not generated code or generated video).
- First content: **history + Reddit-style stories**. MVP inputs: **text script + audio only**.
- Imagery: vector + local illustrations + open map data.
- **Python pipeline + TypeScript/Remotion renderer**, **fully local** (no paid or cloud APIs).
- **9:16 first**; **word-by-word karaoke captions**; **flat editorial vector** style; 1–3 min videos in ~10 min.
- **Scenes + persistent cast**; **single narrator** per video; **mandatory review gate**; **music + SFX from a user-supplied pack**.
- Live mode later, with the **webcam in a corner**.

**September 24, 2026 (selections):**
- **Issue 1 → A + B:** "If the story from reddit seems to be from a female's perspective then use af_heart, else use am_michael." Interpreted in `design_planner.md` §10.
- **Issue 2 → A:** FLUX.2 [klein] 4B.
- **Test stories must be complete stories** (r/stories-style, a full arc), not fragments.

### 5.4 Invariants and intentional design decisions

- **Voice rule asymmetry:** `af_heart` only with first person **and** checkable self-identification (a Reddit tag or a verbatim evidence span with a non-possessive gendered token); everything else is `am_michael`. Never infer gender from occupation, interests, emotions or a partner's gender. `I'm her daughter` → `am_michael` is an accepted false negative.
- **The voice is decided before narration and cannot change within a job**; a different voice means a new job with `--voice`.
- **`--voice` accepts only the installed `af_heart` and `am_michael`.**
- **LLM call counters are incremented at the backend's entry point.**
- **Cast members are vector avatars only**, never generated images. Illustrations are for places and set pieces only.
- **No auto-approve**, under any name. Tests use the real `approve`.
- **`approve` refuses while any text overflows.**
- **Scenes lead the voice by 200 ms; captions never lead.**
- **Scenes are placed at absolute frames. Never `TransitionSeries`**: it shortens the timeline and desyncs every later scene.
- **Item and count timings are computed once, in Python**, and shared by SFX and visuals.
- **Grounding is a hard gate**: numbers, dates and quotes on screen must come from the narration.
- **Place coordinates come from the gazetteer first**; LLM coordinates are accepted only inside the country bbox (+0.5°).
- **Text on cast colours and on `highlight` is navy `bg`**, never `ink` (1.52–3.21 : 1, measured).
- **Python is the contract source of truth**; generated files are never hand-edited.
- **`kinetic_quote` is the universal fallback** and always validates by construction.
- **Captions are hidden only during a `title_card` whose beat is the narrated title.**
- **FLUX.2 klein 9B is non-commercial: never use it.** Z-Image-Turbo is not used either (Issue 2).
- **Beat boundaries are not human-editable** in the MVP.
- **The `sandbox-exec` offline gate stays** even though the tool is deprecated. If it breaks, file it.
- **Fixtures are original texts.** Never commit a real Reddit or other third-party post as a fixture: it is the author's copyrighted work, and its facts are not ours to freeze. Users may of course *run* the tool on any story they have the right to use.

### 5.5 Assessed and rejected — do NOT re-propose

- Live-first, or parallel offline/live tracks.
- LLM-written code per scene (hybrid or pure); text-to-video or image-generated scenes.
- Video input or Reddit URL fetching in the MVP.
- Vector-only imagery; illustration-heavy scenes; generated portraits for cast.
- TypeScript-only or Python-only (Manim/MoviePy) stacks; Claude or any cloud API.
- Both aspects at once, or 16:9 first.
- Sentence subtitles, no captions, or a caption toggle.
- Paper-cutout, whiteboard or dark-cinematic styles; a persistent continuous stage or a pure slideshow.
- Multi-voice in the MVP; an optional review gate or a web editor; music-only or no audio bed.
- `TransitionSeries` for transitions; TypeScript as the schema source; trusting LLM coordinates without a check; re-transcribing TTS audio with Whisper for timings.
- **Voices `bm_george` and `af_bella`** (Issue 1 options C and D).
- **A four-voice listening bake-off** (dropped once the user selected).
- **Z-Image-Turbo, or any image-model bake-off** (Issue 2 option B).
- **Inferring narrator gender from context or stereotypes**, or using `af_heart` as the default.

---

## 6. Where the contracts live

| What | Where |
|---|---|
| Product, pipeline, repo/job layout, CLI, exit codes, env vars, review gate, local-only policy, pinned models | `design_system_architecture.md` |
| JSON file shapes (incl. `voice.json` §9), source of truth, generation, sync gate | `design_data_contracts.md` |
| Ingest, TTS, ASR, loudness, frame math, beats, captions paging, SFX scheduling | `design_audio_and_timing.md` |
| LLM backend, **narrator voice selection (§10)**, prompts, bible, segmentation, selection, props, validators, grounding, fallback, planner eval | `design_planner.md` |
| The 16 templates | `design_templates.md` |
| Palette (with measured contrast), type, layout zones, motion, background, avatars, captions style, illustration | `design_visual_direction.md` |
| Remotion project, clock, spans, overflow, render CLI, preview (voice line), final render, verification, sync probe | `design_rendering.md` |
| Fixtures (four scripts), unit/integration layers, the 14 gates and their falsifications, E2E, offline gate, budget, artefacts | `design_testing_and_validation.md` |
| Live mode, video input, 16:9: constraints now, sketches later | `design_future_live_and_video.md` |
| Phase overview | `master_implementation_plan.md` |
| Open issues, selections, deferred items, resolved index, decision log | `ongoing_general_errors.md` |

---

## 7. Validation standard

- **A gate must be able to fail.** Before trusting a gate, name the input that turns it red, run it, and record the red run next to the green one.
- **Read exit codes bare.**
- **A gate that did not run is not a pass.**
- **Open the artefact and ask what it shows.** A still, contact sheet, frame or `voice.json` you did not look at is not evidence. Describe what you saw in the commit body.
- **Measure; do not estimate.** Record numbers, not "pass".
- **A check over a hand-written list only verifies the list.** Pair it with a containment check against what is actually used (the icon map compiles against the real package; registry ↔ component files in both directions).
- **A search used to prove absence must not encode an incidental convention**, and should be corroborated a second way.
- **Instrumentation has control flow too.** Count at the entry point, or the counter measures a subset of paths.
- **Write the test for the journey, not only the defence.** The review-gate tests run `new → approve → edit → render` in sequence, as a person would.
- **A rename that breaks a test means updating the assertion.** Never add production code whose only consumer is a matcher.
- **Never loosen a bar to pass it.** File it with the measurement.

---

## 8. THE LOOP

```
(1) Is there an approved item? Wave A, A1–A22, in §2 order. If all are done,
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
    green runs. Add ONE line to ongoing_general_errors.md §3 in the same commit;
    collapse Issue 1 with A9 and Issue 2 with A21.
(9) git push origin main.
(10) Next item.
```

---

## 9. Definition of Done: Wave A

- [ ] A1–A22 each landed as one pushed commit, each with its falsifications recorded.
- [ ] §1.3: every gate G1–G14 green, measured this session, read bare.
- [ ] The voice stage matches all four fixture expectations in the slow suite, the planner eval and the E2E.
- [ ] `docs/evals/planner_<date>.md` and `docs/evals/e2e_<date>.md` committed, all bars met or filed.
- [ ] Performance budget on `story_recipe_box` (~3 min, the longest fixture) met or filed with per-stage timings.
- [ ] Issues 1 and 2 collapsed into §3 lines of `ongoing_general_errors.md`.
- [ ] No placeholder template remains; the 16-template containment test is green.
- [ ] README has Setup, Usage (including voice selection) and Credits.
- [ ] This guide rewritten to **Queue Complete** mode. **Then stop. The queue is empty; do not invent work.** The only legitimate triggers for new work are a user selection on an open issue or a deferred item, or a gate going red (investigate and **file** it).

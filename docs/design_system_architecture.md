# System Architecture

This document owns: **what the product is**, the pipeline and its stages, the repository and job-directory layouts, the CLI and its exit codes, the **mandatory review gate**, the local-only policy, the pinned model/tool list, and the **memory guard** (§11). Detailed behaviour of each stage lives in the other `design_*.md` files (see §10).

---

## 1. Product

`animated_infographics` turns **narration** into a **vertical (9:16) animated explainer video**: flat editorial vector scenes that visualise what is being said, in sync with the voice, with word-by-word karaoke captions, a persistent visual cast, optional music and sound effects.

**MVP inputs (decided September 23, 2026):**

| Input | Example | Path through the pipeline |
|---|---|---|
| **Text script** (`.txt`) | A history story, a Reddit-style story | The narrator voice is auto-selected (`af_heart` for a first-person story told by a self-identified woman, otherwise `am_michael`), then local TTS (Kokoro) generates the narration with exact word timings |
| **Audio file** (`.mp3` `.wav` `.m4a`) | A recorded narration or podcast segment | Local ASR (Whisper) produces the word timings |

**MVP output:** `jobs/<job_id>/out/final.mp4`: 1080×1920, 30 fps, H.264 + AAC.

**First content domains:** **history stories** and **Reddit-style personal stories**. Story content drives the template catalogue: characters, dialogue, text threads, places, maps, timelines, big numbers, twists (`design_templates.md`).

**Explicitly NOT in the MVP.** Each is a deferred item in `ongoing_general_errors.md` §4 with its trigger:
- Video input and the picture-in-picture corner of the original speaker.
- 16:9 output.
- Live mode (speak in real time; visuals generated behind you, webcam in a corner).
- Multi-voice narration, Reddit URL fetching, public-domain photo sourcing, historical map borders, a web editor, any cloud LLM.

The architecture must not *preclude* the deferred items. `design_future_live_and_video.md` lists the constraints that keep them open, and they are enforced now.

---

## 2. The pipeline

```
 input (.txt | audio)
   │
   ▼
 ingest ──► voice ──► narrate (text: Kokoro TTS) ──┐
        └─► transcribe (audio: Whisper) ───────────┴─► transcript.json
                                              │
                                              ▼
                                  bible  (LLM: cast, places, set pieces)
                                              │
                                              ▼
                                  segment (LLM + deterministic rules) ──► beats.json
                                              │
                                              ▼
                                  storyboard (LLM: template per beat + props,
                                              validators, retries, fallback)
                                              │
                                              ▼
                                  assets (local image generation, cached)
                                              │
                                              ▼
                                  compile (storyboard ► frame-exact timeline.json)
                                              │
                                              ▼
                                  preview (stills + contact sheet + storyboard.md)
                                              │
                            ═══════ MANDATORY REVIEW GATE ═══════
                              human inspects, optionally edits
                              bible.json / storyboard.json,
                              runs `preview` again, then `approve`
                                              │
                                              ▼
                                  render (Remotion ► out/final.mp4)
```

**Two runtimes, one contract.**
- **Python** (`src/animated_infographics/`, uv, Python **3.12**) owns everything up to and including `timeline.json`: ingest, audio, LLM planning, validation, asset generation, compilation, job state, CLI.
- **TypeScript** (`renderer/`, Remotion) owns drawing: it consumes `timeline.json` and produces stills and video. **The renderer never calls an LLM, never reads the bible or storyboard, and never computes a fact.** It draws resolved props.
- The boundary is **JSON files validated against generated JSON Schema**. Python (Pydantic) is the source of truth; TypeScript types are generated. See `design_data_contracts.md`.

---

## 3. Repository layout

```
animated_infographics/
  AGENTS.md  CLAUDE.md  README.md
  pyproject.toml  uv.lock  .python-version            # 3.12
  src/animated_infographics/
    cli.py                 # Typer app; entry point `infographics`
    config.py              # every constant named in the design docs, one place
    jobs.py                # job dir, state.json, stage runner, hashing
    doctor.py
    ingest.py
    audio/  narrate.py  transcribe.py  loudness.py  mix_prep.py
    timing/ beats.py  captions.py  frames.py
    planner/ llm.py  bible.py  segment.py  select.py  props.py
             validate.py  grounding.py  geo.py  prompts/*.md
    assets/  illustrate.py
    contracts/ models.py  templates.py  icons.py  export.py
    textfit.py             # Pillow text measurement (same TTF files as the renderer)
    compile.py
    preview.py             # stills via renderer + contact sheet via Pillow
    render.py              # invokes the renderer, verifies the output
    evals/   planner.py  e2e.py
  renderer/
    package.json  tsconfig.json  remotion.config.ts
    src/index.ts  src/Root.tsx
    src/clock/             # the ONLY place allowed to touch Remotion's frame APIs
    src/story/             # Story composition: background, scenes, captions, audio
    src/templates/         # one file per template (design_templates.md)
    src/components/        # Avatar, Icon, FitText, Chip, MapView, Bubble, ...
    src/gallery/           # Gallery composition + per-template fixtures
    src/generated/         # GENERATED — never hand-edit (contracts, registry, icons)
    scripts/render.ts      # CLI used by Python: stills | media
    scripts/gen-country-bboxes.ts
    public/fonts/*.ttf  public/fonts/OFL.txt
    goldens/               # committed golden stills for the gallery gate
  schema/                  # GENERATED JSON Schemas
  data/geo/country_bboxes.json          # GENERATED, committed
  data/vendor/             # downloaded by scripts/setup.sh; CHECKSUMS committed, payload gitignored
  fixtures/scripts/  fixtures/audio/  fixtures/music/  fixtures/sfx/
  scripts/                 # setup.sh, battery.sh and every check_*.sh gate
  tests/                   # pytest (unit: default; integration: -m slow)
  docs/                    # this document set; docs/evals/ holds committed eval reports
  jobs/  cache/  artifacts/                                   # gitignored
```

---

## 4. Job directory and state machine

A **job** is one input turned into one video. `job_id` = `<slug>-<YYYYMMDD-HHMMSS>` (local time). `slug` = the input file's stem, lowercased, every run of non-`[a-z0-9]` characters replaced by `-`, trimmed of `-`, truncated to 40 characters.

```
jobs/<job_id>/
  state.json
  input/                       # copies of the source, music file and sfx files
  ingest.json
  voice.json                   # text path only: narrator voice decision
  narration.json               # text path only: per-sentence audio offsets
  audio/narration.wav          # 48 kHz mono s16, loudness-normalised
  audio/music.wav              # optional
  audio/sfx/<role>_<n>.wav     # optional
  transcript.json
  bible.json                   # ← human-editable
  beats.json
  storyboard.json              # ← human-editable
  plan_report.json
  assets/images/<entity_id>.png   assets/manifest.json
  timeline.json
  preview/scene_<id>.png  preview/contact_sheet.png  preview/storyboard.md
  preview/report.json      preview/preview.mp4 (only with --preview-video)
  out/final.mp4  out/verify.json
  logs/<stage>.log
```

**Stages, in order:** `ingest` → (`voice` → `narrate`) *or* `transcribe` → `bible` → `segment` → **`director`** (creative style only, added October 5, 2026; recorded as skipped for `literal`, `design_styles.md` §3.3) → `storyboard` → `assets` → `compile` → `preview` → *(gate)* → `render`.

**Presentation jobs** (`state.json.kind == "presentation"`, added October 5, 2026) run `ingest` → `voice` → `deck` → `deck_bible` → `tree` → `assets` → `perform` → `speak` → `hear` → `follow` → `compose` → `preview` → *(gate)* → `render` → `score`. The stages are defined in `design_presentation_simulation.md`; the gate and job-local rules are unchanged.

**`state.json`:**

```json
{
  "schema_version": 1,
  "job_id": "molasses-flood-20260923-201500",
  "state": "awaiting_review",
  "completed_stages": ["ingest", "voice", "narrate", "bible", "segment", "storyboard", "assets", "compile", "preview"],
  "stage_input_sha256": {"bible": "…", "segment": "…"},
  "plan_sha256": "…",
  "preview_plan_sha256": "…",
  "timeline_plan_sha256": "…",
  "approval": null,
  "timings_ms": {"narrate": 14210, "bible": 20511},
  "failed_stage": null
}
```

`state` ∈ `planning` · `awaiting_review` · `approved` · `rendering` · `rendered` · `failed`.

**`plan_sha256`** = `sha256(bytes(bible.json) + b"\n" + bytes(storyboard.json))`. It is the identity of the human-reviewable plan.

**Job-local inputs are authoritative (added September 25, 2026).** `new` copies every input into `input/`: the story or audio file, the music file, and the SFX files (`input/sfx/`). `ingest.json` records them as job-relative paths (`design_audio_and_timing.md` §1). **Every stage derives music and SFX from those job-local copies, never from command-line options.** If `ingest.json` names a music file or SFX directory that is missing from the job, `compile` fails with `ValidationFailed` (exit 2) naming the path. It never silently renders without it, which was the original defect's shape (added September 26, 2026). Options exist only for the one invocation that received them, and `preview`, `rerun` and `render` receive none. The first implementation read music/SFX from the run context. Because `compile`'s outputs (`audio/music.wav`, `audio/sfx/`) are deleted by invalidation, **every edit → `preview` → `approve` → `render` journey silently rendered without music or SFX**, and no gate noticed.

**Invalidation rule.** Re-running any stage deletes the outputs of every later stage and removes them from `completed_stages`. A stage is never skipped because an output file *exists*. It is skipped only when its recorded `stage_input_sha256` matches the current inputs.

---

## 5. The mandatory review gate

**Decided September 23, 2026 (user):** every video stops for human review before the final render. **There is no `--auto-approve` flag, environment variable or config switch, and none may be added.** Tests exercise the gate through the real `approve` command.

| Command | Precondition | Effect |
|---|---|---|
| `infographics new <input> [opts]` | — | Runs `ingest` … `preview`. Ends in `awaiting_review` and prints the paths of `preview/contact_sheet.png`, `preview/storyboard.md`, `bible.json`, `storyboard.json`. |
| `infographics preview <job>` | state ∈ `awaiting_review`, `approved`, `rendered` | Re-validates the (possibly edited) `bible.json` + `storyboard.json` with the **same validators the planner uses**, regenerates only missing assets, recompiles and re-renders the preview. **Clears `approval`**, sets `preview_plan_sha256 = timeline_plan_sha256 = plan_sha256`, and sets state `awaiting_review`. |
| `infographics approve <job>` | state = `awaiting_review` **and** `preview_plan_sha256 == plan_sha256(now)` | Writes `approval = {"plan_sha256": …, "approved_at": ISO-8601}`, state `approved`. |
| `infographics render <job>` | state = `approved` **and** `approval.plan_sha256 == plan_sha256(now) == timeline_plan_sha256` | Renders `out/final.mp4`, verifies it (`design_rendering.md` §8), state `rendered`. |

A hand-edit after `approve` changes `plan_sha256`, so `render` refuses with exit code **3** and the message `plan changed since approval — run: infographics preview <job>`. The same refusal applies if `preview` was not re-run after an edit made before `approve`.

**Validation of human edits:** `preview` never calls the LLM. Invalid edits exit **2** and print one line per problem in the form `storyboard.json scenes[7].props.value: not grounded in beat text "…"`, and nothing downstream is touched.

---

## 6. CLI

Entry point: `infographics` (`[project.scripts] infographics = "animated_infographics.cli:app"`).

| Command | Options |
|---|---|
| `doctor` | — Checks every dependency in §8 and prints one `OK`/`MISSING` line each. |
| `new <input>` | `--style literal|creative` (default `literal`; recorded in `ingest.json`, `design_styles.md` §1) · `--title TEXT` · `--voice af_heart|am_michael` (text input only; overrides the automatic choice, `design_planner.md` §10) · `--music PATH` · `--sfx-dir PATH` · `--jobs-dir PATH` (default `./jobs`) · `--no-llm-cache` · `--preview-video` |
| `preview <job>` | `--preview-video` |
| `approve <job>` | — |
| `render <job>` | — |
| `status <job>` | — Prints state, completed stages, timings, fallback counts. |
| `rerun <job> --from <stage>` | `<stage>` ∈ `bible`, `segment`, `director`, `storyboard`, `assets`, `compile` (presentation jobs: `deck`, `tree`, `perform`, `follow`, `compose`). Runs from there through `preview`, then stops at the gate. `--style NAME` rewrites `ingest.json.style` first, and is only valid with `--from director` or earlier. |
| `present-sim <script>` (added October 5, 2026) | `--style literal|creative` · `--perturb mild|strong` · `--seed INT` (default 7) · `--tiebreak none|llm` (default `none`) · `--music PATH` · `--sfx-dir PATH` · `--jobs-dir PATH` · `--no-llm-cache`. Creates a presentation job and runs it to the gate (`design_presentation_simulation.md` §1) |
| `score <job>` | `--oracle`. Presentation jobs only; runs after `render` (§8 of the same document) |

`<job>` accepts a job id (resolved under `--jobs-dir`) or a path to a job directory.

**Exit codes. Tests assert on these, never on message text:**

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Unexpected error (traceback written to `logs/<stage>.log`) |
| 2 | Validation error: bad input file, bad option combination, invalid edited plan |
| 3 | Gate refusal: wrong state, or hash mismatch |
| 4 | Missing dependency (the same checks `doctor` runs) |
| 5 | **Not enough memory** (added October 10, 2026; §11): the memory guard waited its limit for a heavy step, or stopped a running one. The job is left resumable: `rerun --from <stage>` |

`--voice` with an audio input, or with any value outside `af_heart`/`am_michael`, exits **2**. `--music`/`--sfx-dir` paths that do not exist exit **2**.

**Environment variables** (the only ones; each exists for tests or gates, and none changes product behaviour silently):

| Variable | Default | Purpose |
|---|---|---|
| `INFOGRAPHICS_PLANNER_MODEL` | `gemma4:26b` | Planner model override (used by `doctor` falsification and the escalation eval) |
| `INFOGRAPHICS_CACHE_DIR` | `./cache` | Relocates the LLM and image caches (the offline gate uses a fresh one) |
| `INFOGRAPHICS_IMAGE_TIMEOUT_S` | `180` | Per-image generation timeout (the fallback test sets `1`) |
| `HF_HUB_OFFLINE` | set to `1` by the CLI at runtime | Blocks Hugging Face network access |
| `INFOGRAPHICS_LOCK_DIR` | `~/.cache/animated_infographics/locks` | Where the machine-wide heavy lock and gate lock live (§11). Tests point it at a temp dir. It is **never** inside `INFOGRAPHICS_CACHE_DIR`, which gates replace with fresh dirs |
| `INFOGRAPHICS_MEM_WAIT_S` | `1800` | The longest the memory guard waits to admit one heavy step before exit 5 (§11) |
| `INFOGRAPHICS_GATE_LOCK_HELD` | unset | Set by a gate script that holds the gate lock, so the gate scripts it calls do not try to take it again (§11) |

---

## 7. Local-only policy

**Decided September 23, 2026 (user): fully local.** No paid or cloud API is called at any point.
- **At setup** (`scripts/setup.sh`), network is allowed: installing packages, pulling model weights, downloading fonts and geodata. Every downloaded data file is pinned by SHA-256 in `data/vendor/CHECKSUMS`.
- **At runtime** (`new` · `preview` · `approve` · `render`), **no outbound network except loopback** (Ollama on `127.0.0.1:11434`, Remotion's local bundle server). This is enforced by `scripts/check_offline.sh` (`design_testing_and_validation.md` §3), not by convention.
- Hugging Face libraries run with `HF_HUB_OFFLINE=1` at runtime. Remotion's headless browser is installed at setup (`npx remotion browser ensure`), never on first render.

---

## 8. Pinned models and tools

The exact versions actually installed are recorded in the execution guide's §1 baseline by item A2. This table is the *choice*.

| Role | Choice | Licence | Notes |
|---|---|---|---|
| Planner LLM | **Ollama `gemma4:26b`** (MoE, 3.8 B active, 19 GB) | Apache-2.0 | Runs through Ollama structured outputs. Escalation candidate: `qwen3.6:35b` (see `design_planner.md` §2). **The same model** also runs the people-scene critic (`design_planner.md` §11) and the illustration text check (image input; `design_visual_direction.md` §7.1), so no extra model is pulled. |
| TTS | **Kokoro-82M** via `kokoro>=0.9.4`, voices **`af_heart`** and **`am_michael`** (auto-selected per story, Issue 1) | Apache-2.0 | Gives word timestamps. Needs `espeak-ng` (Homebrew). |
| ASR | **`mlx-whisper`**, model `mlx-community/whisper-large-v3-turbo` | MIT | `word_timestamps=True`. |
| Image generation | **mflux** 0.20.0 exposes klein through `mflux-generate-flux2 --model flux2-klein-4b` (`uv tool install mflux`), **FLUX.2 [klein] 4B** | Apache-2.0 (4B only; the 9B is non-commercial and must not be used) | Invoked as a subprocess. **Selected September 24, 2026 (Issue 2 → Option A).** |
| Renderer | **Remotion 4.x** (`remotion`, `@remotion/bundler`, `@remotion/renderer`, `@remotion/layout-utils`) | Remotion licence | Free for individuals and companies of ≤ 3 people; confirm at remotion.dev/license before commercial use. |
| Icons | `@phosphor-icons/react`, weight `fill` | MIT | Curated allow-list (`design_templates.md` §4). |
| Map geometry | `world-atlas@2` `countries-50m.json` | ISC / Natural Earth (public domain) | |
| Gazetteer | GeoNames `cities15000.zip` + `countryInfo.txt` | CC BY 4.0 | Attribution in README. |
| Fonts | Poppins (700, 800), Inter (500, 600, 700), static TTF | OFL-1.1 | The same files feed Pillow and Chrome. |
| Media tooling | ffmpeg / ffprobe (Homebrew; 8.1 at design time) | — | |

---

## 9. One renderer, two clocks

The renderer is written so that live mode can reuse every template unchanged. Templates are **pure functions of (props, scene clock)**. The scene clock supplies the time since the scene started. Offline, Remotion's frame counter drives it; live, it will be driven by `requestAnimationFrame`. The rule is enforced by `scripts/check_renderer_purity.sh`; the details are in `design_rendering.md` §3.

---

## 10. Where the contracts live

| What | Where |
|---|---|
| Every JSON file's schema, source-of-truth and sync rule | `design_data_contracts.md` |
| Ingest, TTS, ASR, loudness, frame math, beats, captions paging, audio mix | `design_audio_and_timing.md` |
| LLM backend, prompts, narrator voice selection, bible, segmentation, selection, props, validators, grounding, fallback | `design_planner.md` |
| The templates (16 shared, 2 creative-only, 1 presentation-only): props, limits, layout, motion, SFX cues, validators | `design_templates.md` |
| Styles: `literal`, `creative`, the director stage, the license, overlays | `design_styles.md` |
| Presentation simulation: deck, tree, perturbation, simulated live audio, matcher, scoring | `design_presentation_simulation.md` |
| Palette, typography, layout zones, motion tokens, avatars, illustration style | `design_visual_direction.md` |
| Remotion project, clock, compositions, preview, final render, output verification | `design_rendering.md` |
| Fixtures, gates, falsification, performance budget, evals | `design_testing_and_validation.md` |
| Constraints that keep live mode and video input possible | `design_future_live_and_video.md` |
| The memory guard: heavy steps, admission, the watchdog, the gate lock | this document, §11 |

---

## 11. Memory guard (added October 10, 2026)

**Why.** On October 9, 2026 the 64 GB machine ran out of memory. The macOS JetsamEvent reports at 19:50 and 19:52 show:
- **two image-generation processes at once,** at 26.6–27.2 GB each, about 27.4 GB lifetime peak (FLUX.2 klein 4B through `mflux`);
- **Ollama's `llama-server`** at 10.5 GB;
- **the user's own browser** at 5.6 GB.

Wired memory reached 16 GB, and macOS killed its own services for lack of compressor space.

**The cause:** the implementing agent ran a cold budget, the offline gate (fresh image cache), the E2E and a second budget **at the same time** (`artifacts/budget/20261009_194405`, `artifacts/offline/20261009_194518`, `artifacts/e2e/20261009_195347`, `artifacts/budget/20261009_195734`). Each generated FLUX images. Nothing in the pipeline knew about memory. Other programs (browsers, editors, other agents) also start and stop at will, so the memory free at the start of a run says little about the memory free ten minutes later.

**Principles:**
1. **Admission, not hope.** Before every heavy step, check the memory available *now*.
2. **One heavy step at a time on the machine,** across all pipelines, gates, tests and budgets.
3. **Other programs come and go.** Re-check before every heavy step, and keep watching during it.
4. **Free our own memory first.** Unload our own Ollama model before a non-LLM heavy step if that is what it takes. Never touch another program.
5. **Fail clean, never take the machine down.** A step that cannot get memory waits, then fails with exit 5 and leaves the job resumable. A step still running when memory turns critical is stopped by us, not by the kernel.

**Heavy steps and their declared peaks** (`src/animated_infographics/memguard.py`, `HEAVY_STEPS`):

| Step | Where it runs | How | Declared peak |
|---|---|---|---|
| `flux` | `assets`: illustrations, metaphor images, text-check regenerations | the `mflux-generate-flux2` subprocess | **32 GB.** Measured 27.54 GB (October 10, 2026), 0.5% off 27.4 GB evidence, × 1.15, rounded up |
| `whisper` | `transcribe`, `hear` | in-process `mlx-whisper` | **5 GB.** Measured 4.27 GB (October 10, 2026), × 1.15, rounded up |
| `kokoro` | `narrate`, `speak` | in-process | **3 GB.** Measured 2.42 GB (October 10, 2026), × 1.15, rounded up |
| `render` | `preview` stills, `render`, the oracle render, the gallery | Remotion (node + headless Chrome) subprocess, at the concurrency it actually uses | **6 GB.** Measured 5.16 GB (October 10, 2026), × 1.15, rounded up |
| `llm_load` | the first LLM call of a stage while `gemma4:26b` is not loaded | Ollama | **12 GB.** `llama-server` 10.5 GB resident, × 1.15 |

- **How a peak is measured:** run the step alone, as a subprocess, under `/usr/bin/time -l` on the longest fixture, and read "peak memory footprint". The declared peak is the measurement × 1.15, rounded up to a whole GB.
- **Recorded:** each constant carries its measurement date in a comment, and this table carries the numbers.

**Available memory:**
- **The figure:** `available = hw.memsize × kern.memorystatus_level / 100`. That is the kernel's own "free percentage", the one jetsam acts on and the one `memory_pressure` prints as "System-wide memory free percentage".
- **The pressure level:** `kern.memorystatus_vm_pressure_level`: 1 normal, 2 warning, 4 critical.
- **How it is read:** both through `sysctl -n`, with no new dependency. Reading it is one function, so tests can substitute a fake.

**The floor:** **`FLOOR = 8 GB`** must remain available after a step is admitted. It is the room for the OS, the compressor, and programs that start while the step runs.

**Admission:** `with guard("<step>"):` around every heavy step.
1. **Take the machine-wide heavy lock.** That is `fcntl.flock(LOCK_EX)` on `<INFOGRAPHICS_LOCK_DIR>/heavy.lock`.
   - Every heavy step of every process takes it, so two pipelines never run two heavy steps at once.
   - The OS releases a `flock` when its process dies, so there is never a stale lock.
   - Waiting for the lock counts toward the wait below.
2. **Admit** when `available − peak(step) ≥ FLOOR`.
3. **Unload our own model if that suffices.** If not admitted, and `gemma4:26b` is loaded (`GET /api/ps`), and the step is not `llm_load`:
   - unload it with `POST /api/generate {"model": "gemma4:26b", "keep_alive": 0}`;
   - wait up to 30 s for `/api/ps` to stop listing it;
   - log `memory guard: unloaded gemma4:26b to admit <step>`;
   - check again.
4. **Otherwise wait.** Check every 5 s, and log `memory guard: waiting for <step>: need <peak> GB + floor 8 GB, available <a> GB` at most every 30 s.
5. **Give up cleanly.** After `INFOGRAPHICS_MEM_WAIT_S` (1800 s) in total, raise `ResourceUnavailable`. The stage fails with **exit 5**, `state.json` records the failed stage, and `rerun --from <stage>` resumes.
6. **Record.** Every admitted step writes `memguard step=<s> waited_ms=<w> available_gb=<a> unloaded_llm=<true|false>` into its stage log.

**Watching a running step** (subprocess steps: `flux`, `render`):
- **Poll every 2 s.** If the pressure level reaches 4 (critical) or `available < FLOOR / 2`:
  - send SIGTERM to **our own child**, and SIGKILL after 10 s;
  - release the lock;
  - raise `ResourceUnavailable("memory guard: stopped <step> at <a> GB available")` (exit 5).
- **The watchdog never signals any process but the child it started.**
- **In-process steps** (`whisper`, `kokoro`) get admission only. When the stage ends, they release their model: drop the references, `gc.collect()`, and clear the MLX or MPS cache. The pipeline process must return to within 1 GB of its pre-stage footprint (measured in M1).

**LLM calls:**
- Before a stage's first LLM call, if `gemma4:26b` is not loaded, admit `llm_load`.
- The calls themselves are not locked; Ollama serialises them.
- **Avoid thrashing:** the guard unloads the model only when a step cannot otherwise be admitted.

**Gates never run concurrently.**
- **The gate lock.** Every gate script (`battery.sh`, `e2e.sh`, `creative_e2e.sh`, `presentation_sim.sh`, `check_offline.sh`, `check_gallery.sh`, `measure_budget.sh`) takes a **non-blocking** exclusive lock, `<INFOGRAPHICS_LOCK_DIR>/gate.lock`, at start.
- **If it is held,** the script exits **3** with `another gate is running: <script> pid <pid>`.
- **Nested gates.** A script that holds it sets `INFOGRAPHICS_GATE_LOCK_HELD=<pid>`. A script that sees that variable, with a live pid that is its own ancestor, skips taking the lock. That is how `battery.sh` runs the others in sequence.
- **Offline gate.** `check_offline.sh`'s sandbox profile (`scripts/offline.sb`) is `allow default` with network denied, so the lock dir and `sysctl` already work inside it. M2 verifies this; the profile is not widened.
- **Portability.** macOS ships no `flock(1)` command, so the gate scripts take the lock through a small Python wrapper (`python -m animated_infographics.gatelock <name> -- <command>`). It holds the `flock`, sets `INFOGRAPHICS_GATE_LOCK_HELD`, runs the script and returns its exit code.

**A memory stop is never an image fallback.** `generate_image` (`assets/illustrate.py`) never raises on a tool failure, and a failed image falls back to an icon. `ResourceUnavailable` is the one exception that must pass through it unchanged, and end the stage with exit 5. Otherwise the guard would hide memory failures as quality fallbacks (lesson 2.13).

**Budgets stay honest.** A budget run counts only if every heavy step logged `waited_ms=0`, and no step was stopped. Otherwise the report is headed `INVALID: memory guard waited <ms> ms` and the script exits 1: the conditions for a measurement were not met, just as with cache hits.

**`doctor`** adds:
- a check that fails (exit 4) if `hw.memsize` < the largest declared peak + `llm_load` + `FLOOR`;
- the current available memory and pressure level, and the heavy lock's holder pid if any;
- a warning, not a failure, if available memory is below `flux` + `FLOOR` right now.

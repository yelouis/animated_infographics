# System Architecture

This document owns: **what the product is**, the pipeline and its stages, the repository and job-directory layouts, the CLI and its exit codes, the **mandatory review gate**, the local-only policy, and the pinned model/tool list. Detailed behaviour of each stage lives in the other `design_*.md` files (see §10).

---

## 1. Product

`animated_infographics` turns **narration** into a **vertical (9:16) animated explainer video**: flat editorial vector scenes that visualise what is being said, in sync with the voice, with word-by-word karaoke captions, a persistent visual cast, optional music and sound effects.

**MVP inputs (decided September 23, 2026):**

| Input | Example | Path through the pipeline |
|---|---|---|
| **Text script** (`.txt`) | A history story, a Reddit-style story | Local TTS (Kokoro) generates the narration; TTS gives exact word timings |
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
 ingest ──► narrate (text: Kokoro TTS)  ──┐
        └─► transcribe (audio: Whisper) ──┴─► transcript.json
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

**Stages, in order:** `ingest` → `narrate` *or* `transcribe` → `bible` → `segment` → `storyboard` → `assets` → `compile` → `preview` → *(gate)* → `render`.

**`state.json`:**

```json
{
  "schema_version": 1,
  "job_id": "molasses-flood-20260923-201500",
  "state": "awaiting_review",
  "completed_stages": ["ingest", "narrate", "bible", "segment", "storyboard", "assets", "compile", "preview"],
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
| `new <input>` | `--title TEXT` · `--voice TEXT` (text input only; default `af_heart`) · `--music PATH` · `--sfx-dir PATH` · `--jobs-dir PATH` (default `./jobs`) · `--no-llm-cache` · `--preview-video` |
| `preview <job>` | `--preview-video` |
| `approve <job>` | — |
| `render <job>` | — |
| `status <job>` | — Prints state, completed stages, timings, fallback counts. |
| `rerun <job> --from <stage>` | `<stage>` ∈ `bible`, `segment`, `storyboard`, `assets`, `compile`. Runs from there through `preview`, then stops at the gate. |

`<job>` accepts a job id (resolved under `--jobs-dir`) or a path to a job directory.

**Exit codes. Tests assert on these, never on message text:**

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Unexpected error (traceback written to `logs/<stage>.log`) |
| 2 | Validation error: bad input file, bad option combination, invalid edited plan |
| 3 | Gate refusal: wrong state, or hash mismatch |
| 4 | Missing dependency (the same checks `doctor` runs) |

`--voice` with an audio input exits **2**. `--music`/`--sfx-dir` paths that do not exist exit **2**.

**Environment variables** (the only ones; each exists for tests or gates, and none changes product behaviour silently):

| Variable | Default | Purpose |
|---|---|---|
| `INFOGRAPHICS_PLANNER_MODEL` | `gemma4:26b` | Planner model override (used by `doctor` falsification and the escalation eval) |
| `INFOGRAPHICS_CACHE_DIR` | `./cache` | Relocates the LLM and image caches (the offline gate uses a fresh one) |
| `INFOGRAPHICS_IMAGE_TIMEOUT_S` | `180` | Per-image generation timeout (the fallback test sets `1`) |
| `HF_HUB_OFFLINE` | set to `1` by the CLI at runtime | Blocks Hugging Face network access |

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
| Planner LLM | **Ollama `gemma4:26b`** (MoE, 3.8 B active, 19 GB) | Apache-2.0 | Runs through Ollama structured outputs. Escalation candidate: `qwen3.6:35b` (see `design_planner.md` §2). |
| TTS | **Kokoro-82M** via `kokoro>=0.9.4`, voice `af_heart` | Apache-2.0 | Gives word timestamps. Needs `espeak-ng` (Homebrew). |
| ASR | **`mlx-whisper`**, model `mlx-community/whisper-large-v3-turbo` | MIT | `word_timestamps=True`. |
| Image generation | **mflux** (`uv tool install mflux`), **FLUX.2 [klein] 4B** | Apache-2.0 (4B only; the 9B is non-commercial and must not be used) | Invoked as a subprocess. Alternative under evaluation: Z-Image-Turbo (Issue 2). |
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
| LLM backend, prompts, bible, segmentation, selection, props, validators, grounding, fallback | `design_planner.md` |
| The 16 templates: props, limits, layout, motion, SFX cues, validators | `design_templates.md` |
| Palette, typography, layout zones, motion tokens, avatars, illustration style | `design_visual_direction.md` |
| Remotion project, clock, compositions, preview, final render, output verification | `design_rendering.md` |
| Fixtures, gates, falsification, performance budget, evals | `design_testing_and_validation.md` |
| Constraints that keep live mode and video input possible | `design_future_live_and_video.md` |

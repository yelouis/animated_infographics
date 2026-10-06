# animated_infographics

Turn narration into an **animated explainer video**: flat editorial vector scenes that visualise what is being said, in sync with the voice, with word-by-word karaoke captions. Paste a story (a history piece, a Reddit-style post) or drop in an audio file. You review a storyboard, then get a 1080×1920 MP4. Everything runs locally on an Apple Silicon Mac.

The long-term goal is **live**: speak in real time while the visuals build behind you, like live captioning but as infographics.

> **Status: Waves A–H delivered (Queue Complete).** All items implemented and verified across 16 battery gates (G1–G16).

## How it works

```
story.txt ─► local TTS ─┐
audio.m4a ─► local ASR ─┴─► word timings ─► local LLM plans scenes ─► contact sheet + storyboard.json
                                                                         │
                                                  you review / edit ─────┘
                                                         │ approve
                                                         ▼
                                            Remotion renders final.mp4
```

## Setup

Requires an Apple Silicon Mac with Homebrew, Node.js, and Ollama.

1. Prepare toolchains, models, voices, fonts, and vendor datasets idempotently:
   ```bash
   ./scripts/setup.sh
   ```

2. Verify all dependencies and local caches:
   ```bash
   uv run infographics doctor
   ```

3. Run the verification battery:
   ```bash
   ./scripts/battery.sh
   ```

## Usage

The pipeline enforces a mandatory review gate between automated planning and rendering.

### 1. Ingest and Plan (`new`)
Create a new job from a text story or audio file:
```bash
uv run infographics new path/to/story.txt --music path/to/bed.wav --sfx-dir path/to/sfx/
```

Options:
- `--style literal|creative`: Visual style. `literal` (default) provides strict byte-identical factual scene-by-scene representation. `creative` plans motifs, callbacks, visual metaphors, foreshadowing, and asides with strict license verification.
- `--voice af_heart|am_michael`: Override automatic narrator voice selection.
- `--music <path>`: Background music track (normalised to −16 LUFS, played at −18 dB / volume 0.126 with 1 s fade-in and 2 s fade-out).
- `--sfx-dir <dir>`: Directory containing SFX audio files.
- `--jobs-dir <dir>`: Destination directory for jobs (defaults to `./jobs`).

### 2. Review Storyboard and Contact Sheet
Inspect the planned voice and visuals:
1. Open the contact sheet: `jobs/<job_id>/preview/contact_sheet.png`.
2. Inspect the voice line at the top of `jobs/<job_id>/preview/storyboard.md` or in `jobs/<job_id>/voice.json`.
3. Check template assignments across all scenes.

### 3. Optional Editing and Preview (`preview`)
If you wish to adjust scenes, edit `jobs/<job_id>/storyboard.json` directly. Then regenerate the contact sheet:
```bash
uv run infographics preview <job_id>
```

### 4. Approve (`approve`)
Approve the job once you are satisfied with the plan. **Unapproved jobs cannot be rendered (exit code 3):**
```bash
uv run infographics approve <job_id>
```
*Note: Any edit made to `storyboard.json` after approval invalidates the approval token; you must re-preview and re-approve.*

### 5. Render (`render`)
Render the final 1080×1920 MP4 at 30 fps:
```bash
uv run infographics render <job_id>
```
Output video is saved to `jobs/<job_id>/out/final.mp4`. A verification summary with audio loudness, AV duration alignment, and frame checks is written to `jobs/<job_id>/out/verify.json`.

### 6. Presentation Simulation (`present-sim`)
Simulate real-time speech-driven presentation animations completely offline:
```bash
uv run infographics present-sim path/to/script.txt --style literal|creative --perturb mild|strong --seed 7
```

Options:
- `--style literal|creative`: Deck style.
- `--perturb mild|strong`: Perturbation level simulating live human delivery (paraphrasing, fillers, ad-lib tangents, back-references, point skipping).
- `--seed <int>`: Deterministic random seed.
- `--tiebreak none|llm`: Optional LLM tie-break when lexical matcher candidates are tied (defaults to `none` per §6.4).
- `--jobs-dir <dir>`: Destination directory for jobs.

**What the simulation is:**
- Plans an 8–10 slide deck with 2–4 talking points per slide and contiguous sentence coverage.
- Builds an offline navigation tree with section nodes (`section_title`), point nodes, transition edges (next/skip/back), and BM25 token indices.
- Applies realistic speech delivery variations, synthesizes narration via Kokoro, and transcribes via mlx-whisper.
- Simulates causal streaming matching at speech pauses and emits a live playback plan.
- Composes and renders the final presentation video following the mandatory review gate.

**What the simulation is NOT:**
- **No slide import**: Does not import existing PowerPoint (.pptx), PDF, or Google Slides files.
- **No real-time player**: Does not run a 60 fps browser client with requestAnimationFrame or Web Audio API.
- **No live input**: Does not stream live microphone audio or webcam video.

### 7. Presentation Scoring and Oracle Baseline (`score`)
Score tracking accuracy and render an oracle baseline:
```bash
uv run infographics score <job_id> [--oracle]
```

Evaluates 6 presentation metrics:
1. **Slide accuracy**: Fraction of speaking time spent on the correct slide.
2. **Point accuracy**: Fraction of speaking time spent on the correct talking point.
3. **Onset lag**: Median and P90 lag from speaker transitioning to node commitment on screen.
4. **False switches**: Number of spurious scene transitions per minute.
5. **Ad-lib stability**: Fraction of ad-lib and tangent speaking time where the display stays stable.
6. **Skip recovery**: Time taken to recover after the speaker skips a talking point.

Outputs:
- `jobs/<job_id>/presentation_score.json`: Recorded score report.
- `jobs/<job_id>/strip_chart.png`: Visual strip chart (Pillow) showing ground truth vs shown slide progression.
- `jobs/<job_id>/out/oracle.mp4` (with `--oracle`): Ground-truth baseline video achieving 100% accuracy and 0.0s lag, proving tree and template correctness.

---

## Automatic checks

Between automated planning and your review, three safety checks catch quality defects:
- **Illustrations**: Checked locally for stray lettering and regenerated with new seeds (up to 3 attempts), except when the description calls for writing (e.g., signs, documents, screens).
- **People scenes**: A second, blind reading evaluates dialogue and quote attributions; mismatches trigger a single prompt correction retry.
- **Timelines**: Date labels must use real dates grounded in the narration or exactly one of 17 approved relative time phrases, and must run forward in time.

The review gate flags issues on the contact sheet and storyboard table:
- `image failed`: An illustration failed after 3 attempts or text detection failed; the video still renders with a fallback placeholder.
- `critic changed`: The people-scene critic corrected an attribution or tone discrepancy.

---

## Narrator Voice Selection

When given a text input, the pipeline automatically chooses an installed narrator voice based on perspective:
- **`af_heart`**: Selected when the narrator explicitly self-identifies as female (e.g. `"As the only granddaughter..."`, `"I (28F)..."`).
- **`am_michael`**: Default voice for third-person narratives, neutral perspective, or when gender is unstated / ambiguous. The system deliberately rejects inference traps or stereotypical deductions.
- **Manual override**: Pass `--voice af_heart` or `--voice am_michael` to bypass the LLM voice classification stage entirely with zero LLM overhead.

---

## Music and Sound Effects Convention

- **Music**: Any standard audio format (`.wav`, `.mp3`, `.m4a`). The audio stage normalises and loops/trims the track to match speech duration, normalised to −16 LUFS and played at −18 dB (volume 0.126), 1 s fade-in, 2 s fade-out, no ducking.
- **SFX**: Sound effect files in `--sfx-dir` must begin with a recognised role prefix followed by an underscore:
  - `whoosh_*.wav`: Played at the starts of `title_card`, `comparison`, `location`, and `set_piece`.
  - `pop_*.wav`: Played on item entrances and the `character_intro` / `relationship_map` starts.
  - `ding_*.wav`: Played at a stat's count end (`stat_callout`).
  - `hit_*.wav`: Played at a `reveal`'s start.
  - Files with unrecognised roles (e.g., `clap_*.wav`) are logged with a warning and safely ignored.

---

## Documentation Map

| Doc | What it is |
|---|---|
| [`docs/agent_execution_guide.md`](docs/agent_execution_guide.md) | The item-by-item execution history and validation gates. |
| [`docs/master_implementation_plan.md`](docs/master_implementation_plan.md) | Phase overview and milestones. |
| [`docs/design_system_architecture.md`](docs/design_system_architecture.md) | Pipeline stages, job layout, CLI specification, review gate, and local-only policy. |
| [`docs/design_data_contracts.md`](docs/design_data_contracts.md) | Pydantic and TypeScript contract models; schema sync verification. |
| [`docs/design_audio_and_timing.md`](docs/design_audio_and_timing.md) | TTS synthesis, ASR transcription, loudness targets, beats, frame math, and captions paging. |
| [`docs/design_planner.md`](docs/design_planner.md) | Local LLM planning (Gemma 4 26B), structured outputs, validators, and voice selection rules. |
| [`docs/design_styles.md`](docs/design_styles.md) | Visual styles (`literal`, `creative`), motifs, callbacks, visual metaphors, asides, and license verification. |
| [`docs/design_templates.md`](docs/design_templates.md) | The 19 scene templates (Statement, People, Place & Time sets, Creative, and Presentation). |
| [`docs/design_presentation_simulation.md`](docs/design_presentation_simulation.md) | Offline presentation simulation, deck planning, tree navigation, live speech perturbation, BM25 matching, and scoring. |
| [`docs/design_visual_direction.md`](docs/design_visual_direction.md) | Color palette, typography, layout zones, avatars, kinetic motion, and illustration styles. |
| [`docs/design_rendering.md`](docs/design_rendering.md) | Remotion rendering engine, clock abstractions, sync probe, and media verification. |
| [`docs/design_testing_and_validation.md`](docs/design_testing_and_validation.md) | Fixtures, the 16 gates (G1–G16), E2E test specification, and offline sandbox. |
| [`docs/design_future_live_and_video.md`](docs/design_future_live_and_video.md) | Live mode, webcam PiP, and video input design constraints. |
| [`docs/ongoing_general_errors.md`](docs/ongoing_general_errors.md) | Working log, decision records, and resolved item index. |

---

## Credits & Acknowledgements

- **GeoNames** ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)): Gazetteer data for geographical place and coordinate resolution.
- **Natural Earth & world-atlas** (Public Domain): Vector map topojson and Natural Earth lakes vector datasets for country framing, borders, lakes, and world map rendering.
- **Phosphor Icons** ([MIT](https://github.com/phosphor-icons/core/blob/main/LICENSE)): Iconography for entities, themes, and UI elements.
- **Fonts**: [Poppins](https://fonts.google.com/specimen/Poppins) (Google Fonts, OFL) and [Inter](https://github.com/rsms/inter) (rsms/inter, OFL).
- **Kokoro-82M** ([Apache-2.0](https://huggingface.co/hexgrad/Kokoro-82M)): Local neural text-to-speech voice synthesis.
- **mlx-whisper** ([MIT](https://github.com/ml-explore/mlx-examples/blob/main/whisper/LICENSE) / OpenAI): Local Apple Silicon speech-to-text alignment and transcription.
- **FLUX.2 [klein] 4B** ([Apache-2.0](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B)) via [mflux](https://github.com/filipstrand/mflux): Local 4-step quantized editorial vector illustration generation.
- **Gemma 4 26B** ([Apache-2.0](https://ai.google.dev/gemma/terms)) via [Ollama](https://ollama.com): Local LLM planner for voice selection, bible entity extraction, beat segmentation, and template selection.
- **Remotion** ([Remotion Company License](https://remotion.dev/license)): Programmatic React video rendering. Free for individuals and companies of up to 3 people; review terms prior to commercial use.

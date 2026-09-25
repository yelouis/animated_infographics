# animated_infographics

Turn narration into an **animated explainer video**: flat editorial vector scenes that visualise what is being said, in sync with the voice, with word-by-word karaoke captions. Paste a story (a history piece, a Reddit-style post) or drop in an audio file. You review a storyboard, then get a 1080×1920 MP4. Everything runs locally on an Apple Silicon Mac.

The long-term goal is **live**: speak in real time while the visuals build behind you, like live captioning but as infographics.

> **Status: designed, not yet built.** Wave A (the offline MVP) is specified and approved. Implementation is done by an engineering agent following [`docs/agent_execution_guide.md`](docs/agent_execution_guide.md).

## How it will work

```
story.txt ─► local TTS ─┐
audio.m4a ─► local ASR ─┴─► word timings ─► local LLM plans scenes ─► contact sheet + storyboard.json
                                                                         │
                                                  you review / edit ─────┘
                                                         │ approve
                                                         ▼
                                            Remotion renders final.mp4
```

```bash
infographics new story.txt --music bed.mp3 --sfx-dir sfx/   # stops at review
open jobs/<job>/preview/contact_sheet.png                  # look; edit storyboard.json if needed
infographics preview <job>                                  # after edits
infographics approve <job>
infographics render <job>                                   # → jobs/<job>/out/final.mp4
```

## Documentation map

| Doc | What it is |
|---|---|
| [`docs/agent_execution_guide.md`](docs/agent_execution_guide.md) | **Start here if you are building.** The approved queue, item by item, with validation. |
| [`docs/master_implementation_plan.md`](docs/master_implementation_plan.md) | Phase overview |
| [`docs/design_system_architecture.md`](docs/design_system_architecture.md) | Product scope, pipeline, repo and job layout, CLI, review gate, local-only policy, pinned models |
| [`docs/design_data_contracts.md`](docs/design_data_contracts.md) | Every JSON file's shape; Python as source of truth; the sync gate |
| [`docs/design_audio_and_timing.md`](docs/design_audio_and_timing.md) | TTS, ASR, loudness, frame math, beats, captions, SFX scheduling |
| [`docs/design_planner.md`](docs/design_planner.md) | Local LLM planning, validators, grounding, fallback, planner eval |
| [`docs/design_templates.md`](docs/design_templates.md) | The 16 scene templates |
| [`docs/design_visual_direction.md`](docs/design_visual_direction.md) | Palette, type, layout, motion, avatars, captions, illustration |
| [`docs/design_rendering.md`](docs/design_rendering.md) | Remotion, the clock abstraction, preview, render, verification |
| [`docs/design_testing_and_validation.md`](docs/design_testing_and_validation.md) | Fixtures, the 14 gates, E2E, offline gate, performance budget |
| [`docs/design_future_live_and_video.md`](docs/design_future_live_and_video.md) | Live mode and video input: constraints now, sketches later |
| [`docs/ongoing_general_errors.md`](docs/ongoing_general_errors.md) | Open issues and decisions awaiting you (`Your selection: _____`), deferred features, resolved index |

## Setup

Requires an Apple Silicon Mac with Homebrew, Node.js, and Ollama.

1. Prepare toolchains, models, fonts, and vendor datasets idempotently:
   ```bash
   ./scripts/setup.sh
   ```

2. Verify all dependencies and local caches:
   ```bash
   uv run infographics doctor
   ```

## Usage and credits

Usage instructions arrive in A22. Planned credits: GeoNames (CC BY 4.0), Natural Earth via `world-atlas`, Phosphor Icons (MIT), Poppins and Inter (OFL), Kokoro-82M, Whisper, FLUX.2 [klein] 4B, Gemma 4 (Apache-2.0). Remotion is free for individuals and companies of up to 3 people; check remotion.dev/license before commercial use.


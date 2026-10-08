# animated_infographics: Master Implementation Plan

**Objective:** turn narration into an animated explainer video that visually represents what is being said. Long term, do it **live** while someone speaks. This plan covers the **offline MVP (Wave A)** and names the waves after it. The build spec, item by item, is `agent_execution_guide.md`; system behaviour is in the `design_*.md` contracts.

## Core configuration (MVP)

- **Inputs:** a text script (narrated by local TTS) or an audio file.
- **Output:** 1080×1920 (9:16), 30 fps, H.264/AAC, with word-by-word karaoke captions.
- **Style:** flat editorial vector; a persistent cast of vector avatars; local illustrations for places and set pieces; modern maps from open data.
- **Stack:** Python 3.12 pipeline (uv) + TypeScript/Remotion renderer, joined by a generated JSON contract.
- **Everything local:** Ollama `gemma4:26b` (planning), Kokoro-82M (TTS; `af_heart` for a first-person story told by a self-identified woman, otherwise `am_michael`), mlx-whisper large-v3-turbo (ASR), FLUX.2 klein 4B via mflux (images).
- **Human in the loop:** every video stops at a review gate (contact sheet + editable storyboard) before the final render.
- **Budget:** a ~3-minute story (the longest fixture) reaches review in ≤ 6.5 min and renders in ≤ 3.5 min on an M4 Max: ≤ 10 min total.

## Phase 0: Foundation (A1–A5)
**Goal:** a repository in which correctness can be measured.
- Toolchains, battery, setup script, `doctor`.
- Frozen fixtures (two history stories; two complete, original r/stories-style personal stories of ~3 min; a `say`-voiced audio file; synthetic music and SFX).
- Pydantic contracts with generated JSON Schema / TypeScript and a sync gate.
- Job directory, CLI and the review-gate state machine, locked before anything can render.

## Phase 1: Audio & timing (A6–A10)
**Goal:** the right voice, exact word timings from either input, and the rules that turn them into scenes and captions.
- Frame math, beat constraints and caption paging as pure, tested functions.
- The local LLM backend (needed first by voice selection).
- Narrator voice selection before TTS: deterministic perspective and Reddit-tag checks, then an evidence-checked LLM call.
- Kokoro narration with ground-truth word timestamps; Whisper transcription measured against that ground truth.

## Phase 2: Renderer spine (A11)
**Goal:** the look, captions, sound and sync, with no intelligence attached yet.
- A clock-agnostic template contract (the live-mode enabler), the Story composition, overflow detection, the sync probe, and `kinetic_quote`.

## Phase 3: Planner (A12–A14)
**Goal:** a local LLM that chooses good visuals and cannot put a false fact on screen.
- The story bible with gazetteer geo; segmentation; template selection and props with validators, grounding and a never-failing fallback ladder; a committed planner eval.

## Phase 4: Review gate & render, the walking skeleton (A15–A16)
**Goal:** text → reviewed plan → verified MP4, end to end.
- Compilation to a frame-exact timeline; contact sheet and storyboard preview; final render; output verification (format, loudness, A/V duration, sync probe in the encoded file).

## Phase 5: Visual library (A17–A20)
**Goal:** all 16 templates, held by a gallery gate.
- Avatars, icons and map primitives; statement, people, and place-and-time template sets; golden stills; the placeholder removed.

## Phase 6: Illustration (A21)
**Goal:** places and key objects illustrated locally in one style, with a failure-proof fallback.

## Phase 7: Proof (A22)
**Goal:** the full battery green, the offline guarantee enforced, the performance budget measured, the README complete.

## Wave B: verification fixes (approved September 25, 2026)
Wave A was delivered and independently verified: all gates green, but with defects the gates could not see. Among them: music/SFX dropped after a review edit, text truncated by constrained decoding, two planner crash paths, and an illegible map and image captions. Wave B (B1–B17) fixes them, adds the three user-selected quality checks, and measures the performance budget cold. The checks are:
- a local check for stray lettering in illustrations, with automatic regeneration, skipped when the description calls for writing;
- timeline labels that are real dates or fixed relative-time phrases;
- two meaning rules plus a blind critic for people scenes.

The item-by-item spec is `agent_execution_guide.md`.

## Wave C: verification fixes (approved September 26, 2026)
Wave B was delivered and independently verified: all gates green, all 17 items true to spec. Reviewing real output then found four problems the specs had missed:
- the critic missing a real misattribution, because beat splitting separated a quote from its speaker;
- a fifth of critic retries keeping the wrong scene;
- internal ids on screen;
- caption words colliding.

A fifth problem was added on September 27, 2026: a text thread credited to the wrong contact.

Wave C (C1–C8) fixes them and re-measures. Issue 6 was decided on September 27, 2026: paraphrased dialogue is fine.

## Wave D: picture-first stories (Issue 7 → Option A, selected September 27, 2026)
The story videos put ≈ 4.5 words/s on screen against 2.6 words/s of narration. The user's reference, Casually Explained, leaves half its frames wordless. Wave D (D1–D5) does four things, and keeps karaoke captions:
- removes the text fields that restated the narration;
- caps every remaining field in words;
- limits each video to one timeline and one comparison;
- inserts deterministic reaction shots and pictures after runs of wordy scenes.

Measured before specifying: graphic words fall from 1.1–1.9 per second to 0.5–0.9, and 39–56% of scenes become nearly wordless. Contract: `design_templates.md` §5.

## Waves E and F: verification fixes (delivered, October 4, 2026)
- Critic findings enforced on the final scene.
- Quoted speech never replaced.
- Dates are never stats.
- The icon list is shown to the model.
- No junk text on screen.
- Era stamps are narration years only.

## Wave G: style library (specced October 5, 2026)
The user asked for a style that "adds something to the story", keeping today's output as one style. Wave G does five things:
- adds `--style literal|creative`;
- adds a story-level **director** that plans motifs and callbacks, visual metaphors, foreshadowing plants and payoffs, and small asides, under the user's "small embellishments" license, checked by a blind license pass;
- adds two picture templates (`metaphor`, `callback`) and an overlay layer;
- adds two new ~5-minute fixture stories (measured 5.1 and 5.5 min);
- restates the time budget per narration minute.

Contract: `design_styles.md`.

## Wave H: presentation simulation (specced October 5, 2026)
The first step toward live presentations, in prepared mode. The pipeline runs in this order:
- a deck of key moments is derived from a script;
- an animation tree is built from the deck alone;
- the script is perturbed into a "performed" talk, which is narrated and re-transcribed as simulated live ASR;
- a causal matcher follows the talk through the tree;
- the result is rendered and scored against ground truth (slide and point accuracy, lag, false switches, ad-lib stability), with an oracle baseline for comparison.

Slide import and real-time playback stay deferred. Contract: `design_presentation_simulation.md`.

## Wave I: verification fixes for Waves G and H (specced October 6, 2026)
Waves G and H were delivered and independently verified: 11 of 12 items true to spec. Real-output review found defects the gates could not see:
- callback dots that never counted;
- asides drawn over the motif token and the avatar;
- empty thought bubbles;
- motif names the story never says;
- names on screen before the narration reveals them;
- image generation failing wholesale behind green gates;
- a director that loses the whole creative style to one repeated metaphor, so the creative budget measured a literal video;
- creative presentations without the license check or overlays;
- a presentation gate (G16) that exits 0 on failed bars and re-scores old jobs instead of running.

Wave I (I1–I9) fixes them and re-measures. **Issue 8 is open:** the presentation follower misses its accuracy bars, while the oracle meets them, so the deck and the tree are sound and the matcher is not. It awaits the user's selection.

## Wave J: the presentation follower bake-off (Issue 8 → Option A, selected October 7, 2026)
Two followers are built from deck-only knowledge with the existing models:
- **A1:** sentences anticipated from each slide, with a forward-biased tracker on a 10-word window; no LLM in the live loop;
- **A2:** the local LLM classifying which point is being spoken.

**The test:** each runs on a frozen corpus of 8 simulated talks (4 to decide on, 4 held out), judged by the unchanged scorer.

**The rule:** adopt the first contestant that meets every bar on both sets. A2 is built only if A1 misses. If neither meets them, the evidence goes back to the user.

Contract: `design_presentation_simulation.md` §6.6.

## After Wave J (deferred; each needs a user selection)
Video input with picture-in-picture · 16:9 output · **live mode** (streaming ASR → incremental planning → the same templates on a live clock, webcam in a corner) · multi-voice narration · Reddit URL fetch · public-domain photos · historical borders · a web review editor. See `ongoing_general_errors.md` §4.

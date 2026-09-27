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

Wave C (C1–C8) fixes them and re-measures. Issue 6 was decided on September 27, 2026: paraphrased dialogue is fine. Issue 7 (fewer words on screen in story videos, inspired by Casually Explained) awaits the user and would become the next wave.

## After Wave C (deferred; each needs a user selection)
Video input with picture-in-picture · 16:9 output · **live mode** (streaming ASR → incremental planning → the same templates on a live clock, webcam in a corner) · multi-voice narration · Reddit URL fetch · public-domain photos · historical borders · a web review editor. See `ongoing_general_errors.md` §4.

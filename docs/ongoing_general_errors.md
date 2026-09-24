# Engineering Issues & Decisions — Working Log

**What this file is:** the live queue of open issues, the decisions the user has made or still has to make, the deferred features and their triggers, and a one-line index of resolved work. The execution guide (`docs/agent_execution_guide.md`) is the build spec; this file is where findings and choices live.

**Filing format** is in `.agents/skills/bug_documentation_guidelines/SKILL.md`. Open issues end with a `Your selection: _____` line. **That line belongs to the user, and an agent must never fill it in.**

---

## 1. Open & in-flight

**Wave A (Offline MVP, items A1–A21) was approved on September 23, 2026.** The spec is `agent_execution_guide.md` §3. **Status: not started.** The repository holds the design set and frozen fixture scripts only.

---

## ⚠️ Unresolved Issues & Suggestions

### Issue 1: Default narrator voice

**Status**: ⚠️ Awaiting evidence. Item A7 renders the first paragraph of `fixtures/scripts/molasses_flood.txt` in four Kokoro voices to `docs/evals/voices/`. Until the user selects, the default is `af_heart` (`design_audio_and_timing.md` §2), and `--voice` overrides it per job. Non-blocking.

**Option A (recommended)**: **`af_heart`** (American English, female). Kokoro's highest-graded voice.
  - *Pros*: The most natural prosody of the set; already the default, so nothing changes.
  - *Cons*: Some listeners associate Reddit-story narration with a male voice.

**Option B**: **`am_michael`** (American English, male).
  - *Pros*: A deeper, documentary-style read; suits history pieces.
  - *Cons*: Graded lower than `af_heart` in Kokoro's own voice table; can sound flatter on questions.

**Option C**: **`bm_george`** (British English, male).
  - *Pros*: A distinct "history documentary" colour.
  - *Cons*: A British reading of American stories (Reddit) may feel off; changes number and date phrasing.

**Option D**: **`af_bella`** (American English, female).
  - *Pros*: Brighter and more energetic, suited to short-form drama.
  - *Cons*: Can feel too upbeat for serious history.

Your selection: _____

---

### Issue 2: Local illustration model

**Status**: ⚠️ Awaiting evidence. Item A20 renders every place and set-piece prompt from the three fixture bibles with both models (same prompts, same seeds) into `docs/evals/image_models_<date>.png`, with per-image timings. Until the user selects, the default is **FLUX.2 [klein] 4B** (`design_visual_direction.md` §7). Non-blocking.

**Option A (recommended)**: **FLUX.2 [klein] 4B** via mflux, 4 steps.
  - *Pros*: Apache-2.0; the fastest option, which protects the 10-minute budget; supports reference-image editing, a future route to richer set-piece consistency.
  - *Cons*: Smaller model; may follow the flat-vector style prompt less tightly.

**Option B**: **Z-Image-Turbo** (6B) via mflux, 9 steps.
  - *Pros*: Apache-2.0; strong prompt adherence and detail.
  - *Cons*: More steps and parameters, so slower per image; tuned toward realism, so it may resist the flat style.

Your selection: _____

---

## 2. Lessons that still bite

None yet: this project has no history. Transferable lessons from the user's previous projects are folded into `agent_execution_guide.md` §7 (Validation standard) and `design_testing_and_validation.md`'s preamble. Add an entry here only for a trap that is **live in this codebase**, and point it at the contract that now owns the detail.

---

## 3. Resolved index

One line per delivered item, added in the item's own commit: `A<n> — <title> — <short sha> — <key measured numbers>`.

*(empty)*

---

## 4. Deferred features (do not start without a selection)

| Id | Feature | Trigger to start | Notes |
|---|---|---|---|
| D1 | Video input + PiP of the original speaker | Wave A complete **and** the user selects it | The 9:16 PiP placement is an open design question (`design_future_live_and_video.md` §2) |
| D2 | 16:9 output | User selects it | Roughly doubles template work |
| D3 | Multi-voice narration (character voices) | User selects it | Needs a dialogue-attribution step |
| D4 | **Live mode** (speak in real time, webcam in a corner) | Wave A complete **and** the user answers the three questions in `design_future_live_and_video.md` §4 | The end goal |
| D5 | Reddit URL fetching | User selects it | Terms-of-service review first |
| D6 | Public-domain photo sourcing (e.g. Wikimedia) | User selects it | Requires runtime network, which conflicts with the local-only policy as written |
| D7 | Historical map borders | User selects it | The MVP uses modern borders |
| D8 | Web editor for the review gate | User selects it | The MVP gate is JSON edit + contact sheet |
| D9 | Cloud LLM planner backend | Only if the local planner fails its eval bars on both candidate models **and** the user accepts a paid API | Reverses a user decision; needs explicit selection |

---

## 5. Decision log

**September 23, 2026: design grilling (user).** Offline first; template library; history + Reddit-style stories first; MVP inputs text script + audio only; mixed imagery (vector + local illustration + open map data); Python pipeline + TypeScript/Remotion renderer; **fully local**; 9:16 first; word-by-word karaoke captions; flat editorial vector; 1–3 min videos within ~10 min; scenes + persistent cast; single narrator; **mandatory review gate**; music + SFX from a user-supplied pack; live mode later with the webcam in a corner, with some sources (Reddit, history) having no speaker video at all.

**September 23, 2026: design decisions (designer; revisit only through an issue):** cast drawn only as vector avatars (a generated portrait cannot change expression and drifts between scenes); grounding of on-screen numbers, dates and quotes as a hard gate; gazetteer-first geo; Kokoro's own timestamps rather than re-transcription for the text path; scenes at absolute frames rather than `TransitionSeries`; Python as the contract source of truth; `gemma4:26b` as planner with `qwen3.6:35b` as the measured escalation candidate.

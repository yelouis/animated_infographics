# Engineering Issues & Decisions — Working Log

**What this file is:** the live queue of open issues, the decisions the user has made or still has to make, the deferred features and their triggers, and a one-line index of resolved work. The execution guide (`docs/agent_execution_guide.md`) is the build spec; this file is where findings and choices live.

**Filing format** is in `.agents/skills/bug_documentation_guidelines/SKILL.md`. Open issues end with a `Your selection: _____` line. **That line belongs to the user, and an agent must never fill it in.**

---

## 1. Open & in-flight

**Wave A (Offline MVP) was approved on September 23, 2026, and revised on September 24, 2026 to incorporate the selections on Issues 1 and 2. It now has 22 items (A1–A22).** The spec is `agent_execution_guide.md` §3. **Status: not started.** The repository holds the design set and the four frozen fixture scripts only (two history pieces; two complete r/stories-style stories).

**Selected, specced, not yet delivered.** When an item lands, its implementing commit collapses the issue below into one line in §3.

### Issue 1: Default narrator voice → specced as **A8** (voice selection) and **A9** (narration)

**Status**: ✅ Selected September 24, 2026. The rule and its interpretation are in `design_planner.md` §10: `af_heart` iff the story is first person **and** the narrator explicitly identifies as female; otherwise `am_michael`. That covers every history story and every first-person story without self-identification. The four-voice listening samples previously planned for this issue are dropped as unnecessary.

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

Your selection: Proceed with Option A and B. If the story from reddit seems to be from a female's perspective then use af_heart, else use am_michael.

---

### Issue 2: Local illustration model → specced as **A21** (illustrations)

**Status**: ✅ Selected September 24, 2026. FLUX.2 [klein] 4B is the only image model (`design_visual_direction.md` §7). The side-by-side benchmark against Z-Image-Turbo previously planned for this issue is dropped.

**Option A (recommended)**: **FLUX.2 [klein] 4B** via mflux, 4 steps.
  - *Pros*: Apache-2.0; the fastest option, which protects the 10-minute budget; supports reference-image editing, a future route to richer set-piece consistency.
  - *Cons*: Smaller model; may follow the flat-vector style prompt less tightly.

**Option B**: **Z-Image-Turbo** (6B) via mflux, 9 steps.
  - *Pros*: Apache-2.0; strong prompt adherence and detail.
  - *Cons*: More steps and parameters, so slower per image; tuned toward realism, so it may resist the flat style.

Your selection: Proceed with Option A.

---

## ⚠️ Unresolved Issues & Suggestions

None awaiting a selection.

---

## 2. Lessons that still bite

None yet: this project has no history. Transferable lessons from the user's previous projects are folded into `agent_execution_guide.md` §7 (Validation standard) and `design_testing_and_validation.md`'s preamble. Add an entry here only for a trap that is **live in this codebase**, and point it at the contract that now owns the detail.

---

## 3. Resolved index

One line per delivered item, added in the item's own commit: `A<n> — <title> — <short sha> — <key measured numbers>`.

A1 — Bootstrap — b1ad44a — G1–G7 green, battery 7/7 built gates pass, 1 pytest passed, 1 vitest passed
A2 — Setup script and doctor — 9afa5d6 — 20/20 checks OK in doctor, setup.sh idempotent (twice 0), G14 green

---

## 4. Deferred features (do not start without a selection)

| Id | Feature | Trigger to start | Notes |
|---|---|---|---|
| D1 | Video input + PiP of the original speaker | Wave A complete **and** the user selects it | The 9:16 PiP placement is an open design question (`design_future_live_and_video.md` §2) |
| D2 | 16:9 output | User selects it | Roughly doubles template work |
| D3 | Multi-voice narration (character voices) | User selects it | Needs a dialogue-attribution step. `voice.json` already records `male` separately from `unknown` for this. |
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

**September 24, 2026: selections (user).** Issue 1 → Options A + B with an automatic rule: female-perspective Reddit story → `af_heart`, else `am_michael`. Issue 2 → Option A, FLUX.2 [klein] 4B.

**September 24, 2026: consequences (designer):**
- A new `voice` stage runs before narration, because the voice must be known before audio exists (`design_planner.md` §10).
- "Female perspective" means **explicit self-identification** checked against the text, never a stereotype guess. The default is `am_michael`; `af_heart` needs evidence.
- `--voice` is restricted to the two installed voices (local-only policy).
- The LLM backend moves ahead of narration in the build order, so Wave A is renumbered to 22 items.
- **Fixtures replaced (user request: "the scripts chosen are too short… a complete story like maybe from r/stories"):** the two short AITA fragments became two complete, original r/stories-style stories. `story_recipe_box.txt` (407 words, self-identified female narrator → `af_heart`) and `story_room_12.txt` (365 words, gender never stated, inference traps → `am_michael`). They are original rather than copied posts, for copyright and so their facts are ours to freeze. The end-to-end budget is re-anchored to the longest (~3 min).
- The evidence rule was tightened to two self-identification forms after the new story's traps ("a woman walked in…", "Grandma Rose") passed a looser draft. 23 measured cases are in `design_planner.md` §10.
- The narrator's avatar gets no facial hair when the narrator is female.

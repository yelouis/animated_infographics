# Engineering Issues & Decisions — Working Log

**What this file is:** the live queue of open issues, the decisions the user has made or still has to make, the deferred features and their triggers, and a one-line index of resolved work. The execution guide (`docs/agent_execution_guide.md`) is the build spec; this file is where findings and choices live.

**Filing format** is in `.agents/skills/bug_documentation_guidelines/SKILL.md`. Open issues end with a `Your selection: _____` line. **That line belongs to the user, and an agent must never fill it in.**

---

## 1. Open & in-flight

**Wave A (Offline MVP) was approved on September 23, 2026, and revised on September 24, 2026 to incorporate the selections on Issues 1 and 2. It now has 22 items (A1–A22).** The spec is `agent_execution_guide.md` §3. **Status: not started.** The repository holds the design set and the four frozen fixture scripts only (two history pieces; two complete r/stories-style stories).

**Selected, specced, not yet delivered.** When an item lands, its implementing commit collapses the issue below into one line in §3.

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
A2 — Setup script and doctor — 927d076 — 20/20 checks OK in doctor, setup.sh idempotent (twice 0), G14 green
A3 — Fixtures — 7924f59 — 15 fixture files generated and checksummed, 4 scripts verified against design SHA-256, music peak -20.0 dBFS, 5 SFX generated
A4 — Data contracts and schema sync — c7f0c4b — G8 green (11 files in sync), 10/10 pytest passed, 16 template props validated, G5 compiles iconMap.ts
A5 — Job store, CLI and the review gate — 617e569 — G1–G8, G14 green; 19 pytest passed; all 5 exit 3 refusals verified; journey test verified and falsified (red then green)
A6 — Timing core — 10dd3a2 — G1–G8, G14 green; 39 pytest passed (20 new timing unit tests); 500-stream property test verified; all 3 falsifications verified (red then green)
A7 — LLM backend — 7186803 — G1–G8, G11, G14 green; 45 fast pytest + 1 slow integration test passed; G11 active; 20/20 structured output conformance on gemma4:26b (mean latency 1.96s); both falsifications verified (red then green)
A8 — Narrator voice selection — 9590fb7 — G1–G8, G11, G14 green; 82 fast pytest + 3 slow tests passed; all 23 evidence cases verified; 4 fixtures matched expected facts; all 7 falsifications verified (red then green)
A9 — Narration (Kokoro) — 5824005 — G1–G8, G11, G14 green; 96 fast pytest + 8 slow tests passed; 4 fixtures synthesized with exact sample accounting; loudness -16 ± 0.5 LUFS; emu_war 11.65s (bar ≤ 60s); spectral centroid verified; both falsifications verified (red then green)
A10 — Transcription (Whisper) — 715d670 — G1–G8, G11, G14 green; 98 fast pytest + 11 slow tests passed; molasses_flood_say WER 4.17% (bar ≤ 8%); Kokoro vs Whisper timing: match 97.5% (bar ≥ 90%), median error 40.0ms (bar ≤ 80ms), p95 error 239.4ms (bar ≤ 250ms); emu_war transcribe 6.00s (bar ≤ 45s); falsification verified (red then green)
A11 — Renderer foundation (+ kinetic_quote) — 731ad9e — G1–G9, G11, G14 green; G9 active (pure); 100 fast pytest passed; smoke media render 1080x1920@30fps verified with ffprobe; sync probe flips verified at frames 29/31 (0 vs 255) and 59/61 (255 vs 0); gallery kinetic_quote min/typical/max 0 overflows; both falsifications verified (red then green)
A12 — Bible and geo resolution — 208d445 — G1–G9, G11, G14 green; 118 fast pytest + 13 slow tests passed; Boston, Duluth, Thunder Bay, Amarillo resolved via GeoNames gazetteer; antimeridian-aware country bbox checking; female narrator facial hair repaired to none; both falsifications verified (red then green)
A13 — Segmentation — 1d47dd8 — G1–G9, G11, G14 green; 125 fast pytest + 15 slow tests passed; 4 fixtures segmented with continuous narration tiling and duration bounds [1500, 8000]ms; beat counts: molasses_flood 8, emu_war 20, story_recipe_box 26, story_room_12 24; falsification verified (red then green)
A14 — Storyboard planning and the planner eval — 2b7dc04 — G1–G9, G11, G14 green; 149 fast pytest passed; planner eval passed 4/4 fixtures with 0 violations, fallback L2 0.0% (bar ≤ 15%), distinct templates 6/11/16/13 (bars ≥ 5/7), story_recipe_box wall time 49.0s (bar ≤ 240s), voice match 4/4; falsification verified (red then green)
A15 — Compile and preview — 5260ab2 — G1–G9, G11, G14 green; 158 fast pytest passed; molasses_flood compiled with 10 scenes, duration 1834 frames, 0 overflow, Ajv & Python valid; both falsifications verified (red then green)

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

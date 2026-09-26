# Engineering Issues & Decisions — Working Log

**What this file is:** the live queue of open issues, the decisions the user has made or still has to make, the deferred features and their triggers, and a one-line index of resolved work. The execution guide (`docs/agent_execution_guide.md`) is the build spec; this file is where findings and choices live.

**Filing format** is in `.agents/skills/bug_documentation_guidelines/SKILL.md`. Open issues end with a `Your selection: _____` line. **That line belongs to the user, and an agent must never fill it in.**

---

## 1. Open & in-flight

**Wave A (Offline MVP, A1–A22) was delivered as 22 commits ending at `e374a15`, and independently verified on September 25, 2026.** Every gate G1–G14 was re-run bare in a separate session and reproduced green (numbers in `agent_execution_guide.md` §1). The voice rule (Issue 1) and the image model (Issue 2) are implemented as specced (§3).

**Verification also found defects that no gate could see. They are specced as Wave B in `agent_execution_guide.md`, now B1–B17 including the three selections below.** The defect fixes restore behaviour the user already approved. The largest:
- Music and SFX are **silently dropped** from every video that goes through the edit → `preview` → `approve` → `render` review journey (reproduced in the implementing agent's runs and in the verification run).
- About **one scene in five shows truncated text** ("Rescuers wade through waist-"), because length limits were sent to the model as hard grammar constraints.
- Two **crash paths** in the planner.
- An **unreadable map** and **unreadable captions over light illustrations**. Both came from design values that were never measured as composited; the design is now corrected.
- The **performance budget was never measured cold**.

**Selected September 25, 2026, specced, not yet delivered:** Issues 3, 4 and 5 below, specced as **B10**, **B5** and **B6**. When the delivering item lands, its commit collapses the issue into one line in §3.

### Issue 3: Generated illustrations sometimes contain fake writing → specced as **B10**

**Status**: ✅ Selected September 25, 2026 (Option A, with the user's refinement that text is fine when the description calls for it). The contract, with its design-time measurements (7/7 correct on the labelled `fixtures/vision/` set with the final prompt; a naive yes/no prompt flagged 2 of 4 clean images), is `design_visual_direction.md` §7.1. Original finding: verified September 25, 2026 in the E2E job `story-recipe-box-20260925-180627`: set piece `v1` ("An old wooden box overflowing with hundreds of handwritten recipe cards") rendered pseudo-handwriting on the cards ("Peclpte De fonts ann) Rlondes."). The other two images reviewed (the blueberry pie, the Duluth waterfront) are clean, flat and on-palette. `STYLE` already says "No text, no letters, no words", but FLUX.2 [klein] 4B does not obey it for subjects that inherently carry writing. Today the reviewer can see it at the gate but has no way to regenerate a single image.

**Option A (recommended)**: **Local vision check with an automatic retry** — after each generation, ask `gemma4:26b` (already installed, and it accepts images) a structured question: "does this image contain letters, words or text-like marks?". On *yes*, regenerate with seed + 1, up to 2 retries, then fall back to the icon and list it in `preview/report.json`.
  - *Pros*: Automatic and fully local, using the model already loaded for planning; catches it before the reviewer ever sees it.
  - *Cons*: About +3–5 s per image (up to 3× generation time on a retry); a vision model can miss faint scribbles or flag patterns as text, so it needs a small labelled eval set (the fixture images) to set expectations.

**Option B**: **Steer subjects away from writing** — the bible prompt tells the model not to choose set pieces whose defining feature is writing (letters, cards, signs, books, newspapers, menus), and a validator rejects `visual_description`s containing those words.
  - *Pros*: Zero extra compute; deterministic.
  - *Cons*: Removes some story-critical objects. In `story_recipe_box` the recipe card *is* the story. A word list will always have gaps.

**Option C**: **Rely on the review gate, plus a one-command regenerate** — add `infographics regenerate <job> <entity_id>` (next seed, then re-preview).
  - *Pros*: Human judgement; cheap to build.
  - *Cons*: Manual work in any video that hits it.

Your selection: Proceed with Option A. Though, in the example provided, I think that text is fine if the description calls for text like a recipe.

---

### Issue 4: Timeline "dates" that are not dates → specced as **B5**

**Status**: ✅ Selected September 25, 2026 (Option A). The contract is `design_planner.md` §8 (the date-label row) and `design_templates.md` §2.16. Original finding: verified September 25, 2026 in the same job:
- Scene `s023` is a `timeline` whose `date_label`s are "50+ Years", "No Record" and "Memory Only".
- Scene `s001` has three events all labelled "2013".
- Scene `s010` uses "Last Spring", "Present" and "Now".

The date-grounding rule (`design_planner.md` §8) only checks digits that are present, so a label with no digits passes. Nothing requires labels to be distinct or in order.

**Option A (recommended)**: **Digits or a closed list of relative-time phrases, distinct, in order** — every `date_label` must contain a grounded digit run **or** be one of a fixed list (Today, Now, Present day, That night, That weekend, The next day, Days later, Weeks later, Months later, Years later, Last spring/summer/fall/winter, Last year, Earlier, Later); labels must be pairwise distinct; years present must be non-decreasing.
  - *Pros*: Keeps timelines usable for personal stories ("Last spring → That weekend → Months later") while rejecting nonsense like "No Record".
  - *Cons*: A list to maintain; unusual valid phrasings are rejected and the scene falls back to its alternate template.

**Option B**: **Strict: every label has a grounded digit**, plus distinct and non-decreasing.
  - *Pros*: Simplest and fact-safe.
  - *Cons*: Personal stories rarely have dated sequences, so `timeline` becomes effectively history-only.

**Option C**: **Any short label, but distinct**.
  - *Pros*: Most flexible.
  - *Cons*: "No Record" / "Memory Only" still pass.

Your selection: Proceed with Option A.

---

### Issue 5: Meaning errors that no validator can see → specced as **B6**

**Status**: ✅ Selected September 25, 2026 (Option A). The contract is `design_planner.md` §6 item 6 (deterministic rules) and §11 (the critic, with design-time measurements: 4/4 regression cases on seeds 7–9). Original finding: verified September 25, 2026: at least 4 of the 32 scenes in the `story_recipe_box` E2E job carry a meaning error while passing every schema, grounding and fit check.
- `s012` attributes Danny's texted question to the narrator ("Me").
- `s015` gives the narrator's "Rose?" an *angry* tone.
- `s004` stamps the diner "40 years ago"; the text says it ran for forty years.
- Across the fixtures, one `stat_callout` put `$` in `suffix`.

These are semantic, not format, errors.

**Option A (recommended)**: **Two cheap deterministic rules plus a targeted critic pass.**
  1. Currency symbols (`$ £ €`) are allowed only in `prefix`; an `era_label` may contain "ago" only if the transcript does.
  2. One extra local LLM call per *people* scene (`dialogue`, `text_thread`, `emotion_beat`, and `kinetic_quote` with an attribution): "in this beat, who says or feels this, and in what tone?". A mismatch with the props triggers one props retry.
  - *Pros*: Aims directly at the observed failure classes; about +6–10 calls per video (~15 s at measured latency).
  - *Cons*: The critic can itself be wrong; adds prompt surface to maintain.

**Option B**: **Deterministic rules only** (part 1 of A).
  - *Pros*: Zero runtime cost; fully predictable.
  - *Cons*: Attribution and tone errors remain for the reviewer.

**Option C**: **Rely on the review gate** (no change).
  - *Pros*: Nothing to build; the gate exists for exactly this.
  - *Cons*: The reviewer must catch meaning errors in every video.

**Option D**: **Evaluate `qwen3.6:35b` as the planner** on the four fixtures with a hand-scored semantic rubric, and switch if it scores higher within the 240 s planner bar.
  - *Pros*: May fix several classes at once.
  - *Cons*: A 23 GB model, slower; needs a rubric and human scoring.

Your selection: Option A

---

## ⚠️ Unresolved Issues & Suggestions

None awaiting a selection.

---

## 2. Lessons that still bite

Each entry is a trap that is **live in this codebase**, found in the September 25, 2026 verification of Wave A. It points at the contract that now owns the detail.

#### 2.1 Constrained decoding truncates to satisfy `maxLength`; it does not shorten

Ollama enforces a schema `maxLength` by force-closing the string at the limit. 34 of 701 on-screen strings were cut mid-word or mid-thought and **still passed every validator**. That made the planner eval's 0.0% fallback rate a symptom, not a success. **A perfect score from a gate is a reason to look harder.** Contract: `design_planner.md` §1 (LLM-facing schemas carry no length constraints).

#### 2.2 Invocation options are not job state

`compile` read music and SFX from the command-line context. `preview`, `rerun` and `render` receive no such options, and invalidation deletes `compile`'s outputs. So every reviewed-and-edited video lost its music and SFX, and the E2E never asserted they survived. **Anything a later stage needs must be copied into the job and recorded.** Contract: `design_system_architecture.md` §4.

#### 2.3 A value that is never measured as composited passes every gate

The map's land/sea pair (1.30 : 1) and captions over illustrations (1.95 : 1) were spec values, implemented exactly, invisible on screen, and green in every gate. The contrast test measured flat token pairs only. Contract: `design_visual_direction.md` §2.1.

#### 2.4 Warm-cache timings are not a budget measurement

The E2E's planning stages took 0.0–0.2 s because the LLM cache was warm, yet the delivery report called the 10-minute budget "met". Contract: `design_testing_and_validation.md` §5 (`scripts/measure_budget.sh`).

#### 2.5 A commit cannot contain its own hash

The resolved index cited 22 SHAs. 14 pointed at pre-amend commits no longer on `main` and one (`5b88db1`) at nothing, because each line was written and then the commit amended. **From Wave B on, every commit subject carries its item id as the Conventional-Commit scope (`fix(b3): …`), and resolved lines cite that id rather than a hash.** Contract: `agent_execution_guide.md` §0.

---

## 3. Resolved index

One line per delivered item: `<id> — <title> — <commit> — <verified result>`. Wave A hashes below were **corrected on September 25, 2026** to the commits actually on `main` (`git log --reverse 9d704f2..e374a15`).

**Wave A — delivered; verified September 25, 2026.** "✓" = matches its spec. "→ B<n>" = delivered, but verification found a defect specced in Wave B.

- A1 — Bootstrap — `4df212a` — ✓ toolchains, battery; G1–G7 reproduce.
- A2 — Setup + doctor — `927d076` — ✓ doctor 21 checks OK; → B15 (the README's credits are inaccurate).
- A3 — Fixtures — `66c11a9` — ✓ the four story SHA-256 values match; `CHECKSUMS` verifies from `fixtures/` (accepted equivalent, see guide §5.2).
- A4 — Contracts + schema sync — `5ad59ba` — ✓ G8 reproduces.
- A5 — Job store, CLI, review gate — `617e569` — ✓ gate logic correct (state + approval hash + timeline hash; no bypass); → B1 (music/SFX lost across `preview`/`rerun`).
- A6 — Timing core — `10dd3a2` — ✓ round-half-up, lead, beats, captions; → B14 (`timing/sfx.py` is dead duplicate code).
- A7 — LLM backend — `7186803` — ✓ entry-point counter, cache key, retries; → B2 ("not found" in a 200 body crashes as a missing model).
- A8 — Narrator voice selection — `9590fb7` — ✓ five steps in order, four named sub-rules, 23 evidence cases.
- A9 — Narration (Kokoro) — `5824005` — ✓ slow suite green.
- A10 — Transcription (Whisper) — `bc78bf8` — ✓ slow suite green (WER and timing bars per the agent's report).
- A11 — Renderer foundation — `92dbcd3` — ✓ clock, spans, sync probe; → B13 (purity-gate exemption too broad; fixtures copied into every render).
- A12 — Bible + geo — `1eb9146` — ✓ repairs 1–5, gazetteer; antimeridian handling accepted (guide §5.2).
- A13 — Segmentation — `f8210b7` — ✓.
- A14 — Storyboard + planner eval — `3bc92d5` — → B3 (select/props crash on malformed JSON), B4 (scale-word grounding leak), B7 (truncation via `maxLength`).
- A15 — Compile + preview — `4d7bf6c` — → B1 (music/SFX), B8 (failed images not flagged on the contact sheet).
- A16 — Final render + E2E — `0a73878` — ✓ `verify.json` is a real gate; → B16 (E2E asserts neither music/SFX nor a computed sync count).
- A17 — Visual primitives + gallery gate — `346ba96` — ✓ 51 goldens compared, hold motion; → B13 (overflow check fails open; stale output dirs).
- A18 — Templates: statement set — `ca735c5` — ✓.
- A19 — Templates: people set — `b205b77` — → B12 (`kinetic_quote` attribution is a monogram, not the avatar).
- A20 — Templates: place & time set — `9cddf93` — → B11 (caption scrim), B12 (map legibility); both are spec defects, now corrected in the design.
- A21 — Illustrations — `142b6a7` — ✓ 4B only, `STYLE` byte-identical, seed/cache per design; → B9 (mflux invoked through a symlink in `~/.local/bin`); fake writing in one image → Issue 3 → B10.
- A22 — E2E, offline, budget, README — `e374a15` — ✓ G13 offline gate real (self-check + fresh cache); → B17 (budget never measured cold), B15 (README).

**Issues:**
- **Issue 1 — Narrator voice** — selected September 24, 2026: *"Proceed with Option A and B. If the story from reddit seems to be from a female's perspective then use af_heart, else use am_michael."* — delivered by A8 `9590fb7` + A9 `5824005`. Verified September 25: `voice.json` matched the expectation on 4 of 4 fixtures, in both the cold planner eval and the E2E (`af_heart` for `story_recipe_box` via evidence "As the only granddaughter, I"; `am_michael` for the other three); `--voice am_michael` makes 0 voice-stage LLM calls. The rule's permanent home is `design_planner.md` §10.
- **Issue 2 — Illustration model** — selected September 24, 2026: *"Proceed with Option A."* — delivered by A21 `142b6a7`. Verified September 25: mflux runs with `--model flux2-klein-4b` only, 1024², 4 steps, q8; no Z-Image code path exists. The permanent home is `design_visual_direction.md` §7.

**Wave B:** *(empty; items land here as they are delivered)*

---

## 4. Deferred features (do not start without a selection)

| Id | Feature | Trigger to start | Notes |
|---|---|---|---|
| D1 | Video input + PiP of the original speaker | User selects it | The 9:16 PiP placement is an open design question (`design_future_live_and_video.md` §2) |
| D2 | 16:9 output | User selects it | Roughly doubles template work |
| D3 | Multi-voice narration (character voices) | User selects it | Needs a dialogue-attribution step (see Issue 5 for how often attribution is wrong today). `voice.json` already records `male` separately from `unknown`. |
| D4 | **Live mode** (speak in real time, webcam in a corner) | Wave B complete **and** the user answers the three questions in `design_future_live_and_video.md` §4 | The end goal |
| D5 | Reddit URL fetching | User selects it | Terms-of-service review first |
| D6 | Public-domain photo sourcing (e.g. Wikimedia) | User selects it | Requires runtime network, which conflicts with the local-only policy as written |
| D7 | Historical map borders | User selects it | The MVP uses modern borders |
| D8 | Web editor for the review gate | User selects it | The MVP gate is JSON edit + contact sheet |
| D9 | Cloud LLM planner backend | Only if the local planner fails its eval bars on both candidate models **and** the user accepts a paid API | Reverses a user decision; needs explicit selection |

---

## 5. Decision log

**September 23, 2026: design grilling (user).** Offline first; template library; history + Reddit-style stories first; MVP inputs text script + audio only; mixed imagery (vector + local illustration + open map data); Python pipeline + TypeScript/Remotion renderer; **fully local**; 9:16 first; word-by-word karaoke captions; flat editorial vector; 1–3 min videos within ~10 min; scenes + persistent cast; single narrator; **mandatory review gate**; music + SFX from a user-supplied pack; live mode later with the webcam in a corner, with some sources (Reddit, history) having no speaker video at all.

**September 23, 2026: design decisions (designer; revisit only through an issue):** cast drawn only as vector avatars; grounding of on-screen numbers, dates and quotes as a hard gate; gazetteer-first geo; Kokoro's own timestamps for the text path; scenes at absolute frames rather than `TransitionSeries`; Python as the contract source of truth; `gemma4:26b` as planner with `qwen3.6:35b` as the measured escalation candidate.

**September 24, 2026: selections (user).** Issue 1 → Options A + B with an automatic rule: female-perspective Reddit story → `af_heart`, else `am_michael`. Issue 2 → Option A, FLUX.2 [klein] 4B. Test stories replaced by two complete, original r/stories-style stories at the user's request.

**September 24, 2026: consequences (designer):** a `voice` stage before narration; "female perspective" = explicit, checkable self-identification (default `am_michael`); `--voice` restricted to the two installed voices; the LLM backend moved ahead of narration (22 items); the evidence rule tightened to two grammatical forms (23 measured cases); a female narrator's avatar gets no facial hair.

**September 25, 2026: verification of Wave A (designer).** All 14 gates reproduced green in an independent session. Defects invisible to the gates were found and specced as Wave B. Design contracts corrected where the design itself was the cause:
- map colours, markers and a lakes layer; the image scrim and a rule for text over images (`design_templates.md` §2.13–2.15, `design_visual_direction.md` §2.1);
- `kinetic_quote` attribution clarified;
- LLM-facing schemas without length limits, a text-completeness validator, scale-word grounding, error classification, and "every call through `run_with_retries`" (`design_planner.md` §1, §6, §8);
- job-local inputs authoritative (`design_system_architecture.md` §4);
- fail-closed gallery gate, an exact purity exemption, E2E music/SFX assertions, cold-budget procedure (`design_testing_and_validation.md`).

Three questions filed for the user (Issues 3–5).

**September 25, 2026: selections (user).**
- Issue 3 → Option A: *"Proceed with Option A. Though, in the example provided, I think that text is fine if the description calls for text like a recipe."*
- Issue 4 → Option A: *"Proceed with Option A."*
- Issue 5 → Option A: *"Option A"*.

**September 25, 2026: consequences (designer, measured before specifying):**
- The text check uses a transcription-style prompt with `num_predict` 96 and a ≥ 3-alphanumeric rule, because a yes/no prompt produced 2 false positives on 4 clean images and an uncapped request hung past 300 s.
- "Description calls for text" is a deterministic word/phrase list; bare "sign" is excluded (it matched "signs of structural weakness").
- The critic is blind, and a speaker it reads as "unknown" never counts as a mismatch, but an unsupported strong tone does. That exact combination is what separated the real errors from correct scenes on seeds 7–9.
- Wave B grows to 17 items, reordered so a single planner-eval re-run covers every planner change and the cold budget run measures the finished system.

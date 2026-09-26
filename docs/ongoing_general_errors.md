# Engineering Issues & Decisions — Working Log

**What this file is:** the live queue of open issues, the decisions the user has made or still has to make, the deferred features and their triggers, and a one-line index of resolved work. The execution guide (`docs/agent_execution_guide.md`) is the build spec; this file is where findings and choices live.

**Filing format** is in `.agents/skills/bug_documentation_guidelines/SKILL.md`. Open issues end with a `Your selection: _____` line. **That line belongs to the user, and an agent must never fill it in.**

---

## 1. Open & in-flight

**Wave B (B1–B17) was delivered as 17 commits (`cad065d`…`beb4c4f`) and independently verified on September 26, 2026.** Every gate G1–G14 was re-run bare in a separate session (numbers in `agent_execution_guide.md` §1), and the cold budget was re-measured. Each item's source was read against its spec: **all 17 do what their specs say** (per-item verdicts in §3).

**But the verification looked at real output, not just specs, and found problems no gate covers.** Three of them come from gaps in the Wave B specs themselves. They are specced as **Wave C (C1–C7)** in `agent_execution_guide.md`; each is a fix within behaviour the user already approved:
- **The Issue 5 critic misses the error it was selected to catch.** In the real `story_recipe_box` run, Danny's text "Who is Walter Lindqvist…" was still credited to the narrator and the critic **agreed**. Cause: the beat splitter (`design_audio_and_timing.md` §7) gave colons a bonus and split "…texted me a photo:" from the quote, and the critic treated the previous beat as "context only". Both were measured and fixed in the design (C1, C2).
- **A fifth of critic disagreements (30 of 149) kept the known-wrong scene**, because the retry had a single attempt (C3).
- **Internal ids on screen:** 4 in 311 unique scenes, e.g. "One card missing from the recipe box (v1)." (C4).
- **Caption words collide** when a long word is highlighted ("theengagementfell"). Present since Wave A; the spec scaled the word without reserving space (C5).
- Hygiene: a hand-copied country-code table; a missing music file silently dropped (C6).

**One question needs the user: Issue 6 below.** It does not block Wave C.

## ⚠️ Unresolved Issues & Suggestions

### Issue 6: Dialogue and text messages that the story never contains

**Status**: ⚠️ Confirmed Unresolved — Verified September 26, 2026 over the 61 `dialogue`/`text_thread` lines in Wave B's E2E storyboards: **only 18 (30%) are words that appear in the narration.** The other 43 are invented or paraphrased. Examples:
- `story_room_12`: the narrator and their wife text "You still awake?" / "Yeah, just resting. Why?" / "Just checking in. Love you." The story only says the narrator texted their wife to make sure she was awake.
- `story_recipe_box`: a phone call becomes a text thread with an "Unknown Number" ("Hello? I'm looking for someone regarding Rose." / "Who is this?"), and the narrator asks Walt "Is this Walt? I'm looking for Rose."

The planner's own principle (`design_planner.md`) says quoted words shown on screen must come from the narration; `kinetic_quote` enforces that, but `dialogue` and `text_thread` never did. For history this would put invented words in real people's mouths. For an anonymous Reddit-style story, dramatising may be what you want.

**Option A (recommended)**: **Faithful for real people, dramatised for personal stories** — when `bible.genre == "history"`, every `dialogue`/`text_thread` line must be a verbatim span of the narration (the same check as `kinetic_quote`); for `personal_story` and `other`, lines may paraphrase, but must be a verbatim span **or** share at least 60% of their content words with the current beat (so invented exchanges like "Just checking in. Love you." are rejected).
  - *Pros*: Never invents words for historical figures; keeps Reddit-style stories lively; both checks are deterministic.
  - *Cons*: A word-overlap threshold is a proxy, and it was **measured** (September 26, 2026, over the 51 unique lines, with simple suffix stemming and cast names counted as present). At 60% it:
    - rejects all 8 clear inventions scoring 0% ("Just checking in. Love you.", "Who is this?", "[Silence]"…);
    - but **passes one** ("Is this Walt? I'm looking for Rose.", 67%);
    - and **rejects two faithful paraphrases** ("Do you mind if I use it?", 50%; "It came with a note.", 50%).

    It also means fewer dialogue scenes in history videos.

**Option B**: **Always verbatim** — every line, in every genre, must be a verbatim span of the narration.
  - *Pros*: Simplest and strictest; nothing on screen is ever invented.
  - *Cons*: Only ~30% of today's lines would survive; many story beats (reported speech, texts described but not quoted) lose their dialogue visual and fall back to other templates.

**Option C**: **Paraphrase allowed everywhere, but no new content** — the 60% content-word overlap rule for every genre, history included.
  - *Pros*: Natural phrasing everywhere; blocks wholesale invention.
  - *Cons*: Historical figures can still be given paraphrased "quotes" they never said.

**Option D**: **Keep as is** — the reviewer judges at the gate.
  - *Pros*: Nothing to build; maximum creative freedom.
  - *Cons*: 70% of lines are invented today, and the gate relies on the reviewer knowing the source text.

Your selection: _____

---

## 2. Lessons that still bite

Each entry is a trap that is **live in this codebase**, found in the September 25 (Wave A) and September 26 (Wave B) verifications. It points at the contract that now owns the detail.

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

#### 2.6 A regression set built from tidy inputs can pass while production fails

The critic's regression set scored 4/4 on every seed. Every case had the speaker and the quote in the same beat, but the real pipeline's beat splitter separates them. On the real beats the critic agreed with a wrong attribution on three seeds out of three. **An upstream stage shapes a downstream check's input. Add real production cases to the set** (case E). Contracts: `design_planner.md` §11, `design_audio_and_timing.md` §7.

#### 2.7 An outcome metric must compare before and after

`critic.changed` was set whenever a retry *returned*, even when it returned the same props. Retries that *failed* were invisible, because their errors were not recorded. So "119 changed" overstated what the critic fixed, and "30 unchanged" had no explanation. **Count an effect by comparing the result to the original, and record why a repair did not happen.** Contract: `design_data_contracts.md` §6.

#### 2.8 A visual transform that does not reflow can break layout silently

`transform: scale(1.12)` on the active caption word never changes layout. On long words it swallowed the word spacing, from Wave A on, and every gate passed because nothing measured rendered gaps. **Measure the rendered result (here, empty-column runs), not the style values.** Contract: `design_visual_direction.md` §8.

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
- **Issue 3 — Generated illustrations fake writing** — selected September 25, 2026: *"Proceed with Option A. Though, in the example provided, I think that text is fine if the description calls for text like a recipe."* — delivered by B10 git log --grep "(b10)". Verified: vision check with gemma4:26b runs on generated illustrations not marked text_expected; transcription prompt with >= 3 alphanumeric rule classifies 7/7 fixture images on seeds 7 and 8; naive prompt falsified (flags waterfronts, scoring 5/7); recipe card entity v1 in story_recipe_box skipped as expected; text detected triggers up to 2 retries on seed+1, seed+2; 3 texty images marks failed and deletes image file; unavailable check keeps image as warning. The rules' permanent home is `design_visual_direction.md` §7.1.
- **Issue 4 — Timeline date labels** — selected September 25, 2026: *"Proceed with Option A."* — delivered by B5 git log --grep "(b5)". Verified: date_labels must contain a grounded digit run or match one of 17 relative time phrases; pairwise distinct; first four-digit years in event order non-decreasing. Wave A defects ("2013/2013/2013", "No Record", "Present") rejected; valid dates and relative phrases accepted. The rule's permanent home is `design_planner.md` §8.
- **Issue 5 — Meaning rules + people-scene critic** — selected September 25, 2026: *"Option A"* — delivered by B6 git log --grep "(b6)". Verified: currency symbols rejected in stat_callout suffix; ungrounded 'ago' rejected in location era_label; blind local critic checks dialogue, text_thread, emotion_beat, and attributed kinetic_quote with at most 1 retry and 0 loops; regression set classifies 4/4 cases as expected with gemma4:26b. The rules' permanent home is `design_planner.md` §6 item 6 and §11.

**Wave B — delivered; independently verified September 26, 2026.** Verdicts: B1 ✓ (a missing recorded input is silently dropped → C6) · B2 ✓ · B3 ✓ (7 `run_with_retries` sites; `generate_json` only in `llm.py`) · B4 ✓ · B5 ✓ (all 8 probe cases, exact error strings) · **B6** as specced, but the spec had gaps → C1, C2, C3 · B7 ✓ (the audit's 4 at-limit strings are complete phrases; the bar was corrected in `design_planner.md` §9) · B8 ✓ · B9 ✓ (symlink gone) · B10 ✓ (prompt and lists byte-identical) · B11 ✓ (the white worst case is legible) · B12 ✓ (Lake Superior drawn; country codes hand-copied → C6) · B13 ✓ · B14 ✓ · B15 ✓ · B16 ✓ (sync count parsed from JSON) · B17 ✓ (re-measured; see `agent_execution_guide.md` §1.3).

**Wave B:**

- B1 — Music and SFX survive the review journey — git log --grep "(b1)" — G1–G14 green bare, 171 passed (+2 tests); ingest records job-relative music/sfx; compile reads ingest.json on every run; review journey test verifies music and sfx survive edit and invalidation; e2e step 4 asserts music and sfx present in timeline and files.
- B2 — LLM error classification — git log --grep "(b2)" — G1–G14 green bare, 175 passed (+3 tests); 200 responses containing 'not found' accepted; 404 raises DependencyMissing; non-200 raises LLMResponseError; run_with_retries recovers from transient 500.
- B3 — Planner crash containment — git log --grep "(b3)" — G1–G14 green bare, 180 passed (+5 tests); generate_json called only in llm.py; 5 run_with_retries call sites in planner; select and props recover on attempt 2 after malformed attempt 0; truncated replies complete with fallback_level 2.
- B4 — Grounding scale words — git log --grep "(b4)" — G1–G14 green bare, 181 passed (+1 test); numbers("holding 2.3 million gallons") returns 2.3 and 2300000.0 without stray 1000000.0; spelled runs require small number or leading a/an.
- B5 — Timeline date labels — git log --grep "(b5)" — G1–G14 green bare; timeline_label_errors rejects non-distinct, non-grounded, unapproved relative phrases, and decreasing years; template writing rules updated; schema sync G8 green.
- B6 — Meaning rules + people-scene critic — git log --grep "(b6)" — G1–G14 green bare, 192 passed (+11 tests); stat_callout suffix currency errors rejected; location era_label ungrounded 'ago' rejected; critic runs blind on people scenes with 256 num_predict and temp 0; 1 props retry on mismatch, 0 further critic calls; regression set passes 4/4 on gemma4:26b; planner containment asserts 6 run_with_retries sites.
- B7 — LLM-facing schemas without length limits; text completeness; planner eval re-run — git log --grep "(b7)" — G1–G14 green bare, 203 passed (+11 tests); llm_facing_schema strips length and pattern constraints inside generate_json; retry messages prompt shorter complete phrases; normalize_text collapses whitespace; text_complete_errors catches truncation fragments and punctuation issues; cold planner eval passes all §9 bars (0 newlines, 0 completeness failures, 0 timeline errors, critic 4/4); byte-identity determinism holds.
- B8 — The contact sheet flags failed images — git log --grep "(b8)" — G1–G14 green bare, 204 passed (+1 test); flagged scenes includes overflow ∪ fallback_level 2 ∪ failed image entities; storyboard.md flags gain 'image failed'; report.json carries failed_images and warnings for text_check unavailable.
- B9 — Invoke mflux directly; drop the symlink — git log --grep "(b9)" — G1–G14 green bare; TOOL_NAME set to mflux-generate-flux2; cache_key and generate support seed parameter and actual seed is included in canonical cache key; doctor asserts mflux-generate-flux2 on PATH and --help contains flux2-klein-4b (exit 4 otherwise); setup.sh removes legacy symlink; design docs updated.
- B10 — Illustration text check with automatic retry — git log --grep "(b10)" — G1–G14 green bare, 211 passed (+7 unit tests); vision check with gemma4:26b evaluates illustrations not marked text_expected; text_expected handles whole words and phrases at word boundaries; retries on seed+1, seed+2; 3 texty failures mark entity failed and remove image; unavailable fallback preserves image as warning; fixtures/vision/ achieves 7/7 on seeds 7 and 8; naive prompt falsified at 5/7; run_with_retries count asserts 7 across planner/assets.
- B11 — Legible text over images; captions through FitText — git log --grep "(b11)" — G1–G14 green bare, 215 passed (+1 test); layout.ts exports IMAGE_SCRIM with stops at 640 (0), 800 (0.85), 1120 (0.92) and IMAGE_TEXT_MIN_TOP 807; ImageScrim used in location and set_piece; test_contrast asserts alpha >= 0.85 and ink/inkMuted >= 4.5:1 over white (9.15:1 and 5.57:1 measured; falsified at 0.53 with 1.95:1); captions render through FitText with CAPTION_SLOT; white.png and location__worst golden added; G10 gallery gate passes with 0 overflows.
- B12 — Map legibility; kinetic_quote attribution avatar — git log --grep "(b12)" — G1–G14 green bare, 217 passed (+2 tests); map colors mapSea #0B1326, mapLand #4466A0, mapRegion #7C9FDB, mapBorder #0B1326; test_contrast asserts map contrast rows (land/sea 3.22:1, region/land 2.15:1, stroke/land 3.22:1, stroke/region 6.90:1, fill/stroke 12.83:1, chip ink/bgDeep 16.83:1; falsified with mapLand #1F2F52); Natural Earth ne_50m_lakes downloaded, checksummed, and generated into renderer/public/geo/lakes-50m.json; lakes drawn above land in mapSea; doctor check 13 asserts lakes-50m.json; marker dot radius 14 with 4px bgDeep stroke and 14->48 pulse ring; computeChipPlacement places chips with 12px gap (above at y-26, below at y+26 when y < 120); vitest asserts marker dot and chip disjointness (falsified with -48); kinetic_quote renders parametric Avatar at 120px with name chip in cast color; G10 gallery passes with 0 overflows on all 52 goldens; story_recipe_box preview tile s013 verified with Lake Superior water separating Duluth and Thunder Bay.
- B13 — Gates fail closed; bundle hygiene — git log --grep "(b13)" — G1–G14 green bare, 217 passed; check_gallery.sh cleans output dirs first and fails closed if overflow.json is missing or unparseable (falsified with rm overflow.json -> exit 1); check_renderer_purity.sh drops only paths starting with renderer/src/clock/remotion/ (falsified with renderer/src/templates/remotion/x.tsx -> G9 exit 1); render.ts drops copy of fixtures into render_public (asserted not exists after render); test_smoke_sync_probe builds temporary job dir with fixtures/music/test_bed.wav at audio/narration.wav and verifies bundle hygiene and sync probe flips.
- B14 — Remove the dead SFX scheduler — git log --grep "(b14)" — G1–G14 green bare, 214 passed (-3 tests); timing/sfx.py, its exports from timing/__init__.py, and tests/test_timing_sfx.py deleted; grep asserts zero references in src and tests; test_compile.py SFX tests pass.
- B15 — README accuracy — git log --grep "(b15)" — G1–G14 green bare; README updated with Wave B in progress status, accurate audio mix specs (-16 LUFS, -18 dB / volume 0.126, 1s fade-in, 2s fade-out, no ducking), template-accurate SFX role mappings, font credits restricted to Poppins and Inter, Natural Earth lakes dataset credited, and automatic checks section added; banned terms grep returns 0 matches.
- B16 — E2E: computed counts, audible music — git log --grep "(b16)" — G1–G14 green bare, 218 passed (+4 tests); check-sync outputs JSON {"checked", "expected", "failures"} and asserts equality to len(scenes) - 1 with 0 failures (falsified by --skip-boundary 1 -> exit 1); voice lines read dynamically from voice.json across all fixtures; step 4 final MP4 audio RMS in [duration - 1.4s, duration - 1.0s] measured at -39.85 dBFS (> -60.0 dBFS required; falsified on music-less re-render at -91.16 dBFS -> exit 1); Remotion AudioLayer audio volume clamped to >= 0.001 to prevent unregistering render asset, and RemotionAudioCue passes loop and loopVolumeCurveBehavior="extend" to Audio; report lists critic counts and text_check statuses per fixture.
- B17 — Cold-cache performance budget; close-out — git log --grep "(b17)" — G1–G14 green bare; scripts/measure_budget.sh created and verified on story_recipe_box (~3 min story); cold new->awaiting_review 252.29 s (<= 390 s), render 197.01 s (<= 210 s), total 449.30 s (<= 600 s), warm preview 15.25 s (<= 60 s); verified 0 cache hits; critic 10 calls, text checks 4 calls, 5 images generated; docs/evals/budget_2026-09-26.md generated and committed; full battery G1–G14 exits 0 bare.


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

**September 26, 2026: verification of Wave B (designer).** All 17 items match their specs and every gate reproduces. Real-output review found the four problems above. Design contracts corrected, each measured before specifying:
- quoted speech is not split, and the colon loses its bonus (`design_audio_and_timing.md` §7);
- critic passage framing, a 3-attempt retry, tone repair, and regression case E (`design_planner.md` §11: five cases 5/5 on seeds 7–9 with the new framing; the old framing answered the narrator on the real case three times out of three);
- the internal-id rule (§6 item 8);
- the caption word-spacing contract plus a measured gap check (`design_visual_direction.md` §8: broken page 4 px, correct pages 12–17 px);
- generated country codes;
- a missing input fails loudly;
- the text-audit bar clarified.

Wave C (C1–C7) specced. Issue 6 filed for the user.

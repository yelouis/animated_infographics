# Engineering Issues & Decisions — Working Log

**What this file is:** the live queue of open issues, the decisions the user has made or still has to make, the deferred features and their triggers, and a one-line index of resolved work. The execution guide (`docs/agent_execution_guide.md`) is the build spec; this file is where findings and choices live.

**Filing format** is in `.agents/skills/bug_documentation_guidelines/SKILL.md`. Open issues end with a `Your selection: _____` line. **That line belongs to the user, and an agent must never fill it in.**

---

## 1. Open & in-flight

**Wave B (B1–B17) was delivered as 17 commits (`cad065d`…`beb4c4f`) and independently verified on September 26, 2026.** Every gate G1–G14 was re-run bare in a separate session (numbers in `agent_execution_guide.md` §1), and the cold budget was re-measured. Each item's source was read against its spec: **all 17 do what their specs say** (per-item verdicts in §3).

**Waves C (C1–C8) and D (D1–D5) were delivered as 13 commits (`12209d2`…`98db684`) and independently verified on October 3, 2026.**
- Every gate G1–G14 was re-run bare in a separate session: 254 fast tests, the slow suite, the E2E (913 s), the offline gate and the cold budget (199.2 s / 191.6 s / 390.8 s, 0 cache hits). All green; numbers in `agent_execution_guide.md` §1.
- Each item's source was read against its spec: **all 13 do what their specs say** (verdicts in §3).
- The Wave D bars hold on real renders: every job ≤ 1.0 graphic word/s (0.49–0.81) with ≥ 1/3 light scenes.

**The verification also read the rendered stories as a viewer, and found problems no gate covers.** Four come from gaps in my own Wave C/D specs, one is long-standing, and one is implementation hygiene. They are specced as **Wave E (E1–E6)** in `agent_execution_guide.md`. Each fix stays within behaviour the user already approved (Issue 5 → A, Issue 7 → A):
- **The critic's findings do not stick.**
  - 35 of 87 flagged tones survived a retry that "succeeded" by keeping them. Rose's farewell note was drawn as **sarcastic** dialogue, and a retry introduced "Rose?" said **angry**.
  - An emotion read as "unknown" never counted, so "Meredith was impressed" stayed **angry**.
  - 7 of 8 disputed quote speakers were kept; for example, a narration line was credited to The Soldiers. (E1)
- **The rhythm rule replaced the story's climax.** Rose's quoted note became a neutral face. (E2)
- **A year rendered as a count:** "She had died in 2016" became **"2,016"**. (E3)
- **Icons:** the props prompt never listed the allowed names, so the model's guesses were snapped to "Armchair" (18% of all icons): "Machine Guns", "Trampled crops" and "Farmers" all showed an armchair. Listing the names removed it, 8/54 → 0/56. (E4)
- **Hygiene:** D1 slipped an import-time `HF_HOME` override into the package, which hides the misconfiguration `doctor` exists to report; there are also two stale comments. (E5)

**No question is open for the user.**

## ⚠️ Unresolved Issues & Suggestions

No open issues.

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


#### 2.9 A list whose length the model chooses can silently shrink

With a JSON array for "one sender per message", `gemma4:26b` merged consecutive identical answers: 2–3 "them" messages came back as one element on every seed. The length check made each reply a failed attempt, so the scene ended `unavailable`, unchecked, and **3 of 8** real text threads would have lost their critic. **When the count is known in advance, ask for one required key per item**, and measure answer completeness on real cases whenever a prompt changes. Contract: `design_planner.md` §11.


#### 2.10 A retry the model may decline is not a repair

The critic-triggered retry tells the model "fix the props if that reading fits better; otherwise keep yours". It kept the flagged tone in 35 of 87 cases and the disputed quote speaker in 7 of 8. Each of those retries counted as a success, so the deterministic fallback, which ran only when every attempt *failed*, never fired. **When a rule decides what is acceptable, enforce the rule on the final result, not on the path that produced it.** Contract: `design_planner.md` §11 ("Enforcement after the round").

#### 2.11 A choice list the model never sees becomes a default

The props schema's `enum` held 157 icon names, but the prompt listed none. The model guessed, and constrained decoding snapped each unknown guess to an early allowed name: "Armchair" was 9–18% of all icons in every wave and was never noticed, because the icon was valid. **Show the model the names it must choose from, and measure the distribution of what it picks, not just its validity.** Contract: `design_planner.md` §5.

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
- **Issue 6 — Dialogue and text messages the story never contains** — decided September 27, 2026 in chat, after watching the `story_recipe_box` and `story_room_12` renders: *"I think the paraphrasing is fine."* Recorded as **Option D (keep as is)**: `dialogue` and `text_thread` lines may paraphrase or dramatise in every genre; no verbatim or word-overlap check; the reviewer judges at the gate. Nothing to build. *Who* speaks is still checked by the critic (and, from C8, who the contact is). The permanent home is `design_planner.md` §5.
- **Issue 7 — Too many words on screen in story videos** — selected September 27, 2026: *"Proceed with Option A."* Picture-first stories: no restating text, word caps, a reaction-shot rhythm; karaoke captions stay. To be delivered by **Wave D (D1–D5)**. The measurements behind the option (≈ 4.5 words/s on screen against 2.6 spoken; 6 of 12 sampled Casually Explained frames wordless) and the measured design (`design_templates.md` §5.5: caps met on 93/94 real scenes; 0.52–0.89 graphic words/s and 39–56% light scenes after R6/R7) live in the design docs. The permanent homes are `design_templates.md` §5 and `design_planner.md` §4–§6 and §9.

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

**Waves C and D — delivered; independently verified October 3, 2026.** Verdicts: C1 ✓ (quote tracking resets per sentence, so a quotation spanning two sentences can still be split between them; the spec allowed it, and it is recorded as a known limitation) · C2 ✓ (the critic prompt drops the `Cast:` label; accepted equivalent, regression 8/8) · C8 ✓ · C3 ✓ to spec, but the spec had a gap → E1 · C4 ✓ · C5 ✓ · C6 ✓ · C7 ✓ · D1 ✓ (plus an out-of-scope `HF_HOME` override in `__init__.py` → E5) · D2 ✓ · D3 ✓ to spec, but the spec had a gap → E2; R6's alternates exposed a year-as-stat → E3 · D4 ✓ · D5 ✓.

**Wave C:**

- C1 — Quoted speech stays whole when splitting beats — git log --grep "(c1)" — G1–G14 green bare, 221 passed (+3 tests); colon removed from PUNCT_SUFFIXES; QUOTED_SENTENCE_MAX_MS = 16000; quote spans and opening quotes preserved in split pass; tests/data/quote_sentence.json yields 1 beat instead of 2 (falsified on colon bonus and quote exclusion removal); 17,000ms synthetic sentence splits without breaking opening quote; beat counts: molasses_flood 10, emu_war 25, story_recipe_box 32->29, story_room_12 33->34.
- C2 — Critic passage framing, keyed text-thread answers, regression cases E + H — git log --grep "(c2)" — G1–G14 green bare, 224 passed (+3 tests), 24 slow passed (+2 tests); critic prompt updated to passage framing with verbatim header 'Passage (read all of it; who speaks is often named in the sentence before a quote):\n' and 4 beats joined by spaces, removing all 'context only' text; text_thread answers use keyed message_1..n schema and are normalized to messages array in validate_critic_answer; regression cases E and H added to slow tests and planner eval; cases A, B, B', C, E, H pass on seeds 7, 8, 9 (18/18); falsified on old framing (Case E returns narrator c1 -> agree) and missing keys (failed attempt).
- C8 — Text-thread contact identity — git log --grep "(c8)" — G1–G14 green bare, 226 passed (+2 tests), 24 slow passed (8/8 cases on seeds 7, 8, 9 = 24/24); resolve_contact matches contact_cast_id or unique non-narrator casefolded name; contact question appended to text_thread prompt; contact enum with non-narrator IDs + "unknown" appended as required last property; validate_critic_answer validates and normalizes contact; critic_mismatches checks contact against resolved contact and emits mismatch 'contact: <name> vs <name> (<cid>)'; contact fill populates props_instance.contact_cast_id before validate_scene and in final scene construction; regression cases F and G added; falsified by deleting contact comparison (Case F goes red).
- C3 — Critic retry robustness — git log --grep "(c3)" — G1–G14 green bare, 231 passed (+5 tests); critic-triggered props retry upgraded to 3 attempts with run_with_retries; honest changed bool based on props dict comparison; deterministic tone repair sets line tone to neutral when all mismatches are dialogue tone vs unknown; CriticReport gains repair and retry_errors fields; rule R3 repair path calls _evaluate_scene_critic on replacement scene when needs_critic is true; evals/planner.py reports agree, changed, tone_neutral repairs, and unchanged-after-mismatch; falsified by reverting max_attempts to 1 (test_critic_retry_recovers_on_attempt_2_or_3 goes red).
- C4 — No internal ids on screen — git log --grep "(c4)" — G1–G14 green bare, 234 passed (+3 tests); internal_id_errors checks free-text fields against bible cast, places, and set_pieces; exact error format 'props.<field>: contains the internal id "<id>" — use the name ("<name>")'; validate_scene wires internal_id_errors into all free-text fields; props.md gains verbatim sentence 'Refer to people, places and objects by their names; never write ids like c1, p2 or v1.'; evals/text_audit.py tracks id_leaks_count and id_leaks with bible integration; falsified by disabling check (tests fail red).
- C5 — Caption word spacing — git log --grep "(c5)" — G1–G14 green bare, 236 passed (+2 tests); each caption word renders as inline-grid with hidden 1.12em sizer and visible word at 1em or 1.12em active; marginRight: 0.3em separates adjacent word boxes; transform: scale removed; gallery fixture and golden captions__long_active added (53 goldens); test_caption_spacing.py checks runs >= 16px in caption band; check_gallery.sh runs spacing test; story_recipe_box preview verified across 27 multi-word caption scenes with min word gap 13px at half scale (26–62px full scale; 16px on s020 vs 4px in Wave B); falsified by restoring scale transform (test fails with widest run 8px <= 16px).
- C6 — Hygiene: generated country codes; a missing input fails loudly — git log --grep "(c6)" — G1–G14 green bare, 237 passed (+1 test); gen-country-bboxes.ts generates renderer/src/generated/countryCodes.ts with DO-NOT-EDIT header and sorted numeric keys; renderer/src/components/countryCodes.ts deleted; MapView.tsx updated to import from generated; check_schema_sync.sh covers countryCodes.ts (13 files checked, G8 green; falsified by hand-editing an entry -> G8 red); compile.py raises ValidationFailed when ingest.music or ingest.sfx_dir is recorded but missing from the job; unit test test_compile_missing_music_fails_loudly validates exit-2 error naming the missing path (red first: previously silently dropped).
- C7 — Re-measure; close-out of Wave C — git log --grep "(c7)" — G1–G14 green bare, 237 passed; cold planner eval passes all §9 bars (8/8 critic regression, 0 id leaks, 0 newlines); re-run E2E passes with Walter Lindqvist quote attributed to Danny (c3) in text_thread containing 'texted me a photo:' and 0 unavailable text-thread critics; cold budget 411.10 s (≤ 600 s) with 0 cache hits.

**Wave D:**

- D1 — Word-budget contracts: removed fields, list maxima, neutral, WORD_CAPS, words module, renderer, gallery — git log --grep "(d1)" — G1–G14 green bare, 242 passed (+5 tests); removed 6 fields restating narration across contracts, validate, audit, and templates; list maxima updated for 6 templates; neutral emotion added to EmotionBeat; WORD_CAPS contract and template classes added; count_words, field_values, and graphic_words implemented in planner/words.py; gallery fixtures and goldens updated with 0 overflows.
- D2 — Planner word budget: validator item 9, writing rules, props.md, 12-word fallback, text audit, critic neutral — git log --grep "(d2)" — G1–G14 green bare, 246 passed (+4 tests), 29 slow passed (+5 tests); validator item 9 word_cap_errors enforces WORD_CAPS limits with rewrite prompt; too_long list error formatted per D2; registry writing_rules updated verbatim across 15 templates; prompts/props.md guidelines 3 & 4 updated and prompts/select.md icon_list rule updated; deterministic kinetic_quote capped at 12 words with ellipsis; critic emotion_beat supports neutral first; text audit tracks and enforces word_cap_violations_count == 0; 9 frozen cases in word_cap_cases.json verified and falsified (timeline events[].label to 99 -> red); 5 real beats in tests/slow/test_word_caps_live.py pass within 3 attempts on gemma4:26b with character_intro descriptor omitting cast member name.
- D3 — Selection rules R6 and R7; deterministic pictures — git log --grep "(d3)" — G1–G14 green bare, 251 passed (+5 tests); timeline <= 1 and comparison <= 1 enforced in selection rule R6 and validate_plan; reaction-shot rhythm rule R7 (run >= 2 non-picture scenes in replaceable templates triggers deterministic rhythm target: narrator emotion_beat, named non-narrator cast member, named set_piece, or named location); kept templates and picture templates never replaced; quoted text excluded from first-person narrator match; Choice gains rhythm_id; props plan_storyboard builds deterministic neutral emotion_beat, set_piece, or location with 0 LLM calls; needs_critic bypasses deterministic rhythm picture scenes; recipe_choices.json exact repairs and choices verified; rhythm_cases.json 7/7 verified and falsified (dropping QUOTED stripping picks c1 -> red; dropping kept-class check replaces R7-e/R7-f -> red).
- D4 — Word-density measurement: eval bar, evals/word_density.py, E2E step 9 — git log --grep "(d4)" — G1–G14 green bare, 254 passed (+3 tests); evals/planner.py computes graphic_words_total, graphic_words_per_narration_word, light_share (scenes after title card with graphic words <= 2 / m), and R6/R7 repairs; light_share >= 1/3 bar enforced in fixture_pass; planner report includes metrics and Wave B baselines; evals/word_density.py CLI loads timeline.json, calculates graphic words/s and light share, exits 1 if per_second > 1.0 or light < m/3; scripts/e2e.sh step 9 checks rendered jobs and logs word density lines to e2e report; unit tests on synthetic timeline pass; falsified by dividing duration_frames by 3 (exit 1 -> red) and light_share bar to 0.9 (eval fails -> red).
- D5 — Re-measure; close-out of Wave D — git log --grep "(d5)" — G1–G14 green bare, 254 passed; cold planner eval passes all §9 bars (8/8 critic regression, 0 word-cap violations, 0 newlines, 0 completeness failures, 0 ID leaks, light share 33.3%–57.1% >= 1/3); G12 E2E step 9 passes with all rendered jobs <= 1.0 graphic word/s and >= 1/3 light share; cold budget 390.16 s (<= 600 s) with 0 cache hits; story_recipe_box stills verified (neutral reaction shot, name-only set piece, 3-event timeline, 3-message text thread, 8-word quote); README updated to Waves A–D delivered; agent execution guide rewritten to Queue Complete.

**Wave E:**

- E1 — Critic findings stick: enforcement after the round, the emotion rule, disputed quote speakers removed — git log --grep "(e1)" — G1–G14 green bare, 255 passed (+1 test), live slow tests pass (6/6 emotion mismatch on seeds 7, 8, 9; critic regression 8/8); critic_mismatches treats unknown emotion against non-neutral as mismatch; enforce_reading repairs unconfirmed dialogue tones to neutral ("tone_neutral"), unconfirmed emotions to neutral ("emotion_neutral"), and disputed kinetic_quote attributions to null ("attribution_dropped"); _evaluate_scene_critic applies enforce_reading to standing scene post-round; CriticReport.repair schema updated; evals/planner.py reports all three repair types; all 7 frozen cases verified; falsified by skipping enforce_reading on successful retry (Rose note sarcastic -> red) and reverting emotion rule (angry vs unknown -> agree -> red).
- E2 — R7 never replaces quoted speech — git log --grep "(e2)" — G1–G14 green bare, 255 passed; R7 condition in planner/select.py updated with not QUOTED.search(beat_text); frozen data updated (rhythm_cases.json R7-b expected null, R7-h added; recipe_choices.json s016 repair removed); test_rhythm_cases asserts 8 cases; falsified by removing QUOTED condition (R7-b, R7-h, and recipe choices exact go red bare).
- E3 — A year is not a stat — git log --grep "(e3)" — G1–G14 green bare, 256 passed (+1 test); stat_callout validator rejects integer values 1000..2100 appearing in beat text without comma/formatting as years; real room 12 2016 scene fails with exact error (red first); falsified by deleting rule (2016 passes -> red) and widening range 0..9999 (312 cards fails -> red).
- E4 — The props prompt lists the allowed icon names — git log --grep "(e4)" — G1–G14 green bare, 257 passed (+1 test), live slow tests pass (2/2 emu_war scenes contain 0 Armchair); props user prompt appends icon allow-list block for stat_callout, icon_list, cause_effect, and comparison; unit tests in tests/test_props_prompt.py assert block presence/absence (red first); falsified by removing block (slow test on emu_war scenes reproduces Armchair in both icon_list and cause_effect -> red).
- E5 — Hygiene: no import-time environment change; stale comments — git log --grep "(e5)" — G1–G14 green bare, 257 passed; deleted HF_HOME override from __init__.py; doctor check 7 Kokoro missing message gains explicit hint (if HF_HOME is set, it must contain hub/models--hexgrad--Kokoro-82M; unset it or export HF_HOME="$HOME/.cache/huggingface"); design_testing_and_validation.md §3 documents battery.sh export; location.tsx and set_piece.tsx comments updated for D1 caption removal; red first verified on mktemp HF_HOME printed vs temporary dir, and doctor exits 4 with hint.


---

## 4. Deferred features (do not start without a selection)

| Id | Feature | Trigger to start | Notes |
|---|---|---|---|
| DF1 | Video input + PiP of the original speaker | User selects it | The 9:16 PiP placement is an open design question (`design_future_live_and_video.md` §2) |
| DF2 | 16:9 output | User selects it | Roughly doubles template work |
| DF3 | Multi-voice narration (character voices) | User selects it | Needs a dialogue-attribution step (see Issue 5 for how often attribution is wrong today). `voice.json` already records `male` separately from `unknown`. |
| DF4 | **Live mode** (speak in real time, webcam in a corner) | Wave B complete **and** the user answers the three questions in `design_future_live_and_video.md` §4 | The end goal |
| DF5 | Reddit URL fetching | User selects it | Terms-of-service review first |
| DF6 | Public-domain photo sourcing (e.g. Wikimedia) | User selects it | Requires runtime network, which conflicts with the local-only policy as written |
| DF7 | Historical map borders | User selects it | The MVP uses modern borders |
| DF8 | Web editor for the review gate | User selects it | The MVP gate is JSON edit + contact sheet |
| DF9 | Cloud LLM planner backend | Only if the local planner fails its eval bars on both candidate models **and** the user accepts a paid API | Reverses a user decision; needs explicit selection |

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

**September 27, 2026: selections and direction (user, in chat).**
- Issue 6: *"I think the paraphrasing is fine."* Recorded as Option D.
- Live presentations: *"For real-time presentations, it makes sense to show timelines and repeated graphics to drive home the point."* Recorded in `design_future_live_and_video.md` §4.
- Stories: *"For these stories, is there a way to show less words in general. Watch the youtube videos of casually explained for inspiration."* Filed as Issue 7.

**September 27, 2026: consequences (designer, measured before specifying):**
- Casually Explained studied frame by frame, and word density measured on the six Wave B E2E renders (Issue 7).
- The text-thread critic now answers one key per message (C2 amended: the array schema left 3 of 8 real threads unchecked) and names the contact (C8: Deb caught on `story_room_12` s018 on 3 of 3 seeds, no false contact reading on 8 threads × 3 seeds).
- Regression cases F, G and H were frozen from real output in `tests/data/critic_text_thread_cases.json`; the critic bar is now 8/8.
- Contracts updated: `design_planner.md` §5, §9 and §11; `design_templates.md` §2.10; `design_testing_and_validation.md` §2; `design_future_live_and_video.md` §4.

**September 27, 2026: selection (user).** Issue 7 → *"Proceed with Option A."*

**September 27, 2026: consequences (designer, measured before specifying, `gemma4:26b`, the Wave B E2E storyboards):**
- **Caps met.** The props stage with the proposed caps passed on 93 of 94 real scenes within the normal 3 attempts, with fewer attempts than Wave B (118 vs 147). The one failure is a 13-word verbatim quote, which the ladder moves to its alternate.
- **Both selection rules are needed.** Caps alone left `story_recipe_box` at 1.13 words/s and 31% light scenes. With R6 (one timeline and one comparison per video) and R7 (rhythm), the four fixtures measure 0.52–0.89 words/s and 39–56%.
- **R7 pictures are deterministic.** A neutral reaction shot, or a named set piece or place: the model invented feelings for plain beats, and the critic's readings were unstable.
- **R7 never replaces kept templates.** Unrestricted, it replaced Meredith's introduction and Deb's reply.
- **Quoted speech never counts as the narrator.** Walt's "I've been waiting…" would otherwise have picked the narrator.
- **The words-per-second bar lives in the E2E.** The planner eval simulates timing at 4 words/s, so it carries the light-share bar only.
- **Relabelled:** the deferred features D1–D9 became **DF1–DF9**, so that Wave D's item ids are unambiguous. `design_future_live_and_video.md` already used F1–F6 for its constraints.
- **New frozen real data:** `tests/data/word_cap_cases.json`, `rhythm_cases.json`, `recipe_choices.json` and `word_caps_live_cases.json`.
- **Contracts updated:**
  - `design_templates.md` §1, §2, §3 and §5 (new);
  - `design_planner.md` §4 (R6, R7), §5, §6 item 9, §9 and §11;
  - `design_testing_and_validation.md` §2 and §4 (step 9);
  - `design_data_contracts.md` §5 and §6.

**October 3, 2026: verification of Waves C and D (designer).**
- Every gate G1–G14 and the cold budget reproduce bare, and all 13 items match their specs.
- **Real-output review found:**
  - the critic's findings do not stick after a retry (35/87 tones, 7/8 quote speakers);
  - unknown emotions never count;
  - R7 replaced quoted speech;
  - a year rendered as "2,016";
  - "Armchair" as the default icon (the prompt never listed the names);
  - an import-time `HF_HOME` override.
- **Each was measured before specifying.**
  - The emotion rule was checked on 13 real beats (4 unsupported feelings read "unknown", none supported).
  - The icon list was checked on 27 real scenes (Armchair 8/54 → 0/56).
  - The critic's readings on the frozen cases were identical across seeds 7–9.
  - A reference implementation reproduced the committed R7 expectations exactly before computing the new ones.
- **Contracts updated:**
  - `design_planner.md` §4 (R7 never replaces quoted speech), §5 (the icon block), §6 item 6 (a year is not a stat) and §11 (the emotion rule; enforcement after the round);
  - `design_templates.md` §5.4;
  - `design_data_contracts.md` §6;
  - `design_testing_and_validation.md` §2.
- **New frozen data:** `tests/data/critic_enforcement_cases.json` and `tests/data/wave_e_expectations.json`.
- Wave E (E1–E6) specced. **No question for the user.**


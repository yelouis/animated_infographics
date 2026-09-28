# Agent Execution Guide — Active Build: Wave C (verification fixes, 8 items) then Wave D (picture-first stories, 5 items) — September 27, 2026

**You are an engineering agent with no memory of this project.** The offline MVP (Wave A, A1–A22) and the verification-fix wave (Wave B, B1–B17) are built, committed and pushed (head `beb4c4f`). On September 26, 2026 an independent pass re-ran every gate, read every Wave B item against its spec, **and inspected real output**. All 14 gates reproduce green, and all 17 Wave B items do what their specs say. But real output showed problems the specs had not anticipated:
- **The people-scene critic (Issue 5) misses the error it was chosen to catch.** In a real `story_recipe_box` run it *agreed* that Danny's text "Who is Walter Lindqvist…" was the narrator's. The beat splitter had cut the quote away from "…he texted me a photo:", and the critic treated that neighbouring beat as "context only".
- **30 of 149 critic disagreements kept the known-wrong scene**, because the retry had one attempt.
- **Internal ids appear on screen** ("One card missing from the recipe box (v1).").
- **Highlighted caption words collide with their neighbours** ("theengagementfell").
- **A text thread shows the wrong contact** (added September 27, 2026). Deb's reply "Keep the room. He's never missed one." appears under "Sofia", and the critic cannot see it because it asks only "me or them" per message. While measuring this, the passage framing for C2 turned out to make the model **collapse consecutive same-sender messages into one answer**: 3 of 8 real threads would end unchecked. C2 now asks for one answer per message; C8 adds the contact.

Wave C fixes these. Issue 6 was decided on September 27, 2026: paraphrased dialogue is fine, so there is nothing to build.

**Then Wave D: picture-first stories (Issue 7 → Option A, selected by the user: *"Proceed with Option A."*).**
- **The problem:** the story videos put ≈ 4.5 words/s on screen (every narration word as a caption, plus 1.1–1.9 graphic words/s), while the narrator speaks 2.6 words/s. Half the scenes carried ≥ 10 words. The user's reference, Casually Explained, shows no words in half its frames.
- **Wave D does three things, and keeps karaoke captions:**
  - removes the text fields that restated the narration;
  - caps every remaining field in words;
  - adds two selection rules: at most one timeline and one comparison per video (R6), and a reaction-shot rhythm (R7).
- **Measured on the real Wave B storyboards before specifying:** the model met the caps on 93 of 94 scenes, and graphic words fell to 0.52–0.89 per second, with 39–56% of scenes nearly wordless (§1.4).

**What is approved:** Wave C, items **C1–C8**, then Wave D, items **D1–D5**, all in §3, in the order of §2 (C8 runs third, straight after C2). **Nothing else.** **What NOT to touch:** everything in §5. **What must not be started:** everything in §4.

**Every number and literal string in this document and in the design docs is a decision, not a suggestion.** Implement as written; that includes prompts, header lines, thresholds, seeds and error strings. If a value is genuinely impossible, keep the *intent*, deviate minimally, say so in the commit body, and add it to §5.2. If the design itself cannot work, **STOP and file it in `docs/ongoing_general_errors.md` with options and a `Your selection: _____` line. Do not improvise, and never fill in a selection line yourself.**

**What the product is, in one paragraph.** A local-only CLI that turns a **text story** (narrated by local TTS in an automatically chosen voice) or an **audio narration** into a **1080×1920 animated explainer video**. It uses flat editorial vector scenes chosen from 16 templates, in sync with the voice, with word-by-word karaoke captions, a persistent cast of vector avatars, locally generated illustrations checked for stray lettering, a blind critic for people scenes, and optional music and SFX. Every video **stops for human review** before the final render. The long-term goal is live mode, so the renderer is clock-agnostic.

**The lesson that shaped this wave.** A check that passes on tidy test inputs can still fail on production inputs. **Every item's validation includes a case taken from real pipeline output**, frozen in the repository, and you run it against the unfixed code first and see it fail.

---

## 0. Standing constraints (apply to every item)

1. **The battery is the regression bar.** After every item, run `scripts/battery.sh` (full) and update §1.3. **Read every exit code bare.**
2. **Fully local at runtime.** No cloud API, no network except loopback. Pull no new models.
3. **Python (Pydantic) is the source of truth for every contract.** Generated files are never hand-edited. From C6 this includes `renderer/src/generated/countryCodes.ts`.
4. **Templates read time only through the clock.**
5. **The review gate is mandatory.** No auto-approve under any name.
6. **The planner never crashes the pipeline and never shows an ungrounded, truncated or id-bearing text. Every LLM call goes through `run_with_retries`.**
7. **Red first, on real inputs.** Before fixing, run the item's falsifying check against the *current* code using the frozen real case, and record the failure.
8. **One item = one Conventional Commit, scope = item id** (`fix(c1): …`). WHY plus red and green runs in the body. **Push after every item.** **Never amend a pushed commit.**
9. **Record the resolution in the same commit:** one line under "Wave C" or "Wave D" in `ongoing_general_errors.md` §3, in the form `C<n> — <title> — git log --grep "(c<n>)" — <measured result>` (or `D<n>` / `(d<n>)`), never a hash.
10. **When this guide and a design doc disagree, stop and file it.**
11. Every stage log ends in `llm_calls=<n> cache_hits=<m> elapsed_ms=<t>`; the call counter is incremented at the backend's entry point.

---

## 1. Verified baseline (September 26, 2026, independent verification session)

### 1.1 Environment

Unchanged from Wave B and re-verified by `doctor` (22 checks OK):
- M4 Max 64 GB; ffmpeg 8.1; Node v26.5.0; Python 3.12 (uv).
- Ollama 0.33.0 with `gemma4:26b`; Kokoro 0.9.4; mlx-whisper 0.4.3.
- mflux 0.20.0 via `mflux-generate-flux2 --model flux2-klein-4b` (4B weights only); Remotion 4.0.528.

### 1.2 Repository

- Wave A `4df212a`…`e374a15`; Wave B `cad065d`…`beb4c4f` (17 commits scoped `(b1)`…`(b17)`).
- Design contracts revised September 26, 2026 for Wave C (list in `ongoing_general_errors.md` §5).
- New frozen test data:
  - `tests/data/quote_sentence.json`: the real 9,625 ms quoted sentence and its word timings;
  - `tests/data/critic_text_thread_cases.json` (September 27): real `text_thread` scenes F, G and H, each with cast, the four passage beats, props and expected result;
  - `tests/data/word_cap_cases.json` (September 27, Wave D): 9 real Wave B props objects, one per template that breaks a cap, with the exact expected error strings (40 of the Wave B scenes break at least one cap);
  - `tests/data/rhythm_cases.json` (September 27, Wave D): seven real beats R7-a…g with their entities and the expected R7 target;
  - `tests/data/recipe_choices.json` (September 27, Wave D): the real `story_recipe_box` choices (3 timelines, 2 comparisons), beats and entities, with the exact expected output of the new rule pass;
  - `tests/data/word_caps_live_cases.json` (September 27, Wave D): five real beats (bible, sentence texts, neighbouring beats, Wave B props, probe props) for D2's slow test.

### 1.3 Gates (run bare in the verification session)

| # | Gate | Result |
|---|---|---|
| G1 | `uv run ruff check .` | exit 0 |
| G2 | `uv run ruff format --check .` | exit 0 · 107 files |
| G3 | `uv run mypy src` | exit 0 · 55 source files |
| G4 | `uv run pytest -q -m "not slow"` | exit 0 · **234 passed** |
| G5 | `npm --prefix renderer run typecheck` | exit 0 |
| G6 | `npm --prefix renderer run lint` | exit 0 |
| G7 | `npm --prefix renderer test` | exit 0 · **16 passed** (5 files) |
| G8 | `./scripts/check_schema_sync.sh` | exit 0 |
| G9 | `./scripts/check_renderer_purity.sh` | exit 0 |
| G10 | `./scripts/check_gallery.sh` | exit 0 · 53 goldens, fails closed, caption spacing verified |
| G11 | `uv run pytest -q -m slow` | exit 0 · **24 passed** · 172 s |
| G12 | `./scripts/e2e.sh` | exit 0 · 857 s · steps 1–8 pass; sync probe 9/9, 0 failures; music audible at **−39.85 dBFS** (bar > −60). **But** its `story_recipe_box` job again credits the Walter Lindqvist quote to the narrator, with the critic reporting "agree" (→ C1, C2) |
| G13 | `./scripts/check_offline.sh` | exit 0 · 224 s · self-checks pass (external network denied, loopback allowed); fresh-cache pipeline rendered |
| G14 | `uv run infographics doctor` | exit 0 · 22 checks OK |
| Budget | `./scripts/measure_budget.sh` (cold, `story_recipe_box`) | exit 0 · cold, **0 cache hits** · `new`→review **241.2 s** (≤ 390) · render **198.1 s** (≤ 210, only 12 s of headroom) · total **439.3 s** (≤ 600) · 70 LLM calls, 10 critic calls, 4 text checks, 5 images |

### 1.4 Measurements that shaped Waves C and D (September 26–27, 2026, `gemma4:26b`)

| What | Result |
|---|---|
| Critic on the real split beat (quote alone; the tag in the previous beat, labelled "context only") | answered **the narrator** on seeds 7, 8 and 9: a wrong **agree** |
| Same case with the **passage framing** (`design_planner.md` §11) | answered **Danny** on 7, 8, 9 |
| Same case with the tag kept in the beat (the C1 split rule) | answered **Danny** on 7, 8, 9 |
| Original regression cases A, B, B′, C with the passage framing | **4/4 on every seed** (no regression) |
| Critic outcomes across Wave B's runs | 261 agree · 119 "changed" · **30 retried but unchanged** (known-wrong original kept) |
| Internal ids in free text, Wave B E2E storyboards | **4** in 311 unique scenes |
| Caption gap metric on half-scale stills | broken "theengagementfell": widest empty run **4 px**; correctly spaced pages **12–17 px**; a second collapsed page found ("312 handwritten cards,") |
| **(Sept 27)** `text_thread` critic with passage framing and the **array** schema, 8 real threads × seeds 7–9 | **3 of 8** threads (room12 s018, recipe s011, recipe run 2 s012; all with consecutive "them" messages) returned **1 element** on every seed: a failed attempt each time → `unavailable` |
| **(Sept 27)** Same, with **keyed** answers (`message_1…message_n`) | **24/24** complete; the senders match the array answers wherever those were complete |
| **(Sept 27)** `dialogue` critic, array schema, passage framing, 13 real scenes × 3 seeds | **39/39** complete: dialogue keeps its array |
| **(Sept 27, Wave D)** Props stage with the D2 caps, writing rules and `props.md`, **94 real scenes** (every non-title scene of the four text fixtures' Wave B storyboards), normal 3-attempt retries | **93 pass** (73 on attempt 1). **118 attempts**, versus 147 for the same scenes in Wave B. Retry causes: word caps 13, list maxima 7. The one failure: the 13-word Walter quote as `kinetic_quote` (no ≤ 12-word verbatim span exists), so the ladder moves it to its alternate |
| **(Sept 27, Wave D)** Graphic words/s and scenes with ≤ 2 graphic words: Wave B → the probe's real outputs + R6 + R7 | `molasses_flood` 1.11 → **0.52**, 1/10 → **50%** · `emu_war` 1.51 → **0.63**, 3/25 → **56%** · `story_recipe_box` 1.91 → **0.89**, 3/32 → **44%** · `story_room_12` 1.76 → **0.86**, 1/33 → **39%** |
| **(Sept 27, Wave D)** The same without R6/R7 | `story_recipe_box` **1.13/s and 31%**: fails both bars. Both rules are needed |
| **(Sept 27, Wave D)** `character_intro` descriptor rule without / with "not their name", 6 real intros | without: one retry produced "Major Meredith", repeating the name the template already draws, and Sofia's became "Mr. Alvarez's daughter, Sofia". With: **6/6 pass**, "The military leader", "Mr. Alvarez's daughter" |
| **(Sept 27, Wave D)** LLM-written reaction shots (R7 beats, `neutral` offered) | The props model invented feelings for plain beats: "smug" for "…I think I got the better deal.", "confused" for "I asked if he minded me using it.", "angry" for "Meredith was impressed by his opponent." The critic's readings differed from the props on 6 of 9 beats; a neutral-leaning question answered `neutral` 27/27. → R7 pictures are **deterministic**, with a `neutral` face |
| **(Sept 27, Wave D)** R7 replacing any worded scene | It turned Major Meredith's `character_intro` into a reaction shot and Deb's reply (a `text_thread`) into a picture of Room 12 → the **kept** class (`design_templates.md` §5.4) |
| **(Sept 27)** Contact question (§11 wording), keyed, 8 threads × 3 seeds | s018 "Sofia" → **`c3` Deb** 3/3 (the real error); "Wife" and "Unknown Number" → `unknown`; Deb/Danny threads → `c3` (agree); **0 false contact readings**. The earlier wording without "according to the passage … does not say" answered Danny for an invented Walt thread (a false alarm) |

---

## 2. Execution order

| # | Item | Why this position |
|---|---|---|
| C1 | Quoted speech stays whole when splitting beats | It changes beats, which changes every downstream planner input. It must land before the critic items are measured. |
| C2 | Critic passage framing, keyed text-thread answers, regression cases E + H | The critic's input format; needs C1's beats for its real-output check. The keyed answer must land with the framing, because the framing is what triggers the collapse. |
| C8 | Text-thread contact identity (critic `contact`, contact resolution, avatar fill, cases F + G) | Extends C2's text-thread request; it must precede C3, whose retry path formats its mismatches, and C7's eval. |
| C3 | Critic retry robustness (3 attempts, tone repair, recorded errors, R3 path, honest `changed`) | Builds on C2's critic; its effect is measured in C7's eval. |
| C4 | No internal ids on screen | A validator + prompt change; must precede C7's eval. |
| C5 | Caption word spacing | Renderer-only; changes goldens. Independent of C1–C4. |
| C6 | Hygiene: generated country codes; a missing input fails loudly | Small; before the final measurement. |
| C7 | Re-measure: planner eval, E2E, cold budget; close-out of Wave C | Measures the finished Wave C (C1–C6 and C8) before Wave D changes the planner again, so each wave's effect is attributable. |
| D1 | Word-budget contracts: removed fields, list maxima, `neutral`, `WORD_CAPS`, `planner/words.py`, renderer, gallery | Every other D item builds on these shapes and on `count_words`; the Python and TypeScript shapes must change in one commit to keep G5 and G8 green. |
| D2 | Planner word budget: validator item 9, writing rules, `props.md`, 12-word fallback, text audit, critic `neutral` | Needs D1's `WORD_CAPS`. It must precede D3, whose picture scenes pass through `validate_scene`. |
| D3 | Selection rules R6 and R7; deterministic pictures | Needs D1's template classes and D2's validator. |
| D4 | Word-density measurement: eval bar, `evals/word_density.py`, E2E step 9 | Measures D1–D3; must exist before D5. |
| D5 | Re-measure: planner eval, E2E, cold budget; close-out | Measures the finished system. |

---

## 3. The items

### C1 — Quoted speech stays whole when splitting beats

**What this means for the user:** a character's line appears in the same scene as the words saying who said it, and the critic can see both.

**The gap:**
- `src/animated_infographics/timing/beats.py:15` puts `:` in `PUNCT_SUFFIXES`, and `:159-172` scores every boundary with both halves ≥ 1,500 ms, **including the one right before an opening quote**.
- In Wave B's `story_recipe_box` run, sentence 11 (9,625 ms) was split exactly at `photo: | "Who is Walter…`. The frozen timings are in `tests/data/quote_sentence.json`.
- Contract: `design_audio_and_timing.md` §7 step 3 (revised).

**Implementation:**
1. `QUOTED_SENTENCE_MAX_MS: Final[int] = 16000` in `config.py`/`beats.py`.
2. Remove `:` from `PUNCT_SUFFIXES`; `,`, `;`, `—` and `--` stay.
3. Quote spans per sentence: walk the sentence's words and toggle "inside quote" on each `"`, `“` or `”` character. A word *begins* a quote if its first character is `"`, `“` or `‘`.
4. In the split pass, a boundary is **not** a candidate if the word after it begins a quote, or if the boundary lies inside a quoted span.
5. Boundaries **inside** a sentence that contains a quotation are candidates only if that sentence alone is longer than `QUOTED_SENTENCE_MAX_MS`. Then use its non-quote boundaries, and failing those, the boundaries right after a `.`, `?` or `!` inside the quote. Boundaries **between** sentences stay candidates, still subject to the opening-quote exclusion in step 4.
6. Everything else in the split and merge passes is unchanged.

**Validate:**
- The "quoted-speech splitting" row in `design_testing_and_validation.md` §2.
- **Red first:** feeding `tests/data/quote_sentence.json` to the current `build_beats` yields two beats split at `photo:`; record it.
- After the fix it yields **one** beat.
- A synthetic 17,000 ms quoted sentence is split, and never immediately before its opening quote.
- **Falsify:** put `:` back in `PUNCT_SUFFIXES` and drop the quote exclusion → red.
- Beat counts per fixture change; record them.

**Blast radius:** `timing/beats.py`, `config.py`, `tests/test_timing_beats.py`, `tests/data/quote_sentence.json` (already committed).

---

### C2 — Critic passage framing, keyed text-thread answers, regression cases E + H

**What this means for the user:**
- The critic catches a line credited to the wrong person, including when the speaker is named in the sentence before the quote.
- Text threads get checked instead of silently skipped.

**The gap:**
- `src/animated_infographics/planner/critic.py:59-64` sends `Previous beat [context only]` / `Current beat` / `Next beat [context only]`.
- Measured: on the real split case the critic answered the narrator on seeds 7, 8 and 9, and the rules then report **agree** (§1.4).
- **Measured September 27, with the passage framing:** `critic.py:128-154` asks text threads for a `messages` array.
  - On **3 of 8** real threads, all with consecutive "them" messages, `gemma4:26b` returned a **1-element** array on seeds 7, 8 and 9.
  - `validate_critic_answer` (`critic.py:204-211`) rightly counts that as a failed attempt, so each of those scenes would end `unavailable`, unchecked.
  - With one required key per message: 24/24 complete (§1.4). This is regression case **H**.
- Contract: `design_planner.md` §11 (the revised "User" bullet; the `text_thread` row; "Why the `text_thread` answer is keyed"; cases E and H).

**Implementation:**
1. `build_critic_request` builds the user message as follows:
   - the cast block;
   - a blank line;
   - the **exact** header line `Passage (read all of it; who speaks is often named in the sentence before a quote):`, then a newline;
   - the beat before the previous one, the previous beat, this beat and the next beat, joined by single spaces (skip missing ones);
   - a blank line;
   - the template's question (unchanged in this item).
2. No "context only" text remains anywhere in the request.
3. **`text_thread` answers are keyed.**
   - The schema is `{"type": "object", "properties": {"message_1": E, …, "message_<n>": E}, "required": ["message_1", …, "message_<n>"], "additionalProperties": false}`.
   - `E = {"type": "string", "enum": ["me", "them", "unknown"]}` and `n = len(props.messages)`.
   - The keys appear in this order.
4. `validate_critic_answer` for `text_thread`:
   - a missing `message_<k>` is the error `critic messages missing: message_<k>` (a failed attempt);
   - otherwise it returns the answer **normalised** to `{"messages": [{"sender": answer["message_1"]}, …]}`, so `critic_mismatches` keeps its current sender logic.
5. `dialogue` keeps its array schema (39/39 complete, §1.4).
6. Add cases **E** and **H** to the regression set, in both `tests/slow/` and the planner eval, exactly as in the §11 table.
   - Case E uses its own cast list: `c1 Me (narrator)`, `c2 Grandma Rose`, `c3 Danny`, `c4 Walt`.
   - Case H reads its cast, the four passage beats and its props from `tests/data/critic_text_thread_cases.json` (`"case": "H"`).

**Validate:**
- **Red first:** case E fails on the current framing (the critic answers `c1`, reported as agree).
- **Intermediate red** (the reason step 3 exists): after step 1 but before step 3, case H returns one element on seeds 7, 8 and 9 → `unavailable`. Record it.
- After the fix, the six cases A, B, B′, C, E and H classify correctly on **seeds 7, 8 and 9** (18/18).
- Unit tests:
  - the request contains the header line verbatim and no "context only";
  - a 3-message thread's schema has exactly the keys `message_1`, `message_2`, `message_3`, all required;
  - a stub answer missing `message_2` is a failed attempt.
- **Falsify:**
  - restore the old labels → case E is red;
  - restore the array schema → case H is red.

**Blast radius:** `planner/critic.py`, `tests/test_critic.py`, `tests/slow/`, `evals/planner.py`; `tests/data/critic_text_thread_cases.json` is already committed.

---

### C8 — Text-thread contact identity

**What this means for the user:** a text message is never shown under the wrong person's name, and a thread with someone from the story shows their face.

**The gap:**
- In `story_room_12` s018 (Wave B E2E), the beat `She wrote back: "Keep the room. He's never missed one."` directly follows `By midnight, I texted Deb:`, yet the thread's `contact_name` is **"Sofia"** (`c4`, Mr. Alvarez's daughter).
  - Nothing checks `contact_name`. The critic asks only "me or them" per message (`critic.py:128-154`), and both messages really are "them".
  - `critic_mismatches` compares senders only (`critic.py:263-275`). `plan_report.json` records s018 as **agree**.
- All 8 threads in Wave B's story runs have `contact_cast_id: null`, including the four whose contact is Deb or Danny. So the header avatar (`design_templates.md` §2.10) is never drawn.
- Contracts: `design_planner.md` §11 (the `text_thread` row; "Why `contact`"; "Contact resolution"; the **Contact** mismatch rule; cases F and G); `design_templates.md` §2.10.

**Implementation:**
1. Append to the `text_thread` question, verbatim, with one leading space: ` Who is the other person in this conversation, according to the passage? Answer a cast id, or "unknown" if the passage does not say or they are not in the cast list.` The wording is measured: without "according to the passage … does not say", the model answered Danny for an invented thread with Walt (§1.4).
2. Add `"contact": {"type": "string", "enum": [<every cast id except the narrator's>, "unknown"]}` to the keyed schema from C2, as the **last** property, and require it. With `contact` placed first, a different set of threads collapsed.
3. `planner/critic.py`: add `resolve_contact(props, bible) -> str | None`. Let `norm(x) = " ".join(x.split()).casefold()`. It returns:
   - `contact_cast_id`, if set;
   - otherwise the id of the **only** non-narrator cast member with `norm(name) == norm(contact_name)`;
   - otherwise `None`.
4. `critic_mismatches` for `text_thread`: when `answer["contact"]` is neither `"unknown"` nor `resolve_contact(...)`, append `f"contact: {props.contact_name} vs {name} ({cid})"`, where `cid` is the critic's id and `name` is that cast member's bible name (e.g. `contact: Sofia vs Deb (c3)`). `format_disagreement_message` then renders `- contact: you said Sofia; the reading says Deb (c3)`, and needs no change.
5. **Contact fill** (`planner/props.py`). For every `text_thread` props object the planner produces (primary, alternate and critic retry):
   - after text normalisation and **before** `validate_scene`, if `contact_cast_id` is null and rule 3's name match finds exactly one id, set `contact_cast_id` to it (a new props object);
   - never touch a non-null `contact_cast_id`;
   - leave hand edits in `preview` alone.
6. Add cases **F** and **G** to the regression set in `tests/slow/` and the planner eval, from `tests/data/critic_text_thread_cases.json`.

**Validate:**
- The "critic text threads" row in `design_testing_and_validation.md` §2.
- **Red first:** on the post-C2 code, case F yields no mismatch (reported agree); record it.
- **The falsifying assertion:** F yields exactly `["contact: Sofia vs Deb (c3)"]` on seeds 7, 8 and 9.
- After the fix, the eight cases A, B, B′, C, E, F, G and H classify correctly on seeds 7, 8 and 9 (24/24).
- **Falsify:**
  - delete the contact comparison → F is red;
  - move `contact` before the message keys and re-run F, G and H on the three seeds → record whether any collapses (a measurement for the commit body, not a gate).
- In C7's E2E, for every `text_thread` in `story_room_12` and `story_recipe_box`:
  - list `contact_name`, `contact_cast_id` and the critic status;
  - open the hero frame of each thread whose contact is a cast member, and describe the header avatar.

**Blast radius:** `planner/critic.py`, `planner/props.py`, `tests/test_critic.py`, `tests/slow/`, `evals/planner.py`.

---

### C3 — Critic retry robustness

**What this means for the user:** when the critic spots a wrong speaker or tone, the scene actually gets fixed. Where it can't be, the reviewer can see why.

**The gap:**
- `planner/props.py:382` runs the critic-triggered retry with `max_attempts=1`, so any small validation miss discards it.
- `:389` sets `changed=True` whenever a retry returns, even with identical props.
- Retry errors are not recorded.
- Scenes rebuilt by rule R3 are marked `not_applicable` without a critic call (`:607`).
- Measured: 30 of 149 mismatches ended with the wrong original kept, e.g. `story_recipe_box` s015 "Rose?" stayed **angry**.
- Contract: `design_planner.md` §11 ("On mismatch", "Recorded"); `design_data_contracts.md` §6.

**Implementation:**
1. The critic-triggered retry is one `run_with_retries` round with the default **3** attempts.
2. If it still fails and **every** mismatch has the form `lines[i].tone: <x> vs unknown`, set those lines' tone to `neutral` (a new scene object), re-run `validate_scene`, and record `repair: "tone_neutral"`.
3. `changed` = the final props differ from the original props (dict comparison), never "a retry returned".
4. `CriticReport` gains `repair: Literal["tone_neutral"] | None` and `retry_errors: list[str]`; export (G8).
5. The R3 repair path calls `_evaluate_scene_critic` for its replacement scene when `needs_critic` is true.
6. `evals/planner.py` reports per fixture: critic calls, agree, changed, `tone_neutral` repairs, and **unchanged-after-mismatch**.

**Validate:**
- The "critic hardening" row in `design_testing_and_validation.md` §2 (stub backend: a retry that fails 3 times on a tone-only mismatch → `neutral` and `changed: true`; any other mismatch → original kept with `retry_errors`; an identical retry → `changed: false`; R3 replacement → one critic call).
- **Red first** on the current code.
- **Falsify:** revert to `max_attempts=1` → the 3-attempt test is red.
- In C7's eval, **unchanged-after-mismatch must fall**. Record before (30/149 across Wave B's runs) and after.

**Blast radius:** `planner/props.py`, `contracts/models.py` + exports, `evals/planner.py`, tests.

---

### C4 — No internal ids on screen

**What this means for the user:** viewers never see "(v1)" or "c1 buys the Sundowner from c3".

**The gap:**
- Nothing checks free text for entity ids.
- Measured in Wave B's E2E storyboards: "One card missing from the recipe box (v1).", "c1 stops working nights", "c1 buys the Sundowner from c3", "Feathered adversaries (c4: The Emus)" (4 in 311 unique scenes).
- Contract: `design_planner.md` §6 item 8.

**Implementation:**
1. `planner/validate.py`: `internal_id_errors(path, s, bible) -> list[str]` for the item-7 free-text fields. Tokens are `re.findall(r"[A-Za-z0-9]+", s)`, casefolded. It is an error if any token equals one of this bible's ids.
2. The message is exactly `props.<field>: contains the internal id "<id>" — use the name ("<entity name>")`.
3. Wire it into `validate_scene` (the planner and `preview` both get it).
4. `prompts/props.md` gains the sentence, verbatim: `Refer to people, places and objects by their names; never write ids like c1, p2 or v1.` Record the new prompt SHA-256 in C7's eval.
5. `evals/text_audit.py` counts id leaks.

**Validate:** the "internal ids" row in `design_testing_and_validation.md` §2 ("Plan B", "Route 66", "c3po" accepted). **Red first:** the four real strings pass today. **Falsify:** disable the check → the four are accepted → red. In C7's eval: **0 id leaks**.

**Blast radius:** `planner/validate.py`, `prompts/props.md`, `evals/text_audit.py`, tests.

---

### C5 — Caption word spacing

**What this means for the user:** captions read as separate words ("the engagement fell"), even while a long word is highlighted.

**The gap:**
- `renderer/src/story/Captions.tsx:80-95` enlarges the active word with `transform: scale(1.12)` and 0.15/0.3/0.45 em margins. A transform does not reflow, so on long words the growth plus the 12 px stroke swallows the margins.
- Measured on half-scale stills: the widest empty run was 4 px on "theengagementfell" and on "312 handwritten cards,", versus 12–17 px on correct pages.
- It has been present since Wave A. Contract: `design_visual_direction.md` §8 ("Word spacing", "Spacing check").

**Implementation:**
1. Each word renders as `display: inline-grid` with a single grid area. Child 1 is an invisible sizer (`visibility: hidden`, `font-size: 1.12em`, same text, same stroke). Child 2 is the visible word (`font-size: 1em`, or `1.12em` when active), centred (`justify-self: center; align-self: end`).
2. Adjacent word boxes are separated by `margin-right: 0.3em` (none after the last). There is no `transform: scale` on words.
3. The page still fits through the B11 `FitText` caption slot (76→60 px, 2 lines, 900 px).
4. Add gallery fixture `captions__long_active` (page `["the", "engagement", "fell"]`, `engagement` active) and golden.
5. `tests/test_caption_spacing.py` implements the §8 spacing check on its render: in the caption band, glyph columns are those with a pixel of relative luminance > 0.5, and there must be **≥ 2 runs of ≥ 16 empty columns** at full resolution. Run it from `check_gallery.sh`.

**Validate:**
- **Red first:** the spacing test on the current renderer fails (expect a widest run ≈ 8 px at full resolution).
- After: ≥ 2 runs ≥ 16 px.
- Re-preview `story_recipe_box` and apply the metric at half-scale thresholds (≥ 8 px) to **every** caption page's hero frame in s000–s031. Record the number of pages checked and the minimum gap.
- **Falsify:** restore the scale transform → red.
- Open the new golden and a re-previewed s020, and describe them.

**Blast radius:** `Captions.tsx`, gallery fixture + golden, `tests/test_caption_spacing.py`, `scripts/check_gallery.sh`.

---

### C6 — Hygiene: generated country codes; a missing input fails loudly

**What this means for the user:** the map's country highlighting cannot silently drift from its data, and a job that lost its music file says so instead of rendering without it.

**The gap:**
- `renderer/src/components/countryCodes.ts` is a hand-written copy of `data/vendor/countryInfo.txt`. It matches today: 252/252 entries, 0 disagreements. But no gate would notice drift.
- `src/animated_infographics/stages/compile.py:45` and `:54` silently skip a missing `ingest.music` file or `sfx_dir`.
- Contracts: `design_data_contracts.md` §1 (generated files), `design_system_architecture.md` §4.

**Implementation:**
1. `renderer/scripts/gen-country-bboxes.ts` also writes `renderer/src/generated/countryCodes.ts` (DO-NOT-EDIT header, numeric → ISO3, sorted). Delete `src/components/countryCodes.ts` and update the import in `MapView.tsx:9`. Add the file to `check_schema_sync.sh`.
2. `compile.py`: if `ingest.music` is set but the file is missing, or `ingest.sfx_dir` is set but the directory is missing → `ValidationFailed(f"{path} is recorded in ingest.json but missing from the job")`.

**Validate:**
- G8 covers the new file. **Falsify:** hand-edit one entry → G8 red.
- A unit test deletes `input/<music>` from a job and runs compile → exit-2 error naming the path. **Red first:** today the music silently disappears.

**Blast radius:** `gen-country-bboxes.ts`, `renderer/src/generated/`, `MapView.tsx`, `check_schema_sync.sh`, `stages/compile.py`, tests.

---

### C7 — Re-measure; close-out

**What this means for the user:** they get measured confirmation that the fixes worked on real stories, and that the 10-minute budget still holds.

**Implementation:**
1. Re-run the planner eval (`--no-llm-cache`) → a new `docs/evals/planner_<date>.md`. Every `design_planner.md` §9 bar must hold:
   - critic regression **8/8** (A, B, B′, C, E, F, G, H);
   - text audit with 0 newlines, 0 completeness failures and **0 id leaks**;
   - the critic outcome table, including unchanged-after-mismatch versus Wave B's 30/149.
2. Re-run G12.
   - In `story_recipe_box`'s storyboard, the Walter Lindqvist quote must no longer be attributed to the narrator. Describe what it is attributed to, and whether its beat contains "texted me a photo:".
   - List every `text_thread` in `story_room_12` and `story_recipe_box` with its `contact_name`, `contact_cast_id` and critic status (C8). Count the `unavailable` text-thread critics (expected 0).
3. Re-run `scripts/measure_budget.sh` → `docs/evals/budget_<date>.md`, cold, with 0 cache hits.

**Validate:** bars as above, plus budget ≤ 6.5 / 3.5 / 10 min. Exceeding a bar is filed with numbers, never tuned away.

**Close-out of Wave C (not of this guide):**
1. Full battery, bare; update §1.3.
2. Add Wave C to §5.1 and update `ongoing_general_errors.md` §1.
3. **Do not rewrite this guide and do not stop. Continue with D1.** The Wave B numbers in §1.4 are Wave D's "before".

---

## 3.D Wave D — picture-first stories (Issue 7 → Option A)

**Read first:** `design_templates.md` §5 (the whole word budget: counting, removed fields, caps, template classes, measurements) and `design_planner.md` §4 (R6, R7), §5, §6 item 9, §9 and §11. **Line numbers below are as of `ee0879d`, before Wave C.** Wave C moves some of them, so find code by symbol.

**Standing rule for this wave:** captions are **not** touched. Karaoke captions stay exactly as C5 leaves them; the user chose Option A, which keeps them.

---

### D1 — Word-budget contracts: removed fields, list maxima, `neutral`, `WORD_CAPS`, words module, renderer, gallery

**What this means for the user:** pictures stop carrying captions that repeat the narration, characters are introduced without trait chips, lists get shorter, and a reaction shot can show a plain face.

**The gap:**
- The props models still carry the fields that restated the narration, in `src/animated_infographics/contracts/templates.py`:
  - `StatCalloutProps.caption` (`:82`), `EmotionBeatProps.caption` (`:190`), `LocationProps.caption` (`:234`), `SetPieceProps.caption` (`:243`) and `MapFocusProps.caption` (`:260`);
  - `CharacterIntroProps.traits` (`:148-150`).
- The list maxima allow long lists: `icon_list.items` 4 (`:98`), `cause_effect.nodes` 4 (`:120`), `comparison` points 4 (`:130-132`), `dialogue.lines` 3 (`:165`), `text_thread.messages` 5 (`:181`) and `timeline.events` 6 (`:274`).
- `EmotionBeatProps.emotion` (`:189`) has no `neutral`.
- Nothing counts words.
- **Measured on the Wave B storyboards:** 1.11–1.91 graphic words/s, and only 3–12% of scenes with ≤ 2 words (§1.4).

**Implementation:**
1. **Props models** (`contracts/templates.py`):
   - Delete the six fields above.
   - Set the list maxima: `IconListProps.items` 2..3, `CauseEffectProps.nodes` 2..3, `ComparisonPanel.points` 1..2, `DialogueProps.lines` 1..2, `TextThreadProps.messages` 2..3, `TimelineProps.events` 3..4.
   - `EmotionBeatProps.emotion` becomes `Literal["neutral", "happy", "sad", "angry", "shocked", "confused", "smug", "nervous"]`.
   - Character limits stay as they are.
2. **Registry**:
   - Remove the `caption` slot from `stat_callout`, `emotion_beat`, `location`, `set_piece` and `map_focus`, and the `trait` slot from `character_intro`.
   - `use_when` for `icon_list` becomes `2-3 parallel things (demands, causes, items, reasons).`, and for `timeline`, `3-4 dated events in sequence.`
   - Writing rules change in D2, not here.
3. **`WORD_CAPS: Final[dict[str, dict[str, int]]]`** in `contracts/templates.py`. Copy it verbatim; the path syntax is `a.b` for nested objects and `x[]` for "every element":
   ```python
   WORD_CAPS = {
       "kinetic_quote": {"text": 12},
       "stat_callout": {"suffix": 2},
       "icon_list": {"heading": 3, "items[].label": 3},
       "reveal": {"kicker": 3, "text": 6},
       "cause_effect": {"nodes[].label": 3},
       "comparison": {"a.heading": 3, "b.heading": 3, "a.points[]": 3, "b.points[]": 3},
       "character_intro": {"descriptor": 4},
       "dialogue": {"lines[].text": 10},
       "text_thread": {"contact_name": 3, "messages[].text": 8},
       "relationship_map": {"edges[].label": 3},
       "location": {"era_label": 2},
       "map_focus": {"markers[].label": 3},
       "timeline": {"events[].date_label": 3, "events[].label": 3},
   }
   ```
   Also add the three template classes of `design_templates.md` §5.4 as frozensets: `PICTURE_TEMPLATES`, `REPLACEABLE_TEMPLATES` and `KEPT_TEMPLATES`.
4. **`src/animated_infographics/planner/words.py`** (new):
   - `count_words(s: str | None) -> int`: tokens of `s.split()` that contain a character with `.isalnum()`; 0 for `None`.
   - `field_values(props: Mapping[str, Any], path: str) -> list[tuple[str, str]]`: every `(concrete_path, value)` for a `WORD_CAPS` path, e.g. `items[1].label`, skipping `None`.
   - `graphic_words(template: str, props: Mapping[str, Any]) -> int`: the sum of `count_words` over every `WORD_CAPS[template]` path; 0 for a template without an entry (`title_card`, `emotion_beat`, `set_piece`).
   - This one table therefore defines both the caps and the density metric (`design_templates.md` §5.1).
5. **Regenerate** the JSON Schema and TypeScript types (`contracts/export.py`). G8 must be green.
6. **Python code that read the removed fields:**
   - delete the caption and trait branches in `planner/validate.py` `normalize_props_text` (`:120-123`, `:169-170`, `:197-199`, `:212-214`) and `validate_scene` (`:385`, `:388`, `:439-441`, `:466-467`, `:506`, `:508`, `:533-534`, `:561-562`);
   - update the field list in the docstring of `evals/text_audit.py:125`;
   - update `tests/data/props_examples.json` and every test that builds a removed field or an over-long list (`grep -rn "caption\|traits" tests` lists the files; `caption` also matches karaoke captions, which are not touched).
7. **Renderer:**
   - Delete the drawing of the removed fields in `renderer/src/templates/{stat_callout,emotion_beat,location,set_piece,map_focus,character_intro}.tsx`. Every other element keeps its position (`design_templates.md` §2).
   - `emotion_beat` moves the avatar to top y 400 and the glyph to (800, 420). `neutral` draws **no glyph** and the neutral face. The avatar blinks at scene frames 45 and 135.
   - `dialogue` no longer has a third row.
8. **Gallery:**
   - Update `renderer/src/gallery/fixtures/*.ts` so that every fixture obeys `design_templates.md` §3 and §5.3. `max` strings reach their **character** limit within their **word** cap.
   - `emotion_beat` `typical` shows the neutral face.
   - Re-cut the goldens of the changed fixtures only (`check_gallery.sh --update`), then run G10 without `--update`: 0 overflows.

**Validate:**
- **Red first:** before the change, a test asserting that `StatCalloutProps.model_validate({... "caption": "x"})` raises, and that a 4-item `IconListProps` raises, **fails**. Record it.
- After the change:
  - both raise;
  - a test walks `WORD_CAPS` and asserts that every path resolves to a `str` or `str | None` field of that template's props model, so a typo cannot silently disable a cap;
  - a test asserts the three classes partition the 16 templates;
  - the `count_words` cases in the "word counting and caps" row of `design_testing_and_validation.md` §2 pass.
- G5, G8 and G10 are green.
- **Falsify:**
  - hand-edit a generated TypeScript type to re-add `caption` → G8 is red;
  - add a fourth item to the `icon_list` `max` fixture → the fixture's type check or the gallery overflow check is red.
- Open the new goldens `emotion_beat__typical`, `location__max`, `character_intro__max` and `timeline__max`. Describe each: what text remains, and where the avatar sits.

**Blast radius:** `contracts/templates.py`, `contracts/export.py` outputs (schema and TypeScript), `planner/words.py` (new), `planner/validate.py`, `evals/text_audit.py`, `tests/`, `tests/data/props_examples.json`, 6 renderer templates, `renderer/src/gallery/fixtures/`, `renderer/goldens/`.

---

### D2 — Planner word budget: validator item 9, writing rules, `props.md`, 12-word fallback, text audit, critic `neutral`

**What this means for the user:** every label, quote and message on screen is a few words, not a restated sentence.

**The gap:**
- Nothing checks words.
  - The frozen `tests/data/word_cap_cases.json` holds 9 real Wave B props objects, e.g. a 7-word character descriptor and a 13-word `kinetic_quote`. **All 9 pass `validate_scene` today.** 40 Wave B scenes break at least one cap.
- `planner/props.py:183-207` `_format_pydantic_validation_error` formats only `string_too_long`. A list that is too long reaches the model as Pydantic's raw message.
- `prompts/props.md:29-30` asks for "character limits and line counts" and "punchy on-screen display copy". The measured result was 16 of 32 scenes with ≥ 10 words.
- `prompts/select.md:26` says "2 to 4 parallel items".
- The deterministic `kinetic_quote` (`props.py:74-104`) can produce 17 words.
- The critic's `emotion_beat` enum (`critic.py:165-177`) cannot say `neutral`.

**Implementation:**
1. **Validator item 9** in `planner/validate.py`: `word_cap_errors(template: str, props: Mapping[str, Any]) -> list[str]`.
   - For each path of `WORD_CAPS[template]` in table order, and each value in index order, when `count_words(value) > cap`, emit exactly `f"props.{concrete_path}: {n} words, limit {cap} — rewrite it shorter as a complete phrase"`.
   - Call it from `validate_scene` with `props.model_dump()`, after item 8 (C4).
2. **List error format** in `_format_pydantic_validation_error`: when `type == "too_long"` and the input is a list, return `f"{path}: {len(input)} items, limit {ctx['max_length']} — keep the most important ones"`.
3. **Registry `writing_rules`**, replaced verbatim. Templates not listed keep theirs.

   | Template | `writing_rules` |
   |---|---|
   | `kinetic_quote` | `text is a verbatim span of this beat, at most 12 words` · `each emphasis word is a whole word of text` |
   | `stat_callout` | `value must be a number said in this beat` · `suffix is the unit, at most 2 words (e.g. "gallons", "feet high")` |
   | `icon_list` | `2 to 3 items` · `heading is optional, at most 3 words` · `each label at most 3 words: a name or short noun phrase, not a sentence` |
   | `reveal` | `kicker at most 3 words (rendered uppercase, e.g. "PLOT TWIST")` · `text at most 6 words` · `at most 2 per video (planner R4)` |
   | `cause_effect` | `2 to 3 nodes in sequence` · `each label at most 3 words` |
   | `comparison` | `each heading at most 3 words` · `1 to 2 points per side, each at most 3 words` |
   | `character_intro` | `descriptor at most 4 words, saying who they are, not their name (e.g. "The motel manager")` · `at most once per cast_id per video (planner R3)` |
   | `dialogue` | `1 to 2 lines` · `each line at most 10 words` |
   | `text_thread` | `contact_name at most 3 words` · `2 to 3 messages` · `each message at most 8 words` |
   | `emotion_beat` | `emotion is the feeling this beat shows for that person; neutral if it shows none` |
   | `relationship_map` | the four existing rules, then `each edge label at most 3 words` |
   | `location` | `era_label is optional, at most 2 words` · `era_label digit grounding` |
   | `set_piece` | `set_piece_id is the object this beat is about` |
   | `map_focus` | `1 to 3 markers` · `region is 'world' or ISO3` · `each marker label at most 3 words` |
   | `timeline` | `3 to 4 events` · `0 <= highlight_index < len(events)` · `date_label at most 3 words` · `label at most 3 words` · then the existing date-label rule and `labels all differ and run forward in time`, unchanged |
4. **`prompts/props.md`:** replace guidelines 3 and 4 with the two lines in `design_planner.md` §5, verbatim. C4's sentence stays.
5. **`prompts/select.md:26`:** `- A set of 2 to 3 parallel items, reasons, or steps -> icon_list`.
6. **Deterministic `kinetic_quote`:** the 12-word rule of `design_planner.md` §5.
7. **`critic.py`:** add `"neutral"` first to the `emotion_beat` emotion enum. The mismatch rule is unchanged.
8. **`evals/text_audit.py`:** count word-cap violations over the saved storyboards (`word_cap_errors` per scene). The bar is 0 (`design_planner.md` §9).
9. Record the new SHA-256 of `props.md` and `select.md` in D5's eval.

**Validate:**
- **Red first:** the 9 frozen cases produce `[]` from today's `validate_scene`. After the change, `word_cap_errors` returns **exactly** each case's `expected_errors`, strings and order included.
- The rest of the "word counting and caps" row: the list message, the 30-word fallback, and no error at exactly the cap.
- **Slow test (real model)** `tests/slow/test_word_caps_live.py`. Five real beats from the September 27 probe, one each of `timeline` (`emu_war` s010), `comparison` (`emu_war` s017), `icon_list` (`molasses_flood` s006), `text_thread` (`story_room_12` s016) and `character_intro` (`emu_war` s008), through the real props stage. Each must yield valid props within 3 attempts, with the backend's normal seeds (7 + attempt), and the `character_intro` descriptor must not contain the cast member's name. The probe passed all five. The five cases (bible, sentence texts, neighbouring beats, the Wave B props and the probe's props) are frozen in `tests/data/word_caps_live_cases.json`; build the `Transcript` from its sentence texts as `evals/planner.py` does.
- **Falsify:** raise one cap to 99 → the matching frozen case is red.

**Blast radius:** `planner/validate.py`, `planner/props.py`, `contracts/templates.py` (writing rules), `prompts/props.md`, `prompts/select.md`, `planner/critic.py`, `evals/text_audit.py`, tests.

---

### D3 — Selection rules R6 and R7; deterministic pictures

**What this means for the user:** a story has at most one timeline and one comparison, and after a couple of wordy scenes it cuts to a face, an object or a place, the way Casually Explained does.

**The gap:**
- `planner/select.py:66-143` `apply_rules` runs R1, R2, R4 and R5 only.
  - The frozen `tests/data/recipe_choices.json` (real Wave B `story_recipe_box` choices) keeps **3 timelines and 2 comparisons** through it.
  - Nothing ever inserts a wordless picture.
- `Choice` (`select.py:20-27`) cannot carry an entity.
- `plan_storyboard` (`props.py:445-555`) always calls the LLM.
- `critic.needs_critic` (`critic.py:24-36`) skips only `"deterministic fallback"`.
- `validate_plan` (`validate.py:582-640`) has no per-video limit for timelines or comparisons.

**Implementation:**
1. `Choice` gains `rhythm_id: str | None = None`.
2. `apply_rules(choices, n_scenes, beats, bible)`: the new signature, because R7 needs the beat texts and the bible. The order is R1, **R6**, R2, R4, R5, **R7**, exactly as in `design_planner.md` §4. R6 and R7 log a `RuleRepair` with `rule="R6"` / `"R7"`.
3. **`src/animated_infographics/planner/rhythm.py`** (new):
   - `QUOTED = re.compile(r"\"[^\"]*\"|“[^”]*”")`;
   - `FIRST_PERSON = re.compile(r"\b(i|me|my|mine|myself|we|us|our)\b", re.IGNORECASE)`;
   - `name_tokens(name)`;
   - `named_at(name, text) -> int | None`;
   - `rhythm_target(text, bible, prev, next) -> tuple[str, str] | None` returning `(template, entity_id)`.

   All of it exactly per `design_planner.md` §4, "R7".
4. **Props stage:** for a choice with `rhythm_id`, build the scene **without** the LLM. `build_rhythm_picture(scene_id, beat_i, template, rhythm_id)` produces:
   - `EmotionBeatProps(cast_id=id, emotion="neutral")`;
   - `SetPieceProps(set_piece_id=id)`;
   - `LocationProps(place_id=id, era_label=None)`.

   Each gets `rationale="rhythm picture"`, then `validate_scene`.
   - **Valid:** accept it with `fallback_level` 0, `attempts` 0 and critic `not_applicable`.
   - **Invalid:** run the normal ladder with `choice.alternate` (the replaced template) as the primary and `kinetic_quote` as the alternate.
5. `needs_critic` returns `False` for `rationale == "rhythm picture"`.
6. `validate_plan`: more than one `timeline` → `storyboard: timeline appears <n> times (max 1 per video)`; the same for `comparison`. R7 is a planner behaviour, **not** a plan invariant: a reviewer may replace a picture.

**Validate:**
- The "rhythm rules R6/R7" row in `design_testing_and_validation.md` §2.
- **Red first:** today's `apply_rules` on `tests/data/recipe_choices.json` keeps 3 timelines → the `≤ 1` assertion is red.
- After the change:
  - the output equals the file's `expected.choices` and `expected.rule_repairs` **exactly**: R6 s010, s023 and s008; R7 s002 → `emotion_beat` c1 and s016 → `set_piece` v2;
  - the seven `rhythm_cases.json` cases give their `expected`;
  - a stub-backend storyboard in which R7 fires makes **0** backend calls for that scene (call counter).
- **Falsify:**
  - drop the `QUOTED` stripping → R7-b picks `c1` → red;
  - drop the kept-class check → R7-e and R7-f are replaced → red.

**Blast radius:** `planner/select.py`, `planner/rhythm.py` (new), `planner/props.py`, `planner/critic.py`, `planner/validate.py`, tests; `tests/data/rhythm_cases.json` and `tests/data/recipe_choices.json` are already committed.

---

### D4 — Word-density measurement: eval bar, `evals/word_density.py`, E2E step 9

**What this means for the user:** "fewer words" becomes a number that every run reports and a gate that fails when it drifts.

**The gap:** no report counts on-screen words. The planner eval's transcript is simulated at a fixed 4 words/s (`evals/planner.py:54-99`), so a words-per-second bar can only be measured on real renders.

**Implementation:**
1. **`evals/planner.py`**, per fixture:
   - `graphic_words_total`;
   - `graphic_words_per_narration_word`;
   - `light_share` = scenes after the title card with `graphic_words ≤ 2` / (scenes − 1);
   - R6 and R7 repair counts.

   `light_share ≥ 1/3` joins `fixture_pass`. The report table gains these columns and prints the Wave B baselines from `design_templates.md` §5.5 beside them.
2. **`src/animated_infographics/evals/word_density.py`** (new CLI). Its arguments are job directories. For each it:
   - loads `timeline.json`;
   - sums `graphic_words(scene.template, scene.props)`;
   - sets `seconds = duration_frames / fps`;
   - prints `<job>: graphic_words=<n> seconds=<s.s> per_second=<x.xx> light=<k>/<m>`, where m is the number of scenes after the title card.

   It exits 1 if any job has `per_second > 1.0` or `k < m/3`.
3. **`scripts/e2e.sh`** step 9 per `design_testing_and_validation.md` §4. Its lines go into `docs/evals/e2e_<date>.md`.

**Validate:**
- A unit test on a synthetic two-scene timeline checks exact numbers.
- **Falsify:**
  - the E2E step on a copy of a job whose `duration_frames` is divided by 3 → exit **1**;
  - set the eval's light-share bar to 0.9 temporarily → the eval fails; restore it.

**Blast radius:** `evals/planner.py`, `evals/word_density.py` (new), `scripts/e2e.sh`, tests.

---

### D5 — Re-measure; close-out

**What this means for the user:** they see, measured on the four stories, that the videos carry far fewer words and that nothing else regressed.

**Implementation:**
1. **Planner eval**, cold (`--no-llm-cache`) → `docs/evals/planner_<date>.md`. Every `design_planner.md` §9 bar must hold on every fixture:
   - fallback ≤ 15%, distinct templates, 0 violations;
   - critic regression 8/8;
   - text audit with 0 newlines, completeness failures, id leaks and **word-cap violations**;
   - **light share ≥ 1/3**.
   Report R6/R7 counts and graphic words next to Wave B's.
2. **G12** including step 9. Every rendered job must show **≤ 1.0 graphic word/s and ≥ 1/3 light scenes**. Record each job's line against Wave B (`story_recipe_box` 1.91/s, 3/32).
3. **Cold budget** (`scripts/measure_budget.sh`) → `docs/evals/budget_<date>.md`. The bars are unchanged (≤ 390 s / 210 s / 600 s). R7 pictures remove LLM calls, and the probe used fewer props attempts than Wave B.
4. Open `story_recipe_box`'s contact sheet and five stills, and describe them:
   - a reaction shot (a neutral face, no text);
   - a set piece (name only);
   - the single timeline (≤ 4 events);
   - a text thread (≤ 3 messages);
   - a `kinetic_quote` (≤ 12 words).
5. README: remove any mention of captions under pictures or of trait chips; set the status to "Waves A–D delivered".

**Validate:** the bars above. Exceeding one is filed in `ongoing_general_errors.md` with the numbers, never tuned away. In particular, **do not raise a word cap, lower the light-share bar or add a template to the picture class to pass.**

**Close-out:**
1. Full battery, bare; update §1.3.
2. Rewrite this guide to **Queue Complete**.
3. Move Waves C and D to §5.1.
4. Update `ongoing_general_errors.md` §1.
5. Stop.

---

## 4. Deferred — do NOT start

- **Anything beyond Wave D's five items for Issue 7.** In particular: no change to karaoke captions, no new templates, no redrawn art style, no re-layout of the caption band.
- **DF1–DF9** (`ongoing_general_errors.md` §4): video input + PiP, 16:9, multi-voice, live mode, Reddit URL fetch, public-domain photos, historical borders, web editor, cloud LLM.

---

## 5. Do NOT change

### 5.1 Already delivered

- **Wave A (A1–A22), verified September 25, 2026**, and **Wave B (B1–B17), independently verified September 26, 2026.** One line per item, with verdicts, is in `ongoing_general_errors.md` §3.
- Items marked "✓" are not reworked. Items marked "→ C<n>" are touched only as that item specifies.

### 5.2 Accepted equivalents (checked; do not "fix" these back)

- The sync probe is drawn inside each scene's layer, not a separate Story layer.
- The geo bbox check handles antimeridian-crossing countries (`planner/geo.py`).
- `image_prompt` strips a trailing period from `visual_description`.
- `FitText` gives multi-line boxes 0.35 of a line of extra height for ascenders.
- The gallery computes fixture timing with a TypeScript port of `item_frames`, gallery-only.
- `fixtures/CHECKSUMS` paths are relative to `fixtures/`.
- `plan_report.json.llm_calls` counts the storyboard stage's calls only (select + props + critic).
- Node 26 works; the Node 22 fallback was not needed.
- **(Sept 26)** The critic's context lines use square brackets; this is superseded anyway by C2's passage framing.
- **(Sept 26)** B7's text audit marked PASS with 4 strings exactly at their limit. They are complete phrases, and the bar was corrected in `design_planner.md` §9: at-limit strings are reported, not failed.
- **(Sept 26)** Remotion `AudioLayer` clamps volume to ≥ 0.001 (−60 dB), so a zero-volume fade frame does not unregister the audio asset, and passes `loopVolumeCurveBehavior="extend"`. Needed for the music fade.
- **(Sept 26)** `renderer/public/geo/lakes-50m.json` is pretty-printed (1.5 MB). Size is not a concern.

### 5.3 User decisions

**September 23, 2026:**
- Offline first; a template library.
- History + Reddit-style stories; text + audio inputs.
- Mixed imagery; Python + TypeScript/Remotion; fully local.
- 9:16; karaoke captions; flat editorial vector; 1–3 min videos in about 10 min.
- Scenes + a persistent cast; single narrator; a mandatory review gate; music + SFX from a user-supplied pack.
- Live mode later, with the webcam in a corner.

**September 24, 2026:**
- **Issue 1 → A + B:** "If the story from reddit seems to be from a female's perspective then use af_heart, else use am_michael."
- **Issue 2 → A:** FLUX.2 [klein] 4B.
- Test stories must be complete stories.

**September 25, 2026:**
- **Issue 3 → A:** "Proceed with Option A. Though, in the example provided, I think that text is fine if the description calls for text like a recipe."
- **Issue 4 → A:** "Proceed with Option A."
- **Issue 5 → A:** "Option A".

**September 27, 2026 (in chat):**
- **Issue 6 → D (keep as is):** "I think the paraphrasing is fine." `dialogue` and `text_thread` may paraphrase in every genre.
- **Live presentations:** "For real-time presentations, it makes sense to show timelines and repeated graphics to drive home the point." Recorded for DF4 in `design_future_live_and_video.md` §4.
- **Issue 7 → A:** "Proceed with Option A." Picture-first stories: no restating text, word caps, a reaction-shot rhythm; karaoke captions stay (Wave D).

### 5.4 Invariants and intentional design decisions

**New (September 26, 2026):**
- **Quoted speech is never split from its introducing words** (unless the sentence exceeds 16 s); the colon earns no split bonus (C1).
- **The critic reads one continuous passage**; nothing is labelled "context only" (C2).
- **The critic-triggered retry gets 3 attempts**; only an unsupported tone may be repaired deterministically, to `neutral`; `changed` means the props differ (C3).
- **No bible entity id appears in on-screen text** (C4).
- **Caption words are laid out at their active size**; highlighting never changes layout (C5).
- **A recorded job-local input that is missing is an error, not a silent drop** (C6).

**New (September 27, 2026):**
- **The critic's `text_thread` answer is keyed, one required field per message**; `dialogue` keeps its array (C2).
- **The critic names a thread's contact, and a contact that disagrees is a mismatch.** `unknown` never is (C8).
- **A null `contact_cast_id` is filled only on an exact, unique name match** (C8).
- **`dialogue` and `text_thread` may paraphrase** (Issue 6 → D). Do not add a verbatim or word-overlap check to them.

**New (September 27, 2026, Wave D):**
- **`WORD_CAPS` is the single source** of both the word caps and the density metric; `count_words` is the only word counter.
- **Removed fields stay removed.** No caption under a picture and no trait chips, and no migration for jobs planned earlier.
- **R7 pictures are deterministic:** a neutral reaction shot, or a set piece or place with its name only. No LLM call, no critic call.
- **R7 never replaces a kept template** (`title_card`, `character_intro`, `dialogue`, `text_thread`, `reveal`), and quoted speech never counts as the narrator speaking.
- **At most one `timeline` and one `comparison` per offline video** (R6, also enforced in `validate_plan`). Live mode is exempt by the user's direction.
- **Karaoke captions are unchanged by Wave D.**

**Unchanged:**
- Job-local inputs are authoritative.
- Every LLM call goes through `run_with_retries`.
- LLM-facing schemas carry no length constraints, and `num_predict` bounds short answers.
- Text over images only where the scrim is ≥ 85%.
- The text check never runs on text-expected descriptions.
- The critic is blind, makes at most one critic call per scene, and an `unknown` speaker is never a mismatch.
- Timeline labels are a grounded date or one of 17 phrases.
- The voice-rule asymmetry.
- Cast = vector avatars only.
- No auto-approve.
- Scenes lead by 200 ms; captions never lead.
- Absolute-frame scenes.
- Timings are computed once, in Python.
- Grounding is a hard gate.
- Navy text on cast colours.
- FLUX.2 klein 9B is never used.
- Beat boundaries are not human-editable.
- The offline gate stays.
- Fixtures are original texts.
- Commit scope = item id.

### 5.5 Assessed and rejected — do NOT re-propose

**Carried over from Waves A and B:**
- Live-first; LLM-written scene code; generated video.
- Video input or URL fetching in the MVP.
- Vector-only or illustration-heavy imagery; generated cast portraits.
- Any cloud API.
- Both aspects at once; subtitles or no captions.
- Other art styles.
- Multi-voice in the MVP; an optional gate or a web editor.
- `TransitionSeries`; TypeScript as the schema source.
- Voices `bm_george`/`af_bella`; Z-Image-Turbo.
- Inferring narrator gender from stereotypes.
- Raising `maxLength` to "fix" truncation; relaxing the fallback bar; the mflux symlink.
- Issue 3 options B/C; Issue 4 options B/C; Issue 5 options B/C/D.
- The naive yes/no text-check prompt; an uncapped text-check call.
- Counting an `unknown` speaker as a mismatch; a second critic call per scene; bare "sign" in the text-expected list.
- Removing or skipping the critic or text check to meet the budget.

**New, September 26, 2026:**
- Keeping the "context only" framing and merely adding more regression cases.
- Letting the critic's answer overwrite the props directly without a retry (it can be wrong: case C).
- Deterministically repairing *who* mismatches.
- Fixing caption spacing by lowering the active scale below 1.12.
- Treating at-limit strings as failures.

**New, September 27, 2026:**
- Issue 6 options A, B and C (verbatim or word-overlap checks on dialogue).
- An array schema for per-message critic answers; `contact` before the message keys; the contact question without "according to the passage … does not say".
- Fuzzy or first-name matching for the contact fill.

**New, September 27, 2026 (Wave D):**
- Issue 7 options B (hiding captions on quote, dialogue and text scenes), C (no captions) and D.
- LLM-chosen emotions for R7 reaction shots, and a critic question that leans "neutral" (it answered `neutral` 27/27).
- Letting R7 replace introductions, dialogue, text threads or reveals.
- Raising `kinetic_quote` above 12 words for quotes that do not fit; the ladder's alternate handles them.
- Counting bible names or the stat value in graphic words; a words-per-second bar in the planner eval (its transcript is simulated).

---

## 6. Where the contracts live

| What | Where |
|---|---|
| Pipeline, job layout, **job-local inputs incl. missing-input error (§4)**, CLI, review gate, local-only policy, pinned models | `design_system_architecture.md` |
| JSON shapes (**`plan_report.critic` incl. `repair`, `retry_errors`**), generated files (**`countryCodes.ts`**), sync gate | `design_data_contracts.md` |
| Ingest, TTS, ASR, loudness, frame math, **beat splitting with quoted speech (§7)**, captions, SFX | `design_audio_and_timing.md` |
| LLM backend, **paraphrase rule for dialogue (§5)**, voice §10, validators (**§6 items 6–8**), grounding and timeline labels §8, eval bars §9 (**text audit, 8-case critic regression**), **critic §11 (passage framing, keyed text-thread answers, contact resolution and mismatch, 3-attempt retry, tone repair, cases E–H)** | `design_planner.md` |
| The 16 templates (**§2.10: the contact critic and avatar fill**) | `design_templates.md` |
| Palette, composited contrast §2.1, **captions incl. word spacing and spacing check (§8)**, illustration + text check §7 | `design_visual_direction.md` |
| Remotion, clock, render CLI, preview, verification | `design_rendering.md` |
| Fixtures, test rows (**quoted-speech splitting, internal ids, critic hardening, critic text threads**), gates, E2E, offline, cold budget | `design_testing_and_validation.md` |
| Resolved index (Wave B verdicts; Issues 6 and 7 decisions), lessons 2.6–2.9, deferred items DF1–DF9, decision log | `ongoing_general_errors.md` |
| Live mode, including the user's direction on timelines and repeated graphics | `design_future_live_and_video.md` |
| **Word budget: counting, removed fields, caps table, template classes, measurements (Wave D)** | `design_templates.md` §5 (per-template props in §2) |
| **R6, R7, `rhythm_target`, deterministic pictures, the props prompt, validator item 9, word-budget bars** | `design_planner.md` §4, §5, §6 item 9, §9 |
| **Word-cap and rhythm test rows; E2E step 9 (word density)** | `design_testing_and_validation.md` §2, §4 |

---

## 7. Validation standard

- **Red first, on real inputs.** A regression set built only from tidy cases can pass while production fails (lesson 2.6).
- **Measure outcomes by comparing before and after**, and record why a repair did not happen (lesson 2.7).
- **Measure the rendered result, not the style values** (lesson 2.8).
- A gate must be able to fail, and must fail closed.
- A perfect score is a reason to look harder.
- Warm caches measure nothing about a cold budget.
- Read exit codes bare. A gate that did not run is not a pass. Open every artefact and describe it.
- **Never loosen a bar to pass it.** File it with the measurement.

---

## 8. THE LOOP

```
(1) Is there an approved item? Wave C (C1–C8, C8 third), then Wave D
    (D1–D5), in §2 order. If all are done, STOP. Never start DF1–DF9 or
    anything not in §3 without a user selection.
    Never fill in a `Your selection:` line.
(2) Read the item and EVERY design section it names. Copy prompts, header
    lines, thresholds and error strings VERBATIM.
(3) RED FIRST on the frozen real case; record the failure.
(4) Build only what the item says. Nothing from §5.5.
(5) GREEN; then falsify (break, see red, restore, see green).
(6) Open every artefact and describe it.
(7) Full battery, bare. Update §1.3.
(8) ONE commit, scope = item id (`fix(c1): …`, `feat(d1): …`). WHY +
    red/green in the body. ONE line under "Wave C" / "Wave D" in
    ongoing_general_errors.md §3, citing `git log --grep "(c1)"`.
    Never amend after pushing.
(9) git push origin main.
(10) Next item.
```

---

## 9. Definition of Done: Waves C and D

**Wave C**
- [ ] C1–C8 each landed as one pushed commit scoped to its id, with red and green runs recorded.
- [ ] `tests/data/quote_sentence.json` yields one beat; the Walter Lindqvist quote is not attributed to the narrator in the re-run E2E.
- [ ] Critic regression 8/8 on seeds 7, 8, 9; unchanged-after-mismatch reported and lower than Wave B's 30/149.
- [ ] Case F yields `contact: Sofia vs Deb (c3)`. The re-run E2E lists every text thread's contact, with 0 `unavailable` text-thread critics.
- [ ] 0 id leaks in C7's planner-eval text audit.
- [ ] Caption spacing check green on the gallery fixture and on every re-previewed `story_recipe_box` page.
- [ ] `countryCodes.ts` generated and sync-gated; a missing recorded input fails with exit 2.
- [ ] C7's cold budget measured with 0 cache hits; bars met or filed. Wave C is recorded in §5.1; the guide is **not** rewritten yet.

**Wave D**
- [ ] D1–D5 each landed as one pushed commit scoped to its id, with red and green runs recorded.
- [ ] The removed fields exist nowhere: the props models, the generated schema and TypeScript, the renderer and the fixtures (G5, G8 and G10 green).
- [ ] All 9 frozen word-cap cases give their exact errors; the 7 rhythm cases and `recipe_choices.json` give their exact expected output.
- [ ] Planner eval: every §9 bar on every fixture, including **light share ≥ 1/3** and **0 word-cap violations**; critic 8/8.
- [ ] E2E step 9: every rendered job **≤ 1.0 graphic word/s** and **≥ 1/3 light scenes**, reported beside Wave B's numbers.
- [ ] Cold budget re-measured with 0 cache hits; bars met or filed.
- [ ] Five `story_recipe_box` stills opened and described (reaction shot, set piece, timeline, text thread, quote).
- [ ] §1.3: every gate G1–G14 green, measured this session, read bare.
- [ ] This guide rewritten to **Queue Complete**. **Then stop. Do not invent work.**

# Planner (local LLM)

This document owns: the **LLM backend**, the pre-narration **narrator voice selection** (§10), the four **planning stages** (bible → segment → select → props), the **deterministic rules** that bound the LLM, the **validators** (fit, grounding, references), and the **fallback ladder** that guarantees the planner never crashes the pipeline.

**The governing principle: the LLM proposes; code disposes.** Every LLM output is schema-constrained at generation time, validated semantically after, repaired deterministically where a rule is mechanical, and replaced by a deterministic fallback when it cannot be trusted. **Facts shown on screen (numbers, dates, quoted words) must be traceable to the narration.** The model may choose *how* to show something, never *what is true*.

---

## 1. Backend

```python
class LLMBackend(Protocol):
    def generate_json(self, *, stage: str, system: str, user: str,
                      schema: dict, attempt: int) -> dict: ...
```

**`OllamaBackend`** (the only MVP backend):

| Setting | Value |
|---|---|
| Endpoint | `POST http://127.0.0.1:11434/api/chat` |
| `model` | **`gemma4:26b`** (`PLANNER_MODEL`) |
| `format` | the stage's JSON Schema (Ollama structured outputs) |
| `think` | `false` |
| `stream` | `false` |
| `keep_alive` | `"15m"` |
| `options.temperature` | **0.3** |
| `options.seed` | **7 + attempt** (attempt 0, 1, 2) |
| `options.num_ctx` | **16384** |
| `options.num_predict` | **2048** |
| HTTP timeout | **300 s** |

The response's `message.content` is parsed with `json.loads`. A parse failure counts as a failed attempt, never a crash.

**Error classification (added September 25, 2026).** `DependencyMissing` (exit 4) is raised **only** for a connection failure, or for a **non-200** response whose error body names a missing model. A 200 response is never inspected for words like "not found": the first implementation did that, so any caption containing "not found" crashed the job as a "missing model".

**Images and per-call output caps (added September 25, 2026).** `generate_json` and `run_with_retries` accept `images: list[bytes] | None` (PNG bytes, sent base64 in the user message's `images` field) and `num_predict: int | None` (overrides the default 2048 for that call). The cache key includes each image's **SHA-256**, never the base64 text, plus the effective `num_predict`. The text check (`design_visual_direction.md` §7.1) uses both; the critic (§11) uses `num_predict` 256. Because LLM-facing schemas carry no length limits, **`num_predict` is the only thing that bounds a free-text field's length.** A call that asks for a short answer must set it.

**Every planner LLM call goes through `run_with_retries`** (voice, bible, segment, select, props, critic, text_check). No stage may call `generate_json` directly. `run_with_retries` is the only place that converts parse failures, validation failures and truncated JSON into retries, and then into the stage's deterministic fallback. Two stages that bypassed it (select, props) crashed the storyboard stage on a single malformed reply.

**LLM-facing schemas carry no length constraints (added September 25, 2026).** The schema passed as `format` is the Pydantic schema with **every `maxLength`, `minLength`, `maxItems`, `minItems` and `pattern` removed**; `enum`, `type`, `required` and `additionalProperties` stay. Limits are stated in the prompt instead, and enforced afterwards by Pydantic and the validators, with the retry message naming the field and its limit (`props.caption: 61 characters, limit 48 — rewrite it shorter as a complete phrase`). **Why:** Ollama's constrained decoding enforces `maxLength` by force-closing the string at the limit. It does not make the model write something shorter. Wave A's storyboards had **34 of 701 strings cut mid-word** ("Rescuers wade through waist-", "Modern Era ("), all of which passed validation. That is also why the planner eval reported a 0.0% fallback rate: truncation made every answer valid.

**Response cache.** Key = SHA-256 of the canonical JSON (sorted keys, no whitespace) of `{model, messages, format, options, think}`. Stored at `cache/llm/<key>.json` (`{"request": …, "response": …, "elapsed_ms": …}`). Cache hits are counted in `plan_report.json`. `--no-llm-cache` bypasses reads but still writes. **The cache is what makes re-runs and tests deterministic.** The second run of the same job with a warm cache must produce byte-identical `bible.json`, `beats.json` and `storyboard.json`.

**Retry protocol (every stage):** up to **3 attempts** (0, 1, 2). After a failed attempt, append the model's previous output as an `assistant` message and a `user` message:

```
Your previous JSON was rejected:
- <error 1>
- <error 2>
(at most 20 lines)
Return corrected JSON only.
```

`design_system_architecture.md` §8 names `qwen3.6:35b` as the escalation candidate. **Switching models is not an agent decision.** If `gemma4:26b` fails the bars in §9, the agent re-runs the eval with `qwen3.6:35b`, records both result sets, and files the choice for the human in `ongoing_general_errors.md`.

**Prompts are data.** They live as Markdown in `src/animated_infographics/planner/prompts/` (`voice.md`, `bible.md`, `segment.md`, `select.md`, `props.md`) with `{placeholders}` filled by `str.format_map`. Prompt text changes are reviewed like code, and every prompt change re-runs the planner eval (§9).

---

## 2. Stage 1: Bible (`bible.json`)

**Input:** the full transcript as numbered sentences (`[3] Twenty-one people died…`), plus the title if known, plus `voice.json.narrator_gender` when it is `female` or `male` (text input only; §10). The prompt states it as a fact about the narrator, to be used for the narrator's avatar.

**`bible.md` must instruct, in substance:**
- `cast` = people, animals or **groups** that act, speak or are acted upon ("the soldiers", "the emus"). A first-person narrator is **one** cast member with `is_narrator: true` and `name: "Me"`.
- `places` = named locations that matter to the story. `kind: "real"` for real places with their **modern** country's ISO-3166 alpha-3 code; give `lat`/`lon` only if certain, otherwise null. Fictional or unnamed places are `kind: "fictional"` with null geo.
- `set_pieces` = up to 3 concrete, visual objects or moments worth an illustration (the tank, the machine gun, the wedding cake).
- `visual_description` describes appearance only: no names of real people, no text, no logos.
- Avatars: plausible for the character and era (historical soldiers → `military_cap` or `helmet`; royalty → `crown`).
- Budgets: ≤ 8 cast, ≤ 4 places, ≤ 3 set pieces; `color_slot` unique.

**Schema-level constraints:** ids as enums of the allowed patterns; icon fields as the icon allow-list enum; all length limits as `maxLength`.

**Deterministic post-processing (repairs, not retries):**
1. Truncate lists to budget (keep first N).
2. Duplicate `color_slot` → reassign the later member to the lowest free slot.
3. More than one `is_narrator` → keep the first, set the rest false.
4. **Geo resolution** (`planner/geo.py`) for every `kind: "real"` place:
   - Normalise (casefold, strip diacritics via NFKD) and match against GeoNames `cities15000` `name`, `asciiname` and every comma-separated `alternatenames` entry. Candidates in the place's `country_iso3` (via `countryInfo.txt` ISO→ISO3) are preferred; among those, the highest population wins. A match sets `lat`/`lon` from GeoNames and `geo_source: "gazetteer"`.
   - No gazetteer match but the LLM gave coordinates: accept **only if** they fall inside `data/geo/country_bboxes.json[country_iso3]` expanded by **0.5°** on every side → `geo_source: "llm"`. Otherwise null them → `geo_source: "none"`.
   - `kind: "fictional"` → geo null, `geo_source: "none"`.
   - *Accepted equivalent (September 25, 2026):* the bbox check handles countries whose bbox crosses the antimeridian (USA, RUS, NZL, KIR), where `minLon > maxLon`. Keep it.
5. **Narrator avatar consistency:** if `voice.json.narrator_gender == "female"` and the bible has an `is_narrator` member, set that member's `avatar.facial_hair = "none"`. A female voice over a bearded avatar would contradict itself on screen. No other avatar field is constrained, and nothing is constrained for `male` or `unknown`.

**Fallback** after 3 failed attempts: `{title: <title or first 60 chars of sentence 0>, logline: <first 140 chars of the transcript>, genre: "other", cast: [], places: [], set_pieces: []}`. The pipeline continues; the eval counts it.

---

## 3. Stage 2: Segment (`beats.json`)

**Input:** numbered sentences, each with its duration in ms and paragraph index.

**Output schema:** `{"groups": [[int, …], …]}`, a list of groups of sentence indices.

**Prompt guidance:** one idea per group; aim for **2.5–6 s** per group; do not merge across a paragraph boundary unless a sentence is under 1.5 s; the title sentence is always alone.

**Validation:** the groups must be an **exact ordered partition** of `0..n_sentences-1` (every index once, ascending, groups contiguous). Otherwise it is a failed attempt.

**Fallback:** one group per sentence. Then the deterministic beat constraints (`design_audio_and_timing.md` §7) run **in every case**. The LLM only proposes the grouping; merge and split rules are code.

---

## 4. Stage 3: Template selection

Beat 0 is **always `title_card`** and is not sent to the LLM.

**Allowed templates per job** (computed before prompting; the schema's `enum` contains only these):

| Template | Allowed only if |
|---|---|
| `character_intro`, `emotion_beat`, `dialogue` | `cast` has ≥ 1 member |
| `relationship_map` | `cast` has ≥ 2 members |
| `location` | `places` non-empty |
| `set_piece` | `set_pieces` non-empty |
| `map_focus` | some place has non-null `lat`/`lon` |
| `title_card` | never offered (beat 0 only) |
| all others | always |

**Windows:** beats `1..n-1` in windows of **6**. Each request carries: the compact bible (ids, names, roles, place names, set-piece names), the window's beat texts with indices, the **previous 2 beats' final choices**, and the template menu (name + `use_when` from the registry, one line each).

**Output schema:** `{"choices": [{"beat_i": int, "primary": <enum>, "alternate": <enum>}]}`, exactly one choice per beat in the window, `primary != alternate`.

**`select.md` must convey these mappings:**
spoken exchange → `dialogue`; texts/messages → `text_thread`; a person's first real appearance → `character_intro`; a reaction or feeling → `emotion_beat`; how people relate → `relationship_map`; a specific number → `stat_callout`; a sequence of dated events → `timeline`; a journey or where something is → `map_focus`; arriving somewhere or setting a scene → `location`; a key object or moment → `set_piece`; A-versus-B → `comparison`; X led to Y → `cause_effect`; a set of 2–4 things → `icon_list`; a twist or punchline → `reveal`; a line worth emphasising → `kinetic_quote`.

**Deterministic rule pass** over the whole video, in order. Each repair is logged in `plan_report.json.rule_repairs`:

| Rule | Condition | Repair |
|---|---|---|
| **R1** | Scene 0 is not `title_card` / a later scene is `title_card` | Force / replace with alternate |
| **R2** | Two consecutive scenes share a template (except `dialogue`, `text_thread`) | Second → its alternate; if that also repeats → `kinetic_quote` |
| **R3** | `character_intro` for the same `cast_id` more than once | *(applied after props, §5)* later ones → alternate |
| **R4** | `reveal` more than **2** times | Later ones → alternate |
| **R5** | `kinetic_quote` more than `ceil(0.30 × n_scenes)` times (counting only LLM primaries) | Excess (latest first) → alternate if it is not `kinetic_quote` |

**Fallback** for a window after 3 failed attempts: every beat in it gets `primary = kinetic_quote`, `alternate = kinetic_quote`.

---

## 5. Stage 4: Props (one request per scene)

**Input:** the compact bible; this beat's text; the previous and next beat texts (context only, labelled as such); the template's `use_when`, `writing_rules` and field limits.

**Output schema:** the template's props JSON Schema, **with reference fields narrowed to enums of the ids that exist in this bible** (`cast_id` → `["c1","c2"]`). Reference errors are thus impossible at generation time. Validators still re-check them for hand edits.

**`props.md` must state:** use only facts in *this beat's* text or the bible; never invent numbers, dates, names or quotes; stay within the length limits; write short, concrete, on-screen language (not sentences copied wholesale, except where a template requires a verbatim span); JSON only.

**The fallback ladder for each scene:**

```
primary template:  attempt 0 → validate → attempt 1 → validate → attempt 2 → validate
      ↓ still invalid
alternate template: same 3 attempts
      ↓ still invalid
kinetic_quote built deterministically (never fails)      ← fallback_level 2
```

**Deterministic `kinetic_quote`:** `text` = the beat text if ≤ 90 characters, else the beat text cut at the last word boundary at or before character 89, followed by `…`; `emphasis = []`; `attribution_cast_id = null`. It always passes the verbatim validator by construction.

`title_card` props for scene 0 are **not** LLM-generated: `title` = `bible.title`; `subtitle` = null; `icon` = the first set piece's icon, else the first place's icon, else null.

---

## 6. Validators (`planner/validate.py`)

The **same functions** run on LLM output (inside the ladder) and on human edits (inside `preview`). A validator returns a list of human-readable error strings addressed by JSON path. Empty means valid.

1. **Schema:** Pydantic validation of the props model.
2. **References:** every `cast_id`, `place_id`, `set_piece_id`, and every relationship edge endpoint exists; `map_focus` markers' places have non-null geo.
3. **Text fit (§7).**
4. **Grounding (§8)** where the template declares it (`design_templates.md`).
5. **Template-specific rules** listed per template in `design_templates.md` (e.g. `highlight_index` in range, edge endpoints distinct).
6. **Meaning rules that code can decide (Issue 5 → Option A, part 1; selected September 25, 2026):**
   - `stat_callout.suffix` must not contain `$`, `£` or `€`. Error: `props.suffix: currency symbols belong in prefix`.
   - `location.era_label` may contain the whole word "ago" (casefolded) only if the whole transcript does. Error: `props.era_label: "ago" is not in the narration`.
   - `timeline.events[].date_label`: see §8 (Issue 4).
7. **Text completeness (added September 25, 2026)**, for every free-text string field (not ids, enums, `prefix`, or `date_label`/`era_label`):
   - **Repair (not an error):** runs of whitespace, including `\n`, collapse to one space; strip the ends.
   - **Errors:** the string contains no letter or digit (`"..."`, `"—"`); it ends with `-`, `(`, `[`, `,`, `:` or `/`; its `(`/`)`, `[`/`]` or `"` characters are unbalanced; its last word is a truncation fragment (a single **lowercase** letter other than `a`, e.g. "…crowds at p"; a capital like "Plan B" is legitimate). Error format: `props.caption: looks cut off ("…crowds at p")`.

---

## 7. Text fit (`textfit.py`)

For every text field bound to a registry `TextSlot`: measure with **Pillow `ImageFont.truetype(<the exact TTF the renderer uses>, size_min)`**. Greedy word-wrap at `box_width × 0.95` (the 5% margin absorbs Pillow-vs-Chrome shaping differences). The text **fits** iff the wrapped line count ≤ `max_lines`. A single word wider than the box on its own does not fit. Error format: `props.caption: does not fit (4 lines at 32px, max 3)`.

The renderer independently detects overflow in the DOM (`design_rendering.md` §6). The two checks are deliberately redundant: Pillow catches it before review, and the DOM check catches a Pillow/Chrome disagreement.

---

## 8. Grounding (`planner/grounding.py`)

**Normalisation** `norm(s)`: casefold; curly quotes → straight; replace every character that is not a letter, digit, apostrophe or space with a space; collapse whitespace; strip.

**Number extraction** `numbers(s)` returns a multiset of floats:
- Digit numbers: `\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?`, commas removed. If followed by whitespace plus `thousand|million|billion` (case-insensitive), multiply by 1e3/1e6/1e9 **and also** keep the unscaled value.
- Spelled numbers: maximal runs of `zero…nineteen`, `twenty…ninety` (hyphenated compounds like `twenty-one` included), `hundred`, `thousand`, `million`, `billion`, with an optional leading `a` (`a thousand` = 1000), parsed with standard English place-value rules.
- `%` is stripped (the value is the number).
- **A scale word is never a number on its own (added September 25, 2026).** `thousand`/`million`/`billion` count as a spelled number only as part of a spelled run (`two million`) or with a leading `a` (`a million`). After a digit number (`2.3 million`) they only scale it. The first implementation extracted a stray `1,000,000` from "2.3 million gallons", so a wrong on-screen "1 million" would have been accepted as grounded.

**Rules:**

| Template field | Grounded iff |
|---|---|
| `stat_callout`: `N = value × scale(display_scale)` | some `n ∈ numbers(beat.text)` with `|n − N| ≤ 0.005 × max(|N|, 1)` |
| `location.era_label` | every maximal digit run in the label appears as a digit run in the **whole transcript**, or equals a spelled number found there |
| `timeline.events[].date_label` (**Issue 4 → Option A, selected September 25, 2026**) | **each** label either (a) contains ≥ 1 digit run, and every digit run is grounded as above; or (b) after normalisation (casefold, collapse whitespace, strip trailing `. , ! :`) is exactly one of: `today`, `now`, `present day`, `that night`, `that weekend`, `the next day`, `days later`, `weeks later`, `months later`, `years later`, `last spring`, `last summer`, `last fall`, `last winter`, `last year`, `earlier`, `later`. **And** the normalised labels are pairwise distinct. **And** the four-digit years (`\b(1[0-9]{3}\|20[0-9]{2})\b`, first per label) are non-decreasing in event order. |
| `kinetic_quote.text` | `norm(text without a trailing "…")` is a substring of `norm(beat.text)` **starting and ending at word boundaries** |
| `kinetic_quote.emphasis[]` | each `norm(word)` is a whole word of `norm(text)` |

**Why grounding is a hard gate:** a local model will cheerfully turn "about 150 were injured" into "1,500 injured". The error is invisible to a quick human skim and permanent once published. Code can decide groundedness exactly, so code does, and a wrong number never reaches review.

---

## 9. Planner eval (`evals/planner.py`)

`uv run python -m animated_infographics.evals.planner` runs voice → bible → storyboard on **all four** text fixtures (`fixtures/scripts/`) with `--no-llm-cache` and writes `docs/evals/planner_<YYYY-MM-DD>.md` (committed). The report contains, per fixture: the voice decision (`voice`, `reason`, `evidence`) and whether it matches `fixtures/expected/<name>.json`; scene count; distinct templates; `fallback_level` histogram; rule repairs by rule; validator error histogram (by validator and template); LLM calls; wall time.

**Bars (each fixture):**

| Metric | Bar |
|---|---|
| Scenes at `fallback_level` 2 | ≤ **15%** |
| Distinct templates | ≥ **5** (`molasses_flood`), ≥ **7** (`emu_war`, `story_recipe_box`, `story_room_12`) |
| Grounding / reference / fit violations in the **final** storyboard | **0**, re-verified by running §6 over the saved `storyboard.json` as an independent pass |
| Planner wall time for `story_recipe_box`, the longest fixture (cold LLM cache, model already loaded) | ≤ **240 s** |
| Voice decision matches `fixtures/expected/<name>.json` (`voice` and `reason`) | **4 of 4** fixtures |
| Critic regression set (§11) | **4 of 4** cases classified as expected |
| Critic cost | reported per fixture: critic calls, mismatches, props changed (no bar; the cold budget run bounds the time) |

A bar that fails is **filed, not tuned away**. Do not raise the fallback threshold, drop a validator, or loosen grounding to pass. Prompt changes are legitimate; each one re-runs the full eval and the report records the prompt files' SHA-256.

---

## 10. Stage 0: Narrator voice selection (`voice.json`; text input only)

Runs after `ingest` and **before** `narrate`, because the voice must be known before any audio exists. Audio inputs skip this stage and have no `voice.json`.

**The decision (user, September 24, 2026, Issue 1), verbatim:** *"Proceed with Option A and B. If the story from reddit seems to be from a female's perspective then use af_heart, else use am_michael."*

**How it is interpreted (recorded so it can be corrected through a new issue, not by an agent):**
- "A story from Reddit" = a **first-person personal story**, the Reddit-story form. Third-person stories (all history) fall in the "else" branch → `am_michael`.
- "From a female's perspective" = the **narrator explicitly identifies as female in the text**. Gender is **never** inferred from occupation, interests, emotions, the gender of a partner, or how other characters are described.
- The rule is **deliberately asymmetric.** `am_michael` is the default; `af_heart` requires positive, checkable evidence. When in doubt, the answer is `am_michael`. A wrong female voice is the more jarring error, and this is the direction the user's "else" already points.

| Constant | Value |
|---|---|
| `VOICE_DEFAULT` | **`am_michael`** |
| `VOICE_FEMALE_NARRATOR` | **`af_heart`** |
| `INSTALLED_VOICES` | `{"af_heart", "am_michael"}`: the only voices `setup.sh` downloads; `--voice` accepts nothing else (exit 2), because fetching another voice at runtime would break the local-only policy |
| `FIRST_PERSON_TOKENS` | `{i, i'm, i've, i'd, i'll, me, my, mine, myself}` (casefolded) |
| `FIRST_PERSON_RATE_MIN` | **2.0** first-person tokens per 100 words |

**Algorithm (`planner/voice.py`), in order:**

1. **Flag override.** `--voice` given → `voice = <flag>`, `source: "flag"`, `reason: "flag"`; every analysis field `null`; **no LLM call.** Stop.
2. **Perspective (deterministic).** Text = title + body with every double-quoted span (`"…"`, after curly-quote normalisation) removed, because quoted speech contains *other people's* "I". Tokens = `re.findall(r"[A-Za-z']+", text)`, casefolded. `first_person_rate = round(100 × |tokens ∈ FIRST_PERSON_TOKENS| / |tokens|, 2)`. `perspective = "first_person"` iff `first_person_rate ≥ 2.0`, else `"third_person"`. **Third person → `voice = am_michael`, `reason: "third_person"`, `narrator_gender: "unknown"`, no LLM call. Stop.**
   *Measured at design time:* `story_recipe_box` 5.45 · `story_room_12` 3.67 · `molasses_flood` 0.00 · `emu_war` 0.00.
3. **Reddit gender tag (deterministic).** The first match of

   ```
   \b(I|I'm|me|my|myself)\s*[\(\[]\s*(?:(\d{1,2})\s*([FfMm])|([FfMm])\s*(\d{1,2}))\s*[\)\]]
   ```

   (case-insensitive) in the **unmodified** title + body. `F` → `female`, `M` → `male`; `evidence` = the matched text; `reason: "tag"`; no LLM call. The first-person prefix is what makes the tag the *narrator's*: `My (34M) wife (33F)` → male; `My sister (22F) said` → no narrator tag. Any other tag letter → no match.
4. **LLM (first person, no tag).** One request via §1 with schema `{"narrator_gender": "female"|"male"|"unknown", "evidence": string|null (maxLength 160)}`. `prompts/voice.md` must say, in substance: decide the first-person narrator's gender **only** from words where the narrator identifies themself ("I'm a first-time mom", "As a dad of three, I…", "Being the only daughter, I…"); `evidence` must be copied exactly from the text **and include the narrator's own "I"/"I'm"**; anything weaker → `"unknown"` with `evidence: null`; never infer from occupation, hobbies, emotions, a partner's gender, or other characters' pronouns.
   **Validation** (a failure is a failed attempt under the §1 retry protocol; after 3 failed attempts → `narrator_gender: "unknown"`, `reason: "no_evidence"`):
   - a. `unknown` with non-null evidence → evidence normalised to `null` (a repair, not an error).
   - b. `female`/`male` needs non-null `evidence` that is a **verbatim span** of the text (§8's word-boundary substring test on `norm()`).
   - c. `evidence` must contain a **self-identification** of the claimed gender, by one of two forms. Split `evidence` into clauses on `. ! ? ; :`; tokenise each clause with `[A-Za-z0-9'\-éÉ]+`, **keeping the original case**. `SUBJ = {"I", "I'm", "I've", "I'd"}` (case-sensitive).
     - **Form A (copula):** an opener `I'm`, or `I` followed by `am`/`was`/`became`, or `I've` followed by `been`. The candidate is any of the **next 4 tokens** after the opener. Example: "I'm a first-time **mom**", "I was a young **bride**".
     - **Form B (as/being):** a token `as`/`being` (any case). The candidate is any of the **next 4 tokens**, **and** a `SUBJ` token must occur within the 4 tokens after the candidate. Example: "As the only **granddaughter**, I…", "As a **dad** of three, I…".
     - **A candidate counts only if all four hold:**
       1. it is written **in lowercase** (so "Grandma Rose", "Mom said" and "the Queen" do not count; kinship words used as names are capitalised);
       2. it, or its part before the first hyphen (`mother-in-law` → `mother`), is in the claimed gender's lexicon;
       3. the token before it is **not** a possessive (`my our your his her their its`, any case) and does not end in `'s`;
       4. the token after it does **not** start with an uppercase letter unless it is in `SUBJ` (so "sister Maya" is a title before a name, not a self-description).

     This is deliberately narrow. Self-identification has a recognisable grammar; a gendered word that merely sits near an "I" ("a woman walked in holding a suitcase I recognized") is someone else.
     - `FEMALE_TOKENS` = {woman, women, girl, wife, mother, mom, mum, mommy, daughter, sister, aunt, niece, girlfriend, bride, lady, fiancee, fiancée, grandmother, grandma, granddaughter, queen, princess, stepmother, stepmom, stepdaughter, female}
     - `MALE_TOKENS` = {man, men, guy, boy, husband, father, dad, daddy, son, brother, uncle, nephew, boyfriend, groom, gentleman, fiance, fiancé, grandfather, grandpa, grandson, king, prince, stepfather, stepdad, stepson, male}
   - *Measured at design time (23 cases, all as expected; these are the required unit cases, and the four marked † each isolate one sub-rule for falsification):*

     | Evidence | Claimed | Result |
     |---|---|---|
     | `I'm a first-time mom` | female | ✓ `mom` |
     | `As the only granddaughter, I got Grandma Rose's recipe box` | female | ✓ `granddaughter` |
     | `Being the oldest daughter, I` | female | ✓ `daughter` |
     | `I'm a 30-year-old woman` | female | ✓ `woman` |
     | `I was a young bride` | female | ✓ `bride` |
     | `She called me selfish, and as a sister I felt awful` | female | ✓ `sister` |
     | `As a dad of three, I never thought` | male | ✓ `dad` |
     | `I got Grandma Rose's recipe box` | female | ✗ (no form; capitalised) |
     | `My sister Maya` | female | ✗ |
     | `my mother-in-law, Linda` | female | ✗ |
     | `Mom said family doesn't send invoices` | female | ✗ |
     | `I'm her daughter` † | female | ✗ (possessive, rule 3: accepted false negative) |
     | `I'm Maya's sister` | female | ✗ |
     | `I'm the bride's cousin` | female | ✗ |
     | `I am the Queen of this house` † | female | ✗ (capitalised, rule 1) |
     | `I'm sister Maya's favourite` † | female | ✗ (title before a name, rule 4) |
     | `She treated me as a sister for years` † | female | ✗ (Form B without a following `I`) |
     | `a woman walked in holding a small suitcase I recognized` | female | ✗ (no form) |
     | `When I met the bride at the door` | female | ✗ (no form) |
     | `texted my wife to make sure she was still awake` | female / male | ✗ / ✗ |
     | `I did crosswords, knitted scarves nobody asked for` | female | ✗ |
     | `As my sister Maya said, I was wrong` | female | ✗ |
     | `My brother Danny got her house` | male | ✗ |

     Every ✗ that is actually true of a narrator (e.g. `I'm her daughter`) is an **accepted false negative**: it falls back to `am_michael`, which is the safe direction of the asymmetry.
   - `reason`: `"llm"` if `female`/`male` was accepted, `"no_evidence"` otherwise.
5. **Decide:** `voice = af_heart` **iff** `perspective == "first_person"` **and** `narrator_gender == "female"`; otherwise `am_michael`. That makes `male` and `unknown` behave identically today. They are recorded separately because the bible (§2 repair 5) and any future multi-voice work (D3) can use the difference.

**`voice.json`:**

```json
{"schema_version": 1, "voice": "af_heart", "source": "auto", "reason": "llm",
 "perspective": "first_person", "first_person_rate": 5.45,
 "narrator_gender": "female", "evidence": "As the only granddaughter, I got Grandma Rose's recipe box"}
```

`source` ∈ `auto` · `flag`; `reason` ∈ `flag` · `third_person` · `tag` · `llm` · `no_evidence`; `perspective` ∈ `first_person` · `third_person` · null (flag only); `narrator_gender` ∈ `female` · `male` · `unknown` · null (flag only).

**Visibility at the review gate:** `preview/storyboard.md` opens with one line: `Voice: af_heart — auto (first person, female narrator: "As the only granddaughter, I got…")`, or `Voice: am_michael — auto (third person)`, `… auto (first person, no self-identification found)`, `… set by --voice`. A reviewer who disagrees starts a new job with `--voice`. The voice cannot be changed inside a job, because every word timing, beat and scene depends on it.

**Expected on the fixtures** (`fixtures/expected/*.json`, checked by the planner eval and the slow tests):

| Fixture | `perspective` | `narrator_gender` | `reason` | `voice` |
|---|---|---|---|---|
| `molasses_flood` | third_person | unknown | third_person | am_michael |
| `emu_war` | third_person | unknown | third_person | am_michael |
| `story_room_12` | first_person | unknown | no_evidence | am_michael |
| `story_recipe_box` | first_person | female | llm | af_heart |

`story_room_12` is the **inference trap**: the narrator knits and texts "my wife", and "a woman walked in" is someone else. Nothing in the text is a self-identification, so any guess, female *or* male, must be rejected by rule c. `story_recipe_box` has one genuine self-identification ("As the only granddaughter, I got…") surrounded by gendered words about other people ("Grandma Rose", "My mom", "his mother").

---

## 11. The people-scene critic (Issue 5 → Option A, part 2; selected September 25, 2026)

**The user's selection:** *"Option A."* Part 1 (the deterministic rules) is §6 item 6. Part 2 is this section: one extra local LLM call per *people* scene, asking **blind** who says or feels what, and one props retry when that reading disagrees with the props.

**Which scenes:** `dialogue`, `text_thread`, `emotion_beat`, and `kinetic_quote` **with** a non-null `attribution_cast_id`. Never the deterministic fallback scenes.

**When:** inside props planning, after a candidate scene has passed `validate_scene` (fallback level 0 or 1), before it is accepted.

**Call:** `run_with_retries(stage="critic", num_predict=256)`, `temperature` 0.
- **System:** `You check who says or feels what in a story beat. Answer only from the text. Output JSON matching the schema.`
- **User:** the cast list (`- <id>: <name> (<role>)`, plus ` [narrator]` for the narrator), the previous beat (labelled "context only"), this beat, the next beat (labelled "context only"), and the template's question.
- **Blind:** the question gives the scene's *texts* but **never** the proposed speaker, sender, tone or emotion.

| Template | Question (the quoted texts come from the props) | Schema |
|---|---|---|
| `kinetic_quote` | `Who wrote or said these quoted words: "<text>" Answer a cast id, "narration" if they are the narrator telling the story, or "unknown".` | `{"speaker": <cast ids> \| "narration" \| "unknown"}` |
| `dialogue` | `The scene shows these lines in order: 1. "<text>" 2. "<text>" … For each line, who says it (cast id or "unknown") and in what tone?` | `{"lines": [{"speaker": <cast ids> \| "unknown", "tone": neutral\|angry\|happy\|sad\|shocked\|sarcastic\|unknown}]}`, the same length as `props.lines` (a length mismatch is a failed attempt) |
| `text_thread` | `The phone belongs to the narrator. Messages in order: 1. "<text>" … For each, was it sent by the narrator ("me") or the other person ("them")?` | `{"messages": [{"sender": "me"\|"them"\|"unknown"}]}`, the same length as `props.messages` |
| `emotion_beat` | `Which cast member feels something in this beat, and what is the main feeling?` | `{"cast_id": <cast ids> \| "unknown", "emotion": happy\|sad\|angry\|shocked\|confused\|smug\|nervous\|unknown}` |

**Mismatch rules (deterministic, `planner/critic.py`):**
- **Who** (speaker, sender, `cast_id`): a mismatch iff the critic's value is not `unknown` **and** differs from the props. For `kinetic_quote`, `narration` agrees only with the narrator's cast id. A speaker the critic cannot resolve (`unknown`) is **never** a mismatch.
- **Dialogue tone:** a mismatch iff (the critic's tone is not `unknown` and differs from the props) **or** (the critic's tone is `unknown` and the props' tone is not `neutral`). A strong tone the text does not show is an error.
- **Emotion** (`emotion_beat`): a mismatch iff the critic's value is not `unknown` and differs from the props.

**On mismatch:** exactly **one** props retry for the same template, with an added user message:

```
A second, independent reading of this beat disagrees:
- <field>: you said <x>; the reading says <y>
Fix the props if that reading fits the beat text better; otherwise keep yours.
```

The retry result must pass `validate_scene`. If it does, it replaces the scene, **with no second critic call** (no loops). If it does not, the original validated scene stands. If the critic call fails entirely, the scene is accepted with critic status `unavailable`.

**Recorded** in `plan_report.json` per scene: `critic: {"status": "not_applicable"|"agree"|"mismatch_retried"|"unavailable", "mismatches": ["lines[0].tone: angry vs unknown"], "changed": bool}` (`design_data_contracts.md` §6).

**Measured September 25, 2026** with `gemma4:26b`, seeds 7, 8 and 9, all consistent. These four cases are the **critic regression set**, run as slow tests with the cast `c1 Me (narrator)`, `c2 Danny`, `c3 Walt`, `c4 Deb`:

| Case (from Wave A's real output) | Props | Critic said | Rule result | Expected |
|---|---|---|---|---|
| A: Danny's text "Who is Walter Lindqvist…" as a `kinetic_quote` | attribution `c1` | `c2` | mismatch | mismatch ✓ |
| B: "Rose?" as a `dialogue` line | `c1`, tone `angry` | `c1`, `unknown` | mismatch (tone) | mismatch ✓ |
| B′: the same line with tone `neutral` | `c1`, `neutral` | `c1`, `unknown` | agree | agree ✓ |
| C: "I've been waiting for someone to call about the pie." | attribution `c3` | `unknown` | agree | agree ✓ |

Latency was ~0.5 s per call. Case C is why "unknown" must never count as a mismatch for *who*: the critic could not resolve "he said" from the beat alone, and the props were right.

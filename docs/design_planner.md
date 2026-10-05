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
spoken exchange → `dialogue`; texts/messages → `text_thread`; a person's first real appearance → `character_intro`; a reaction or feeling → `emotion_beat`; how people relate → `relationship_map`; a specific number → `stat_callout`; a sequence of dated events → `timeline`; a journey or where something is → `map_focus`; arriving somewhere or setting a scene → `location`; a key object or moment → `set_piece`; A-versus-B → `comparison`; X led to Y → `cause_effect`; a set of 2–3 things → `icon_list` (2–4 until September 27, 2026); a twist or punchline → `reveal`; a line worth emphasising → `kinetic_quote`.

**Deterministic rule pass** over the whole video, in order. Each repair is logged in `plan_report.json.rule_repairs`:

| Rule | Condition | Repair |
|---|---|---|
| **R1** | Scene 0 is not `title_card` / a later scene is `title_card` | Force / replace with alternate |
| **R2** | Two consecutive scenes share a template (except `dialogue`, `text_thread`) | Second → its alternate; if that also repeats → `kinetic_quote` |
| **R3** | `character_intro` for the same `cast_id` more than once | *(applied after props, §5)* later ones → alternate |
| **R4** | `reveal` more than **2** times | Later ones → alternate |
| **R5** | `kinetic_quote` more than `ceil(0.30 × n_scenes)` times (counting only LLM primaries) | Excess (latest first) → alternate if it is not `kinetic_quote` |
| **R6** (added September 27, 2026) | More than one `timeline`, or more than one `comparison`, in the video | Later ones → alternate if it is neither the same template nor `title_card`, else `kinetic_quote` |
| **R7** (added September 27, 2026) | Two worded scenes in a row, then a **replaceable** scene whose beat names a picture target | That scene → a deterministic **picture** (below) |

**Rule order (revised September 27, 2026):** R1, **R6**, R2, R4, R5, **R7**, then R3 after props. R6 runs before R2 so that R2 removes any consecutive duplicate R6 creates. R7 runs last and never creates one.

**R7, the reaction-shot rhythm (Issue 7 → Option A).** The template classes (picture, replaceable, kept) are in `design_templates.md` §5.4.
```
run = 1                                   # scene 0 (title_card) counts as worded
for i in 1 .. n-1:
    t = choices[i].primary
    if run >= 2 and t in REPLACEABLE and not QUOTED.search(beats[i].text):   # quoted speech: added October 3, 2026
        target = rhythm_target(beats[i].text, bible,
                               prev=choices[i-1].primary,
                               next=choices[i+1].primary if i+1 < n else None)
        if target is not None:
            choices[i] = Choice(beat_i=i, primary=target.template, alternate=t, rhythm_id=target.id)
            log RuleRepair(rule="R7", scene=f"s{i:03d}", from=t, to=target.template)
    run = 0 if choices[i].primary in PICTURE else run + 1
```
`rhythm_target` returns the **first** of these candidates, in this priority order, whose template differs from both `prev` and `next`, or `None`:
1. **`emotion_beat`** (only if the bible has cast):
   - **the narrator**, if the bible has one and the beat text, **with quoted spans removed** (`"[^"]*"` and `“[^”]*”`), matches `\b(i|me|my|mine|myself|we|us|our)\b` case-insensitively;
   - otherwise **the non-narrator cast member named earliest** in the beat.
2. **`set_piece`**: the set piece named earliest.
3. **`location`**: the place named earliest.

**"Named":**
- A name's tokens are `re.findall(r"[a-z0-9]+", name.casefold())` of length ≥ 3, excluding `the`, `and`, `for`, `with` and `from`.
- A name is named at the smallest offset in the casefolded beat where any token matches `\b<token>(?:s|'s|’s)?\b`.
- Ties go to bible order.

**The picture is built deterministically in the props stage.** No LLM call, no critic call, `rationale: "rhythm picture"`, `fallback_level` 0:
- `emotion_beat` → `{cast_id, emotion: "neutral"}`, the **reaction shot**;
- `set_piece` → `{set_piece_id}`;
- `location` → `{place_id, era_label: null}`.

If it fails `validate_scene`, the scene goes through the normal ladder with its alternate (the replaced template) as the primary.

**Why deterministic, and why these exclusions (measured September 27, 2026, `gemma4:26b`):**
- Given the reaction-shot beats R7 picks, the props model invented feelings for plain beats: "smug" for "…I think I got the better deal.", "confused" for "I asked if he minded me using it.", and "angry" for "Meredith was impressed by his opponent."
- The blind critic's emotion readings were no steadier. Across 9 real beats its answers differed from the props in person or feeling on 6. Asked to prefer "neutral", it answered "neutral" on all 27 calls, which tells us nothing.
- A neutral face invents nothing, which is what the reaction shot is for.
- Quoted spans are removed before the first-person test, because Walt's line "I've been waiting for someone to call about the pie." would otherwise pick the narrator.
- Kept templates are never replaced (`design_templates.md` §5.4).
- **A beat that contains quoted speech or writing is never replaced** (`QUOTED` matches; added October 3, 2026). The quoted words are story content, not restated narration.
  - Measured in Wave D's final E2E: R7 replaced the `kinetic_quote` of Rose's note — "It was always yours. Give it to whoever comes asking.", the story's climax — with a neutral reaction shot of Grandma Rose. That was 2 of 10 R7 repairs across 26 Wave D jobs.
  - Case R7-b (Walt's line) is therefore no longer replaced either.
- The real cases are frozen in `tests/data/rhythm_cases.json` (R7-a…h; R7-h is Rose's note).

**Scope:** R6 and R7 are offline rules. Live presentations want timelines and repeated graphics (`design_future_live_and_video.md` §4).

**Fallback** for a window after 3 failed attempts: every beat in it gets `primary = kinetic_quote`, `alternate = kinetic_quote`.

---

## 5. Stage 4: Props (one request per scene)

**Input:** the compact bible; this beat's text; the previous and next beat texts (context only, labelled as such); the template's `use_when`, `writing_rules` and field limits.

**Output schema:** the template's props JSON Schema, **with reference fields narrowed to enums of the ids that exist in this bible** (`cast_id` → `["c1","c2"]`). Reference errors are thus impossible at generation time. Validators still re-check them for hand edits.

**`props.md` must state:** use only facts in *this beat's* text or the bible; never invent numbers, dates, names or quotes; stay within the length limits; write short, concrete, on-screen language (not sentences copied wholesale, except where a template requires a verbatim span); JSON only.

**Word budget in the props prompt (added September 27, 2026, Issue 7 → Option A).** In `prompts/props.md`, guidelines 3 and 4 become, verbatim:
```
3. Length: Stay within every word and item limit in the writing rules. Fewer words is better.
4. Style: The viewer hears the narration, so on-screen words must not repeat it. Write names, labels and numbers, not sentences. Do not copy sentences unless required by kinetic_quote.
```
Each template's registry `writing_rules` state its word caps and list maxima (`design_templates.md` §5.3); the exact strings were in the Wave D guide's item D2 and now live in the registry.

**Era stamps show a year from the narration, or nothing (added October 4, 2026).** In props planning, after text normalisation and before `validate_scene`, a `location`'s `era_label` is normalised deterministically, with no LLM call:
- if it contains a four-digit year (`\b(1[0-9]{3}|20[0-9]{2})s?\b`) that also appears in the transcript, it becomes that year token: "1919 Boston" → "1919", "1932 era" → "1932", "1960s" stays;
- otherwise it becomes `null`.

This applies to planner output only; human edits in `preview` are untouched.
- **Why:** the stamp is drawn rotated on the image, so its words must be right.
- **Measured** over all 358 location scenes since Wave A: only **4** stamps were already a bare narration year; **115** contained one ("1932 Era"); **228** had none, and were invented ("Present Day" for "Last spring" and "I drove up that weekend", "Modern Era" for a 1990s motel, "40 Years", "N/A").
- A retry-based rule was tried first, on 11 real scenes. It produced worse stamps ("Two days", "forty years") and failed the 1919 molasses location outright, so the rule is deterministic.

**Allowed icon names in the props prompt (added October 3, 2026).** For templates with an `icon` field (`stat_callout`, `icon_list`, `cause_effect`, `comparison`), the user message ends with this block, verbatim, followed by every name of the icon allow-list in its `contracts/icons.py` order, separated by `", "`:
```

# Icons
Every icon field must be one of these names. Pick the one that depicts the label; if none does and the field is optional, leave it out.
```
- **Why:** the prompt never showed the 157 allowed names. The model guessed a name, and the schema's `enum` snapped the guess to an allowed one. "Armchair", second in the list, became the most-used icon in every wave: 9% of icons in Wave A, 18% in Wave D's final run ("Machine Guns", "Trampled crops", "Farmers" and "986 emus killed" all showed an armchair).
- **Measured** October 3, 2026, by re-planning all 27 icon-bearing scenes of Wave D's final E2E with and without the block: Armchair **8 of 54 → 0 of 56** icons. Picks became depictions: "Rescuers" `Users`, "Trampled crops" `Plant`, "Machine Guns" `Bomb`, "deaths" `Skull`, "emus" `Bird`. The removed fields (`design_templates.md` §5.2) are no longer in the props models, so the schema cannot ask for them. The measured effect is in `design_templates.md` §5.5.

**Dialogue and text messages may paraphrase (Issue 6 → Option D; the user, September 27, 2026, after watching both story renders: *"I think the paraphrasing is fine."*).** `dialogue` lines and `text_thread` messages may paraphrase or dramatise what the beat reports, in every genre. Only `kinetic_quote` needs a verbatim span (§8). **Do not add a verbatim or word-overlap check to `dialogue` or `text_thread`.** *Who* says each line is still checked by the critic (§11).

**The fallback ladder for each scene:**

```
primary template:  attempt 0 → validate → attempt 1 → validate → attempt 2 → validate
      ↓ still invalid
alternate template: same 3 attempts
      ↓ still invalid
kinetic_quote built deterministically (never fails)      ← fallback_level 2
```

**Deterministic `kinetic_quote` (revised September 27, 2026, for the 12-word cap):**
1. Take the beat text's whitespace tokens up to and including the 12th word (a token with a letter or digit).
2. If the beat has more words, join them with single spaces and append `…`.
3. Then, if the result is longer than 90 characters, apply the old rule: cut at the last word boundary at or before character 89, followed by `…`.

`emphasis = []`; `attribution_cast_id = null`. It always passes the verbatim validator and the word cap by construction; a unit test proves both on a 30-word beat.

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
   - **A year is not a stat (added October 3, 2026).** It is an error when all of these hold:
     - a `stat_callout` has `decimals` 0 and `display_scale` `"none"`;
     - its `value` is an integer from 1000 to 2100;
     - the beat contains that number as a bare four-digit token: `(?<![\d,.])<value>(?![\d]|,\d)`.

     Error: `props.value: <value> is a year in this beat; a year belongs in a timeline or an era label, not a stat`.
     - **Measured:** Wave D's R6 demoted `story_room_12`'s second timeline to its alternate `stat_callout`, which rendered "She had died in 2016…" as **"2,016"** counting up from 0, under an armchair icon. Given a unit field, the model wrote "Year died" instead. That is the only year-like stat in every run since Wave A.
     - Counts from 1000 to 2100 written without a thousands separator are treated as years; the ladder then uses the alternate template.
   - **A day of a date is not a stat either (added October 4, 2026; the year rule above was too narrow).** It is an error when:
     - a `stat_callout` has `decimals` 0, `display_scale` `"none"` and an integer `value` v;
     - and the beat contains v as the day of a date: `\b(?:<month>)\.?\s+<v>(?:st|nd|rd|th)?\b` or `\b<v>(?:st|nd|rd|th)?\s+(?:of\s+)?(?:<month>)\b`, case-insensitive, where `<month>` is any full English month name.

     Error: `props.value: <v> is a day of a date in this beat; a date belongs in a timeline or an era label, not a stat`.
     - **Measured:** after the year rule blocked "2016", the model drew "She had died in 2016, and March 3rd was her birthday." as a big **3** with the unit "March" (Wave E's final run). "March 3rd" had already been drawn as "3" + "rd" in Wave A and Wave B.
     - With the rule, that scene failed all 3 attempts and fell to the deterministic quote of the sentence.
   - `timeline.events[].date_label`: see §8 (Issue 4).
7. **Text completeness (added September 25, 2026)**, for every free-text string field (not ids, enums, `prefix`, or `date_label`/`era_label`):
   - **Repair (not an error):** runs of whitespace, including `\n`, collapse to one space; strip the ends.
   - **Errors:** the string contains no letter or digit (`"..."`, `"—"`); it ends with `-`, `(`, `[`, `,`, `:` or `/`; its `(`/`)`, `[`/`]` or `"` characters are unbalanced; its last word is a truncation fragment (a single **lowercase** letter other than `a`, e.g. "…crowds at p"; a capital like "Plan B" is legitimate). Error format: `props.caption: looks cut off ("…crowds at p")`.
   - **No placeholders or instructions on screen (added October 4, 2026).** For every `WORD_CAPS` field:
     - a value matching `\bicon\s*:` (case-insensitive) is an error: `props.<path>: "<value>" is an instruction, not on-screen text — put icons only in icon fields`;
     - a value whose normalised form (`re.sub(r"[^\w/ ]", "", v).strip().casefold()`) is one of `not specified`, `unspecified`, `not mentioned`, `n/a`, `na`, `none`, `unknown`, `tbd`, `no data`, `not applicable` is an error: `props.<path>: "<value>" is a placeholder — show only what the beat says`.
     - **Measured** over all 9,080 on-screen strings of every E2E run since Wave A, the rule flags only real junk:
       - "N/A" ×15 (Wave A timeline labels);
       - **"Icon: Bullet" and "Icon: Bird"**, written into comparison points after E4 showed the icon names;
       - **"Not specified"**, a comparison side the beat does not have.

       It flags no legitimate string ("UNKNOWN IDENTITY" is not a whole-string placeholder). On retry, the model wrote "10 per bird" and a real second panel.
8. **No internal ids on screen (added September 26, 2026).** No free-text field (the list in item 7) may contain a whole token equal to one of **this bible's** entity ids (`c1`–`c8`, `p1`–`p4`, `v1`–`v3`), with or without surrounding parentheses or a trailing colon, casefolded. Error: `props.text: contains the internal id "v1" — use the name ("the recipe box")`. The props prompt says: "Refer to people, places and objects by their names; never write ids like c1, p2 or v1." Measured in Wave B's E2E storyboards: 4 leaks in 311 unique scenes, e.g. "One card missing from the recipe box (v1).", "c1 buys the Sundowner from c3", "Feathered adversaries (c4: The Emus)".
9. **Word caps (added September 27, 2026, Issue 7 → Option A).**
   - For every `(template, field path)` in `WORD_CAPS` (`design_templates.md` §5.3), `count_words(value)` must be ≤ the cap. Error: `props.items[0].label: 5 words, limit 3 — rewrite it shorter as a complete phrase`.
   - A list longer than its model maximum is reported as `props.items: 4 items, limit 3 — keep the most important ones`, formatted from Pydantic's `too_long` error.
   - Both run on LLM output and on human edits in `preview`, like every validator.

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
| Critic regression set (§11) | **8 of 8** cases (A, B, B′, C, E, F, G, H) classified as expected |
| Critic cost | reported per fixture: critic calls, mismatches, props changed, tone repairs, **mismatches left unchanged** (no bar; the cold budget run bounds the time) |
| Word budget (added September 27, 2026, Issue 7 → Option A) | **Light share ≥ 1/3**: scenes after the title card with ≤ 2 graphic words (`design_templates.md` §5.1). Also reported, with no bar: total graphic words, graphic words per narration word, and R6/R7 repairs. The per-second bar (**≤ 1.0 graphic word per second**) needs real narration timing, so it is checked in the E2E, not here: this eval's simulated transcript runs at a fixed 4 words/s (`design_testing_and_validation.md` §4). |
| Text audit (added September 26, 2026) | **0** strings containing a newline, **0** completeness failures, **0** internal-id leaks (§6 item 8), **0** word-cap violations (§6 item 9, added September 27, 2026). Strings exactly at their limit are **reported, not failed**: the model never sees the limit, so they cannot be truncations. Wave B's four were complete phrases ("Major Meredith of the Royal Australian Artillery"). |

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
5. **Decide:** `voice = af_heart` **iff** `perspective == "first_person"` **and** `narrator_gender == "female"`; otherwise `am_michael`. That makes `male` and `unknown` behave identically today. They are recorded separately because the bible (§2 repair 5) and any future multi-voice work (DF3) can use the difference.

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

**Which scenes:** `dialogue`, `text_thread`, `emotion_beat`, and `kinetic_quote` **with** a non-null `attribution_cast_id`. Never the deterministic scenes: `rationale` `"deterministic fallback"` or, from September 27, 2026, `"rhythm picture"` (R7's reaction shots and pictures, §4).

**When:** inside props planning, after a candidate scene has passed `validate_scene` (fallback level 0 or 1), before it is accepted. **This includes scenes rebuilt by a rule repair** (R3's alternate), which the first implementation skipped (revised September 26, 2026).

**Call:** `run_with_retries(stage="critic", num_predict=256)`, `temperature` 0.
- **System:** `You check who says or feels what in a story beat. Answer only from the text. Output JSON matching the schema.`
- **User (revised September 26, 2026):** the cast list (`- <id>: <name> (<role>)`, plus ` [narrator]` for the narrator), then **one continuous passage**: the beat before the previous one, the previous beat, this beat and the next beat, joined by single spaces, introduced by exactly this line:

  ```
  Passage (read all of it; who speaks is often named in the sentence before a quote):
  ```

  Then the template's question.
  - **Why:** the first framing labelled the neighbouring beats "context only". In Wave B's `story_recipe_box` E2E, beat splitting had put "…he found a shoebox of letters and texted me a photo:" in the previous beat and the bare quote in this one. The critic then answered the narrator (`c1`) on seeds 7, 8 and 9, and **agreed with the wrong attribution**.
  - With the passage framing it answered Danny on all three seeds, and the four original regression cases still scored 4/4 on every seed (measured September 26, 2026). That case is now **regression case E** below.
- **Blind:** the question gives the scene's *texts* but **never** the proposed speaker, sender, contact, tone or emotion.

| Template | Question (the quoted texts come from the props) | Schema |
|---|---|---|
| `kinetic_quote` | `Who wrote or said these quoted words: "<text>" Answer a cast id, "narration" if they are the narrator telling the story, or "unknown".` | `{"speaker": <cast ids> \| "narration" \| "unknown"}` |
| `dialogue` | `The scene shows these lines in order: 1. "<text>" 2. "<text>" … For each line, who says it (cast id or "unknown") and in what tone?` | `{"lines": [{"speaker": <cast ids> \| "unknown", "tone": neutral\|angry\|happy\|sad\|shocked\|sarcastic\|unknown}]}`, the same length as `props.lines` (a length mismatch is a failed attempt) |
| `text_thread` (revised September 27, 2026) | `The phone belongs to the narrator. Messages in order: 1. "<text>" … For each, was it sent by the narrator ("me") or the other person ("them")? Who is the other person in this conversation, according to the passage? Answer a cast id, or "unknown" if the passage does not say or they are not in the cast list.` | **Keyed, one field per message**, in this order: `{"message_1": "me"\|"them"\|"unknown", …, "message_<n>": …, "contact": <cast ids except the narrator> \| "unknown"}`, where n = `len(props.messages)`; every key is required; `additionalProperties: false` |
| `emotion_beat` | `Which cast member feels something in this beat, and what is the main feeling?` | `{"cast_id": <cast ids> \| "unknown", "emotion": neutral\|happy\|sad\|angry\|shocked\|confused\|smug\|nervous\|unknown}`. `neutral` was added September 27, 2026 with the props enum (`design_templates.md` §2.11); the mismatch rule is unchanged. |

**Why the `text_thread` answer is keyed (measured September 27, 2026, `gemma4:26b`, seeds 7, 8, 9, passage framing).** With a `messages` array, the model collapses consecutive messages from the same sender into one element. On the 8 real `text_thread` scenes of Wave B's story runs, **3 returned a 1-element array on all three seeds**: `story_room_12` s018 and `story_recipe_box` s011, and s012 of a second run, each with 2–3 consecutive "them" messages. Every attempt then fails the length check and the scene ends `unavailable`, unchecked. With one required key per message, **24 of 24** answers were complete, and the sender readings matched the array answers wherever those were complete. `dialogue` was measured with its array schema, and all 39 answers were complete (13 real scenes × 3 seeds), so it keeps its array.

**Why `contact` (measured September 27, 2026, same runs).** In `story_room_12`, s018 shows Deb's reply ("She wrote back: 'Keep the room. He's never missed one.'", right after "I texted Deb:") in a thread labelled **"Sofia"**. The per-message sender check cannot see this, because both messages really are "them". With the question above, the critic answered `c3` (Deb) for s018 on all three seeds; `unknown` for the non-cast "Wife" (s004) and the invented "Unknown Number" (s014); `c3` for the three correct Deb/Danny threads. **No false contact reading on 8 scenes × 3 seeds.**
- The earlier wording without "according to the passage … does not say" answered **Danny** for an invented thread with Walt (a second run's s027). That would have been a false mismatch.
- `contact` sits **last** in the schema: placed first, it changed which scenes collapsed.

**Contact resolution (deterministic).** A thread's *props contact* is:
1. `contact_cast_id`, if set;
2. otherwise the id of the **one** non-narrator cast member whose `name`, after `casefold()` and whitespace collapse, equals `contact_name` the same way;
3. otherwise **none**.

Before validation, the planner **fills** a null `contact_cast_id` with rule 2's id when there is exactly one match. That way a thread with a cast member shows their avatar in the header (`design_templates.md` §2.10). In Wave B's runs, all 8 threads had `contact_cast_id: null`, including the four with Deb or Danny.

**Mismatch rules (deterministic, `planner/critic.py`):**
- **Who** (speaker, sender, `cast_id`): a mismatch iff the critic's value is not `unknown` **and** differs from the props. For `kinetic_quote`, `narration` agrees only with the narrator's cast id. A speaker the critic cannot resolve (`unknown`) is **never** a mismatch.
- **Contact** (`text_thread`, added September 27, 2026): a mismatch iff the critic's `contact` is not `unknown` **and** differs from the props contact (none counts as different). It is recorded as `contact: <contact_name> vs <critic's cast name> (<critic's id>)`, e.g. `contact: Sofia vs Deb (c3)`, so the retry message names the person.
- **Dialogue tone:** a mismatch iff (the critic's tone is not `unknown` and differs from the props) **or** (the critic's tone is `unknown` and the props' tone is not `neutral`). A strong tone the text does not show is an error.
- **Emotion** (`emotion_beat`; **revised October 3, 2026**, now that `neutral` exists): a mismatch iff (the critic's emotion is not `unknown` and differs from the props) **or** (the critic's emotion is `unknown` and the props' emotion is not `neutral`). This is the dialogue-tone rule: a strong feeling the text does not show is an error.
  - **Why:** under the old rule, "unknown" was never a mismatch, so unsupported feelings passed as "agree".
  - **Measured** October 3, 2026, on the 13 model-planned emotion beats of the Wave C/D E2E runs, seeds 7–9, all three seeds identical: the critic read `unknown` on 4 beats whose props showed "angry" for "Meredith was impressed by his opponent.", "angry" for "I called the number I found online, expecting nothing." and "shocked"/"angry" for "…he was quiet for a long time."
  - All 4 were unsupported; no beat whose feeling the text shows was read as `unknown`.

**On mismatch:** exactly **one** props retry for the same template, with an added user message:

```
A second, independent reading of this beat disagrees:
- <field>: you said <x>; the reading says <y>
Fix the props if that reading fits the beat text better; otherwise keep yours.
```

The retry is one `run_with_retries` round with its **normal 3 attempts** (for format and validation). The first implementation allowed 1 attempt, and 30 of 149 critic mismatches across Wave B's runs ended with the known-wrong original kept. The retry result must pass `validate_scene`. If it does, it replaces the scene, **with no second critic call** (no loops).

If all attempts fail, the original validated scene stands. Its retry errors are recorded, never silently discarded.

**Enforcement after the round (revised October 3, 2026; replaces the "only if every attempt fails" tone repair).** After a mismatch, whichever scene stands is checked against the critic's **original reading** (the answer that produced the mismatch). This happens whether the retry succeeded or failed:
- **`dialogue`:** a line `i` keeps a non-`neutral` tone only if the reading's line `i` has the **same** tone. Otherwise its tone becomes `neutral` (`repair: "tone_neutral"`).
- **`emotion_beat`:** a non-`neutral` emotion is kept only if the reading's emotion is the **same**. Otherwise it becomes `neutral` (`repair: "emotion_neutral"`).
- **`kinetic_quote`:** the attribution is **removed** (`attribution_cast_id: null`, `repair: "attribution_dropped"`) when the reading names a speaker that disagrees with it: a cast id other than the props', or `narration` when the props name anyone but the narrator. An `unknown` reading never removes anything.

These repairs only ever **remove** a claim: a feeling, a tone or a face. They never assert the critic's own reading, which can be wrong (case C). Assigning the critic's speaker stays rejected. The enforced scene is re-validated, and `changed` compares the final props with the original.

**Why (measured October 3, 2026, 48 E2E jobs of Waves C and D):**
- **35 of 87** flagged tones survived a retry that "succeeded" by keeping them. The model is told "otherwise keep yours", and it does.
  - In the final run, Rose's farewell note "It was always yours." / "Give it to whoever comes asking." was drawn as **sarcastic**.
  - Another retry, triggered by a speaker mismatch, rewrote a line as "Rose?" said **angry**, which is Wave A's regression case B. Nothing re-checked it.
- **7 of 8** disputed quote attributions were kept, because the retry returned identical props. For example, the narration line "The first attack came on November 2." was credited to The Soldiers (reading: `narration`), and Mr. Alvarez's list item to Sofia (reading: `c2`).
- The real cases, with the critic's readings on seeds 7–9 (identical), are frozen in `tests/data/critic_enforcement_cases.json`.

If the critic call itself fails entirely, the scene is accepted with critic status `unavailable`.

**Recorded** in `plan_report.json` per scene: `critic: {"status": "not_applicable"|"agree"|"mismatch_retried"|"unavailable", "mismatches": ["lines[0].tone: angry vs unknown"], "changed": bool, "repair": "tone_neutral"|"emotion_neutral"|"attribution_dropped"|null, "retry_errors": [str]}` (`design_data_contracts.md` §6). `changed` is true **only if the final props differ** from the original. An identical retry is not a change.

**Measured September 25, 2026** with `gemma4:26b`, seeds 7, 8 and 9, all consistent. These four cases are the **critic regression set**, run as slow tests with the cast `c1 Me (narrator)`, `c2 Danny`, `c3 Walt`, `c4 Deb`:

| Case (from Wave A's real output) | Props | Critic said | Rule result | Expected |
|---|---|---|---|---|
| A: Danny's text "Who is Walter Lindqvist…" as a `kinetic_quote` | attribution `c1` | `c2` | mismatch | mismatch ✓ |
| B: "Rose?" as a `dialogue` line | `c1`, tone `angry` | `c1`, `unknown` | mismatch (tone) | mismatch ✓ |
| B′: the same line with tone `neutral` | `c1`, `neutral` | `c1`, `unknown` | agree | agree ✓ |
| C: "I've been waiting for someone to call about the pie." | attribution `c3` | `unknown` | agree | agree ✓ |
| **E** (added September 26, 2026): the bare quote "Who is Walter Lindqvist and why did he write to Grandma 60 times?", previous beat "While clearing the attic, he found a shoebox of letters and texted me a photo:" (cast for this case: `c1 Me (narrator)`, `c2 Grandma Rose`, `c3 Danny`, `c4 Walt`; the beat before: "Last spring, Danny finally sold the house.") | attribution `c1` | `c3` (passage framing) | mismatch | mismatch ✓ |
| **F** (added September 27, 2026): `story_room_12` s018, "Keep the room." / "He's never missed one." after "I texted Deb:" | contact "Sofia" (resolves to `c4`), senders them, them | `c3`; them, them | mismatch (`contact: Sofia vs Deb (c3)`) | mismatch ✓ |
| **G** (added September 27, 2026): `story_room_12` s004, a thread with "Wife", who is not in the cast | contact "Wife" (none), senders me, them, me | `unknown`; me, them, me | agree | agree ✓ |
| **H** (added September 27, 2026): `story_recipe_box` s011, three consecutive "them" messages from Danny | contact "Danny" (resolves to `c3`), senders them ×3 | `c3`; them ×3, **3 keys answered** | agree | agree ✓ (the array schema returned 1 element on every seed: `unavailable`) |

Cases F, G and H use their own casts and passages, frozen from real output in `tests/data/critic_text_thread_cases.json`.

Latency was ~0.5 s per call. Case C is why "unknown" must never count as a mismatch for *who*: the critic could not resolve "he said" from the beat alone, and the props were right. **Regression bar: all eight cases (A, B, B′, C, E, F, G, H), on seeds 7, 8 and 9.**

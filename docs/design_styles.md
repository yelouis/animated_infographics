# Style Library

This document owns **styles**. A style is a named bundle that changes **how** a story is visualised, never **what is true**: grounding, the critic, the word budget, the review gate and every validator apply in every style.

**The user's direction (October 5, 2026), verbatim:** *"one of the things I noticed is that the generated animations are very literal to what is being said at any given moment. Lets set up something like a style library. We can keep this as one of the styles but lets have a style that is a bit more creative where the animation adds something to the story."*

**Selections (October 5, 2026, in chat):**
- **Creative ingredients:** all four offered: motifs & callbacks, visual metaphors, foreshadowing & reveals, visual gags & asides.
- **License:** "Small embellishments". Invented background details that don't change the story are allowed, as long as they never contradict the narration.
- **Test stories:** 4–6 minutes long.

---

## 1. Styles in the pipeline

- **Choosing a style.** `infographics new <input> --style literal|creative`; the default is `literal`.
  - `ingest.json` records `style` as a job-local input (`design_system_architecture.md` §4), and `plan_report.json` records it too.
  - `rerun <job> --from director` (creative) or `--from storyboard` re-plans with the recorded style.
  - Changing a job's style is `rerun <job> --from director --style <name>`, which rewrites `ingest.json.style`.
- **`StyleSpec`** (Pydantic, `contracts/styles.py`; generated to JSON Schema and TypeScript like every contract) has these fields:
  - `name`
  - `director: bool`: whether the director stage runs (§3.3)
  - `templates`: allowed templates
  - `overlays: bool`
  - `license: Literal["none", "small_embellishments"]`
- **The registry, `STYLES`**, holds exactly the two styles in §2 and §3.
- **What every style shares:**
  - the word budget (`design_templates.md` §5);
  - rules R1–R7 (`design_planner.md` §4);
  - the critic and enforcement after the round (§11);
  - every §6 validator;
  - the review gate.
- **Stage order with the director:** ingest → voice → narrate/transcribe → bible → segment → **director** (creative only) → storyboard → assets → compile → preview → (review) → render. For `literal`, `director` is recorded as skipped.

---

## 2. `literal` (today's behaviour)

- **Definition:** exactly the pipeline of Waves A–F. `director: false`, the 16 templates, no overlays, `license: "none"`.
- **Invariant:** with `--style literal`, every stage output is **byte-identical** to the pre-style pipeline on the same inputs and warm cache. The determinism step of the E2E (step 8) and the existing goldens prove it.

---

## 3. `creative`

### 3.1 What it adds

The style adds the four ingredients the user chose, each realised by a concrete mechanism:

| Ingredient | Mechanism | Where it shows |
|---|---|---|
| **Motifs & callbacks** | 1–3 recurring objects or symbols chosen for the whole story; each recurs and pays off once | A **motif token** overlay on earlier scenes; a **`callback`** scene at the payoff |
| **Visual metaphors** | A beat shown as what it *means* rather than what is said (a relationship as two countries on a map; a deadline as an hourglass) | A **`metaphor`** scene: a generated illustration of the metaphor, with an optional ≤ 3-word label and up to two cast avatars |
| **Foreshadowing & reveals** | A motif is **planted** subtly before it matters (a small token in the corner), then **paid off** when the story reveals it | Plant = motif token; payoff = `callback` scene |
| **Visual gags & asides** | A small extra that the narration doesn't say: a thought bubble, an ironic label, a background prop | An **aside** overlay on a scene |

### 3.2 The license: "small embellishments"

| Allowed | Not allowed |
|---|---|
| Interpretive visuals: metaphors, mood | New **events**, or actions by characters |
| Recurring motifs drawn from things the story contains | **Dialogue** or quotes not in the narration |
| Plants of objects the story later mentions; a plant shows only the object, never its meaning | **Facts**: numbers, dates, names, places, outcomes the story does not contain |
| Background details that don't change the story: weather, a pet, a prop | Anything that **contradicts** the narration |
| Ironic labels of ≤ 3 words | A plant that **reveals the twist** before the narration does |

These are enforced twice: by deterministic validators (§3.3) and by an LLM license check (§3.4).

### 3.3 The director stage (`planner/director.py`, creative only)

**One call** over the whole story: `run_with_retries(stage="director", num_predict=1536)`, temperature 0.3, 3 attempts.
- **Input:** the compact bible (cast, places and set pieces with ids and names), every beat as `[i] text`, the number of beats `n`, the license text of §3.2 verbatim, and the allowed icon names (the E4 block).
- **Output:** `director.json`, whose schema follows. Its `beat_i` fields are enums of `1 … n−1`, icons and cast ids are enums, and no length constraints are given to the model (`design_planner.md` §1).

```json
{"motifs": [{"id": "m1", "name": "the checkout card", "icon": "IdentificationCard",
             "set_piece_id": null,
             "appearances": [{"beat_i": 5, "role": "plant"},
                             {"beat_i": 21, "role": "echo"},
                             {"beat_i": 52, "role": "payoff"}]}],
 "metaphors": [{"beat_i": 19, "image": "two chairs facing each other across an empty library table",
                "label": "Their mailbox", "cast_ids": []}],
 "asides": [{"beat_i": 9, "kind": "thought", "icon": "Coins", "text": null, "cast_id": "c2"},
            {"beat_i": 33, "kind": "label", "icon": null, "text": "Very overdue", "cast_id": null},
            {"beat_i": 40, "kind": "prop", "icon": "Cat", "text": null, "cast_id": null}]}
```

**Counts:**
- motifs: 1–3;
- metaphors: `max(2, min(5, n // 12))`;
- asides: `max(2, min(6, n // 10))`.

For the 64-beat `story_overdue_book` that is 5 metaphors and 6 asides.

**Validators** (deterministic; a violation is a retry message, exactly like props):
1. Every `beat_i` is in `1 … n−1`. Beat 0 (the title) carries nothing.
2. **One directive per beat:** a beat has at most one metaphor, one payoff and one aside, and never both a metaphor and a payoff.
3. **Each motif:** exactly one `payoff`; ≥ 1 `plant`, each at least **3 beats before** the payoff; at most 4 `echo`s, each before the payoff; no two appearances on the same beat.
   - **Spacing (added October 6, 2026):** consecutive appearances of one motif (plants, echoes and the payoff, in beat order) are **≥ 3 beats apart**, and the payoff comes **≤ 20 beats** after the motif's previous appearance. Errors: `motifs[<k>].appearances: beats 18 and 19 are too close — keep appearances at least 3 beats apart` and `motifs[<k>].appearances: the payoff at beat 51 is 32 beats after the last appearance at 19 — add an echo or move the payoff within 20 beats`.
   - **Measured:** the overdue ink motif had echoes at 15, 18 and 19 and its payoff at 51, about 2.5 minutes after the viewer last saw the ink. A callback works only if the viewer still remembers what it calls back to.
4. **Quoted speech stays:** a metaphor or payoff may not sit on a beat containing quoted speech (`QUOTED`, `design_planner.md` §4). Asides may.
5. **Text checks:** `name`, `label` and `text` are each ≤ 3 words (`name` ≤ 4). They pass the placeholder/instruction rule, the internal-id rule and text completeness. They contain no digits, no quotation marks and no cast, place or set-piece name **other than** the motif's own.
   - **A motif is named in the story's own words (added October 6, 2026).** Every word of a motif's `name` other than `a`, `an`, `the`, `of` and `and` must occur in the narration as a whole word, casefolded. A trailing `s` may be added or removed. Error: `motifs[<k>].name: "silver" is not in the narration — name the motif with the story's own words`.
   - **Why:** a motif is an object from the story, and its name is shown on the callback, so it cannot be interpreted the way a metaphor is. Metaphor `label`s and aside `text` are interpretation by design ("thick soup", "so gross"); the license check (§3.4) covers them, and this rule does not apply to them.
   - **Measured:** "Silver Pump Handle" (the narration never says "silver") and "Blue ink pen" (never "pen").
6. `image` is ≤ 25 words, contains no quotation marks, and must not ask for writing (the `text_expected` word list of `design_visual_direction.md` §7.1 returns false on it).
7. `set_piece_id` and `cast_ids` exist in the bible. A `thought` aside needs a `cast_id` **and an `icon` or a `text`** (added October 6, 2026); a `prop` needs an `icon`; a `label` needs `text`. Error: `asides[<k>]: a thought needs an icon or text`. *Measured:* `story_overdue_book` s001 carried a thought with neither, and the renderer drew a generic "…" bubble.

**Show the model rule 6's words (added October 6, 2026; lesson 2.11).** The director prompt states, verbatim, `Metaphor images must not show anything that carries writing. Never use these words in an image: <list>.` The list is every word of `TEXT_EXPECTED_WORDS` and every phrase of `TEXT_EXPECTED_PHRASES` (`assets/illustrate.py`), comma-separated, in their source order. It is generated from those constants, never copied.

**Salvage after the last attempt (added October 6, 2026).** If the third attempt still has errors, an error is **item-local** when it names one `motifs[k]`, `metaphors[k]` or `asides[k]` (rules 1, 3–7).
- **When every error is item-local or a count error:**
  - each erring item is removed and recorded in `director.json`'s new list `director_dropped: [{"item": "metaphors[1]", "error": "<message>"}]`;
  - count errors are waived;
  - the remaining plan is accepted if it still holds **at least one** motif, metaphor or aside.
- **Any other plan-level error** (e.g. two directives on one beat, rule 2) is not salvaged.
- **Why:** the creative bars (§3.7) still judge the result, so a thin plan is reported, not hidden.
- **Measured:** the director's all-or-nothing retry lost the whole creative style to one metaphor, twice:
  - **The cold creative long budget** (both the agent's run and the designer's): after `ollama stop`, all 3 attempts kept "A paper book … mailbox flag" for beat 24. That breaks rule 6 ("book"), so the job degraded to literal. The budget reported 5 images and 114 LLM calls, the literal signature (a creative run gives 9 and 117), and called it a creative PASS.
  - **`story_overdue_book`'s presentation deck:** all 3 attempts kept "A massive mountain of sand slowly burying a single small book", so every creative presentation of it has been literal.
  - With the model loaded warm, the same story planned 1 motif, 4 metaphors and 5 asides. The degradation depends on the model's load state, so a single run proves nothing.

**If every attempt fails and salvage leaves nothing:** the job continues as `literal` with `plan_report.style_degraded: true` and a warning in `report.json`. It never crashes.

### 3.4 The license check (LLM, blind)

For each metaphor and aside, one call: `run_with_retries(stage="license", num_predict=64)`, temperature 0.
- **Prompt:** the passage around the beat (the critic's four-beat passage framing) and the visual described in words: the metaphor's `image` + `label`, or the aside's kind, icon and text.
- **Question, verbatim:** `Would showing this visual add something the passage does not contain: an event, a line of dialogue, or a fact; or contradict the passage? Background details that change nothing are fine.`
- **Schema:** `{"verdict": "ok" | "adds_event" | "adds_dialogue" | "adds_fact" | "contradicts"}`.

Any verdict other than `ok` **removes that item** from `director.json` and records it under `license_dropped`. As in Wave E's enforcement, a claim is only ever removed, never rewritten. If the call itself fails, the item is removed too (fail closed), and the failure is recorded.

### 3.5 How directives become scenes

Selection gains **rule R8**, which runs after R1 and before R6. Then the remaining rules run:
- each **metaphor** beat's choice becomes `primary: "metaphor"`, with `alternate` = the LLM's primary;
- each **payoff** beat becomes `primary: "callback"`, likewise;
- each change is logged as `RuleRepair(rule="R8")`.

R7 counts `metaphor` and `callback` in the **picture** class, and they are never replaced. Both are built **deterministically** with no props LLM call, with `rationale: "director"`:
- `metaphor` props: `{"image_entity": "<metaphor id>", "label": <label|null>, "cast_ids": [...]}`. Its illustration is generated by the assets stage exactly like a set piece: FLUX.2 klein 4B, the `STYLE` string, the text check and its retries, the same cache keys. Its `visual_description` is the directive's `image`. A failed image falls back to the alternate template through the ladder.
- `callback` props: `{"motif_id": "m1", "label": <motif name, ≤ 3 words> | null}`.

**Overlays** are computed by `compile` from `director.json` and written into each timeline scene as `overlays: [...]` (`design_data_contracts.md` §7):
- **motif token** on every `plant` and `echo` beat: `{"kind": "motif_token", "icon": <motif icon>, "anchor": "top_right"}`;
- **aside** on its beat: `{"kind": "thought" | "label" | "prop", "icon", "text", "anchor": "top_left" | "bottom_left"}`. Thought bubbles and labels are anchored **`top_left`** (moved from `top_right` on October 6, 2026: they were drawn on top of the motif token and `character_intro`'s avatar); props `bottom_left`. **The anchor follows from the kind:** `motif_token` → `top_right`, `thought` and `label` → `top_left`, `prop` → `bottom_left`. `compile` writes it, and a contract validator rejects any other pairing.
- **Where overlays may go** (their zones are free of template text at every template's `max` fixture): `kinetic_quote`, `stat_callout`, `reveal`, `cause_effect`, `character_intro`, `emotion_beat`, `relationship_map`, `location`, `set_piece`, `metaphor`.
  - **Never** on `title_card`, `callback`, `icon_list`, `comparison`, `timeline`, `text_thread`, `dialogue` or `map_focus`.
- **When the beat's scene can't take an overlay:**
  - a motif token moves to the nearest allowed scene within 2 beats **before** the payoff;
  - an aside moves to the nearest allowed scene within 1 beat;
  - otherwise the item is dropped and recorded under `overlay_dropped`.
- **At most** one motif token and one aside per scene. When two collide, the earlier-planned item wins and the other moves under the same rules.

### 3.6 Templates and overlays (renderer)

Template specs follow `design_templates.md` §2; these are added there as §2.17 and §2.18.

- **`metaphor`** (picture class; no text fields except `label`):
  - Image 960×960 at (60, 160), radius 32, with the `location` scrim and Ken Burns.
  - The label is drawn in the `location` name slot (display 800 72→48 · 2 lines · 880 px); WORD cap 3.
  - Up to two cast avatars, 200 px, sit at (140, 900) and (740, 900), overlapping the image's bottom edge with a 10 px ring in the cast colour.
  - With no image, the template shows the label in a `bgRaised` circle like `location`'s no-image fallback.
- **`callback`** (picture class):
  - **Motif with a set piece:** that set piece's illustration fills the image box with a 12 px `highlight` ring that pulses (period 45 frames), zooming 1.00→1.12 over the scene.
  - **Otherwise:** the motif icon, 360 px, sits in a 560 px `highlight` circle centred at (540, 560).
  - Label in the name slot (WORD cap 3).
  - **"Seen before" dots:** a row of 24 px `highlight` dots under the label, **one per earlier rendered appearance** of the motif (a scene before this one carrying its motif token), filling in at the scene's `item_frames` (`spread 0.4`; `design_templates.md` §2.18). This makes the callback visible as a callback. `compile` supplies the count: the item count of a `callback` scene is the number of earlier timeline scenes whose `overlays` hold a `motif_token` with this scene's `motif_id`. The renderer draws exactly `item_frames.length` dots, with **no default**: 0 items means no row.
- **`OverlayLayer`** (`renderer/src/story/OverlayLayer.tsx`): drawn above the template and below captions, driven by the scene clock.
  - **Motif token:** a 120 px `bgRaised` circle with a 4 px `highlight` ring and a 72 px `highlight` icon, centred at (900, 240).
  - **Thought bubble** (top-left, revised October 6, 2026): a cloud 240×170 centred at (180, 250), i.e. the box [60, 165, 300, 335], fill `ink` at 0.92. It holds ≤ 3 words in body 700 36→28 · 2 lines · 200 px if `text` is set, otherwise an 84 px navy icon.
  - **Label** (top-left, revised October 6, 2026): a chip `bgDeep` / `ink`, body 700 34→26 · **2 lines · 240 px**, left edge at x 60, top at y 200, so its box lies within [60, 200, 300, 302].
  - **Why these boxes:** the column x 60–300 above y 345 is clear of every allowed template at its `max` fixture. Its nearest neighbours are `character_intro`'s avatar (from x 320, or x 308 with its 12 px ring), `stat_callout`'s icon (x 460), `relationship_map`'s top node (x 450) and `cause_effect`'s cards (y 345). The motif token [840, 180, 960, 300] stays top-right.
  - **Prop:** a 140 px icon in `inkMuted`, centred at (170, 1090).
  - **Motion:** each enters at scene frame 15 (`SPRING_POP`) and bobs 4 px with a period of 60 frames.
  - **Hold motion:** the 45-frame rule (`design_templates.md` §1) applies to overlays.
  - **No fallback icons:** an overlay without the data its kind needs is not drawn. The `Sparkle`, `ChatCircleDots` and `Package` defaults are removed. `compile` already drops such an item and records it under `overlay_dropped` with the reason `incomplete`, so the renderer never sees one.
- **Gallery:**
  - `max` fixtures for `metaphor` and `callback`;
  - **Two overlay fixtures for every allowed template** (from October 6, 2026). Between them, they place every overlay kind beside the token:
    - `overlays__<template>`: a token, a thought with the widest 3-word text, and a prop. Two asides at once is a probe-only combination; their boxes are far apart.
    - `overlays_label__<template>`: a token and the widest 3-word label.
    
    Thought and label share the top-left aside slot and are never drawn together.
  - **Overlap is measured on the rendered frame, not in a table (October 6, 2026; lesson 2.15).**
    - **Markers:** every overlay root carries `data-overlay="<kind>"`. Every `FitText` root carries `data-slot="<slot>"`. Every avatar root, and every template icon or node that is part of the layout, carries `data-occupies="<name>"`. Illustrations do not: overlays sit on images by design.
    - **The probe:** in gallery mode only, a probe in the gallery composition runs after layout on the golden's frame. It reads `getBoundingClientRect()` for every marked element of the scene. For every pair of overlay × overlay and overlay × (slot or occupied element) whose intersection area is > 0, it logs `OVERLAP fixture=<id> overlay=<kind> other=<name> px=<area>`. Elements inside an overlay root (its own `FitText` and icon) belong to that overlay and are never compared with it.
    - **Collection:** `render.ts` collects these lines into `overlap.json`, exactly as it collects `OVERFLOW`. Gallery mode exits 1 on any.
    - **The vitest keeps two checks:** the allowed/forbidden partition, and the `OVERLAY_BOUNDS` boxes of every pair drawn together being disjoint: token × thought, token × label, token × prop and thought × prop. The hand-kept `TEMPLATE_SLOT_BOUNDS` table is deleted.

### 3.7 Evaluation and bars (creative)

Per creative job:
- **Motifs:** every motif has ≥ 1 plant **rendered** (as a token) before its payoff **rendered** (as a `callback`).
- **Counts:** ≥ 2 `metaphor` scenes and ≥ 2 asides rendered.
- **License:** 0 items left that failed the license check.
- **Overlays:** every overlay sits on an allowed template, with the anchor its kind requires (§3.5). Geometry is proven once, on the rendered gallery (§3.6: 0 `OVERLAP` lines in G10), so a per-job table check is not repeated.
- **Inherited bars:** the word density (≤ 1.0 graphic word/s, light share ≥ 1/3; an overlay's text counts as graphic words) and every E2E step-10 column hold.
- **Report:** `report.json` lists every director item with its fate: rendered, moved, `license_dropped` or `overlay_dropped`.
- **Human review:** the contact sheet marks metaphor and callback tiles, and draws overlays on the tiles they belong to.

### 3.8 What creative does not do

- It adds no new facts (§3.2).
- It doesn't change narration, captions or the cast's look.
- It doesn't re-plan the literal scenes it leaves alone.
- It doesn't apply in live presentations: the presentation profile is separate (`design_presentation_simulation.md` §3).

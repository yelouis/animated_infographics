# Template Catalogue

This document owns the **16 templates** (19 from Waves G and H: `metaphor` and `callback` belong to the creative style, `design_styles.md`; `section_title` belongs to the presentation profile, `design_presentation_simulation.md`): what each is for, its props and limits, its layout on the 9:16 canvas, its motion, its SFX cues and its template-specific validators. Everything here is encoded once in `contracts/templates.py` (`design_data_contracts.md` §8) and drawn by `renderer/src/templates/<name>.tsx`.

**Read `design_visual_direction.md` first.** Colours, fonts, layout zones and motion tokens are named here and defined there. All coordinates are canvas pixels on 1080×1920. The **stage** is x 60–1020, y 140–1180 (960×1040).

---

## 1. Rules that apply to every template

1. **Pure function of `(props, scene clock, timeline dictionaries)`.** No `useCurrentFrame`, no `Math.random`, no `Date` (`design_rendering.md` §3).
2. **Every text field is drawn through `FitText`** with the slot's registry typography. The font shrinks from `size_max` toward `size_min` until it fits `max_lines` in `box_width`. The DOM overflow check fires if it still does not fit.
3. **Entrance** uses `ENTER_FRAMES`; **exit** plays in the `EXIT_FRAMES` after `end_frame` (`design_rendering.md` §4). **Hold motion is mandatory:** nothing on screen may be perfectly still for more than 45 frames (the gallery gate's hold-motion check, `design_testing_and_validation.md` §3, enforces this).
4. **Text on a cast colour is `bg` navy, never `ink`.** Measured: ink on the cast slots is 1.52–3.21 : 1; navy on them is 4.53–9.56 : 1 (`design_visual_direction.md` §2).
5. **Item timing comes from the timeline, not from the template.** Python computes `timing.item_frames` (frames relative to scene start) and `timing.count_frames`, and writes them into each timeline scene. The same numbers drive both the SFX cues and the visual entrances, so the two cannot drift. Formula (`compile.py`): `item_frames[i] = i × max(STAGGER_FRAMES, floor(scene_frames × spread / n))`, where `spread` is the template's value below and `scene_frames = end_frame − start_frame`.
6. **SFX roles:** `whoosh`, `pop`, `ding`, `hit`. Cues: `start` (frame 0 of the scene), `item` (each `item_frames[i]`), `count_end` (`count_frames`). Rate limiting is global (`design_audio_and_timing.md` §9).
7. **Every free-text field has a word cap as well as a character limit (added September 27, 2026, Issue 7 → Option A).** The character limit is about fit; the word cap is about how much the viewer has to read. Both are enforced (§5, `design_planner.md` §6 item 9).

---

## 2. The catalogue

Notation: `str≤N` = 1..N characters; `?` = nullable; `[a..b]` = list length bounds. Slot rows: *font weight size_max→size_min · max lines · box width*. "display" = Poppins, "body" = Inter.

### 2.1 `title_card` (fallback category: scene 0 only)
- **Use when:** scene 0, always (forced; never LLM-selected).
- **Props:** `title: str≤60`, `subtitle: str≤80?`, `icon: Icon?`
- **Layout:** icon 200 px, colour `highlight`, centred at (540, 380). Title block centred at y 640. Subtitle top = title bottom + 32, colour `inkMuted`.
- **Slots:** title display 800 104→64 · 3 · 900 | subtitle body 600 44→32 · 2 · 860
- **Motion:** icon springs in (`SPRING_POP`) at frame 0; title words stagger 3 frames each; subtitle enters at frame 12. Hold: title block scales 1.00→1.03 across the scene.
- **SFX:** `whoosh` at `start`.

### 2.2 `kinetic_quote` (fallback category, the universal fallback)
- **Use when:** a line worth emphasising and nothing more specific fits.
- **Props:** `text: str≤90`, **≤ 12 words**, `emphasis: [0..3] str≤24`, `attribution_cast_id: CastId?` *(word caps and list maxima revised September 27, 2026: §5)*
- **Layout:** text centred in the stage, block centre y 660. Attribution (if any): the cast member's **`Avatar` component at 120 px** (the same parametric avatar used everywhere, expression `neutral`, not a letter monogram), with a name chip in the cast colour directly below it, the pair centred 40 px below the text block. *(Clarified September 25, 2026: the first implementation drew a one-letter monogram, which breaks "the same person looks the same everywhere".)*
- **Slots:** text display 800 84→56 · 5 · 920 | attribution name body 700 36→28 · 1 · 600
- **Motion:** words stagger 2 frames; emphasis words in `highlight` at 1.15 scale. Hold: gentle 6 px float, period 90 frames.
- **Validators:** verbatim-span grounding of `text`; each emphasis word is a whole word of `text` (`design_planner.md` §8). **With an attribution, the scene also goes through the people-scene critic** (`design_planner.md` §11).
- **SFX:** none.

### 2.3 `stat_callout` (statement)
- **Use when:** a specific number is the point of the beat.
- **Props:** `value: float ≥ 0`, `decimals: 0|1|2`, `prefix: "" | "$" | "£" | "€" | "~" | "#"`, `display_scale: "none"|"thousand"|"million"|"billion"`, `suffix: str≤14` (may be empty; **≤ 2 words**), `icon: Icon?`. **No `caption`** (removed September 27, 2026, §5)
- **Rendered value line:** `prefix + format(value, decimals, en-US thousands separators) + (" " + display_scale if not "none")`. Example: `value 2.3, decimals 1, display_scale "million"` → **`2.3 million`**, suffix `gallons`.
- **Layout:** icon 160 px centred at (540, 330); value line centred at y 560; suffix 16 px below in `highlight`.
- **Slots:** value display 800 200→110 · 1 · 940 | suffix display 700 64→44 · 1 · 900
- **Motion:** count-up from 0 to `value` over `count_frames = min(24, floor(0.4 × scene_frames))` with ease-out-cubic, displayed at `decimals` throughout. Hold: value scales 1.00→1.04.
- **Validators:** number grounding of `value × scale`; **`suffix` contains no `$`, `£` or `€`** (currency belongs in `prefix`; Issue 5, `design_planner.md` §6 item 6).
- **SFX:** `ding` at `count_end`.

### 2.4 `icon_list` (statement)
- **Use when:** 2–3 parallel things (demands, causes, items, reasons).
- **Props:** `heading: str≤36?` (**≤ 3 words**), `items: [2..3] {icon: Icon, label: str≤32}` (each label **≤ 3 words**) *(word caps and list maxima revised September 27, 2026: §5)*
- **Layout:** heading top y 200. Rows 150 px tall starting at y 400 (or y 240 with no heading). Each row: a 132 px circle in cast slot colour `i mod 4` holding a 96 px navy icon, centred at x 190; label left edge at x 290.
- **Slots:** heading display 800 64→44 · 2 · 900 | label body 700 48→34 · 2 · 700
- **Motion:** rows enter at `item_frames`, `spread 0.5`. Hold: circles pulse 1.00→1.05, period 60 frames, phase-offset by row.
- **SFX:** `pop` at each `item`.

### 2.5 `reveal` (statement)
- **Use when:** a twist, punchline or verdict.
- **Props:** `kicker: str≤24` (rendered uppercase, e.g. "PLOT TWIST"; **≤ 3 words**), `text: str≤60` (**≤ 6 words**) *(word caps and list maxima revised September 27, 2026: §5)*
- **Layout:** kicker centred at y 440 in `danger`, letter-spacing 4 px; text block centred at y 700.
- **Slots:** kicker display 800 56→40 · 1 · 900 | text display 800 96→60 · 4 · 920
- **Motion:** full-canvas `ink` flash at opacity 0.35 fading to 0 over frames 0–3; text zooms 1.30→1.00 with `SPRING_POP`. Hold: 2 px shake decaying to 0 over 20 frames, then a slow 1.00→1.02 scale.
- **Rule:** at most 2 per video (planner R4).
- **SFX:** `hit` at `start`.

### 2.6 `cause_effect` (statement)
- **Use when:** X led to Y (to Z).
- **Props:** `nodes: [2..3] {label: str≤36, icon: Icon?}` (each label **≤ 3 words**) *(word caps and list maxima revised September 27, 2026: §5)*
- **Layout:** cards 840×150, radius 28, fill `bgRaised`, centred at x 540. Card tops are evenly distributed so the stack's vertical centre is y 660 with 90 px between cards. Icon 80 px centred at x 160 inside the card; label left edge x 230. Down-arrows between cards: 8 px `highlight` stroke with a head.
- **Slots:** label body 700 44→32 · 2 · 620
- **Motion:** nodes at `item_frames` (`spread 0.6`); each arrow draws (dash offset) during the 8 frames before the next node appears. Hold: the last arrow's head pulses.
- **SFX:** `pop` at each `item`.

### 2.7 `comparison` (statement)
- **Use when:** A versus B (two people, two prices, before/after). **At most one `comparison` per video** (planner R6).
- **Props:** `a` and `b`, each `{heading: str≤20, cast_id: CastId?, icon: Icon?, points: [1..2] str≤32}`; headings and points **≤ 3 words** each *(word caps and list maxima revised September 27, 2026: §5)*
- **Layout:** panel A y 160–620, panel B y 700–1160, each 960 wide, radius 32, fill `bgRaised`, 10 px left accent bar (the cast colour if `cast_id`, else slot 0 for A and slot 1 for B). "VS" badge: 120 px `highlight` circle at (540, 660) with navy "VS". Heading row: 96 px avatar (if `cast_id`) or 80 px icon, then the heading. Bulleted points below.
- **Slots:** heading display 800 56→40 · 1 · 760 | point body 600 38→28 · 2 · 820
- **Motion:** A enters at 0; B at `item_frames[1]` (n = 2, `spread 0.3`); points stagger 4 frames within each panel. Hold: VS badge rotates ±3° slowly.
- **SFX:** `whoosh` at `start`, `pop` at each `item`.

### 2.8 `character_intro` (people)
- **Use when:** a person's first real appearance.
- **Props:** `cast_id: CastId`, `descriptor: str≤48` (**≤ 4 words**, e.g. "The motel manager"). **No `traits`** (removed September 27, 2026, §5)
- **Layout:** avatar 440 px centred at x 540, top y 180, 12 px ring in the cast colour. Name (from the bible) top y 660, in the cast colour. Descriptor 16 px below, `ink`.
- **Slots:** name display 800 96→64 · 1 · 900 | descriptor body 600 44→32 · 2 · 860
- **Motion:** avatar springs in; name at frame 6; descriptor at 10. Hold: avatar blinks (eyes scale-y to 0.1 for 3 frames) at scene frames 45 and 135.
- **Rule:** at most once per `cast_id` per video (planner R3).
- **SFX:** `pop` at `start`.

### 2.9 `dialogue` (people)
- **Use when:** someone says something (quoted or reported speech).
- **Props:** `lines: [1..2] {cast_id: CastId, text: str≤90, tone: "neutral"|"angry"|"happy"|"sad"|"shocked"|"sarcastic"}`; each line **≤ 10 words** (paraphrase allowed, Issue 6) *(word caps and list maxima revised September 27, 2026: §5)*
- **Layout:** rows stacked from y 200 with 40 px gaps. Row = 140 px avatar + speech bubble (max width 700, padding 28/36, radius 36, tail toward the avatar). The first distinct speaker sits left, the second right. Bubble fill = speaker's cast colour; text navy. If the stack exceeds the stage, all bubbles step down in font size **uniformly**.
- **Tone → avatar expression:** neutral→neutral, angry→angry, happy→happy, sad→sad, shocked→shocked, sarcastic→smug.
- **Slots:** line body 700 44→32 · 4 · 628
- **Motion:** lines at `item_frames` (`spread 0.6`); bubbles scale 0.9→1 from the tail. Hold: the latest speaker's avatar mouth animates (open/closed every 6 frames) until the next line appears.
- **SFX:** `pop` at each `item`.
- **Critic:** every accepted scene goes through the people-scene critic (`design_planner.md` §11): who says or feels it, and in what tone, read blind from the beat.

### 2.10 `text_thread` (people)
- **Use when:** text messages, DMs, chats.
- **Props:** `contact_name: str≤20` (**≤ 3 words**), `contact_cast_id: CastId?`, `messages: [2..3] {from: "me"|"them", text: str≤80}`; each message **≤ 8 words** *(word caps and list maxima revised September 27, 2026: §5)*
- **Layout:** phone body 760×1000 at (160, 160), radius 64, fill `#0E1830`, 6 px `bgRaised` border. Header bar 120 px: a 64 px avatar if `contact_cast_id`, then the contact name. Messages from y 320 with 24 px gaps: "me" right-aligned, fill slot 7 (sky), navy text; "them" left-aligned, fill `bgRaised`, `ink` text; max bubble width 540. When the stack overflows the phone, it scrolls up so the newest message stays visible.
- **Slots:** contact body 700 40→30 · 1 · 560 | message body 600 38→30 · 4 · 476
- **Motion:** messages at `item_frames` (`spread 0.7`); each "them" message is preceded by a 12-frame typing indicator (three dots) that ends at its item frame. Hold: the phone floats 6 px, period 90 frames.
- **SFX:** `pop` at each `item`.
- **Critic:** every accepted scene goes through the people-scene critic (`design_planner.md` §11): who sent each message (the narrator or the contact), and **who the contact is** (added September 27, 2026), read blind from the passage.
- **Contact avatar:** when `contact_name` names exactly one non-narrator cast member (case-insensitive), the planner fills a null `contact_cast_id`, so the header shows that person's avatar (`design_planner.md` §11, "Contact resolution").

### 2.11 `emotion_beat` (people)
- **Use when:** a reaction or feeling is the point.
- **Props:** `cast_id: CastId`, `emotion: "neutral"|"happy"|"sad"|"angry"|"shocked"|"confused"|"smug"|"nervous"`. **`neutral` added and `caption` removed September 27, 2026 (§5):** this is also the *reaction shot* that planner rule R7 inserts (`design_planner.md` §4), always with `neutral`.
- **Layout:** avatar 520 px, expression = `emotion`, centred at x 540, **top y 400** (centred in the stage now that there is no caption; it was y 200), ring in the cast colour. Emotion glyph 140 px at **(800, 420)**. Glyph map: happy `Smiley`, sad `SmileySad`, angry `SmileyAngry`, shocked `ExclamationMark`, confused `Question`, smug `SmileyWink`, nervous `SmileyNervous`, **neutral: no glyph**.
- **Slots:** none (the template draws no text).
- **Motion:** avatar springs in; glyph bobs 8 px, period 36 frames. Hold: angry → 2 px shake; sad → slow 10 px sink; others, **including neutral**, → gentle float; the avatar blinks at scene frames 45 and 135 (as in `character_intro`).
- **SFX:** none.
- **Critic:** every accepted scene goes through the people-scene critic (`design_planner.md` §11): who says or feels it, and what emotion, read blind from the beat.

### 2.12 `relationship_map` (people)
- **Use when:** how 2–5 people relate (family, alliances, betrayals).
- **Props:** `cast_ids: [2..5] CastId` (unique), `edges: [1..6] {from_id: CastId, to_id: CastId, label: str≤18, style: "solid"|"dashed"|"broken"}`; each edge label **≤ 3 words** *(word caps and list maxima revised September 27, 2026: §5)*
- **Layout:** 180 px avatars on a circle centred at (540, 640), radius 330, the first node at the top (12 o'clock), clockwise. Two nodes: at (240, 640) and (840, 640). Names 12 px under each avatar in the cast colour. Edges are 6 px `inkMuted` lines between avatar rims: `dashed` = 18/12 dash, `broken` = solid with a `danger` zig-zag mark at the midpoint. Label chip at the edge midpoint: fill `bgRaised`, text `ink`.
- **Slots:** name body 700 32→24 · 1 · 220 | edge label body 700 30→24 · 1 · 260
- **Motion:** nodes stagger 4 frames; edges draw (8 frames each, stagger 4) after the last node. Hold: nodes float, phase-offset.
- **Validators:** every edge endpoint ∈ `cast_ids`; `from_id != to_id`; no duplicate unordered pair.
- **SFX:** `pop` at `start`.

### 2.13 `location` (place_time)
- **Use when:** arriving somewhere, or establishing where the story is.
- **Props:** `place_id: PlaceId`, `era_label: str≤12?` (**≤ 2 words**). **No `caption`** (removed September 27, 2026, §5). **From October 4, 2026 the planner normalises `era_label` to a four-digit year found in the narration, or null** (`design_planner.md` §5): the stamp never shows invented phrases like "Present Day" or "Modern Era"
- **Layout:** image 960×960 at (60, 160), radius 32, `object-fit: cover`. **Scrim (revised September 25, 2026):** a vertical gradient of `bg` over the image from y 640 to y 1120 with stops **0% alpha at y 640 → 85% at y 800 → 92% at y 1120**. Place name bottom-aligned at y 1080, left x 100. *(The caption that sat 12 px above the name was removed September 27, 2026; with it, the text block's top was y 807. The name alone sits lower, so **every glyph still sits where the scrim is ≥ 85%**, and `IMAGE_TEXT_MIN_TOP` 807 remains a valid bound.)* Worst case, over a pure-white image pixel, that measures `ink` 9.15 : 1 and `inkMuted` 5.57 : 1 (`design_visual_direction.md` §2.1). The original 320 px 0→85% scrim put the caption where the scrim was only ~53%: `inkMuted` measured **1.95 : 1** over white, and was unreadable on the light illustrations FLUX.2 klein produces. Era stamp: `highlight` text on a `bgDeep` pill, rotated −6°, centred at (880, 220). **No image:** the place icon at 360 px in a 560 px `bgRaised` circle centred at (540, 560), with the name as above.
- **Slots:** name display 800 72→48 · 2 · 880 | era display 800 44→32 · 1 · 240
- **Motion:** image fades in 12 frames. Hold: Ken Burns scale 1.00→1.08 and pan x −20→+20 px across the scene. Name slides up at frame 8.
- **Validators:** `era_label` digit grounding; **"ago" in `era_label` only if the transcript says "ago"** (Issue 5, `design_planner.md` §6 item 6).
- **SFX:** `whoosh` at `start`.

### 2.14 `set_piece` (place_time)
- **Use when:** a key object or moment is the subject.
- **Props:** `set_piece_id: SetPieceId`. **No `caption`** (removed September 27, 2026, §5)
- Layout, slots, motion and no-image fallback are **identical to `location`** without the era stamp; the name comes from the bible. Planner rule R7 may insert a `set_piece` as a picture beat (`design_planner.md` §4).
- **SFX:** `whoosh` at `start`.

### 2.15 `map_focus` (place_time)
- **Use when:** a journey, or where something is.
- **Props:** `region: "world" | ISO3`, `markers: [1..3] {place_id: PlaceId, label: str≤24}` (each label **≤ 3 words**), `path: bool`. **No `caption`** (removed September 27, 2026, §5)
- **Layout:** map panel (60, 160)–(1020, 1060), radius 32, clipped. **Colours (revised September 25, 2026; the originals measured land/sea 1.30 : 1 and were effectively invisible):** sea `#0B1326`; land `#4466A0`; region-country land `#7C9FDB`; country borders `#0B1326` at 1.5 px; **lakes** from Natural Earth `ne_50m_lakes` drawn above land in the sea colour, so that inland water such as Lake Superior reads as water. Measured contrast is in `design_visual_direction.md` §2.1. **Framing:** geo bbox of the markers, expanded symmetrically to a minimum span of 8° lon × 6° lat (60° × 40° when `region == "world"`), then padded 25% on each side, fitted with `d3.geoMercator().fitExtent` (`geoNaturalEarth1` when `region == "world"`). **Markers (revised September 25, 2026; "16 px" was ambiguous and was built as a radius-8 dot hidden under its label):** a dot of **radius 14 px**, fill `highlight`, with a **4 px `bgDeep` stroke** (so it separates from every map fill: 3.22 : 1 against land, 6.90 against region land, 12.83 against the dot fill), plus a pulse ring (radius 14→48 px, 4 px `highlight` stroke, opacity 0.6→0, period 30 frames). **Label chip:** `bgDeep` fill, `ink` text, its bottom edge **12 px above the dot's top edge** (the chip bottom sits at marker y − 26). If the marker is within 120 px of the panel top, the chip's top edge sits 12 px below the dot instead (y + 26). **A chip never overlaps its own dot.** The gallery `max` fixture includes one marker within 120 px of the panel top, to exercise the below-dot placement. A vitest case asserts the chip rectangle and the dot circle are disjoint for both placements.
- **Path** (`path: true` and ≥ 2 markers): a quadratic curve from each marker to the next, control point offset perpendicular by 20% of the segment length, 6 px `highlight` dashed 14/10, drawn over 20 frames after the last marker appears, arrowhead at the end.
- **Slots:** marker label display 800 40→30 · 1 · 360
- **Motion:** map fades in 10 frames; markers at `item_frames` (`spread 0.3`). Hold: pulse rings.
- **Validators:** every marker's place has geo; `region == "world"` or `region` equals the `country_iso3` of at least one marker's place.
- **SFX:** `pop` at each `item`.

### 2.16 `timeline` (place_time)
- **Use when:** 3–4 dated events in sequence.
- **Props:** `events: [3..4] {date_label: str≤14, label: str≤28}` (date labels and labels **≤ 3 words** each), `highlight_index: int`. **At most one `timeline` per video** (planner R6) *(word caps and list maxima revised September 27, 2026: §5)*
- **Layout:** vertical axis at x 160 from y 220 to 1120, 6 px `inkMuted`. Events evenly spaced along it. Dot r 18 (the highlighted event r 26 in `highlight` with a soft glow). Date label left edge x 220 (the highlighted one in `highlight`, others `ink`); event label directly below its date in `inkMuted`.
- **Slots:** date display 800 44→32 · 1 · 760 | label body 600 40→28 · 2 · 760
- **Motion:** the axis draws top-down over 12 frames; events at `item_frames` (`spread 0.6`). Hold: the highlighted dot's glow pulses.
- **Validators:** `0 ≤ highlight_index < len(events)`; **the date-label rule of `design_planner.md` §8 (Issue 4)**: each label is a grounded date/number or one of 17 relative-time phrases; labels are distinct; years are non-decreasing. Examples from Wave A that are now rejected: `2013 / 2013 / 2013` (not distinct); `50+ Years / No Record / Memory Only` ("No Record" is neither); `Last Spring / Present / Now` ("Present" alone is not on the list; "Present day" is).
- **SFX:** `pop` at each `item`.

### 2.17 `metaphor` (creative style only; picture class; added October 5, 2026)
- **Use when:** never selected by the LLM. It is placed by rule R8 from a director metaphor (`design_styles.md` §3.3, §3.5).
- **Props:** `image_entity: str` (the metaphor's generated-image id), `label: str≤24?` (**≤ 3 words**), `cast_ids: [0..2] CastId`. Built deterministically from `director.json`.
- **Layout:**
  - **Image:** 960×960 at (60, 160), radius 32, with the `location` scrim (`IMAGE_SCRIM`) and Ken Burns.
  - **Label:** in the `location` name slot, bottom-aligned at y 1080, left x 100.
  - **Avatars:** up to two, 200 px, centred at (240, 1000) and (840, 1000), overlapping the image's bottom edge, each with a 10 px ring in its cast colour.
  - **No image:** the label centred in a 560 px `bgRaised` circle at (540, 560), as in `location`'s fallback.
- **Slots:** label display 800 72→48 · 2 · 880
- **Motion:** image fades in over 12 frames; avatars spring in at frames 6 and 10. Hold: Ken Burns 1.00→1.08.
- **Validators:** the label passes word caps, placeholder, id and completeness rules; no digits; no quotation marks.
- **SFX:** `whoosh` at `start`.

### 2.18 `callback` (creative style only; picture class; added October 5, 2026)
- **Use when:** never selected by the LLM. It is placed by R8 at a motif's payoff.
- **Props:** `motif_id: str`, `label: str≤24?` (**≤ 3 words**). Built deterministically.
- **Layout:**
  - **Motif with a set piece:** that set piece's illustration fills the image box (as `set_piece`), with a 12 px `highlight` ring that pulses (period 45 frames).
  - **Otherwise:** the motif's icon, 360 px, in a 560 px `highlight` circle centred at (540, 560), drawn navy.
  - **Label:** in the name slot.
  - **"Seen before" row:** 24 px dots, one per earlier rendered appearance of the motif, centred at y 1140 with 16 px gaps. They fill in to `highlight` at `item_frames` (`spread 0.4`).
- **Slots:** label display 800 72→48 · 2 · 880
- **Motion:** zoom 1.00→1.12 over the scene. The dots fill at their item frames.
- **SFX:** `ding` at the last `item`.

### 2.19 `section_title` (presentation profile only; added October 5, 2026)
- **Use when:** never selected by the LLM. It is the `section` node of a presentation tree (`design_presentation_simulation.md` §3), built deterministically.
- **Props:** `title: str≤48` (**≤ 6 words**, the slide title), `index: int ≥ 0`, `count: int 1..10`.
- **Layout:**
  - **Title:** a display-font block centred at y 620.
  - **Progress row:** `count` dots of 28 px with 24 px gaps, centred at y 820. The dot at `index` is `highlight` and 36 px; earlier dots are `ink`; later dots are `inkMuted`.
  - The same layout for every slide makes it the presentation's **repeated graphic**.
- **Slots:** title display 800 96→64 · 3 · 900
- **Motion:** the title words stagger 3 frames each. The current dot springs from 28 to 36 px at frame 8. Hold: the current dot pulses 1.00→1.10, period 45 frames.
- **Validators:** `0 ≤ index < count`; the title passes word caps, placeholder, id and completeness rules.
- **SFX:** `whoosh` at `start`.

---

## 3. Gallery fixtures (required per template)

Each template ships three fixtures in `renderer/src/gallery/fixtures/<name>.ts`: **`min`** (fewest items, shortest strings), **`typical`** (realistic content from the fixture stories), **`max`** (most items, every string at its limit using wide text, e.g. repeated `W` and `M` mixed with real words). **From September 27, 2026 every fixture obeys §5:** list lengths at most the new maxima, and every string within its word cap. A `max` string reaches its *character* limit with at most its cap of long words, e.g. a 3-word label `WWWWWWWWW MMMMMMMMMM WWWWWWWWWWW`. A fixture that breaks a word cap tests a state the planner can never produce. The gallery gate (`design_testing_and_validation.md` §3) renders every fixture at the hold frame and must show **zero** overflow logs. **If `max` cannot fit, the limit in this document is wrong: lower it here and in the registry in the same commit, and never raise `size_min` or shrink below it to force a fit.**

---

## 4. Icon allow-list (`contracts/icons.py`)

- **120–200** Phosphor icon names (bare names, e.g. `Drop`, `Buildings`, `Sword`), used with weight `fill`.
- Must cover: people and relationships, emotions (at least the seven glyphs in §2.11), home and family, money and work, time and calendar, places and buildings, transport, war and conflict, nature, animals, weather, food and drink, communication (phone, chat, mail), law and justice, health, tools and objects, documents.
- Generated into `renderer/src/generated/iconMap.ts` as **explicit named imports** from `@phosphor-icons/react`, using whichever export form the installed version provides (e.g. `DropIcon` in v2.1+). **A misspelt or non-existent name then fails `tsc`.** That is the gate, and it can go red.
- The same list is the JSON-Schema `enum` for every `icon` field, so the LLM cannot emit a name outside it.

---

## 5. Word budget (Issue 7 → Option A; selected September 27, 2026)

**The user's selection:** *"Proceed with Option A."* That option reads: picture-first stories, meaning no text that restates the narration, word caps, and a reaction-shot rhythm; karaoke captions stay. The option and its measurements are in `ongoing_general_errors.md` (Issue 7). The reference is Casually Explained, where half the sampled frames carry no words: the narration carries the information and the picture carries the joke.

### 5.1 Counting words

- **A word** is a whitespace-separated token containing at least one letter or digit (`str.isalnum()` on any character). `"$1,500"` is 1 word, `"Mr. Alvarez"` 2, `"—"` 0. The single implementation is `count_words(s)` in `planner/words.py`.
- **A scene's graphic words** are the sum of `count_words` over the free-text props fields the template draws, as listed in the table below.
- They exclude names the template draws from the bible (cast, place and set-piece names, the `kinetic_quote` attribution name), the `stat_callout` value line, and the deterministic `title_card` title.
- The implementation is `graphic_words(scene)` in `planner/words.py`.
- **The light share** is the fraction of scenes **after the title card** (scenes 1…n−1) with ≤ 2 graphic words. The title card is excluded because its title is not a props text.

### 5.2 Removed fields

These fields restated the narration. They are **deleted from the props models** (Pydantic, generated JSON Schema and TypeScript types) and from the templates that drew them:
- `stat_callout.caption`, `emotion_beat.caption`, `location.caption`, `set_piece.caption` and `map_focus.caption`;
- `character_intro.traits`.

`title_card.subtitle` stays; it is always null by construction. Jobs planned before the change no longer load and must be re-planned with `rerun <job> --from storyboard`. **There is no migration**: jobs are disposable, and the E2E creates fresh ones.

### 5.3 Word caps and list maxima (the single source is `WORD_CAPS` and the props models in `contracts/templates.py`)

| Template | List maxima (were) | Word caps (field path → max words) |
|---|---|---|
| `title_card` | — | none (the title is the bible's) |
| `kinetic_quote` | — | `text` 12 |
| `stat_callout` | — | `suffix` 2 |
| `icon_list` | `items` 2..**3** (2..4) | `heading` 3 · `items[].label` 3 |
| `reveal` | — | `kicker` 3 · `text` 6 |
| `cause_effect` | `nodes` 2..**3** (2..4) | `nodes[].label` 3 |
| `comparison` | `a.points`, `b.points` 1..**2** (1..4) | `a.heading`, `b.heading` 3 · `a.points[]`, `b.points[]` 3 |
| `character_intro` | — | `descriptor` 4 |
| `dialogue` | `lines` 1..**2** (1..3) | `lines[].text` 10 |
| `text_thread` | `messages` 2..**3** (2..5) | `contact_name` 3 · `messages[].text` 8 |
| `emotion_beat` | — | none (no text fields) |
| `relationship_map` | — | `edges[].label` 3 |
| `location` | — | `era_label` 2 |
| `set_piece` | — | none (no text fields) |
| `map_focus` | — | `markers[].label` 3 |
| `timeline` | `events` 3..**4** (3..6) | `events[].date_label` 3 · `events[].label` 3 |
| `metaphor` (Wave G) | `cast_ids` 0..2 | `label` 3 |
| `callback` (Wave G) | — | `label` 3 |
| `section_title` (Wave H) | — | `title` 6 |
| overlays (Wave G) | — | an aside's `text` 3; a motif's `name` 4. Overlay text counts as graphic words for its scene (`design_styles.md` §3.6) |

Character limits are unchanged. Per-video limits (at most one `timeline` and one `comparison`) are planner rule R6; the reaction-shot rhythm is rule R7 (`design_planner.md` §4).

### 5.4 Template classes for the rhythm rule (R7)

| Class | Templates | Meaning |
|---|---|---|
| **picture** | `emotion_beat`, `set_piece`, `location`, `stat_callout`, `map_focus`, and from Wave G **`metaphor`** and **`callback`** | ≤ 2 graphic words by contract (map markers are labels on a picture). They end a run of worded scenes. |
| **replaceable** | `kinetic_quote`, `cause_effect`, `icon_list`, `comparison`, `timeline`, `relationship_map` | Their words restate the narration. R7 may replace one with a picture. |
| **kept** | `title_card`, `character_intro`, `dialogue`, `text_thread`, `reveal`, `section_title` (Wave H) — and, from October 3, 2026, **any scene whose beat contains quoted speech or writing** | Words the story itself contains (speech, texts, a punchline) or a first appearance. They count as worded but are **never replaced**. Measured: without this class, R7 turned Major Meredith's introduction into a reaction shot, and Deb's reply "Keep the room. He's never missed one." into a picture of Room 12. |

### 5.5 Measured (September 27, 2026, `gemma4:26b`, the Wave B E2E storyboards)

- **Caps are writable.** The props stage with these caps, the new writing rules and the new `props.md` guideline was run on **94 real scenes** (every non-title scene of `molasses_flood`, `emu_war`, `story_recipe_box` and `story_room_12`). **93 passed within the normal 3 attempts** (73 on the first). Total attempts were 118, versus 147 props attempts for the same scenes in Wave B.
  - The one failure was the 13-word quote "Who is Walter Lindqvist and why did he write to Grandma 60 times?" as a `kinetic_quote`. It cannot be a verbatim span of ≤ 12 words, so the ladder moves it to its alternate template.
  - Most retries were word caps (13) and list maxima (7), each fixed by the retry message.
- **Density.** These are the probe's real outputs with R6 and R7 applied:

  | Fixture | Graphic words/s (Wave B → now) | Scenes with ≤ 2 words (Wave B → now) |
  |---|---|---|
  | `molasses_flood` | 1.11 → **0.52** | 1/10 → **50%** |
  | `emu_war` | 1.51 → **0.63** | 3/25 → **56%** |
  | `story_recipe_box` | 1.91 → **0.89** | 3/32 → **44%** |
  | `story_room_12` | 1.76 → **0.86** | 1/33 → **39%** |

  (These shares count the title card as a worded scene over all n scenes, which is slightly stricter than the light-share definition in §5.1.) Without R6 and R7, `story_recipe_box` measured 1.13 words/s and 31%, failing both bars. **Both rules are needed.**


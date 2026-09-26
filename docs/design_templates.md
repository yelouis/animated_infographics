# Template Catalogue

This document owns the **16 templates**: what each is for, its props and limits, its layout on the 9:16 canvas, its motion, its SFX cues and its template-specific validators. Everything here is encoded once in `contracts/templates.py` (`design_data_contracts.md` §8) and drawn by `renderer/src/templates/<name>.tsx`.

**Read `design_visual_direction.md` first.** Colours, fonts, layout zones and motion tokens are named here and defined there. All coordinates are canvas pixels on 1080×1920. The **stage** is x 60–1020, y 140–1180 (960×1040).

---

## 1. Rules that apply to every template

1. **Pure function of `(props, scene clock, timeline dictionaries)`.** No `useCurrentFrame`, no `Math.random`, no `Date` (`design_rendering.md` §3).
2. **Every text field is drawn through `FitText`** with the slot's registry typography. The font shrinks from `size_max` toward `size_min` until it fits `max_lines` in `box_width`. The DOM overflow check fires if it still does not fit.
3. **Entrance** uses `ENTER_FRAMES`; **exit** plays in the `EXIT_FRAMES` after `end_frame` (`design_rendering.md` §4). **Hold motion is mandatory:** nothing on screen may be perfectly still for more than 45 frames (the gallery gate's hold-motion check, `design_testing_and_validation.md` §3, enforces this).
4. **Text on a cast colour is `bg` navy, never `ink`.** Measured: ink on the cast slots is 1.52–3.21 : 1; navy on them is 4.53–9.56 : 1 (`design_visual_direction.md` §2).
5. **Item timing comes from the timeline, not from the template.** Python computes `timing.item_frames` (frames relative to scene start) and `timing.count_frames`, and writes them into each timeline scene. The same numbers drive both the SFX cues and the visual entrances, so the two cannot drift. Formula (`compile.py`): `item_frames[i] = i × max(STAGGER_FRAMES, floor(scene_frames × spread / n))`, where `spread` is the template's value below and `scene_frames = end_frame − start_frame`.
6. **SFX roles:** `whoosh`, `pop`, `ding`, `hit`. Cues: `start` (frame 0 of the scene), `item` (each `item_frames[i]`), `count_end` (`count_frames`). Rate limiting is global (`design_audio_and_timing.md` §9).

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
- **Props:** `text: str≤90`, `emphasis: [0..3] str≤24`, `attribution_cast_id: CastId?`
- **Layout:** text centred in the stage, block centre y 660. Attribution (if any): the cast member's **`Avatar` component at 120 px** (the same parametric avatar used everywhere, expression `neutral`, not a letter monogram), with a name chip in the cast colour directly below it, the pair centred 40 px below the text block. *(Clarified September 25, 2026: the first implementation drew a one-letter monogram, which breaks "the same person looks the same everywhere".)*
- **Slots:** text display 800 84→56 · 5 · 920 | attribution name body 700 36→28 · 1 · 600
- **Motion:** words stagger 2 frames; emphasis words in `highlight` at 1.15 scale. Hold: gentle 6 px float, period 90 frames.
- **Validators:** verbatim-span grounding of `text`; each emphasis word is a whole word of `text` (`design_planner.md` §8).
- **SFX:** none.

### 2.3 `stat_callout` (statement)
- **Use when:** a specific number is the point of the beat.
- **Props:** `value: float ≥ 0`, `decimals: 0|1|2`, `prefix: "" | "$" | "£" | "€" | "~" | "#"`, `display_scale: "none"|"thousand"|"million"|"billion"`, `suffix: str≤14` (may be empty), `caption: str≤70?`, `icon: Icon?`
- **Rendered value line:** `prefix + format(value, decimals, en-US thousands separators) + (" " + display_scale if not "none")`. Example: `value 2.3, decimals 1, display_scale "million"` → **`2.3 million`**, suffix `gallons`.
- **Layout:** icon 160 px centred at (540, 330); value line centred at y 560; suffix 16 px below in `highlight`; caption 32 px below that in `inkMuted`.
- **Slots:** value display 800 200→110 · 1 · 940 | suffix display 700 64→44 · 1 · 900 | caption body 600 44→32 · 3 · 860
- **Motion:** count-up from 0 to `value` over `count_frames = min(24, floor(0.4 × scene_frames))` with ease-out-cubic, displayed at `decimals` throughout. Hold: value scales 1.00→1.04.
- **Validators:** number grounding of `value × scale`.
- **SFX:** `ding` at `count_end`.

### 2.4 `icon_list` (statement)
- **Use when:** 2–4 parallel things (demands, causes, items, reasons).
- **Props:** `heading: str≤36?`, `items: [2..4] {icon: Icon, label: str≤32}`
- **Layout:** heading top y 200. Rows 150 px tall starting at y 400 (or y 240 with no heading). Each row: a 132 px circle in cast slot colour `i mod 4` holding a 96 px navy icon, centred at x 190; label left edge at x 290.
- **Slots:** heading display 800 64→44 · 2 · 900 | label body 700 48→34 · 2 · 700
- **Motion:** rows enter at `item_frames`, `spread 0.5`. Hold: circles pulse 1.00→1.05, period 60 frames, phase-offset by row.
- **SFX:** `pop` at each `item`.

### 2.5 `reveal` (statement)
- **Use when:** a twist, punchline or verdict.
- **Props:** `kicker: str≤24` (rendered uppercase, e.g. "PLOT TWIST"), `text: str≤60`
- **Layout:** kicker centred at y 440 in `danger`, letter-spacing 4 px; text block centred at y 700.
- **Slots:** kicker display 800 56→40 · 1 · 900 | text display 800 96→60 · 4 · 920
- **Motion:** full-canvas `ink` flash at opacity 0.35 fading to 0 over frames 0–3; text zooms 1.30→1.00 with `SPRING_POP`. Hold: 2 px shake decaying to 0 over 20 frames, then a slow 1.00→1.02 scale.
- **Rule:** at most 2 per video (planner R4).
- **SFX:** `hit` at `start`.

### 2.6 `cause_effect` (statement)
- **Use when:** X led to Y (to Z).
- **Props:** `nodes: [2..4] {label: str≤36, icon: Icon?}`
- **Layout:** cards 840×150, radius 28, fill `bgRaised`, centred at x 540. Card tops are evenly distributed so the stack's vertical centre is y 660 with 90 px between cards. Icon 80 px centred at x 160 inside the card; label left edge x 230. Down-arrows between cards: 8 px `highlight` stroke with a head.
- **Slots:** label body 700 44→32 · 2 · 620
- **Motion:** nodes at `item_frames` (`spread 0.6`); each arrow draws (dash offset) during the 8 frames before the next node appears. Hold: the last arrow's head pulses.
- **SFX:** `pop` at each `item`.

### 2.7 `comparison` (statement)
- **Use when:** A versus B (two people, two prices, before/after).
- **Props:** `a` and `b`, each `{heading: str≤20, cast_id: CastId?, icon: Icon?, points: [1..4] str≤32}`
- **Layout:** panel A y 160–620, panel B y 700–1160, each 960 wide, radius 32, fill `bgRaised`, 10 px left accent bar (the cast colour if `cast_id`, else slot 0 for A and slot 1 for B). "VS" badge: 120 px `highlight` circle at (540, 660) with navy "VS". Heading row: 96 px avatar (if `cast_id`) or 80 px icon, then the heading. Bulleted points below.
- **Slots:** heading display 800 56→40 · 1 · 760 | point body 600 38→28 · 2 · 820
- **Motion:** A enters at 0; B at `item_frames[1]` (n = 2, `spread 0.3`); points stagger 4 frames within each panel. Hold: VS badge rotates ±3° slowly.
- **SFX:** `whoosh` at `start`, `pop` at each `item`.

### 2.8 `character_intro` (people)
- **Use when:** a person's first real appearance.
- **Props:** `cast_id: CastId`, `descriptor: str≤48`, `traits: [0..3] str≤18`
- **Layout:** avatar 440 px centred at x 540, top y 180, 12 px ring in the cast colour. Name (from the bible) top y 660, in the cast colour. Descriptor 16 px below, `ink`. Trait chips 32 px below that: fill = cast colour, text navy, radius 999, padding 18/28, centred row, wrapping to at most 2 rows.
- **Slots:** name display 800 96→64 · 1 · 900 | descriptor body 600 44→32 · 2 · 860 | trait body 700 34→28 · 1 · 400
- **Motion:** avatar springs in; name at frame 6; descriptor at 10; chips stagger 4 frames from frame 14. Hold: avatar blinks (eyes scale-y to 0.1 for 3 frames) at scene frames 45 and 135.
- **Rule:** at most once per `cast_id` per video (planner R3).
- **SFX:** `pop` at `start`.

### 2.9 `dialogue` (people)
- **Use when:** someone says something (quoted or reported speech).
- **Props:** `lines: [1..3] {cast_id: CastId, text: str≤90, tone: "neutral"|"angry"|"happy"|"sad"|"shocked"|"sarcastic"}`
- **Layout:** rows stacked from y 200 with 40 px gaps. Row = 140 px avatar + speech bubble (max width 700, padding 28/36, radius 36, tail toward the avatar). The first distinct speaker sits left, the second right, a third left. Bubble fill = speaker's cast colour; text navy. If the stack exceeds the stage, all bubbles step down in font size **uniformly**.
- **Tone → avatar expression:** neutral→neutral, angry→angry, happy→happy, sad→sad, shocked→shocked, sarcastic→smug.
- **Slots:** line body 700 44→32 · 4 · 628
- **Motion:** lines at `item_frames` (`spread 0.6`); bubbles scale 0.9→1 from the tail. Hold: the latest speaker's avatar mouth animates (open/closed every 6 frames) until the next line appears.
- **SFX:** `pop` at each `item`.

### 2.10 `text_thread` (people)
- **Use when:** text messages, DMs, chats.
- **Props:** `contact_name: str≤20`, `contact_cast_id: CastId?`, `messages: [2..5] {from: "me"|"them", text: str≤80}`
- **Layout:** phone body 760×1000 at (160, 160), radius 64, fill `#0E1830`, 6 px `bgRaised` border. Header bar 120 px: a 64 px avatar if `contact_cast_id`, then the contact name. Messages from y 320 with 24 px gaps: "me" right-aligned, fill slot 7 (sky), navy text; "them" left-aligned, fill `bgRaised`, `ink` text; max bubble width 540. When the stack overflows the phone, it scrolls up so the newest message stays visible.
- **Slots:** contact body 700 40→30 · 1 · 560 | message body 600 38→30 · 4 · 476
- **Motion:** messages at `item_frames` (`spread 0.7`); each "them" message is preceded by a 12-frame typing indicator (three dots) that ends at its item frame. Hold: the phone floats 6 px, period 90 frames.
- **SFX:** `pop` at each `item`.

### 2.11 `emotion_beat` (people)
- **Use when:** a reaction or feeling is the point.
- **Props:** `cast_id: CastId`, `emotion: "happy"|"sad"|"angry"|"shocked"|"confused"|"smug"|"nervous"`, `caption: str≤40?`
- **Layout:** avatar 520 px, expression = `emotion`, centred at x 540, top y 200, ring in the cast colour. Emotion glyph 140 px at (800, 220). Glyph map: happy `Smiley`, sad `SmileySad`, angry `SmileyAngry`, shocked `ExclamationMark`, confused `Question`, smug `SmileyWink`, nervous `SmileyNervous`. Caption top y 800.
- **Slots:** caption display 800 64→44 · 2 · 900
- **Motion:** avatar springs in; glyph bobs 8 px, period 36 frames. Hold: angry → 2 px shake; sad → slow 10 px sink; others → gentle float.
- **SFX:** none.

### 2.12 `relationship_map` (people)
- **Use when:** how 2–5 people relate (family, alliances, betrayals).
- **Props:** `cast_ids: [2..5] CastId` (unique), `edges: [1..6] {from_id: CastId, to_id: CastId, label: str≤18, style: "solid"|"dashed"|"broken"}`
- **Layout:** 180 px avatars on a circle centred at (540, 640), radius 330, the first node at the top (12 o'clock), clockwise. Two nodes: at (240, 640) and (840, 640). Names 12 px under each avatar in the cast colour. Edges are 6 px `inkMuted` lines between avatar rims: `dashed` = 18/12 dash, `broken` = solid with a `danger` zig-zag mark at the midpoint. Label chip at the edge midpoint: fill `bgRaised`, text `ink`.
- **Slots:** name body 700 32→24 · 1 · 220 | edge label body 700 30→24 · 1 · 260
- **Motion:** nodes stagger 4 frames; edges draw (8 frames each, stagger 4) after the last node. Hold: nodes float, phase-offset.
- **Validators:** every edge endpoint ∈ `cast_ids`; `from_id != to_id`; no duplicate unordered pair.
- **SFX:** `pop` at `start`.

### 2.13 `location` (place_time)
- **Use when:** arriving somewhere, or establishing where the story is.
- **Props:** `place_id: PlaceId`, `caption: str≤48?`, `era_label: str≤12?`
- **Layout:** image 960×960 at (60, 160), radius 32, `object-fit: cover`. **Scrim (revised September 25, 2026):** a vertical gradient of `bg` over the image from y 640 to y 1120 with stops **0% alpha at y 640 → 85% at y 800 → 92% at y 1120**. Place name bottom-aligned at y 1080, left x 100; caption 12 px above the name, `inkMuted`. With both at their line maxima the text block's top is y 807, so **every glyph sits where the scrim is ≥ 85%**. Worst case, over a pure-white image pixel, that measures `ink` 9.15 : 1 and `inkMuted` 5.57 : 1 (`design_visual_direction.md` §2.1). The original 320 px 0→85% scrim put the caption where the scrim was only ~53%: `inkMuted` measured **1.95 : 1** over white, and was unreadable on the light illustrations FLUX.2 klein produces. Era stamp: `highlight` text on a `bgDeep` pill, rotated −6°, centred at (880, 220). **No image:** the place icon at 360 px in a 560 px `bgRaised` circle centred at (540, 560), with name and caption as above.
- **Slots:** name display 800 72→48 · 2 · 880 | caption body 600 40→30 · 2 · 880 | era display 800 44→32 · 1 · 240
- **Motion:** image fades in 12 frames. Hold: Ken Burns scale 1.00→1.08 and pan x −20→+20 px across the scene. Name slides up at frame 8.
- **Validators:** `era_label` digit grounding.
- **SFX:** `whoosh` at `start`.

### 2.14 `set_piece` (place_time)
- **Use when:** a key object or moment is the subject.
- **Props:** `set_piece_id: SetPieceId`, `caption: str≤48?`
- Layout, slots, motion and no-image fallback are **identical to `location`** without the era stamp; the name comes from the bible.
- **SFX:** `whoosh` at `start`.

### 2.15 `map_focus` (place_time)
- **Use when:** a journey, or where something is.
- **Props:** `region: "world" | ISO3`, `markers: [1..3] {place_id: PlaceId, label: str≤24}`, `path: bool`, `caption: str≤60?`
- **Layout:** map panel (60, 160)–(1020, 1060), radius 32, clipped. **Colours (revised September 25, 2026; the originals measured land/sea 1.30 : 1 and were effectively invisible):** sea `#0B1326`; land `#4466A0`; region-country land `#7C9FDB`; country borders `#0B1326` at 1.5 px; **lakes** from Natural Earth `ne_50m_lakes` drawn above land in the sea colour, so that inland water such as Lake Superior reads as water. Measured contrast is in `design_visual_direction.md` §2.1. **Framing:** geo bbox of the markers, expanded symmetrically to a minimum span of 8° lon × 6° lat (60° × 40° when `region == "world"`), then padded 25% on each side, fitted with `d3.geoMercator().fitExtent` (`geoNaturalEarth1` when `region == "world"`). **Markers (revised September 25, 2026; "16 px" was ambiguous and was built as a radius-8 dot hidden under its label):** a dot of **radius 14 px**, fill `highlight`, with a **4 px `bgDeep` stroke** (so it separates from every map fill: 3.22 : 1 against land, 6.90 against region land, 12.83 against the dot fill), plus a pulse ring (radius 14→48 px, 4 px `highlight` stroke, opacity 0.6→0, period 30 frames). **Label chip:** `bgDeep` fill, `ink` text, its bottom edge **12 px above the dot's top edge** (the chip bottom sits at marker y − 26). If the marker is within 120 px of the panel top, the chip's top edge sits 12 px below the dot instead (y + 26). **A chip never overlaps its own dot.** The gallery `max` fixture includes one marker within 120 px of the panel top, to exercise the below-dot placement. A vitest case asserts the chip rectangle and the dot circle are disjoint for both placements. Caption below the panel at y 1090.
- **Path** (`path: true` and ≥ 2 markers): a quadratic curve from each marker to the next, control point offset perpendicular by 20% of the segment length, 6 px `highlight` dashed 14/10, drawn over 20 frames after the last marker appears, arrowhead at the end.
- **Slots:** marker label display 800 40→30 · 1 · 360 | caption body 600 40→30 · 2 · 900
- **Motion:** map fades in 10 frames; markers at `item_frames` (`spread 0.3`). Hold: pulse rings.
- **Validators:** every marker's place has geo; `region == "world"` or `region` equals the `country_iso3` of at least one marker's place.
- **SFX:** `pop` at each `item`.

### 2.16 `timeline` (place_time)
- **Use when:** 3–6 dated events in sequence.
- **Props:** `events: [3..6] {date_label: str≤14, label: str≤28}`, `highlight_index: int`
- **Layout:** vertical axis at x 160 from y 220 to 1120, 6 px `inkMuted`. Events evenly spaced along it. Dot r 18 (the highlighted event r 26 in `highlight` with a soft glow). Date label left edge x 220 (the highlighted one in `highlight`, others `ink`); event label directly below its date in `inkMuted`.
- **Slots:** date display 800 44→32 · 1 · 760 | label body 600 40→28 · 2 · 760
- **Motion:** the axis draws top-down over 12 frames; events at `item_frames` (`spread 0.6`). Hold: the highlighted dot's glow pulses.
- **Validators:** `0 ≤ highlight_index < len(events)`; date-label digit grounding.
- **SFX:** `pop` at each `item`.

---

## 3. Gallery fixtures (required per template)

Each template ships three fixtures in `renderer/src/gallery/fixtures/<name>.ts`: **`min`** (fewest items, shortest strings), **`typical`** (realistic content from the fixture stories), **`max`** (most items, every string at its limit using wide text, e.g. repeated `W` and `M` mixed with real words). The gallery gate (`design_testing_and_validation.md` §3) renders every fixture at the hold frame and must show **zero** overflow logs. **If `max` cannot fit, the limit in this document is wrong: lower it here and in the registry in the same commit, and never raise `size_min` or shrink below it to force a fit.**

---

## 4. Icon allow-list (`contracts/icons.py`)

- **120–200** Phosphor icon names (bare names, e.g. `Drop`, `Buildings`, `Sword`), used with weight `fill`.
- Must cover: people and relationships, emotions (at least the seven glyphs in §2.11), home and family, money and work, time and calendar, places and buildings, transport, war and conflict, nature, animals, weather, food and drink, communication (phone, chat, mail), law and justice, health, tools and objects, documents.
- Generated into `renderer/src/generated/iconMap.ts` as **explicit named imports** from `@phosphor-icons/react`, using whichever export form the installed version provides (e.g. `DropIcon` in v2.1+). **A misspelt or non-existent name then fails `tsc`.** That is the gate, and it can go red.
- The same list is the JSON-Schema `enum` for every `icon` field, so the LLM cannot emit a name outside it.

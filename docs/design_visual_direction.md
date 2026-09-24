# Visual Direction

This document owns the **look**: palette, typography, layout zones, motion tokens, background, avatars, captions, and the **illustration generation** style and parameters. The renderer implements these as tokens in `renderer/src/theme/` and nowhere else. A hex code or font size typed directly into a template is a defect.

**Art direction (decided September 23, 2026): flat editorial vector.** Think of a good explainer channel: bold flat shapes, a limited saturated palette on a deep navy ground, confident type, smooth purposeful motion. It is **not** a pastiche of any specific studio: no borrowed characters, logos or signature motifs.

**Anti-patterns (reject in review):** gradients other than the two specified (background vignette, image scrim); drop shadows other than the specified glows; outlines on filled shapes; emoji fonts; more than three text sizes in one scene; text on a busy image without the scrim; any element that is perfectly still for more than 45 frames.

---

## 1. Canvas and layout zones (9:16)

Canvas **1080 × 1920**. Zones:

| Zone | Rect (x0, y0)–(x1, y1) | What goes there |
|---|---|---|
| Top reserve | (0, 0)–(1080, 140) | Background only (platform status UI) |
| **Stage** | **(60, 140)–(1020, 1180)** | All template content |
| **Caption band** | **(90, 1220)–(990, 1460)** | Karaoke captions only; vertical centre y 1340 |
| Bottom reserve | (0, 1500)–(1080, 1920) | Background only (Shorts/TikTok/Reels overlay their title, buttons and progress here) |

**Nothing but the background may be drawn in either reserve**, including exit animations. A template that needs more room must shrink its content, not borrow a reserve.

---

## 2. Palette

| Token | Hex | Use |
|---|---|---|
| `bg` | `#14213D` | Canvas; **text on any cast colour or on `highlight`** |
| `bgRaised` | `#1F2F52` | Cards, panels, "them" bubbles |
| `bgDeep` | `#0B1326` | Caption stroke, stamps, vignette edge |
| `ink` | `#F8F4E9` | Primary text on `bg` / `bgRaised` |
| `inkMuted` | `#B8C1D6` | Secondary text, axes, edges |
| `highlight` | `#FFD166` | Active caption word, emphasis, markers, arrows |
| `danger` | `#FF6B8B` | Reveal kicker, broken-relationship mark |
| cast slot 0–7 | `#F4A261` `#2A9D8F` `#E76F51` `#E9C46A` `#8AB17D` `#7B7FE0` `#F28482` `#4CC9F0` | One per cast member (`color_slot`); icon circles; accents |

**Measured contrast (WCAG 2.x relative luminance, computed September 23, 2026):**

| Pair | Ratio |
|---|---|
| `ink` on `bg` / on `bgRaised` | **14.53** / **12.04** |
| `inkMuted` on `bg` / on `bgRaised` | 8.85 / 7.33 |
| `highlight` on `bg` | 11.08 |
| `danger` on `bg` / on `bgRaised` | 5.88 / 4.87 |
| cast slots on `bg` (as shapes) | **4.53 – 9.56** (all ≥ 3 : 1 non-text floor) |
| **`bg` text on cast slots** | **4.53 – 9.56**: required pairing |
| ⛔ **`ink` text on cast slots** | **1.52 – 3.21**: **forbidden** |
| `ink` / `highlight` caption words on `bgDeep` stroke | 16.83 / 12.83 |

`danger` was moved from `#EF476F` (4.41 : 1 on `bg`, under the 4.5 floor) to `#FF6B8B` for this reason. The caption's active and inactive words differ by only **1.31 : 1** (`highlight` vs `ink`), so **colour is never the only cue**: the active word is also scaled 1.12.

**Contrast test** (`tests/test_contrast.py`, part of G4): recomputes every ratio above from `renderer/src/theme/palette.ts` (parsed) and asserts the floors (text ≥ 4.5, shapes ≥ 3.0). It also asserts that the forbidden pair is still below 4.5. If someone "fixes" the palette so that ink-on-cast becomes legal, the rule in `design_templates.md` §1 (rule 4) should be revisited deliberately rather than left stale.

---

## 3. Typography

| Family | Files (static TTF, OFL-1.1) | Role |
|---|---|---|
| **Poppins** | `Poppins-Bold.ttf` (700), `Poppins-ExtraBold.ttf` (800) | "display": titles, numbers, captions, names |
| **Inter** | `Inter-Medium.ttf` (500), `Inter-SemiBold.ttf` (600), `Inter-Bold.ttf` (700) | "body": labels, descriptions, bubbles |

Stored at `renderer/public/fonts/` with `OFL.txt`. Loaded in the renderer with `@remotion/fonts` `loadFont()` over `staticFile()`, and in Python by `textfit.py` from the **same files**. Line height: display **1.12**, body **1.25**. Letter-spacing 0 except where a template says otherwise. Per-slot sizes live in the template registry (`design_templates.md`).

---

## 4. Motion tokens

| Token | Value |
|---|---|
| `ENTER_FRAMES` | **12** (400 ms) |
| `EXIT_FRAMES` | **8** (267 ms) |
| `STAGGER_FRAMES` | **4** |
| `EASE_ENTER` | `Easing.bezier(0.16, 1, 0.3, 1)` |
| `EASE_EXIT` | `Easing.bezier(0.7, 0, 0.84, 0)` |
| `SPRING_POP` | `spring({fps: 30, config: {damping: 14, stiffness: 180, mass: 0.8}})` |
| Default entrance | opacity 0→1, translateY +40→0 px (cards also scale 0.96→1), `EASE_ENTER`, `ENTER_FRAMES` |
| Default exit | opacity 1→0, translateY 0→−24 px, `EASE_EXIT`, `EXIT_FRAMES` |

`interpolate`, `Easing` and `spring` from `remotion` are **pure functions** and allowed in templates. Frame *sources* are not (`design_rendering.md` §3).

---

## 5. Background

Drawn once beneath all scenes by the `Story` composition, driven by the global clock:
- Fill `bg`; a radial vignette from `#1A2A4A` at the centre to `bgDeep` at the corners.
- Two soft circles, fill `bgRaised` at opacity 0.55, radii 520 and 380, drifting sinusoidally (amplitude 40 px; periods 12 s and 17 s; starting positions (260, 520) and (860, 1320)).
- Nothing else. The background must be identical between two renders of the same timeline.

---

## 6. Avatars (`components/Avatar.tsx`)

Parametric flat SVG, `viewBox 0 0 200 200`, driven only by `bible.cast[].avatar`, `color_slot` and an `expression`:
- **Body:** a half-ellipse at the bottom in the cast colour (the "shirt"); neck in skin tone.
- **Head:** circle r 48 at (100, 84).
- **Skin tones (`skin` 0–5):** `#F9D7C0` `#EDB98A` `#D08B5B` `#AE5D29` `#7B4A2E` `#4A2F22`.
- **Hair colours:** black `#1C1C1C`, brown `#5A3825`, blonde `#E6C36A`, red `#B5462B`, gray `#9AA0A6`, white `#E8E8E8`. Six distinct `hair_style` silhouettes; `bald` draws none.
- **Age:** `child` scales the head ×1.12 and the body ×0.8; `elder` adds two 3 px `inkMuted` wrinkle lines and forces hair to `gray` if it is `black` or `brown`.
- **Headwear:** `hat`, `crown` (`highlight`), `military_cap`, `helmet`, `headscarf` (in the cast colour, covering the hair). `glasses` = two 18 px round rims, 4 px `#1C1C1C`. `facial_hair` `beard` / `mustache` in the hair colour.
- **Features:** eyes are two r 5 dots at (82, 86) and (118, 86), `#1C1C1C`. Brows and mouth are 5 px round-cap strokes whose shapes are set by **expression**: `neutral`, `happy`, `sad`, `angry`, `shocked`, `confused`, `smug`, `nervous`. Every expression must be recognisable at 140 px (the dialogue size); the gallery `typical` fixture of `emotion_beat` renders all eight side by side for review.
- **No outlines on filled shapes**; strokes are for features only.

**Persistence is the point:** one cast member renders identically in every scene except for expression. There is no per-scene avatar randomness.

---

## 7. Illustration generation (places and set pieces only)

**Never for cast.** See `design_data_contracts.md` §3 for why.

| Setting | Value |
|---|---|
| Tool | `mflux-generate-flux2-klein` (installed with `uv tool install mflux`), **4B** weights. Verify the model variant with `--help` and the download path; the 9B is non-commercial and **must not** be used. |
| Size | **1024 × 1024** |
| Steps | **4** |
| Quantize | **8** |
| Seed | `int(sha256(prompt.encode()).hexdigest()[:8], 16) % 2**31`, so the same prompt gives the same image in every job |
| Timeout | **180 s** per image |
| Budget | places ≤ 4 + set pieces ≤ 3 = **≤ 7 images per job** (bible caps) |

**Prompts:**

```
PLACE     = "{visual_description}. Wide establishing view of the place, no people in the foreground. {STYLE}"
SET_PIECE = "{visual_description}. One clear central subject. {STYLE}"
STYLE     = "Flat vector editorial illustration, bold simple geometric shapes, smooth flat colour fills,
             no gradients, no outlines, limited palette of deep navy, warm orange, teal, mustard yellow
             and coral, clean uncluttered composition, plain background. No text, no letters, no words,
             no numbers, no watermark, no logo."
```

(`STYLE` is one line in code; wrapped here for reading.)

**Cache:** `cache/images/<key>.png`, key = SHA-256 of canonical JSON `{tool, model, prompt, width, height, steps, seed, quantize, mflux_version}`. A cache hit copies the file into `jobs/<id>/assets/images/<entity_id>.png`. `assets/manifest.json` records per entity: `{id, prompt, cache_key, status: "generated"|"cached"|"failed", elapsed_ms, error}`.

**Failure is not fatal:** a non-zero exit, a timeout or an unreadable PNG sets `status: "failed"` and `image: null` in the timeline, and the template draws its icon fallback. `preview/report.json` lists the failures so the reviewer sees them.

**Model choice is open** (`ongoing_general_errors.md` Issue 2): item A20 produces a side-by-side contact sheet of FLUX.2 klein 4B versus Z-Image-Turbo on the fixture prompts, with timings. The default stays klein 4B until the user selects.

---

## 8. Captions

| Property | Value |
|---|---|
| Font | Poppins 800, **76 px** → min 60 px (FitText), max **2 lines**, box width 900 |
| Colour | inactive `ink`; **active `highlight` + scale 1.12** (transform-origin bottom centre) |
| Stroke | 12 px `bgDeep`, painted *under* the fill (`paint-order: stroke fill`) |
| Position | centred in the caption band (vertical centre y 1340) |
| Page entrance | 4 frames: scale 0.92→1, opacity 0→1 |
| Case | as written (no forced uppercase) |

Paging and timing rules: `design_audio_and_timing.md` §8.

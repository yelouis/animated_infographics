# Rendering

This document owns: the **Remotion project**, the **clock abstraction**, the `Story` and `Gallery` compositions, **scene spans and transitions**, **overflow detection**, the **sync probe**, the **render CLI** Python calls, **preview** (stills, contact sheet, storyboard.md), the **final render** settings and **output verification**.

---

## 1. Project

`renderer/` is a standalone Remotion 4.x TypeScript project (`npm ci`). Compositions registered in `src/Root.tsx`:

| Id | Size | Purpose |
|---|---|---|
| `Story` | 1080×1920 @ 30 | Everything real. `inputProps` = the full `timeline.json`. |
| `Gallery` | 1080×1920 @ 30 | Renders one template fixture (`inputProps: {template, variant}`) inside a synthetic one-scene timeline. Used by the gallery gate and golden stills. |

`Story.calculateMetadata`: validate `inputProps` with Ajv against `schema/timeline.schema.json` (throw on failure, message includes the first 10 Ajv errors), then return `durationInFrames = timeline.duration_frames`.

**Node version:** the machine has Node 26. If Remotion's bundler or renderer fails on Node 26, pin **Node 22 LTS** for `renderer/` (`.node-version`, installed via `fnm`) and record it in the execution guide's accepted-equivalents list. Do not patch Remotion.

---

## 2. Render CLI used by Python (`renderer/scripts/render.ts`)

Invoked as `npx tsx scripts/render.ts <mode> --job <job_dir> [options]` with `cwd=renderer/`:

| Mode | Options | Output |
|---|---|---|
| `stills` | `--frames <json file: [{"scene_id","frame","out"}]>` `--scale 0.5` | One PNG per entry |
| `media` | `--out <path.mp4>` `[--scale 0.5] [--crf N] [--sync-probe]` | MP4 |
| `gallery` | `--out-dir <dir>` | One PNG per template × variant at its hold frame |

**Bundling:** one `bundle()` per invocation with `publicDir` = a freshly assembled `<job_dir>/render_public/` containing a copy of `renderer/public/*` plus a `job/` subtree (the job's `audio/` and `assets/images/`), **and nothing else**. The repository's `fixtures/` are never copied into a job's bundle. *(Clarified September 25, 2026: the first implementation copied all fixtures into every render, a test affordance in the production path.)* The smoke timeline's test assembles its own temporary job directory containing a copy of `fixtures/music/test_bed.wav` at `audio/narration.wav`. Timeline `src` paths (`job/audio/narration.wav`) resolve with `staticFile()`. Every `stills` entry and every media frame shares one bundle and one browser instance (`openBrowser` once, pass `puppeteerInstance`).

**Browser logs:** every call passes `onBrowserLog`. Lines are appended to `<job_dir>/logs/render_browser.log`. Lines matching `^OVERFLOW ` are also collected and written to `<job_dir>/logs/overflow.json` as `[{"scene_id","template","slot"}]`, de-duplicated.

**Exit codes:** 0 ok · 2 invalid timeline · 6 overflow detected in `gallery` mode · 1 anything else. In `stills`/`media` mode an overflow does **not** change the exit code. Python reads `overflow.json` and applies the rule in §7.

---

## 3. The clock abstraction (live-mode readiness)

```ts
// src/clock/types.ts
export type SceneClock = {
  frame: number;          // since scene start; float-safe (live mode will pass fractional frames)
  fps: 30;
  sceneFrames: number;    // end_frame - start_frame
  phase: "enter" | "hold" | "exit";
  enterProgress: number;  // 0..1 over ENTER_FRAMES
  exitProgress: number;   // 0..1 over EXIT_FRAMES after sceneFrames; 0 before
};
export type GlobalClock = { frame: number; fps: 30 };
```

- Templates and components read time **only** through `useSceneClock()` / `useGlobalClock()` from `src/clock/`.
- The Remotion adapter (`src/clock/remotion/`) is the **only** code allowed to call `useCurrentFrame`, `useVideoConfig`, or render `<Sequence>`/`<Series>`.
- Templates must not assume `frame` is an integer.

**`scripts/check_renderer_purity.sh`** (a gate). It exits 1 if any of these match under `renderer/src/` **outside** `src/clock/remotion/`:
`useCurrentFrame` · `useVideoConfig` · `<Sequence` · `<Series` · `Math.random` · `Date.now` · `new Date(` · `performance.now` · `fetch(` · `http://` · `https://`.
The patterns must be searched with fixed-string matching (`grep -rnF`) over **all** `.ts`/`.tsx` files. **It must be falsified once:** add `useCurrentFrame()` to one template, see exit 1, revert, see exit 0. Record both runs in the commit body.

---

## 4. Scene spans and transitions

For scene `k` with `[start_frame, end_frame)` from the timeline:
- It is mounted from `start_frame` for `min(end_frame + EXIT_FRAMES, duration_frames) − start_frame` frames.
- `phase = "enter"` while `frame < ENTER_FRAMES`; `"exit"` when `frame ≥ sceneFrames`; otherwise `"hold"`. (A scene shorter than `ENTER_FRAMES`, impossible given `BEAT_MIN_MS`, would be clamped.)
- **Z-order:** later scenes on top. The outgoing scene's exit plays *underneath* the incoming scene's entrance for 8 frames, which gives a transition with no dead frames and **no shift in timing**.
- **Why not `@remotion/transitions` `TransitionSeries`:** it overlaps sequences by *shortening* the total duration, which would drift every later scene away from the narration. Scenes here are placed at absolute frames; transitions are drawn by the templates' own enter/exit.

**Layer order (bottom → top):** background · scenes · captions · sync probe (debug only).

---

## 5. Captions layer

Draws `timeline.captions.pages` with the styling in `design_visual_direction.md` §8, driven by the **global** clock. A page is drawn only while `start_frame ≤ frame < end_frame`, and not during frames inside a `hide_captions` scene's `[start_frame, end_frame)`.

---

## 6. Overflow detection (`components/FitText.tsx`)

`FitText` receives a slot spec from `templateRegistry.json`. On layout (`useLayoutEffect`), it steps the font size down in 2 px steps from `size_max` to `size_min` until `scrollHeight ≤ clientHeight` and `scrollWidth ≤ clientWidth` for a box of `box_width` × (`max_lines` × line-height × size). If it still overflows at `size_min`, it:
1. keeps `size_min` (never goes smaller),
2. sets `data-overflow="true"` and, **only when `timeline.debug` is present or the composition is `Gallery`**, draws a 6 px `danger` border,
3. calls `console.error("OVERFLOW scene=<id> template=<name> slot=<slot>")`.

Font loading must complete before measuring (`delayRender` until `document.fonts.ready`). Otherwise a fallback font measures the text and the result is meaningless.

---

## 7. Preview (`preview.py`)

1. **Hero frame** per scene: `start_frame + min(sceneFrames − 1, max(round(0.6 × sceneFrames), max(item_frames, default=0) + ENTER_FRAMES))`, so every list item has entered.
2. `render.ts stills` at scale **0.5** (540×960) → `preview/scene_<id>.png`.
3. **Contact sheet** (Pillow): 5 columns; each tile 270×480 (the still at half size again) plus a 44 px label strip reading `s004 · stat_callout · 0:12.4` (scene start as m:ss.t). The label strip is `danger` for any scene with an overflow, `fallback_level 2`, or a failed image, and `bgRaised` otherwise. → `preview/contact_sheet.png`.
4. `preview/storyboard.md`: first the **voice line** for text inputs (exact formats in `design_planner.md` §10; audio inputs print `Voice: (recorded audio)`), then a Markdown table `| scene | time | template | beat text | key props | flags |`, flags from the same three conditions.
5. `preview/report.json`: `{"overflow": [...], "fallback_scenes": [...], "failed_images": [...], "plan_sha256": "…"}`.
6. `--preview-video`: `render.ts media --scale 0.5 --crf 28` → `preview/preview.mp4`.

**`approve` refuses (exit 3) while `report.json.overflow` is non-empty**, with the message `text overflows in <ids> — shorten it in storyboard.json and run preview`. Broken text must never reach an approved render. Fallbacks and failed images are warnings only.

---

## 8. Final render and output verification (`render.py`)

`renderMedia` settings:

| Option | Value |
|---|---|
| `codec` | `h264` |
| `crf` | **18** |
| `pixelFormat` | `yuv420p` |
| `imageFormat` / `jpegQuality` | `jpeg` / **90** |
| `audioCodec` / `audioBitrate` | `aac` / `"192k"` |
| `concurrency` | Remotion default (record the effective value in the log) |

**Audio** is mixed by Remotion from `timeline.audio`: narration from frame 0 at volume 1; music looped at `volume` with the fade-in/out envelope as a volume callback; each SFX in its own sequence at its `frame` and `volume`. Use the audio component the installed Remotion version documents as current; record which in the commit body.

**`out/verify.json`**: every check is asserted and `render` exits 1 if any fails:

| Check | Tool | Bar |
|---|---|---|
| Video stream | ffprobe | h264, `yuv420p`, 1080×1920, `r_frame_rate` 30/1 |
| Frame count | ffprobe `-count_frames` | == `timeline.duration_frames` |
| Audio stream | ffprobe | aac, 48000 Hz |
| A/V duration | ffprobe | \|audio − video\| ≤ **50 ms** |
| Loudness | `ffmpeg -af ebur128=peak=true` | integrated ∈ **[−18, −14] LUFS**, true peak ≤ **−0.5 dBTP** |
| Non-blank | ffmpeg `signalstats` at 5 evenly spaced frames | luma std-dev > 2 on every sample |

**Sync probe** (`--sync-probe`, used by the E2E gate, never by `infographics render`): the Story layer draws a 48×48 square at (0, 0), `#000000` while the current scene index is even and `#FFFFFF` while odd. "Current scene" is the one whose `[start_frame, end_frame)` contains the frame. The E2E gate samples pixel (24, 24) at `start_frame − 1` and `start_frame + 1` for every scene `k ≥ 1` (ffmpeg `select` → rawvideo) and asserts the colours flip exactly there. **This is the test that scene timing survived compile, bundling and encoding**. A green unit test of `frames.py` cannot prove that.

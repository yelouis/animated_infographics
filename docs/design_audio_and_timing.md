# Audio & Timing

This document owns: **input ingest**, **text-to-speech**, **speech recognition**, **loudness**, **frame math**, **beat constraints**, **caption paging**, and the **music/SFX mix**. Every constant here is implemented once in `src/animated_infographics/config.py` under the same name.

---

## 1. Ingest

| Extension | Kind | Next stage |
|---|---|---|
| `.txt` | `text` | `voice` (`design_planner.md` §10), then `narrate` |
| `.mp3` `.wav` `.m4a` | `audio` | `transcribe` |
| anything else | — | exit 2 `unsupported input type: <ext>` |

**Text file format:** UTF-8. If line 1 is non-empty **and** line 2 is empty, line 1 is the **title** and the body starts at line 3. Otherwise the whole file is body and there is no title sentence. Paragraphs are separated by one or more blank lines. `--title` overrides the title *text* for text input: the overridden title is narrated. For audio input, `--title` sets `bible.title` only.

Text normalisation before TTS (in this order): convert CRLF to LF; replace curly quotes `“ ” ‘ ’` with `" " ' '`; collapse runs of spaces/tabs to one space; strip each line. **Nothing else is rewritten.** Numbers, currency and abbreviations go to Kokoro as written.

Empty body after normalisation → exit 2. Body longer than **1,200 words** → exit 2 `input too long for MVP (max 1200 words)`. That is about 8 minutes of narration, above the 1–3 minute target, and the cap keeps the budget in §9 honest.

`ingest.json`: `{"schema_version":1,"kind":"text"|"audio","source":"input/<file>","title":str|null,"paragraphs":[str]|null,"word_count":int|null,"music":"input/<file>"|null,"sfx_dir":"input/sfx"|null}`. `music` and `sfx_dir` are the job-local copies that `compile` reads on every run (`design_system_architecture.md` §4).

---

## 2. Narration (text path): Kokoro

- **Sentence splitting:** `pysbd.Segmenter(language="en", clean=False)` per paragraph. The title (if any) is its own sentence 0 with `is_title: true`.
- **Synthesis:** one `KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M", device="cpu")` for the whole job; **one call per sentence**, voice = `voice.json.voice` (`af_heart` or `am_michael`, chosen by `design_planner.md` §10 or `--voice`), `speed=1.0`. Both voices are American English, so `lang_code="a"` serves both. A sentence may yield several `Result`s. Concatenate them in order, each result's timestamps offset by the samples already emitted for that sentence.
- **Pauses (silence inserted between sentence audio):**

| Constant | Value |
|---|---|
| `PAUSE_AFTER_TITLE_MS` | **800** |
| `PAUSE_BETWEEN_SENTENCES_MS` | **250** |
| `PAUSE_BETWEEN_PARAGRAPHS_MS` | **600** |
| `TAIL_SILENCE_MS` | **500** (appended after the last sentence) |

- Kokoro outputs **24 kHz**. The concatenated waveform is written as float32 WAV to `audio/narration_24k_raw.wav` (kept; it is what the exact-offset test measures), then resampled and normalised in one ffmpeg pass (§5) to `audio/narration.wav` at **48 kHz mono s16**.
- `narration.json`: `{"schema_version":1,"voice":"am_michael","sentences":[{"i":0,"start_ms":0,"end_ms":1420}]}`. These offsets are **exact**: computed from sample counts, not measured.

**Word timings come from Kokoro itself** (`Result.tokens`: `MToken.text`, `.start_ts`, `.end_ts`, `.whitespace`, in seconds relative to that result). They are ground truth, because they are the durations the model generated. Token → word rules:
1. A token with no letters or digits (punctuation) is **appended** to the previous word's text and does not create a word. If it is the first token of a sentence, prepend it to the next word.
2. A word token with `start_ts`/`end_ts` of `None` gets timings **linearly interpolated** between its timed neighbours within the sentence. If it is at a sentence edge, it gets the sentence edge.
3. Word `start_ms`/`end_ms` = round-half-up of (sentence offset + result offset + ts) × 1000.
4. Enforce the transcript invariants (`design_data_contracts.md` §2): if `start_ms[i] < end_ms[i-1]`, set `end_ms[i-1] = start_ms[i]`; if then `end_ms <= start_ms`, set `end_ms = start_ms + 40`.

`transcript.json.source = "tts"`.

---

## 3. Transcription (audio path): Whisper

```python
mlx_whisper.transcribe(
    "audio/narration.wav",
    path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
    word_timestamps=True, language="en", temperature=0.0,
    condition_on_previous_text=False,
)
```

- The input is first converted and normalised by §5 into `audio/narration.wav`; Whisper transcribes **that** file, so ASR timings and the rendered audio share one timebase.
- Words come from `segments[].words[]` (`word`, `start`, `end`). Strip each word's leading space. Drop words whose stripped text is empty.
- **Sentence boundaries:** a sentence ends after a word whose text ends in `.` `?` `!` (optionally followed by any of `"'”’)`), **unless** the word (casefolded, without trailing quotes) is in `ABBREVIATIONS = {"mr.","mrs.","ms.","dr.","st.","vs.","jr.","sr.","u.s.","u.k.","e.g.","i.e.","etc.","no."}`. Paragraphs: a new paragraph starts where the gap between consecutive words is ≥ **1,200 ms** (`ASR_PARAGRAPH_GAP_MS`). No sentence is `is_title`.
- Apply invariant rule 4 from §2.

`transcript.json.source = "asr"`.

**Accuracy bar** (measured on fixtures, `design_testing_and_validation.md` §2): on the `say`-voiced `molasses_flood` fixture, normalised WER ≤ **8%**. On Kokoro-generated audio of `molasses_flood`, Whisper word-start error against Kokoro's own timestamps: median ≤ **80 ms**, p95 ≤ **250 ms**. These bars say how far live mode and audio input can be trusted for sync. Record the measured numbers, not just pass/fail.

---

## 4. Word text conventions

`words[].text` is what captions display. Text path: the source spelling (`$1,500`, `AITA`, `Meredith's`). Audio path: Whisper's spelling. Captions never re-case, re-spell or strip punctuation.

---

## 5. Loudness and format (ffmpeg)

**Narration:** two-pass `loudnorm` to integrated **−16 LUFS**, true peak **−1.5 dBTP**, LRA 11; output `-ar 48000 -ac 1 -c:a pcm_s16le`.

**Music** (`--music`): two-pass `loudnorm` to **−16 LUFS**, true peak −1.5 dBTP, output 48 kHz **stereo** s16 → `audio/music.wav`. In the mix it plays at `MUSIC_VOLUME = 0.126` (−18 dB), looped, with `MUSIC_FADE_IN_FRAMES = 30` and `MUSIC_FADE_OUT_FRAMES = 60` at the end of the video.

**SFX** (`--sfx-dir`): files are grouped by **role** = filename prefix before the first `_`, `-`, digit or `.`, casefolded. Roles: **`whoosh`**, **`pop`**, **`ding`**, **`hit`**. Other prefixes are ignored with a warning. Each file is peak-normalised to **−3 dBFS** (`volumedetect` then `volume`), converted to 48 kHz stereo s16 → `audio/sfx/<role>_<n>.wav` (n = 0-based index in sorted filename order). It plays at `SFX_VOLUME = 0.35`. `loudnorm` is **not** used on SFX: two-pass loudness on sub-second clips is unreliable.

**Final mix target** (verified on the rendered MP4): integrated loudness in **[−18, −14] LUFS**, true peak ≤ **−0.5 dBTP**.

---

## 6. Frame math (`timing/frames.py`: the only ms↔frame conversion)

| Constant | Value |
|---|---|
| `FPS` | **30** |
| `LEAD_MS` | **200**: a scene appears this long *before* its first word; anticipation reads as sync |
| `END_HOLD_MS` | **1500**: hold after the last word before the video ends |

- `ms_to_frame(ms) = floor(ms * FPS / 1000 + 0.5)` (round-half-up; never Python's banker's `round`).
- Scene `k` start: `scene_start_frame[0] = 0`; for `k ≥ 1`: `max(scene_start_frame[k-1] + 1, ms_to_frame(beat[k].start_ms - LEAD_MS))`.
- Scene `k` end (exclusive) = scene `k+1` start; the last scene ends at `duration_frames`.
- `duration_frames = ms_to_frame(max(transcript.duration_ms, words[-1].end_ms + END_HOLD_MS))`.
- **Captions are never shifted by `LEAD_MS`.** Only scenes lead; the highlighted word must match the voice exactly.

---

## 7. Beat constraints (`timing/beats.py`, deterministic, no LLM)

| Constant | Value |
|---|---|
| `BEAT_MIN_MS` | **1500** |
| `BEAT_TARGET_MIN_MS` / `BEAT_TARGET_MAX_MS` | **2500** / **6000** (prompt guidance only) |
| `BEAT_MAX_MS` | **8000** |

Input: sentence groups from the LLM (`design_planner.md` §4), or one group per sentence as the fallback. Algorithm, in this order:

1. **Build** beats from groups. The title sentence (if any) is always its own beat 0, whatever the groups say.
2. **Merge pass.** Repeat while some beat `k ≥ 1` has duration < `BEAT_MIN_MS`: merge it with whichever neighbour yields the smaller combined duration (ties → the previous one). Beat 0 is never a merge target and is exempt from the minimum.
3. **Split pass.** Repeat while some beat has duration > `BEAT_MAX_MS`: consider every inter-word boundary inside it where **both** halves would be ≥ `BEAT_MIN_MS`. Score = `gap_ms + (1000 if the left word ends in , ; : — or -- else 0) − |t_boundary − t_midpoint| / 4`. Split at the maximum score (ties → earlier boundary). If there is no candidate, leave the beat long and log `beat <k> exceeds BEAT_MAX_MS with no valid split`.
4. **Bounds.** `start_ms` = first word's `start_ms` (beat 0: 0); `end_ms` = next beat's `start_ms`; last beat's `end_ms` = last word's `end_ms`.

Durations in steps 2–3 are measured on the *tiled* bounds from step 4 (recomputed after every merge/split).

---

## 8. Caption paging (`timing/captions.py`, deterministic)

| Constant | Value |
|---|---|
| `CAPTION_MAX_WORDS` | **3** |
| `CAPTION_MAX_CHARS` | **22** (characters including single spaces between words) |
| `CAPTION_MAX_GAP_MS` | **700** |
| `CAPTION_TAIL_MS` | **300** |

Per sentence (**pages never cross a sentence boundary**):

```
page = []
for w in sentence.words:
    if page and (len(page) == CAPTION_MAX_WORDS or len(" ".join(p.text for p in page + [w])) > CAPTION_MAX_CHARS):
        emit(page); page = []
    page.append(w)
    if w.text ends with one of , ; : — and len(page) >= 2:
        emit(page); page = []
emit(page) if page
```

A single word longer than 22 characters is its own page. Page timing: `start = first word start_ms`; `end = next page start` if `next start − last word end ≤ CAPTION_MAX_GAP_MS`, else `last word end + CAPTION_TAIL_MS`. The final page ends at `last word end + CAPTION_TAIL_MS`. Pages are emitted in frames (§6) into `timeline.json.captions.pages`.

**Active word:** within a page, word `j` is active from its `start_frame` until the next word's `start_frame` (the last word until the page end). Before the first word's start nothing is active; that cannot happen, because pages begin at the first word's start.

**Hidden captions:** a scene's `hide_captions` is `true` **iff** its template is `title_card` and every sentence in its beat has `is_title: true`. The narrated title is already on screen as the title. Captions whose page overlaps a hidden scene are not drawn for those frames.

---

## 9. SFX scheduling (`compile.py`)

Cues come from each template's registry `sfx_cues` (`design_templates.md`), resolved to absolute frames, e.g. `at="start"` → the scene start frame; `at="item"` → each item's appear frame; `at="count_end"` → start + `COUNT_FRAMES`. Then:
1. Drop cues of scenes with `mute_sfx: true`, and cues whose role has no files.
2. Sort by frame; **drop any cue within `SFX_MIN_GAP_FRAMES = 24` (0.8 s) of the previous kept cue.**
3. File choice per role: round-robin over that role's files in order of appearance (`n = k mod count`).

No music or SFX flags → `audio.music = null`, `audio.sfx = []`. The narration always starts at frame 0.

---

## 10. Budget

End-to-end performance bars are in `design_testing_and_validation.md` §5. For this document's stages on the 2-minute `emu_war` fixture: `narrate` ≤ **60 s**; `transcribe` of 2 minutes of audio ≤ **45 s**. Both are measured on the M4 Max and recorded.

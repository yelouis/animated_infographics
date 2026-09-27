# Future: Live Mode, Video Input, 16:9

None of this is approved for build. It exists for two reasons: (1) to record the **end goal** so the MVP does not paint itself into a corner, and (2) to list the **constraints the MVP must honour now**, each already enforced by a gate or a contract elsewhere.

**The end goal (user, September 23, 2026):** speak in real time, with no pre-recorded video, and a video plays behind you that visually explains what you are saying, like live captioning but as infographics. The first live layout is **the infographic full-frame with the speaker's webcam in a corner**. Separately, existing videos (lectures) become inputs, with the original shown in a corner.

---

## 1. Constraints the MVP honours now

| # | Constraint | Enforced by |
|---|---|---|
| F1 | Templates are pure functions of (props, scene clock). No Remotion frame APIs outside `src/clock/remotion/`. | `check_renderer_purity.sh` (G9) |
| F2 | A template never reads another scene, the full timeline, or the future. It needs only its own props plus the entity dictionaries. So scenes can be appended one at a time. | `design_data_contracts.md` §7; code review |
| F3 | Planner selection is **windowed** (6 beats plus 2 previous) and props are **per scene**. Both already work on partial transcripts. | `design_planner.md` §4–5 |
| F4 | Every piece of timing logic (beats, captions, frames) is a pure function of a word list, so it can run on a growing word list. | `timing/` unit tests |
| F5 | Transcript words carry absolute ms; nothing assumes the transcript is complete except `duration_frames` and the final beat's end. | `design_audio_and_timing.md` |
| F6 | No `--auto-approve` for *offline* jobs. Live mode is a different product surface with no review gate by nature, and must be a separate command, not a flag on `render`. | `design_system_architecture.md` §5 |

---

## 2. Deferred: video input with picture-in-picture (DF1)

- Input `.mp4`/`.mov` → ffmpeg extracts audio → the existing `transcribe` path. The renderer shows the source video with `<OffthreadVideo>` in a PiP box, audio muted (the narration track is the extracted audio).
- **The open design question (user's call when DF1 is selected):** where the PiP sits in **9:16**. The caption band (y 1220–1460) and the bottom reserve (y 1500+) are both spoken for. Candidate options: (A) a 16:9 PiP 480×270 inside the stage's bottom-left, shrinking the stage to y 140–880; (B) move captions into the stage and put the PiP in the caption band; (C) PiP only in 16:9 output. That decision gets filed as an issue with mock-ups at the time.

---

## 3. Deferred: 16:9 output (DF2)

Every template needs a second layout; the registry's `TextSlot`s become per-aspect; the layout zones get a 16:9 table; the gallery gate doubles. It is a separate wave because it roughly doubles the template work.

---

## 4. Deferred: live mode (DF4): a sketch, not a spec

```
mic ─► streaming ASR (local) ─► word stream ─► live beat closer ─► selector+props (1 call)
                                                                      │
 webcam (getUserMedia) ─┐                                              ▼
                        └──► browser app: same templates, rAF-driven clock ◄── scene specs over WebSocket
                                   │
                                   └──► fullscreen window / OBS browser source / virtual camera
```

- **ASR candidates** (to be measured when DF4 starts): an MLX Whisper streaming wrapper (word timestamps on a ~200 ms cadence were reported in April 2026) and `parakeet-mlx`. The selection criterion is word-final latency and WER on the fixtures, measured, not assumed.
- **Beat closer:** close a beat at sentence-final punctuation from the ASR, or at a pause ≥ 600 ms, or at 8 s. That is the same `BEAT_MAX_MS`.
- **The latency reality:** a beat cannot be planned before it has been said. With a MoE model at the MVP's speed, visuals will lag speech by roughly **2–4 s**. Two mitigations to evaluate: (a) show an immediate `kinetic_quote` of the live words, then upgrade to the planned template when it arrives; (b) **prepared mode**: if the speaker has a script or outline, plan every scene in advance with the offline planner and, live, only *match* speech to the next planned scene. That gives near-zero lag and full quality.
- **Rendering:** the templates run unchanged in a plain React app. The clock adapter swaps `useCurrentFrame` for a `requestAnimationFrame` counter (F1 is what makes that a small change). Remotion is not needed live.

**User direction for live presentations (September 27, 2026), verbatim:** *"For real-time presentations, it makes sense to show timelines and repeated graphics to drive home the point."* So live mode gets its **own** visual profile when DF4 is specced:
- Timelines stay a first-class device.
- Graphics may **recur** to reinforce a point, e.g. the same timeline returning with the next event highlighted. The offline no-repeat rule R2 (`design_planner.md` §4) and any per-video template limits do not carry over.
- Any word-density limits chosen for offline **story** videos (Issue 7 in `ongoing_general_errors.md`) do not apply to live mode.

**Questions for the user when DF4 is selected:** improvised or scripted talks (decides between mitigations (a) and (b))? Where does the output go (fullscreen, OBS, Zoom virtual camera)? What lag is acceptable?

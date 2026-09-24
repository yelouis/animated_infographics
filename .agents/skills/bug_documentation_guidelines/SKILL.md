---
name: Bug Documentation Style Guide
description: A strict style guide for filing issues, decisions awaiting the user, and resolved work in the animated_infographics project's docs/ongoing_general_errors.md. Follow this to keep the engineering history consistent and machine-readable.
---

# Bug and Decision Documentation Style Guide

This guide defines how issues, open decisions and resolved work MUST be recorded in [ongoing_general_errors.md](../../../docs/ongoing_general_errors.md). It keeps the history transparent and actionable for both the user and AI agents.

## 1. Resolved work

Delivered items go in `## 3. Resolved index`, **one line each**, added in the same commit as the work:

```
A7 — Narration (Kokoro) — 1a2b3c4 — emu_war narrate 41 s; offsets exact to the sample; −16.1 LUFS
```

- The detailed *why* lives in the commit body; the *design consequence* lives in the relevant `docs/design_*.md`. The index line is a pointer, not a history.
- Name the key measured numbers. "Done" is not a result.

## 2. Unresolved issues and decisions awaiting the user

Placed under `## ⚠️ Unresolved Issues & Suggestions`.

### Mandatory structure
- **Issue heading:** `### Issue [Number]: [Title]`. Numbers are never reused.
- **Status line:** `**Status**: ⚠️ <Confirmed Unresolved | Awaiting evidence | Blocked> — <what was verified, where (file:line, command, measurement)>`.
- **Options:** `**Option A (recommended)**: **Name** — description`, then Option B, and so on. An easy issue may have one option; a hard one needs several viable paths.
- **Pros/Cons:** every option has `*Pros*` and `*Cons*` bullets that are technical and specific ("adds ~40 s per image on the M4 Max", "breaks the Pillow/Chrome fit parity").
- **Selection line:** end every issue with `Your selection: _____`. **Only the user fills this in. An agent never does, not even with the recommended option.**
- **Separation:** `---` between issues.

### Style constraints
- **Evidence, not opinion.** The status line cites the measurement or source that shows the problem (`docs/evals/planner_2026-10-02.md: fallback_level 2 = 22% on emu_war, bar 15%`).
- **No placeholder options.** Every option must be implementable as written.
- **A failing bar is filed, not tuned away.** If an eval, budget or gate misses its bar, the issue records the measured value next to the bar. "Relax the bar" may be an option, but only as an explicit choice for the user.

## 3. Example

```markdown
### Issue 3: Planner fallback rate above bar on emu_war

**Status**: ⚠️ Confirmed Unresolved — `docs/evals/planner_2026-10-02.md`: 9 of 38 scenes (23.7%) reached fallback_level 2 against a 15% bar. 7 of the 9 were `timeline` props failing date grounding: the model writes "Nov. 2nd" while the transcript says "November 2".

**Option A (recommended)**: **Normalise ordinal suffixes in grounding** — strip `st|nd|rd|th` after digit runs in `planner/grounding.py` before matching.
  - *Pros*: Fixes 7 of the 9 without touching the prompt; still exact on the digits themselves.
  - *Cons*: Needs a new unit case per suffix; still leaves 2 unrelated failures.

**Option B**: **Prompt the planner to copy dates verbatim** — add a writing rule to `timeline`'s registry entry.
  - *Pros*: No change to the validator's strictness.
  - *Cons*: A local model follows it inconsistently; requires a full eval re-run to show an effect.

Your selection: _____
```

## 4. Enforcement
- Before closing an item, check that `ongoing_general_errors.md` follows this guide.
- When a resolved item changes documented behaviour, update the `design_*.md` that owns it **in the same commit**. A fix whose design doc still describes the old behaviour is not finished.

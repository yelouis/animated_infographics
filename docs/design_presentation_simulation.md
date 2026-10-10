# Presentation Simulation

This document owns the **presentation simulation**: the first step toward live presentations (`design_future_live_and_video.md` §4, DF4), in its *prepared mode*.

**The user's direction (October 5, 2026), verbatim:**
- The goal: *"This should build towards a version where I can pass in a powerpoint or a google slides and then give a presentation where the powerpoint/google slides are references for the animation to be built around. In a real presentation, you will not know the transcript and what will be said in the moment but you will know the rough powerpoint which contains all the talking points. This will allow you to create a tree of animations that will link each slide to each other as the real time voice is being said."*
- The simulation: *"To imitate this, you can take the transcript right now and create a couple of slides from the transcript (key moments) and use that as the power point, then you can create the tree of animations that links each slide together. Then perform some flair on the original transcript (perturb the transcript a bit like how a real presentation does not follow a strict transcript) and see what video generates from it. Then we can still run similar analysis that analyzes if the final outputted video was done well."*
- On slide import: *"Don't worry about this part for now. I was just explaining the potential future. We do not need to build this out now."*

**Out of scope:**
- reading `.pptx`, PDF or Google Slides;
- a real-time player, microphone or webcam.

**In scope:** everything below runs offline and produces a rendered video and a score.

---

## 1. The command and the job

`infographics present-sim <script.txt> --style literal|creative --perturb mild|strong --seed <int> [--matcher bm25|anticipate|llm] [--jobs-dir …]` creates a **presentation job** (`kind: "presentation"` in `state.json`). The job runs these stages and stops at the review gate like any job:

```
script ──► deck ──► deck_bible ──► tree ──► anticipate ──┐   (anticipate: only with --matcher anticipate, §6.6.1)
   │                                                       ▼
   └──► perform ──► speak ──► hear ──► follow ──► compose ──► preview ─(review)─► render ──► score
```

- **`deck` and `tree` never see the performance**, and the tree never sees the script (§3). This is the honest part of the simulation: at presentation time, only the deck is known.
- **`perform`, `speak` and `hear` stand in for the live speaker.**
- **`follow` is the only component that would run live.** It sees only what was *heard*: ASR words with timestamps.
- **`score` uses the ground truth** that `perform` records. Nothing upstream of `score` may read it; a test asserts that `follow`'s inputs are only `tree.json`, the ASR words and, for the `anticipate` matcher, `anticipation.json` (itself built from the deck only).

Every stage obeys the standing rules: job-local inputs, `run_with_retries`, stage logs ending in `llm_calls=… cache_hits=… elapsed_ms=…`, and invalidation by input hash.

---

## 2. `deck`: slides from the script (imitating the user's PowerPoint)

**Input:** the script's sentences, numbered (the ingest sentence list; no narration needed).

**One LLM call** (`run_with_retries(stage="deck", num_predict=1536)`, temperature 0.3) produces `deck.json`:

```json
{"slides": [{"id": "d1", "title": "London cannot breathe",
             "points": [{"text": "Summer 1858: the Thames is an open sewer", "sentence_ids": [1, 2, 3]},
                        {"text": "Parliament soaks its curtains in lime", "sentence_ids": [4, 5, 6]}],
             "sentence_ids": [1, 2, 3, 4, 5, 6]}]}
```

**Rules** (validators; a violation is a retry message):
1. **Slide count:** `round(words / 100)`, clamped to 4–10. That is 7–8 for the new 675–755-word fixtures, like a real deck of key moments.
2. **Points:** 2–4 per slide.
3. **Lengths:** `title` ≤ 6 words; a point's `text` ≤ 12 words.
4. **Coverage:** slides' `sentence_ids` are contiguous, in order, and **partition** every sentence except the title (sentence 0). Each slide's points partition its sentences the same way. *This partition is the ground truth that maps the script to slides and points.*
5. **Grounding:** every digit run in a title or point is grounded in its own sentences (`digits_grounded`, `design_planner.md` §8).
6. **Text checks:** the placeholder/instruction rule and the internal-id rule apply. No quotation marks.

`deck.json` is shown on the contact sheet's first page as a slide list, so the reviewer sees the "PowerPoint".

---

## 3. `tree`: the animation tree, built from the deck only

**The presentation profile.** Per the user's September 27 direction, *"For real-time presentations, it makes sense to show timelines and repeated graphics to drive home the point"*:
- per-video template limits (R6) and the rhythm rule (R7) **do not apply**;
- R2 (no consecutive repeats) does not apply either;
- the word budget, every validator and the critic **do** apply;
- the style (`literal` or `creative`) applies as in `design_styles.md`. Creative's director runs over the point list instead of beats.
- **R1 is skipped too** (accepted October 6, 2026): `section_title` replaces the title card. Its second half still holds as an assertion: **no point node may use `title_card`**, and the tree stage replaces one with its alternate (`RuleRepair(rule="R1")`).

**Creative in a presentation job (spelled out October 6, 2026; lesson 2.16).** Everything that travels with the director in a video job travels with it here:
1. **The director** runs over the points in deck order: point k is beat k, the first point is beat 0 and carries nothing, and `n` is the number of points. It writes `director.json`, and its counts (`design_styles.md` §3.3) are computed from that `n`.
2. **The license check** (`design_styles.md` §3.4) runs on every metaphor and aside, before selection. The passage is the point's slide (its title and all its points) in place of the four-beat passage, because the deck is the only text the tree may see. Failed and errored checks remove the item and are recorded in `director.json`'s `license_dropped` list, as in video jobs.
3. **Overlays** are computed by the same `compute_scene_overlays` over the point scenes in deck order, then stored in each node's `overlays`. `compose` copies a node's `overlays` into every timeline scene it emits for that node. `section_title` is not an allowed overlay template.
4. **The callback's dots** count the earlier point nodes, in deck order, that carry the motif's token.
5. **`logs/tree.log`** ends with `director=<ok|degraded> license_calls=<m> license_dropped=<d> overlays=<o>`, where `m` equals the number of metaphors and asides the director returned.
6. **Degradation is recorded, never silent.** If the director fails every attempt:
   - `tree.json` gets `"style_degraded": true`;
   - `logs/tree.log` prints `director: degraded to literal after <n> attempts: <last validator error>`;
   - the presentation report shows it.

   G16 treats a degraded creative run as a failure (`design_testing_and_validation.md` §4c), as G15 does through its creative bars.
- **Measured (October 6, 2026):**
  - `history_great_stink` creative/strong has 2 metaphor and 2 callback nodes, but its metaphors were never license-checked, and its timeline has 0 overlays.
  - `story_overdue_book` creative/mild has no `director.json` at all, and its template counts are identical to the literal run's. **The cause:** all 3 director attempts on the deck keep "A massive mountain of sand slowly burying a single small book", which rule 6 rejects. `design_styles.md` §3.3's salvage keeps the rest of the plan.

**The deck bible.** The tree needs a bible (cast, places and set pieces with avatars, geo and illustrations), but the script's bible would leak the transcript. So `tree` first runs the existing `bible` stage over the **deck text only**: slide titles and points joined as paragraphs. The result is `deck_bible.json`; geo, avatars and the illustration pipeline work on it unchanged.

**Nodes:**
- **A `section` node per slide.** It uses the new template **`section_title`** (`design_templates.md` §2.19): the slide title, plus a progress row of one dot per slide, current dot in `highlight`. *This is the repeated graphic.* It is built deterministically: no LLM, no critic.
- **A `point` node per point.**
  - Its scene is planned by the existing planner (select + props) with the **point text as the beat**, the slide title and its other points as context, and the deck as the only grounding text.
  - A synthetic one-beat-per-point "transcript" is built from the deck for grounding; no script or performance text is visible.
  - The critic runs on people scenes as usual, with the slide's points as the passage.
- **Node text for matching** = slide title + point text + the scene's free-text fields (`WORD_CAPS` fields), normalised (§6.2).

**Edges** (`tree.json`), with the transition cost the matcher uses:

| Edge | From → to | Cost |
|---|---|---|
| `next` | point k → point k+1 of the same slide; last point → next slide's `section`; `section` → its first point | 0.0 |
| `skip` | any node → any point of the **same or next two** slides that is ahead of it | 0.15 per point skipped, capped at 0.6 |
| `back` | any node → any **earlier** point | 0.5 |

A node with no matching edge cannot be reached in one commit.

**`tree.json`** has the shape `{"nodes": [{"id", "slide", "kind": "section" | "point", "point_i", "text", "scene": <Scene>, "overlays": [<SceneOverlay>]}], "edges": [{"from", "to", "kind", "cost"}], "style_degraded": false}`. `overlays` and `style_degraded` were added October 6, 2026; `overlays` is `[]` for literal trees and section nodes. Its scenes go through `assets` (illustrations) once, at tree time.

---

## 4. `perform`: the presenter's "flair" (simulated, seeded, labelled)

**Input:** the script sentences and `deck.json`, for the ground truth only. Seeded with `--seed`. It produces `performance.json`: an ordered list of performed sentences, each with its **ground-truth label**.

**Operations,** each applied with a seeded RNG at the rates below:

| Operation | `mild` | `strong` | How |
|---|---|---|---|
| **Paraphrase** a sentence | p = 0.4 | p = 0.8 | LLM, temperature 0.7. It must keep every number, name and quoted phrase (a validator checks that digit runs and capitalised names survive; on failure the sentence stays verbatim) |
| **Filler** ("um", "so", "you know", "basically", "right") | 1 per 40 words | 1 per 15 words | Deterministic, inserted at clause boundaries (after commas) or sentence starts |
| **Drop** a sentence | p = 0.05 | p = 0.15 | Never a slide's first sentence |
| **Swap** two adjacent sentences within a point | p = 0.05 | p = 0.15 | Deterministic |
| **Ad-lib tangent** | 1 | 3 | LLM: 1–2 on-topic sentences not in the deck ("I love this part, honestly."), inserted between points. Label `adlib` |
| **Back-reference** | 0 | 1 | LLM: one sentence referring back to an earlier slide's point ("Remember that pump handle?"), inserted ≥ 2 slides later. Label `{"back_ref": <point>}` |
| **Skip a whole point** | 0 | 1 | All of a point's sentences dropped; never the first slide's |

**Labels:**
- each kept or paraphrased sentence: `{"slide": "d3", "point": 1}`;
- an ad-lib: `"adlib"`;
- a back-reference: `{"back_ref": {"slide": "d1", "point": 0}}`.

**Validators:**
- the performance keeps ≥ 70% (mild) or ≥ 50% (strong) of the source sentences in some form;
- labels are consistent with the deck partition;
- the seed reproduces the same `performance.json` byte for byte.

`report.json` records the operation counts.

---

## 5. `speak` and `hear`: simulated live audio

- **`speak`:** Kokoro narrates the performance with the job's voice, by the voice rule (`design_planner.md` §10). It records **ground-truth timing**: each performed sentence's start and end in ms, from Kokoro's sentence offsets (`design_audio_and_timing.md`).
- **`hear`:** mlx-whisper transcribes that audio exactly as in the audio-input path. The ASR words and timestamps are **the only speech `follow` may use**, recognition errors included. This is what a live ASR would deliver.

---

## 6. `follow`: the live matcher, simulated

### 6.1 Streaming

`follow` consumes ASR words in time order. A **decision point** occurs:
- at the end of any word followed by a gap ≥ 300 ms, and
- otherwise at least every 1.5 s of audio.

At a decision point it sees only the words ended so far. It looks at a **window** of the last 20 words (fewer at the start). *Measured October 6, 2026: 20 words hold ≈ 8 s of speech, so a new point outweighs the old one only halfway through it. This window is one cause of Issue 8 (`ongoing_general_errors.md`). §6.1–§6.4 describe the **`bm25` matcher**, the baseline; the user selected Option A on October 7, 2026, and §6.6 specifies the two contestants and the rule that picks one.*

### 6.2 Scoring

- **Normalisation:** casefold; strip punctuation; drop a fixed English stopword list (in `presentation/match.py`, committed); apply the suffix stemming used by the Issue 6 measurement (`-s`, `-es`, `-ed`, `-ing`, `-ly`). Numbers are kept as tokens.
- **Lexical score of a node:** BM25 (k1 = 1.2, b = 0.75), with document frequencies computed over **all node texts of this tree**. The window is the query.
- **Total score:** `lexical(node) − cost(edge from current node → node)`. The current node scores with cost 0. A node unreachable in one edge is ineligible.

### 6.3 Committing, hysteresis and dwell

- The matcher **commits** a candidate as the new current node when **all** of these hold:
  - it has the top total score at **2 consecutive** decision points;
  - its score exceeds the current node's by **≥ 1.0** (BM25 units);
  - the current node has been shown for **≥ 2.0 s**.
- Otherwise the current scene **holds**. Scenes loop their hold motion indefinitely, so holding is always safe.
- **Before the first commit,** the first slide's `section` node is shown from t = 0.
- **Simulated latency:** a commit takes effect at the decision point's time **+ the matcher's measured compute time** for that decision. This is measured, not assumed, and recorded per decision.
- **No look-ahead:** a test feeds the same words with the future truncated, and the commits must be identical (the matcher is causal).

### 6.4 Optional LLM tie-break (measured, off by default)

When the top two candidates are within 1.0 of each other at a decision point, `follow --tiebreak llm` asks gemma4:26b, at temperature 0 with `num_predict` 16:

> `Which talking point is the speaker on now? Answer one id.`

It passes the window and the two candidates' point texts, and adds the call's measured time to the latency. **The default is off.** The tie-break becomes default only if, on all fixtures and both perturbation levels, it raises point accuracy by ≥ 5 points **and** keeps median lag within the bar (§8). The measurement and the decision are recorded in the eval report.

### 6.5 Output

`playback.json`: `[{"node": "<id>", "start_ms": int, "decided_ms": int, "latency_ms": int, "score_margin": float}]`, in time order.

`playback.json` also records `"matcher": "bm25" | "anticipate" | "llm"` (added October 7, 2026).

### 6.6 The follower bake-off (Issue 8 → Option A, selected by the user October 7, 2026)

**The finding** (Issue 8): the `bm25` matcher misses every accuracy bar while the oracle meets them. Two failures add up:
- a 12-word deck point and a paraphrase of it share too few words;
- the 20-word window holds ≈ 8 s of speech.

**The decision.** Build two followers from deck-only knowledge with the existing models, and adopt one by a fixed rule (§6.6.4). Nothing here may read the script, the performance or the ground truth. The isolation and causality tests cover both contestants.

**Frozen during the bake-off:**
- the scorer and every §8 bar;
- decision points (§6.1);
- normalisation and BM25 parameters (§6.2);
- simulated latency (§6.3);
- the tree, the deck, and the corpus's `perform`/`speak`/`hear` outputs.

Only the follower changes.

#### 6.6.1 Contestant A1: anticipated speech + forward tracker (`--matcher anticipate`; no LLM in the live loop)

**The `anticipate` stage** runs after `tree`, only when the job's matcher is `anticipate`. Otherwise it is skipped and writes nothing. It reads only `deck.json` and `tree.json`.
- **Calls:** one per node (section and point): `run_with_retries(stage="anticipate", num_predict=320)`, temperature 0.6, 3 attempts.
- **Point node prompt** (user message, verbatim):

  ```
  Here is one slide from a talk.
  Slide title: <slide title>
  Points on this slide:
  - <point 1>
  - <point 2>
  …
  The presenter is now covering this point: "<point text>"
  Write 4 different sentences the presenter might actually say out loud while covering this point. Use plain spoken English, the way a person talks, not slide text. Do not add facts that are not on the slide.
  ```
- **Section node prompt:** the same, with the last two lines replaced by `The presenter is now moving on to this slide.` and `Write 4 different sentences the presenter might say out loud to introduce this slide. Use plain spoken English, the way a person talks, not slide text. Do not add facts that are not on the slide.`
- **Schema:** `{"sentence_1": str, "sentence_2": str, "sentence_3": str, "sentence_4": str}`, all required, one key per item (lesson 2.9), with no length constraints given to the model.
- **Validators** (each failure is a retry message):
  - each sentence has 6–35 words;
  - no two sentences are equal, casefolded and stripped of punctuation;
  - no sentence equals the point text (for a section node, the slide title);
  - every digit run in a sentence occurs in the slide's title or points.

  Error strings:
  - `sentence_<k>: <n> words — write 6 to 35 words`
  - `sentence_<j> repeats sentence_<k> — write a different sentence`
  - `sentence_<k> copies the slide — say it the way a presenter would`
  - `sentence_<k>: "<digits>" is not on the slide — do not add numbers`
- **After 3 failed attempts** the node keeps 0 anticipated sentences. The log records `anticipate: <node id> failed: <last error>`. The job never crashes.
- **Output:** `anticipation.json`: `{"schema_version": 1, "nodes": {"<node id>": ["<s1>", "<s2>", "<s3>", "<s4>"]}}`. The log ends `anticipate: nodes=<n> filled=<f> failed=<x> llm_calls=… cache_hits=… elapsed_ms=…`.

**The tracker** (`follow` with `--matcher anticipate`):
- **Document per node:** the node's `text` (§3) followed by its anticipated sentences, joined by spaces. BM25 document frequencies and average length are computed over these documents.
- **Window:** the last **10** heard words (fewer at the start).
- **Candidates:**
  - the current node `c`;
  - the **forward set**, the next 3 nodes after `c` in deck order (section nodes included): `f1`, `f2`, `f3`;
  - the **back set**, every point node before `c` in deck order.
  
  Nothing else is eligible. `tree.json`'s edges and their costs are not used; they remain the `bm25` matcher's.
- **Score:** `BM25(window, doc) − cost`, with cost 0 for `c` and `f1`, 0.15 for `f2`, 0.30 for `f3`, and 0.5 for any back node.
- **Commit** (dwell ≥ 2.0 s on `c` is required in every case):
  - **Forward step:** the top candidate is `f1`, and `score(f1) − score(c) ≥ 0.5`, at **one** decision point.
  - **Any other move** (`f2`, `f3`, or a back node): the same node is top at **2 consecutive** decision points, and its score exceeds `c`'s by **≥ 1.5**.
  - Otherwise **hold**. Holds record their reason as in the `bm25` matcher.
- **Unchanged:** the first section is shown from t = 0, compute time is added to latency, and the matcher is causal.

#### 6.6.2 Contestant A2: LLM point classifier (`--matcher llm`)

At **each** decision point, one call: `generate_json(stage="follow_llm", temperature=0, num_predict=32)`, with no retries. A failed or invalid answer means **hold**, with reason `llm_error`.
- **Candidates:**
  - the current node `c`;
  - the next 3 nodes after `c` in deck order;
  - every point node before `c`.

  `tree.json`'s edges are not used.
- **Prompt** (user message, verbatim):

  ```
  You are following a live talk against its slide deck. You hear only the last few seconds of speech.
  The speaker is currently on: <c id> — <slide title>: <point text>
  Candidates:
  <id> — <slide title>: <point text>
  …
  Last words heard: "<the last 25 heard words>"
  Which point is the speaker on now? If they are between points, telling a side story, or you are unsure, answer the current point. Answer one id.
  ```
  A section node is listed as `<id> — <slide title>: (start of this slide)`.
- **Schema:** `{"node": <enum of the candidate ids>}`, required.
- **Commit** (dwell ≥ 2.0 s on `c` is required in every case):
  - the answer is the next node in deck order (`f1`), at **one** decision point;
  - or any other non-current answer, the **same** answer at **2 consecutive** decision points.
  - An answer of `c` holds.
- **Latency is honest on warm reruns.** The commit takes effect at the decision time plus the call's elapsed time. On a cache hit, that is the `elapsed_ms` stored in the cache entry, never the near-zero time of the hit. A warm rerun therefore reproduces the cold run's commits and latencies exactly.
- **Reported, not a bar:** the median and p90 call time per decision. A2 is viable live only if p90 < 1.5 s (the decision cadence). The report states whether it is.

#### 6.6.3 The corpus and the replay harness

- **The corpus:** 8 presentation jobs, the four §9 configurations × seeds **7 and 11**, created once with `--matcher bm25` after Wave I lands, in `artifacts/matcher_bakeoff/<date>/corpus/`.
  - Seed 7 is **the decision set**: the "four runs" of the user's rule.
  - Seed 11 is **the held-out set**, a guard against tuning to the decision set.
  - The corpus is never regenerated during the bake-off.
- **The harness:** `uv run python -m animated_infographics.evals.matcher_bakeoff --corpus <dir> --matcher <m> --out <dir>`. For each corpus job it:
  1. copies the job into `<out>/<job id>/`;
  2. runs `anticipate` (A1 only), `follow` with the matcher, `compose` and `score` (no render, no oracle);
  3. writes `bakeoff.json` with, per job, every §8 metric, its bar, PASS/MISS, the matcher's LLM calls, and the median and p90 compute time per decision;
  4. prints one `BAR <job> <metric> <value> <bar> PASS|MISS` line per check;
  5. exits 0 only if every bar passes on all 8 jobs.
- **Diagnostic column, not a bar: "perfect hearing".** The same matcher fed the performed sentences (`performance.json` text) with each sentence's words spread evenly over its `speak_timing.json` span, in place of `heard.json`. It separates matcher error from ASR error. It reads the ground truth, so only the harness builds it, outside any job. It is never reachable from `present-sim` and never decides adoption.
- **The baseline row:** `--matcher bm25` through the harness must reproduce each corpus job's own `presentation_score.json` within 0.01 on every metric. This proves the harness changes nothing but the follower.

#### 6.6.4 The adoption rule (the user's Option A, applied mechanically)

1. **Build A1 and run the harness.**
   - If A1 meets every §8 bar on all **4 decision-set** jobs **and** all **4 held-out** jobs, **adopt A1** and stop; A2 is not built.
   - If A1 passes the decision set but misses on the held-out set, **stop and file it** with both tables. This is a generalisation question for the user, not a reason to move on.
2. **Otherwise build A2 and run the harness,** with the same two conditions and the same stop-and-file case.
3. **If neither is adopted,** file a new issue with both contestants' tables, the best result per metric, and the "perfect hearing" column, and stop. G16 stays at exit 3.
4. **On adoption:**
   - the adopted matcher becomes `present-sim`'s default and the one G16 gates;
   - `bm25` stays selectable as the baseline;
   - a fresh G16 must exit **0**.
5. **No tuning, ever.** No constant in §6.6.1–§6.6.2 changes during the bake-off: windows, margins, costs, candidate sets, prompts, temperatures, the BM25 parameters. A contestant that misses, misses. If a constant is wrong, the evidence goes into the filed issue for the designer.

#### 6.6.5 Round 1 result (October 9, 2026) and the spec defect it exposed

**Neither contestant was adopted** (`docs/evals/matcher_bakeoff_2026-10-09.md`).
- **Most of that verdict comes from this spec, not the contestants.** Both candidate sets (§6.6.1, §6.6.2) offered only the next 3 nodes ahead, and a slide is 4 nodes. A follower one slide behind could never be offered the true point again.
- **The cost:** the true point was unreachable for 46–60% of the talk for A2, and 68–81% for A1.
- **A second defect:** a section node and its slide's first point are one moment in speech, but moving onto the first point counted as a two-decision jump.
- **The designer's replays** fix both, and change A2's prompt so that only side stories answer "current". They take A2's slide accuracy from 0.34–0.40 to 0.66–0.86 and its false switches from 3.6–4.4 to 0.5–1.25 per minute; lag still misses. The full table is in Issue 9.
- **Not yet the contract.** These corrections are measured but not adopted into §6.6.1–§6.6.2: the next step is the user's selection in Issue 9. Until then §6.6.1–§6.6.2 describe what Round 1 tested.
- **Invariant for any next round (lesson 2.17):** every node is reachable from every state, and the harness reports the share of talk time during which the true point was not a candidate.

---

## 7. `compose`, `preview` and `render`

- **`compose`** builds `timeline.json` from the playback:
  - each committed node's scene plays from its `start_ms` until the next commit, at absolute frames;
  - there is no `LEAD_MS`, because a live system cannot lead the voice;
  - **audio** is the `speak` narration;
  - **captions** come from the ASR words (what was heard), each page shown 300 ms after its words end, simulating live caption lag;
  - music and SFX follow the job's inputs as usual;
  - a scene shorter than `ENTER_FRAMES + EXIT_FRAMES` is merged into the previous one, and recorded.
- **`preview`, review and `render`** are unchanged.
- **The review page** shows the deck and, per scene, the node it came from plus the ground-truth slide/point at its midpoint. Mismatches are marked, so the reviewer sees where following failed.

---

## 8. `score`: was the video done well?

`score` reads the ground truth (§4, §5), `playback.json` and the rendered timeline, and writes `presentation_score.json` plus a strip chart PNG: ground-truth slide vs shown slide over time.

| Metric | Definition | Bar: `mild` | Bar: `strong` |
|---|---|---|---|
| **Slide accuracy** | Fraction of non-ad-lib speech time where shown slide = ground-truth slide | ≥ 0.90 | ≥ 0.80 |
| **Point accuracy** | Same, at point level; a `section` node counts as correct during its slide's first point | ≥ 0.75 | ≥ 0.60 |
| **Onset lag** | Per point present in the performance: time from its first spoken word `t0` until its node is on screen (for point 0, its slide's `section` node also counts). Revised October 9, 2026 (Wave K, K2): **0** if the node is already on screen at `t0`; otherwise the first commit to it before `t_end`, the end of the point's first contiguous spoken run; **missed** (never on screen in that run) counts `max(10 s, t_end − t0)`, so missing is never better than being late. A later revisit never counts as the onset. Median and p90 | median ≤ 3.0 s, p90 ≤ 6.0 s | median ≤ 4.0 s, p90 ≤ 8.0 s |
| **False switches** | Commits to a node that is neither the ground-truth node nor the next one in the deck, per minute | ≤ 1.0 / min | ≤ 2.0 / min |
| **Ad-lib stability** | Fraction of ad-lib time with no commit | ≥ 0.80 | ≥ 0.70 |
| **Skip recovery** | (`strong`) time from the first word after a skipped point to the correct node | — | ≤ 6.0 s |

**Inherited checks** on the rendered presentation video:
- E2E step 9's density (≤ 1.0 graphic word/s per second of narration; the light-share bar is **not** applied, by the presentation profile);
- step 10's scene criteria (dates, junk text, era stamps, etc.);
- `verify.json`;
- the sync probe is **not** applied (scenes are deliberately not word-synchronised).

**Oracle baseline:** `score --oracle` composes the same tree from ground-truth timing (each point shown from its first spoken word). It reports the same metrics and renders `oracle.mp4`. The gap between oracle and `follow` isolates matcher error from tree quality.

**First measurement (October 6, 2026).** The oracle meets every bar (slide and point accuracy 0.98–1.00), so the deck, the tree and the scorer are sound. The BM25 follower misses every accuracy, lag and false-switch bar on all four runs: slide 0.32–0.56 and point 0.20–0.36. The analysis and the options are in Issue 8.

**G16's exit code states the bars** (`design_testing_and_validation.md` §4c): 0 when every bar is met, 3 when the run is mechanically sound but a follower bar is missed (filed), and 1 for anything else.

**A bar that fails is filed with numbers, never tuned away.** These bars are initial decisions. If the first measured run misses one on any fixture, the agent files an issue with the measurement and options for the user (e.g. accept the number, enable the tie-break, change the commit rule), instead of changing the threshold.

---

## 9. Fixtures for the simulation

- **`history_great_stink`:** a talk-like history. Run `literal` + `mild`, and `creative` + `strong`.
- **`story_overdue_book`:** a personal story with a twist. Run `literal` + `strong`, and `creative` + `mild`.
- **Seed:** 7 for all runs.
- **Report:** `docs/evals/presentation_<date>.md` collects all four runs plus the oracle rows.

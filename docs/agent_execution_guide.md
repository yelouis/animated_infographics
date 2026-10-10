# Agent Execution Guide — Active Build: Wave M (memory guards, 2 items), then K4 and Wave L (follower Round 2) — October 10, 2026

**You are an engineering agent with no memory of this project.** Waves A–J are built, committed and pushed (head `main`).
- **The verification.** Waves I and J were independently verified by the designer on October 9, 2026. **All 12 items do what their specs say,** and every Wave I target is fixed on fresh output (`ongoing_general_errors.md` §1, §3).
- **The bake-off.** Wave J's bake-off ended with neither follower adopted. The designer traced most of that to a defect in **the designer's own** §6.6 spec: a lost follower could never get back. Replays with that corrected roughly double the LLM follower's accuracy, but lag still misses (Issue 9, rewritten).
- **The user's decisions (October 10, 2026):** *"For issue 9 select Option A, for issue 10 select Option A. Update the agent_execution_guide to reflect these choices"*.
  - **Issue 9 → A:** Round 2 of the bake-off. The corrected LLM follower is judged against the unchanged bars on fresh held-out talks. That is **Wave L**.
  - **Issue 10 → A:** long-story budgets are judged on the total time per narration minute only. That is part of **K1**.
- **Wave K's K1–K3 are delivered** (`5c224a5`, `879b978`, `7da35ef`; not yet independently verified).
- **K4's re-measure was interrupted when the machine ran out of memory** (October 9, 19:50–19:52). Four heavy runs, a cold budget, the offline gate, the E2E and a second budget, ran **at the same time**. Two 27 GB image generations met Ollama's 10.5 GB and the user's own programs on a 64 GB Mac.
- **The user's direction (October 10, 2026):** *"Write guards so that we don't run out of memory. Assume that other program can start and stop which will take from the available memory."* That is **Wave M**, and it comes **before** K4, whose battery and budgets are heavy.

**Status:** **Active Build: Wave M** (M1–M2), then **K4**, then **Wave L** (L1–L3), in the §2 order. No user decision is pending. L2 may end in a filed **Issue 11**, whose `Your selection:` line will belong to the user.

**Every number and literal string in this guide and the design docs is a decision, not a suggestion.**

**The product, in one paragraph.** A local-only CLI that turns a text story (narrated by local TTS) or an audio narration into a 1080×1920 animated explainer video. It has karaoke captions, a persistent avatar cast, checked illustrations, a blind critic, and a mandatory review gate. It has two styles:
- **literal**: the pictures show what is said;
- **creative**: a director adds motifs and callbacks, visual metaphors and small asides, under the user's "small embellishments" license.

An offline **presentation simulation** derives a deck from a script, builds an animation tree from the deck alone, perturbs the script into a "performed" talk, follows it with a causal matcher, and scores the result.

**The lessons that shape these waves** (`ongoing_general_errors.md` §2):
- **2.18:** a machine shared with other programs needs admission control. Free memory at the start of a run says nothing about ten minutes later, and nothing in the pipeline asked.
- **2.14:** a gate's exit code must state its bars. The budget script still writes FAIL and exits 0.
- **2.17:** an evaluation must measure what it claims. The onset-lag scorer counted a point already on screen as a 10 s miss, and the harness's "per-decision" latency was measured over commits only.
- **Still binding:** 2.8, 2.10, 2.12, 2.13.

---

## 0. Standing constraints (apply to every item)

1. **The battery is the regression bar.** After every item, run the full battery (G1–G16) bare and update §1.3. Read every exit code bare.
   - **The expected G16 code is 3** (follower bars missed) **until L3 adopts the corrected A2; then it is 0.**
   - A 1 is always a regression. A 0 before L3 is impossible without a follower change, so investigate it.
2. **Fully local at runtime.** No cloud API, and no network except loopback. **Pull no new models**: `gemma4:26b`, Kokoro, mlx-whisper and FLUX.2 klein 4B only.
3. **Python (Pydantic) is the source of truth for every contract.** Generated files are never hand-edited, and G8 covers every contract change (K3).
4. **Templates read time only through the clock.**
5. **The review gate is mandatory** for video and presentation jobs alike. No auto-approve.
6. **The planner never crashes the pipeline.** Every LLM call goes through `run_with_retries`. Every new error string is copied **verbatim** from the design doc that defines it.
7. **Red first, on real inputs.** Before building, run the item's falsifying check against the current code, using the recorded artefacts this guide names, and record the failure.
8. **One item = one Conventional Commit, scope = item id** (`fix(k1): …`). Put the WHY and the red and green runs in the body. Push after every item. Never amend a pushed commit.
9. **Record each resolution in the same commit,** as one line under a new "**Wave K:**" heading in `ongoing_general_errors.md` §3: `K<n> — <title> — git log --grep "(k<n>)" — <measured result>`.
10. **When this guide and a design doc disagree, stop and file it.**
11. Every stage log ends in `llm_calls=<n> cache_hits=<m> elapsed_ms=<t>`.
12. **Nothing in the package changes the environment at import.** Any run that generates images must show 0 asset execution errors to count.
13. **Ids:** waves A–M; deferred features DF1–DF9; live constraints LC1–LC6; issues up to 10 (the next is Issue 11).
14. **Eval reports are named by date.** A second E2E or budget run on the same day overwrites the first. Commit each report in the item that produced it.
15. **The follower changes only in L2, and only as `design_presentation_simulation.md` §6.6.6 says.**
    - **In Wave K and L1:** do not change any matcher's candidates, window, prompt, commit rule, costs or tie-break. L1 only *records* candidate ids.
    - K2 changes **how onset lag is measured**, to match §8's definition; it does not change what any follower does.
    - **Never:** change the §8 bars or the frozen scorer during Round 2, regenerate `corpus_r2`, or tune §6.6.6's constants to pass.
16. **One heavy run at a time** (added October 10, 2026, after the out-of-memory event).
    - **Never start a gate, budget, pipeline run, corpus build or bake-off while another is running**: not in the background, not in a second terminal, not as parallel tool calls. After M2 the gate lock enforces this for gates; for everything else, it is on you.
    - **Before a long run,** run `memory_pressure | tail -1`. If the free percentage is below 45%, wait, or release what **you** started: your own leftover processes, or `ollama stop gemma4:26b`.
    - **Never kill or signal the user's programs.**
    - **If the memory guard waits, let it wait.** Exit 5 means "not enough memory now": `rerun --from <stage>` later. It is never a reason to bypass the guard.

---

## 1. Verified baseline (October 9, 2026; the designer's re-run of Waves I and J)

### 1.1 Environment

`doctor`: 22 checks OK.
- M4 Max 64 GB; ffmpeg 8.1; Node v26.5.0; Python 3.12 (uv).
- Ollama with `gemma4:26b`; Kokoro 0.9.4; mlx-whisper 0.4.3.
- mflux (`flux2-klein-4b`); Remotion 4.0.528.

### 1.2 Repository

- Waves A–H: `4df212a` … `6150482`.
- Wave I: `ae0d00f` … `e71006e`.
- Wave J: `b11dfde` … `a3fe8c2`.
- Wave K: K1 `5c224a5`, K2 `879b978`, K3 `7da35ef` (delivered October 9; to be verified with K4's numbers).
- Per-item verdicts: `ongoing_general_errors.md` §3.

### 1.3 Gates (run bare October 9, 2026 by the designer; the regression bar)

| # | Gate | Result |
|---|---|---|
| G1–G3 | ruff / format / mypy | exit 0 |
| G4 | `uv run pytest -q -m "not slow"` | exit 0 · **411 passed** |
| G5–G7 | renderer typecheck / lint / vitest | exit 0 · 21 vitest |
| G8 | schema sync | exit 0 |
| G9 | renderer purity | exit 0 |
| G10 | gallery | exit 0 · 82 goldens, 0 overflows, 0 overlaps |
| G11 | `uv run pytest -q -m slow` | exit 0 · **43 passed** (378 s) |
| G12 | `./scripts/e2e.sh` | exit 0 (916 s) · steps 1–10 · 0.52–0.83 graphic words/s |
| G13 | offline | exit 0 (263 s) |
| G14 | doctor | exit 0 · 22 OK |
| G15 | `./scripts/creative_e2e.sh` | exit 0 (1,534 s) · 0.68 / 0.82 graphic words/s · callbacks 4 dots = 4 tokens · 0 spoilers |
| G16 | `./scripts/presentation_sim.sh` | **exit 3** (3,263 s) · four fresh jobs · falsifications (a)–(c) pass · follower slide 0.33–0.56, point 0.20–0.35, lag median 7.4–10 s |
| Budget | `story_recipe_box`, cold | 218.02 / 193.65 / 411.67 s (≤ 390 / 210 / 600), 0 cache hits, 0 execution errors |
| Budget (long) | literal | total **138.90 s/min (≤ 170)**. Watch numbers: new 58.43, render 80.47 s/min. The render bar was removed under Issue 10 → A; the script's exit 0 on its FAIL row is fixed in K1 |
| Budget (long creative) | creative | 77.05 / 79.54 / 156.58 s/min (≤ 110 / 85 / 195), 9 images, not degraded |

### 1.4 Measurements that shaped Wave K and Issue 9 (October 9, 2026)

| What | Result |
|---|---|
| Budget fail-open | `measure_budget.sh:292–295` computes PASS/FAIL and writes it, but nothing turns FAIL into an exit code: the long literal run wrote FAIL and exited 0 |
| Onset-lag scorer | `score.py:146` ignores any commit made more than 0.5 s before the point's first word, and `:154` then scores the point as a 10 s miss. A point shown early and still on screen is "missed" (`history-great-stink-20261009-074656`, d4_p1, in the designer's replay). A later revisit counts as the onset (lags of 74.7 s in October 6 runs), while a point never shown counts only 10 s |
| Harness latency | `matcher_bakeoff.py:278` takes "per decision" compute percentiles over **commits only**, including the 0 ms initial commit. Holds carry no compute time (`contracts/playback.py:48–57`). The reported "A2 p90 598 ms" is therefore not a per-decision figure; the replay's cache entries show 0.65–0.78 s per call |
| **Out of memory** (October 9, 19:50–19:52) | JetsamEvent reports: two `mflux` processes at 26.6 and 27.2 GB at once (lifetime peak 27.4 GB), `llama-server` 10.5 GB, a browser tab 5.6 GB, 16 GB wired; macOS killed its own services. The cause was four heavy runs at once (M1's evidence). Image generation runs `mflux` serially within one job (`illustrate.py:342`), so only concurrent jobs can double it |
| Follower trap (Issue 9) | The true point was unreachable 46–60% of the talk for A2, 68–81% for A1 and 32–62% for `bm25`. The designer's corrections cut it to 2–9% and raise A2's slide accuracy to 0.66–0.86 |

---

## 2. Execution order

| # | Item | Why this position |
|---|---|---|
| K1–K3 | **Delivered** (`5c224a5`, `879b978`, `7da35ef`) | Verified at the next designer pass, with K4's numbers |
| M1 | The memory guard: admission, the heavy lock, the watchdog, exit 5, measured peaks | Every later item runs heavy steps: K4's battery and budgets, L1's corpus, L2's ≈ 2,000 LLM calls |
| M2 | Gates never run concurrently; budgets stay honest; `doctor` reports memory; discard the interrupted K4 output | Needs M1's guard (the budget validity check reads its log lines) |
| K4 | Re-measure; close-out of Waves K and M | The Round 2 corpus must be scored by the finished scorer, and the battery must run under the guards |
| L1 | The Round 2 corpus (seed 7 + a fresh seed 13) and the diagnostics | The yardstick first. It needs K2's scorer and K3's per-decision times |
| L2 | The corrected A2; Round 2; decide | Needs L1's corpus and diagnostics |
| L3 | Adopt or file; close out | Needs the decision |

---

## 3. The items

### K1–K3 — Delivered (October 9, 2026)

- **K1** `5c224a5`: budget exit codes, and long stories judged on the total.
- **K2** `879b978`: onset lag per §8.
- **K3** `7da35ef`: compute time per decision.

Their specs are in the design docs (`design_testing_and_validation.md` §2 and §5, `design_presentation_simulation.md` §8, `design_data_contracts.md` §10) and in this guide's previous version (`git show 9bafe70:docs/agent_execution_guide.md`). **Do not rework them;** K4's numbers are their check.

---

### M1 — The memory guard

**What this means for the user:** on October 9 two image generations ran at once and pushed the 64 GB Mac out of memory; macOS started killing its own services. After this item:
- every heavy step asks for memory first and waits its turn;
- the pipeline frees its own LLM before taking memory from anything else;
- if memory runs short (including when the user opens other programs mid-run), our step stops cleanly with exit 5, not the machine.

**The gap:**
- **Nothing in the pipeline knows about memory:**
  - `assets/illustrate.py:342` runs `mflux-generate-flux2` with `subprocess.run`;
  - `audio/transcribe.py:205` calls `mlx_whisper.transcribe`;
  - `audio/narrate.py:231` builds Kokoro's `KPipeline`;
  - `preview.py:79–135` and `render.py:16–40` run Remotion through `npx`;
  - `planner/llm.py:137` (`generate_json`) loads the model on demand.
- **No machine-wide lock** exists, and the exit codes stop at 4.
- **The evidence:**
  - `/Library/Logs/DiagnosticReports/JetsamEvent-2026-10-09-195051.ips` and `-195211.ips`: two `python3.12` processes at 26.6–27.2 GB each (`mflux`), `llama-server` at 10.5 GB, 16 GB wired, and system services killed for "vm-compressor-space-shortage";
  - the four concurrent runs that caused it: `artifacts/budget/20261009_194405`, `artifacts/offline/20261009_194518`, `artifacts/e2e/20261009_195347`, `artifacts/budget/20261009_195734`.
- **Contract:** `design_system_architecture.md` §11 (all of it) and §6 (exit 5, the three new variables); the "`memguard.py`" row and the "Slow memory-guard test" and "One-off validation" paragraphs in `design_testing_and_validation.md` §2.

**Implementation** (§11, verbatim rules):
1. **`src/animated_infographics/memguard.py`:**
   - `HEAVY_STEPS`, `FLOOR = 8 GB`;
   - `read_memory() -> (available_bytes, pressure_level)` from `sysctl -n hw.memsize kern.memorystatus_level kern.memorystatus_vm_pressure_level`. This is the only function tests replace;
   - `guard(step)`: the heavy lock, admission, our own Ollama unload, the wait, the timeout, and the `memguard …` log line;
   - `watch(step, popen)`: the watchdog that only ever signals that child;
   - `ResourceUnavailable`.
2. **Exit 5:** the CLI's error handler maps `ResourceUnavailable` to exit **5**, and the job keeps its failed stage, so `rerun --from <stage>` resumes. Document it in the README.
3. **Wire every heavy step:**
   - **`flux`:** each `mflux` call in `illustrate.py` becomes `Popen` under `guard("flux")` and `watch`, keeping the existing `INFOGRAPHICS_IMAGE_TIMEOUT_S`. **`ResourceUnavailable` must pass through `generate_image` unchanged, never into the icon fallback.**
   - **`render`:** `preview.py` (stills and media), `render.py`, the oracle render, and the gallery run, each under `guard("render")` and `watch`.
   - **`whisper`:** under `guard("whisper")`, then release the model.
   - **`kokoro`:** under `guard("kokoro")`, then release the model.
   - **`llm_load`:** in `OllamaBackend`, before a stage's first call, `GET /api/ps`. If `gemma4:26b` is not loaded, that first call runs under `guard("llm_load")`.
   - **The presentation stages** (`speak`, `hear`, `tree`'s assets) reach the same functions. Confirm that by test.
4. **Measure the peaks** on the longest fixture, `story_overdue_book`: each step alone, as a subprocess under `/usr/bin/time -l`, reading "peak memory footprint".
   - **The steps:** one `flux` illustration; `whisper` on its narration; `kokoro` narrating it; a final `render` at the concurrency it uses.
   - **Write the results** (× 1.15, rounded up to a GB) into `HEAVY_STEPS` with the date, and into §11's table, in the same commit.
   - **Check `flux` against the evidence.** If it is off from 27.4 GB by > 10%, write why.
   - **Check the reader.** Print `read_memory()` next to `memory_pressure`'s "System-wide memory free percentage"; they must agree within 1 point.
5. **Release in-process models.** After `whisper` and `kokoro`: drop the references, `gc.collect()`, and clear the MLX or MPS cache. Measure the pipeline process's footprint before the stage and after the release: it must be within 1 GB.

**Validation:**
- **Red first. Do NOT reproduce the out-of-memory condition.** The two JetsamEvent reports above are the red evidence; quote their numbers in the commit body. The new unit cases are red because the module does not exist.
- **Green:**
  - the "`memguard.py`" unit row (a)–(f);
  - the slow test (two real processes are serialised);
  - **the one-off validation on real work** (two cold jobs at once, with the safety monitor): no `flux` overlap, minimum `available` ≥ 7 GB, no new JetsamEvent file, both jobs at `awaiting_review`. Paste the monitor's minimum and the two `memguard` logs into the commit body.
- **Falsify:**
  - (1) in a scratch copy, skip the heavy lock → the slow test's intervals overlap;
  - (2) make the watchdog ignore the pressure level → unit (e) goes red;
  - (3) let `ResourceUnavailable` fall into the icon fallback → the unit case "stage exits 5, no icon" goes red.

  Restore each.

**Blast radius:**
- `memguard.py` (new);
- `assets/illustrate.py`, `audio/transcribe.py`, `audio/narrate.py`, `preview.py`, `render.py`, `planner/llm.py`;
- `cli.py` (exit 5), the README;
- tests;
- `design_system_architecture.md` §11's measured numbers.

---

### M2 — Gates never run concurrently; budgets stay honest; `doctor` reports memory

**What this means for the user:** a second gate started by mistake now refuses at once instead of doubling the machine's load. A budget run that had to wait for memory says so, instead of reporting slow numbers as real. `doctor` tells you whether there is room to run.

**The gap:**
- **No gate lock:** none of the seven gate scripts takes one. On October 9 four heavy runs went at once (M1's evidence).
- **Budgets:** `measure_budget.sh` does not look for memory waits.
- **`doctor`** has no memory check.
- **The interrupted K4 left invalid, uncommitted output,** measured while four gates competed for memory: `docs/evals/budget_2026-10-09.md` (modified), and the untracked `docs/evals/e2e_2026-10-09.md` and `docs/evals/assets/2026-10-09/`.
- **Contract:** `design_system_architecture.md` §11 ("Gates never run concurrently", "Budgets stay honest", `doctor`); `design_testing_and_validation.md` §3 (the battery line) and §5 (the budget validity line); the "gate lock" and "budget validity" rows in §2.

**Implementation:**
1. **`src/animated_infographics/gatelock.py`:** `python -m animated_infographics.gatelock <name> -- <command…>`.
   - It takes a non-blocking `flock` on `<INFOGRAPHICS_LOCK_DIR>/gate.lock`.
   - **If it is held,** it prints `another gate is running: <holder name> pid <pid>` and exits **3**. The holder writes its name and pid into the lock file.
   - **Otherwise** it sets `INFOGRAPHICS_GATE_LOCK_HELD=<its pid>`, runs the command, and returns the command's exit code.
2. **Every gate script** (`battery.sh`, `e2e.sh`, `creative_e2e.sh`, `presentation_sim.sh`, `check_offline.sh`, `check_gallery.sh`, `measure_budget.sh`) re-executes itself through the wrapper on its first line, **unless** `INFOGRAPHICS_GATE_LOCK_HELD` names a live ancestor pid.
3. **`measure_budget.sh`:** after the run, scan the archived stage logs' `memguard` lines. Any `waited_ms` > 0, or a stopped step, gives `INVALID: memory guard waited <ms> ms` at the top of the report and exit 1.
4. **`doctor`:** the three additions of §11.
5. **The offline gate** passes with the guard active. Confirm that `scripts/offline.sb` needs no change; if it does, STOP and file it.
6. **Discard the interrupted K4 output.**
   - First check that `git status` shows exactly the three paths above.
   - Then: `git checkout -- docs/evals/budget_2026-10-09.md`, and remove `docs/evals/e2e_2026-10-09.md` and `docs/evals/assets/2026-10-09/`.
   - Say so in the commit body. K4 re-measures.

**Validation:**
- **Green:**
  - the "gate lock" and "budget validity" rows;
  - **a real refusal:** start `./scripts/check_gallery.sh`, and while it runs start `./scripts/e2e.sh`. The second exits **3** within 2 s, with the message;
  - the battery runs end to end under one lock;
  - `doctor` prints the memory lines;
  - G13 exits 0.
- **Falsify:** remove the wrapper line from `e2e.sh` → the real refusal check fails, because the second gate starts. Restore.

**Blast radius:** `gatelock.py` (new), the seven gate scripts, `doctor.py`, tests, and the three discarded eval files.

---

### K4 — Re-measure; close-out of Waves K and M

**Run everything one at a time** (constraint 16). The battery and the three budgets run sequentially under the gate lock, and every heavy step under the memory guard. A budget marked `INVALID` (the guard waited) is re-run when the machine is quieter. It is never reported as a measurement.


1. **The full battery G1–G16, bare.** Expected: all 0 except **G16 = 3**.
2. **The three cold budgets.** Record their exit codes. Long literal is 0 or 3, with 3 filed under Issue 10 while it is open.
3. **Update the docs:**
   - `ongoing_general_errors.md` §3: the Wave K lines;
   - §1: a short paragraph for Wave K;
   - Issue 9: a one-line note with the K2-corrected lag of the four seed-7 `bm25` jobs.
4. **Update §1.3** (re-measured) and add Wave K to §5.1. **Do not stop:** continue with L1.

---

### L1 — The Round 2 corpus and the diagnostics

**What this means for the user:** Round 2 is judged on talks nobody has looked at, and the report says *why* the follower lags, not just by how much.

**The gap:**
- **The held-out set has been seen.** Round 1's held-out jobs (seed 11) were looked at by the designer's replays.
- **No diagnostics:** the harness (`evals/matcher_bakeoff.py`) reports neither the share of decisions whose true node was not a candidate nor how long the follower kept answering "current" after the speaker moved on.
- **No candidate record:** a playback does not record which candidates each decision considered.
- **Contract:** `design_presentation_simulation.md` §6.6.6 (corpus and diagnostics), and the "bake-off diagnostics" row in `design_testing_and_validation.md` §2.

**Implementation:**
1. **The candidate record.** `PlaybackCommit` and `PlaybackHold` gain `candidate_ids: list[str] = []` (G8). Every matcher fills it with the ids it considered at that decision; for `LiveMatcher`, the current node plus the nodes reachable by an edge. It is diagnostics only: `compose` and `score` ignore it, and **no matcher reads the ground truth.**
2. **The diagnostics,** computed in the harness from the ground truth (as it already does for scoring):
   - **"unreachable share":** among all decisions, the share whose true node at the decision time (for a point 0, its slide's section also counts) is not in `candidate_ids`;
   - **"stuck on current":** after each change of the true point, the number of consecutive decisions whose answer or top candidate was the current node while the current node was not the true one. Report its median and p90 per job.
3. **The corpus,** built only after K4:
   - copy the 4 seed-7 jobs from `artifacts/matcher_bakeoff/2026-10-09/corpus/` into `artifacts/matcher_bakeoff/<date>/corpus_r2/`, and verify that their hashes equal Round 1's;
   - create **4 new seed-13 jobs**, one per §9 configuration: `present-sim … --seed 13 --matcher bm25 --jobs-dir <corpus_r2>`, then `score` (the K2 scorer);
   - check: 0 asset execution errors; creative jobs not degraded, each with a `director.json`;
   - write `corpus_r2/corpus.json` with all 8 jobs and their hashes.
4. **The baseline:** the harness with `--matcher bm25` on `corpus_r2`, written as the "before" of `docs/evals/matcher_bakeoff_r2_<date>.md`, with both diagnostics.

**Validation:**
- **Red first:** today the harness has no diagnostics, and `PlaybackHold` has no `candidate_ids`.
- **Green:**
  - the unit row: re-run Round 1's A2 on `history-great-stink-20261009-074656` through the harness so that candidates are recorded, and "unreachable share" is ≥ 0.40.
    - Use `INFOGRAPHICS_CACHE_DIR=artifacts/matcher_bakeoff/2026-10-09/cache_llm`, so the warm cache reproduces Round 1's decisions.
    - This must run **before L2** changes `ClassifierMatcher`; that is why L1 comes first.
  - `bm25` reproduces every `corpus_r2` job's own score within 0.01;
  - the corpus hashes are verified before and after the run.
- **Falsify:** make "unreachable share" ignore `candidate_ids` and return 0.0 → the Round 1 case goes red. Restore.

**Blast radius:** `contracts/playback.py` and generated files, the three matchers (recording only), `evals/matcher_bakeoff.py`, tests, the corpus (artifacts), and the report.

---

### L2 — The corrected A2; Round 2; decide

**What this means for the user:** the LLM follower can always find its place again after a wrong turn, steps onto a new slide in one decision, and holds only during side stories. The user chose to test this on fresh talks against the original bars.

**The gap** (`presentation/match.py`, `ClassifierMatcher`):
- **Candidates:** the current node, the next 3 nodes and earlier points (`:825–842`). One slide behind, the true point is unreachable.
- **The forward step** is a single node (`:904`), so a slide's first point needs two decisions after its section.
- **The prompt's last line** says "or you are unsure, answer the current point" (`:767`).
- **Contract:** `design_presentation_simulation.md` §6.6.6, verbatim.

**Implementation** (§6.6.6, revised in place; `playback.json`'s `matcher` stays `llm`):
1. **Candidates:** every node of the tree, in deck order. The schema enum is every node id.
2. **The step set:** the node after `c`, plus the node after that when the first is a `section` node. An answer in the step set commits at one decision point. Any other non-current answer needs 2 consecutive identical answers. Dwell is ≥ 2.0 s in every case.
3. **The prompt's last line,** verbatim: `Which point is the speaker on now? If they are telling a side story that matches no point, answer the current point. Answer one id.`
4. **Everything else** in §6.6.2 is unchanged, as is K3's per-decision compute time.
5. **Round 2:** run the harness with `--matcher llm` on `corpus_r2`, **cold** (a fresh `INFOGRAPHICS_CACHE_DIR`), so that call times are real. Then run it with `--hearing perfect`.
6. **Decide by §6.6.6's rule,** quoting it in the report:
   - **Every §8 bar on all 8 jobs → adopted.** Go to L3.
   - **The decision set passes but the held-out set misses → STOP.** File **Issue 11** with both tables, following `.agents/skills/bug_documentation_guidelines/SKILL.md` (options included), and wait.
   - **The decision set misses → STOP.** File **Issue 11** with each metric's residual against its bar, both diagnostics, "perfect hearing" and the call-time percentiles, and wait. Nothing is tuned.

**Validation:**
- **Red first:** the unit case "6 nodes behind; the stub answers the true point twice → commit" fails against today's `ClassifierMatcher`, because the true point is not a candidate.
- **Green:**
  - the "corrected A2, Round 2" unit row;
  - causality;
  - a warm rerun reproduces the cold run's commits and latencies exactly;
  - "unreachable share" is 0.0 on all 8 jobs.
- **Cross-check against the designer's replay.** On the 4 seed-7 jobs, slide and point accuracy should land within 0.05 of Issue 9's last column (slide 0.863 / 0.846 / 0.662 / 0.681; point 0.633 / 0.601 / 0.463 / 0.502). K2 changes lag, not accuracy. A larger gap means the build differs from §6.6.6: find out why before deciding.
- **Falsify:** restore Round 1's "next 3 nodes" candidate block → "unreachable share" > 0 on at least one decision-set job, and the 6-behind unit case goes red. Restore.
- **Look:**
  - read 10 decisions sampled at true point changes in one decision-set job: prompt, answer, ground truth;
  - open one strip chart, against `bm25`'s;
  - describe both in the report.

**Blast radius:** `presentation/match.py` (`ClassifierMatcher` only), tests, and the report.

---

### L3 — Adopt or file; close out

**What this means for the user:** either presentations now follow the speaker well enough to meet the bars, and the presentation gate turns green honestly, or the user gets one more evidence-based decision.

1. **If L2 adopted the corrected A2:**
   - make `llm` the default of `present-sim` (`cli.py`) and the matcher G16 gates. G16's falsifications use it.
   - Run G16 bare on fresh jobs: **exit 0**. Record the BAR table. If it is not 0, STOP and file it; never re-tune. G16 now makes about 250 LLM calls per job, so expect it to take ≈ 12 min longer.
   - Update the docs:
     - `design_presentation_simulation.md` §6.6.6 gains a short **Result** paragraph;
     - `design_future_live_and_video.md` §4 records the adopted matcher and its per-decision p90 for DF4;
     - Issue 9 moves to the resolved index;
     - the README documents `--matcher`.
2. **If L2 stopped:** Issue 11 is filed. G16 stays at exit 3.
3. **Full battery, bare** (G1–G16). Update §1.3.
4. **Rewrite this guide** to **Queue Complete** (or **Queue Complete — waiting on Issue 11**). **Then stop. Do not invent work.**

---

## 4. Deferred — do NOT start

- **Issue 9's options that were not selected:** B (restated bars), C (an embedding contestant) and D (a pause). Do not build them. A1 (`anticipate`) is retired from Round 2.
- **Budget bars:** apart from removing the long-story span bars (K1, Issue 10 → A), change none.
- **DF1–DF9** (`ongoing_general_errors.md` §4). The real-time parts of DF4 (live mode) stay deferred:
  - slide import (.pptx / PDF / Google Slides);
  - a browser player on a requestAnimationFrame clock;
  - the microphone, streaming ASR and the webcam.
- **Known limitations, unscheduled:**
  - a quotation spanning two sentences can be split between beats;
  - the critic's `emotion_beat` *who* reading is noisy;
  - R7 treats reported speech without quotation marks as narration;
  - the spoiler rule treats a name token that is also a common word ("June") as naming.

---

## 5. Do NOT change

### 5.1 Already delivered

- Waves **A** (verified September 25), **B** (September 26), **C/D** (October 3), **E** and **F** (October 4), **G** and **H** (October 6), and **I** and **J** (October 9, 2026), all independently verified.
- One line per item, with verdicts: `ongoing_general_errors.md` §3. Nothing marked "✓" is reworked beyond what a Wave K item names.

### 5.2 Accepted equivalents (checked; do not "fix" these back)

- The sync probe is drawn inside each scene's layer.
- The antimeridian bbox handling.
- `image_prompt` strips a trailing period.
- `FitText`'s 0.35-line ascender allowance.
- The gallery's TypeScript port of `item_frames`.
- `CHECKSUMS` paths are relative to `fixtures/`.
- `plan_report.llm_calls` counts the storyboard stage only.
- Node 26.
- At-limit strings are reported, not failed.
- `AudioLayer`'s volume clamp and `loopVolumeCurveBehavior="extend"`.
- The pretty-printed lakes file.
- The critic's cast list has no `Cast:` label.
- `battery.sh` exports `HF_HOME`.
- E4's icon block follows any disagreement message.
- R6 keeps the original alternate even when it equals the new primary.
- F3's era normalisation runs before the length check.
- **New, October 6, 2026:**
  - **`num_predict=2048` in the deck stage.** `design_presentation_simulation.md` §2 suggested 1536; 8–10 slides need ≈ 1,520–1,600 tokens.
  - **The presentation profile also skips R1.** `section_title` replaces the title card. There were 0 `title_card` nodes in 4 trees, and I7 makes R1's second half an assertion.
  - **Motif ids are free strings** (e.g. `motif_blue_ink`). The spec's `m1` was an example, and ids never reach the screen.
- **New, October 9, 2026:**
  - **The overlap probe skips elements nested inside a `data-occupies` element.** The enclosing box already contains them.
  - **The harness calls the stage functions directly** (`run_follow_stage`, `run_compose_stage`, `compute_presentation_score`), as specified, rather than shelling out to the CLI.

### 5.3 User decisions

**September 23, 2026:**
- Offline first; a template library.
- History + Reddit-style stories; text + audio inputs.
- Mixed imagery; Python + TypeScript/Remotion; fully local.
- 9:16; karaoke captions; flat editorial vector; 1–3 min videos in about 10 min. *For the long fixtures, the budget is restated per minute, as the user's 4–6-minute choice implied.*
- Scenes + a persistent cast; single narrator; a mandatory review gate; music + SFX.
- Live mode later, with the webcam in a corner.

**September 24–25, 2026:** Issues 1–5 (verbatim in `ongoing_general_errors.md` §3).

**September 27, 2026:**
- **Issue 6 → D:** "I think the paraphrasing is fine."
- **Live presentations:** "For real-time presentations, it makes sense to show timelines and repeated graphics to drive home the point."
- **Issue 7 → A** (Wave D).

**October 5, 2026:**
- **A style library**, keeping today's output as one style, with a creative style that "adds something to the story".
- **Creative ingredients:** motifs & callbacks, visual metaphors, foreshadowing & reveals, visual gags & asides.
- **License:** "Small embellishments".
- **Stories:** 4–6 minutes.
- **The presentation simulation,** as described above.
- **Slide import:** not now.
- **"Make sure to not actually perform any coding and just update the docs + execution guide for another agent to implement".** This applies to the designer; you implement.

**October 10, 2026 (memory):** *"During another agent's last implementation and testing it seems like we ran out of memory. Write guards so that we don't run out of memory. Assume that other program can start and stop which will take from the available memory."*

**October 10, 2026:** *"For issue 9 select Option A, for issue 10 select Option A. Update the agent_execution_guide to reflect these choices"*.
- **Issue 9 → A:** Round 2 with the corrected A2 against the unchanged bars, on a fresh held-out set (Wave L).
- **Issue 10 → A:** long-story budgets are judged on the total only (K1).

**October 7, 2026:**
- **Issue 8 → Option A:** *"For issue 8, select Option A and write the agent execution guide to reflect that with validation"*.
- **Designer's validation, added under that instruction:** a held-out seed-11 set. If it disagrees with the decision set, that is filed for the user, not decided by you.

### 5.4 Invariants and intentional design decisions

**New (October 10, 2026):**
- **Every heavy step asks the memory guard first;** one heavy step runs at a time on the machine; gates never run concurrently.
- **A memory stop is exit 5,** never an icon fallback and never a crash of the machine. The watchdog only ever signals the child it started.
- **A budget that waited for memory is not a measurement.**

**New (October 9, 2026):**
- **Every follower state can reach every correct state** (lesson 2.17), and any follower evaluation reports the share of talk time during which the true point was not a candidate.
- **Missing a point is never scored better than being late to it** (§8 onset lag, K2).

**New (October 7, 2026):**
- **The follower bake-off is judged on a frozen corpus by the unchanged scorer,** and no contestant is tuned on it. The held-out set exists to catch exactly that.
- **Every follower sees only the deck** (and sentences anticipated from the deck) **and the words heard so far.** `LiveMatcher` (`bm25`) stays as the measured baseline.

**New (October 6, 2026):**
- **An overlay's anchor follows from its kind:** token top-right, thought and label top-left, prop bottom-left. Overlap is measured on the rendered gallery, never in a hand-kept table.
- **The renderer has no data defaults for creative devices:** no fallback icons, and no fallback dots.
- **A name reaches the screen only after the narration has said it.** Avatars may come earlier.
- **Fallbacks never hide execution errors.** A gate fails when a generator never ran.
- **A gate's exit code states its bars.** A known, filed miss is exit 3, never 0.
- **A stage reused in another pipeline brings all of its checks.**

**From October 5, 2026:**
- **A style changes how, never what is true.** Grounding, the critic, word caps, validators and the review gate apply in every style.
- **`literal` is byte-identical to the pre-Wave-G pipeline.**
- **Creative items only ever add interpretation or small embellishments.** The license check removes anything else, and a failed check removes the item.
- **Plants show only the object, never its meaning,** and come ≥ 3 beats before their payoff.
- **Overlays only on the 10 allowed templates;** at most one token and one aside per scene. Overlay text counts as graphic words.
- **In the presentation simulation:**
  - the tree sees only the deck;
  - the matcher sees only heard words;
  - only `score` sees the ground truth;
  - the matcher is causal;
  - nothing leads the voice.

**From Waves C–F:**
- Enforcement after the round; the `unknown`-emotion rule; R7 never replaces quoted speech.
- The icon list in prompts; no environment changes at import.
- Dates are never stats; no placeholder or instruction text; era stamps are narration years or nothing.
- Quoted speech is kept whole; passage framing; keyed text-thread answers; contact resolution.
- 3-attempt critic retries; no ids on screen; caption spacing.
- Missing inputs are errors; paraphrased dialogue is allowed.
- `WORD_CAPS` is the single source; R6/R7; karaoke captions.

**Unchanged:**
- Job-local inputs are authoritative; `run_with_retries` everywhere; no LLM length constraints.
- Scrim ≥ 85%; the text check is skipped for text-expected descriptions.
- A blind critic with one call per scene; the timeline label rule; the voice asymmetry.
- Avatars only; no auto-approve; a 200 ms scene lead (video jobs); absolute frames; timings computed in Python.
- Grounding is a hard gate; navy text on cast colours; never FLUX klein 9B.
- Beats are not human-editable; the offline gate stays; fixtures are original texts; commit scope = item id.

### 5.5 Assessed and rejected — do NOT re-propose

- **Every item listed in the Wave F guide's §5.5**, which is preserved in git at `69c0378`.
- **From October 5, 2026:**
  - **Slide import in these waves**, per the user.
  - **A real-time player in these waves.**
  - **Letting the tree or the matcher see the script, the performance or the ground truth.** It makes the simulation meaningless.
  - **Creative embellishments beyond the license:** new events, dialogue, facts, contradictions, or plants that reveal the twist.
  - **Raising word caps for creative scenes.**
  - **A creative style that changes the cast's look or the illustration `STYLE`.**
- **New, October 6, 2026:**
  - **Making G16 green by tuning edge costs, loosening the §8 bars or enabling the tie-break.** Wave J's rule decides.
  - **Tuning a contestant on the corpus,** whether windows, margins, costs, candidate sets, prompts or temperatures. A miss is filed with its evidence.
  - **Raising the back-edge cost as the fix for Issue 8.** It was measured: at best slide 0.55–0.59.
  - **Re-introducing renderer defaults** for dots or overlay icons.
  - **Loosening the motif spacing (3 / 20) or the spoiler rule** to keep a fixture from degrading. File it instead.
  - **Running heavy work in parallel to save time,** whether gates, budgets, corpus jobs or bake-off runs. That is what ran the machine out of memory on October 9.
  - **Lowering FLUX quality (quantisation, smaller images) to save memory** without the user's decision. The guard makes room by waiting and by unloading our own LLM, not by degrading output.
  - **Re-running Round 1's contestants unchanged.** Their candidate sets contain a trap (Issue 9). A1 also measured weak with the trap removed (slide 0.34–0.57, 5–8 false switches per minute).
  - **Removing "book" (or any word) from `TEXT_EXPECTED_WORDS`, or skipping rule 6 for metaphors,** to stop a degradation. A book in a FLUX image grows lettering that the skipped text check would never catch; salvage is the fix.

---

## 6. Where the contracts live

| What | Where |
|---|---|
| Styles, the director, the license, overlays, creative bars | `design_styles.md` §3.3–3.7 |
| The presentation simulation; the follower bake-off (§6.6), its Round 1 result (§6.6.5) and **Round 2** (§6.6.6); the onset-lag definition (§8) | `design_presentation_simulation.md` |
| Job files incl. `playback.json` (holds gain `compute_ms`) | `design_data_contracts.md` §10 |
| **The memory guard** (heavy steps, admission, the watchdog, exit 5, the gate lock, budget validity, `doctor`) | `design_system_architecture.md` §11 and §6; tests in `design_testing_and_validation.md` §2, §3 and §5 |
| The name rule (item 6), R8 and the rule order | `design_planner.md` §4, §6 |
| Templates; the callback dot count; word caps | `design_templates.md` §2.18, §5 |
| Test rows (Wave K: onset lag, decision compute time, budget exit codes; Wave L: corrected A2, bake-off diagnostics), gates, the budget rules (long stories: total only) | `design_testing_and_validation.md` §2–§5 |
| Issues 9 and 10 (decided October 10), lessons (2.13–2.17), verdicts, the deferred list | `ongoing_general_errors.md` |

---

## 7. Validation standard

- **Red first, on real inputs** (lesson 2.6). Every item names its recorded artefacts.
- **Measure outcomes before and after** (2.7).
- **Measure the rendered result** (2.8, 2.15).
- **Enforce rules on the final result** (2.10).
- **Name the defect class** (2.12).
- **A gate must be able to fail, must fail closed, and its exit code must state its bars** (2.13, 2.14).
- **An evaluation must measure what it names** (2.17): a lag that calls an on-screen point "missed", or a "per-decision" time taken over commits, is a defect.
- **Never loosen a bar to pass it.** File it with the measurement and options.

---

## 8. THE LOOP

```
(1) Is there an approved item? Wave M (M1–M2), then K4, then Wave L
    (L1–L3), in §2 order. If all are done, STOP. Never start DF1–DF9 or
    anything not in §3. Never fill in a `Your selection:` line.
    One heavy run at a time (constraint 16).
(2) Read the item and EVERY design section it names. Copy rules, thresholds
    and error strings VERBATIM.
(3) RED FIRST on the recorded artefacts the item names; record the failure.
(4) Build only what the item says. Nothing from §5.5.
(5) GREEN; then falsify (break, see red, restore, see green).
(6) Open every artefact and describe it.
(7) Full battery, bare. Update §1.3.
(8) ONE commit, scope = item id (`feat(m1): …`, `fix(k4): …`, `feat(l2): …`).
    WHY + red/green in the body. ONE line under "Wave M", "Wave K" or
    "Wave L" in ongoing_general_errors.md §3.
    Never amend after pushing.
(9) git push origin main.
(10) Next item. A failed bar or an impossible rule → file it and stop at
    that item until the user selects. In L2, §6.6.6's rule says exactly
    when a result means "adopt" and when it means "stop and file".
```

---

## 9. Definition of Done: Waves M, K and L

**Wave M**
- [ ] M1: every heavy step (`flux`, `render`, `whisper`, `kokoro`, `llm_load`) runs under `guard()`, and subprocess steps under `watch()`; exit 5 resumes with `rerun`; peaks measured and recorded; in-process models released; the real two-job validation passed with no JetsamEvent; three falsifications shown.
- [ ] M2: every gate script is under the gate lock, and a second gate exits 3; invalid budgets exit 1; `doctor` reports memory; the offline gate is green; the interrupted K4 output is discarded.

**Wave K**

- [ ] K1: `measure_budget.sh` exits 0 / 3 / 1 by its bars; long runs are judged on the total only, with `new` and `render` shown as watch numbers; the verdict is unit-tested and falsified; a real long run's code is recorded.
- [ ] K2: onset lag follows §8 (on screen at the first word → 0; the first run only; missing never beats late). The oracle stays at 0, the harness is re-baselined, and before/after numbers are recorded.
- [ ] K3: every hold carries `compute_ms`; the harness reports per-decision percentiles; the A2 addendum is written.
- [ ] §1.3 re-measured bare (G1–G16, three budgets with their exit codes); continue to Wave L.

**Wave L**
- [ ] L1: every decision records `candidate_ids`; the harness reports "unreachable share" and "stuck on current"; `corpus_r2` (seed 7 copied, 4 new seed-13 jobs) is frozen with hashes; the `bm25` baseline is written.
- [ ] L2: `ClassifierMatcher` matches §6.6.6 verbatim. Round 2 is run cold on all 8 jobs, with "unreachable share" 0.0, the cross-check against Issue 9's replay within 0.05, and the decision written out with the rule.
- [ ] L3: `llm` is the default and G16 on fresh jobs exits **0**; or Issue 11 is filed and G16 stays at 3.
- [ ] §1.3 re-measured bare (G1–G16).
- [ ] This guide rewritten to **Queue Complete** (or **Queue Complete — waiting on Issue 11**). **Then stop. Do not invent work.**

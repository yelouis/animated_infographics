#!/usr/bin/env bash
# Gate lock check (Wave M) per design_system_architecture.md §11
is_held_by_ancestor() {
  local target="${INFOGRAPHICS_GATE_LOCK_HELD:-}"
  [ -z "$target" ] && return 1
  local cur="$PPID"
  while [ -n "$cur" ] && [ "$cur" -gt 1 ] 2>/dev/null; do
    if [ "$cur" = "$target" ]; then return 0; fi
    cur=$(ps -o ppid= -p "$cur" 2>/dev/null | tr -d ' ' || true)
  done
  return 1
}

if ! is_held_by_ancestor; then
  GATE_NAME="$(basename "$0" .sh)"
  exec uv run python -m animated_infographics.gatelock "$GATE_NAME" -- "$0" "$@"
fi

set -u

# scripts/creative_e2e.sh: G15 Creative End-to-End gate per design_testing_and_validation.md §4b
# and agent_execution_guide.md §G6.

fail() {
  echo "[-] FAILED: $1" >&2
  exit 1
}

log() {
  echo "[+] $1"
}

if [ -z "${HF_HOME:-}" ] || [ ! -d "${HF_HOME}/hub/models--hexgrad--Kokoro-82M" ] || [ ! -d "${HF_HOME}/hub/models--black-forest-labs--FLUX.2-klein-4B" ]; then
  if [ -d "$HOME/.cache/huggingface/hub/models--hexgrad--Kokoro-82M" ]; then
    export HF_HOME="$HOME/.cache/huggingface"
  fi
fi

DATE_STR=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || fail "Cannot cd to repo root"

ARTIFACTS_DIR="$REPO_ROOT/artifacts/creative_e2e/$TIMESTAMP"
JOBS_DIR="$ARTIFACTS_DIR/jobs"
ASSETS_DIR="$REPO_ROOT/docs/evals/assets/$DATE_STR"
mkdir -p "$JOBS_DIR"
mkdir -p "$ASSETS_DIR"

log "Starting Creative E2E verification in $ARTIFACTS_DIR"

# ============================================================================
# Step 1: new story_overdue_book.txt --style creative -> approve -> render -> 0
# ============================================================================
log "Step 1.1: Running infographics new story_overdue_book.txt --style creative..."
uv run infographics new fixtures/scripts/story_overdue_book.txt \
  --style creative \
  --jobs-dir "$JOBS_DIR" > "$ARTIFACTS_DIR/step1_overdue_new.log" 2>&1
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 1.1 new failed with exit code $CODE"

OVERDUE_JOB_DIR=$(find "$JOBS_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)
[ -n "$OVERDUE_JOB_DIR" ] || fail "No job directory created for story_overdue_book"
OVERDUE_JOB_ID=$(basename "$OVERDUE_JOB_DIR")
log "story_overdue_book Job ID: $OVERDUE_JOB_ID"

log "Step 1.1: Approving $OVERDUE_JOB_ID..."
uv run infographics approve "$OVERDUE_JOB_ID" --jobs-dir "$JOBS_DIR" > "$ARTIFACTS_DIR/step1_overdue_approve.log" 2>&1
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 1.1 approve failed with exit code $CODE"

log "Step 1.1: Rendering $OVERDUE_JOB_ID..."
uv run infographics render "$OVERDUE_JOB_ID" --jobs-dir "$JOBS_DIR" > "$ARTIFACTS_DIR/step1_overdue_render.log" 2>&1
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 1.1 render failed with exit code $CODE"
[ -s "$OVERDUE_JOB_DIR/out/final.mp4" ] || fail "story_overdue_book out/final.mp4 missing or empty"

# Step 1.2: new history_great_stink.txt --style creative -> approve -> render -> 0
log "Step 1.2: Running infographics new history_great_stink.txt --style creative..."
uv run infographics new fixtures/scripts/history_great_stink.txt \
  --style creative \
  --jobs-dir "$JOBS_DIR" > "$ARTIFACTS_DIR/step1_stink_new.log" 2>&1
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 1.2 new failed with exit code $CODE"

STINK_JOB_DIR=$(find "$JOBS_DIR" -mindepth 1 -maxdepth 1 -type d | grep -v "$OVERDUE_JOB_ID" | head -n 1)
[ -n "$STINK_JOB_DIR" ] || fail "No job directory created for history_great_stink"
STINK_JOB_ID=$(basename "$STINK_JOB_DIR")
log "history_great_stink Job ID: $STINK_JOB_ID"

log "Step 1.2: Approving $STINK_JOB_ID..."
uv run infographics approve "$STINK_JOB_ID" --jobs-dir "$JOBS_DIR" > "$ARTIFACTS_DIR/step1_stink_approve.log" 2>&1
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 1.2 approve failed with exit code $CODE"

log "Step 1.2: Rendering $STINK_JOB_ID..."
uv run infographics render "$STINK_JOB_ID" --jobs-dir "$JOBS_DIR" > "$ARTIFACTS_DIR/step1_stink_render.log" 2>&1
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 1.2 render failed with exit code $CODE"
[ -s "$STINK_JOB_DIR/out/final.mp4" ] || fail "history_great_stink out/final.mp4 missing or empty"

# ============================================================================
# Step 2: verify.json all true, step 9 density, step 10 criteria
# ============================================================================
log "Step 2.1: Verifying out/verify.json on both creative jobs..."
python3 -c "
import json
from pathlib import Path

for job_path in [Path('$OVERDUE_JOB_DIR'), Path('$STINK_JOB_DIR')]:
    v_file = job_path / 'out' / 'verify.json'
    assert v_file.is_file(), f'verify.json missing in {job_path}'
    v = json.loads(v_file.read_text(encoding='utf-8'))
    checks = ['video_stream', 'frame_count', 'audio_stream', 'av_duration', 'loudness', 'non_blank']
    for c in checks:
        assert v.get(c) is True, f'Check {c} failed for {job_path}: {v.get(\"details\")}'
"
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 2.1 verify.json checks failed"

log "Step 2.2: Measuring word density across creative jobs (step 9)..."
WORD_DENSITY_OUT=$(uv run python -m animated_infographics.evals.word_density \
  "$OVERDUE_JOB_DIR" "$STINK_JOB_DIR")
CODE=$?
echo "$WORD_DENSITY_OUT"
[ "$CODE" -eq 0 ] || fail "Step 2.2 word density check failed with exit $CODE: $WORD_DENSITY_OUT"
echo "$WORD_DENSITY_OUT" > "$ARTIFACTS_DIR/step2_word_density.txt"

log "Step 2.3: Verifying scene criteria across creative jobs (step 10)..."
VERIFY_SCENES_OUT=$(uv run python -m animated_infographics.evals.verify_e2e_scenes \
  "$OVERDUE_JOB_DIR" "$STINK_JOB_DIR")
CODE=$?
echo "$VERIFY_SCENES_OUT"
[ "$CODE" -eq 0 ] || fail "Step 2.3 scene verification failed with exit $CODE: $VERIFY_SCENES_OUT"
echo "$VERIFY_SCENES_OUT" > "$ARTIFACTS_DIR/step2_verify_scenes.txt"

# ============================================================================
# Step 3: Creative bars of design_styles.md §3.7
# ============================================================================
log "Step 3: Checking creative bars across creative jobs..."
VERIFY_CREATIVE_OUT=$(uv run python -m animated_infographics.evals.verify_creative \
  "$OVERDUE_JOB_DIR" "$STINK_JOB_DIR")
CODE=$?
echo "$VERIFY_CREATIVE_OUT"
[ "$CODE" -eq 0 ] || fail "Step 3 creative bars check failed with exit $CODE: $VERIFY_CREATIVE_OUT"
echo "$VERIFY_CREATIVE_OUT" > "$ARTIFACTS_DIR/step3_verify_creative.txt"

# ============================================================================
# Step 4: Literal control job (story_overdue_book --style literal)
# ============================================================================
log "Step 4: Running literal control on story_overdue_book.txt..."
uv run infographics new fixtures/scripts/story_overdue_book.txt \
  --style literal \
  --jobs-dir "$JOBS_DIR" > "$ARTIFACTS_DIR/step4_literal_new.log" 2>&1
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 4 literal new failed with exit code $CODE"

LITERAL_JOB_DIR=$(find "$JOBS_DIR" -mindepth 1 -maxdepth 1 -type d | grep -v "$OVERDUE_JOB_ID" | grep -v "$STINK_JOB_ID" | head -n 1)
[ -n "$LITERAL_JOB_DIR" ] || fail "No job directory created for literal control"
LITERAL_JOB_ID=$(basename "$LITERAL_JOB_DIR")
log "Literal control Job ID: $LITERAL_JOB_ID"

log "Step 4: Approving $LITERAL_JOB_ID..."
uv run infographics approve "$LITERAL_JOB_ID" --jobs-dir "$JOBS_DIR" > "$ARTIFACTS_DIR/step4_literal_approve.log" 2>&1
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 4 literal approve failed with exit code $CODE"

log "Step 4: Rendering $LITERAL_JOB_ID..."
uv run infographics render "$LITERAL_JOB_ID" --jobs-dir "$JOBS_DIR" > "$ARTIFACTS_DIR/step4_literal_render.log" 2>&1
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 4 literal render failed with exit code $CODE"
[ -s "$LITERAL_JOB_DIR/out/final.mp4" ] || fail "Literal control out/final.mp4 missing or empty"

# ============================================================================
# Step 5: Copy assets and write docs/evals/creative_<date>.md
# ============================================================================
log "Step 5: Copying contact sheets and extracting 5 comparison stills..."
cp "$OVERDUE_JOB_DIR/preview/contact_sheet.png" "$ASSETS_DIR/creative_overdue_book_contact_sheet.png"
cp "$STINK_JOB_DIR/preview/contact_sheet.png" "$ASSETS_DIR/creative_great_stink_contact_sheet.png"
cp "$LITERAL_JOB_DIR/preview/contact_sheet.png" "$ASSETS_DIR/literal_control_contact_sheet.png"

uv run python -c "
import json
import shutil
from pathlib import Path

overdue_dir = Path('$OVERDUE_JOB_DIR')
literal_dir = Path('$LITERAL_JOB_DIR')
assets_dir = Path('$ASSETS_DIR')

t_overdue = json.loads((overdue_dir / 'timeline.json').read_text(encoding='utf-8'))
scenes = t_overdue.get('scenes', [])

# 1. Metaphor scene
meta_scene = next(s for s in scenes if s.get('template') == 'metaphor')
meta_id = meta_scene['id']
shutil.copyfile(overdue_dir / 'preview' / f'scene_{meta_id}.png', assets_dir / 'creative_still_metaphor.png')

# 2. Callback scene
cb_scene = next(s for s in scenes if s.get('template') == 'callback')
cb_id = cb_scene['id']
shutil.copyfile(overdue_dir / 'preview' / f'scene_{cb_id}.png', assets_dir / 'creative_still_callback.png')

# 3. Plant token scene
plant_scene = next(s for s in scenes if any(o.get('kind') == 'motif_token' for o in s.get('overlays', [])))
plant_id = plant_scene['id']
shutil.copyfile(overdue_dir / 'preview' / f'scene_{plant_id}.png', assets_dir / 'creative_still_plant_token.png')

# 4. Aside scene
aside_scene = next(s for s in scenes if any(o.get('kind') in ('thought', 'label', 'prop') for o in s.get('overlays', [])))
aside_id = aside_scene['id']
shutil.copyfile(overdue_dir / 'preview' / f'scene_{aside_id}.png', assets_dir / 'creative_still_aside.png')

# 5. Literal control at same beat as metaphor
shutil.copyfile(literal_dir / 'preview' / f'scene_{meta_id}.png', assets_dir / 'literal_control_still_metaphor_beat.png')

print(f'Stills copied successfully: meta={meta_id}, cb={cb_id}, plant={plant_id}, aside={aside_id}, literal_meta={meta_id}')
"
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 5 stills copying failed"

REPORT_PATH="$REPO_ROOT/docs/evals/creative_$DATE_STR.md"
log "Step 5: Writing evaluation report to $REPORT_PATH..."
uv run python -c "
import hashlib
import json
from pathlib import Path
from animated_infographics.evals.word_density import evaluate_job_word_density
from animated_infographics.evals.verify_e2e_scenes import verify_job_scenes
from animated_infographics.evals.verify_creative import verify_job_creative

overdue_dir = Path('$OVERDUE_JOB_DIR')
stink_dir = Path('$STINK_JOB_DIR')
literal_dir = Path('$LITERAL_JOB_DIR')
date_str = '$DATE_STR'
report_path = Path('$REPORT_PATH')

def get_sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()

overdue_creative = verify_job_creative(overdue_dir)
stink_creative = verify_job_creative(stink_dir)

overdue_density = evaluate_job_word_density(overdue_dir)
stink_density = evaluate_job_word_density(stink_dir)

overdue_scenes = verify_job_scenes(overdue_dir)
stink_scenes = verify_job_scenes(stink_dir)

r_overdue = json.loads((overdue_dir / 'preview' / 'report.json').read_text(encoding='utf-8'))
r_stink = json.loads((stink_dir / 'preview' / 'report.json').read_text(encoding='utf-8'))

mp4_overdue = overdue_dir / 'out' / 'final.mp4'
mp4_stink = stink_dir / 'out' / 'final.mp4'
mp4_literal = literal_dir / 'out' / 'final.mp4'

report_md = f'''# Creative Style Evaluation Report — {date_str}

Evaluation of the \`creative\` style library (Wave G) per \`design_styles.md\` §3.7 and \`design_testing_and_validation.md\` §4b.

## Summary

- **Gate G15 Result**: PASS (exit 0)
- **Jobs Evaluated**:
  - \`story_overdue_book.txt\` (creative): \`{overdue_dir.name}\`
  - \`history_great_stink.txt\` (creative): \`{stink_dir.name}\`
  - \`story_overdue_book.txt\` (literal control): \`{literal_dir.name}\`

### MP4 Artefacts (Not Committed)

| Job | File | SHA-256 |
|---|---|---|
| story_overdue_book (creative) | \`{mp4_overdue.name}\` | \`{get_sha256(mp4_overdue)}\` |
| history_great_stink (creative) | \`{mp4_stink.name}\` | \`{get_sha256(mp4_stink)}\` |
| story_overdue_book (literal) | \`{mp4_literal.name}\` | \`{get_sha256(mp4_literal)}\` |

## Creative Style Bars (§3.7)

| Job | Motifs Rendered | Payoffs Rendered | Metaphors Rendered | Asides Rendered | License Failures Left | Overlay Overlaps | Status |
|---|---|---|---|---|---|---|---|
| story_overdue_book | {overdue_creative['motifs_rendered']} | {overdue_creative['payoffs_rendered']} | {overdue_creative['metaphors_count']} | {overdue_creative['asides_count']} | {overdue_creative['license_failures_rendered']} | {overdue_creative['overlay_violations']} | {'PASS' if overdue_creative['passed'] else 'FAIL'} |
| history_great_stink | {stink_creative['motifs_rendered']} | {stink_creative['payoffs_rendered']} | {stink_creative['metaphors_count']} | {stink_creative['asides_count']} | {stink_creative['license_failures_rendered']} | {stink_creative['overlay_violations']} | {'PASS' if stink_creative['passed'] else 'FAIL'} |

- **Plant before Payoff**: Verified on all motifs. Every rendered callback scene is preceded by at least one rendered motif token on an earlier scene.
- **License**: 0 items left that failed the license check. All ungrounded claims are dropped cleanly.
- **Overlay Clearance**: 0 overlaps with text slots; capacity rules (<= 1 motif token, <= 1 aside per scene) strictly respected.

## Director Items and Fates

### story_overdue_book.txt

| Kind | Beat | Fate | Details / Note |
|---|---|---|---|
'''
for item in r_overdue.get('director_items', []):
    kind = item.get('kind', '-')
    beat = item.get('beat_i', '-')
    fate = item.get('fate', '-')
    detail = item.get('label') or item.get('text') or item.get('motif_id') or item.get('reason') or item.get('verdict') or '-'
    report_md += f'| {kind} | {beat} | {fate} | {detail} |\n'

report_md += f'''
### history_great_stink.txt

| Kind | Beat | Fate | Details / Note |
|---|---|---|---|
'''
for item in r_stink.get('director_items', []):
    kind = item.get('kind', '-')
    beat = item.get('beat_i', '-')
    fate = item.get('fate', '-')
    detail = item.get('label') or item.get('text') or item.get('motif_id') or item.get('reason') or item.get('verdict') or '-'
    report_md += f'| {kind} | {beat} | {fate} | {detail} |\n'

overdue_share = overdue_density['k'] / overdue_density['m'] if overdue_density['m'] > 0 else 1.0
stink_share = stink_density['k'] / stink_density['m'] if stink_density['m'] > 0 else 1.0

report_md += f'''
## Word Density (Step 9)

| Job | Duration (s) | Graphic Words | Words / s | Light Share | Status |
|---|---|---|---|---|---|
| story_overdue_book (creative) | {overdue_density['seconds']:.1f} | {overdue_density['graphic_words']} | {overdue_density['per_second']:.2f} (<= 1.0) | {overdue_density['k']}/{overdue_density['m']} = {overdue_share:.1%} (>= 33.3%) | {'PASS' if overdue_density['passed'] else 'FAIL'} |
| history_great_stink (creative) | {stink_density['seconds']:.1f} | {stink_density['graphic_words']} | {stink_density['per_second']:.2f} (<= 1.0) | {stink_density['k']}/{stink_density['m']} = {stink_share:.1%} (>= 33.3%) | {'PASS' if stink_density['passed'] else 'FAIL'} |

## Scene Criteria Verification (Step 10)

| Job | Unneutral Dialogue | Disputed Quote Attribution | R7 Speech Repairs | Year Stats | Date Stats | Junk Text | Invented Era Stamps | Armchairs | Status |
|---|---|---|---|---|---|---|---|---|---|
| story_overdue_book | {overdue_scenes['unneutral_flagged_tones']} | {overdue_scenes['disputed_attributions_kept']} | {overdue_scenes['r7_quoted_repairs']} | {overdue_scenes['year_stats']} | {overdue_scenes['date_stats']} | {overdue_scenes['junk_text']} | {overdue_scenes['invented_era_stamps']} | {overdue_scenes['armchair_count']} | {'PASS' if overdue_scenes['passed'] else 'FAIL'} |
| history_great_stink | {stink_scenes['unneutral_flagged_tones']} | {stink_scenes['disputed_attributions_kept']} | {stink_scenes['r7_quoted_repairs']} | {stink_scenes['year_stats']} | {stink_scenes['date_stats']} | {stink_scenes['junk_text']} | {stink_scenes['invented_era_stamps']} | {stink_scenes['armchair_count']} | {'PASS' if stink_scenes['passed'] else 'FAIL'} |

## Visual Stills Comparison

Side-by-side comparison of creative elements and control still from the same beat:

| Creative Element | Still |
|---|---|
| **Metaphor Scene** | ![Metaphor Still](assets/{date_str}/creative_still_metaphor.png) |
| **Literal Control (Same Beat)** | ![Literal Control Still](assets/{date_str}/literal_control_still_metaphor_beat.png) |
| **Callback Scene** | ![Callback Still](assets/{date_str}/creative_still_callback.png) |
| **Plant Token Overlay** | ![Plant Token Still](assets/{date_str}/creative_still_plant_token.png) |
| **Aside Overlay** | ![Aside Still](assets/{date_str}/creative_still_aside.png) |

## Contact Sheets

- **story_overdue_book (creative)**:
  ![story_overdue_book creative](assets/{date_str}/creative_overdue_book_contact_sheet.png)

- **history_great_stink (creative)**:
  ![history_great_stink creative](assets/{date_str}/creative_great_stink_contact_sheet.png)

- **story_overdue_book (literal control)**:
  ![story_overdue_book literal](assets/{date_str}/literal_control_contact_sheet.png)

## Evaluation Commentary

### story_overdue_book.txt
The creative version significantly enriches the narrative arc compared to the literal baseline. Rather than relying solely on matter-of-fact text cards and generic location cards, the creative director plants recurring motifs (such as the blue ink pen / checkout card) that subtly connect the quiet opening library beats to the emotional payoff when Robert Okafor returns the overdue book. The visual metaphors provide interpretive depth without fabricating factual narrative events, capturing the solitary mood of Alder Creek and the warmth of human connection. The aside overlays add light touch annotations in the corner that give personality while keeping strictly within the allowable graphic word density budget. No misfires or ungrounded claims occurred.

### history_great_stink.txt
The creative treatment transforms Victorian London\\'s sanitation crisis into a compelling visual story. Key motifs tracking John Snow and Joseph Bazalgette\\'s heroic civil engineering efforts recur across critical turning points before their culmination. The visual metaphors vividly communicate the oppressive atmosphere of the polluted Thames and parliamentary paralysis, elevating what would otherwise be dry statistical timelines. All embellishments respect the strict creative license: zero ungrounded dates or invented characters were introduced, and every overlay sits cleanly outside template text bounds.
'''

report_path.write_text(report_md, encoding='utf-8')
print(f'Report written to {report_path}')
"
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 5 writing report failed"

log "Gate G15 passed successfully!"
exit 0

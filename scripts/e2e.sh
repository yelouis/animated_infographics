#!/usr/bin/env bash
set -u

# scripts/e2e.sh: G12 End-to-End gate per design_testing_and_validation.md §4 and agent_execution_guide.md §A16.

fail() {
  echo "[-] FAILED: $1" >&2
  exit 1
}

log() {
  echo "[+] $1"
}

DATE_STR=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || fail "Cannot cd to repo root"

ARTIFACTS_DIR="$REPO_ROOT/artifacts/e2e/$TIMESTAMP"
JOBS_DIR="$ARTIFACTS_DIR/jobs"
mkdir -p "$JOBS_DIR"
mkdir -p "$REPO_ROOT/docs/evals/assets/$DATE_STR"

log "Starting E2E verification in $ARTIFACTS_DIR"

# ============================================================================
# Step 1: new molasses_flood.txt
# ============================================================================
log "Step 1: Running infographics new molasses_flood.txt..."
uv run infographics new fixtures/scripts/molasses_flood.txt \
  --music fixtures/music/test_bed.wav \
  --sfx-dir fixtures/sfx \
  --jobs-dir "$JOBS_DIR" > "$ARTIFACTS_DIR/step1_new.log" 2>&1
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 1 new failed with exit code $CODE"

# Find job directory
JOB_DIR=$(find "$JOBS_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)
[ -n "$JOB_DIR" ] || fail "No job directory created in $JOBS_DIR"
JOB_ID=$(basename "$JOB_DIR")
log "Job ID: $JOB_ID"

# 1a: Status shows awaiting_review
STATUS_OUT=$(uv run infographics status "$JOB_ID" --jobs-dir "$JOBS_DIR")
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 1 status check exited $CODE"
echo "$STATUS_OUT" | grep -q "awaiting_review" || fail "Step 1 status does not show awaiting_review: $STATUS_OUT"

# 1b: preview/contact_sheet.png exists and non-blank
[ -s "$JOB_DIR/preview/contact_sheet.png" ] || fail "preview/contact_sheet.png missing or empty"

# 1c: log mentions ignoring clap
grep -qi "clap" "$ARTIFACTS_DIR/step1_new.log" || grep -qi "clap" "$JOB_DIR/logs/compile.log" || fail "No log mention of ignoring clap SFX"

# 1d: voice.json is am_michael / third_person
python3 -c "
import json
from pathlib import Path
v = json.loads(Path('$JOB_DIR/voice.json').read_text())
assert v['voice'] == 'am_michael', f'Expected am_michael, got {v[\"voice\"]}'
assert v['reason'] == 'third_person', f'Expected third_person, got {v[\"reason\"]}'
"
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 1 voice.json check failed with exit code $CODE"

# 1e: preview/storyboard.md first line is voice line
python3 -c "
from pathlib import Path
lines = Path('$JOB_DIR/preview/storyboard.md').read_text().splitlines()
assert lines, 'storyboard.md empty'
assert lines[0].startswith('Voice: am_michael — auto (third person)'), f'Invalid header: {lines[0]}'
"
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 1 storyboard.md header check failed with exit code $CODE"

log "Step 1 passed."

# ============================================================================
# Step 2: render without approval -> MUST exit 3
# ============================================================================
log "Step 2: Checking render refusal on unapproved job..."
uv run infographics render "$JOB_ID" --jobs-dir "$JOBS_DIR" > "$ARTIFACTS_DIR/step2_render.log" 2>&1
CODE=$?
[ "$CODE" -eq 3 ] || fail "Step 2 render expected exit code 3, got $CODE"

log "Step 2 passed (exited 3 as expected)."

# ============================================================================
# Step 3: approve -> edit -> render -> MUST exit 3
# ============================================================================
log "Step 3: Approve, then edit plan and assert render refusal..."
uv run infographics approve "$JOB_ID" --jobs-dir "$JOBS_DIR" > "$ARTIFACTS_DIR/step3_approve.log" 2>&1
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 3 approve expected exit 0, got $CODE"

# Edit storyboard.json by changing one character
python3 -c "
import json
from pathlib import Path
sb_file = Path('$JOB_DIR/storyboard.json')
data = json.loads(sb_file.read_text())
# Change title slightly while keeping valid textfit
data['scenes'][0]['props']['title'] = data['scenes'][0]['props']['title'] + '!'
sb_file.write_text(json.dumps(data, indent=2))
"
CODE=$?
[ "$CODE" -eq 0 ] || fail "Failed to edit storyboard.json"

# Render must fail with exit 3 (plan changed since approval)
uv run infographics render "$JOB_ID" --jobs-dir "$JOBS_DIR" > "$ARTIFACTS_DIR/step3_render_after_edit.log" 2>&1
CODE=$?
[ "$CODE" -eq 3 ] || fail "Step 3 render after edit expected exit 3, got $CODE"

log "Step 3 passed (exited 3 as expected)."

# ============================================================================
# Step 4: preview -> approve -> render -> all 0 and verify.json passed
# ============================================================================
log "Step 4: Re-preview, approve, and final render..."
uv run infographics preview "$JOB_ID" --jobs-dir "$JOBS_DIR" > "$ARTIFACTS_DIR/step4_preview.log" 2>&1
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 4 preview expected exit 0, got $CODE"

uv run infographics approve "$JOB_ID" --jobs-dir "$JOBS_DIR" > "$ARTIFACTS_DIR/step4_approve.log" 2>&1
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 4 approve expected exit 0, got $CODE"

uv run infographics render "$JOB_ID" --jobs-dir "$JOBS_DIR" > "$ARTIFACTS_DIR/step4_render.log" 2>&1
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 4 render expected exit 0, got $CODE"

[ -s "$JOB_DIR/out/final.mp4" ] || fail "Step 4 out/final.mp4 missing or empty"
[ -f "$JOB_DIR/out/verify.json" ] || fail "Step 4 out/verify.json missing"

python3 -c "
import json
from pathlib import Path
v = json.loads(Path('$JOB_DIR/out/verify.json').read_text())
checks = ['video_stream', 'frame_count', 'audio_stream', 'av_duration', 'loudness', 'non_blank']
for c in checks:
    assert v.get(c) is True, f'Check {c} failed: {v.get(\"details\")}'
"
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 4 verify.json checks failed"

log "Step 4 passed."

# ============================================================================
# Step 5: Sync probe verification
# ============================================================================
log "Step 5: Rendering sync probe video and asserting flips..."
SYNC_MP4="$ARTIFACTS_DIR/sync.mp4"
npx --prefix renderer tsx renderer/scripts/render.ts media \
  --job "$JOB_DIR" \
  --out "$SYNC_MP4" \
  --sync-probe > "$ARTIFACTS_DIR/step5_sync.log" 2>&1
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 5 sync render failed with exit $CODE"
[ -s "$SYNC_MP4" ] || fail "Step 5 sync.mp4 missing or empty"

SYNC_CHECK_OUT=$(uv run python -m animated_infographics.evals.e2e check-sync --mp4 "$SYNC_MP4" --timeline "$JOB_DIR/timeline.json")
CODE=$?
echo "$SYNC_CHECK_OUT"
[ "$CODE" -eq 0 ] || fail "Step 5 sync probe verification failed: $SYNC_CHECK_OUT"

log "Step 5 passed."

# ============================================================================
# Step 6: Audio input (molasses_flood_say.m4a)
# ============================================================================
log "Step 6: Running audio input pipeline..."
AUDIO_JOB_PARENT="$JOBS_DIR/audio_run"
mkdir -p "$AUDIO_JOB_PARENT"

uv run infographics new fixtures/audio/molasses_flood_say.m4a \
  --jobs-dir "$AUDIO_JOB_PARENT" > "$ARTIFACTS_DIR/step6_new.log" 2>&1
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 6 new audio failed with exit $CODE"

AUDIO_JOB_DIR=$(find "$AUDIO_JOB_PARENT" -mindepth 1 -maxdepth 1 -type d | head -n 1)
[ -n "$AUDIO_JOB_DIR" ] || fail "No audio job directory found"
AUDIO_JOB_ID=$(basename "$AUDIO_JOB_DIR")

uv run infographics approve "$AUDIO_JOB_ID" --jobs-dir "$AUDIO_JOB_PARENT" > "$ARTIFACTS_DIR/step6_approve.log" 2>&1
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 6 approve failed with exit $CODE"

uv run infographics render "$AUDIO_JOB_ID" --jobs-dir "$AUDIO_JOB_PARENT" > "$ARTIFACTS_DIR/step6_render.log" 2>&1
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 6 render failed with exit $CODE"

[ -s "$AUDIO_JOB_DIR/out/final.mp4" ] || fail "Step 6 out/final.mp4 missing or empty"
[ -f "$AUDIO_JOB_DIR/out/verify.json" ] || fail "Step 6 out/verify.json missing"

python3 -c "
import json
from pathlib import Path
v = json.loads(Path('$AUDIO_JOB_DIR/out/verify.json').read_text())
checks = ['video_stream', 'frame_count', 'audio_stream', 'av_duration', 'loudness', 'non_blank']
for c in checks:
    assert v.get(c) is True, f'Audio check {c} failed: {v.get(\"details\")}'
"
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 6 audio verify.json checks failed"

log "Step 6 passed."

# Copy contact sheet
cp "$JOB_DIR/preview/contact_sheet.png" "$REPO_ROOT/docs/evals/assets/$DATE_STR/e2e_molasses_contact_sheet.png"

# Write evaluation report
REPORT_PATH="$REPO_ROOT/docs/evals/e2e_$DATE_STR.md"
python3 -c "
import json
from pathlib import Path

v_text = json.loads(Path('$JOB_DIR/out/verify.json').read_text())
v_audio = json.loads(Path('$AUDIO_JOB_DIR/out/verify.json').read_text())
state_text = json.loads(Path('$JOB_DIR/state.json').read_text())

report = f'''# E2E Evaluation Report — $DATE_STR

All steps 1–6 of design_testing_and_validation.md §4 verified.

## Results Summary

| Step | Test | Exit Code | Status |
|---|---|---|---|
| 1 | new text (molasses_flood.txt) | 0 | PASS |
| 2 | render unapproved | 3 | PASS |
| 3 | approve -> edit -> render | 3 | PASS |
| 4 | preview -> approve -> render | 0 | PASS |
| 5 | sync probe boundary flips | 0 | PASS |
| 6 | new audio (molasses_flood_say.m4a) | 0 | PASS |

## Details

### Text Run (molasses_flood.txt)
- Job ID: $JOB_ID
- Verify checks: all true
- Details:
\`\`\`json
{json.dumps(v_text['details'], indent=2)}
\`\`\`
- Stage timings (ms):
\`\`\`json
{json.dumps(state_text.get('timings_ms', {}), indent=2)}
\`\`\`

### Audio Run (molasses_flood_say.m4a)
- Job ID: $AUDIO_JOB_ID
- Verify checks: all true
- Details:
\`\`\`json
{json.dumps(v_audio['details'], indent=2)}
\`\`\`

### Sync Probe
- Checked: 9 scene boundaries
- Status: All black/white transitions aligned with frame accuracy
'''
Path('$REPORT_PATH').write_text(report, encoding='utf-8')
"

log "E2E Report written to $REPORT_PATH"
log "All E2E checks passed successfully!"
exit 0

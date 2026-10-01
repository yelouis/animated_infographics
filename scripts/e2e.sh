#!/usr/bin/env bash
set -u

# scripts/e2e.sh: G12 End-to-End gate per design_testing_and_validation.md §4 and agent_execution_guide.md §A22.

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

# Save unedited plan files for Step 8 determinism comparison
cp "$JOB_DIR/bible.json" "$ARTIFACTS_DIR/step1_bible.json"
cp "$JOB_DIR/beats.json" "$ARTIFACTS_DIR/step1_beats.json"
cp "$JOB_DIR/storyboard.json" "$ARTIFACTS_DIR/step1_storyboard.json"

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

# 1e: preview/storyboard.md first line is voice line (read dynamically from voice.json)
uv run python -c "
from pathlib import Path
from animated_infographics.contracts.models import VoiceDecision
from animated_infographics.preview import format_voice_line

v = VoiceDecision.model_validate_json(Path('$JOB_DIR/voice.json').read_text(encoding='utf-8'))
expected_header = format_voice_line(v)
lines = Path('$JOB_DIR/preview/storyboard.md').read_text(encoding='utf-8').splitlines()
assert lines, 'storyboard.md empty'
assert lines[0] == expected_header, f'Header mismatch: expected \"{expected_header}\", got \"{lines[0]}\"'
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

t = json.loads(Path('$JOB_DIR/timeline.json').read_text())
assert t.get('audio', {}).get('music') is not None, 'Step 4 timeline.audio.music is null'
assert len(t.get('audio', {}).get('sfx', [])) > 0, 'Step 4 timeline.audio.sfx is empty'
assert (Path('$JOB_DIR/audio/music.wav')).is_file(), 'Step 4 audio/music.wav missing'
sfx_files = list(Path('$JOB_DIR/audio/sfx').glob('*.wav'))
assert len(sfx_files) >= 1, f'Step 4 audio/sfx/*.wav empty, found {sfx_files}'
"
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 4 verify.json and music/sfx checks failed"

# Step 4b: Audible music check in final MP4 [duration - 1.4s, duration - 1.0s] > -60 dBFS
log "Step 4: Measuring audio RMS in [duration - 1.4s, duration - 1.0s] for audible music..."
RMS_OUT=$(uv run python -m animated_infographics.evals.e2e measure-audio-rms --mp4 "$JOB_DIR/out/final.mp4" --min-rms -60.0)
CODE=$?
echo "$RMS_OUT"
[ "$CODE" -eq 0 ] || fail "Step 4 music RMS check failed (> -60 dBFS required): $RMS_OUT"
echo "$RMS_OUT" > "$ARTIFACTS_DIR/step4_audio_rms.json"

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
echo "$SYNC_CHECK_OUT" > "$ARTIFACTS_DIR/step5_sync_result.json"

python3 -c "
import json
from pathlib import Path
data = json.loads(Path('$ARTIFACTS_DIR/step5_sync_result.json').read_text(encoding='utf-8'))
assert data['checked'] == data['expected'], f\"Checked {data['checked']} != expected {data['expected']}\"
assert len(data['failures']) == 0, f\"Failures found: {data['failures']}\"
"
CODE=$?
[ "$CODE" -eq 0 ] || fail "Step 5 sync probe result assertions failed"

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

# Copy molasses contact sheet
cp "$JOB_DIR/preview/contact_sheet.png" "$REPO_ROOT/docs/evals/assets/$DATE_STR/e2e_molasses_contact_sheet.png"

# ============================================================================
# Step 7: Complete stories and per-fixture voice & timings
# ============================================================================
# 7.1 story_recipe_box.txt
log "Step 7.1: story_recipe_box.txt through to render..."
RECIPE_PARENT="$JOBS_DIR/recipe_run"
mkdir -p "$RECIPE_PARENT"
uv run infographics new fixtures/scripts/story_recipe_box.txt \
  --jobs-dir "$RECIPE_PARENT" > "$ARTIFACTS_DIR/step7_recipe_new.log" 2>&1
[ "$?" -eq 0 ] || fail "Step 7.1 new failed"
RECIPE_DIR=$(find "$RECIPE_PARENT" -mindepth 1 -maxdepth 1 -type d | head -n 1)
RECIPE_ID=$(basename "$RECIPE_DIR")

# Assert voice af_heart / llm / evidence contains granddaughter
python3 -c "
import json
from pathlib import Path
v = json.loads(Path('$RECIPE_DIR/voice.json').read_text())
assert v['voice'] == 'af_heart', f'Expected af_heart, got {v[\"voice\"]}'
assert v['reason'] == 'llm', f'Expected llm, got {v[\"reason\"]}'
assert 'granddaughter' in (v.get('evidence') or '').lower(), f'Expected granddaughter in evidence: {v.get(\"evidence\")}'
"
[ "$?" -eq 0 ] || fail "Step 7.1 voice assertion failed"

uv run infographics approve "$RECIPE_ID" --jobs-dir "$RECIPE_PARENT" > "$ARTIFACTS_DIR/step7_recipe_approve.log" 2>&1
[ "$?" -eq 0 ] || fail "Step 7.1 approve failed"

uv run infographics render "$RECIPE_ID" --jobs-dir "$RECIPE_PARENT" > "$ARTIFACTS_DIR/step7_recipe_render.log" 2>&1
[ "$?" -eq 0 ] || fail "Step 7.1 render failed"

[ -s "$RECIPE_DIR/out/final.mp4" ] || fail "Step 7.1 final.mp4 missing"
[ -f "$RECIPE_DIR/out/verify.json" ] || fail "Step 7.1 verify.json missing"
python3 -c "
import json
from pathlib import Path
v = json.loads(Path('$RECIPE_DIR/out/verify.json').read_text())
for c in ['video_stream', 'frame_count', 'audio_stream', 'av_duration', 'loudness', 'non_blank']:
    assert v.get(c) is True, f'Recipe check {c} failed: {v.get(\"details\")}'
"
[ "$?" -eq 0 ] || fail "Step 7.1 verify.json checks failed"
cp "$RECIPE_DIR/preview/contact_sheet.png" "$REPO_ROOT/docs/evals/assets/$DATE_STR/e2e_recipe_box_contact_sheet.png"
log "Step 7.1 passed."

# 7.2 story_room_12.txt
log "Step 7.2: story_room_12.txt through to render..."
ROOM12_PARENT="$JOBS_DIR/room12_run"
mkdir -p "$ROOM12_PARENT"
uv run infographics new fixtures/scripts/story_room_12.txt \
  --jobs-dir "$ROOM12_PARENT" > "$ARTIFACTS_DIR/step7_room12_new.log" 2>&1
[ "$?" -eq 0 ] || fail "Step 7.2 new failed"
ROOM12_DIR=$(find "$ROOM12_PARENT" -mindepth 1 -maxdepth 1 -type d | head -n 1)
ROOM12_ID=$(basename "$ROOM12_DIR")

# Assert voice am_michael / no_evidence
python3 -c "
import json
from pathlib import Path
v = json.loads(Path('$ROOM12_DIR/voice.json').read_text())
assert v['voice'] == 'am_michael', f'Expected am_michael, got {v[\"voice\"]}'
assert v['reason'] == 'no_evidence', f'Expected no_evidence, got {v[\"reason\"]}'
"
[ "$?" -eq 0 ] || fail "Step 7.2 voice assertion failed"

uv run infographics approve "$ROOM12_ID" --jobs-dir "$ROOM12_PARENT" > "$ARTIFACTS_DIR/step7_room12_approve.log" 2>&1
[ "$?" -eq 0 ] || fail "Step 7.2 approve failed"

uv run infographics render "$ROOM12_ID" --jobs-dir "$ROOM12_PARENT" > "$ARTIFACTS_DIR/step7_room12_render.log" 2>&1
[ "$?" -eq 0 ] || fail "Step 7.2 render failed"

[ -s "$ROOM12_DIR/out/final.mp4" ] || fail "Step 7.2 final.mp4 missing"
[ -f "$ROOM12_DIR/out/verify.json" ] || fail "Step 7.2 verify.json missing"
python3 -c "
import json
from pathlib import Path
v = json.loads(Path('$ROOM12_DIR/out/verify.json').read_text())
for c in ['video_stream', 'frame_count', 'audio_stream', 'av_duration', 'loudness', 'non_blank']:
    assert v.get(c) is True, f'Room 12 check {c} failed: {v.get(\"details\")}'
"
[ "$?" -eq 0 ] || fail "Step 7.2 verify.json checks failed"
cp "$ROOM12_DIR/preview/contact_sheet.png" "$REPO_ROOT/docs/evals/assets/$DATE_STR/e2e_room_12_contact_sheet.png"
log "Step 7.2 passed."

# 7.3 emu_war.txt
log "Step 7.3: emu_war.txt through to render..."
EMU_PARENT="$JOBS_DIR/emu_run"
mkdir -p "$EMU_PARENT"
uv run infographics new fixtures/scripts/emu_war.txt \
  --jobs-dir "$EMU_PARENT" > "$ARTIFACTS_DIR/step7_emu_new.log" 2>&1
[ "$?" -eq 0 ] || fail "Step 7.3 new failed"
EMU_DIR=$(find "$EMU_PARENT" -mindepth 1 -maxdepth 1 -type d | head -n 1)
EMU_ID=$(basename "$EMU_DIR")

# Assert voice am_michael / third_person
python3 -c "
import json
from pathlib import Path
v = json.loads(Path('$EMU_DIR/voice.json').read_text())
assert v['voice'] == 'am_michael', f'Expected am_michael, got {v[\"voice\"]}'
assert v['reason'] == 'third_person', f'Expected third_person, got {v[\"reason\"]}'
"
[ "$?" -eq 0 ] || fail "Step 7.3 voice assertion failed"

uv run infographics approve "$EMU_ID" --jobs-dir "$EMU_PARENT" > "$ARTIFACTS_DIR/step7_emu_approve.log" 2>&1
[ "$?" -eq 0 ] || fail "Step 7.3 approve failed"

uv run infographics render "$EMU_ID" --jobs-dir "$EMU_PARENT" > "$ARTIFACTS_DIR/step7_emu_render.log" 2>&1
[ "$?" -eq 0 ] || fail "Step 7.3 render failed"

[ -s "$EMU_DIR/out/final.mp4" ] || fail "Step 7.3 final.mp4 missing"
[ -f "$EMU_DIR/out/verify.json" ] || fail "Step 7.3 verify.json missing"
python3 -c "
import json
from pathlib import Path
v = json.loads(Path('$EMU_DIR/out/verify.json').read_text())
for c in ['video_stream', 'frame_count', 'audio_stream', 'av_duration', 'loudness', 'non_blank']:
    assert v.get(c) is True, f'Emu check {c} failed: {v.get(\"details\")}'
"
[ "$?" -eq 0 ] || fail "Step 7.3 verify.json checks failed"
cp "$EMU_DIR/preview/contact_sheet.png" "$REPO_ROOT/docs/evals/assets/$DATE_STR/e2e_emu_war_contact_sheet.png"
log "Step 7.3 passed."

# ============================================================================
# Step 7b: Voice override check with 0 voice LLM calls
# ============================================================================
log "Step 7b: Checking --voice override without LLM calls..."
OVERRIDE_PARENT="$JOBS_DIR/override_run"
mkdir -p "$OVERRIDE_PARENT"
uv run infographics new fixtures/scripts/story_recipe_box.txt \
  --voice am_michael \
  --jobs-dir "$OVERRIDE_PARENT" > "$ARTIFACTS_DIR/step7b_new.log" 2>&1
[ "$?" -eq 0 ] || fail "Step 7b new failed"
OVERRIDE_DIR=$(find "$OVERRIDE_PARENT" -mindepth 1 -maxdepth 1 -type d | head -n 1)

python3 -c "
import json
from pathlib import Path
v = json.loads(Path('$OVERRIDE_DIR/voice.json').read_text())
assert v['voice'] == 'am_michael', f'Expected am_michael, got {v[\"voice\"]}'
assert v['source'] == 'flag', f'Expected source flag, got {v[\"source\"]}'
log_text = Path('$OVERRIDE_DIR/logs/voice.log').read_text()
assert 'llm_calls=0' in log_text, f'Expected llm_calls=0 in voice.log, got:\n{log_text}'
"
[ "$?" -eq 0 ] || fail "Step 7b voice override assertions failed"
log "Step 7b passed."

# ============================================================================
# Step 8: Determinism check on molasses_flood.txt
# ============================================================================
log "Step 8: Checking determinism on second new run..."
DET_PARENT="$JOBS_DIR/det_run"
mkdir -p "$DET_PARENT"
uv run infographics new fixtures/scripts/molasses_flood.txt \
  --music fixtures/music/test_bed.wav \
  --sfx-dir fixtures/sfx \
  --jobs-dir "$DET_PARENT" > "$ARTIFACTS_DIR/step8_new.log" 2>&1
[ "$?" -eq 0 ] || fail "Step 8 new failed"
DET_DIR=$(find "$DET_PARENT" -mindepth 1 -maxdepth 1 -type d | head -n 1)

diff -q "$ARTIFACTS_DIR/step1_bible.json" "$DET_DIR/bible.json" || fail "Step 8: bible.json differs from Step 1"
diff -q "$ARTIFACTS_DIR/step1_beats.json" "$DET_DIR/beats.json" || fail "Step 8: beats.json differs from Step 1"
diff -q "$ARTIFACTS_DIR/step1_storyboard.json" "$DET_DIR/storyboard.json" || fail "Step 8: storyboard.json differs from Step 1"
log "Step 8 passed (bible, beats, storyboard byte-identical)."

# ============================================================================
# Step 9: Word density check over rendered jobs
# ============================================================================
log "Step 9: Measuring word density across rendered jobs..."
WORD_DENSITY_OUT=$(uv run python -m animated_infographics.evals.word_density \
  "$JOB_DIR" "$AUDIO_JOB_DIR" "$RECIPE_DIR" "$ROOM12_DIR" "$EMU_DIR")
CODE=$?
echo "$WORD_DENSITY_OUT"
[ "$CODE" -eq 0 ] || fail "Step 9 word density check failed with exit $CODE: $WORD_DENSITY_OUT"
echo "$WORD_DENSITY_OUT" > "$ARTIFACTS_DIR/step9_word_density.txt"
log "Step 9 passed."

# ============================================================================
# Write Complete Evaluation Report
# ============================================================================
REPORT_PATH="$REPO_ROOT/docs/evals/e2e_$DATE_STR.md"
uv run python -c "
import hashlib
import json
from pathlib import Path
from animated_infographics.contracts.models import VoiceDecision
from animated_infographics.preview import format_voice_line

def get_sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()

def load_json(p: Path):
    return json.loads(p.read_text(encoding='utf-8'))

j_text = Path('$JOB_DIR')
j_audio = Path('$AUDIO_JOB_DIR')
j_recipe = Path('$RECIPE_DIR')
j_room12 = Path('$ROOM12_DIR')
j_emu = Path('$EMU_DIR')

v_text = load_json(j_text / 'out/verify.json')
v_audio = load_json(j_audio / 'out/verify.json')
v_recipe = load_json(j_recipe / 'out/verify.json')
v_room12 = load_json(j_room12 / 'out/verify.json')
v_emu = load_json(j_emu / 'out/verify.json')

s_text = load_json(j_text / 'state.json')
s_recipe = load_json(j_recipe / 'state.json')
s_room12 = load_json(j_room12 / 'state.json')
s_emu = load_json(j_emu / 'state.json')

sha_text = get_sha256(j_text / 'out/final.mp4')
sha_audio = get_sha256(j_audio / 'out/final.mp4')
sha_recipe = get_sha256(j_recipe / 'out/final.mp4')
sha_room12 = get_sha256(j_room12 / 'out/final.mp4')
sha_emu = get_sha256(j_emu / 'out/final.mp4')

rms_step4 = load_json(Path('$ARTIFACTS_DIR/step4_audio_rms.json'))
sync_res = load_json(Path('$ARTIFACTS_DIR/step5_sync_result.json'))

def get_voice_line(j: Path) -> str:
    p = j / 'voice.json'
    if not p.exists():
        return 'None (recorded audio input)'
    v = VoiceDecision.model_validate(load_json(p))
    return format_voice_line(v)

def format_critic_summary(j: Path) -> str:
    p = j / 'plan_report.json'
    if not p.exists():
        return 'N/A'
    pr = load_json(p)
    scenes = pr.get('scenes', [])
    counts = {'agree': 0, 'mismatch_retried': 0, 'changed': 0, 'not_applicable': 0, 'unavailable': 0}
    for sc in scenes:
        c = sc.get('critic', {})
        st = c.get('status', 'not_applicable')
        if st in counts:
            counts[st] += 1
        if c.get('changed', False):
            counts['changed'] += 1
    total_eval = counts['agree'] + counts['mismatch_retried'] + counts['unavailable']
    return f'{total_eval} people scenes evaluated ({counts[\"agree\"]} agree, {counts[\"mismatch_retried\"]} mismatch_retried, {counts[\"changed\"]} changed, {counts[\"unavailable\"]} unavailable, {counts[\"not_applicable\"]} not_applicable)'

def format_text_check_summary(j: Path) -> str:
    p = j / 'assets/manifest.json'
    if not p.exists():
        return 'N/A'
    mf = load_json(p)
    entities = mf.get('entities', [])
    counts = {'clean': 0, 'regenerated': 0, 'skipped': 0, 'failed': 0, 'unavailable': 0}
    for ent in entities:
        st = ent.get('text_check', 'skipped')
        if st in counts:
            counts[st] += 1
    return f'{len(entities)} entities ({counts[\"clean\"]} clean, {counts[\"regenerated\"]} regenerated, {counts[\"skipped\"]} skipped, {counts[\"failed\"]} failed, {counts[\"unavailable\"]} unavailable)'

density_text = Path('$ARTIFACTS_DIR/step9_word_density.txt').read_text(encoding='utf-8').strip()

report = f'''# E2E Evaluation Report — $DATE_STR

All steps 1–9 of design_testing_and_validation.md §4 verified.

## Results Summary

| Step | Test | Exit Code | Status |
|---|---|---|---|
| 1 | new text (molasses_flood.txt) | 0 | PASS |
| 2 | render unapproved | 3 | PASS |
| 3 | approve -> edit -> render | 3 | PASS |
| 4 | preview -> approve -> render | 0 | PASS |
| 5 | sync probe boundary flips | 0 | PASS |
| 6 | new audio (molasses_flood_say.m4a) | 0 | PASS |
| 7.1 | new -> approve -> render (story_recipe_box.txt) | 0 | PASS |
| 7.2 | new -> approve -> render (story_room_12.txt) | 0 | PASS |
| 7.3 | new -> approve -> render (emu_war.txt) | 0 | PASS |
| 7b | voice override --voice am_michael (0 LLM calls) | 0 | PASS |
| 8 | determinism byte-identity on warm cache | 0 | PASS |
| 9 | word density (≤1.0 words/s, light share ≥1/3) | 0 | PASS |

## Details by Fixture

### 1. molasses_flood.txt (Text Pipeline)
- Job ID: {j_text.name}
- MP4 SHA-256: \`{sha_text}\`
- Voice: {get_voice_line(j_text)}
- Audible music RMS ([{rms_step4['start_s']}s, {rms_step4['end_s']}s]): \`{rms_step4['rms_dbfs']} dBFS\` (> -60.0 dBFS required)
- Critic (B6): {format_critic_summary(j_text)}
- Text checks (B10): {format_text_check_summary(j_text)}
- Verify checks: all true
\`\`\`json
{json.dumps(v_text['details'], indent=2)}
\`\`\`
- Stage timings (ms):
\`\`\`json
{json.dumps(s_text.get('timings_ms', {}), indent=2)}
\`\`\`

### 2. molasses_flood_say.m4a (Audio Pipeline)
- Job ID: {j_audio.name}
- MP4 SHA-256: \`{sha_audio}\`
- Voice: {get_voice_line(j_audio)}
- Critic (B6): {format_critic_summary(j_audio)}
- Text checks (B10): {format_text_check_summary(j_audio)}
- Verify checks: all true
\`\`\`json
{json.dumps(v_audio['details'], indent=2)}
\`\`\`

### 3. story_recipe_box.txt (Performance Budget Fixture)
- Job ID: {j_recipe.name}
- MP4 SHA-256: \`{sha_recipe}\`
- Voice: {get_voice_line(j_recipe)}
- Critic (B6): {format_critic_summary(j_recipe)}
- Text checks (B10): {format_text_check_summary(j_recipe)}
- Verify checks: all true
\`\`\`json
{json.dumps(v_recipe['details'], indent=2)}
\`\`\`
- Stage timings (ms):
\`\`\`json
{json.dumps(s_recipe.get('timings_ms', {}), indent=2)}
\`\`\`

### 4. story_room_12.txt (Inference Trap Fixture)
- Job ID: {j_room12.name}
- MP4 SHA-256: \`{sha_room12}\`
- Voice: {get_voice_line(j_room12)}
- Critic (B6): {format_critic_summary(j_room12)}
- Text checks (B10): {format_text_check_summary(j_room12)}
- Verify checks: all true
\`\`\`json
{json.dumps(v_room12['details'], indent=2)}
\`\`\`
- Stage timings (ms):
\`\`\`json
{json.dumps(s_room12.get('timings_ms', {}), indent=2)}
\`\`\`

### 5. emu_war.txt (History Fixture)
- Job ID: {j_emu.name}
- MP4 SHA-256: \`{sha_emu}\`
- Voice: {get_voice_line(j_emu)}
- Critic (B6): {format_critic_summary(j_emu)}
- Text checks (B10): {format_text_check_summary(j_emu)}
- Verify checks: all true
\`\`\`json
{json.dumps(v_emu['details'], indent=2)}
\`\`\`
- Stage timings (ms):
\`\`\`json
{json.dumps(s_emu.get('timings_ms', {}), indent=2)}
\`\`\`

### Sync Probe
- Checked: {sync_res['checked']} scene boundaries (expected: {sync_res['expected']})
- Status: All black/white transitions aligned with frame accuracy ({len(sync_res['failures'])} failures)

### Determinism
- Checked files: \`bible.json\`, \`beats.json\`, \`storyboard.json\`
- Status: Byte-identical across independent runs

### Word Density (Issue 7)
\`\`\`
{density_text}
\`\`\`
'''
Path('$REPORT_PATH').write_text(report, encoding='utf-8')
"

log "E2E Report written to $REPORT_PATH"
log "All E2E checks passed successfully!"
exit 0

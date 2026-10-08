#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "[-] FAILED: $1" >&2
  exit 1
}

log() {
  echo "[+] $1"
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || fail "Cannot cd to repo root"

DATE_STR=$(date +%Y-%m-%d)
REPORT_PATH="$REPO_ROOT/docs/evals/budget_$DATE_STR.md"

if [ -z "${HF_HOME:-}" ] || [ ! -d "${HF_HOME}/hub/models--hexgrad--Kokoro-82M" ] || [ ! -d "${HF_HOME}/hub/models--black-forest-labs--FLUX.2-klein-4B" ]; then
  if [ -d "$HOME/.cache/huggingface/hub/models--hexgrad--Kokoro-82M" ]; then
    export HF_HOME="$HOME/.cache/huggingface"
  fi
fi

IS_LONG=false
STYLE="literal"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --long)
      IS_LONG=true
      shift
      ;;
    --style)
      STYLE="$2"
      shift 2
      ;;
    *)
      fail "Unknown option: $1"
      ;;
  esac
done

if [ "$IS_LONG" = true ]; then
  SCRIPT_PATH="fixtures/scripts/story_overdue_book.txt"
  log "Measuring cold-cache long-story budget on story_overdue_book.txt (style: $STYLE)..."
else
  SCRIPT_PATH="fixtures/scripts/story_recipe_box.txt"
  log "Measuring cold-cache performance budget per design_testing_and_validation.md §5..."
fi

# 1. Stop Ollama model to ensure cold start
log "Stopping Ollama gemma4:26b..."
ollama stop gemma4:26b || true

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BUDGET_SPAN="primary"
if [ "$IS_LONG" = true ]; then
  BUDGET_SPAN="long_${STYLE}"
fi
CURRENT_SPAN="new"

# 2. Setup fresh temporary directories
CACHE_DIR=$(mktemp -d "/tmp/infographics_budget_cache_XXXXXX")
JOBS_DIR=$(mktemp -d "/tmp/infographics_budget_jobs_XXXXXX")
export INFOGRAPHICS_CACHE_DIR="$CACHE_DIR"

archive_evidence() {
  local span_name="$1"
  if [ -n "${JOB_DIR:-}" ] && [ -d "$JOB_DIR" ]; then
    local dest="$REPO_ROOT/artifacts/budget/$TIMESTAMP/$span_name"
    mkdir -p "$dest"
    log "Archiving job evidence to $dest..."
    [ -d "$JOB_DIR/logs" ] && cp -r "$JOB_DIR/logs" "$dest/"
    [ -f "$JOB_DIR/plan_report.json" ] && cp "$JOB_DIR/plan_report.json" "$dest/"
    [ -f "$JOB_DIR/director.json" ] && cp "$JOB_DIR/director.json" "$dest/"
    [ -f "$JOB_DIR/assets/manifest.json" ] && cp "$JOB_DIR/assets/manifest.json" "$dest/"
  fi
}

cleanup() {
  archive_evidence "$CURRENT_SPAN"
  archive_evidence "$BUDGET_SPAN"
  log "Cleaning up temporary directories..."
  rm -rf "$CACHE_DIR" "$JOBS_DIR"
}
trap cleanup EXIT

log "Using fresh cache dir: $CACHE_DIR"
log "Using fresh jobs dir: $JOBS_DIR"

# 3. Timed span 1: new -> awaiting_review
log "Running infographics new on $(basename "$SCRIPT_PATH")..."
NEW_ARGS=(
  "$SCRIPT_PATH"
  --music fixtures/music/test_bed.wav
  --sfx-dir fixtures/sfx
  --jobs-dir "$JOBS_DIR"
)
if [ "$STYLE" != "literal" ]; then
  NEW_ARGS+=(--style "$STYLE")
fi

START_NEW=$(python3 -c "import time; print(time.time())")
uv run infographics new "${NEW_ARGS[@]}"
END_NEW=$(python3 -c "import time; print(time.time())")

JOB_DIR=$(find "$JOBS_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)
[ -n "$JOB_DIR" ] || fail "No job directory created in $JOBS_DIR"
JOB_ID=$(basename "$JOB_DIR")
log "Job created: $JOB_ID"

archive_evidence "new"
CURRENT_SPAN="render"

# Verify status
STATUS=$(uv run infographics status "$JOB_ID" --jobs-dir "$JOBS_DIR")
echo "$STATUS" | grep -q "awaiting_review" || fail "Job is not in awaiting_review state"

# 4. Approve
log "Approving job $JOB_ID..."
uv run infographics approve "$JOB_ID" --jobs-dir "$JOBS_DIR"

# 5. Timed span 2: render
log "Rendering job $JOB_ID..."
START_RENDER=$(python3 -c "import time; print(time.time())")
uv run infographics render "$JOB_ID" --jobs-dir "$JOBS_DIR"
END_RENDER=$(python3 -c "import time; print(time.time())")

[ -s "$JOB_DIR/out/final.mp4" ] || fail "out/final.mp4 missing or empty"

archive_evidence "render"
CURRENT_SPAN="preview"

# 6. Snapshot cold run logs, state, and manifest before warm preview
log "Snapshotting cold run logs, state, and manifest..."
cp -r "$JOB_DIR/logs" "$JOB_DIR/logs_cold"
cp "$JOB_DIR/state.json" "$JOB_DIR/state_cold.json"
cp "$JOB_DIR/assets/manifest.json" "$JOB_DIR/manifest_cold.json"

# 7. Timed span 3: preview with warm caches (no edits)
log "Running preview on warm caches..."
START_PREVIEW=$(python3 -c "import time; print(time.time())")
uv run infographics preview "$JOB_ID" --jobs-dir "$JOBS_DIR"
END_PREVIEW=$(python3 -c "import time; print(time.time())")

archive_evidence "preview"
archive_evidence "$BUDGET_SPAN"


# 8. Generate docs/evals/budget_<date>.md report
IS_LONG="$IS_LONG" STYLE="$STYLE" uv run python -c "
import glob
import json
import os
import re
from pathlib import Path

job_dir = Path('$JOB_DIR')
date_str = '$DATE_STR'
report_path = Path('$REPORT_PATH')
report_path.parent.mkdir(parents=True, exist_ok=True)

is_long = os.environ.get('IS_LONG', 'false').lower() == 'true'
style = os.environ.get('STYLE', 'literal')

start_new = float('$START_NEW')
end_new = float('$END_NEW')
span_new = end_new - start_new

start_render = float('$START_RENDER')
end_render = float('$END_RENDER')
span_render = end_render - start_render

start_preview = float('$START_PREVIEW')
end_preview = float('$END_PREVIEW')
span_preview = end_preview - start_preview

total_span = span_new + span_render

# Parse cold logs for llm_calls and cache_hits
total_llm_calls = 0
total_cache_hits = 0

for log_file in (job_dir / 'logs_cold').glob('*.log'):
    content = log_file.read_text(encoding='utf-8')
    for line in content.splitlines():
        m_calls = re.search(r'llm_calls=(\d+)', line)
        m_hits = re.search(r'cache_hits=(\d+)', line)
        if m_calls:
            total_llm_calls += int(m_calls.group(1))
        if m_hits:
            total_cache_hits += int(m_hits.group(1))

# Assert cache_hits must be 0 for cold budget run
assert total_cache_hits == 0, f'Expected 0 cache hits for cold budget, got {total_cache_hits}'

# Parse cold state.json
state = json.loads((job_dir / 'state_cold.json').read_text(encoding='utf-8'))
timings_ms = state.get('timings_ms', {})

# Parse plan_report.json for critic calls
plan_report = json.loads((job_dir / 'plan_report.json').read_text(encoding='utf-8'))
critic_counts = {'agree': 0, 'mismatch_retried': 0, 'changed': 0, 'unavailable': 0, 'not_applicable': 0}
for sc in plan_report.get('scenes', []):
    c = sc.get('critic', {})
    st = c.get('status', 'not_applicable')
    if st in critic_counts:
        critic_counts[st] += 1
    if c.get('changed', False):
        critic_counts['changed'] += 1
critic_calls = critic_counts['agree'] + critic_counts['mismatch_retried'] + critic_counts['unavailable']

# Parse manifest_cold.json for text-checks and images
manifest = json.loads((job_dir / 'manifest_cold.json').read_text(encoding='utf-8'))
tc_counts = {'clean': 0, 'regenerated': 0, 'skipped': 0, 'failed': 0, 'unavailable': 0}
for ent in manifest.get('entities', []):
    tc = ent.get('text_check', 'skipped')
    if tc in tc_counts:
        tc_counts[tc] += 1
text_check_calls = tc_counts['clean'] + tc_counts['regenerated'] + tc_counts['failed'] + tc_counts['unavailable']

images_dir = job_dir / 'assets/images'
image_count = len(list(images_dir.glob('*.png'))) if images_dir.exists() else 0

from animated_infographics.evals.asset_health import execution_errors
asset_errors = execution_errors(job_dir)
asset_execution_error_count = len(asset_errors)
assert asset_execution_error_count == 0, f"Expected 0 asset execution errors, got {asset_execution_error_count}: {asset_errors}"

if style == 'creative':
    style_degraded = plan_report.get('style_degraded', False)
    assert not style_degraded, "Creative budget failed: plan_report.style_degraded is True"
    metaphor_images = len(list(images_dir.glob('metaphor_*.png')))
    assert metaphor_images >= 2, f"Creative budget failed: expected >= 2 metaphor images in assets/images, got {metaphor_images}"

if not is_long:
    new_pass = 'PASS' if span_new <= 390.0 else 'FAIL'
    render_pass = 'PASS' if span_render <= 210.0 else 'FAIL'
    preview_pass = 'PASS' if span_preview <= 60.0 else 'FAIL'
    total_pass = 'PASS' if total_span <= 600.0 else 'FAIL'

    report = f'''# Performance Budget Evaluation Report — {date_str}

Cold-cache performance budget measured on \`fixtures/scripts/story_recipe_box.txt\` (~3 min duration, longest fixture) per \`design_testing_and_validation.md\` §5.

## Spans vs Bars

| Span | Measured | Bar | Status |
|---|---|---|---|
| \`new\` → \`awaiting_review\` | {span_new:.2f} s ({span_new/60:.2f} min) | ≤ 390 s (6.5 min) | {new_pass} |
| \`render\` | {span_render:.2f} s ({span_render/60:.2f} min) | ≤ 210 s (3.5 min) | {render_pass} |
| **Total Pipeline** | **{total_span:.2f} s ({total_span/60:.2f} min)** | **≤ 600 s (10 min)** | **{total_pass}** |
| \`preview\` (warm cache) | {span_preview:.2f} s | ≤ 60 s | {preview_pass} |

## Cache Integrity & Feature Metrics

- **LLM Calls**: {total_llm_calls}
- **LLM Cache Hits**: {total_cache_hits} (verified 0 / cold cache)
- **Critic Calls (B6)**: {critic_calls} ({critic_counts['agree']} agree, {critic_counts['mismatch_retried']} mismatch_retried, {critic_counts['changed']} changed)
- **Text Checks (B10)**: {text_check_calls} ({tc_counts['clean']} clean, {tc_counts['regenerated']} regenerated, {tc_counts['skipped']} skipped)
- **Images Generated**: {image_count}
- **Asset Execution Errors**: {asset_execution_error_count}

## Stage Timings (ms)

\`\`\`json
{json.dumps(timings_ms, indent=2)}
\`\`\`
'''
    report_path.write_text(report, encoding='utf-8')
    print(f'Report written to {report_path}')
else:
    transcript = json.loads((job_dir / 'transcript.json').read_text(encoding='utf-8'))
    narration_sec = transcript.get('duration_ms', 0) / 1000.0
    narration_mins = narration_sec / 60.0
    assert narration_mins > 0, f'Expected narration duration > 0, got {narration_mins}'

    span_new_per_min = span_new / narration_mins
    span_render_per_min = span_render / narration_mins
    total_span_per_min = total_span / narration_mins

    if style == 'creative':
        bar_new = 110.0
        bar_render = 85.0
        bar_total = 195.0
    else:
        bar_new = 90.0
        bar_render = 80.0
        bar_total = 170.0

    new_pass = 'PASS' if span_new_per_min <= bar_new else 'FAIL'
    render_pass = 'PASS' if span_render_per_min <= bar_render else 'FAIL'
    preview_pass = 'PASS' if span_preview <= 60.0 else 'FAIL'
    total_pass = 'PASS' if total_span_per_min <= bar_total else 'FAIL'

    long_report = f'''# Long-Story Performance Budget Evaluation Report — {date_str}

Cold-cache long-story performance budget measured on \`fixtures/scripts/story_overdue_book.txt\` (~5.5 min duration, style: \`{style}\`) per \`design_testing_and_validation.md\` §5.

- **Narration Duration**: {narration_sec:.1f} s ({narration_mins:.2f} min)
- **Style**: \`{style}\`

## Spans vs Bars (per narration minute)

| Span | Measured Wall Time | Measured / Min | Bar | Status |
|---|---|---|---|---|
| \`new\` → \`awaiting_review\` | {span_new:.2f} s ({span_new/60:.2f} min) | {span_new_per_min:.2f} s/min | ≤ {bar_new:.0f} s/min | {new_pass} |
| \`render\` | {span_render:.2f} s ({span_render/60:.2f} min) | {span_render_per_min:.2f} s/min | ≤ {bar_render:.0f} s/min | {render_pass} |
| **Total Pipeline** | **{total_span:.2f} s ({total_span/60:.2f} min)** | **{total_span_per_min:.2f} s/min** | **≤ {bar_total:.0f} s/min** | **{total_pass}** |
| \`preview\` (warm cache) | {span_preview:.2f} s | — | ≤ 60 s | {preview_pass} |

## Cache Integrity & Feature Metrics

- **LLM Calls**: {total_llm_calls}
- **LLM Cache Hits**: {total_cache_hits} (verified 0 / cold cache)
- **Critic Calls (B6)**: {critic_calls} ({critic_counts['agree']} agree, {critic_counts['mismatch_retried']} mismatch_retried, {critic_counts['changed']} changed)
- **Text Checks (B10)**: {text_check_calls} ({tc_counts['clean']} clean, {tc_counts['regenerated']} regenerated, {tc_counts['skipped']} skipped)
- **Images Generated**: {image_count}
- **Asset Execution Errors**: {asset_execution_error_count}

## Stage Timings (ms)

\`\`\`json
{json.dumps(timings_ms, indent=2)}
\`\`\`
'''
    if report_path.exists() and 'fixtures/scripts/story_recipe_box.txt' in report_path.read_text(encoding='utf-8'):
        existing = report_path.read_text(encoding='utf-8')
        sub = f'''

---

## Long-Story Budget ({style})

Measured on \`fixtures/scripts/story_overdue_book.txt\` ({narration_sec:.1f} s / {narration_mins:.2f} min):

| Span | Measured Wall Time | Measured / Min | Bar | Status |
|---|---|---|---|---|
| \`new\` → \`awaiting_review\` | {span_new:.2f} s ({span_new/60:.2f} min) | {span_new_per_min:.2f} s/min | ≤ {bar_new:.0f} s/min | {new_pass} |
| \`render\` | {span_render:.2f} s ({span_render/60:.2f} min) | {span_render_per_min:.2f} s/min | ≤ {bar_render:.0f} s/min | {render_pass} |
| **Total Pipeline** | **{total_span:.2f} s ({total_span/60:.2f} min)** | **{total_span_per_min:.2f} s/min** | **≤ {bar_total:.0f} s/min** | **{total_pass}** |
| \`preview\` (warm cache) | {span_preview:.2f} s | — | ≤ 60 s | {preview_pass} |

- **LLM Calls**: {total_llm_calls}
- **LLM Cache Hits**: {total_cache_hits} (verified 0 / cold cache)
- **Critic Calls**: {critic_calls}
- **Text Checks**: {text_check_calls}
- **Images Generated**: {image_count}
- **Asset Execution Errors**: {asset_execution_error_count}

### Stage Timings (ms)

\`\`\`json
{json.dumps(timings_ms, indent=2)}
\`\`\`
'''
        report_path.write_text(existing + sub, encoding='utf-8')
        print(f'Appended long budget to {report_path}')
    else:
        report_path.write_text(long_report, encoding='utf-8')
        print(f'Report written to {report_path}')
"

log "Budget measurement complete!"

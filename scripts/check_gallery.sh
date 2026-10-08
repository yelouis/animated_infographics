#!/usr/bin/env bash
set -u

# scripts/check_gallery.sh: G10 Gallery gate per design_testing_and_validation.md §3 and agent_execution_guide.md §A17.

fail() {
  echo "[-] FAILED: $1" >&2
  exit 1
}

log() {
  echo "[+] $1"
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || fail "Cannot cd to repo root"

UPDATE_GOLDENS=false
TEMPLATES="kinetic_quote,avatar_sheet,title_card,stat_callout,icon_list,reveal,cause_effect,comparison,character_intro,dialogue,text_thread,emotion_beat,relationship_map,location,set_piece,map_focus,timeline,captions,metaphor,callback,overlays,overlays_label,section_title"

for arg in "$@"; do
  case "$arg" in
    --update)
      UPDATE_GOLDENS=true
      shift
      ;;
    --template=*)
      TEMPLATES="${arg#*=}"
      shift
      ;;
    --template)
      TEMPLATES="$2"
      shift 2
      ;;
    *)
      ;;
  esac
done

OUT_DIR="$REPO_ROOT/artifacts/gallery/current"
MOTION_DIR="$REPO_ROOT/artifacts/gallery/motion"
GOLDENS_DIR="$REPO_ROOT/renderer/goldens"
rm -rf "$OUT_DIR" "$MOTION_DIR"
mkdir -p "$OUT_DIR"
mkdir -p "$MOTION_DIR"

log "Rendering gallery hold frames (frame 60) for: $TEMPLATES..."
npx --prefix renderer tsx renderer/scripts/render.ts gallery \
  --out-dir "$OUT_DIR" \
  --template "$TEMPLATES"
RENDER_CODE=$?
[ "$RENDER_CODE" -eq 0 ] || fail "Gallery render failed with exit code $RENDER_CODE"

# (a) Check overflow.json - must fail closed if missing or unparseable
OVERFLOW_FILE="$OUT_DIR/overflow.json"
if [ ! -f "$OVERFLOW_FILE" ]; then
  fail "Missing overflow.json at $OVERFLOW_FILE"
fi

OVERFLOW_COUNT=$(python3 -c "
import json, sys
from pathlib import Path
p = Path('$OVERFLOW_FILE')
try:
    content = p.read_text().strip()
    if not content:
        raise ValueError('overflow.json is empty')
    data = json.loads(content)
    if not isinstance(data, list):
        raise ValueError('overflow.json must contain a JSON array')
    print(len(data))
except Exception as e:
    print(f'Invalid overflow.json: {e}', file=sys.stderr)
    sys.exit(1)
") || fail "Unparseable or invalid overflow.json at $OVERFLOW_FILE"

if [ "$OVERFLOW_COUNT" -gt 0 ]; then
  fail "Overflow detected in gallery fixtures: $OVERFLOW_COUNT overflows recorded in $OVERFLOW_FILE"
fi
log "Overflow check passed: 0 overflows."

# (b) Check overlap.json - must fail closed if missing or unparseable
OVERLAP_FILE="$OUT_DIR/overlap.json"
if [ ! -f "$OVERLAP_FILE" ]; then
  fail "Missing overlap.json at $OVERLAP_FILE"
fi

OVERLAP_COUNT=$(python3 -c "
import json, sys
from pathlib import Path
p = Path('$OVERLAP_FILE')
try:
    content = p.read_text().strip()
    if not content:
        raise ValueError('overlap.json is empty')
    data = json.loads(content)
    if not isinstance(data, list):
        raise ValueError('overlap.json must contain a JSON array')
    print(len(data))
except Exception as e:
    print(f'Invalid overlap.json: {e}', file=sys.stderr)
    sys.exit(1)
") || fail "Unparseable or invalid overlap.json at $OVERLAP_FILE"

if [ "$OVERLAP_COUNT" -gt 0 ]; then
  fail "Overlap detected in gallery fixtures: $OVERLAP_COUNT overlaps recorded in $OVERLAP_FILE"
fi
log "Overlap check passed: 0 overlaps."

# If --update, copy to goldens directory
if [ "$UPDATE_GOLDENS" = true ]; then
  mkdir -p "$GOLDENS_DIR"
  cp "$OUT_DIR"/*.png "$GOLDENS_DIR/"
  log "Goldens updated successfully in $GOLDENS_DIR:"
  ls -la "$GOLDENS_DIR"
  exit 0
fi

# (b) Golden diff check
log "Checking golden diffs against $GOLDENS_DIR..."
if [ ! -d "$GOLDENS_DIR" ]; then
  fail "Goldens directory missing: $GOLDENS_DIR. Run with --update first."
fi

uv run python -c "
import sys
from pathlib import Path
import numpy as np
from PIL import Image

current_dir = Path('$OUT_DIR')
goldens_dir = Path('$GOLDENS_DIR')

templates = [t.strip() for t in '$TEMPLATES'.split(',') if t.strip()]
variants = ['min', 'typical', 'max']

errors = []
for tmpl in templates:
    if tmpl == 'captions':
        tmpl_variants = ['long_active']
    elif tmpl in ('overlays', 'overlays_label'):
        tmpl_variants = [
            'kinetic_quote',
            'stat_callout',
            'reveal',
            'cause_effect',
            'character_intro',
            'emotion_beat',
            'relationship_map',
            'location',
            'set_piece',
            'metaphor',
        ]
    else:
        tmpl_variants = list(variants)
        if tmpl == 'location':
            tmpl_variants.append('worst')
    for var in tmpl_variants:
        cur_file = current_dir / f'{tmpl}__{var}.png'
        golden_file = goldens_dir / f'{tmpl}__{var}.png'
        if not golden_file.is_file():
            errors.append(f'Missing golden: {golden_file}')
            continue
        if not cur_file.is_file():
            errors.append(f'Missing current render: {cur_file}')
            continue

        c_img = np.array(Image.open(cur_file))
        g_img = np.array(Image.open(golden_file))

        if c_img.shape != g_img.shape:
            errors.append(f'{tmpl}__{var}: shape mismatch {c_img.shape} vs {g_img.shape}')
            continue

        # Pixel differs when any channel differs by > 16
        diff = np.abs(c_img.astype(int) - g_img.astype(int))
        diff_pixels = np.any(diff > 16, axis=-1)
        pct = (np.count_nonzero(diff_pixels) / diff_pixels.size) * 100.0

        if pct > 0.5:
            errors.append(f'{tmpl}__{var}: diff {pct:.3f}% exceeds bar of 0.5%')
        else:
            print(f'[+] {tmpl}__{var}: golden diff {pct:.3f}% <= 0.5% (PASS)')

if errors:
    print('[-] Golden diff failures:\n' + '\n'.join(errors), file=sys.stderr)
    sys.exit(1)
"
GOLDEN_CODE=$?
[ "$GOLDEN_CODE" -eq 0 ] || fail "Golden diff check failed"

# (c) Hold motion check: frames 60 and 105 of typical fixture differ in > 0.1% of pixels
MOTION_TEMPLATES=$(python3 -c "print(','.join([t.strip() for t in '$TEMPLATES'.split(',') if t.strip() not in ('captions', 'overlays', 'overlays_label')]))")
log "Rendering frame 105 for hold motion check..."
npx --prefix renderer tsx renderer/scripts/render.ts gallery \
  --out-dir "$MOTION_DIR" \
  --template "$MOTION_TEMPLATES" \
  --variant typical \
  --frame 105
MOTION_RENDER_CODE=$?
[ "$MOTION_RENDER_CODE" -eq 0 ] || fail "Motion frame render failed with exit $MOTION_RENDER_CODE"

log "Asserting hold motion (> 0.1% pixels differ between frame 60 and 105)..."
uv run python -c "
import sys
from pathlib import Path
import numpy as np
from PIL import Image

f60_dir = Path('$OUT_DIR')
f105_dir = Path('$MOTION_DIR')

templates = [t.strip() for t in '$MOTION_TEMPLATES'.split(',') if t.strip()]

errors = []
for tmpl in templates:
    f60_file = f60_dir / f'{tmpl}__typical.png'
    f105_file = f105_dir / f'{tmpl}__typical.png'

    if not f60_file.is_file() or not f105_file.is_file():
        errors.append(f'Missing files for motion check on {tmpl}')
        continue

    img60 = np.array(Image.open(f60_file))
    img105 = np.array(Image.open(f105_file))

    diff = np.abs(img60.astype(int) - img105.astype(int))
    diff_pixels = np.any(diff > 16, axis=-1)
    pct = (np.count_nonzero(diff_pixels) / diff_pixels.size) * 100.0

    if pct <= 0.1:
        errors.append(f'{tmpl} hold motion diff {pct:.3f}% is <= 0.1% (FROZEN)')
    else:
        print(f'[+] {tmpl} hold motion diff: {pct:.3f}% > 0.1% (PASS)')

if errors:
    print('[-] Hold motion failures:\n' + '\n'.join(errors), file=sys.stderr)
    sys.exit(1)
"
MOTION_CODE=$?
[ "$MOTION_CODE" -eq 0 ] || fail "Hold motion check failed"

# (d) Caption spacing check: runs of empty columns >= 16 in caption band
log "Running caption spacing check on captions__long_active..."
uv run pytest tests/test_caption_spacing.py -k test_caption_spacing_long_active
SPACING_CODE=$?
[ "$SPACING_CODE" -eq 0 ] || fail "Caption spacing check failed"

log "G10 Gallery gate passed: all goldens matched, 0 overflows, hold motion verified, caption spacing verified."
exit 0

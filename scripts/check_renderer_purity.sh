#!/usr/bin/env bash
set -euo pipefail

# scripts/check_renderer_purity.sh (Gate G9)
# Asserts that no Remotion time hooks, sequences, non-deterministic calls,
# or network requests exist in renderer/src/ outside src/clock/remotion/.

matches=$(grep -rnF \
  --exclude-dir="remotion" \
  --include="*.ts" \
  --include="*.tsx" \
  -e "useCurrentFrame" \
  -e "useVideoConfig" \
  -e "<Sequence" \
  -e "<Series" \
  -e "Math.random" \
  -e "Date.now" \
  -e "new Date(" \
  -e "performance.now" \
  -e "fetch(" \
  -e "http://" \
  -e "https://" \
  renderer/src/ || true)

if [ -n "$matches" ]; then
  echo "ERROR: Forbidden impure pattern found in renderer/src/ outside src/clock/remotion/:" >&2
  echo "$matches" >&2
  exit 1
fi

echo "Renderer purity check passed (all files pure)."
exit 0

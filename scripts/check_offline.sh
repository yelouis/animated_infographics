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

# scripts/check_offline.sh: G13 Offline gate per design_testing_and_validation.md §6.

fail() {
  echo "[-] FAILED: $1" >&2
  exit 1
}

log() {
  echo "[+] $1"
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || fail "Cannot cd to repo root"

SB_PROFILE="$REPO_ROOT/scripts/offline.sb"
[ -f "$SB_PROFILE" ] || fail "Missing sandbox profile: $SB_PROFILE"

# Self-check 1: External network must fail inside sandbox
log "Self-check 1: Testing external network denial..."
sandbox-exec -f "$SB_PROFILE" curl -sS -m 5 https://example.com > /dev/null 2>&1
CODE=$?
if [ "$CODE" -eq 0 ]; then
  fail "Self-check failed: external network succeeded inside sandbox (expected denial)"
fi
log "Self-check 1 passed (external network was denied, exit $CODE)."

# Self-check 2: Localhost Ollama must succeed inside sandbox
log "Self-check 2: Testing localhost Ollama access..."
sandbox-exec -f "$SB_PROFILE" curl -sS -m 5 http://127.0.0.1:11434/api/tags > /dev/null 2>&1
CODE=$?
if [ "$CODE" -ne 0 ]; then
  fail "Self-check failed: localhost Ollama unreachable inside sandbox (exit $CODE)"
fi
log "Self-check 2 passed (localhost Ollama accessible)."

# Run offline pipeline test with fresh cache and fresh jobs dir
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OFFLINE_DIR="$REPO_ROOT/artifacts/offline/$TIMESTAMP"
CACHE_DIR="$OFFLINE_DIR/cache"
JOBS_DIR="$OFFLINE_DIR/jobs"
mkdir -p "$CACHE_DIR" "$JOBS_DIR"

log "Running pipeline inside sandbox with fresh cache and HF_HUB_OFFLINE=1..."

# Step A: new
log "Running infographics new inside sandbox..."
sandbox-exec -f "$SB_PROFILE" env HF_HUB_OFFLINE=1 INFOGRAPHICS_CACHE_DIR="$CACHE_DIR" \
  uv run infographics new fixtures/scripts/molasses_flood.txt \
  --music fixtures/music/test_bed.wav \
  --sfx-dir fixtures/sfx \
  --jobs-dir "$JOBS_DIR"
CODE=$?
[ "$CODE" -eq 0 ] || fail "infographics new failed inside sandbox with exit $CODE"

JOB_DIR=$(find "$JOBS_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)
[ -n "$JOB_DIR" ] || fail "No job directory created in $JOBS_DIR"
JOB_ID=$(basename "$JOB_DIR")
log "Job ID: $JOB_ID"

# Step B: approve
log "Running infographics approve inside sandbox..."
sandbox-exec -f "$SB_PROFILE" env HF_HUB_OFFLINE=1 INFOGRAPHICS_CACHE_DIR="$CACHE_DIR" \
  uv run infographics approve "$JOB_ID" --jobs-dir "$JOBS_DIR"
CODE=$?
[ "$CODE" -eq 0 ] || fail "infographics approve failed inside sandbox with exit $CODE"

# Step C: render
log "Running infographics render inside sandbox..."
sandbox-exec -f "$SB_PROFILE" env HF_HUB_OFFLINE=1 INFOGRAPHICS_CACHE_DIR="$CACHE_DIR" \
  uv run infographics render "$JOB_ID" --jobs-dir "$JOBS_DIR"
CODE=$?
[ "$CODE" -eq 0 ] || fail "infographics render failed inside sandbox with exit $CODE"

[ -s "$JOB_DIR/out/final.mp4" ] || fail "out/final.mp4 missing or empty"
[ -f "$JOB_DIR/out/verify.json" ] || fail "out/verify.json missing"

log "G13 Offline check passed: full pipeline ran with network blocked, verified final.mp4 produced."
exit 0

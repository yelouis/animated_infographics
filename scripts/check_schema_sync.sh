#!/usr/bin/env bash
# Gate G8: Ensure schemas, generated TypeScript types, registries, and geo data match Python models.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

FILES_TO_CHECK=(
  "schema/voice.schema.json"
  "schema/transcript.schema.json"
  "schema/bible.schema.json"
  "schema/beats.schema.json"
  "schema/storyboard.schema.json"
  "schema/timeline.schema.json"
  "schema/styles.schema.json"
  "schema/director.schema.json"
  "schema/deck.schema.json"
  "schema/tree.schema.json"
  "schema/performance.schema.json"
  "schema/playback.schema.json"
  "renderer/src/generated/contracts.ts"
  "renderer/src/generated/styles.ts"
  "renderer/src/generated/director.ts"
  "renderer/src/generated/deck.ts"
  "renderer/src/generated/tree.ts"
  "renderer/src/generated/performance.ts"
  "renderer/src/generated/playback.ts"
  "renderer/src/generated/templateRegistry.json"
  "renderer/src/generated/iconNames.json"
  "renderer/src/generated/iconMap.ts"
  "renderer/src/generated/countryCodes.ts"
  "data/geo/country_bboxes.json"
  "renderer/public/geo/lakes-50m.json"
)

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

# 1. Regenerate contracts and schemas into temp dir
uv run python -m animated_infographics.contracts.export --out "$TMP_DIR" > /dev/null

# 2. Regenerate country bboxes and country codes into temp dir
mkdir -p "$TMP_DIR/data/geo" "$TMP_DIR/renderer/src/generated"
npx --prefix renderer tsx renderer/scripts/gen-country-bboxes.ts \
  "$TMP_DIR/data/geo/country_bboxes.json" \
  "$TMP_DIR/renderer/src/generated/countryCodes.ts" > /dev/null

# 3. Regenerate lakes into temp dir
mkdir -p "$TMP_DIR/renderer/public/geo"
npx --prefix renderer tsx renderer/scripts/gen-lakes.ts "$TMP_DIR/renderer/public/geo/lakes-50m.json" > /dev/null

# 4. Check for existence, non-emptiness, and identity on each file
for file in "${FILES_TO_CHECK[@]}"; do
  # Check committed file exists and is not empty
  if [ ! -f "$REPO_ROOT/$file" ]; then
    echo "ERROR: Committed file missing: $file" >&2
    exit 1
  fi
  if [ ! -s "$REPO_ROOT/$file" ]; then
    echo "ERROR: Committed file is empty: $file" >&2
    exit 1
  fi

  # Check generated file exists and is not empty
  if [ ! -f "$TMP_DIR/$file" ]; then
    echo "ERROR: Generated file missing: $file" >&2
    exit 1
  fi
  if [ ! -s "$TMP_DIR/$file" ]; then
    echo "ERROR: Generated file is empty: $file" >&2
    exit 1
  fi

  # Diff committed against generated
  if ! diff -u "$REPO_ROOT/$file" "$TMP_DIR/$file"; then
    echo "ERROR: File differs from generated output: $file" >&2
    exit 1
  fi
done

echo "G8: Schema and contracts sync check passed (${#FILES_TO_CHECK[@]} files verified)."
exit 0

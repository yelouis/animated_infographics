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

FAST=0
if [ "${1:-}" = "--fast" ]; then
  FAST=1
fi

if [ -z "${HF_HOME:-}" ] || [ ! -d "${HF_HOME}/hub/models--hexgrad--Kokoro-82M" ] || [ ! -d "${HF_HOME}/hub/models--black-forest-labs--FLUX.2-klein-4B" ]; then
  if [ -d "$HOME/.cache/huggingface/hub/models--hexgrad--Kokoro-82M" ]; then
    export HF_HOME="$HOME/.cache/huggingface"
  fi
fi

mkdir -p artifacts/battery

failed=0

run_gate() {
  local gate="$1"
  local cmd="$2"
  local item="$3"
  local check_type="$4"
  local check_path="$5"

  local is_built=0
  case "$check_type" in
    always)
      is_built=1
      ;;
    file)
      if [ -f "$check_path" ]; then
        is_built=1
      fi
      ;;
    glob)
      if compgen -G "$check_path" > /dev/null 2>&1; then
        is_built=1
      fi
      ;;
  esac

  if [ "$is_built" -eq 0 ]; then
    printf "%-4s | %-4s | NOT BUILT (%s)\n" "$gate" "-" "$item"
    return 0
  fi

  if [ "$FAST" -eq 1 ]; then
    case "$gate" in
      G11|G12|G13|G15|G16)
        printf "%-4s | %-4s | SKIPPED (--fast)\n" "$gate" "-"
        return 0
        ;;
    esac
  fi

  if [ "$gate" = "G16" ] && [ -n "${PRESENTATION_REUSE_JOBS:-}" ]; then
    printf "%-4s | %-4s | REFUSED (PRESENTATION_REUSE_JOBS set)\n" "$gate" "1"
    failed=1
    return 0
  fi

  local log_file="artifacts/battery/${gate}.log"
  eval "$cmd" > "$log_file" 2>&1
  local code=$?

  if [ "$code" -ne 0 ]; then
    failed=1
  fi

  local key_num="exit $code"
  case "$gate" in
    G1)
      local match
      match=$(grep -o "[0-9]\+ error" "$log_file" 2>/dev/null || grep -o "All checks passed" "$log_file" 2>/dev/null || true)
      [ -n "$match" ] && key_num="$match"
      ;;
    G2)
      local match
      match=$(grep -o "[0-9]\+ files\? [^.]*" "$log_file" 2>/dev/null || true)
      [ -n "$match" ] && key_num="$match"
      ;;
    G3)
      local match
      match=$(grep -o "Success: no issues found in [0-9]\+ source files" "$log_file" 2>/dev/null || grep -o "Found [0-9]\+ error[s]\?" "$log_file" 2>/dev/null || true)
      [ -n "$match" ] && key_num="$match"
      ;;
    G4|G11)
      local match
      match=$(grep -o "[0-9]\+ passed" "$log_file" 2>/dev/null | tail -n 1 || true)
      [ -n "$match" ] && key_num="$match"
      ;;
    G5|G6)
      if [ "$code" -eq 0 ]; then
        key_num="0 errors"
      fi
      ;;
    G7)
      local match
      match=$(grep -o "[0-9]\+ passed" "$log_file" 2>/dev/null | tail -n 1 || true)
      [ -n "$match" ] && key_num="$match"
      ;;
    G8)
      if [ "$code" -eq 0 ]; then
        key_num="in sync"
      fi
      ;;
    G9)
      if [ "$code" -eq 0 ]; then
        key_num="pure"
      fi
      ;;
    G10)
      local match
      match=$(grep -o "[0-9]\+ overflows" "$log_file" 2>/dev/null | tail -n 1 || true)
      [ -n "$match" ] && key_num="$match"
      ;;
    G12|G13|G15)
      if [ "$code" -eq 0 ]; then
        key_num="passed"
      fi
      ;;
    G16)
      if [ "$code" -eq 0 ]; then
        key_num="passed"
      fi
      ;;
    G14)
      if [ "$code" -eq 0 ]; then
        key_num="ok"
      fi
      ;;
  esac

  printf "%-4s | %-4s | %s\n" "$gate" "$code" "$key_num"
}

run_gate "G1"  "uv run ruff check ."                   "A1"  "always" ""
run_gate "G2"  "uv run ruff format --check ."          "A1"  "always" ""
run_gate "G3"  "uv run mypy src"                       "A1"  "always" ""
run_gate "G4"  "uv run pytest -q -m \"not slow\""      "A1"  "always" ""
run_gate "G5"  "npm --prefix renderer run typecheck"   "A1"  "always" ""
run_gate "G6"  "npm --prefix renderer run lint"        "A1"  "always" ""
run_gate "G7"  "npm --prefix renderer test"            "A1"  "always" ""
run_gate "G8"  "./scripts/check_schema_sync.sh"        "A4"  "file"   "./scripts/check_schema_sync.sh"
run_gate "G9"  "./scripts/check_renderer_purity.sh"    "A11" "file"   "./scripts/check_renderer_purity.sh"
run_gate "G10" "./scripts/check_gallery.sh"            "A17" "file"   "./scripts/check_gallery.sh"
run_gate "G11" "uv run pytest -q -m slow"              "A7"  "glob"   "tests/slow/*.py"
run_gate "G12" "./scripts/e2e.sh"                      "A16" "file"   "./scripts/e2e.sh"
run_gate "G13" "./scripts/check_offline.sh"            "A22" "file"   "./scripts/check_offline.sh"
run_gate "G14" "uv run infographics doctor"            "A2"  "file"   "src/animated_infographics/doctor.py"
run_gate "G15" "./scripts/creative_e2e.sh"             "G6"  "file"   "./scripts/creative_e2e.sh"
run_gate "G16" "./scripts/presentation_sim.sh"         "H5"  "file"   "./scripts/presentation_sim.sh"

exit "$failed"

#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== 1. System packages ==="
if ! command -v espeak-ng >/dev/null 2>&1; then
  echo "Installing espeak-ng via brew..."
  brew install espeak-ng
else
  echo "espeak-ng already installed."
fi

echo "=== 2. Python environment ==="
uv sync

echo "=== 3. Renderer environment ==="
npm --prefix renderer ci

echo "=== 4. Ollama planner model ==="
if curl -s http://127.0.0.1:11434/api/tags | grep -q '"gemma4:26b"'; then
  echo "gemma4:26b already pulled."
else
  echo "Pulling gemma4:26b..."
  ollama pull gemma4:26b
fi

echo "=== 5. mflux tool ==="
if ! command -v mflux-generate-flux2 >/dev/null 2>&1; then
  echo "Installing mflux..."
  uv tool install mflux
fi

# Ensure mflux-generate-flux2-klein is available on PATH
if ! command -v mflux-generate-flux2-klein >/dev/null 2>&1; then
  FLUX2_BIN="$(command -v mflux-generate-flux2)"
  ln -sf "$FLUX2_BIN" "$HOME/.local/bin/mflux-generate-flux2-klein"
fi

echo "=== 6. Pre-downloading HuggingFace models ==="
uv run python -c '
from huggingface_hub import snapshot_download, try_to_load_from_cache

# Whisper model
if not try_to_load_from_cache("mlx-community/whisper-large-v3-turbo", "config.json"):
    print("Downloading mlx-community/whisper-large-v3-turbo...")
    snapshot_download("mlx-community/whisper-large-v3-turbo")
else:
    print("Whisper model already cached.")

# Kokoro model & voices
if not (try_to_load_from_cache("hexgrad/Kokoro-82M", "voices/af_heart.pt") and
        try_to_load_from_cache("hexgrad/Kokoro-82M", "voices/am_michael.pt")):
    print("Downloading hexgrad/Kokoro-82M...")
    snapshot_download("hexgrad/Kokoro-82M")
else:
    print("Kokoro model & voices already cached.")
'

# FLUX.2 klein 4B weights
uv run python -c '
from huggingface_hub import scan_cache_dir
import subprocess, os

cached = False
try:
    scan = scan_cache_dir()
    for repo in scan.repos:
        if repo.repo_id == "black-forest-labs/FLUX.2-klein-4B":
            cached = True
            break
except Exception:
    pass

if not cached:
    print("Generating warmup image to fetch FLUX.2 klein 4B weights...")
    cmd = [
        "mflux-generate-flux2",
        "--model", "flux2-klein-4b",
        "--prompt", "warmup",
        "--width", "256",
        "--height", "256",
        "--steps", "1",
        "--output", "/tmp/flux2_setup_warmup.png"
    ]
    subprocess.run(cmd, check=True)
    if os.path.exists("/tmp/flux2_setup_warmup.png"):
        os.remove("/tmp/flux2_setup_warmup.png")
else:
    print("FLUX.2 klein 4B weights already cached.")
'

echo "=== 7. Remotion headless browser ==="
npx --prefix renderer remotion browser ensure

echo "=== 8. Fonts ==="
FONTS_DIR="renderer/public/fonts"
mkdir -p "$FONTS_DIR"

if [ ! -f "$FONTS_DIR/Poppins-Bold.ttf" ] || [ ! -f "$FONTS_DIR/Poppins-ExtraBold.ttf" ] || [ ! -f "$FONTS_DIR/OFL.txt" ]; then
  echo "Downloading Poppins fonts..."
  curl -sSL https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-Bold.ttf -o "$FONTS_DIR/Poppins-Bold.ttf"
  curl -sSL https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-ExtraBold.ttf -o "$FONTS_DIR/Poppins-ExtraBold.ttf"
  curl -sSL https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/OFL.txt -o "$FONTS_DIR/OFL.txt"
fi

if [ ! -f "$FONTS_DIR/Inter-Medium.ttf" ] || [ ! -f "$FONTS_DIR/Inter-SemiBold.ttf" ] || [ ! -f "$FONTS_DIR/Inter-Bold.ttf" ]; then
  echo "Downloading Inter fonts..."
  gh release download v4.1 --repo rsms/inter --pattern "Inter-*.zip" --dir /tmp
  unzip -jo /tmp/Inter-4.1.zip "extras/ttf/Inter-Medium.ttf" "extras/ttf/Inter-SemiBold.ttf" "extras/ttf/Inter-Bold.ttf" "LICENSE.txt" -d "$FONTS_DIR/"
  mv "$FONTS_DIR/LICENSE.txt" "$FONTS_DIR/Inter-LICENSE.txt"
  rm -f /tmp/Inter-4.1.zip
fi

echo "=== 9. GeoNames vendor data ==="
VENDOR_DIR="data/vendor"
mkdir -p "$VENDOR_DIR"

if [ ! -f "$VENDOR_DIR/cities15000.txt" ]; then
  echo "Downloading cities15000..."
  curl -sSL https://download.geonames.org/export/dump/cities15000.zip -o "$VENDOR_DIR/cities15000.zip"
  unzip -o "$VENDOR_DIR/cities15000.zip" -d "$VENDOR_DIR/"
  rm -f "$VENDOR_DIR/cities15000.zip"
fi

if [ ! -f "$VENDOR_DIR/countryInfo.txt" ]; then
  echo "Downloading countryInfo.txt..."
  curl -sSL https://download.geonames.org/export/dump/countryInfo.txt -o "$VENDOR_DIR/countryInfo.txt"
fi

echo "Verifying data/vendor/CHECKSUMS..."
(cd "$VENDOR_DIR" && shasum -a 256 -c CHECKSUMS)

echo "=== 10. Generate country bboxes ==="
npx --prefix renderer tsx renderer/scripts/gen-country-bboxes.ts

echo "=== Setup complete ==="

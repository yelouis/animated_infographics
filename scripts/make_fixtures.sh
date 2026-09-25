#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

mkdir -p fixtures/audio fixtures/music fixtures/sfx fixtures/expected

echo "=== 1. Generate audio: molasses_flood_say.m4a ==="
TMP_AIFF="$(mktemp /tmp/molasses_say.XXXXXX.aiff)"
say -v Samantha -f fixtures/scripts/molasses_flood.txt -o "$TMP_AIFF"
ffmpeg -y -v error -i "$TMP_AIFF" -c:a aac -b:a 128k -ac 1 fixtures/audio/molasses_flood_say.m4a
rm -f "$TMP_AIFF"

echo "=== 2. Generate music: test_bed.wav ==="
# 20 s, 220 Hz + 330 Hz sines, -20 dBFS peak, 48 kHz stereo s16
ffmpeg -y -v error -f lavfi \
  -i "aevalsrc=0.074*sin(2*PI*220*t)+0.074*sin(2*PI*330*t):s=48000:d=20" \
  -ac 2 -c:a pcm_s16le fixtures/music/test_bed.wav

echo "=== 3. Generate SFX ==="
# whoosh: 0.4 s pink-noise swell
ffmpeg -y -v error -f lavfi \
  -i "anoisesrc=color=pink:sample_rate=48000:duration=0.4,afade=t=in:ss=0:d=0.2,afade=t=out:st=0.2:d=0.2,volume=0.5" \
  -ac 2 -c:a pcm_s16le fixtures/sfx/whoosh_test.wav

# pop: 0.08 s 880 Hz sine
ffmpeg -y -v error -f lavfi \
  -i "sine=frequency=880:sample_rate=48000:duration=0.08,afade=t=out:st=0.05:d=0.03,volume=0.8" \
  -ac 2 -c:a pcm_s16le fixtures/sfx/pop_test.wav

# ding: 0.6 s 1320 Hz decaying sine
ffmpeg -y -v error -f lavfi \
  -i "sine=frequency=1320:sample_rate=48000:duration=0.6,afade=t=out:st=0:d=0.6,volume=0.8" \
  -ac 2 -c:a pcm_s16le fixtures/sfx/ding_test.wav

# hit: 0.3 s 80 Hz sine
ffmpeg -y -v error -f lavfi \
  -i "sine=frequency=80:sample_rate=48000:duration=0.3,afade=t=out:st=0:d=0.3,volume=0.9" \
  -ac 2 -c:a pcm_s16le fixtures/sfx/hit_test.wav

# clap: unknown role, 0.2 s pink noise
ffmpeg -y -v error -f lavfi \
  -i "anoisesrc=color=pink:sample_rate=48000:duration=0.2,afade=t=out:st=0:d=0.2,volume=0.5" \
  -ac 2 -c:a pcm_s16le fixtures/sfx/clap_test.wav

echo "=== 4. Compute fixtures/CHECKSUMS ==="
(
  cd fixtures
  shasum -a 256 \
    scripts/*.txt \
    audio/*.m4a \
    music/*.wav \
    sfx/*.wav \
    expected/*.json \
    > CHECKSUMS
)

echo "Fixtures generated and checksummed successfully."

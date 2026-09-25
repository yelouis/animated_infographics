"""Slow integration tests for Kokoro narration across all four fixtures."""

import json
import subprocess
import time
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from kokoro import KPipeline

from animated_infographics.audio.loudness import measure_loudness
from animated_infographics.audio.narrate import build_sentence_list, narrate
from animated_infographics.config import (
    PAUSE_AFTER_TITLE_MS,
    PAUSE_BETWEEN_PARAGRAPHS_MS,
    PAUSE_BETWEEN_SENTENCES_MS,
    TAIL_SILENCE_MS,
)
from animated_infographics.ingest import ingest
from animated_infographics.planner.llm import OllamaBackend
from animated_infographics.planner.voice import select_voice

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "scripts"
FIXTURE_NAMES = ("story_recipe_box", "story_room_12", "molasses_flood", "emu_war")


def compute_spectral_centroid(audio: np.ndarray, sample_rate: int = 24000) -> float:
    """Compute median spectral centroid over 2048-sample frames with RMS > -40 dBFS."""
    frame_len = 2048
    hop = 1024
    centroids: list[float] = []
    freqs = np.fft.rfftfreq(frame_len, d=1.0 / sample_rate)

    for i in range(0, len(audio) - frame_len, hop):
        frame = audio[i : i + frame_len]
        rms = np.sqrt(np.mean(frame**2))
        rms_db = 20.0 * np.log10(max(rms, 1e-12))
        if rms_db > -40.0:
            spec = np.abs(np.fft.rfft(frame))
            sum_spec = np.sum(spec)
            if sum_spec > 1e-12:
                centroids.append(float(np.sum(freqs * spec) / sum_spec))

    if not centroids:
        return 0.0
    return float(np.median(centroids))


@pytest.mark.slow
def test_voice_parameter_reaches_kokoro_spectral_centroid() -> None:
    """Synthesize first sentence of molasses_flood with each voice.

    Verify arrays differ and af_heart has higher median spectral centroid.
    """
    ingest_record = ingest(FIXTURES_DIR / "molasses_flood.txt", None)
    sentence = ingest_record.title or "The Great Molasses Flood"
    pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M", device="cpu")

    gen_heart = pipeline(sentence, voice="af_heart", speed=1.0)
    audio_heart = np.concatenate([r.audio.numpy() for r in gen_heart])

    gen_michael = pipeline(sentence, voice="am_michael", speed=1.0)
    audio_michael = np.concatenate([r.audio.numpy() for r in gen_michael])

    assert not np.array_equal(audio_heart, audio_michael), "Voice outputs must not be identical"

    centroid_heart = compute_spectral_centroid(audio_heart)
    centroid_michael = compute_spectral_centroid(audio_michael)

    print(f"\naf_heart centroid: {centroid_heart:.2f} Hz")
    print(f"am_michael centroid: {centroid_michael:.2f} Hz")

    assert centroid_heart > centroid_michael, (
        f"Expected af_heart ({centroid_heart:.2f}) > am_michael ({centroid_michael:.2f})"
    )


@pytest.mark.slow
@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_narrate_fixture(name: str, tmp_path: Path) -> None:
    """Validate narration stage across each fixture."""
    fixture_path = FIXTURES_DIR / f"{name}.txt"
    ingest_record = ingest(fixture_path, title_override=None)

    # Determine voice using select_voice
    backend = OllamaBackend(no_cache=True)
    body = "\n\n".join(ingest_record.paragraphs or [])
    voice_decision = select_voice(
        title=ingest_record.title,
        body=body,
        flag_voice=None,
        backend=backend,
    )

    out_dir = tmp_path / name
    t0 = time.perf_counter()
    transcript, narration = narrate(ingest_record, voice_decision, out_dir)
    wall_time = time.perf_counter() - t0

    # 1. Voice check
    expected_voice = "af_heart" if name == "story_recipe_box" else "am_michael"
    assert narration.voice == expected_voice, (
        f"{name}: expected voice {expected_voice}, got {narration.voice}"
    )
    assert narration.voice == voice_decision.voice

    # 2. Timing budget on emu_war
    if name == "emu_war":
        dur = transcript.duration_ms
        print(f"\nemu_war narrate wall time: {wall_time:.2f}s, duration: {dur}ms")
        assert wall_time <= 60.0, f"emu_war narration wall time {wall_time:.2f}s exceeded 60s bar"

    # 3. Transcript contract invariants
    assert transcript.schema_version == 1
    assert transcript.source == "tts"
    assert transcript.duration_ms >= transcript.words[-1].end_ms

    for idx, w in enumerate(transcript.words):
        assert w.i == idx
        assert w.end_ms > w.start_ms, f"Word {idx} end <= start"
        if idx > 0:
            assert w.start_ms >= transcript.words[idx - 1].end_ms, f"Word {idx} start < prev end"

    title_sents = [s for s in transcript.sentences if s.is_title]
    if title_sents:
        assert len(title_sents) == 1
        assert title_sents[0].i == 0

    assert transcript.sentences[0].word_start == 0
    for idx, s in enumerate(transcript.sentences):
        assert s.i == idx
        if idx > 0:
            assert s.word_start == transcript.sentences[idx - 1].word_end
        for w_idx in range(s.word_start, s.word_end):
            assert transcript.words[w_idx].sentence_i == s.i
    assert transcript.sentences[-1].word_end == len(transcript.words)

    # 4. Exact sample offset accounting on raw 24k audio
    raw_wav_path = out_dir / "audio" / "narration_24k_raw.wav"
    raw_data, sample_rate = sf.read(str(raw_wav_path))
    assert sample_rate == 24000
    total_raw_samples = len(raw_data)

    specs = build_sentence_list(ingest_record)
    total_calc_samples = 0
    for idx, offset in enumerate(narration.sentences):
        sent_samples = (offset.end_ms - offset.start_ms) * 24
        total_calc_samples += sent_samples

        if idx == len(narration.sentences) - 1:
            pause_ms = TAIL_SILENCE_MS
        elif specs[idx][2]:  # is_title
            pause_ms = PAUSE_AFTER_TITLE_MS
        elif specs[idx + 1][1] != specs[idx][1]:
            pause_ms = PAUSE_BETWEEN_PARAGRAPHS_MS
        else:
            pause_ms = PAUSE_BETWEEN_SENTENCES_MS

        total_calc_samples += pause_ms * 24

    assert total_calc_samples == total_raw_samples, (
        f"{name}: exact offset sum {total_calc_samples} != "
        f"raw wav samples {total_raw_samples} (diff={total_calc_samples - total_raw_samples})"
    )

    # 5. Loudness and audio format of final narration.wav
    final_wav_path = out_dir / "audio" / "narration.wav"
    report = measure_loudness(final_wav_path)
    assert abs(report.integrated_lufs - (-16.0)) <= 0.5, (
        f"{name}: integrated LUFS {report.integrated_lufs} not within -16 ± 0.5"
    )

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=codec_name,channels,sample_rate",
        "-of",
        "json",
        str(final_wav_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    info = json.loads(res.stdout)
    stream = info["streams"][0]
    assert stream["codec_name"] == "pcm_s16le", f"Expected pcm_s16le, got {stream['codec_name']}"
    assert int(stream["channels"]) == 1, f"Expected 1 channel, got {stream['channels']}"
    assert int(stream["sample_rate"]) == 48000, f"Expected 48000 sr, got {stream['sample_rate']}"

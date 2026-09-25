"""Slow integration tests for ASR transcription accuracy and timing using MLX-Whisper."""

import difflib
import re
import time
from pathlib import Path

import jiwer
import numpy as np
import pytest

from animated_infographics.audio.narrate import narrate
from animated_infographics.audio.transcribe import transcribe
from animated_infographics.contracts.models import VoiceDecision
from animated_infographics.ingest import ingest

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


def normalize_for_wer(text: str) -> str:
    """Normalize text for WER: lowercase and strip punctuation."""
    t = text.lower()
    return re.sub(r"[^\w\s]", "", t).strip()


def normalize_token(token: str) -> str:
    """Normalize single word token for alignment."""
    return re.sub(r"[^\w]", "", token.lower())


@pytest.mark.slow
def test_transcribe_wer_accuracy(tmp_path: Path) -> None:
    """Verify WER <= 8% on molasses_flood_say.m4a vs source text."""
    audio_path = FIXTURES_DIR / "audio" / "molasses_flood_say.m4a"
    source_path = FIXTURES_DIR / "scripts" / "molasses_flood.txt"

    transcript = transcribe(audio_path, tmp_path)
    ref_norm = normalize_for_wer(source_path.read_text(encoding="utf-8"))
    hyp_text = " ".join(w.text for w in transcript.words)
    hyp_norm = normalize_for_wer(hyp_text)

    wer = jiwer.wer(ref_norm, hyp_norm)
    print(f"\nmolasses_flood_say WER: {wer * 100:.2f}%")
    assert wer <= 0.08, f"WER {wer * 100:.2f}% exceeded 8% bar"


@pytest.mark.slow
def test_transcribe_timing_accuracy_vs_kokoro(tmp_path: Path) -> None:
    """Verify word-start error vs Kokoro: median <= 80 ms, p95 <= 250 ms."""
    source_path = FIXTURES_DIR / "scripts" / "molasses_flood.txt"
    ingest_record = ingest(source_path, title_override=None)
    voice_decision = VoiceDecision(
        voice="am_michael",
        source="auto",
        reason="third_person",
        perspective="third_person",
        first_person_rate=0.0,
        narrator_gender="unknown",
        evidence=None,
    )

    kokoro_dir = tmp_path / "kokoro"
    kokoro_transcript, _ = narrate(ingest_record, voice_decision, kokoro_dir)

    whisper_dir = tmp_path / "whisper"
    whisper_transcript = transcribe(kokoro_dir / "audio" / "narration.wav", whisper_dir)

    k_tokens = [normalize_token(w.text) for w in kokoro_transcript.words]
    w_tokens = [normalize_token(w.text) for w in whisper_transcript.words]

    matcher = difflib.SequenceMatcher(None, k_tokens, w_tokens)
    errors: list[int] = []

    for block in matcher.get_matching_blocks():
        k_start, w_start, size = block.a, block.b, block.size
        for i in range(size):
            kw = kokoro_transcript.words[k_start + i]
            ww = whisper_transcript.words[w_start + i]
            errors.append(abs(kw.start_ms - ww.start_ms))

    match_rate = len(errors) / float(len(kokoro_transcript.words))
    median_err = float(np.median(errors))
    p95_err = float(np.percentile(errors, 95))

    print(
        f"\nWhisper vs Kokoro timing on molasses_flood: "
        f"match_rate={match_rate * 100:.1f}%, "
        f"median_err={median_err:.1f}ms, p95_err={p95_err:.1f}ms"
    )

    assert match_rate >= 0.90, f"Match rate {match_rate * 100:.1f}% below 90%"
    assert median_err <= 80.0, f"Median start error {median_err:.1f}ms exceeded 80ms bar"
    assert p95_err <= 250.0, f"p95 start error {p95_err:.1f}ms exceeded 250ms bar"


@pytest.mark.slow
def test_transcribe_emu_war_time_budget(tmp_path: Path) -> None:
    """Verify transcription of emu_war narration completes within 45s."""
    source_path = FIXTURES_DIR / "scripts" / "emu_war.txt"
    ingest_record = ingest(source_path, title_override=None)
    voice_decision = VoiceDecision(
        voice="am_michael",
        source="auto",
        reason="third_person",
        perspective="third_person",
        first_person_rate=0.0,
        narrator_gender="unknown",
        evidence=None,
    )

    kokoro_dir = tmp_path / "kokoro"
    kokoro_transcript, _ = narrate(ingest_record, voice_decision, kokoro_dir)

    whisper_dir = tmp_path / "whisper"
    t0 = time.perf_counter()
    whisper_transcript = transcribe(kokoro_dir / "audio" / "narration.wav", whisper_dir)
    wall_time = time.perf_counter() - t0

    print(
        f"\nemu_war transcribe wall time: {wall_time:.2f}s, "
        f"duration: {whisper_transcript.duration_ms}ms"
    )
    assert wall_time <= 45.0, f"transcribe wall time {wall_time:.2f}s exceeded 45s bar"

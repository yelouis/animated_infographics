"""Audio transcription via MLX-Whisper with sentence and paragraph segmentation."""

import re
from pathlib import Path
from typing import Final

import mlx_whisper
import numpy as np
import soundfile as sf

from animated_infographics.audio.loudness import loudnorm_two_pass
from animated_infographics.audio.narrate import enforce_rule4_invariants, round_half_up
from animated_infographics.config import ASR_PARAGRAPH_GAP_MS
from animated_infographics.contracts.models import (
    Transcript,
    TranscriptSentence,
    TranscriptWord,
)

ABBREVIATIONS: Final[frozenset[str]] = frozenset(
    {
        "mr.",
        "mrs.",
        "ms.",
        "dr.",
        "st.",
        "vs.",
        "jr.",
        "sr.",
        "u.s.",
        "u.k.",
        "e.g.",
        "i.e.",
        "etc.",
        "no.",
    }
)

SENTENCE_END_RE: Final[re.Pattern[str]] = re.compile(r"[\.\?\!]['\"”’)]*$")
TRAILING_PUNCT_RE: Final[re.Pattern[str]] = re.compile(r"['\"”’)]+$")


def is_sentence_boundary(word_text: str) -> bool:
    """Determine if a word ends a sentence according to ASR punctuation rules."""
    if not SENTENCE_END_RE.search(word_text):
        return False

    clean_word = TRAILING_PUNCT_RE.sub("", word_text).casefold()
    if clean_word in ABBREVIATIONS:
        return False

    return True


def refine_word_start_with_audio_onset(
    start_ms: int,
    end_ms: int,
    audio: np.ndarray,
    sr: int,
) -> int:
    """Trim leading silence from a word if its duration exceeds 300 ms."""
    if end_ms - start_ms <= 300:
        return start_ms

    start_samp = int(start_ms * sr / 1000)
    end_samp = int(end_ms * sr / 1000)
    chunk = audio[start_samp:end_samp]
    if len(chunk) == 0:
        return start_ms

    frame_len = int(0.02 * sr)
    hop = int(0.01 * sr)
    if len(chunk) <= frame_len:
        return start_ms

    rms_vals: list[tuple[int, float]] = []
    for f in range(0, len(chunk) - frame_len, hop):
        rms_vals.append((f, float(np.sqrt(np.mean(chunk[f : f + frame_len] ** 2)))))

    if not rms_vals:
        return start_ms

    max_rms = max(r[1] for r in rms_vals)
    if max_rms < 0.005:
        return start_ms

    thresh = max(0.005, max_rms * 0.1)
    for f, r in rms_vals:
        if r >= thresh:
            onset_ms = start_ms + int(f * 1000 / sr)
            return min(onset_ms, end_ms - 40)

    return start_ms


def segment_asr_words(
    raw_words: list[tuple[str, int, int]],
) -> tuple[list[TranscriptWord], list[TranscriptSentence]]:
    """Segment raw word tuples into TranscriptWord and TranscriptSentence models.

    Sentence boundaries are determined by punctuation (unless in ABBREVIATIONS).
    Paragraph boundaries are determined by gaps >= ASR_PARAGRAPH_GAP_MS (1200 ms).
    """
    if not raw_words:
        return [], []

    all_words: list[TranscriptWord] = []
    sentences: list[TranscriptSentence] = []

    current_sentence_words: list[tuple[str, int, int]] = []
    sentence_idx = 0
    paragraph_idx = 0
    word_counter = 0

    num_words = len(raw_words)

    for i in range(num_words):
        w_text, w_start, w_end = raw_words[i]
        current_sentence_words.append((w_text, w_start, w_end))

        # Check for paragraph gap to the next word
        is_last_word = i == num_words - 1
        has_paragraph_gap = False
        if not is_last_word:
            next_start = raw_words[i + 1][1]
            if next_start - w_end >= ASR_PARAGRAPH_GAP_MS:
                has_paragraph_gap = True

        is_sent_end = is_sentence_boundary(w_text)

        if is_sent_end or has_paragraph_gap or is_last_word:
            sent_word_start = word_counter
            sent_word_end = word_counter + len(current_sentence_words)

            for w_idx_in_sent, (t, s_ms, e_ms) in enumerate(current_sentence_words):
                all_words.append(
                    TranscriptWord(
                        i=sent_word_start + w_idx_in_sent,
                        text=t,
                        start_ms=s_ms,
                        end_ms=e_ms,
                        sentence_i=sentence_idx,
                    )
                )

            sent_text = " ".join(w[0] for w in current_sentence_words)
            sentences.append(
                TranscriptSentence(
                    i=sentence_idx,
                    text=sent_text,
                    start_ms=current_sentence_words[0][1],
                    end_ms=current_sentence_words[-1][2],
                    word_start=sent_word_start,
                    word_end=sent_word_end,
                    paragraph_i=paragraph_idx,
                    is_title=False,
                )
            )

            word_counter = sent_word_end
            current_sentence_words = []
            sentence_idx += 1

            if has_paragraph_gap:
                paragraph_idx += 1

    repaired_words = enforce_rule4_invariants(all_words)

    repaired_sentences: list[TranscriptSentence] = []
    for s in sentences:
        if s.word_start < len(repaired_words):
            repaired_sentences.append(
                s.model_copy(
                    update={
                        "start_ms": repaired_words[s.word_start].start_ms,
                        "end_ms": repaired_words[s.word_end - 1].end_ms,
                    }
                )
            )
        else:
            repaired_sentences.append(s)

    return repaired_words, repaired_sentences


def transcribe(audio_path: Path, out_dir: Path) -> Transcript:
    """Transcribe an audio file using MLX-Whisper and produce a validated Transcript."""
    audio_dir = out_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    narration_wav = audio_dir / "narration.wav"

    # Step 1: Normalize audio to 48kHz mono s16 at -16 LUFS if not already there
    if audio_path.resolve() != narration_wav.resolve():
        loudnorm_two_pass(
            audio_path,
            narration_wav,
            target_lufs=-16.0,
            true_peak=-1.5,
            lra=11.0,
            sample_rate=48000,
            channels=1,
        )

    # Step 2: Transcribe normalized audio with mlx_whisper
    res = mlx_whisper.transcribe(
        str(narration_wav),
        path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
        word_timestamps=True,
        language="en",
        temperature=0.0,
        condition_on_previous_text=False,
    )

    audio_data, sr = sf.read(str(narration_wav))
    if audio_data.ndim > 1:
        audio_data = audio_data.mean(axis=1)

    # Step 3: Extract words from segments and refine onset across silence
    raw_words: list[tuple[str, int, int]] = []
    segments = res.get("segments", [])
    for seg in segments:
        seg_words = seg.get("words", [])
        for w in seg_words:
            w_text = w.get("word", "").lstrip()
            if not w_text:
                continue
            s_ms = round_half_up(float(w["start"]) * 1000.0)
            e_ms = round_half_up(float(w["end"]) * 1000.0)
            if e_ms <= s_ms:
                e_ms = s_ms + 40
            s_ms = refine_word_start_with_audio_onset(s_ms, e_ms, audio_data, sr)
            raw_words.append((w_text, s_ms, e_ms))

    # Step 4: Segment into words and sentences
    words, sentences = segment_asr_words(raw_words)

    # Audio duration
    wav_info = sf.info(str(narration_wav))
    audio_dur_ms = round_half_up(wav_info.duration * 1000.0)
    duration_ms = max(audio_dur_ms, words[-1].end_ms if words else 0)

    return Transcript(
        schema_version=1,
        source="asr",
        audio_path="audio/narration.wav",
        duration_ms=duration_ms,
        words=words,
        sentences=sentences,
    )

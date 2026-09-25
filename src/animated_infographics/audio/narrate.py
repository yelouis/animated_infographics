"""Narration synthesis via Kokoro TTS with exact sample accounting and word timings."""

import math
from pathlib import Path
from typing import Any

import numpy as np
import pysbd
import soundfile as sf
from kokoro import KPipeline

from animated_infographics.audio.loudness import loudnorm_two_pass
from animated_infographics.config import (
    PAUSE_AFTER_TITLE_MS,
    PAUSE_BETWEEN_PARAGRAPHS_MS,
    PAUSE_BETWEEN_SENTENCES_MS,
    TAIL_SILENCE_MS,
)
from animated_infographics.contracts.models import (
    IngestRecord,
    NarrationOffsets,
    SentenceOffset,
    Transcript,
    TranscriptSentence,
    TranscriptWord,
    VoiceDecision,
)

KOKORO_SAMPLE_RATE = 24000
OPENING_PUNCTUATION = frozenset({'"', "'", "“", "‘", "(", "[", "{", "$", "£", "€"})


def round_half_up(x: float) -> int:
    """Round-half-up: never use banker's round."""
    return math.floor(x + 0.5)


def build_sentence_list(ingest: IngestRecord) -> list[tuple[str, int, bool]]:
    """Build list of (sentence_text, paragraph_i, is_title) from ingest record."""
    sentences: list[tuple[str, int, bool]] = []
    segmenter = pysbd.Segmenter(language="en", clean=False)

    if ingest.title:
        sentences.append((ingest.title, 0, True))
        paragraph_offset = 1
    else:
        paragraph_offset = 0

    if ingest.paragraphs:
        for p_idx, paragraph in enumerate(ingest.paragraphs):
            raw_sents = segmenter.segment(paragraph)
            for s in raw_sents:
                cleaned = s.strip()
                if cleaned:
                    sentences.append((cleaned, p_idx + paragraph_offset, False))

    return sentences


def process_sentence_tokens(
    tokens: list[tuple[str, float | None, float | None]],
    sentence_start_sec: float,
    sentence_duration_sec: float,
    sentence_i: int,
    word_start_i: int,
) -> list[TranscriptWord]:
    """Convert Kokoro tokens to TranscriptWord models enforcing Rules 1-3.

    Rule 1: Punctuation (no letters/digits) attaches to adjacent words without creating a word.
            Opening punctuation or initial punctuation attaches to the following word;
            closing punctuation attaches to the preceding word.
    Rule 2: None timestamps get linear interpolation within the sentence between timed neighbours.
    Rule 3: start_ms/end_ms = round_half_up((sentence_start + ts) * 1000).
    """
    if not tokens:
        return []

    # Step 1: Identify word tokens and attach punctuation tokens
    # Group punctuation onto word tokens
    raw_words: list[dict[str, Any]] = []
    pending_prefix = ""

    for text, start_ts, end_ts in tokens:
        has_alnum = any(c.isalnum() for c in text)
        if not has_alnum:
            # Punctuation token
            is_opening = any(c in OPENING_PUNCTUATION for c in text)
            if not raw_words or is_opening:
                # Prepend to next word
                pending_prefix += text
            else:
                # Append to previous word
                raw_words[-1]["text"] += text
        else:
            word_text = pending_prefix + text
            pending_prefix = ""
            raw_words.append(
                {
                    "text": word_text,
                    "start_ts": start_ts,
                    "end_ts": end_ts,
                }
            )

    # If trailing punctuation remains, attach to the last word if present
    if pending_prefix and raw_words:
        raw_words[-1]["text"] += pending_prefix

    if not raw_words:
        return []

    # Step 2: Linear interpolation for None timestamps (Rule 2)
    n = len(raw_words)
    # Find all indices with valid start_ts and end_ts
    for i in range(n):
        if raw_words[i]["start_ts"] is None or raw_words[i]["end_ts"] is None:
            # Find previous timed point
            prev_t = 0.0
            for p in range(i - 1, -1, -1):
                if raw_words[p]["end_ts"] is not None:
                    prev_t = raw_words[p]["end_ts"]
                    break

            # Find next timed point
            next_t = sentence_duration_sec
            next_idx = n
            for s in range(i + 1, n):
                if raw_words[s]["start_ts"] is not None:
                    next_t = raw_words[s]["start_ts"]
                    next_idx = s
                    break

            # Interpolate for the contiguous block of untimed words [i..next_idx-1]
            gap_count = next_idx - i
            step = (next_t - prev_t) / (gap_count + 1)
            for k in range(gap_count):
                cur_idx = i + k
                t_start = prev_t + (k + 1) * step
                t_end = t_start + step
                raw_words[cur_idx]["start_ts"] = t_start
                raw_words[cur_idx]["end_ts"] = t_end

    # Step 3: Convert to milliseconds (Rule 3)
    words: list[TranscriptWord] = []
    for idx, rw in enumerate(raw_words):
        s_ts = rw["start_ts"]
        e_ts = rw["end_ts"]
        w_start_ms = round_half_up((sentence_start_sec + s_ts) * 1000.0)
        w_end_ms = round_half_up((sentence_start_sec + e_ts) * 1000.0)
        if w_end_ms <= w_start_ms:
            w_end_ms = w_start_ms + 40

        words.append(
            TranscriptWord(
                i=word_start_i + idx,
                text=rw["text"],
                start_ms=w_start_ms,
                end_ms=w_end_ms,
                sentence_i=sentence_i,
            )
        )

    return words


def enforce_rule4_invariants(words: list[TranscriptWord]) -> list[TranscriptWord]:
    """Enforce transcript invariants (Rule 4):

    If start_ms[i] < end_ms[i-1], set end_ms[i-1] = start_ms[i].
    If then end_ms <= start_ms, set end_ms = start_ms + 40.
    """
    if not words:
        return []

    repaired = list(words)
    # Ensure word 0 has end_ms > start_ms
    if repaired[0].end_ms <= repaired[0].start_ms:
        repaired[0] = repaired[0].model_copy(update={"end_ms": repaired[0].start_ms + 40})

    for i in range(1, len(repaired)):
        prev = repaired[i - 1]
        curr = repaired[i]

        if curr.start_ms < prev.end_ms:
            prev = prev.model_copy(update={"end_ms": curr.start_ms})
            if prev.end_ms <= prev.start_ms:
                prev = prev.model_copy(update={"end_ms": prev.start_ms + 40})
                if curr.start_ms < prev.end_ms:
                    curr = curr.model_copy(update={"start_ms": prev.end_ms})
                    if curr.end_ms <= curr.start_ms:
                        curr = curr.model_copy(update={"end_ms": curr.start_ms + 40})
            repaired[i - 1] = prev
            repaired[i] = curr
        elif curr.end_ms <= curr.start_ms:
            curr = curr.model_copy(update={"end_ms": curr.start_ms + 40})
            repaired[i] = curr

    return repaired


def narrate(
    ingest: IngestRecord,
    voice: VoiceDecision,
    out_dir: Path,
) -> tuple[Transcript, NarrationOffsets]:
    """Synthesize narration audio with Kokoro and generate transcript and offsets."""
    audio_dir = out_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    raw_wav_path = audio_dir / "narration_24k_raw.wav"
    final_wav_path = audio_dir / "narration.wav"

    sentence_specs = build_sentence_list(ingest)
    pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M", device="cpu")

    audio_chunks: list[np.ndarray] = []
    current_sample = 0

    sentence_offsets: list[SentenceOffset] = []
    transcript_sentences: list[TranscriptSentence] = []
    all_words: list[TranscriptWord] = []
    word_counter = 0

    num_sentences = len(sentence_specs)

    for idx, (sentence_text, p_idx, is_title) in enumerate(sentence_specs):
        sentence_start_sample = current_sample
        sentence_audio_parts: list[np.ndarray] = []
        sentence_tokens: list[tuple[str, float | None, float | None]] = []

        generator = pipeline(sentence_text, voice=voice.voice, speed=1.0)
        sentence_samples_emitted = 0

        for res in generator:
            audio_np = res.audio.numpy() if hasattr(res.audio, "numpy") else np.array(res.audio)
            sentence_audio_parts.append(audio_np)

            res_offset_sec = sentence_samples_emitted / float(KOKORO_SAMPLE_RATE)
            if hasattr(res, "tokens") and res.tokens:
                for tok in res.tokens:
                    s_ts = res_offset_sec + tok.start_ts if tok.start_ts is not None else None
                    e_ts = res_offset_sec + tok.end_ts if tok.end_ts is not None else None
                    sentence_tokens.append((tok.text, s_ts, e_ts))

            sentence_samples_emitted += len(audio_np)

        if sentence_audio_parts:
            combined_audio = np.concatenate(sentence_audio_parts)
        else:
            combined_audio = np.zeros(0, dtype=np.float32)

        # Pad sentence audio to multiple of 24 samples (1 ms) so sample math is exact
        pad_len = (24 - (len(combined_audio) % 24)) % 24
        if pad_len > 0:
            combined_audio = np.pad(combined_audio, (0, pad_len))

        sentence_samples = len(combined_audio)
        audio_chunks.append(combined_audio)

        sentence_end_sample = sentence_start_sample + sentence_samples
        current_sample = sentence_end_sample

        # Offsets in ms
        sent_start_ms = sentence_start_sample // 24
        sent_end_ms = sentence_end_sample // 24

        sentence_offsets.append(
            SentenceOffset(
                i=idx,
                start_ms=sent_start_ms,
                end_ms=sent_end_ms,
            )
        )

        # Process words for this sentence
        sentence_start_sec = sentence_start_sample / float(KOKORO_SAMPLE_RATE)
        sentence_duration_sec = sentence_samples / float(KOKORO_SAMPLE_RATE)
        sent_words = process_sentence_tokens(
            tokens=sentence_tokens,
            sentence_start_sec=sentence_start_sec,
            sentence_duration_sec=sentence_duration_sec,
            sentence_i=idx,
            word_start_i=word_counter,
        )

        word_start_idx = word_counter
        word_end_idx = word_counter + len(sent_words)
        word_counter = word_end_idx
        all_words.extend(sent_words)

        transcript_sentences.append(
            TranscriptSentence(
                i=idx,
                text=sentence_text,
                start_ms=sent_start_ms,
                end_ms=sent_end_ms,
                word_start=word_start_idx,
                word_end=word_end_idx,
                paragraph_i=p_idx,
                is_title=is_title,
            )
        )

        # Insert pause after sentence
        is_last = idx == num_sentences - 1
        if is_last:
            pause_ms = TAIL_SILENCE_MS
        elif is_title:
            pause_ms = PAUSE_AFTER_TITLE_MS
        elif sentence_specs[idx + 1][1] != p_idx:
            pause_ms = PAUSE_BETWEEN_PARAGRAPHS_MS
        else:
            pause_ms = PAUSE_BETWEEN_SENTENCES_MS

        pause_samples = pause_ms * 24
        silence = np.zeros(pause_samples, dtype=np.float32)
        audio_chunks.append(silence)
        current_sample += pause_samples

    # Enforce Rule 4 transcript invariants across all words
    repaired_words = enforce_rule4_invariants(all_words)

    # Full raw waveform
    full_raw_audio = np.concatenate(audio_chunks) if audio_chunks else np.zeros(0, dtype=np.float32)
    sf.write(str(raw_wav_path), full_raw_audio, KOKORO_SAMPLE_RATE, subtype="FLOAT")

    # Two-pass loudnorm to 48 kHz mono s16 at -16 LUFS
    loudnorm_two_pass(
        raw_wav_path,
        final_wav_path,
        target_lufs=-16.0,
        true_peak=-1.5,
        lra=11.0,
        sample_rate=48000,
        channels=1,
    )

    duration_ms = current_sample // 24
    if repaired_words and duration_ms < repaired_words[-1].end_ms:
        duration_ms = repaired_words[-1].end_ms

    transcript = Transcript(
        schema_version=1,
        source="tts",
        audio_path="audio/narration.wav",
        duration_ms=duration_ms,
        words=repaired_words,
        sentences=transcript_sentences,
    )

    narration_offsets = NarrationOffsets(
        schema_version=1,
        voice=voice.voice,
        sentences=sentence_offsets,
    )

    return transcript, narration_offsets

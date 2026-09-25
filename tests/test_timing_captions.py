"""Unit tests for timing/captions.py pagination rules and timing."""

from animated_infographics.contracts.models import (
    Transcript,
    TranscriptSentence,
    TranscriptWord,
)
from animated_infographics.timing.captions import (
    paginate,
)


def _make_transcript_sentences(
    sentence_words: list[list[tuple[str, int, int]]],
) -> Transcript:
    words: list[TranscriptWord] = []
    sentences: list[TranscriptSentence] = []

    for s_i, s_words in enumerate(sentence_words):
        w_start = len(words)
        for w_text, start_ms, end_ms in s_words:
            words.append(
                TranscriptWord(
                    i=len(words),
                    text=w_text,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    sentence_i=s_i,
                )
            )
        w_end = len(words)
        sentences.append(
            TranscriptSentence(
                i=s_i,
                text=" ".join(words[w].text for w in range(w_start, w_end)),
                start_ms=words[w_start].start_ms,
                end_ms=words[w_end - 1].end_ms,
                word_start=w_start,
                word_end=w_end,
                paragraph_i=0,
                is_title=False,
            )
        )

    return Transcript(
        source="tts",
        audio_path="audio/narration.wav",
        duration_ms=words[-1].end_ms + 1000 if words else 0,
        words=words,
        sentences=sentences,
    )


def test_captions_3_word_cap() -> None:
    """Verify pages never contain more than 3 words."""
    words = [
        ("One", 0, 100),
        ("two", 100, 200),
        ("three", 200, 300),
        ("four", 300, 400),
        ("five", 400, 500),
    ]
    transcript = _make_transcript_sentences([words])
    pages = paginate(transcript)

    assert len(pages) == 2
    assert len(pages[0].words) == 3
    assert len(pages[1].words) == 2
    assert [w.text for w in pages[0].words] == ["One", "two", "three"]
    assert [w.text for w in pages[1].words] == ["four", "five"]


def test_captions_22_char_cap() -> None:
    """Verify pages break before exceeding 22 characters."""
    # "Aaaaaaaaaa" (10 chars), "Bbbbbbbbbb" (10 chars) -> "Aaaaaaaaaa Bbbbbbbbbb" = 21 chars <= 22
    # Third word "C" -> 21 + 1 + 1 = 23 chars > 22 -> must break!
    words = [
        ("Aaaaaaaaaa", 0, 100),
        ("Bbbbbbbbbb", 100, 200),
        ("C", 200, 300),
    ]
    transcript = _make_transcript_sentences([words])
    pages = paginate(transcript)

    assert len(pages) == 2
    assert len(pages[0].words) == 2
    assert len(pages[1].words) == 1
    assert [w.text for w in pages[0].words] == ["Aaaaaaaaaa", "Bbbbbbbbbb"]
    assert [w.text for w in pages[1].words] == ["C"]


def test_captions_comma_break_at_2_or_more_words() -> None:
    """Verify comma/punctuation breaks page when page has >= 2 words."""
    # Page 1: "Hello," (only 1 word, does NOT break yet)
    # "world," (2 words, ends with comma -> breaks!)
    # Page 2: "how" "are" "you" (3 words cap)
    words = [
        ("Hello,", 0, 100),
        ("world,", 100, 200),
        ("how", 200, 300),
        ("are", 300, 400),
        ("you", 400, 500),
    ]
    transcript = _make_transcript_sentences([words])
    pages = paginate(transcript)

    assert len(pages) == 2
    assert len(pages[0].words) == 2
    assert [w.text for w in pages[0].words] == ["Hello,", "world,"]
    assert len(pages[1].words) == 3
    assert [w.text for w in pages[1].words] == ["how", "are", "you"]


def test_captions_no_page_crosses_sentence_boundary() -> None:
    """Verify caption pages never cross a sentence boundary."""
    s1_words = [("Short", 0, 100)]
    s2_words = [("Another", 150, 250), ("sentence", 250, 350)]

    transcript = _make_transcript_sentences([s1_words, s2_words])
    pages = paginate(transcript)

    assert len(pages) == 2
    assert [w.text for w in pages[0].words] == ["Short"]
    assert [w.text for w in pages[1].words] == ["Another", "sentence"]


def test_captions_gap_tail_rule() -> None:
    """Verify page ends at next page start if gap <= 700ms, else last word end + 300ms."""
    # Sentence 1: words end at 500. Next page starts at 800 (gap = 300 ms <= 700 ms).
    # Page 1 end must be 800 (next page start).
    # Sentence 2: words end at 1200. Next sentence starts at 2500 (gap = 1300 ms > 700 ms).
    # Page 2 end must be 1200 + 300 = 1500 ms.
    # Sentence 3 (final): words end at 3000.
    # Page 3 end must be 3000 + 300 = 3300 ms.
    s1 = [("Page", 0, 200), ("one", 200, 500)]
    s2 = [("Page", 800, 1000), ("two", 1000, 1200)]
    s3 = [("Final", 2500, 2800), ("page", 2800, 3000)]

    transcript = _make_transcript_sentences([s1, s2, s3])
    pages = paginate(transcript)

    assert len(pages) == 3
    # Page 1: gap = 300 <= 700 -> end = 800
    assert pages[0].start_frame == 0
    assert pages[0].end_frame == 800

    # Page 2: gap = 1300 > 700 -> end = 1200 + 300 = 1500
    assert pages[1].start_frame == 800
    assert pages[1].end_frame == 1500

    # Page 3: final page -> end = 3000 + 300 = 3300
    assert pages[2].start_frame == 2500
    assert pages[2].end_frame == 3300


def test_captions_23_char_word_alone_on_page() -> None:
    """Verify a 23+ char word is placed alone on its own page."""
    long_word = "Supercalifragilisticexp"  # 23 chars
    words = [
        ("Start", 0, 100),
        (long_word, 100, 200),
        ("End", 200, 300),
    ]
    transcript = _make_transcript_sentences([words])
    pages = paginate(transcript)

    assert len(pages) == 3
    assert [w.text for w in pages[0].words] == ["Start"]
    assert [w.text for w in pages[1].words] == [long_word]
    assert [w.text for w in pages[2].words] == ["End"]

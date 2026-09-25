"""Unit tests for ASR word segmentation, abbreviation handling, and paragraph gaps."""

from animated_infographics.audio.transcribe import is_sentence_boundary, segment_asr_words


def test_is_sentence_boundary() -> None:
    """Verify sentence boundaries detect punctuation but exempt abbreviations."""
    # Endings with punctuation
    assert is_sentence_boundary("hello.") is True
    assert is_sentence_boundary("world!") is True
    assert is_sentence_boundary("really?") is True
    assert is_sentence_boundary('said."') is True
    assert is_sentence_boundary("done!')") is True

    # No sentence-ending punctuation
    assert is_sentence_boundary("hello") is False
    assert is_sentence_boundary('said,"') is False

    # Abbreviations exempt
    assert is_sentence_boundary("mr.") is False
    assert is_sentence_boundary("Mr.") is False
    assert is_sentence_boundary("dr.") is False
    assert is_sentence_boundary("u.s.") is False
    assert is_sentence_boundary("etc.") is False
    assert is_sentence_boundary('etc."') is False


def test_segment_asr_words_abbreviations_and_paragraphs() -> None:
    """Verify sentences don't break on abbreviations, but break on paragraph gaps."""
    raw_words = [
        ("Mr.", 0, 300),
        ("Smith", 350, 700),
        ("arrived.", 750, 1200),
        # Gap of 1300 ms (2500 - 1200 >= 1200 ms) -> new paragraph
        ("He", 2500, 2700),
        ("left.", 2750, 3000),
    ]
    words, sentences = segment_asr_words(raw_words)

    assert len(words) == 5
    assert len(sentences) == 2

    # First sentence includes Mr. without breaking
    assert sentences[0].text == "Mr. Smith arrived."
    assert sentences[0].paragraph_i == 0
    assert sentences[0].is_title is False
    assert sentences[0].word_start == 0
    assert sentences[0].word_end == 3

    # Second sentence is in paragraph 1
    assert sentences[1].text == "He left."
    assert sentences[1].paragraph_i == 1
    assert sentences[1].is_title is False
    assert sentences[1].word_start == 3
    assert sentences[1].word_end == 5

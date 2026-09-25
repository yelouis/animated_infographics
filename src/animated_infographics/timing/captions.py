"""Caption pagination and timing algorithms."""

from collections.abc import Sequence

from animated_infographics.contracts.models import (
    CaptionPage,
    CaptionWord,
    Transcript,
    TranscriptWord,
)
from animated_infographics.timing.frames import ms_to_frame

CAPTION_MAX_WORDS: int = 3
CAPTION_MAX_CHARS: int = 22
CAPTION_MAX_GAP_MS: int = 700
CAPTION_TAIL_MS: int = 300

PUNCT_BREAKS: tuple[str, ...] = (",", ";", ":", "—", "--")


def paginate(transcript: Transcript, to_frames: bool = False) -> list[CaptionPage]:
    """Break transcript words into caption pages according to design constraints.

    Per sentence (pages never cross a sentence boundary):
    - Max 3 words per page
    - Max 22 chars per page (including spaces)
    - Break at punctuation (, ; : — --) if page has >= 2 words
    - A 23+ char word is alone on its page
    - Page timing: start = first word start; end = next page start if gap <= 700ms,
      else last word end + 300ms
    - Final page ends at last word end + 300ms
    """
    raw_pages: list[list[TranscriptWord]] = []

    for sentence in transcript.sentences:
        sentence_words = transcript.words[sentence.word_start : sentence.word_end]
        page: list[TranscriptWord] = []

        for w in sentence_words:
            if page and (
                len(page) == CAPTION_MAX_WORDS
                or len(" ".join(p.text for p in page + [w])) > CAPTION_MAX_CHARS
            ):
                raw_pages.append(page)
                page = []

            page.append(w)

            if len(page) >= 2 and w.text.rstrip().endswith(PUNCT_BREAKS):
                raw_pages.append(page)
                page = []

        if page:
            raw_pages.append(page)

    if not raw_pages:
        return []

    # Calculate page timings (in milliseconds)
    pages_ms: list[tuple[int, int, list[TranscriptWord]]] = []
    num_pages = len(raw_pages)

    for i in range(num_pages):
        p_words = raw_pages[i]
        start_ms = p_words[0].start_ms
        last_word_end_ms = p_words[-1].end_ms

        if i < num_pages - 1:
            next_start_ms = raw_pages[i + 1][0].start_ms
            gap_ms = next_start_ms - last_word_end_ms
            if gap_ms <= CAPTION_MAX_GAP_MS:
                end_ms = next_start_ms
            else:
                end_ms = last_word_end_ms + CAPTION_TAIL_MS
        else:
            end_ms = last_word_end_ms + CAPTION_TAIL_MS

        pages_ms.append((start_ms, end_ms, p_words))

    # Construct CaptionPage objects
    result_pages: list[CaptionPage] = []
    for start_val, end_val, p_words in pages_ms:
        if to_frames:
            page_start = ms_to_frame(start_val)
            page_end = ms_to_frame(end_val)
            c_words = [
                CaptionWord(
                    text=w.text,
                    start_frame=ms_to_frame(w.start_ms),
                    end_frame=ms_to_frame(w.end_ms),
                )
                for w in p_words
            ]
        else:
            page_start = start_val
            page_end = end_val
            c_words = [
                CaptionWord(
                    text=w.text,
                    start_frame=w.start_ms,
                    end_frame=w.end_ms,
                )
                for w in p_words
            ]

        result_pages.append(
            CaptionPage(
                start_frame=page_start,
                end_frame=page_end,
                words=c_words,
            )
        )

    return result_pages


def pages_to_frames(pages: Sequence[CaptionPage]) -> list[CaptionPage]:
    """Convert millisecond-timed CaptionPages into frame-timed CaptionPages."""
    converted: list[CaptionPage] = []
    for p in pages:
        converted.append(
            CaptionPage(
                start_frame=ms_to_frame(p.start_frame),
                end_frame=ms_to_frame(p.end_frame),
                words=[
                    CaptionWord(
                        text=w.text,
                        start_frame=ms_to_frame(w.start_frame),
                        end_frame=ms_to_frame(w.end_frame),
                    )
                    for w in p.words
                ],
            )
        )
    return converted

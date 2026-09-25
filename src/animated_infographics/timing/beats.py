"""Beat construction, merging, and splitting algorithms."""

import logging
from collections.abc import Sequence

from animated_infographics.contracts.models import Beat, Transcript, TranscriptWord

logger = logging.getLogger(__name__)

BEAT_MIN_MS: int = 1500
BEAT_TARGET_MIN_MS: int = 2500
BEAT_TARGET_MAX_MS: int = 6000
BEAT_MAX_MS: int = 8000

PUNCT_SUFFIXES: tuple[str, ...] = (",", ";", ":", "—", "--")


def _compute_bounds(
    ranges: list[tuple[int, int]], words: Sequence[TranscriptWord]
) -> list[tuple[int, int]]:
    """Compute tiled [start_ms, end_ms) bounds for each word range."""
    bounds: list[tuple[int, int]] = []
    n = len(ranges)
    for i in range(n):
        w_start, w_end = ranges[i]
        start_ms = 0 if i == 0 else words[w_start].start_ms
        if i < n - 1:
            next_w_start = ranges[i + 1][0]
            end_ms = words[next_w_start].start_ms
        else:
            end_ms = words[w_end - 1].end_ms
        bounds.append((start_ms, end_ms))
    return bounds


def build_beats(
    transcript: Transcript,
    groups: Sequence[Sequence[int]],
    *,
    skip_merge: bool = False,
) -> list[Beat]:
    """Build beats from sentence groups with merge and split passes.

    1. Build initial beats from groups. Title sentence is always beat 0.
    2. Merge pass: merge beats k >= 1 under BEAT_MIN_MS with smaller neighbour.
    3. Split pass: split beats over BEAT_MAX_MS at highest scoring boundary.
    4. Construct tiled Beat models.
    """
    words = transcript.words
    sentences = transcript.sentences

    if not words or not sentences:
        return []

    # Identify if sentence 0 is a title sentence
    has_title = sentences[0].is_title

    # 1. Normalize groups
    # Default fallback: one group per sentence
    clean_groups: list[list[int]] = []
    if groups:
        for g in groups:
            clean_g = [int(idx) for idx in g if 0 <= idx < len(sentences)]
            if clean_g:
                clean_groups.append(clean_g)

    if not clean_groups:
        clean_groups = [[s.i] for s in sentences]

    if has_title:
        # Title sentence must be its own beat 0
        filtered_groups: list[list[int]] = []
        for g in clean_groups:
            rem = [idx for idx in g if idx != 0]
            if rem:
                filtered_groups.append(rem)
        clean_groups = [[0]] + filtered_groups

    # Convert groups of sentence indices to word index ranges [w_start, w_end)
    ranges: list[tuple[int, int]] = []
    for g in clean_groups:
        group_sentences = [sentences[idx] for idx in g]
        w_start = min(s.word_start for s in group_sentences)
        w_end = max(s.word_end for s in group_sentences)
        ranges.append((w_start, w_end))

    # Sort ranges by word_start and ensure contiguous partition of words
    ranges.sort(key=lambda r: r[0])
    normalized_ranges: list[tuple[int, int]] = []
    curr_start = 0
    for r_start, r_end in ranges:
        if r_start > curr_start:
            # Fill gap
            normalized_ranges.append((curr_start, r_start))
        normalized_ranges.append((max(curr_start, r_start), r_end))
        curr_start = max(curr_start, r_end)
    if curr_start < len(words):
        normalized_ranges.append((curr_start, len(words)))
    ranges = normalized_ranges

    # 2. Merge pass: repeat while some beat k >= 1 has duration < BEAT_MIN_MS
    while not skip_merge:
        bounds = _compute_bounds(ranges, words)
        found_k: int | None = None
        for k in range(1, len(ranges)):
            if bounds[k][1] - bounds[k][0] < BEAT_MIN_MS:
                found_k = k
                break

        if found_k is None:
            break

        k = found_k
        can_merge_prev = k - 1 >= 1  # Beat 0 is never a merge target
        can_merge_next = k + 1 < len(ranges)

        if not can_merge_prev and not can_merge_next:
            # Cannot merge anywhere (e.g. only 2 beats: beat 0 and beat 1)
            break

        if can_merge_prev and can_merge_next:
            dur_prev = bounds[k][1] - bounds[k - 1][0]
            dur_next = bounds[k + 1][1] - bounds[k][0]
            # Ties -> previous neighbour
            target = k - 1 if dur_prev <= dur_next else k + 1
        elif can_merge_prev:
            target = k - 1
        else:
            target = k + 1

        if target == k - 1:
            merged = (ranges[k - 1][0], ranges[k][1])
            ranges = ranges[: k - 1] + [merged] + ranges[k + 1 :]
        else:
            merged = (ranges[k][0], ranges[k + 1][1])
            ranges = ranges[:k] + [merged] + ranges[k + 2 :]

    # 3. Split pass: repeat while some beat has duration > BEAT_MAX_MS
    unsplitable: set[tuple[int, int]] = set()
    while True:
        bounds = _compute_bounds(ranges, words)
        found_k = None
        for k in range(len(ranges)):
            if (ranges[k] not in unsplitable) and (bounds[k][1] - bounds[k][0] > BEAT_MAX_MS):
                found_k = k
                break

        if found_k is None:
            break

        k = found_k
        w_start, w_end = ranges[k]
        b_start, b_end = bounds[k]
        t_midpoint = (b_start + b_end) / 2.0

        best_split: int | None = None
        best_score = float("-inf")

        for w_split in range(w_start + 1, w_end):
            left_dur = words[w_split].start_ms - b_start
            right_dur = b_end - words[w_split].start_ms
            if left_dur < BEAT_MIN_MS or right_dur < BEAT_MIN_MS:
                continue

            left_word = words[w_split - 1]
            right_word = words[w_split]
            gap_ms = right_word.start_ms - left_word.end_ms
            ends_punct = left_word.text.rstrip().endswith(PUNCT_SUFFIXES)
            punct_bonus = 1000 if ends_punct else 0
            t_boundary = right_word.start_ms
            penalty = abs(t_boundary - t_midpoint) / 4.0
            score = gap_ms + punct_bonus - penalty

            if score > best_score:  # strictly greater ensures ties pick earlier boundary
                best_score = score
                best_split = w_split

        if best_split is None:
            logger.warning("beat %d exceeds BEAT_MAX_MS with no valid split", k)
            unsplitable.add(ranges[k])
        else:
            ranges = ranges[:k] + [(w_start, best_split), (best_split, w_end)] + ranges[k + 1 :]

    # 4. Final bounds and Beat objects
    final_bounds = _compute_bounds(ranges, words)
    beats: list[Beat] = []
    for i in range(len(ranges)):
        w_start, w_end = ranges[i]
        b_start, b_end = final_bounds[i]
        beat_text = " ".join(words[w].text for w in range(w_start, w_end))
        beats.append(
            Beat(
                i=i,
                word_start=w_start,
                word_end=w_end,
                start_ms=b_start,
                end_ms=b_end,
                text=beat_text,
            )
        )

    return beats

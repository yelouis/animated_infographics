"""Grounding and normalization helpers for planner verification."""

import re
import unicodedata

SMALL_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}

SCALE_WORDS = {
    "hundred": 100,
    "thousand": 1_000,
    "million": 1_000_000,
    "billion": 1_000_000_000,
}

DIGIT_SCALE_MAP = {
    "thousand": 1e3,
    "million": 1e6,
    "billion": 1e9,
}


def norm(s: str) -> str:
    """Normalize text: casefold, straight quotes, strip non-alphanumeric/spaces, collapse spaces.

    Per design_planner.md §8:
    - casefold
    - curly quotes -> straight
    - replace every char that is not letter, digit, apostrophe or space with a space
    - collapse whitespace, strip
    """
    if not s:
        return ""

    # Unicode normalization to decompose special forms
    s = unicodedata.normalize("NFKD", s)

    # Curly quotes to straight
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    s = s.casefold()

    # Replace anything not a letter, digit, apostrophe, or whitespace with space
    s = re.sub(r"[^a-z0-9'\s]+", " ", s)

    # Collapse whitespace and strip
    return re.sub(r"\s+", " ", s).strip()


def is_verbatim_span(needle: str, haystack: str) -> bool:
    """Check if normalized needle is a word-boundary substring of normalized haystack."""
    norm_needle = norm(needle)
    norm_haystack = norm(haystack)

    if not norm_needle or not norm_haystack:
        return False

    pattern = r"(?:^|\s)" + re.escape(norm_needle) + r"(?:$|\s)"
    return bool(re.search(pattern, norm_haystack))


def _parse_small(w: str) -> int | None:
    w = w.lower()
    if w in SMALL_WORDS:
        return SMALL_WORDS[w]
    if "-" in w:
        parts = w.split("-")
        if len(parts) == 2 and parts[0] in SMALL_WORDS and parts[1] in SMALL_WORDS:
            return SMALL_WORDS[parts[0]] + SMALL_WORDS[parts[1]]
    return None


def _is_num_word(w: str) -> bool:
    return _parse_small(w) is not None or w.lower() in SCALE_WORDS


def _parse_spelled_run(tokens: list[str]) -> float | None:
    if not any(_is_num_word(t) for t in tokens):
        return None
    while tokens and tokens[-1].lower() == "and":
        tokens = tokens[:-1]
    if not tokens:
        return None

    total = 0.0
    current = 0.0
    for i, t in enumerate(tokens):
        tl = t.lower()
        if tl in ("a", "an"):
            if i == 0 and len(tokens) > 1 and tokens[1].lower() in SCALE_WORDS:
                current = 1.0
            else:
                continue
        elif tl == "and":
            continue
        elif (val := _parse_small(tl)) is not None:
            current += val
        elif tl == "hundred":
            if current == 0:
                current = 1.0
            current *= 100
        elif tl in ("thousand", "million", "billion"):
            if current == 0:
                current = 1.0
            total += current * SCALE_WORDS[tl]
            current = 0.0
    total += current
    return total


def _extract_spelled_numbers(text: str) -> list[float]:
    tokens = re.findall(r"\b[A-Za-z0-9'\-]+\b", text)
    runs: list[list[str]] = []
    current_run: list[str] = []
    for i, token in enumerate(tokens):
        tl = token.lower()
        if _is_num_word(tl):
            current_run.append(token)
        elif (
            tl in ("a", "an")
            and not current_run
            and i + 1 < len(tokens)
            and tokens[i + 1].lower() in SCALE_WORDS
        ):
            current_run.append(token)
        elif tl == "and" and current_run and any(_is_num_word(t) for t in current_run):
            if i + 1 < len(tokens) and _is_num_word(tokens[i + 1].lower()):
                current_run.append(token)
            else:
                if current_run:
                    runs.append(current_run)
                    current_run = []
        else:
            if current_run:
                runs.append(current_run)
                current_run = []
    if current_run:
        runs.append(current_run)

    results: list[float] = []
    for r in runs:
        val = _parse_spelled_run(r)
        if val is not None:
            results.append(val)
    return results


def numbers(s: str) -> list[float]:
    r"""Extract numbers from text as a multiset of floats.

    Per design_planner.md §8:
    - Digit numbers: \d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?, commas removed.
      If followed by whitespace plus thousand|million|billion (case-insensitive),
      multiply by 1e3/1e6/1e9 and also keep the unscaled value.
    - Spelled numbers: maximal runs of zero..nineteen, twenty..ninety (hyphenated compounds
      like twenty-one included), hundred, thousand, million, billion, with an optional
      leading a (a thousand = 1000), parsed with standard English place-value rules.
    - % is stripped (the value is the number).
    """
    if not s:
        return []

    results: list[float] = []

    # 1. Digit numbers
    pattern = re.compile(
        r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?:\s*%)?(?:\s+(thousand|million|billion)\b)?",
        re.IGNORECASE,
    )
    for m in pattern.finditer(s):
        num_str = m.group(1).replace(",", "")
        try:
            val = float(num_str)
        except ValueError:
            continue
        results.append(val)
        scale_word = m.group(2)
        if scale_word:
            scaled = val * DIGIT_SCALE_MAP[scale_word.lower()]
            results.append(scaled)

    # 2. Spelled numbers
    spelled = _extract_spelled_numbers(s)
    results.extend(spelled)

    return results


def digits_grounded(label: str, transcript_text: str) -> bool:
    """Check if all maximal digit runs in label are grounded in transcript.

    Per design_planner.md §8:
    Every maximal digit run in label appears as a digit run in the whole transcript,
    or equals a spelled number found there.
    """
    digit_runs = re.findall(r"\d+", label)
    if not digit_runs:
        return True

    transcript_digit_runs = set(re.findall(r"\d+", transcript_text))
    transcript_numbers = set(numbers(transcript_text))

    for d in digit_runs:
        if d in transcript_digit_runs:
            continue
        try:
            val = float(d)
            if any(abs(val - n) < 1e-4 for n in transcript_numbers):
                continue
        except ValueError:
            pass
        return False

    return True


def is_stat_grounded(value: float, display_scale: str, beat_text: str) -> bool:
    """Check if stat callout value is grounded in beat text.

    Per design_planner.md §8:
    N = value * scale(display_scale)
    Grounded iff some n in numbers(beat.text) with |n - N| <= 0.005 * max(|N|, 1)
    """
    scale_map = {
        "none": 1.0,
        "thousand": 1e3,
        "million": 1e6,
        "billion": 1e9,
    }
    scale = scale_map.get(display_scale, 1.0)
    target = value * scale

    tolerance = 0.005 * max(abs(target), 1.0)
    beat_numbers = numbers(beat_text)
    return any(abs(n - target) <= tolerance for n in beat_numbers)


def is_kinetic_quote_grounded(
    text: str, emphasis: list[str], beat_text: str
) -> tuple[bool, list[str]]:
    """Check if kinetic quote text and emphasis are grounded in beat text.

    Per design_planner.md §8:
    - text: norm(text without trailing "…") is a substring of norm(beat.text)
      starting and ending at word boundaries.
    - emphasis: each norm(word) is a whole word of norm(text).
    """
    errors: list[str] = []
    clean_text = text.rstrip("…").rstrip()
    if not is_verbatim_span(clean_text, beat_text):
        errors.append(f"props.text: '{text}' is not a verbatim span of the beat narration")

    norm_quote_words = set(norm(text).split())
    for emp in emphasis:
        emp_words = norm(emp).split()
        if not emp_words or not all(w in norm_quote_words for w in emp_words):
            errors.append(f"props.emphasis: '{emp}' is not a whole word of quote text")

    return (len(errors) == 0, errors)

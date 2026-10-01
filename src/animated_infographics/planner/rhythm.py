"""Reaction-shot rhythm rules and target resolution for planner selection (R7).

Per design_planner.md §4.
"""

import re
from builtins import next as builtin_next

from animated_infographics.contracts.models import Bible

QUOTED = re.compile(r"\"[^\"]*\"|“[^”]*”")
FIRST_PERSON = re.compile(r"\b(i|me|my|mine|myself|we|us|our)\b", re.IGNORECASE)
STOP_TOKENS = frozenset({"the", "and", "for", "with", "from"})


def name_tokens(name: str) -> list[str]:
    """Extract tokens of length >= 3 from casefolded name, ignoring common stopwords."""
    tokens = re.findall(r"[a-z0-9]+", name.casefold())
    return [t for t in tokens if len(t) >= 3 and t not in STOP_TOKENS]


def named_at(name: str, text: str) -> int | None:
    """Return smallest character offset in casefolded text where any token matches.

    Matches token optionally followed by 's, ’s, or s at word boundaries.
    """
    tokens = name_tokens(name)
    if not tokens:
        return None
    text_lower = text.casefold()
    earliest: int | None = None
    for tok in tokens:
        pat = re.compile(rf"\b{re.escape(tok)}(?:s|'s|’s)?\b", re.IGNORECASE)
        m = pat.search(text_lower)
        if m:
            if earliest is None or m.start() < earliest:
                earliest = m.start()
    return earliest


def rhythm_target(
    text: str,
    bible: Bible,
    prev: str | None = None,
    next: str | None = None,
) -> tuple[str, str] | None:
    """Return (template, entity_id) for the highest-priority picture candidate, or None.

    Priority order per design_planner.md §4:
    1. emotion_beat (only if cast non-empty):
       - the narrator, if the bible has one and beat text outside quotes has first-person words;
       - otherwise the non-narrator cast member named earliest in the beat.
    2. set_piece: the set piece named earliest.
    3. location: the place named earliest.

    Ties go to bible order. Returns the first candidate whose template differs
    from both prev and next.
    """
    candidates: list[tuple[str, str]] = []

    # 1. emotion_beat
    if bible.cast:
        narrator = builtin_next((c for c in bible.cast if c.is_narrator), None)
        unquoted = QUOTED.sub("", text)
        if narrator and FIRST_PERSON.search(unquoted):
            candidates.append(("emotion_beat", narrator.id))
        else:
            non_narrators = [c for c in bible.cast if not c.is_narrator]
            named_cast: list[tuple[int, str]] = []
            for c in non_narrators:
                pos = named_at(c.name, text)
                if pos is not None:
                    named_cast.append((pos, c.id))
            if named_cast:
                # Stable sort preserves bible tie-breaker
                named_cast.sort(key=lambda x: x[0])
                candidates.append(("emotion_beat", named_cast[0][1]))

    # 2. set_piece
    if bible.set_pieces:
        named_sp: list[tuple[int, str]] = []
        for sp in bible.set_pieces:
            pos = named_at(sp.name, text)
            if pos is not None:
                named_sp.append((pos, sp.id))
        if named_sp:
            named_sp.sort(key=lambda x: x[0])
            candidates.append(("set_piece", named_sp[0][1]))

    # 3. location
    if bible.places:
        named_pl: list[tuple[int, str]] = []
        for pl in bible.places:
            pos = named_at(pl.name, text)
            if pos is not None:
                named_pl.append((pos, pl.id))
        if named_pl:
            named_pl.sort(key=lambda x: x[0])
            candidates.append(("location", named_pl[0][1]))

    for tmpl, eid in candidates:
        if tmpl != prev and tmpl != next:
            return (tmpl, eid)

    return None

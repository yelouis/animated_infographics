"""Presentation matching, text normalisation, and tokenisation.

Per design_presentation_simulation.md §3 and §6.2.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from animated_infographics.contracts.templates import WORD_CAPS
from animated_infographics.planner.words import field_values

ENGLISH_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "about",
        "above",
        "after",
        "again",
        "against",
        "all",
        "am",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "because",
        "been",
        "before",
        "being",
        "below",
        "between",
        "both",
        "but",
        "by",
        "cannot",
        "could",
        "did",
        "do",
        "does",
        "doing",
        "down",
        "during",
        "each",
        "few",
        "for",
        "from",
        "further",
        "had",
        "has",
        "have",
        "having",
        "he",
        "her",
        "here",
        "hers",
        "herself",
        "him",
        "himself",
        "his",
        "how",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "itself",
        "me",
        "more",
        "most",
        "my",
        "myself",
        "no",
        "nor",
        "not",
        "of",
        "off",
        "on",
        "once",
        "only",
        "or",
        "other",
        "ought",
        "our",
        "ours",
        "ourselves",
        "out",
        "over",
        "own",
        "same",
        "she",
        "should",
        "so",
        "some",
        "such",
        "than",
        "that",
        "the",
        "their",
        "theirs",
        "them",
        "themselves",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "to",
        "too",
        "under",
        "until",
        "up",
        "very",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "who",
        "whom",
        "why",
        "with",
        "would",
        "you",
        "your",
        "yours",
        "yourself",
        "yourselves",
    }
)


def stem_token(token: str) -> str:
    """Apply suffix stemming for -s, -es, -ed, -ing, -ly while keeping numbers."""
    if token.isdigit():
        return token
    if token.endswith("ing") and len(token) > 5:
        return token[:-3]
    if token.endswith("ly") and len(token) > 4:
        return token[:-2]
    if token.endswith("es") and len(token) > 4:
        return token[:-2]
    if token.endswith("ed") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and len(token) > 3 and not token.endswith("ss"):
        return token[:-1]
    return token


def normalize_tokens(text: str) -> list[str]:
    """Tokenise, casefold, strip punctuation, drop stopwords, and stem."""
    raw_tokens = re.findall(r"[a-z0-9]+", text.casefold())
    stemmed: list[str] = []
    for tok in raw_tokens:
        if tok in ENGLISH_STOPWORDS:
            continue
        stemmed.append(stem_token(tok))
    return stemmed


def normalize_node_text(text: str) -> str:
    """Normalise arbitrary text to a space-joined normalised string."""
    return " ".join(normalize_tokens(text))


def extract_scene_free_text(scene: Any) -> list[str]:
    """Extract free-text strings from scene props defined by WORD_CAPS."""
    template = getattr(scene, "template", None)
    props = getattr(scene, "props", None)
    if not template or not props:
        return []
    props_dict = (
        props.model_dump()
        if hasattr(props, "model_dump")
        else (props if isinstance(props, Mapping) else {})
    )
    caps = WORD_CAPS.get(template, {})
    texts: list[str] = []
    for path in caps:
        for _, val in field_values(props_dict, path):
            if val:
                texts.append(val)
    return texts

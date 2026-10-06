"""Presentation matching, text normalisation, and tokenisation.

Per design_presentation_simulation.md §3 and §6.2.
"""

from __future__ import annotations

import logging
import math
import re
import time
from collections import Counter
from collections.abc import Mapping
from typing import Any

from animated_infographics.contracts.models import TranscriptWord
from animated_infographics.contracts.playback import (
    PlaybackCommit,
    PlaybackHold,
    PlaybackPlan,
)
from animated_infographics.contracts.templates import WORD_CAPS
from animated_infographics.contracts.tree import TreePlan
from animated_infographics.planner.llm import LLMBackend
from animated_infographics.planner.words import field_values

logger = logging.getLogger(__name__)

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


class BM25Index:
    """BM25 index over tree nodes per design_presentation_simulation.md §6.2.

    Parameters: k1 = 1.2, b = 0.75.
    Document frequencies computed over all node texts of the tree.
    """

    def __init__(self, tree: TreePlan, k1: float = 1.2, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.nodes = tree.nodes
        self.node_ids = [n.id for n in tree.nodes]
        self.node_map = {n.id: n for n in tree.nodes}

        self.doc_tokens: dict[str, list[str]] = {n.id: normalize_tokens(n.text) for n in tree.nodes}
        self.doc_lens: dict[str, int] = {nid: len(toks) for nid, toks in self.doc_tokens.items()}
        self.n = len(self.node_ids)
        self.avgdl = sum(self.doc_lens.values()) / max(1, self.n)

        self.doc_tf: dict[str, Counter[str]] = {
            nid: Counter(toks) for nid, toks in self.doc_tokens.items()
        }
        self.df: Counter[str] = Counter()
        for toks in self.doc_tokens.values():
            for term in set(toks):
                self.df[term] += 1

    def idf(self, term: str) -> float:
        """Robertson BM25 IDF: ln((N - df + 0.5) / (df + 0.5) + 1.0)."""
        df = self.df.get(term, 0)
        return math.log((self.n - df + 0.5) / (df + 0.5) + 1.0)

    def score(self, query_tokens: list[str], node_id: str) -> float:
        """Compute BM25 score of a node for the query tokens."""
        tf_map = self.doc_tf.get(node_id)
        if not tf_map or not query_tokens:
            return 0.0

        doc_len = self.doc_lens.get(node_id, 0)
        score = 0.0
        denom_part = self.k1 * (1.0 - self.b + self.b * (doc_len / max(1e-6, self.avgdl)))
        for term in query_tokens:
            if term not in tf_map:
                continue
            tf = tf_map[term]
            idf = self.idf(term)
            term_score = idf * (tf * (self.k1 + 1.0)) / (tf + denom_part)
            score += term_score
        return score


def find_decision_points(words: list[TranscriptWord]) -> list[int]:
    """Find word indices where decision points occur per §6.1.

    A decision point occurs:
    - at the end of any word followed by a gap >= 300 ms, and
    - otherwise at least every 1.5 s of audio, and
    - at the last word.
    """
    if not words:
        return []

    points: list[int] = []
    last_dp_ms = 0

    for i in range(len(words)):
        w = words[i]
        is_last = i == len(words) - 1
        has_gap = False
        if not is_last:
            next_w = words[i + 1]
            if next_w.start_ms - w.end_ms >= 300:
                has_gap = True

        time_since_last = w.end_ms - last_dp_ms
        if has_gap or time_since_last >= 1500:
            points.append(i)
            last_dp_ms = w.end_ms

    return points


class LiveMatcher:
    """Live causal presentation matcher per design_presentation_simulation.md §6."""

    def __init__(
        self,
        tree: TreePlan,
        tiebreak: str = "none",
        backend: LLMBackend | None = None,
    ) -> None:
        self.tree = tree
        self.tiebreak = tiebreak
        self.backend = backend
        self.bm25 = BM25Index(tree)

        self.edge_costs: dict[tuple[str, str], float] = {
            (e.from_, e.to): e.cost for e in tree.edges
        }

        # Find initial node: first slide section node
        self.initial_node_id = self._find_initial_node_id()

    def _find_initial_node_id(self) -> str:
        for node in self.tree.nodes:
            if node.kind == "section":
                return node.id
        return self.tree.nodes[0].id if self.tree.nodes else "d1_section"

    def run(self, words: list[TranscriptWord]) -> PlaybackPlan:
        """Run matcher over words in time order and generate PlaybackPlan."""
        if not words:
            return PlaybackPlan(
                schema_version=1,
                commits=[
                    PlaybackCommit(
                        node_id=self.initial_node_id,
                        at_ms=0,
                        decision_ms=0,
                        compute_ms=0,
                        score=0.0,
                    )
                ],
                holds=[],
            )

        commits: list[PlaybackCommit] = [
            PlaybackCommit(
                node_id=self.initial_node_id,
                at_ms=0,
                decision_ms=0,
                compute_ms=0,
                score=0.0,
            )
        ]
        holds: list[PlaybackHold] = []

        current_node_id = self.initial_node_id
        current_node_start_ms = 0
        prev_top_id: str | None = None

        dp_indices = find_decision_points(words)

        for w_idx in dp_indices:
            t0 = time.perf_counter()
            dp_ms = words[w_idx].end_ms
            ended_words = words[: w_idx + 1]

            # 20-word window
            window = ended_words[-20:]
            query_tokens = normalize_tokens(" ".join(w.text for w in window))

            # Score all eligible nodes
            # Current node has cost 0; other nodes must be reachable in 1 edge
            candidate_scores: list[tuple[str, float]] = []
            for node in self.tree.nodes:
                nid = node.id
                if nid == current_node_id:
                    lex = self.bm25.score(query_tokens, nid)
                    candidate_scores.append((nid, lex))
                elif (current_node_id, nid) in self.edge_costs:
                    cost = self.edge_costs[(current_node_id, nid)]
                    lex = self.bm25.score(query_tokens, nid)
                    candidate_scores.append((nid, lex - cost))

            if not candidate_scores:
                candidate_scores = [(current_node_id, 0.0)]

            # Sort descending by score
            candidate_scores.sort(key=lambda item: item[1], reverse=True)
            top_id, top_score = candidate_scores[0]

            runner_up_id: str | None = None
            runner_up_gap: float | None = None
            if len(candidate_scores) > 1:
                runner_up_id, runner_up_score = candidate_scores[1]
                runner_up_gap = round(top_score - runner_up_score, 3)

            tiebreak_used = False
            # Optional LLM tie-break per §6.4
            if (
                self.tiebreak == "llm"
                and self.backend is not None
                and runner_up_id is not None
                and runner_up_gap is not None
                and runner_up_gap <= 1.0
                and top_id != current_node_id
            ):
                top_node_obj = self.bm25.node_map.get(top_id)
                ru_node_obj = self.bm25.node_map.get(runner_up_id)
                t_window = " ".join(w.text for w in window)
                prompt = (
                    f'Speech window: "{t_window}"\n'
                    f'Candidate 1: {top_id} - "{top_node_obj.text if top_node_obj else ""}"\n'
                    f'Candidate 2: {runner_up_id} - "{ru_node_obj.text if ru_node_obj else ""}"\n\n'
                    "Which talking point is the speaker on now? Answer one id."
                )
                try:
                    resp = self.backend.generate_json(
                        stage="follow",
                        messages=[{"role": "user", "content": prompt}],
                        schema={
                            "type": "object",
                            "properties": {"node_id": {"type": "string"}},
                            "required": ["node_id"],
                        },
                        attempt=0,
                        temperature=0.0,
                        num_predict=48,
                    )
                    picked_id = resp.get("node_id", "").strip() if resp else ""
                except Exception as exc:
                    logger.warning("LLM tiebreak failed: %s", exc)
                    picked_id = ""
                if picked_id == runner_up_id:
                    top_id, runner_up_id = runner_up_id, top_id
                    tiebreak_used = True

            # Commit conditions (§6.3):
            # 1. Top score at 2 consecutive decision points
            # 2. Score exceeds current node's score by >= 1.0
            # 3. Current node has been shown for >= 2.0 s (2000 ms)
            current_score = next((s for nid, s in candidate_scores if nid == current_node_id), 0.0)
            score_gap = top_score - current_score

            consecutive_top = top_id == prev_top_id
            score_gap_met = score_gap >= 1.0
            dwell_met = dp_ms - current_node_start_ms >= 2000
            is_different = top_id != current_node_id

            compute_ms = max(0, int((time.perf_counter() - t0) * 1000))

            if is_different and consecutive_top and score_gap_met and dwell_met:
                # Commit!
                commit_at_ms = dp_ms + compute_ms
                commits.append(
                    PlaybackCommit(
                        node_id=top_id,
                        at_ms=commit_at_ms,
                        decision_ms=dp_ms,
                        compute_ms=compute_ms,
                        score=round(top_score, 3),
                        runner_up_id=runner_up_id,
                        runner_up_gap=runner_up_gap,
                        tiebreak_used=tiebreak_used,
                    )
                )
                current_node_id = top_id
                current_node_start_ms = commit_at_ms
                prev_top_id = None
            else:
                # Hold!
                reasons: list[str] = []
                if not is_different:
                    reasons.append("top_is_current")
                if not consecutive_top:
                    reasons.append("consecutive_top_not_met")
                if not score_gap_met:
                    reasons.append(f"score_gap_{score_gap:.2f}_below_1.0")
                if not dwell_met:
                    dwell_ms = dp_ms - current_node_start_ms
                    reasons.append(f"dwell_{dwell_ms}ms_below_2000ms")

                holds.append(
                    PlaybackHold(
                        decision_ms=dp_ms,
                        current_node_id=current_node_id,
                        top_candidate_id=top_id,
                        top_candidate_score=round(top_score, 3),
                        reason="; ".join(reasons),
                    )
                )
                prev_top_id = top_id

        return PlaybackPlan(schema_version=1, commits=commits, holds=holds)

"""Data contracts for presentation performance and speak timing.

Per design_presentation_simulation.md §4, §5 and design_data_contracts.md §10.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PointTarget(BaseModel):
    """Ground truth reference to a slide and point index."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    slide: str
    point: int


class BackRefTarget(BaseModel):
    """Back-reference target point."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    back_ref: PointTarget


class PerformedSentence(BaseModel):
    """A sentence in the simulated presentation performance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str
    label: PointTarget | Literal["adlib"] | BackRefTarget
    op: Literal["verbatim", "paraphrase", "filler", "adlib", "back_ref"]
    source_sentence_id: int | None = None


class PerformancePlan(BaseModel):
    """Complete presentation performance record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    seed: int
    level: Literal["mild", "strong"]
    sentences: list[PerformedSentence]
    op_counts: dict[str, int]


class SpeakTimingItem(BaseModel):
    """Ground-truth timing for a performed sentence in milliseconds."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sentence_i: int
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
